import os
import psycopg2

DB_USER = os.getenv("DB_USER", "malakul-tech")
DB_NAME = os.getenv("DB_NAME", "digital_self")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db():
    conn = psycopg2.connect(
        user=DB_USER,
        dbname=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )
    try:
        yield conn
    finally:
        conn.close()
