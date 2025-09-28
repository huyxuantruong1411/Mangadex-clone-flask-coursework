import pyodbc
import uuid
import random
import math
from datetime import datetime, timedelta

# ===== Connection =====
DRIVER = "ODBC Driver 17 for SQL Server"
SERVER = "HEDI-SNOWY\\SQLEXPRESS"
DATABASE = "MangaLibrary"
connection_string = f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"

conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

# ===== Load manga & chapters =====
print("Loading manga and related data...")

cursor.execute("""
SELECT m.MangaId, s.Follows
FROM Manga m
LEFT JOIN MangaStatistics s ON m.MangaId = s.MangaId
""")
mangas = cursor.fetchall()

cursor.execute("SELECT MangaId, ChapterId FROM Chapter")
chapter_rows = cursor.fetchall()
chapter_dict = {}
for row in chapter_rows:
    chapter_dict.setdefault(row.MangaId, []).append(row.ChapterId)

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

top_tags = set([tid for tid, _ in sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:10]])

# ===== Prepare weighted manga list =====
weighted_mangas = []
for m in mangas:
    m_id, follows = m.MangaId, m.Follows or 0
    if m_id not in chapter_dict:
        continue
    weight = 1 + math.log1p(follows)
    if set(manga_tags.get(m_id, [])) & top_tags:
        weight *= 1.5
    weighted_mangas.append((m_id, weight))

if not weighted_mangas:
    raise RuntimeError("No manga with chapters found!")

total_weight = sum(w for _, w in weighted_mangas)
weighted_probs = [w / total_weight for _, w in weighted_mangas]

# ===== Simulation parameters =====
USER_COUNT = 300
users_rows = []
reading_history_rows = []
rating_rows = []
comment_rows = []

today = datetime.now()

print("Generating users and behaviors...")

for i in range(USER_COUNT):
    user_id = str(uuid.uuid4())
    username = f"user_{i+1}"
    email = f"user{i+1}@example.com"
    password_hash = "fakehash123"
    created_at = today - timedelta(days=random.randint(0, 30))

    users_rows.append((user_id, username, email, password_hash, "user", created_at))

    # Each user reads 5–30 manga
    manga_sample_count = random.randint(5, 30)
    manga_ids = random.choices([m for m, _ in weighted_mangas], weights=weighted_probs, k=manga_sample_count)

    for manga_id in set(manga_ids):  # avoid duplicate manga for same user
        if manga_id not in chapter_dict:
            continue
        chapters = chapter_dict[manga_id]
        # Random 2–10 chapters
        chapter_sample = random.sample(chapters, min(len(chapters), random.randint(2, 10)))

        # Insert ReadingHistory for each chapter
        for chap in chapter_sample:
            history_id = str(uuid.uuid4())
            last_page = random.randint(1, 30)
            read_at = today - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 1440))
            reading_history_rows.append((history_id, user_id, manga_id, chap, last_page, read_at))

        # Insert Rating (1 per manga per user)
        rating_id = str(uuid.uuid4())
        score = max(1, min(10, int(random.normalvariate(7, 2))))
        rating_rows.append((rating_id, user_id, manga_id, score))

        # Insert Comment (40% chance)
        if random.random() < 0.4:
            comment_id = str(uuid.uuid4())
            content = f"User {username} says something about {manga_id[:6]}"
            created_at = today - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 1440))
            like_count = max(0, int(random.normalvariate(3, 2)))
            dislike_count = max(0, int(random.normalvariate(1, 1)))
            comment_rows.append((comment_id, user_id, manga_id, random.choice(chapters), content,
                                 created_at, created_at, 0, like_count, dislike_count))

# ===== Insert into DB =====
cursor.fast_executemany = True

print("Inserting Users...")
cursor.executemany("""
INSERT INTO [User] (UserId, Username, Email, PasswordHash, Role, CreatedAt)
VALUES (?, ?, ?, ?, ?, ?)
""", users_rows)

print("Inserting ReadingHistory...")
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

print(f"Done! Inserted {len(users_rows)} users, {len(reading_history_rows)} histories, {len(rating_rows)} ratings, {len(comment_rows)} comments.")
