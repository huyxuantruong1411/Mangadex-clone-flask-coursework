import pyodbc
import uuid
import random
import datetime
from slugify import slugify      # Cần: pip install python-slugify
from faker import Faker          # Thư viện mới: pip install Faker

# --- Cấu hình ---
conn_str = (
    r"DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=DESKTOP-HKIPI1M;"
    r"DATABASE=MangaLibrary;"
    r"Trusted_Connection=yes;"
)

MIN_LISTS_PER_USER = 3
MAX_LISTS_PER_USER = 10
MIN_MANGA_PER_LIST = 5
MAX_MANGA_PER_LIST = 25

# --- Khởi tạo Faker ---
# Sử dụng 'en_US' để có các câu tiếng Anh. 
# Bạn có thể dùng 'ja_JP' nếu muốn data tiếng Nhật, v.v.
fake = Faker('en_US')

# --- Script chính ---
conn = None
cursor = None

print("Starting list population script with FAKER...")

try:
    # Kết nối đến DB
    conn = pyodbc.connect(conn_str)
    conn.autocommit = False  # Bật chế độ transaction
    cursor = conn.cursor()
    print("Kết nối thành công! Bắt đầu transaction.")

    # 1. Lấy tất cả User
    cursor.execute("SELECT UserId, Username FROM dbo.[User]")
    users = cursor.fetchall()
    if not users:
        print("Không tìm thấy user nào. Hủy bỏ.")
        raise Exception("No users found in database.")

    print(f"Tìm thấy {len(users)} user.")

    # 2. Lấy tất cả MangaId (để làm pool chọn ngẫu nhiên)
    cursor.execute("SELECT MangaId FROM dbo.Manga")
    # Lấy MangaId từ tuple (row[0])
    all_manga_ids = [row.MangaId for row in cursor.fetchall()]
    
    if not all_manga_ids:
        print("Không tìm thấy manga nào. Hủy bỏ.")
        raise Exception("No manga found in database.")

    print(f"Tìm thấy {len(all_manga_ids)} manga để làm pool.")

    total_lists_created = 0
    total_items_added = 0

    # 3. Lặp qua từng user để tạo list
    for user in users:
        user_id = user.UserId
        username = user.Username
        print(f"\nProcessing user: {username} ({user_id})")

        num_lists_to_create = random.randint(MIN_LISTS_PER_USER, MAX_LISTS_PER_USER)
        print(f"  - Sẽ tạo {num_lists_to_create} list...")

        for i in range(num_lists_to_create):
            # 3a. Chuẩn bị data cho list mới
            new_list_id = uuid.uuid4()
            
            # === THAY ĐỔI Ở ĐÂY: Dùng Faker ===
            # Tạo tên list ngẫu nhiên, hấp dẫn
            list_name_base = random.choice([
                fake.bs().title(),             # Vd: "Synergistic E-Commerce"
                fake.catch_phrase(),           # Vd: "Vision-Oriented Desktop"
                f"My {fake.job()} Collection", # Vd: "My Web Developer Collection"
            ])
            # Thêm tên user để dễ nhận biết (và đảm bảo khác nhau)
            list_name = f"{list_name_base} (by {username})"
            # Giới hạn độ dài tên list nếu cần (schema là nvarchar(200))
            list_name = list_name[:200]
            
            # Tạo mô tả ngẫu nhiên (schema là nvarchar(max))
            list_desc = fake.text(max_nb_chars=250) # Tạo một đoạn text ngắn
            # ====================================

            # Tạo slug đơn giản (dùng base name cho slug đẹp hơn)
            slug_base = slugify(list_name_base) 
            list_slug = f"{slug_base}-{str(new_list_id)[:8]}"
            
            now = datetime.datetime.utcnow()
            
            # 3b. Chọn manga cho list này
            num_manga_to_add = random.randint(MIN_MANGA_PER_LIST, MAX_MANGA_PER_LIST)
            # Đảm bảo không chọn nhiều hơn số manga đang có
            num_manga_to_add = min(num_manga_to_add, len(all_manga_ids))
            
            selected_manga_ids = random.sample(all_manga_ids, num_manga_to_add)
            item_count = len(selected_manga_ids)

            # 3c. Insert vào bảng List
            sql_insert_list = """
            INSERT INTO dbo.List 
                (ListId, UserId, Name, Description, Visibility, Slug, CreatedAt, UpdatedAt, FollowerCount, ItemCount, IsPublic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_insert_list, (
                new_list_id, user_id, list_name, list_desc,
                'public', list_slug, now, now, 0, item_count, 1
            ))

            # 3d. Chuẩn bị data cho bảng ListManga (batch insert)
            items_to_insert = []
            for j, manga_id in enumerate(selected_manga_ids):
                items_to_insert.append((new_list_id, manga_id, now, j + 1)) # (ListId, MangaId, AddedAt, Position)
            
            sql_insert_items = """
            INSERT INTO dbo.ListManga (ListId, MangaId, AddedAt, Position)
            VALUES (?, ?, ?, ?)
            """
            
            # Thực thi batch insert
            cursor.executemany(sql_insert_items, items_to_insert)
            
            print(f"    + Đã tạo list: '{list_name}' với {item_count} items.")
            total_lists_created += 1
            total_items_added += item_count

except Exception as e:
    # Nếu có lỗi, rollback
    print(f"\n--- LỖI XẢY RA ---")
    print(f"Lỗi: {e}")
    if conn:
        print("Đang rollback tất cả thay đổi...")
        conn.rollback()
        print("Rollback hoàn tất.")
else:
    # Nếu không có lỗi, commit
    if conn:
        print("\n--- THÀNH CÔNG ---")
        print(f"Đã tạo tổng cộng {total_lists_created} list và thêm {total_items_added} manga items.")
        print("Đang commit transaction...")
        conn.commit()
        print("Commit hoàn tất.")
finally:
    # Luôn đóng kết nối
    if cursor:
        cursor.close()
    if conn:
        conn.close()
    print("Đã đóng kết nối. Script kết thúc.")