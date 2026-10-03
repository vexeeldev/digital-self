import os
import psycopg2

DB_USER = os.getenv("DB_USER", "malakul-tech")
DB_NAME = os.getenv("DB_NAME", "digital_self")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")

conn = psycopg2.connect(
    user=DB_USER,
    dbname=DB_NAME,
    host=DB_HOST,
    port=DB_PORT
)
cur = conn.cursor()

try:
    print("Truncating tables...")
    cur.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    if tables:
        # Don't truncate schema_migrations or similar if they exist, but here we probably want to clear all data tables
        table_list = ", ".join(tables)
        print(f"Tables to truncate: {table_list}")
        cur.execute(f"TRUNCATE TABLE {table_list} CASCADE;")
        conn.commit()
        print("Database cleared successfully!")
    else:
        print("No tables found.")
except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
finally:
    cur.close()
    conn.close()
