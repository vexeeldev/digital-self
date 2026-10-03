"""
Tests for Initial Pattern Formation (V2.1)
"""

import os
import uuid
import pytest
import psycopg2
from pattern import form_patterns, MINIMUM_EVIDENCE
from models import AssociationType

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

def create_mock_association(conn, pos_ev, neg_ev, strength=0.5):
    """Helper to inject controlled test data without full ingestion flow."""
    exp_ids = [uuid.uuid4() for _ in range(pos_ev + neg_ev)]
    assoc_id = uuid.uuid4()
    src = uuid.uuid4()
    tgt = uuid.uuid4()
    
    with conn.cursor() as cur:
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', %s)", (str(src), str(src)))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', %s)", (str(tgt), str(tgt)))
        
        for exp in exp_ids:
            cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, 'x')", (str(exp),))
            
        source_exp = exp_ids[0] if exp_ids else uuid.uuid4()
        if not exp_ids:
            cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, 'x')", (str(source_exp),))
            
        cur.execute(
            """
            INSERT INTO associations (id, source_node_id, target_node_id, type, strength, positive_evidence, negative_evidence, source_experience_id)
            VALUES (%s, %s, %s, 'co_occurs_with', %s, %s, %s, %s)
            """,
            (str(assoc_id), str(src), str(tgt), strength, pos_ev, neg_ev, str(source_exp))
        )
        
        for i, exp in enumerate(exp_ids):
            is_pos = (i < pos_ev)
            cur.execute(
                """
                INSERT INTO experience_associations (experience_id, association_id, is_positive)
                VALUES (%s, %s, %s)
                """,
                (str(exp), str(assoc_id), is_pos)
            )
            
    return assoc_id, exp_ids

def test_pattern_minimum_evidence(db_connection):
    # Under minimum
    create_mock_association(db_connection, MINIMUM_EVIDENCE - 1, 0)
    pats = form_patterns(db_connection)
    assert len(pats) == 0
    
    # Exactly minimum
    assoc_id, _ = create_mock_association(db_connection, MINIMUM_EVIDENCE, 0)
    pats = form_patterns(db_connection)
    assert len(pats) == 1
    assert pats[0].association_id == assoc_id
    
    # Over minimum
    assoc_id_2, _ = create_mock_association(db_connection, MINIMUM_EVIDENCE + 2, 0)
    pats = form_patterns(db_connection)
    assert len(pats) == 2

def test_pattern_confidence_and_strength(db_connection):
    # 3 pos, 1 neg -> confidence = 3/4 = 0.75
    assoc_id, exps = create_mock_association(db_connection, 3, 1, 0.8)
    pats = form_patterns(db_connection, minimum_evidence=3)
    
    assert len(pats) == 1
    pat = pats[0]
    assert pat.evidence_count == 3
    assert pat.confidence == 0.75
    assert pat.association_strength == 0.8
    assert len(pat.supporting_experiences) == 4
    
    # 3 pos, 0 neg -> confidence = 1.0
    assoc_id2, _ = create_mock_association(db_connection, 3, 0)
    pats = form_patterns(db_connection, minimum_evidence=3)
    pat2 = next(p for p in pats if p.association_id == assoc_id2)
    assert pat2.confidence == 1.0

def test_pattern_zero_denominator(db_connection):
    assoc_id, _ = create_mock_association(db_connection, 0, 0)
    pats = form_patterns(db_connection, minimum_evidence=0)
    
    pat = next(p for p in pats if p.association_id == assoc_id)
    assert pat.confidence == 0.0

def test_pattern_relationships(db_connection):
    assoc_id, _ = create_mock_association(db_connection, 3, 0)
    pats = form_patterns(db_connection, minimum_evidence=3)
    assert pats[0].relationship_type == AssociationType.CO_OCCURS_WITH

def test_pattern_no_side_effects(db_connection):
    assoc_id, _ = create_mock_association(db_connection, 3, 0, 0.5)
    
    pats_1 = form_patterns(db_connection, minimum_evidence=3)
    pats_2 = form_patterns(db_connection, minimum_evidence=3)
    
    assert pats_1 == pats_2
    
    with db_connection.cursor() as cur:
        cur.execute("SELECT strength, positive_evidence FROM associations WHERE id = %s", (str(assoc_id),))
        row = cur.fetchone()
        assert float(row[0]) == 0.5
        assert int(row[1]) == 3

from pattern import form_assembly_patterns, AssemblyMemberStruct

def create_mock_assembly_evidence(conn, num_experiences, members_config, duplicate_exp=False):
    """
    members_config: list of dicts {'node_id': uuid, 'role': str, 'weight': float}
    """
    exp_ids = []
    with conn.cursor() as cur:
        for i in range(num_experiences):
            if duplicate_exp and i > 0:
                exp_id = exp_ids[0]
            else:
                exp_id = uuid.uuid4()
                cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, 'assembly text')", (str(exp_id),))
                exp_ids.append(exp_id)
                
            asm_id = uuid.uuid4()
            cur.execute("INSERT INTO assemblies (id, experience_id, context_summary) VALUES (%s, %s, 'test')", (str(asm_id), str(exp_id)))
            
            for m in members_config:
                # Use node_id as name to avoid unique name constraints
                cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', %s) ON CONFLICT (id) DO NOTHING", (str(m['node_id']), str(m['node_id'])))
                cur.execute("INSERT INTO assembly_members (assembly_id, node_id, role, weight) VALUES (%s, %s, %s, %s)",
                            (str(asm_id), str(m['node_id']), m['role'], m['weight']))
    return exp_ids

def test_assembly_pattern_minimum_evidence(db_connection):
    n1 = uuid.uuid4()
    n2 = uuid.uuid4()
    config = [
        {'node_id': n1, 'role': 'context', 'weight': 1.0},
        {'node_id': n2, 'role': 'participant', 'weight': 0.8}
    ]
    
    # Under minimum
    create_mock_assembly_evidence(db_connection, MINIMUM_EVIDENCE - 1, config)
    pats = form_assembly_patterns(db_connection, minimum_evidence=MINIMUM_EVIDENCE)
    assert len(pats) == 0
    
    # Minimum met
    create_mock_assembly_evidence(db_connection, 1, config)
    pats = form_assembly_patterns(db_connection, minimum_evidence=MINIMUM_EVIDENCE)
    assert len(pats) == 1
    assert pats[0].evidence_count == MINIMUM_EVIDENCE
    assert pats[0].confidence == 1.0

def test_assembly_pattern_ordering_identity(db_connection):
    n1 = uuid.uuid4()
    n2 = uuid.uuid4()
    configA = [
        {'node_id': n1, 'role': 'context', 'weight': 1.0},
        {'node_id': n2, 'role': 'participant', 'weight': 0.8}
    ]
    configB = [
        {'node_id': n2, 'role': 'participant', 'weight': 0.8},
        {'node_id': n1, 'role': 'context', 'weight': 1.0}
    ]
    
    create_mock_assembly_evidence(db_connection, 2, configA)
    create_mock_assembly_evidence(db_connection, 1, configB)
    
    pats = form_assembly_patterns(db_connection, minimum_evidence=3)
    assert len(pats) == 1
    assert pats[0].evidence_count == 3

def test_assembly_pattern_different_config(db_connection):
    n1 = uuid.uuid4()
    n2 = uuid.uuid4()
    configA = [{'node_id': n1, 'role': 'role1', 'weight': 1.0}]
    configB = [{'node_id': n1, 'role': 'role2', 'weight': 1.0}]
    configC = [{'node_id': n1, 'role': 'role1', 'weight': 0.5}]
    configD = [{'node_id': n2, 'role': 'role1', 'weight': 1.0}]
    
    create_mock_assembly_evidence(db_connection, 3, configA)
    create_mock_assembly_evidence(db_connection, 3, configB)
    create_mock_assembly_evidence(db_connection, 3, configC)
    create_mock_assembly_evidence(db_connection, 3, configD)
    
    pats = form_assembly_patterns(db_connection, minimum_evidence=3)
    assert len(pats) == 4

import psycopg2.errors

def test_assembly_pattern_duplicate_evidence(db_connection):
    n1 = uuid.uuid4()
    config = [{'node_id': n1, 'role': 'r1', 'weight': 1.0}]
    
    # DB explicitly prevents duplicate assemblies for the same experience
    # which structurally guarantees deduplication
    with pytest.raises(psycopg2.errors.UniqueViolation):
        create_mock_assembly_evidence(db_connection, 3, config, duplicate_exp=True)
