import pyodbc
import logging

# =======================
# Cấu hình logging
# =======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =======================
# Chuỗi kết nối
# =======================
conn_str = (
    r"DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=DESKTOP-HKIPI1M;"
    r"DATABASE=MangaLibrary;"
    r"Trusted_Connection=yes;"
)

# =======================
# Kết nối DB
# =======================
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
logging.info("Kết nối thành công tới SQL Server.")

try:
    # =======================
    # Xóa bản ghi trùng manga_id, giữ lại bản mới nhất
    # =======================
    delete_sql = """
    WITH CTE AS (
        SELECT *,
               ROW_NUMBER() OVER (PARTITION BY MangaId ORDER BY FetchedAt DESC) AS rn
        FROM dbo.MangaStatistics
    )
    DELETE FROM CTE
    WHERE rn > 1;
    """
    cursor.execute(delete_sql)
    deleted_count = cursor.rowcount
    conn.commit()
    logging.info(f"Đã xóa {deleted_count} bản ghi trùng trong bảng MangaStatistics.")

except Exception as e:
    logging.error(f"Lỗi khi xóa bản ghi: {e}")
    conn.rollback()

finally:
    cursor.close()
    conn.close()
    logging.info("Đóng kết nối SQL Server.")
