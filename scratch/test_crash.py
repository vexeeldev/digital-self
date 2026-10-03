import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../brain"))

from ingestion import ingest_experience
from experience import ExperienceCreate
from llm_provider import get_llm_client
from api.deps import get_db

def test():
    db_gen = get_db()
    conn = next(db_gen)
    llm = get_llm_client()
    try:
        exp, nodes, assocs, assembly = ingest_experience(
            conn, 
            ExperienceCreate(raw_text="jujur ini agak menyedihkan ya sih kakaknya pacarku meninggal"), 
            llm_client=llm
        )
        print("Success!")
        print("Nodes:", len(nodes))
        for n in nodes:
            print(" -", n.name)
        print("Assocs:", len(assocs))
        for a in assocs:
            print(" -", a.source_node_id, "->", a.target_node_id)
        # Rollback so we don't save this duplicate
        conn.rollback()
    except Exception as e:
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        db_gen.close()

test()
