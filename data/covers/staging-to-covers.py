import pyodbc
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures
import logging
from uuid import UUID
from datetime import datetime
import time
import json
import os
from tqdm import tqdm  # Giả sử đã import từ trước, nếu không thì thêm

# Thiết lập logging với UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('staging_to_covers.log', encoding='utf-8'),  # UTF-8 cho file
        logging.StreamHandler()  # In ra console
    ]
)

# Đặt encoding console nếu cần (cho Windows)
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Connection strings (giữ nguyên)
STAGING_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=localhost\SQLEXPRESS;"
    "DATABASE=MangaLibrary_Staging;"
    "Trusted_Connection=yes;"
)

MAIN_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=localhost\SQLEXPRESS;"
    "DATABASE=MangaLibrary;"
    "Trusted_Connection=yes;"
)

# Checkpoint file
CHECKPOINT_FILE = 'checkpoint.json'

# User-Agent cho MangaDex
USER_AGENT = "MangaLibraryScript/1.0 (huy14112002@gmail.com)"

def connect_to_db(conn_str):
    """Kết nối tới database."""
    try:
        conn = pyodbc.connect(conn_str)
        logging.info("Kết nối database thành công.")
        return conn
    except Exception as e:
        logging.error(f"Lỗi kết nối database: {e}")
        raise

def extract_from_staging(staging_conn, batch_size=1000, last_cover_id=None):
    """Trích xuất dữ liệu từ staging theo batch."""
    cursor = staging_conn.cursor()
    query = """
    SELECT TOP (?) 
        cover_id, description, volume, file_name, locale, 
        created_at, updated_at, version, manga_id
    FROM dbo.MangadexCoverArts
    WHERE cover_id > ?
    ORDER BY cover_id
    """
    cursor.execute(query, (batch_size, last_cover_id or ''))
    rows = cursor.fetchall()
    cursor.close()
    logging.info(f"Trích xuất {len(rows)} bản ghi từ staging (batch).")
    return rows

def check_duplicate(main_conn, cover_id):
    """Kiểm tra trùng lặp cover_id."""
    cursor = main_conn.cursor()
    query = "SELECT COUNT(*) FROM dbo.Covers WHERE cover_id = ?"
    cursor.execute(query, (cover_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0

def build_url(manga_id_str, file_name):
    """Xây dựng URL cho ảnh cover."""
    if not file_name.lower().endswith('.jpg'):
        file_name += '.jpg'
    return f"https://uploads.mangadex.org/covers/{manga_id_str}/{file_name}"

def check_url_exists(url, session):
    """Kiểm tra xem URL có tồn tại không bằng HEAD request."""
    try:
        response = session.head(url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        logging.warning(f"Lỗi kiểm tra URL {url}: {e}")
        return False

def download_image(url, max_retries=3, backoff_factor=5):  # Tăng backoff
    """Tải ảnh với retry logic."""
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    retries = Retry(total=max_retries, backoff_factor=backoff_factor, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        # Kiểm tra URL trước
        if not check_url_exists(url, session):
            logging.warning(f"URL không tồn tại: {url}")
            return None
        
        response = session.get(url, timeout=10)
        response.raise_for_status()
        x_request_id = response.headers.get('X-Request-ID', 'N/A')
        logging.info(f"Tải ảnh thành công từ {url}, X-Request-ID: {x_request_id}")
        return response.content
    except requests.exceptions.RequestException as e:
        x_request_id = response.headers.get('X-Request-ID', 'N/A') if 'response' in locals() else 'N/A'
        logging.error(f"Lỗi tải ảnh từ {url}, X-Request-ID: {x_request_id}: {e}")
        return None
    finally:
        session.close()

def transform_and_insert(main_conn, row):
    """Chuyển đổi và chèn dữ liệu."""
    cover_id_str = row[0]
    description = row[1]
    volume = row[2]
    file_name = row[3]
    locale = row[4]
    created_at = row[5]
    updated_at = row[6]
    version = row[7]
    manga_id_str = row[8]

    try:
        cover_id = UUID(cover_id_str)
        manga_id = UUID(manga_id_str)
    except ValueError as e:
        logging.error(f"UUID không hợp lệ cho cover_id {cover_id_str} hoặc manga_id {manga_id_str}: {e}")
        return False

    if check_duplicate(main_conn, cover_id):
        logging.info(f"Bỏ qua cover_id trùng lặp: {cover_id}")
        return False

    url = build_url(manga_id_str, file_name)
    image_data = download_image(url)
    if image_data is None:
        logging.warning(f"Bỏ qua chèn cover_id {cover_id} do lỗi tải ảnh.")
        return False

    if created_at:
        created_at = created_at.replace(tzinfo=None).isoformat() + '+00:00'
    if updated_at:
        updated_at = updated_at.replace(tzinfo=None).isoformat() + '+00:00'

    type_val = "cover_art"
    rel_user_id = None

    cursor = main_conn.cursor()
    query = """
    INSERT INTO dbo.Covers (
        cover_id, manga_id, type, description, volume, fileName, locale, 
        createdAt, updatedAt, version, rel_user_id, url, image_data
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        cover_id, manga_id, type_val, description, volume, file_name, locale,
        created_at, updated_at, version, rel_user_id, url, image_data
    )
    try:
        cursor.execute(query, params)
        main_conn.commit()
        logging.info(f"Chèn thành công cover_id: {cover_id}")
        return True
    except Exception as e:
        main_conn.rollback()
        logging.error(f"Lỗi chèn cover_id {cover_id}: {e}")
        return False
    finally:
        cursor.close()

def load_checkpoint():
    """Tải checkpoint từ file."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f).get('last_cover_id', '')
    return ''

def save_checkpoint(cover_id):
    """Lưu checkpoint."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'last_cover_id': cover_id}, f)

def main():
    staging_conn = connect_to_db(STAGING_CONN_STR)
    main_conn = connect_to_db(MAIN_CONN_STR)

    batch_size = 1000
    last_cover_id = load_checkpoint()
    total_inserted = 0

    try:
        while True:
            rows = extract_from_staging(staging_conn, batch_size, last_cover_id)
            if not rows:
                break

            with tqdm(total=len(rows), desc="Xử lý batch", unit="bản ghi") as pbar:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:  # Giảm workers
                    futures = [executor.submit(transform_and_insert, main_conn, row) for row in rows]
                    for future, row in zip(futures, rows):
                        if future.result():
                            total_inserted += 1
                            last_cover_id = row[0]  # Cập nhật checkpoint
                            save_checkpoint(last_cover_id)
                        time.sleep(3)  # Delay 3 giây giữa các bản ghi
                        pbar.update(1)

            logging.info(f"Đã xử lý {total_inserted} bản ghi tổng cộng.")
            if len(rows) < batch_size:
                break

    finally:
        staging_conn.close()
        main_conn.close()
        logging.info("Đóng kết nối database.")

if __name__ == "__main__":
    main()