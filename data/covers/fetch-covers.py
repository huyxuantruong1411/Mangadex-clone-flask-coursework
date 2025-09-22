import os
import time
import json
import random
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests
import pyodbc
from tqdm import tqdm

# ====== CONFIG ======
BASE_URL = "https://api.mangadex.org"  # Fixed typo: mangadex not mangadx
COVER_ENDPOINT = "/cover"

# API page params
PAGE_LIMIT = 100  # safe upper bound

# Enhanced retry params
MAX_RETRIES = 20  # Tăng từ 5 lên 20
MIN_DELAY = 1   # Tăng delay tối thiểu
MAX_DELAY = 120.0 # Tăng delay tối đa lên 2 phút
BACKOFF_FACTOR = 2.0  # Hệ số nhân backoff
JITTER_RANGE = 0.3    # Random jitter để tránh thundering herd

# Download threads - giảm để tránh quá tải
MAX_DOWNLOAD_WORKERS = 4

# File storage
BASE_COVER_DIR = "covers"

# ====== MSSQL CONNECTION ======
DRIVER = "ODBC Driver 17 for SQL Server"
SERVER = r"localhost\SQLEXPRESS"
DATABASE = "MangaLibrary"
CONN_STR = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)

TABLE_NAME = "MangaCovers"

# ====== LOGGING ======
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("mangadx_covers.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mangadx_covers")

# ====== USER AGENT POOL ======
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
]

REFERER_POOL = [
    "https://mangadex.org/",
    "https://mangadex.org/titles/",
    "https://mangadex.org/recent",
    "https://mangadex.org/follows",
    "https://www.google.com/",
    "https://www.bing.com/",
    ""  # Empty referer
]

class EnhancedMangaDxCoverFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.rotate_headers()  # Set initial random headers
        
        # Cấu hình retry adapter với urllib3
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        self.request_count = 0

    def rotate_headers(self):
        """Rotate User-Agent and other headers randomly."""
        user_agent = random.choice(USER_AGENTS)
        referer = random.choice(REFERER_POOL)
        
        # Additional random headers to look more browser-like
        accept_encoding = random.choice([
            "gzip, deflate, br",
            "gzip, deflate",
            "gzip, deflate, br, zstd"
        ])
        
        accept_language = random.choice([
            "en-US,en;q=0.9",
            "en-US,en;q=0.9,vi;q=0.8",
            "en-US,en;q=0.8,vi;q=0.7",
            "vi-VN,vi;q=0.9,en;q=0.8",
            "en-GB,en;q=0.9",
            "en-US,en;q=0.5"
        ])
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": accept_language,
            "Accept-Encoding": accept_encoding,
            "DNT": random.choice(["1", "0", ""]),
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": random.choice(["document", "empty", "image"]),
            "Sec-Fetch-Mode": random.choice(["navigate", "cors", "no-cors"]),
            "Sec-Fetch-Site": random.choice(["same-origin", "cross-site", "none"]),
            "Cache-Control": random.choice(["no-cache", "max-age=0", ""]),
        }
        
        if referer:
            headers["Referer"] = referer
            
        # Randomly omit some headers to add variation
        if random.random() < 0.3:
            headers.pop("DNT", None)
        if random.random() < 0.4:
            headers.pop("Cache-Control", None)
        if random.random() < 0.2:
            headers.pop("Upgrade-Insecure-Requests", None)
            
        self.session.headers.clear()
        self.session.headers.update(headers)
        
        logger.debug(f"Rotated to UA: {user_agent[:50]}...")

    def refresh_session(self):
        """Refresh the session periodically to avoid session-based tracking."""
        logger.debug("Refreshing session to avoid tracking")
        self.session.close()
        self.session = requests.Session()
        
        # Recreate retry adapter
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        
        self.rotate_headers()

    def make_request(self, path, params=None, is_image=False):
        """Enhanced request method với rotating headers và exponential backoff."""
        url = BASE_URL + path if not is_image else path
        
        # Refresh session every 50-100 requests to avoid tracking
        if self.request_count > 0 and self.request_count % random.randint(50, 100) == 0:
            self.refresh_session()
            logger.debug(f"Session refreshed at request #{self.request_count}")
        
        # Rotate headers every 5-15 requests
        self.request_count += 1
        if self.request_count % random.randint(5, 15) == 0:
            self.rotate_headers()
            logger.debug(f"Headers rotated at request #{self.request_count}")
        
        
        for attempt in range(MAX_RETRIES):
            try:
                # Adaptive delay based on attempt number and recent failures
                base_delay = MIN_DELAY * (BACKOFF_FACTOR ** attempt)
                
                # Add extra conservative delay for image downloads
                if is_image:
                    base_delay *= 1.5
                
                # Random jitter
                jitter = random.uniform(-JITTER_RANGE, JITTER_RANGE) * base_delay
                delay = min(MAX_DELAY, max(MIN_DELAY, base_delay + jitter))
                
                if attempt > 0:
                    logger.info(f"Attempt {attempt + 1}/{MAX_RETRIES}, waiting {delay:.2f}s before retry...")
                    time.sleep(delay)
                else:
                    # Random delay for first request to look more human-like
                    initial_delay = random.uniform(0.3, 1.2) if not is_image else random.uniform(0.5, 2.0)
                    time.sleep(initial_delay)

                response = self.session.get(url, params=params, timeout=30)
                
                # Xử lý rate limit 429
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited (429). Waiting {retry_after}s as instructed by server...")
                    time.sleep(retry_after + random.uniform(1, 5))  # Thêm buffer
                    continue
                
                # Success cases
                if response.status_code == 200:
                    if is_image:
                        return response.content
                    else:
                        data = response.json()
                        if data.get("result") == "ok":
                            return data
                        else:
                            logger.error(f"API returned error: {data.get('errors', 'Unknown error')}")
                            return None
                
                elif response.status_code == 204:
                    return {} if not is_image else b""
                
                else:
                    logger.warning(f"HTTP {response.status_code}: {response.text[:200]}")
                    if response.status_code in [404, 403]:
                        # Không retry cho lỗi 404, 403
                        return None
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                continue
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                continue
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                continue
        
        logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
        return None

    def get_conn(self):
        return pyodbc.connect(CONN_STR, autocommit=True)

    def ensure_table(self):
        """Create table if not exists."""
        create_sql = f"""
        IF NOT EXISTS (
            SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[{TABLE_NAME}]') AND type in (N'U')
        )
        BEGIN
            CREATE TABLE [dbo].[{TABLE_NAME}](
                [cover_id] NVARCHAR(50) PRIMARY KEY,
                [manga_id] UNIQUEIDENTIFIER NOT NULL,
                [file_name] NVARCHAR(300),
                [description] NVARCHAR(MAX),
                [volume] NVARCHAR(50),
                [locale] NVARCHAR(20),
                [created_at] DATETIMEOFFSET,
                [updated_at] DATETIMEOFFSET,
                [version] INT,
                [image_url] NVARCHAR(1000),
                [file_path] NVARCHAR(1000),
                [downloaded_at] DATETIMEOFFSET NULL,
                [raw_json] NVARCHAR(MAX),
                [inserted_at] DATETIMEOFFSET DEFAULT SYSUTCDATETIME()
            );
        END
        """
        
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            cur.execute(create_sql)
            logger.info(f"Ensured table [{TABLE_NAME}] exists")
        finally:
            cur.close()
            conn.close()

    def upsert_cover_meta(self, cover):
        """Upsert cover metadata với kiểm tra manga tồn tại."""
        cover_id = cover.get("id")
        if not cover_id:
            return False
            
        attributes = cover.get("attributes", {}) or {}
        file_name = attributes.get("fileName")
        description = attributes.get("description")
        volume = attributes.get("volume")
        locale = attributes.get("locale")
        created_at = attributes.get("createdAt")
        updated_at = attributes.get("updatedAt")
        version = attributes.get("version")
        
        # Find manga relationship
        manga_id = None
        for rel in cover.get("relationships", []):
            if rel.get("type") == "manga":
                manga_id = rel.get("id")
                break
        
        if not manga_id:
            logger.debug(f"Cover {cover_id} has no manga relationship - skipping")
            return False
        
        conn = self.get_conn()
        cur = conn.cursor()
        
        try:
            # Build image URL
            image_url = None
            if manga_id and file_name:
                image_url = f"https://uploads.mangadex.org/covers/{manga_id}/{file_name}"  # Fixed URL
            
            raw_json = json.dumps(cover, ensure_ascii=False)
            
            # Upsert using MERGE
            merge_sql = f"""
            MERGE INTO [dbo].[{TABLE_NAME}] AS target
            USING (SELECT ? AS cover_id) AS src
            ON target.cover_id = src.cover_id
            WHEN MATCHED THEN
              UPDATE SET
                manga_id = ?, file_name = ?, description = ?, volume = ?, locale = ?,
                created_at = ?, updated_at = ?, version = ?, image_url = ?, raw_json = ?
            WHEN NOT MATCHED THEN
              INSERT (cover_id, manga_id, file_name, description, volume, locale, created_at, updated_at, version, image_url, raw_json)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """
            
            params = (
                cover_id,
                manga_id, file_name, description, volume, locale, 
                created_at, updated_at, version, image_url, raw_json,
                cover_id, manga_id, file_name, description, volume, locale,
                created_at, updated_at, version, image_url, raw_json
            )
            
            cur.execute(merge_sql, params)
            return True
            
        except Exception as e:
            logger.error(f"Error upserting cover {cover_id}: {e}")
            return False
        finally:
            cur.close()
            conn.close()

    def update_download_info(self, cover_id, file_path):
        """Update download information."""
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            update_sql = f"""
            UPDATE [dbo].[{TABLE_NAME}]
            SET file_path = ?, downloaded_at = ?
            WHERE cover_id = ?
            """
            cur.execute(update_sql, (file_path, datetime.utcnow(), cover_id))
        finally:
            cur.close()
            conn.close()

    def download_image(self, image_url, local_path):
        """Download image với enhanced retry."""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            content = self.make_request(image_url, is_image=True)
            if content:
                tmp_path = local_path + ".tmp"
                with open(tmp_path, "wb") as f:
                    f.write(content)
                os.replace(tmp_path, local_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error downloading {image_url}: {e}")
            return False

    def fetch_all_covers_and_save(self, start_offset=0):
        """Main function to fetch all covers."""
        logger.info("Starting enhanced MangaDx cover fetcher")
        
        os.makedirs(BASE_COVER_DIR, exist_ok=True)
        self.ensure_table()
        
        offset = start_offset
        total_fetched = 0
        saved_meta = 0
        skipped = 0
        to_download = []
        
        try:
            while True:
                params = {"limit": PAGE_LIMIT, "offset": offset}
                logger.info(f"Fetching covers page offset={offset} limit={PAGE_LIMIT}")
                
                data = self.make_request(COVER_ENDPOINT, params=params)
                if not data:
                    logger.error(f"Failed to fetch page at offset {offset}")
                    break
                
                items = data.get("data", [])
                if not items:
                    logger.info("No more cover data returned; finished pagination.")
                    break
                
                # Process items
                for cover in items:
                    total_fetched += 1
                    if self.upsert_cover_meta(cover):
                        saved_meta += 1
                        
                        # Prepare download info
                        attributes = cover.get("attributes", {}) or {}
                        file_name = attributes.get("fileName")
                        manga_id = None
                        for rel in cover.get("relationships", []):
                            if rel.get("type") == "manga":
                                manga_id = rel.get("id")
                                break
                        
                        if manga_id and file_name:
                            image_url = f"https://uploads.mangadex.org/covers/{manga_id}/{file_name}"  # Fixed URL
                            local_path = os.path.join(BASE_COVER_DIR, manga_id, file_name)
                            
                            if not os.path.exists(local_path):
                                to_download.append((cover.get("id"), manga_id, file_name, image_url))
                    else:
                        skipped += 1
                
                logger.info(f"Processed page: offset {offset} -> items {len(items)} (saved: {saved_meta}, skipped: {skipped})")
                offset += PAGE_LIMIT
                
                # Checkpoint every 10 pages
                if offset % (PAGE_LIMIT * 10) == 0:
                    logger.info(f"Checkpoint: processed {total_fetched} covers, saved {saved_meta}, queued {len(to_download)} for download")
        
        except KeyboardInterrupt:
            logger.info(f"Interrupted by user. Processed up to offset {offset}")
        except Exception as e:
            logger.error(f"Unexpected error during fetching: {e}")
        
        logger.info(f"Finished fetching metadata. total_fetched={total_fetched}, saved_meta={saved_meta}, to_download={len(to_download)}")
        
        # Download images
        if to_download:
            self.download_images(to_download)
        
        logger.info("All done!")

    def download_images(self, to_download):
        """Download images với thread pool."""
        downloaded = 0
        failed = 0
        
        logger.info(f"Starting downloads with {MAX_DOWNLOAD_WORKERS} workers")
        
        with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
            future_to_cover = {}
            
            for cover_id, manga_id, file_name, image_url in to_download:
                local_path = os.path.join(BASE_COVER_DIR, manga_id, file_name)
                future = executor.submit(self._download_and_update, cover_id, image_url, local_path)
                future_to_cover[future] = (cover_id, image_url)
            
            for future in tqdm(as_completed(future_to_cover), total=len(future_to_cover), desc="Downloading covers"):
                cover_id, image_url = future_to_cover[future]
                try:
                    success = future.result()
                    if success:
                        downloaded += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Download future error for cover {cover_id}: {e}")
                    failed += 1
        
        logger.info(f"Download completed. downloaded={downloaded}, failed={failed}")

    def _download_and_update(self, cover_id, image_url, local_path):
        """Worker function for downloading and updating DB."""
        try:
            success = self.download_image(image_url, local_path)
            if success:
                self.update_download_info(cover_id, local_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error in download worker for {cover_id}: {e}")
            return False

    def close(self):
        """Clean up resources."""
        if self.session:
            self.session.close()

def main():
    fetcher = EnhancedMangaDxCoverFetcher()
    try:
        # Có thể resume từ offset cụ thể nếu bị gián đoạn
        start_offset = 0  # Thay đổi nếu cần resume
        fetcher.fetch_all_covers_and_save(start_offset)
    finally:
        fetcher.close()

if __name__ == "__main__":
    main()