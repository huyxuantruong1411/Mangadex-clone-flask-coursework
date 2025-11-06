import os
import urllib

class Config:
    # Lấy SECRET_KEY từ biến môi trường
    SECRET_KEY = os.environ.get("SECRET_KEY", "day_la_secret_key_mac_dinh_cho_dev")

    # Lấy thông tin database từ biến môi trường
    # Các giá trị mặc định (sau dấu phẩy) chỉ dùng khi chạy local
    DRIVER = os.environ.get("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    SERVER = os.environ.get("SQL_SERVER") # Sẽ được Render cung cấp
    DATABASE = os.environ.get("SQL_DATABASE", "MangaLibrary")
    USERNAME = os.environ.get("SQL_USERNAME", "sa")
    PASSWORD = os.environ.get("SQL_PASSWORD") # Sẽ được set trên Render

    # Tạo connection string mới, sử dụng SQL Server Authentication (Username/Password)
    # Bỏ 'Trusted_Connection=yes'
    connection_string = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        f"TrustServerCertificate=yes;" # Nên thêm dòng này khi deploy
    )

    SQLALCHEMY_DATABASE_URI = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(connection_string)
    SQLALCHEMY_TRACK_MODIFICATIONS = False