from pymongo import MongoClient
import argparse

# ======================
# 1. KẾT NỐI MONGODB
# ======================
client = MongoClient("mongodb://localhost:27017/")
db = client["manga_raw_data"]

col_manga = db["mangadex_manga"]
col_anilist = db["anilist_data"]
col_mal = db["mal_data"]
col_mu = db["mangaupdates_data"]

# ======================
# 2. HÀM LẤY TÊN MANGA
# ======================
def get_manga_title(m):
    title_dict = m.get("attributes", {}).get("title", {}) or {}
    alt_titles = m.get("attributes", {}).get("altTitles", []) or []
    mid = m.get("id") or str(m.get("_id"))

    for key in ["en", "ja-ro", "ja", "zh", "it"]:
        if title_dict.get(key):
            return title_dict[key]

    for alt in alt_titles:
        if "en" in alt:
            return alt["en"]
        if alt:
            return next(iter(alt.values()))

    return mid

# ======================
# 3. BUILD ID MAP
# ======================
def build_id_map():
    id_map = {}
    for m in col_manga.find({}):
        mid = m.get("id") or str(m.get("_id"))
        links = m.get("attributes", {}).get("links", {}) or {}

        if "mal" in links:
            id_map[f"mal:{links['mal']}"] = mid
        if "al" in links:
            id_map[f"al:{links['al']}"] = mid
        if "mu" in links:
            id_map[f"mu:{links['mu']}"] = mid
        if "ap" in links:
            id_map[f"ap:{links['ap']}"] = mid
    return id_map

# ======================
# 4. LẤY CÁC RECOMMENDATIONS LIÊN QUAN
# ======================
def get_related_manga(target_uuid, id_map, source="all"):
    related_ids = set()

    # MAL
    if source in ("mal", "all"):
        for doc in col_mal.find({}):
            src = id_map.get(f"mal:{doc.get('manga_id')}")
            if src == target_uuid:
                for r in doc.get("recommendations", []):
                    tgt = id_map.get(f"mal:{r['entry']['mal_id']}")
                    if tgt:
                        related_ids.add(tgt)

    # AniList
    if source in ("anilist", "all"):
        for doc in col_anilist.find({}):
            src = id_map.get(f"al:{doc.get('source_id')}")
            if src == target_uuid:
                for r in doc.get("recommendations", []):
                    tgt = id_map.get(f"al:{r['id']}")
                    if tgt:
                        related_ids.add(tgt)

    # MangaUpdates
    if source in ("mu", "all"):
        for doc in col_mu.find({}):
            src = id_map.get(f"mu:{doc.get('source_id')}")
            if src == target_uuid:
                for r in doc.get("recommendations", []):
                    tgt = id_map.get(f"mu:{r['id']}")
                    if tgt:
                        related_ids.add(tgt)

    return list(related_ids)

# ======================
# 5. MAIN
# ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find related manga for a given MangaDex UUID")
    parser.add_argument("uuid", type=str, help="UUID of the manga (MangaDex id)")
    parser.add_argument("--source", type=str, default="all", choices=["mal", "anilist", "mu", "all"],
                        help="Which source to use for recommendations")
    args = parser.parse_args()

    id_map = build_id_map()
    related = get_related_manga(args.uuid, id_map, source=args.source)

    if not related:
        print(f"Không tìm thấy manga liên quan cho uuid={args.uuid} (source={args.source})")
    else:
        print(f"Các manga liên quan đến {args.uuid} (source={args.source}):")
        for rid in related:
            m = col_manga.find_one({"id": rid})
            title = get_manga_title(m) if m else "Unknown"
            print(f"- {rid} | {title}")
