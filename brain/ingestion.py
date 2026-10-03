"""
Digital Self — ingestion.py
Version: V2.1

End-to-end pipeline for memory ingestion (Stage 1-15).
Connects Experience, Node Extraction, Resolution, Association Extraction, and Assembly.
"""
from psycopg2.extensions import connection

from models import ExperienceCreate
from experience import save_experience
from extraction import extract_nodes, save_extracted_nodes, extract_associations, save_extracted_associations
from assembly import extract_assembly, save_assembly

def ingest_experience(conn: connection, exp_create: ExperienceCreate, llm_client=None):
    """
    Ingests a raw experience, extracting nodes, associations, and an assembly.
    Does not silently skip errors; failures will bubble up so the caller can rollback.
    """
    # 1. Save Experience (Immutable)
    exp = save_experience(conn, exp_create)
    
    # 2. Extract and Save Nodes (Resolution handles canonical mapping)
    nodes_in = extract_nodes(exp, llm_client)
    saved_nodes = save_extracted_nodes(conn, exp.id, nodes_in)
    
    # 3. Extract and Save Associations
    assocs_in = extract_associations(exp, saved_nodes, llm_client)
    saved_assocs = save_extracted_associations(conn, exp.id, assocs_in)
    
    # 4. Extract and Save Assembly
    extraction = extract_assembly(exp, saved_nodes, llm_client)
    assembly = save_assembly(conn, exp.id, extraction, saved_nodes)
    
    return exp, saved_nodes, saved_assocs, assembly
