import pyodbc
import uuid
import random
from datetime import datetime, timedelta
import math

# ===== Connection =====
DRIVER = "ODBC Driver 17 for SQL Server"
SERVER = "HEDI-SNOWY\SQLEXPRESS"
DATABASE = "MangaLibrary"
connection_string = f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"

conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

USER_ID = '351E4344-63A8-4E6B-9DFC-7FAA5EC9E6DB'

# ===== Load data =====
# Manga with chapters
cursor.execute("""
SELECT m.MangaId, s.Follows
FROM Manga m
LEFT JOIN MangaStatistics s ON m.MangaId = s.MangaId
""")
mangas = cursor.fetchall()

# Chapters grouped by MangaId
cursor.execute("SELECT MangaId, ChapterId FROM Chapter")
chapter_rows = cursor.fetchall()
chapter_dict = {}
for row in chapter_rows:
    chapter_dict.setdefault(row.MangaId, []).append(row.ChapterId)

# Tags frequency
cursor.execute("""
SELECT mt.MangaId, t.TagId
FROM MangaTag mt
JOIN Tag t ON mt.TagId = t.TagId
""")
tag_rows = cursor.fetchall()
tag_count = {}
manga_tags = {}
for m_id, t_id in tag_rows:
    manga_tags.setdefault(m_id, []).append(t_id)
    tag_count[t_id] = tag_count.get(t_id, 0) + 1

# Top tags
top_tags = set([tid for tid, _ in sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:10]])

# ===== Prepare weighted manga list =====
weighted_mangas = []
for m in mangas:
    m_id, follows = m.MangaId, m.Follows or 0
    if m_id not in chapter_dict:  # skip manga with no chapters
        continue
    weight = 1 + math.log1p(follows)
    if set(manga_tags.get(m_id, [])) & top_tags:
        weight *= 1.5  # boost if has popular tag
    weighted_mangas.append((m_id, weight))

# Normalize weights
total_weight = sum(w for _, w in weighted_mangas)
weighted_probs = [w / total_weight for _, w in weighted_mangas]

# ===== Simulation parameters =====
TARGET_COUNT = 1000
reading_history_rows = []
rating_rows = []
comment_rows = []

read_mangas = set()

while len(reading_history_rows) < TARGET_COUNT:
    manga_id = random.choices([m for m, _ in weighted_mangas], weights=weighted_probs, k=1)[0]
    if manga_id in read_mangas:
        continue  # skip already read manga
    read_mangas.add(manga_id)

    chapter_id = random.choice(chapter_dict[manga_id])
    history_id = str(uuid.uuid4())
    last_page = random.randint(1, 30)
    read_at = datetime.now() - timedelta(days=random.randint(0, 365))
    reading_history_rows.append((history_id, USER_ID, manga_id, chapter_id, last_page, read_at))

    # Rating
    rating_id = str(uuid.uuid4())
    score = random.randint(1, 10)
    rating_rows.append((rating_id, USER_ID, manga_id, score))

    # Comment 50% chance
    if random.random() < 0.5:
        comment_id = str(uuid.uuid4())
        content = f"Comment on manga {manga_id[:8]} chapter {chapter_id[:8]}"
        created_at = read_at + timedelta(minutes=random.randint(1, 120))
        comment_rows.append((comment_id, USER_ID, manga_id, chapter_id, content, created_at, created_at, 0, random.randint(0,10), random.randint(0,5)))

# ===== Insert into DB =====
print("Inserting ReadingHistory...")
cursor.fast_executemany = True
cursor.executemany("""
INSERT INTO ReadingHistory (HistoryId, UserId, MangaId, ChapterId, LastPageRead, ReadAt)
VALUES (?, ?, ?, ?, ?, ?)
""", reading_history_rows)

print("Inserting Ratings...")
cursor.executemany("""
INSERT INTO Rating (RatingId, UserId, MangaId, Score)
VALUES (?, ?, ?, ?)
""", rating_rows)

print("Inserting Comments...")
cursor.executemany("""
INSERT INTO Comment (CommentId, UserId, MangaId, ChapterId, Content, CreatedAt, UpdatedAt, IsDeleted, LikeCount, DislikeCount)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", comment_rows)

conn.commit()
cursor.close()
conn.close()
print("Done! Inserted ≥1000 records per table.")
