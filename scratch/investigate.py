import os
os.environ["DIGITAL_SELF_LLM_PROVIDER"] = "antigravity_cli"
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'brain'))

import asyncio
import logging
from pprint import pprint
import psycopg2

from models import ExperienceCreate
from ingestion import ingest_experience
from llm_provider import get_llm_client

logging.basicConfig(level=logging.DEBUG)

def run():
    print("=== START INVESTIGATION ===")
    
    provider = get_llm_client()
    print(f"Provider: {provider.__class__.__name__}")
    print(f"Is Enabled: {provider.is_enabled()}")
    
    # Check API KEY
    print(f"GEMINI_API_KEY set: {'GEMINI_API_KEY' in os.environ}")
    
    raw_text = "Kemarin sore aku pulang dari kampus agak terlambat karena menyelesaikan tugas. Di perjalanan aku mampir membeli roti dan air mineral. Setelah sampai rumah, aku langsung menaruh barang di meja, membuka laptop, lalu melanjutkan tugas sampai malam. Aku sempat merasa lelah, tetapi tetap ingin menyelesaikannya sebelum tidur."
    exp_create = ExperienceCreate(raw_text=raw_text)
    
    conn = psycopg2.connect("dbname=digital_self user=malakul-tech")
    conn.autocommit = False
    
    try:
        from extraction import extract_nodes, extract_associations
        nodes_in = extract_nodes(exp_create, llm_client=provider)
        
        print("\n--- NODES EXTRACTED ---")
        print(f"Count: {len(nodes_in)}")
        for n in nodes_in:
            print(f"- {n.name} ({n.type})")
            
        assocs_in = extract_associations(exp_create, nodes_in, llm_client=provider)
        
        print("\n--- ASSOCIATIONS EXTRACTED ---")
        print(f"Count: {len(assocs_in)}")
        for a in assocs_in:
            print(f"- {a.source} -> {a.type} -> {a.target}")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    run()
