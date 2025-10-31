# export_data.py (version 4 - Final Fix)
import os
import pandas as pd
from sqlalchemy import create_engine, text
import urllib

def export_database_to_csv_v4():
    """
    Connects to the source SQL Server database using a robust SQLAlchemy
    engine configuration. This version uses the text() construct for
    SQLAlchemy 2.0+ compatibility, preventing "Not an executable object" errors.
    """
    # --- 1. Connection details for the SOURCE machine ---
    server = r"DESKTOP-HKIPI1M"
    database = "MangaLibrary"
    driver = "ODBC Driver 17 for SQL Server"

    # --- 2. Create 'data' directory if it doesn't exist ---
    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    try:
        # --- 3. Build the ODBC connection string ---
        odbc_conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
        )
        
        quoted_conn_str = urllib.parse.quote_plus(odbc_conn_str)
        engine_url = f"mssql+pyodbc:///?odbc_connect={quoted_conn_str}"
        engine = create_engine(engine_url)

        # --- 4. Get a list of all user tables ---
        with engine.connect() as conn:
            print("Successfully connected to the source database using SQLAlchemy.")
            
            # *** FIX: Wrap the SQL string in the text() construct ***
            tables_query = text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            
            result = conn.execute(tables_query)
            table_names = [row[0] for row in result]
        
        print(f"Found {len(table_names)} tables to export: {table_names}")

        # --- 5. Loop through each table and export its data ---
        with engine.connect() as conn:
            for table_name in table_names:
                print(f"Exporting data from table: {table_name}...")
                try:
                    query = f'SELECT * FROM [{table_name}]'
                    df = pd.read_sql(query, conn)

                    file_path = os.path.join(output_dir, f"{table_name}.csv")
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')
                    print(f"-> Successfully exported {len(df)} rows to {file_path}")

                except Exception as e:
                    print(f"!! Error exporting table [{table_name}]: {e}")

    except Exception as e:
        print(f"!! An unexpected error occurred: {e}")
    finally:
        if 'engine' in locals():
            engine.dispose()
            print("Database connection closed.")

if __name__ == "__main__":
    export_database_to_csv_v4()