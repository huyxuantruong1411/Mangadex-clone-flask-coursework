import urllib

class Config:
    SECRET_KEY = "secret_key_demo"

    DRIVER = "ODBC Driver 17 for SQL Server"
    SERVER = "HEDI-SNOWY\SQLEXPRESS"
    DATABASE = "MangaLibrary"
    connection_string = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"Trusted_Connection=yes;"
    )

    SQLALCHEMY_DATABASE_URI = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(connection_string)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
