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
    # Get the latest experience
    cur.execute("SELECT id, raw_text FROM experiences ORDER BY created_at DESC;")
    exps = cur.fetchall()
    for exp in exps:
        exp_id = exp[0]
        cur.execute("""
            SELECT node_id FROM experience_nodes WHERE experience_id = %s
        """, (str(exp_id),))
        raw_nodes = cur.fetchall()
        print(f"Exp {exp_id} - {exp[1][:30]}... Nodes: {len(raw_nodes)}")
finally:
    cur.close()
    conn.close()
