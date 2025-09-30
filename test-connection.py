import pyodbc

conn_str = (
    r"DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=DESKTOP-HKIPI1M;"
    r"DATABASE=MangaLibrary;"
    r"Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    print("Kết nối thành công!")
except Exception as e:
    print("Kết nối thất bại:", e)