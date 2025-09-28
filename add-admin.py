import uuid
import pyodbc
from werkzeug.security import generate_password_hash
from datetime import datetime

# ===== Cấu hình DB =====
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=HEDI-SNOWY\SQLEXPRESS;"           # sửa host hoặc host,port
    "DATABASE=MangaLibrary;"
    "Trusted_Connection=yes;"     # dùng Windows Auth; nếu dùng SQL Auth thì thay bằng UID=...;PWD=...
)

# ===== Thông tin admin =====
user_id = str(uuid.uuid4())
username = "admin"
email = "admin@example.com"
password = "1234"  # đổi mật khẩu tại đây
password_hash = generate_password_hash(password)

# ===== Thêm vào DB =====
with pyodbc.connect(conn_str) as conn:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO [dbo].[User] (
            UserId, Username, Email, PasswordHash, Avatar, Role, IsLocked, CreatedAt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, username, email, password_hash,
        None, "Admin", 0, datetime.utcnow()
    ))
    conn.commit()

print("✅ Admin user created successfully.")
print(f"UserId: {user_id}")
print(f"Username: {username}")
print(f"Email: {email}")
