from flask import config
import pyodbc
import requests
import json
import datetime
import time
import uuid
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from config import Config

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("manga_db_update.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Thông số
BASE_URL = "https://api.mangadex.org"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://mangadex.org/"
}
MAX_RETRIES = 5
MIN_DELAY = 0.25
LANG_PRIORITY = ["vi", "en"]

# Kết nối DB
def connect_db():
    logger.info("Khởi tạo kết nối đến cơ sở dữ liệu.")
    try:
        conn = pyodbc.connect(Config.SQLALCHEMY_DATABASE_URI.split('mssql+pyodbc:///?odbc_connect=')[1])
        logger.info("Đã kết nối đến cơ sở dữ liệu.")
        return conn
    except pyodbc.Error as e:
        logger.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        raise 

# Hàm gọi API
def request_api(endpoint, params=None):
    logger.debug(f"Yêu cầu API: {BASE_URL + endpoint} với params: {params}")
    session = requests.Session()
    retries = Retry(total=MAX_RETRIES, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    try:
        time.sleep(MIN_DELAY)
        resp = session.get(BASE_URL + endpoint, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited. Chờ {retry_after} giây.")
            time.sleep(retry_after)
            return request_api(endpoint, params)
        resp.raise_for_status()
        logger.debug(f"Yêu cầu API thành công: {endpoint}")
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi yêu cầu API {endpoint}: {e}")
        raise
    finally:
        session.close()
        logger.debug("Đã đóng session API.")

# Hàm parse datetime
def parse_dt(s):
    logger.debug(f"Phân tích datetime: {s}")
    if not s:
        return None
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        logger.debug(f"Đã phân tích datetime thành: {dt}")
        return dt
    except Exception as e:
        logger.error(f"Lỗi phân tích datetime {s}: {e}")
        return None

# Hàm tạo URL cho MangaLink
def create_manga_link_url(provider, value):
    logger.debug(f"Tạo URL cho provider: {provider}, value: {value}")
    link_formats = {
        "al": f"https://anilist.co/manga/{value}",
        "ap": f"https://www.anime-planet.com/manga/{value}",
        "bw": f"https://bookwalker.jp/{value}",
        "mu": f"https://www.mangaupdates.com/series.html?id={value}",
        "nu": f"https://www.novelupdates.com/series/{value}",
        "kt": f"https://kitsu.io/api/edge/manga/{value}" if value.isdigit() else f"https://kitsu.io/api/edge/manga?filter[slug]={value}",
        "amz": value,
        "ebj": value,
        "mal": f"https://myanimelist.net/manga/{value}",
        "cdj": value,
        "raw": value,
        "engtl": value
    }
    url = link_formats.get(provider, value)
    logger.debug(f"URL được tạo: {url}")
    return url

# Hàm upsert các bảng
def upsert_manga(conn, manga_list):
    cursor = conn.cursor()
    for manga in manga_list:
        manga_id_upper = str(manga['MangaId']).upper()
        logger.info(f"Xử lý upsert manga ID: {manga_id_upper}")
        try:
            cursor.execute("""
                MERGE INTO [dbo].[Manga] AS target
                USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) 
                AS source (MangaId, Type, TitleEn, ChapterNumbersResetOnNewVolume, ContentRating, CreatedAt, UpdatedAt, IsLocked, LastChapter, LastVolume, LatestUploadedChapter, OriginalLanguage, PublicationDemographic, State, Status, Year, OfficialLinks)
                ON target.MangaId = source.MangaId
                WHEN MATCHED AND (
                    target.Type != source.Type OR
                    target.TitleEn != source.TitleEn OR
                    target.ChapterNumbersResetOnNewVolume != source.ChapterNumbersResetOnNewVolume OR
                    target.ContentRating != source.ContentRating OR
                    target.CreatedAt != source.CreatedAt OR
                    target.UpdatedAt != source.UpdatedAt OR
                    target.IsLocked != source.IsLocked OR
                    target.LastChapter != source.LastChapter OR
                    target.LastVolume != source.LastVolume OR
                    target.LatestUploadedChapter != source.LatestUploadedChapter OR
                    target.OriginalLanguage != source.OriginalLanguage OR
                    target.PublicationDemographic != source.PublicationDemographic OR
                    target.State != source.State OR
                    target.Status != source.Status OR
                    target.Year != source.Year OR
                    target.OfficialLinks != source.OfficialLinks
                ) THEN
                    UPDATE SET 
                        Type = source.Type,
                        TitleEn = source.TitleEn,
                        ChapterNumbersResetOnNewVolume = source.ChapterNumbersResetOnNewVolume,
                        ContentRating = source.ContentRating,
                        CreatedAt = source.CreatedAt,
                        UpdatedAt = source.UpdatedAt,
                        IsLocked = source.IsLocked,
                        LastChapter = source.LastChapter,
                        LastVolume = source.LastVolume,
                        LatestUploadedChapter = source.LatestUploadedChapter,
                        OriginalLanguage = source.OriginalLanguage,
                        PublicationDemographic = source.PublicationDemographic,
                        State = source.State,
                        Status = source.Status,
                        Year = source.Year,
                        OfficialLinks = source.OfficialLinks
                WHEN NOT MATCHED THEN
                    INSERT (MangaId, Type, TitleEn, ChapterNumbersResetOnNewVolume, ContentRating, CreatedAt, UpdatedAt, IsLocked, LastChapter, LastVolume, LatestUploadedChapter, OriginalLanguage, PublicationDemographic, State, Status, Year, OfficialLinks)
                    VALUES (source.MangaId, source.Type, source.TitleEn, source.ChapterNumbersResetOnNewVolume, source.ContentRating, source.CreatedAt, source.UpdatedAt, source.IsLocked, source.LastChapter, source.LastVolume, source.LatestUploadedChapter, source.OriginalLanguage, source.PublicationDemographic, source.State, source.Status, source.Year, source.OfficialLinks);
            """, (
                manga_id_upper, manga['Type'], manga['TitleEn'], manga['ChapterNumbersResetOnNewVolume'],
                manga['ContentRating'], manga['CreatedAt'], manga['UpdatedAt'], manga['IsLocked'],
                manga['LastChapter'], manga['LastVolume'], manga['LatestUploadedChapter'], manga['OriginalLanguage'],
                manga['PublicationDemographic'], manga['State'], manga['Status'], manga['Year'], manga['OfficialLinks']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert Manga: {manga['TitleEn']}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert Manga ID {manga_id_upper}: {e}")
            raise

def upsert_manga_alt_title(conn, alt_titles):
    cursor = conn.cursor()
    for alt in alt_titles:
        manga_id_upper = str(alt['MangaId']).upper()
        logger.info(f"Xử lý upsert MangaAltTitle cho MangaId: {manga_id_upper}")
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM [dbo].[MangaAltTitle] WHERE MangaId = ? AND LangCode = ?)
                INSERT INTO [dbo].[MangaAltTitle] (MangaId, LangCode, AltTitle)
                VALUES (?, ?, ?)
            """, (
                manga_id_upper, alt['LangCode'], alt['AltTitle'],
                manga_id_upper, alt['LangCode'], alt['AltTitle']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert MangaAltTitle cho MangaId: {manga_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert MangaAltTitle cho MangaId {manga_id_upper}: {e}")
            raise

def upsert_manga_description(conn, descriptions):
    cursor = conn.cursor()
    for desc in descriptions:
        manga_id_upper = str(desc['MangaId']).upper()
        logger.info(f"Xử lý upsert MangaDescription cho MangaId: {manga_id_upper}")
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM [dbo].[MangaDescription] WHERE MangaId = ? AND LangCode = ?)
                INSERT INTO [dbo].[MangaDescription] (MangaId, LangCode, Description)
                VALUES (?, ?, ?)
            """, (
                manga_id_upper, desc['LangCode'], desc['Description'],
                manga_id_upper, desc['LangCode'], desc['Description']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert MangaDescription cho MangaId: {manga_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert MangaDescription cho MangaId {manga_id_upper}: {e}")
            raise

def upsert_manga_available_language(conn, languages):
    cursor = conn.cursor()
    for lang in languages:
        manga_id_upper = str(lang['MangaId']).upper()
        logger.info(f"Xử lý upsert MangaAvailableLanguage cho MangaId: {manga_id_upper}")
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM [dbo].[MangaAvailableLanguage] WHERE MangaId = ? AND LangCode = ?)
                INSERT INTO [dbo].[MangaAvailableLanguage] (MangaId, LangCode)
                VALUES (?, ?)
            """, (
                manga_id_upper, lang['LangCode'],
                manga_id_upper, lang['LangCode']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert MangaAvailableLanguage cho MangaId: {manga_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert MangaAvailableLanguage cho MangaId {manga_id_upper}: {e}")
            raise

def upsert_manga_link(conn, links):
    cursor = conn.cursor()
    for link in links:
        manga_id_upper = str(link['MangaId']).upper()
        logger.info(f"Xử lý upsert MangaLink cho MangaId: {manga_id_upper}")
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM [dbo].[MangaLink] WHERE MangaId = ? AND Provider = ?)
                INSERT INTO [dbo].[MangaLink] (MangaId, Provider, Url)
                VALUES (?, ?, ?)
            """, (
                manga_id_upper, link['Provider'], link['Url'],
                manga_id_upper, link['Provider'], link['Url']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert MangaLink cho MangaId: {manga_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert MangaLink cho MangaId {manga_id_upper}: {e}")
            raise

def upsert_manga_statistics(conn, statistics):
    cursor = conn.cursor()
    for stat in statistics:
        statistic_id_upper = str(stat['StatisticId']).upper()
        manga_id_upper = str(stat['MangaId']).upper()
        logger.info(f"Xử lý upsert MangaStatistics cho MangaId: {manga_id_upper}")
        try:
            cursor.execute("""
                MERGE INTO [dbo].[MangaStatistics] AS target
                USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?)) 
                AS source (StatisticId, MangaId, Source, Follows, AverageRating, BayesianRating, UnavailableChapters, FetchedAt)
                ON target.StatisticId = source.StatisticId
                WHEN MATCHED AND (
                    target.MangaId != source.MangaId OR
                    target.Source != source.Source OR
                    target.Follows != source.Follows OR
                    target.AverageRating != source.AverageRating OR
                    target.BayesianRating != source.BayesianRating OR
                    target.UnavailableChapters != source.UnavailableChapters OR
                    target.FetchedAt != source.FetchedAt
                ) THEN
                    UPDATE SET 
                        MangaId = source.MangaId,
                        Source = source.Source,
                        Follows = source.Follows,
                        AverageRating = source.AverageRating,
                        BayesianRating = source.BayesianRating,
                        UnavailableChapters = source.UnavailableChapters,
                        FetchedAt = source.FetchedAt
                WHEN NOT MATCHED THEN
                    INSERT (StatisticId, MangaId, Source, Follows, AverageRating, BayesianRating, UnavailableChapters, FetchedAt)
                    VALUES (source.StatisticId, source.MangaId, source.Source, source.Follows, source.AverageRating, source.BayesianRating, source.UnavailableChapters, source.FetchedAt);
            """, (
                statistic_id_upper, manga_id_upper, stat['Source'], stat['Follows'], stat['AverageRating'],
                stat['BayesianRating'], stat['UnavailableChapters'], stat['FetchedAt']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert MangaStatistics cho MangaId: {manga_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert MangaStatistics cho MangaId {manga_id_upper}: {e}")
            raise

def upsert_manga_tag(conn, manga_tags):
    cursor = conn.cursor()
    for tag in manga_tags:
        manga_id_upper = str(tag['MangaId']).upper()
        tag_id_upper = str(tag['TagId']).upper()
        logger.info(f"Xử lý upsert MangaTag cho MangaId: {manga_id_upper}, TagId: {tag_id_upper}")
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM [dbo].[MangaTag] WHERE MangaId = ? AND TagId = ?)
                INSERT INTO [dbo].[MangaTag] (MangaId, TagId)
                VALUES (?, ?)
            """, (
                manga_id_upper, tag_id_upper,
                manga_id_upper, tag_id_upper
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert MangaTag cho MangaId: {manga_id_upper}, TagId: {tag_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert MangaTag cho MangaId {manga_id_upper}, TagId {tag_id_upper}: {e}")
            raise

def upsert_chapter(conn, chapters):
    cursor = conn.cursor()
    for chapter in chapters:
        chapter_id_upper = str(chapter['ChapterId']).upper()
        manga_id_upper = str(chapter['MangaId']).upper()
        logger.info(f"Xử lý upsert Chapter cho ChapterId: {chapter_id_upper}")
        try:
            cursor.execute("""
                MERGE INTO [dbo].[Chapter] AS target
                USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) 
                AS source (ChapterId, MangaId, Type, Volume, ChapterNumber, Title, TranslatedLang, Pages, PublishAt, ReadableAt, IsUnavailable, CreatedAt, UpdatedAt)
                ON target.ChapterId = source.ChapterId
                WHEN MATCHED AND (
                    target.Type != source.Type OR
                    target.Volume != source.Volume OR
                    target.ChapterNumber != source.ChapterNumber OR
                    target.Title != source.Title OR
                    target.TranslatedLang != source.TranslatedLang OR
                    target.Pages != source.Pages OR
                    target.PublishAt != source.PublishAt OR
                    target.ReadableAt != source.ReadableAt OR
                    target.IsUnavailable != source.IsUnavailable OR
                    target.CreatedAt != source.CreatedAt OR
                    target.UpdatedAt != source.UpdatedAt
                ) THEN
                    UPDATE SET 
                        Type = source.Type,
                        Volume = source.Volume,
                        ChapterNumber = source.ChapterNumber,
                        Title = source.Title,
                        TranslatedLang = source.TranslatedLang,
                        Pages = source.Pages,
                        PublishAt = source.PublishAt,
                        ReadableAt = source.ReadableAt,
                        IsUnavailable = source.IsUnavailable,
                        CreatedAt = source.CreatedAt,
                        UpdatedAt = source.UpdatedAt
                WHEN NOT MATCHED THEN
                    INSERT (ChapterId, MangaId, Type, Volume, ChapterNumber, Title, TranslatedLang, Pages, PublishAt, ReadableAt, IsUnavailable, CreatedAt, UpdatedAt)
                    VALUES (source.ChapterId, source.MangaId, source.Type, source.Volume, source.ChapterNumber, source.Title, source.TranslatedLang, source.Pages, source.PublishAt, source.ReadableAt, source.IsUnavailable, source.CreatedAt, source.UpdatedAt);
            """, (
                chapter_id_upper, manga_id_upper, chapter['Type'], chapter['Volume'], chapter['ChapterNumber'],
                chapter['Title'], chapter['TranslatedLang'], chapter['Pages'], chapter['PublishAt'], chapter['ReadableAt'],
                chapter['IsUnavailable'], chapter['CreatedAt'], chapter['UpdatedAt']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert Chapter cho ChapterId: {chapter_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert Chapter cho ChapterId {chapter_id_upper}: {e}")
            raise

def upsert_covers(conn, covers):
    cursor = conn.cursor()
    for cover in covers:
        cover_id_upper = str(cover['cover_id']).upper()
        manga_id_upper = str(cover['manga_id']).upper()
        logger.info(f"Xử lý upsert Covers cho cover_id: {cover_id_upper}")
        try:
            cursor.execute("""
                MERGE INTO [dbo].[Covers] AS target
                USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) 
                AS source (cover_id, manga_id, type, description, volume, fileName, locale, createdAt, updatedAt, version, rel_user_id, url, image_data)
                ON target.cover_id = source.cover_id
                WHEN MATCHED AND (
                    target.manga_id != source.manga_id OR
                    target.type != source.type OR
                    target.description != source.description OR
                    target.volume != source.volume OR
                    target.fileName != source.fileName OR
                    target.locale != source.locale OR
                    target.createdAt != source.createdAt OR
                    target.updatedAt != source.updatedAt OR
                    target.version != source.version OR
                    target.rel_user_id != source.rel_user_id OR
                    target.url != source.url OR
                    (target.image_data IS NULL AND source.image_data IS NOT NULL)
                ) THEN
                    UPDATE SET 
                        manga_id = source.manga_id,
                        type = source.type,
                        description = source.description,
                        volume = source.volume,
                        fileName = source.fileName,
                        locale = source.locale,
                        createdAt = source.createdAt,
                        updatedAt = source.updatedAt,
                        version = source.version,
                        rel_user_id = source.rel_user_id,
                        url = source.url,
                        image_data = source.image_data
                WHEN NOT MATCHED THEN
                    INSERT (cover_id, manga_id, type, description, volume, fileName, locale, createdAt, updatedAt, version, rel_user_id, url, image_data)
                    VALUES (source.cover_id, source.manga_id, source.type, source.description, source.volume, source.fileName, source.locale, source.createdAt, source.updatedAt, source.version, source.rel_user_id, source.url, source.image_data);
            """, (
                cover_id_upper, manga_id_upper, cover['type'], cover['description'], cover['volume'],
                cover['fileName'], cover['locale'], cover['createdAt'], cover['updatedAt'], cover['version'],
                cover['rel_user_id'] if cover['rel_user_id'] else None, cover['url'], cover['image_data']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert Covers cho cover_id: {cover_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert Covers cho cover_id {cover_id_upper}: {e}")
            raise

def upsert_creator(conn, creators):
    cursor = conn.cursor()
    for creator in creators:
        creator_id_upper = str(creator['CreatorId']).upper()
        logger.info(f"Xử lý upsert Creator cho CreatorId: {creator_id_upper}")
        try:
            cursor.execute("""
                MERGE INTO [dbo].[Creator] AS target
                USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)) 
                AS source (CreatorId, Type, Name, ImageUrl, BiographyEn, BiographyJa, BiographyPtBr, CreatedAt, UpdatedAt)
                ON target.CreatorId = source.CreatorId
                WHEN MATCHED AND (
                    target.Type != source.Type OR
                    target.Name != source.Name OR
                    target.ImageUrl != source.ImageUrl OR
                    target.BiographyEn != source.BiographyEn OR
                    target.BiographyJa != source.BiographyJa OR
                    target.BiographyPtBr != source.BiographyPtBr OR
                    target.CreatedAt != source.CreatedAt OR
                    target.UpdatedAt != source.UpdatedAt
                ) THEN
                    UPDATE SET 
                        Type = source.Type,
                        Name = source.Name,
                        ImageUrl = source.ImageUrl,
                        BiographyEn = source.BiographyEn,
                        BiographyJa = source.BiographyJa,
                        BiographyPtBr = source.BiographyPtBr,
                        CreatedAt = source.CreatedAt,
                        UpdatedAt = source.UpdatedAt
                WHEN NOT MATCHED THEN
                    INSERT (CreatorId, Type, Name, ImageUrl, BiographyEn, BiographyJa, BiographyPtBr, CreatedAt, UpdatedAt)
                    VALUES (source.CreatorId, source.Type, source.Name, source.ImageUrl, source.BiographyEn, source.BiographyJa, source.BiographyPtBr, source.CreatedAt, source.UpdatedAt);
            """, (
                creator_id_upper, creator['Type'], creator['Name'], creator['ImageUrl'], creator['BiographyEn'],
                creator['BiographyJa'], creator['BiographyPtBr'], creator['CreatedAt'], creator['UpdatedAt']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert Creator cho CreatorId: {creator_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert Creator cho CreatorId {creator_id_upper}: {e}")
            raise

def upsert_creator_relationship(conn, relationships):
    cursor = conn.cursor()
    for rel in relationships:
        creator_id_upper = str(rel['CreatorId']).upper()
        related_id_upper = str(rel['RelatedId']).upper()
        logger.info(f"Xử lý upsert CreatorRelationship cho CreatorId: {creator_id_upper}, RelatedId: {related_id_upper}")
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM [dbo].[CreatorRelationship] WHERE CreatorId = ? AND RelatedId = ? AND RelatedType = ?)
                INSERT INTO [dbo].[CreatorRelationship] (CreatorId, RelatedId, RelatedType)
                VALUES (?, ?, ?)
            """, (
                creator_id_upper, related_id_upper, rel['RelatedType'],
                creator_id_upper, related_id_upper, rel['RelatedType']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert CreatorRelationship cho CreatorId: {creator_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert CreatorRelationship cho CreatorId {creator_id_upper}: {e}")
            raise

def upsert_manga_related(conn, related):
    cursor = conn.cursor()
    for rel in related:
        manga_id_upper = str(rel['MangaId']).upper()
        related_id_upper = str(rel['RelatedId']).upper()
        logger.info(f"Xử lý upsert MangaRelated cho MangaId: {manga_id_upper}, RelatedId: {related_id_upper}")
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM [dbo].[MangaRelated] WHERE MangaId = ? AND RelatedId = ? AND Type = ?)
                INSERT INTO [dbo].[MangaRelated] (MangaId, RelatedId, Type, Related, FetchedAt)
                VALUES (?, ?, ?, ?, ?)
            """, (
                manga_id_upper, related_id_upper, rel['Type'], rel['Related'], rel['FetchedAt'],
                manga_id_upper, related_id_upper, rel['Type'], rel['Related'], rel['FetchedAt']
            ))
            conn.commit()
            logger.debug(f"Hoàn thành upsert MangaRelated cho MangaId: {manga_id_upper}")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert MangaRelated cho MangaId {manga_id_upper}: {e}")
            raise

# Hàm fetch dữ liệu từ API
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

def fetch_statistics(manga_ids):
    logger.info(f"Lấy thống kê cho {len(manga_ids)} manga.")
    stats = {}
    batch_size = 100
    for i in range(0, len(manga_ids), batch_size):
        ids = [str(mid).upper() for mid in manga_ids[i:i+batch_size]]
        logger.debug(f"Lấy thống kê cho batch: {ids}")
        params = [("manga[]", mid.lower()) for mid in ids]
        data = request_api("/statistics/manga", params=params)
        stats.update(data.get("statistics", {}))
    logger.info(f"Hoàn thành lấy thống kê.")
    return stats

def fetch_chapters(manga_id):
    manga_id_upper = str(manga_id).upper()
    logger.info(f"Lấy danh sách chương cho manga ID: {manga_id_upper}")
    chapters = []
    offset = 0
    while True:
        params = {
            "limit": 100,
            "offset": offset,
            "translatedLanguage[]": LANG_PRIORITY,
            "manga": manga_id.lower(),
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
                "ChapterId": str(chap.get("id")).upper(),
                "MangaId": manga_id_upper,
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
    logger.info(f"Tổng cộng lấy được {len(chapters)} chương cho manga ID: {manga_id_upper}")
    return chapters

def fetch_covers(manga_id):
    manga_id_lower = str(manga_id).lower()
    manga_id_upper = str(manga_id).upper()
    logger.info(f"Lấy toàn bộ cover cho manga ID: {manga_id_upper}")
    covers = []
    offset = 0
    limit = 10
    while True:
        params = {
            "manga[]": manga_id_lower,
            "limit": limit,
            "offset": offset
        }
        try:
            data = request_api("/cover", params=params)
            cover_list = data.get("data", [])
            if not cover_list:
                break
            logger.debug(f"Tìm thấy {len(cover_list)} cover tại offset {offset}.")
            for cover in cover_list:
                cover_id_upper = str(cover.get("id")).upper()
                attr = cover.get("attributes", {})
                file_name = attr.get("fileName", "")
                if not file_name:
                    logger.warning(f"Không tìm thấy fileName cho cover ID: {cover_id_upper}")
                    continue
                cover_url = f"https://uploads.mangadex.org/covers/{manga_id_lower}/{file_name}"
                logger.debug(f"URL ảnh bìa: {cover_url}")
                image_data = None
                try:
                    session = requests.Session()
                    retries = Retry(total=7, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
                    session.mount('https://', HTTPAdapter(max_retries=retries))
                    time.sleep(MIN_DELAY)
                    resp = session.get(cover_url, headers=HEADERS, timeout=30)
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited khi tải ảnh bìa. Chờ {retry_after} giây.")
                        time.sleep(retry_after)
                        resp = session.get(cover_url, headers=HEADERS, timeout=30)
                    if resp.status_code == 404:
                        logger.warning(f"Ảnh bìa không tồn tại (404) cho cover ID: {cover_id_upper}")
                        continue
                    resp.raise_for_status()
                    content_type = resp.headers.get('Content-Type', '')
                    if content_type not in ['image/jpeg', 'image/png']:
                        logger.warning(f"Định dạng ảnh không hợp lệ cho cover ID: {cover_id_upper} ({content_type})")
                        continue
                    content_length = int(resp.headers.get('Content-Length', 0))
                    if content_length > 10 * 1024 * 1024:
                        logger.warning(f"Ảnh bìa quá lớn ({content_length} bytes) cho cover ID: {cover_id_upper}")
                        continue
                    image_data = resp.content
                    logger.info(f"Đã tải ảnh bìa cho cover ID: {cover_id_upper}, kích thước: {len(image_data)} bytes")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Lỗi khi tải ảnh bìa cho cover ID {cover_id_upper}: {e}")
                    continue
                finally:
                    session.close()
                    logger.debug("Đã đóng session tải ảnh.")
                rel_user_id = None
                for rel in cover.get("relationships", []):
                    if rel["type"] == "user":
                        rel_user_id = str(rel["id"]).upper()
                        break
                cover_data = {
                    "cover_id": cover_id_upper,
                    "manga_id": manga_id_upper,
                    "type": "cover_art",
                    "description": attr.get("description"),
                    "volume": attr.get("volume"),
                    "fileName": file_name,
                    "locale": attr.get("locale"),
                    "createdAt": parse_dt(attr.get("createdAt")),
                    "updatedAt": parse_dt(attr.get("updatedAt")),
                    "version": attr.get("version"),
                    "rel_user_id": rel_user_id,
                    "url": cover_url,
                    "image_data": image_data
                }
                covers.append(cover_data)
            offset += limit
            if offset >= data.get("total", 0):
                break
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi lấy danh sách cover cho manga ID {manga_id_upper}: {e}")
            break
    logger.info(f"Tổng cộng lấy được {len(covers)} cover cho manga ID: {manga_id_upper}")
    return covers

def fetch_creator(creator_id):
    creator_id_lower = str(creator_id).lower()
    creator_id_upper = str(creator_id).upper()
    logger.info(f"Lấy thông tin creator ID: {creator_id_upper}")
    data = request_api(f"/author/{creator_id_lower}")
    attr = data.get("data", {}).get("attributes", {})
    creator_data = {
        "CreatorId": creator_id_upper,
        "Type": None,
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

def fetch_related(manga_id, manga_data):
    manga_id_upper = str(manga_id).upper()
    logger.info(f"Lấy manga liên quan cho manga ID: {manga_id_upper}")
    related = []
    for rel in manga_data.get("relationships", []):
        if rel["type"] == "manga":
            logger.debug(f"Đã tìm thấy manga liên quan: {rel['id']}")
            related.append({
                "MangaId": manga_id_upper,
                "RelatedId": str(rel["id"]).upper(),
                "Type": rel.get("attributes", {}).get("relation", "unknown"),
                "Related": rel.get("attributes", {}).get("relation", "unknown"),
                "FetchedAt": parse_dt(datetime.datetime.now().isoformat())
            })
    logger.info(f"Tìm thấy {len(related)} manga liên quan.")
    return related

def fetch_and_upsert_tags(conn, tag_ids, manga_id):
    cursor = conn.cursor()
    for tag_id in tag_ids:
        tag_id_upper = str(tag_id).upper()
        logger.info(f"Xử lý tag ID: {tag_id_upper} cho manga ID: {manga_id}")
        try:
            cursor.execute("SELECT 1 FROM [dbo].[Tag] WHERE TagId = ?", (tag_id_upper,))
            if not cursor.fetchone():
                logger.debug(f"Gửi yêu cầu API để lấy thông tin tag ID: {tag_id_upper}")
                data = request_api(f"/manga/{manga_id}")
                tags = [t for t in data.get("data", {}).get("attributes", {}).get("tags", []) if t["id"] == tag_id]
                if not tags:
                    logger.warning(f"Không tìm thấy tag ID {tag_id_upper} trong dữ liệu manga.")
                    continue
                tag = tags[0]
                attr = tag.get("attributes", {})
                tag_data = {
                    "TagId": tag_id_upper,
                    "NameEn": attr.get("name", {}).get("en", "Unknown"),
                    "GroupName": attr.get("group", "unknown")
                }
                cursor.execute("""
                    MERGE INTO [dbo].[Tag] AS target
                    USING (VALUES (?, ?, ?))
                    AS source (TagId, NameEn, GroupName)
                    ON target.TagId = source.TagId
                    WHEN MATCHED AND (
                        target.NameEn != source.NameEn OR
                        target.GroupName != source.GroupName
                    ) THEN
                        UPDATE SET
                            NameEn = source.NameEn,
                            GroupName = source.GroupName
                    WHEN NOT MATCHED THEN
                        INSERT (TagId, NameEn, GroupName)
                        VALUES (source.TagId, source.NameEn, source.GroupName);
                """, (
                    tag_data['TagId'], tag_data['NameEn'], tag_data['GroupName']
                ))
                conn.commit()
                logger.info(f"Đã upsert tag: {tag_data['NameEn']} (ID: {tag_id_upper})")
        except pyodbc.Error as e:
            conn.rollback()
            logger.error(f"Lỗi upsert tag ID {tag_id_upper} cho manga ID {manga_id}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi lấy thông tin tag ID {tag_id_upper}: {e}")

# Hàm chính để map và upsert manga
def map_manga_to_db(manga, stats_dict, conn):
    manga_id = manga.get("id")
    manga_id_upper = str(manga_id).upper()
    logger.info(f"Bắt đầu mapping và upsert manga ID: {manga_id_upper}")
    attr = manga.get("attributes", {})
    
    # Manga table
    manga_db = {
        "MangaId": manga_id_upper,
        "Type": manga.get("type"),
        "TitleEn": attr.get("title", {}).get("en") or list(attr.get("title", {}).values())[0] if attr.get("title") else "Unknown",
        "ChapterNumbersResetOnNewVolume": attr.get("chapterNumbersResetOnNewVolume", False),
        "ContentRating": attr.get("contentRating"),
        "CreatedAt": parse_dt(attr.get("createdAt")),
        "UpdatedAt": parse_dt(attr.get("updatedAt")),
        "IsLocked": attr.get("isLocked", False),
        "LastChapter": attr.get("lastChapter"),
        "LastVolume": attr.get("lastVolume"),
        "LatestUploadedChapter": str(attr.get("latestUploadedChapter", "")).upper() if attr.get("latestUploadedChapter") else None,
        "OriginalLanguage": attr.get("originalLanguage"),
        "PublicationDemographic": attr.get("publicationDemographic"),
        "State": attr.get("state"),
        "Status": attr.get("status"),
        "Year": attr.get("year"),
        "OfficialLinks": json.dumps(attr.get("links", {})) if attr.get("links") else None
    }
    upsert_manga(conn, [manga_db])
    manga_id = manga.get("id")
    manga_id_upper = str(manga_id).upper()
    logger.info(f"Bắt đầu mapping và upsert manga ID: {manga_id_upper}")
    attr = manga.get("attributes", {})

    # Manga table
    manga_db = {
        "MangaId": manga_id_upper,
        "Type": manga.get("type"),
        "TitleEn": attr.get("title", {}).get("en") or list(attr.get("title", {}).values())[0] if attr.get("title") else "Unknown",
        "ChapterNumbersResetOnNewVolume": attr.get("chapterNumbersResetOnNewVolume", False),
        "ContentRating": attr.get("contentRating"),
        "CreatedAt": parse_dt(attr.get("createdAt")),
        "UpdatedAt": parse_dt(attr.get("updatedAt")),
        "IsLocked": attr.get("isLocked", False),
        "LastChapter": attr.get("lastChapter"),
        "LastVolume": attr.get("lastVolume"),
        "LatestUploadedChapter": str(attr.get("latestUploadedChapter", "")).upper() if attr.get("latestUploadedChapter") else None,
        "OriginalLanguage": attr.get("originalLanguage"),
        "PublicationDemographic": attr.get("publicationDemographic"),
        "State": attr.get("state"),
        "Status": attr.get("status"),
        "Year": attr.get("year"),
        "OfficialLinks": json.dumps(attr.get("links", {})) if attr.get("links") else None
    }
    upsert_manga(conn, [manga_db])
    logger.debug(f"Đã upsert Manga: {manga_db['TitleEn']}")

    # MangaAltTitle
    alt_titles = [{"MangaId": manga_id_upper, "LangCode": lang, "AltTitle": title} for alt in attr.get("altTitles", []) for lang, title in alt.items()]
    upsert_manga_alt_title(conn, alt_titles)
    logger.debug(f"Đã upsert {len(alt_titles)} tiêu đề thay thế.")

    # MangaDescription
    descriptions = [{"MangaId": manga_id_upper, "LangCode": lang, "Description": desc} for lang, desc in attr.get("description", {}).items()]
    upsert_manga_description(conn, descriptions)
    logger.debug(f"Đã upsert {len(descriptions)} mô tả.")

    # MangaAvailableLanguage
    available_languages = [{"MangaId": manga_id_upper, "LangCode": lang} for lang in attr.get("availableTranslatedLanguages", [])]
    upsert_manga_available_language(conn, available_languages)
    logger.debug(f"Đã upsert {len(available_languages)} ngôn ngữ có sẵn.")

    # MangaLink
    links = [{"MangaId": manga_id_upper, "Provider": provider, "Url": create_manga_link_url(provider, url)} for provider, url in attr.get("links", {}).items()]
    upsert_manga_link(conn, links)
    logger.debug(f"Đã upsert {len(links)} liên kết.")

    # MangaRelated
    related = fetch_related(manga_id, manga)
    upsert_manga_related(conn, related)

    # MangaStatistics
    stat = stats_dict.get(manga_id, {})
    rating = stat.get("rating", {})
    statistics_db = {
        "StatisticId": str(uuid.uuid4()).upper(),
        "MangaId": manga_id_upper,
        "Source": "Mangadex",
        "Follows": stat.get("follows"),
        "AverageRating": rating.get("average"),
        "BayesianRating": rating.get("bayesian"),
        "UnavailableChapters": stat.get("unavailableChaptersCount", 0),
        "FetchedAt": parse_dt(datetime.datetime.now().isoformat())
    }
    upsert_manga_statistics(conn, [statistics_db])
    logger.debug(f"Đã upsert thống kê: Follows={statistics_db['Follows']}")

    # MangaTag
    tag_ids = [t["id"] for t in attr.get("tags", [])]
    fetch_and_upsert_tags(conn, tag_ids, manga_id_upper)
    manga_tags = [{"MangaId": manga_id_upper, "TagId": str(t["id"]).upper()} for t in attr.get("tags", [])]
    upsert_manga_tag(conn, manga_tags)
    logger.debug(f"Đã upsert {len(manga_tags)} liên kết MangaTag.")

    # Chapter
    chapters = fetch_chapters(manga_id)
    upsert_chapter(conn, chapters)

    # Covers and Creators
    covers_db = fetch_covers(manga_id)
    creators_db = []
    creator_rels = []
    creator_ids = set()
    for rel in manga.get("relationships", []):
        rtype = rel.get("type")
        rid = str(rel.get("id")).upper()
        if rtype in ["author", "artist"]:
            if rid not in creator_ids:
                creator_full = fetch_creator(rel["id"])
                creator_full["Type"] = rtype
                creators_db.append(creator_full)
                creator_ids.add(rid)
            creator_rels.append({
                "CreatorId": rid,
                "RelatedId": manga_id_upper,
                "RelatedType": "manga"
            })
    upsert_creator(conn, creators_db)
    upsert_creator_relationship(conn, creator_rels)
    upsert_covers(conn, covers_db)
    logger.debug(f"Đã upsert {len(covers_db)} cover, {len(creators_db)} creator.")

    logger.info(f"Hoàn thành mapping và upsert manga ID: {manga_id_upper}")