import pyodbc
import random

# ===== Connection =====
DRIVER = "ODBC Driver 17 for SQL Server"
SERVER = "HEDI-SNOWY\\SQLEXPRESS"
DATABASE = "MangaLibrary"
connection_string = f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"

conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

# ===== Detect invalid ratings =====
print("Checking invalid ratings...")
cursor.execute("""
SELECT RatingId, Score
FROM Rating
WHERE Score < 1 OR Score > 10 OR Score IS NULL
""")
bad_ratings = cursor.fetchall()

print(f"Found {len(bad_ratings)} invalid rating(s).")

# ===== Fix by reassigning random valid score =====
fixed_rows = []
for r in bad_ratings:
    rating_id, score = r
    new_score = random.randint(1, 10)
    fixed_rows.append((new_score, rating_id))
    print(f"Fixing RatingId={rating_id}, old Score={score}, new Score={new_score}")

if fixed_rows:
    cursor.executemany("""
    UPDATE Rating
    SET Score = ?
    WHERE RatingId = ?
    """, fixed_rows)
    conn.commit()
    print(f"Updated {len(fixed_rows)} rating(s).")
else:
    print("No invalid ratings found. Nothing to update.")

cursor.close()
conn.close()
print("Done.")
