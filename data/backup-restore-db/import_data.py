# import_data_complete.py - Complete import including binary data
import pyodbc
import pandas as pd
import os
from sqlalchemy import create_engine, text
import urllib
import time
import ast

def import_data_complete():
    """
    Complete import with ALL data including binary fields
    """
    # --- 1. Connection details ---
    dest_server = r"HEDI-SNOWY\SQLEXPRESS"
    dest_db = "MangaLibrary"
    driver = "ODBC Driver 17 for SQL Server"

    master_conn_str = f"DRIVER={{{driver}}};SERVER={dest_server};DATABASE=master;Trusted_Connection=yes;autocommit=True"
    db_conn_str = f"DRIVER={{{driver}}};SERVER={dest_server};DATABASE={dest_db};Trusted_Connection=yes;"
    
    quoted_conn_str = urllib.parse.quote_plus(db_conn_str)
    engine_url = f"mssql+pyodbc:///?odbc_connect={quoted_conn_str}"
    engine = create_engine(engine_url, fast_executemany=True)

    # --- 2. Paths ---
    schema_file = 'schema.sql'
    data_dir = 'data'

    if not os.path.exists(schema_file) or not os.path.exists(data_dir):
        print(f"!! Error: Make sure 'schema.sql' and the 'data' directory exist.")
        return

    # --- 3. Configuration mappings ---
    identity_tables = {
        'CreatorRelationship': 'Id',
        'MangaAltTitle': 'AltTitleId',
        'MangaAvailableLanguage': 'LangId',
        'MangaDescription': 'DescriptionId',
        'MangaLink': 'LinkId'
    }

    # Tables with binary columns
    binary_columns_map = {
        'Covers': 'image_data',
        'MangaCover': 'ImageData'
    }

    # Map table columns that should be boolean (bit)
    boolean_columns = {
        'Chapter': ['IsUnavailable'],
        'Comment': ['IsDeleted', 'IsSpoiler'],
        'List': ['IsPublic'],
        'Manga': ['ChapterNumbersResetOnNewVolume', 'IsLocked'],
        'User': ['IsLocked']
    }

    # Map table columns that should be integer
    integer_columns = {
        'Chapter': ['Pages'],
        'Comment': ['LikeCount', 'DislikeCount'],
        'Manga': ['Year'],
        'Rating': ['Score'],
        'ReadingHistory': ['LastPageRead']
    }

    def convert_boolean(value):
        """Convert string boolean to bit (0/1)"""
        if pd.isna(value) or value is None:
            return None
        if isinstance(value, str):
            return 1 if value.lower() in ['true', '1', 'yes'] else 0
        return int(bool(value))

    def convert_integer(value):
        """Safely convert to integer"""
        if pd.isna(value) or value is None or value == '':
            return None
        try:
            return int(float(value))
        except:
            return None

    def convert_binary(value):
        """Convert string representation of binary to actual bytes"""
        if pd.isna(value) or value is None or value == '':
            return None
        
        try:
            # Case 1: Python bytes literal string like "b'\\xff\\xd8...'"
            if isinstance(value, str) and value.startswith("b'") and value.endswith("'"):
                # Remove b' and trailing '
                hex_str = value[2:-1]
                # Use ast.literal_eval to properly decode escape sequences
                return ast.literal_eval(f"b'{hex_str}'")
            
            # Case 2: Already bytes
            elif isinstance(value, bytes):
                return value
            
            # Case 3: Hex string without prefix
            elif isinstance(value, str):
                try:
                    return bytes.fromhex(value)
                except:
                    # Try to evaluate as Python literal
                    return ast.literal_eval(value)
            
            return None
        except Exception as e:
            print(f"      Warning: Could not convert binary value: {str(e)[:100]}")
            return None

    try:
        # --- 4. Drop and recreate database ---
        print(f"Connecting to master database to manage '{dest_db}'...")
        with pyodbc.connect(master_conn_str, autocommit=True) as master_conn:
            with master_conn.cursor() as cursor:
                if cursor.execute(f"SELECT db_id('{dest_db}')").fetchone()[0]:
                    print(f"Database '{dest_db}' already exists. Dropping it...")
                    cursor.execute(f"ALTER DATABASE [{dest_db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;")
                    time.sleep(2)
                    cursor.execute(f"DROP DATABASE [{dest_db}]")
                    print(f"-> Database '{dest_db}' dropped successfully.")
                
                print(f"Creating a new, clean database: '{dest_db}'...")
                cursor.execute(f"CREATE DATABASE [{dest_db}]")
                print(f"-> Database '{dest_db}' created successfully.")

        # --- 5. Execute schema script ---
        with pyodbc.connect(db_conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                print("Creating schema from 'schema.sql'...")
                with open(schema_file, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                    for command in sql_script.split('GO'):
                        if command.strip():
                            cursor.execute(command)
                print("-> Schema created successfully.")
                
                print("Disabling all foreign key constraints for bulk import...")
                cursor.execute("EXEC sp_msforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT all'")
                print("-> All foreign keys disabled.")

        # --- 6. Import ALL data with proper type conversion ---
        csv_files = sorted([f for f in os.listdir(data_dir) if f.endswith('.csv')])
        print(f"\nFound {len(csv_files)} CSV files to import.")

        for file_name in csv_files:
            table_name = os.path.splitext(file_name)[0]
            file_path = os.path.join(data_dir, file_name)
            
            print(f"Importing data for table: {table_name}...")
            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str, low_memory=False)
                df = df.where(pd.notna(df), None)

                # A. Remove IDENTITY columns
                if table_name in identity_tables:
                    identity_col = identity_tables[table_name]
                    if identity_col in df.columns:
                        print(f"   -> Removing IDENTITY column '{identity_col}'")
                        df = df.drop(columns=[identity_col])
                
                # B. Convert binary columns (DO NOT SKIP!)
                if table_name in binary_columns_map:
                    binary_col = binary_columns_map[table_name]
                    if binary_col in df.columns:
                        print(f"   -> Converting '{binary_col}' to binary (this may take time...)")
                        df[binary_col] = df[binary_col].apply(convert_binary)
                        # Remove rows where binary conversion failed
                        original_count = len(df)
                        df = df[df[binary_col].notna()]
                        if len(df) < original_count:
                            print(f"      Note: Skipped {original_count - len(df)} rows with invalid binary data")
                
                # C. Convert boolean columns
                if table_name in boolean_columns:
                    for col in boolean_columns[table_name]:
                        if col in df.columns:
                            print(f"   -> Converting '{col}' to boolean")
                            df[col] = df[col].apply(convert_boolean)
                
                # D. Convert integer columns
                if table_name in integer_columns:
                    for col in integer_columns[table_name]:
                        if col in df.columns:
                            print(f"   -> Converting '{col}' to integer")
                            df[col] = df[col].apply(convert_integer)
                
                # E. Import data (smaller chunks for binary data)
                chunk_size = 100 if table_name in binary_columns_map else 500
                df.to_sql(table_name, engine, if_exists='append', index=False, chunksize=chunk_size)
                print(f"-> Successfully imported {len(df)} rows into {table_name}.")

            except Exception as e:
                print(f"!! Error importing data for table {table_name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # --- 7. Validate and clean orphaned records ---
        print("\n=== Validating Foreign Key Relationships ===")
        with engine.connect() as conn:
            # Check and clean Chapter -> Manga
            result = conn.execute(text("""
                SELECT COUNT(*) FROM Chapter c
                LEFT JOIN Manga m ON c.MangaId = m.MangaId
                WHERE m.MangaId IS NULL
            """)).fetchone()
            
            if result[0] > 0:
                print(f"!! Found {result[0]} orphaned chapters. Cleaning up...")
                conn.execute(text("DELETE FROM Chapter WHERE MangaId NOT IN (SELECT MangaId FROM Manga)"))
                conn.commit()
                print("   -> Cleaned.")
            
            # Check and clean Comment -> Chapter
            result = conn.execute(text("""
                SELECT COUNT(*) FROM Comment c
                LEFT JOIN Chapter ch ON c.ChapterId = ch.ChapterId
                WHERE c.ChapterId IS NOT NULL AND ch.ChapterId IS NULL
            """)).fetchone()
            
            if result[0] > 0:
                print(f"!! Found {result[0]} orphaned comments. Cleaning up...")
                conn.execute(text("DELETE FROM Comment WHERE ChapterId IS NOT NULL AND ChapterId NOT IN (SELECT ChapterId FROM Chapter)"))
                conn.commit()
                print("   -> Cleaned.")
            
            # Check and clean CommentReaction -> Comment
            result = conn.execute(text("""
                SELECT COUNT(*) FROM CommentReaction cr
                LEFT JOIN Comment c ON cr.CommentId = c.CommentId
                WHERE c.CommentId IS NULL
            """)).fetchone()
            
            if result[0] > 0:
                print(f"!! Found {result[0]} orphaned comment reactions. Cleaning up...")
                conn.execute(text("DELETE FROM CommentReaction WHERE CommentId NOT IN (SELECT CommentId FROM Comment)"))
                conn.commit()
                print("   -> Cleaned.")

        # --- 8. Re-enable foreign key constraints ---
        print("\nRe-enabling all foreign key constraints...")
        with pyodbc.connect(db_conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute("EXEC sp_msforeachtable 'ALTER TABLE ? WITH CHECK CHECK CONSTRAINT all'")
        print("-> All foreign keys re-enabled.")
        
        # --- 9. Summary ---
        print("\n" + "="*60)
        print("✅ COMPLETE DATA MIGRATION SUCCESSFUL!")
        print("="*60)
        with engine.connect() as conn:
            tables_to_check = ['Chapter', 'Comment', 'Manga', 'User', 'Covers', 'MangaCover']
            for table in tables_to_check:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM [{table}]")).fetchone()
                    print(f"   {table}: {result[0]:,} rows")
                except:
                    pass
        print("="*60)

    except Exception as e:
        print(f"!! An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'engine' in locals():
            engine.dispose()
            print("Database engine disposed.")


if __name__ == "__main__":
    import_data_complete()