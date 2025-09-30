import urllib

class Config:
    SECRET_KEY = "secret_key_demo"

    DRIVER = "ODBC Driver 17 for SQL Server"
    SERVER = "DESKTOP-HKIPI1M"
    DATABASE = "MangaLibrary"
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"  # Sử dụng {{}} để escape
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"Trusted_Connection=yes;"
    )

    SQLALCHEMY_DATABASE_URI = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(connection_string)
    SQLALCHEMY_TRACK_MODIFICATIONS = False