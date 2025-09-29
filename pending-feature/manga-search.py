import requests
import json
import datetime
import time
import uuid
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("manga_search.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------------------
# Thông số
# -------------------------------
search_title = "Aku no Hana"  # Thay chuỗi tìm kiếm
BASE_URL = "https://api.mangadex.org"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://mangadex.org/"
}
OUTPUT_FILE = "manga_mapped_data.json"
MAX_RETRIES = 5
MIN_DELAY = 0.25
LANG_PRIORITY = ["vi", "en"]

# -------------------------------
# Hàm tạo URL cho MangaLink theo tài liệu MangaDex
# -------------------------------
def create_manga_link_url(provider, value):
    link_formats = {
        "al": f"https://anilist.co/manga/{value}",  # Stored as id
        "ap": f"https://www.anime-planet.com/manga/{value}",  # Stored as slug
        "bw": f"https://bookwalker.jp/{value}",  # Stored as "series/"
        "mu": f"https://www.mangaupdates.com/series.html?id={value}",  # Stored as id
        "nu": f"https://www.novelupdates.com/series/{value}",  # Stored as slug
        "kt": f"https://kitsu.io/api/edge/manga/{value}" if value.isdigit() else f"https://kitsu.io/api/edge/manga?filter[slug]={value}",  # id or slug
        "amz": value,  # Full URL
        "ebj": value,  # Full URL
        "mal": f"https://myanimelist.net/manga/{value}",  # Stored as id
        "cdj": value,  # Full URL
        "raw": value,  # Full URL
        "engtl": value  # Full URL
    }
    return link_formats.get(provider, value)

# -------------------------------
# Utils
# -------------------------------
def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat()
    except Exception:
        return None

def request_api(endpoint, params=None):
    session = requests.Session()
    retries = Retry(total=MAX_RETRIES, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    try:
        logger.debug(f"Yêu cầu API: {endpoint} với params: {params}")
        time.sleep(MIN_DELAY)
        resp = session.get(BASE_URL + endpoint, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited. Chờ {retry_after} giây.")
            time.sleep(retry_after)
            return request_api(endpoint, params)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi yêu cầu API {endpoint}: {e}")
        raise
    finally:
        session.close()

# -------------------------------
# Search manga
# -------------------------------
def search_manga(title):
    logger.info(f"Bắt đầu tìm kiếm manga với tiêu đề: {title}")
    params = {
        "title": title,
        "limit": 5,
        "includes[]": ["cover_art", "author", "artist"]
    }
    data = request_api("/manga", params=params)
    mangas = data.get("data", [])
    logger.info(f"Tìm thấy {len(mangas)} manga.")
    return mangas

# -------------------------------
# Fetch statistics
# -------------------------------
def fetch_statistics(manga_ids):
    logger.info(f"Lấy thống kê cho {len(manga_ids)} manga.")
    stats = {}
    batch_size = 100
    for i in range(0, len(manga_ids), batch_size):
        ids = [str(mid) for mid in manga_ids[i:i+batch_size]]
        logger.debug(f"Lấy thống kê cho batch: {ids}")
        params = [("manga[]", mid) for mid in ids]
        data = request_api("/statistics/manga", params=params)
        stats.update(data.get("statistics", {}))
    logger.info(f"Hoàn thành lấy thống kê.")
    return stats

# -------------------------------
# Fetch chapters
# -------------------------------
def fetch_chapters(manga_id):
    logger.info(f"Lấy danh sách chương cho manga ID: {manga_id}")
    chapters = []
    offset = 0
    while True:
        params = {
            "limit": 100,
            "offset": offset,
            "translatedLanguage[]": LANG_PRIORITY,
            "manga": manga_id,
            "order[chapter]": "desc"
        }
        data = request_api("/chapter", params=params)
        chaps = data.get("data", [])
        if not chaps:
            break
        logger.debug(f"Tìm thấy {len(chaps)} chương tại offset {offset}.")
        for chap in chaps:
            attr = chap.get("attributes", {})
            chapters.append({
                "ChapterId": chap.get("id"),
                "MangaId": manga_id,
                "Type": "chapter" if attr.get("chapter") else "oneshot",
                "Volume": attr.get("volume"),
                "ChapterNumber": attr.get("chapter"),
                "Title": attr.get("title"),
                "TranslatedLang": attr.get("translatedLanguage"),
                "Pages": attr.get("pages"),
                "PublishAt": parse_dt(attr.get("publishAt")),
                "ReadableAt": parse_dt(attr.get("readableAt")),
                "IsUnavailable": attr.get("isUnavailable", False),
                "CreatedAt": parse_dt(attr.get("createdAt")),
                "UpdatedAt": parse_dt(attr.get("updatedAt"))
            })
        offset += 100
    logger.info(f"Tổng cộng lấy được {len(chapters)} chương cho manga ID: {manga_id}")
    return chapters

# -------------------------------
# Fetch related manga (parse from existing manga data)
# -------------------------------
def fetch_related(manga_id, manga_data):
    logger.info(f"Lấy manga liên quan cho manga ID: {manga_id}")
    related = []
    for rel in manga_data.get("relationships", []):
        if rel["type"] == "manga":
            logger.debug(f"Đã tìm thấy manga liên quan: {rel['id']}")
            related.append({
                "MangaId": manga_id,
                "RelatedId": rel["id"],
                "Type": rel.get("attributes", {}).get("relation", "unknown"),
                "Related": rel.get("attributes", {}).get("relation", "unknown"),
                "FetchedAt": parse_dt(datetime.datetime.now().isoformat())
            })
    logger.info(f"Tìm thấy {len(related)} manga liên quan.")
    return related

# -------------------------------
# Fetch full creator details
# -------------------------------
def fetch_creator(creator_id):
    logger.info(f"Lấy thông tin creator ID: {creator_id}")
    data = request_api(f"/author/{creator_id}")
    attr = data.get("data", {}).get("attributes", {})
    creator_data = {
        "CreatorId": creator_id,
        "Type": None,  # Sẽ được gán trong map_manga_to_db
        "Name": attr.get("name", "Unknown"),
        "ImageUrl": attr.get("imageUrl"),
        "BiographyEn": attr.get("biography", {}).get("en"),
        "BiographyJa": attr.get("biography", {}).get("ja"),
        "BiographyPtBr": attr.get("biography", {}).get("pt-br"),
        "CreatedAt": parse_dt(attr.get("createdAt")),
        "UpdatedAt": parse_dt(attr.get("updatedAt"))
    }
    logger.debug(f"Hoàn thành lấy thông tin creator: {creator_data['Name']}")
    return creator_data

# -------------------------------
# Fetch full cover details
# -------------------------------
def fetch_cover(cover_id):
    logger.info(f"Lấy thông tin cover ID: {cover_id}")
    data = request_api(f"/cover/{cover_id}")
    attr = data.get("data", {}).get("attributes", {})
    rel_user_id = None
    for rel in data.get("data", {}).get("relationships", []):
        if rel["type"] == "user":
            rel_user_id = rel["id"]
            break
    cover_data = {
        "cover_id": cover_id,
        "type": "cover_art",
        "description": attr.get("description"),
        "volume": attr.get("volume"),
        "fileName": attr.get("fileName"),
        "locale": attr.get("locale"),
        "createdAt": parse_dt(attr.get("createdAt")),
        "updatedAt": parse_dt(attr.get("updatedAt")),
        "version": attr.get("version"),
        "rel_user_id": rel_user_id
    }
    logger.debug(f"Hoàn thành lấy thông tin cover: {cover_data['fileName']}")
    return cover_data, data

# -------------------------------
# Map manga to DB structures
# -------------------------------
def map_manga_to_db(manga, stats_dict):
    logger.info(f"Bắt đầu mapping manga ID: {manga.get('id')}")
    attr = manga.get("attributes", {})
    manga_id = manga.get("id")

    # Manga table
    manga_db = {
        "MangaId": manga_id,
        "Type": manga.get("type"),
        "TitleEn": attr.get("title", {}).get("en") or list(attr.get("title", {}).values())[0] if attr.get("title") else "Unknown",
        "ChapterNumbersResetOnNewVolume": attr.get("chapterNumbersResetOnNewVolume", False),
        "ContentRating": attr.get("contentRating"),
        "CreatedAt": parse_dt(attr.get("createdAt")),
        "UpdatedAt": parse_dt(attr.get("updatedAt")),
        "IsLocked": attr.get("isLocked", False),
        "LastChapter": attr.get("lastChapter"),
        "LastVolume": attr.get("lastVolume"),
        "LatestUploadedChapter": attr.get("latestUploadedChapter"),
        "OriginalLanguage": attr.get("originalLanguage"),
        "PublicationDemographic": attr.get("publicationDemographic"),
        "State": attr.get("state"),
        "Status": attr.get("status"),
        "Year": attr.get("year"),
        "OfficialLinks": json.dumps(attr.get("links", {})) if attr.get("links") else None
    }
    logger.debug(f"Đã mapping Manga: {manga_db['TitleEn']}")

    # MangaAltTitle: list of dicts
    alt_titles = [{"MangaId": manga_id, "LangCode": lang, "AltTitle": title} for alt in attr.get("altTitles", []) for lang, title in alt.items()]
    logger.debug(f"Đã mapping {len(alt_titles)} tiêu đề thay thế.")

    # MangaDescription: list of dicts
    descriptions = [{"MangaId": manga_id, "LangCode": lang, "Description": desc} for lang, desc in attr.get("description", {}).items()]
    logger.debug(f"Đã mapping {len(descriptions)} mô tả.")

    # MangaAvailableLanguage: list of dicts
    available_languages = [{"MangaId": manga_id, "LangCode": lang} for lang in attr.get("availableTranslatedLanguages", [])]
    logger.debug(f"Đã mapping {len(available_languages)} ngôn ngữ có sẵn.")

    # MangaLink: list of dicts from official links
    links = [{"MangaId": manga_id, "Provider": provider, "Url": create_manga_link_url(provider, url)} for provider, url in attr.get("links", {}).items()]
    logger.debug(f"Đã mapping {len(links)} liên kết.")

    # MangaRelated: from fetch_related
    related = fetch_related(manga_id, manga)

    # MangaStatistics: dict (one per manga)
    stat = stats_dict.get(manga_id, {})
    rating = stat.get("rating", {})
    statistics_db = {
        "StatisticId": str(uuid.uuid4()),
        "MangaId": manga_id,
        "Source": "Mangadex",
        "Follows": stat.get("follows"),
        "AverageRating": rating.get("average"),
        "BayesianRating": rating.get("bayesian"),
        "UnavailableChapters": stat.get("unavailableChaptersCount", 0),
        "FetchedAt": parse_dt(datetime.datetime.now().isoformat())
    }
    logger.debug(f"Đã mapping thống kê: Follows={statistics_db['Follows']}")

    # MangaTag: list of dicts (không thêm vào Tag vì đã fix cứng)
    manga_tags = [{"MangaId": manga_id, "TagId": t["id"]} for t in attr.get("tags", [])]
    logger.debug(f"Đã mapping {len(manga_tags)} liên kết MangaTag.")

    # Chapter: from fetch_chapters
    chapters = fetch_chapters(manga_id)

    # Chỉ Covers
    covers_db = []  # for Covers
    creators_db = []  # for Creator
    creator_rels = []  # for CreatorRelationship
    creator_ids = set()
    for rel in manga.get("relationships", []):
        rtype = rel.get("type")
        rid = rel.get("id")
        if rtype in ["author", "artist"]:
            if rid not in creator_ids:
                creator_full = fetch_creator(rid)
                creator_full["Type"] = rtype
                creators_db.append(creator_full)
                creator_ids.add(rid)
            creator_rels.append({
                "CreatorId": rid,
                "RelatedId": manga_id,
                "RelatedType": "manga"
            })
        elif rtype == "cover_art":
            cover_full, cover_data = fetch_cover(rid)
            filename = cover_full.get("fileName")
            if filename:
                url = f"https://uploads.mangadex.org/covers/{manga_id}/{filename}"
                cover_entry = {
                    "cover_id": str(rid),
                    "manga_id": manga_id,
                    "type": cover_full["type"],
                    "description": cover_full["description"],
                    "volume": cover_full["volume"],
                    "fileName": filename,
                    "locale": cover_full["locale"],
                    "createdAt": cover_full["createdAt"],
                    "updatedAt": cover_full["updatedAt"],
                    "version": cover_full["version"],
                    "rel_user_id": cover_full["rel_user_id"],
                    "url": url,
                    "image_data": None  # Để download: requests.get(url).content
                }
                covers_db.append(cover_entry)
    logger.debug(f"Đã mapping {len(covers_db)} cover, {len(creators_db)} creator.")

    logger.info(f"Hoàn thành mapping manga ID: {manga_id}")
    return {
        "Manga": [manga_db],
        "MangaAltTitle": alt_titles,
        "MangaDescription": descriptions,
        "MangaAvailableLanguage": available_languages,
        "MangaLink": links,
        "MangaRelated": related,
        "MangaStatistics": [statistics_db],
        "MangaTag": manga_tags,
        "Chapter": chapters,
        "Covers": covers_db,
        "Creator": creators_db,
        "CreatorRelationship": creator_rels
    }

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    try:
        logger.info("Bắt đầu chạy script.")
        mangas = search_manga(search_title)

        manga_ids = [m.get("id") for m in mangas]
        stats_dict = fetch_statistics(manga_ids)

        all_db_data = {
            "Manga": [], "MangaAltTitle": [], "MangaDescription": [],
            "MangaAvailableLanguage": [], "MangaLink": [], "MangaRelated": [],
            "MangaStatistics": [], "MangaTag": [], "Chapter": [],
            "Covers": [], "Creator": [], "CreatorRelationship": []
        }

        for idx, m in enumerate(mangas, 1):
            logger.info(f"Xử lý manga {idx}/{len(mangas)}: ID {m.get('id')}")
            db_data = map_manga_to_db(m, stats_dict)
            for key in all_db_data:
                all_db_data[key].extend(db_data.get(key, []))
            logger.info(f"Hoàn thành xử lý manga {idx}/{len(mangas)}.")

        # Deduplicate Creators and Covers
        logger.info("Deduplicate dữ liệu.")
        all_db_data["Creator"] = list({c["CreatorId"]: c for c in all_db_data["Creator"]}.values())
        all_db_data["Covers"] = list({c["cover_id"]: c for c in all_db_data["Covers"]}.values())
        logger.debug(f"Số lượng sau deduplicate: Creators={len(all_db_data['Creator'])}, Covers={len(all_db_data['Covers'])}")

        # Ghi ra file JSON
        logger.info(f"Ghi dữ liệu ra file: {OUTPUT_FILE}")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_db_data, f, ensure_ascii=False, indent=4)

        logger.info(f"Hoàn thành! Dữ liệu đã được ghi vào file: {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Lỗi khi chạy script: {e}")