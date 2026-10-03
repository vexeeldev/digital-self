"""
Tests for Association Learning (V2.1)
"""

import os
import uuid
import pytest
import psycopg2

from learning import (
    record_positive_evidence, 
    record_negative_evidence, 
    apply_decay, 
    ALPHA, BETA, DECAY_LAMBDA
)

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

def setup_data(conn):
    """Creates a basic experience, nodes, and an association."""
    exp_id = uuid.uuid4()
    n1_id = uuid.uuid4()
    n2_id = uuid.uuid4()
    
    with conn.cursor() as cur:
        # We need an experience for the initial association provenance
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id), "text0"))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'person', 'teman')", (str(n1_id),))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'place', 'kantor')", (str(n2_id),))
        
        # Insert initial association
        cur.execute(
            """
            INSERT INTO associations (source_node_id, target_node_id, type, strength, positive_evidence, negative_evidence, source_experience_id)
            VALUES (%s, %s, 'co_occurs_with', 0.5, 1, 0, %s)
            RETURNING id;
            """,
            (str(n1_id), str(n2_id), str(exp_id))
        )
        assoc_id = cur.fetchone()[0]
        
    return assoc_id, exp_id

def test_params_loaded():
    assert ALPHA == 0.20
    assert BETA == 0.10
    assert DECAY_LAMBDA == 0.01

def test_apply_decay():
    assert apply_decay(1.0, 0.01, 0) == 1.0
    assert apply_decay(1.0, 0.01, 100) == pytest.approx(0.367879, abs=1e-4) # e^-1
    
def test_positive_evidence(db_connection):
    assoc_id, orig_exp_id = setup_data(db_connection)
    
    # New experience
    exp_id = uuid.uuid4()
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id), "pos text"))
        
    # Initial state is s=0.5, pos=1, neg=0
    record_positive_evidence(db_connection, assoc_id, exp_id, weight=1.0)
    
    with db_connection.cursor() as cur:
        cur.execute("SELECT strength, positive_evidence, negative_evidence FROM associations WHERE id = %s", (str(assoc_id),))
        row = cur.fetchone()
        
    s_new = float(row[0])
    pos_ev = row[1]
    neg_ev = row[2]
    
    # Formula: 0.5 + 0.2 * 1 * (1 - 0.5) = 0.5 + 0.1 = 0.6
    assert pytest.approx(s_new, 0.001) == 0.6
    assert pos_ev == 2
    assert neg_ev == 0

def test_negative_evidence(db_connection):
    assoc_id, orig_exp_id = setup_data(db_connection)
    
    # New experience
    exp_id = uuid.uuid4()
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id), "neg text"))
        
    # Initial state is s=0.5, pos=1, neg=0
    record_negative_evidence(db_connection, assoc_id, exp_id, weight=1.0)
    
    with db_connection.cursor() as cur:
        cur.execute("SELECT strength, positive_evidence, negative_evidence FROM associations WHERE id = %s", (str(assoc_id),))
        row = cur.fetchone()
        
    s_new = float(row[0])
    pos_ev = row[1]
    neg_ev = row[2]
    
    # Formula: 0.5 - 0.1 * 1 * 0.5 = 0.5 - 0.05 = 0.45
    assert pytest.approx(s_new, 0.001) == 0.45
    assert pos_ev == 1
    assert neg_ev == 1
    
def test_double_evidence_from_same_experience_is_ignored(db_connection):
    assoc_id, orig_exp_id = setup_data(db_connection)
    
    exp_id = uuid.uuid4()
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id), "dup text"))
        
    record_positive_evidence(db_connection, assoc_id, exp_id, weight=1.0)
    record_positive_evidence(db_connection, assoc_id, exp_id, weight=1.0) # Should be ignored
    
    with db_connection.cursor() as cur:
        cur.execute("SELECT strength, positive_evidence FROM associations WHERE id = %s", (str(assoc_id),))
        row = cur.fetchone()
        
    # Should only increment once
    assert pytest.approx(float(row[0]), 0.001) == 0.6
    assert row[1] == 2

def test_invalid_weight(db_connection):
    assoc_id, orig_exp_id = setup_data(db_connection)
    exp_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="must be > 0"):
        record_positive_evidence(db_connection, assoc_id, exp_id, weight=0.0)

def test_bounds_respected(db_connection):
    assoc_id, orig_exp_id = setup_data(db_connection)
    exp_id = uuid.uuid4()
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id), "text"))
        
    # massive weight to push beyond 1.0
    record_positive_evidence(db_connection, assoc_id, exp_id, weight=100.0)
    
    with db_connection.cursor() as cur:
        cur.execute("SELECT strength FROM associations WHERE id = %s", (str(assoc_id),))
        s_new = float(cur.fetchone()[0])
        
    assert s_new == 1.0
    
    exp_id_2 = uuid.uuid4()
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id_2), "text"))
        
    # massive weight to push below 0.0
    record_negative_evidence(db_connection, assoc_id, exp_id_2, weight=100.0)
    
    with db_connection.cursor() as cur:
        cur.execute("SELECT strength FROM associations WHERE id = %s", (str(assoc_id),))
        s_new_2 = float(cur.fetchone()[0])
        
    assert s_new_2 == 0.0
