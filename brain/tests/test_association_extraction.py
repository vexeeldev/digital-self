"""
Tests for Association Extraction (V2.1)
"""

import os
import uuid
import pytest
import psycopg2

from models import Experience, Node, NodeType, AssociationType, AssociationCreate
from extraction import extract_associations, save_extracted_associations

DB_USER = os.getenv("DB_USER", "malakul-tech")
DB_NAME = os.getenv("DB_NAME", "digital_self")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")

@pytest.fixture(scope="function")
def db_connection():
    conn = psycopg2.connect(
        user=DB_USER,
        dbname=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )
    yield conn
    conn.rollback()
    conn.close()

def test_extract_associations_valid_fake():
    exp = Experience(
        id=uuid.uuid4(),
        raw_text="Tadi di kantor temanku sepatunya agak bau."
    )
    nodes = [
        Node(id=uuid.uuid4(), type=NodeType.PERSON, name="teman"),
        Node(id=uuid.uuid4(), type=NodeType.PLACE, name="kantor"),
        Node(id=uuid.uuid4(), type=NodeType.OBJECT, name="sepatu"),
        Node(id=uuid.uuid4(), type=NodeType.CONCEPT, name="bau")
    ]
    
    assocs = extract_associations(exp, nodes, llm_client=None)
    
    assert len(assocs) == 3
    # Check types and properties
    for a in assocs:
        assert isinstance(a.type, AssociationType)
        assert 0.0 <= a.confidence <= 1.0
        assert a.source_node_id != a.target_node_id
        assert a.source_experience_id == exp.id

def test_extract_associations_ignores_missing_nodes():
    exp = Experience(
        id=uuid.uuid4(),
        raw_text="Tadi di kantor temanku sepatunya agak bau."
    )
    # Give it only 1 node, so the mock LLM output won't match the nodes dict
    nodes = [Node(id=uuid.uuid4(), type=NodeType.PERSON, name="teman")]
    
    assocs = extract_associations(exp, nodes, llm_client=None)
    
    # Should be empty because it requires BOTH source and target to be in the provided list
    assert len(assocs) == 0

def test_extract_associations_empty_text():
    exp = Experience(id=uuid.uuid4(), raw_text="   ")
    nodes = [Node(id=uuid.uuid4(), type=NodeType.PERSON, name="teman")]
    assocs = extract_associations(exp, nodes, llm_client=None)
    assert len(assocs) == 0

def test_save_extracted_associations(db_connection):
    # Need an experience and two nodes in DB
    exp_id = uuid.uuid4()
    n1_id = uuid.uuid4()
    n2_id = uuid.uuid4()
    
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id), "text"))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'person', 'teman')", (str(n1_id),))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'place', 'kantor')", (str(n2_id),))
        
    assocs_in = [
        AssociationCreate(
            source_node_id=n1_id,
            target_node_id=n2_id,
            type=AssociationType.LOCATED_AT,
            confidence=0.9,
            source_experience_id=exp_id
        )
    ]
    
    saved = save_extracted_associations(db_connection, exp_id, assocs_in)
    
    assert len(saved) == 1
    assert saved[0].source_node_id == n1_id
    assert saved[0].target_node_id == n2_id
    assert saved[0].type == AssociationType.LOCATED_AT
    assert saved[0].confidence == 0.9
    
    # Check experience_associations bridge
    with db_connection.cursor() as cur:
        cur.execute("SELECT is_positive FROM experience_associations WHERE experience_id = %s AND association_id = %s", 
                    (str(exp_id), str(saved[0].id)))
        row = cur.fetchone()
        
    assert row is not None
    assert row[0] is True  # is_positive

def test_save_duplicate_association_handles_gracefully(db_connection):
    exp_id = uuid.uuid4()
    exp_id_2 = uuid.uuid4()
    n1_id = uuid.uuid4()
    n2_id = uuid.uuid4()
    
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id), "text1"))
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id_2), "text2"))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'person', 'teman')", (str(n1_id),))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'place', 'kantor')", (str(n2_id),))
        
    assoc_in = AssociationCreate(
        source_node_id=n1_id,
        target_node_id=n2_id,
        type=AssociationType.LOCATED_AT,
        confidence=0.9,
        source_experience_id=exp_id
    )
    
    # Save once
    saved1 = save_extracted_associations(db_connection, exp_id, [assoc_in])
    assert len(saved1) == 1
    assoc_id = saved1[0].id
    
    # Create the exact same directed association again but from a different experience
    assoc_in_2 = AssociationCreate(
        source_node_id=n1_id,
        target_node_id=n2_id,
        type=AssociationType.LOCATED_AT,
        confidence=0.8,
        source_experience_id=exp_id_2
    )
    
    # Save again - it should not create a new association (because of UNIQUE constraint)
    # but it SHOULD create a new experience_associations link
    saved2 = save_extracted_associations(db_connection, exp_id_2, [assoc_in_2])
    assert len(saved2) == 0  # No brand NEW associations returned
    
    # Check experience_associations - should have 2 links for assoc_id
    with db_connection.cursor() as cur:
        cur.execute("SELECT experience_id FROM experience_associations WHERE association_id = %s", (str(assoc_id),))
        rows = cur.fetchall()
        
    assert len(rows) == 2
    exp_ids = {row[0] for row in rows}
    assert str(exp_id) in exp_ids
    assert str(exp_id_2) in exp_ids
