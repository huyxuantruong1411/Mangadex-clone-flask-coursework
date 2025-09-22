import os
import sys
import pyodbc
import pymongo
from datetime import datetime

# ========== CONFIG ==========
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "manga_raw_data"
MONGO_COL = "mangadex_cover_arts"

DRIVER = "ODBC Driver 17 for SQL Server"
SERVER = r"localhost\SQLEXPRESS"
DATABASE = "MangaLibrary_Staging"
CONN_STR = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)

SQL_FILE = "create_table_mangadex_cover_arts.sql"
TABLE_NAME = "dbo.MangadexCoverArts"
BATCH_SIZE = 500


# ========== HELPER FUNCTIONS ==========
def ensure_table_exists(cursor):
    """Run SQL script to create table if not exists"""
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()
    try:
        cursor.execute(sql_script)
        print("[INFO] Table created successfully (or already exists).")
    except Exception as e:
        if "already an object" not in str(e):
            raise


def normalize_document(doc):
    """Extract and flatten fields from Mongo document"""
    data = doc.get("data", {})
    attr = data.get("attributes", {})
    rels = data.get("relationships", [])

    # relationships
    manga_id = None
    user_id = None
    for r in rels:
        if r.get("type") == "manga":
            manga_id = r.get("id")
        elif r.get("type") == "user":
            user_id = r.get("id")

    return (
        data.get("id"),  # cover_id
        doc.get("result"),
        doc.get("response"),
        safe_datetime(doc.get("fetched_at")),
        attr.get("description"),
        attr.get("volume"),
        attr.get("fileName"),
        attr.get("locale"),
        safe_datetime(attr.get("createdAt")),
        safe_datetime(attr.get("updatedAt")),
        attr.get("version"),
        manga_id,
        user_id,
    )


def safe_datetime(value):
    """Convert ISO string to datetime or None"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def print_progress(current, total, bar_length=40):
    """ASCII progress bar"""
    percent = current / total if total > 0 else 0
    filled = int(bar_length * percent)
    if filled >= bar_length:
        bar = "=" * bar_length
    else:
        bar = "=" * filled + ">" + " " * (bar_length - filled - 1)
    sys.stdout.write(f"\r[{bar}] {current}/{total} ({percent*100:.2f}%)")
    sys.stdout.flush()


# ========== MAIN ==========
def main():
    # Mongo connection
    mongo_client = pymongo.MongoClient(MONGO_URI)
    mongo_col = mongo_client[MONGO_DB][MONGO_COL]

    # SQL Server connection
    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cursor = conn.cursor()

    # ensure table exists
    ensure_table_exists(cursor)
    conn.commit()

    # fetch all documents
    total = mongo_col.count_documents({})
    docs = mongo_col.find({})
    print(f"[INFO] Total documents to ETL: {total}")

    batch = []
    inserted = 0

    insert_sql = f"""
        INSERT INTO {TABLE_NAME} (
            cover_id, result, response, fetched_at,
            description, volume, file_name, locale,
            created_at, updated_at, version,
            manga_id, user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for doc in docs:
        row = normalize_document(doc)
        batch.append(row)

        if len(batch) >= BATCH_SIZE:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            inserted += len(batch)
            print_progress(inserted, total)
            batch.clear()

    if batch:
        cursor.executemany(insert_sql, batch)
        conn.commit()
        inserted += len(batch)
        print_progress(inserted, total)

    print()  # newline after progress bar
    print(f"[DONE] Total inserted: {inserted}/{total}")

    cursor.close()
    conn.close()
    mongo_client.close()


if __name__ == "__main__":
    main()
