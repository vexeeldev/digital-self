import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'brain')))
import psycopg2
from ingestion import ingest_experience
from experience import ExperienceCreate
from llm_provider import get_llm_client

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

try:
    llm_client = get_llm_client()
    exp_create = ExperienceCreate(raw_text="Aku mencoba minum kopi.")
    print("Ingesting...")
    exp, saved_nodes, saved_assocs, assembly = ingest_experience(conn, exp_create, llm_client)
    conn.commit()
    print(f"Nodes: {len(saved_nodes)}")
    for n in saved_nodes:
        print(f" - {n.name}")
    print(f"Assocs: {len(saved_assocs)}")
    for a in saved_assocs:
        print(f" - {a.source_node_id} -> {a.target_node_id}")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    conn.close()
