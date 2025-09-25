import pyodbc
import concurrent.futures
import logging
from uuid import UUID
from datetime import datetime
import time
import json
import os
from tqdm import tqdm

# ==============================================================================
# 1. Cấu hình
# ==============================================================================

# Thiết lập logging với UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('staging_to_covers.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Đặt encoding console nếu cần (cho Windows)
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Connection strings
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
MAX_WORKERS = 4 # Tăng số luồng để xử lý nhanh hơn (tùy thuộc vào CPU và DB)

# ==============================================================================
# 2. Hàm Database và Utility
# ==============================================================================

def connect_to_db(conn_str):
    """Kết nối tới database."""
    try:
        conn = pyodbc.connect(conn_str)
        # logging.info("Kết nối database thành công.") # Log quá nhiều
        return conn
    except Exception as e:
        logging.error(f"Lỗi kết nối database: {e}")
        raise

def extract_from_staging(staging_conn, batch_size=1000, last_cover_id=None):
    """Trích xuất dữ liệu từ staging theo batch."""
    cursor = staging_conn.cursor()
    # Chú ý: SQL Server so sánh chuỗi GUID/UUID theo thứ tự lexicographical.
    # Đảm bảo cột cover_id là kiểu CHAR/VARCHAR/NVARCHAR hoặc tương đương với UUID.
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
    logging.info(f"Trích xuất {len(rows)} bản ghi từ staging (batch), bắt đầu từ ID: {last_cover_id or 'Bắt đầu'}.")
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

# ==============================================================================
# 3. Logic chuyển đổi và chèn (Core Logic)
# ==============================================================================

def transform_and_insert_logic(main_conn, row):
    """
    Chuyển đổi và chèn dữ liệu (Logic cốt lõi).
    Hàm này được gọi bên trong mỗi luồng, sử dụng kết nối riêng.
    """
    cover_id_str, description, volume, file_name, locale, created_at, updated_at, version, manga_id_str = row

    try:
        cover_id = UUID(cover_id_str)
        manga_id = UUID(manga_id_str)
    except ValueError as e:
        logging.error(f"UUID không hợp lệ cho cover_id {cover_id_str} hoặc manga_id {manga_id_str}: {e}")
        return False

    # 1. Kiểm tra trùng lặp
    if check_duplicate(main_conn, cover_id):
        # logging.info(f"Bỏ qua cover_id trùng lặp: {cover_id}") # Log quá nhiều
        return False

    # 2. Chuyển đổi
    url = build_url(manga_id_str, file_name)
    image_data = None  # Không tải ảnh, dùng NULL. Cột image_data phải cho phép NULL.

    # Định dạng lại thời gian cho SQL Server (nếu cần)
    if created_at:
        # Loại bỏ tzinfo trước khi định dạng
        created_at = created_at.replace(tzinfo=None).isoformat() + '+00:00'
    if updated_at:
        updated_at = updated_at.replace(tzinfo=None).isoformat() + '+00:00'

    type_val = "cover_art"
    rel_user_id = None

    # 3. Chèn
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
        # logging.info(f"Chèn thành công cover_id: {cover_id}") # Log quá nhiều
        return True
    except Exception as e:
        main_conn.rollback()
        # HY000 (Connection is busy) không nên xảy ra với kết nối riêng.
        # Nếu gặp lỗi khác, log chi tiết.
        logging.error(f"Lỗi chèn cover_id {cover_id}: {e}")
        return False
    finally:
        cursor.close()

# ==============================================================================
# 4. Hàm Quản lý Đa luồng (Wrapper)
# ==============================================================================

def transform_and_insert_threaded(conn_str, row):
    """Hàm wrapper cho luồng: tạo kết nối, chạy logic, đóng kết nối."""
    main_conn = None
    try:
        # TẠO KẾT NỐI RIÊNG cho luồng này
        main_conn = connect_to_db(conn_str)
        return transform_and_insert_logic(main_conn, row)
    except Exception as e:
        # Lỗi xảy ra trong quá trình kết nối hoặc logic cốt lõi
        logging.error(f"Lỗi nghiêm trọng trong luồng xử lý: {e}")
        return False
    finally:
        # Đảm bảo kết nối được đóng
        if main_conn:
            try:
                main_conn.close()
            except Exception as e:
                logging.error(f"Lỗi khi đóng kết nối trong luồng: {e}")


# ==============================================================================
# 5. Checkpoint
# ==============================================================================

def load_checkpoint():
    """Tải checkpoint từ file."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f).get('last_cover_id', '')
        except Exception as e:
            logging.error(f"Lỗi khi đọc checkpoint: {e}")
            return ''
    return ''

def save_checkpoint(cover_id):
    """Lưu checkpoint."""
    try:
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump({'last_cover_id': cover_id}, f)
    except Exception as e:
        logging.error(f"Lỗi khi ghi checkpoint: {e}")


# ==============================================================================
# 6. Hàm Main
# ==============================================================================

def main():
    # Chỉ cần một kết nối cho Staging (chỉ dùng để đọc)
    staging_conn = connect_to_db(STAGING_CONN_STR)

    batch_size = 1000
    last_cover_id = load_checkpoint()
    total_inserted = 0

    logging.info(f"Bắt đầu xử lý từ cover_id: {last_cover_id if last_cover_id else 'Đầu tiên'}")

    try:
        while True:
            rows = extract_from_staging(staging_conn, batch_size, last_cover_id)
            if not rows:
                logging.info("Hoàn thành: Không còn bản ghi nào để trích xuất.")
                break

            new_last_cover_id = last_cover_id
            batch_inserted_count = 0

            with tqdm(total=len(rows), desc=f"Xử lý batch (từ {last_cover_id[:8]}...)", unit="bản ghi") as pbar:
                # Sử dụng ThreadPoolExecutor để chạy song song
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    # Truyền chuỗi kết nối (MAIN_CONN_STR) thay vì đối tượng kết nối
                    futures = [executor.submit(transform_and_insert_threaded, MAIN_CONN_STR, row) for row in rows]
                    
                    # Chờ và xử lý kết quả
                    for future, row in zip(futures, rows):
                        try:
                            if future.result():
                                total_inserted += 1
                                batch_inserted_count += 1
                        except Exception as e:
                            logging.error(f"Lỗi khi lấy kết quả luồng: {e}")
                            
                        # Cập nhật ID cuối cùng của batch (vì đã ORDER BY)
                        new_last_cover_id = row[0]
                        pbar.update(1)

            # Cập nhật checkpoint và last_cover_id sau khi xong toàn bộ batch
            if new_last_cover_id != last_cover_id:
                last_cover_id = new_last_cover_id
                save_checkpoint(last_cover_id)
                logging.info(f"Checkpoint được lưu: {last_cover_id}")
            
            logging.info(f"Hoàn thành batch. Đã chèn thành công {batch_inserted_count} bản ghi. Tổng cộng đã chèn: {total_inserted}")

            if len(rows) < batch_size:
                break # Kết thúc nếu batch cuối cùng không đầy đủ

    except Exception as e:
        logging.critical(f"LỖI CHÍNH XẢY RA, CHƯƠNG TRÌNH DỪNG LẠI: {e}")
    finally:
        staging_conn.close()
        logging.info("Đóng kết nối database staging.")

if __name__ == "__main__":
    main()