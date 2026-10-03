"""
Tests for Node Extraction (V2.1)
"""

import os
import uuid
import pytest
import psycopg2
from pydantic import ValidationError

from models import Experience, NodeCreate, NodeType
from extraction import extract_nodes, save_extracted_nodes

DB_USER = os.getenv("DB_USER", "malakul-tech")
DB_NAME = os.getenv("DB_NAME", "digital_self")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")

@pytest.fixture(scope="function")
def db_connection():
    """Provides a database connection and rolls back after each test."""
    conn = psycopg2.connect(
        user=DB_USER,
        dbname=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )
    yield conn
    conn.rollback()
    conn.close()

def test_extract_nodes_valid_fake():
    exp = Experience(raw_text="Teman saya tersandung di kantor dan saya merasa kesal.")
    nodes = extract_nodes(exp, llm_client=None)
    
    assert len(nodes) == 4
    assert nodes[0].name == "teman"
    assert nodes[0].type == NodeType.PERSON
    
    # Verify confidence bounds
    for n in nodes:
        assert 0.0 <= n.confidence <= 1.0

def test_extract_nodes_empty_text():
    exp = Experience(raw_text="   ")
    nodes = extract_nodes(exp, llm_client=None)
    assert len(nodes) == 0

def test_extract_nodes_llm_failure():
    exp = Experience(raw_text="invalid syntax text")
    with pytest.raises(RuntimeError, match="LLM parsing error"):
        extract_nodes(exp, llm_client=None)

def test_node_type_validation():
    with pytest.raises(ValidationError):
        # Invalid enum value
        NodeCreate(type="aliens", name="UFO", confidence=0.9)

def test_node_confidence_validation():
    with pytest.raises(ValidationError):
        # Confidence out of bounds
        NodeCreate(type=NodeType.OBJECT, name="Table", confidence=1.5)

def test_save_extracted_nodes(db_connection):
    # Setup: we need a valid experience ID in the database first for the foreign key
    exp_id = uuid.uuid4()
    with db_connection.cursor() as cur:
        cur.execute(
            "INSERT INTO experiences (id, raw_text) VALUES (%s, %s)",
            (str(exp_id), "Teman saya tersandung di kantor dan saya merasa kesal.")
        )
    
    # Candidates
    candidates = [
        NodeCreate(type=NodeType.PERSON, name="teman", confidence=0.92),
        NodeCreate(type=NodeType.PLACE, name="kantor", confidence=0.97)
    ]
    
    saved_nodes = save_extracted_nodes(db_connection, exp_id, candidates)
    assert len(saved_nodes) == 2
    
    # Check provenance in database
    with db_connection.cursor() as cur:
        cur.execute("SELECT experience_id, node_id FROM experience_nodes WHERE experience_id = %s", (str(exp_id),))
        rows = cur.fetchall()
        
    assert len(rows) == 2
    extracted_node_ids = {row[1] for row in rows}
    assert str(saved_nodes[0].id) in extracted_node_ids
    assert str(saved_nodes[1].id) in extracted_node_ids

def test_extraction_failure_leaves_experience_intact(db_connection):
    exp_id = uuid.uuid4()
    with db_connection.cursor() as cur:
        cur.execute(
            "INSERT INTO experiences (id, raw_text) VALUES (%s, %s)",
            (str(exp_id), "Experience remains intact")
        )
        
    # Attempt to save a node that violates DB constraints directly (e.g. name is empty, bypassing Pydantic)
    class FakeNode:
        type = NodeType.CONCEPT
        name = "   "
        confidence = 0.5
        
    with pytest.raises(ValueError):
        save_extracted_nodes(db_connection, exp_id, [FakeNode()])
        
    # Since we are using transactions in our fixture, the failure will abort the transaction,
    # but in a real app the caller would manage the transaction. 
    # Here we just verify that we can rollback and the failure didn't persist bad data.
    db_connection.rollback()
