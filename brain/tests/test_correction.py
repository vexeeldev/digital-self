import uuid
import os
import psycopg2
import pytest
from models import AssociationType
from correction import emit_association_correction, emit_assembly_member_correction, add_human_association

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

def test_add_human_association_new(db_connection):
    cur = db_connection.cursor()
    # Create nodes
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('test exp') RETURNING id")
    exp_id = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Alice_{uuid.uuid4().hex}",))
    src = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Bob_{uuid.uuid4().hex}",))
    tgt = cur.fetchone()[0]
    db_connection.commit()

    assoc_id = add_human_association(db_connection, uuid.UUID(exp_id), uuid.UUID(src), uuid.UUID(tgt), AssociationType.CO_OCCURS_WITH)
    db_connection.commit()

    cur.execute("SELECT id FROM experience_associations WHERE experience_id = %s", (exp_id,))
    ea_id = cur.fetchone()[0]
    
    cur.execute("SELECT operation FROM experience_association_corrections WHERE experience_association_id = %s", (ea_id,))
    assert cur.fetchone()[0] == 'ADD'
    
    cur.execute("SELECT positive_evidence FROM associations WHERE id = %s", (str(assoc_id),))
    assert cur.fetchone()[0] == 1

def test_reject_and_restore_association(db_connection):
    cur = db_connection.cursor()
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('test exp 2') RETURNING id")
    exp_id = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Charlie_{uuid.uuid4().hex}",))
    src = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Dave_{uuid.uuid4().hex}",))
    tgt = cur.fetchone()[0]
    
    # Simulate system extraction
    cur.execute("INSERT INTO associations (source_node_id, target_node_id, type, source_experience_id) VALUES (%s, %s, 'co_occurs_with', %s) RETURNING id", (src, tgt, exp_id))
    assoc_id = cur.fetchone()[0]
    cur.execute("INSERT INTO experience_associations (experience_id, association_id, is_positive) VALUES (%s, %s, true) RETURNING id", (exp_id, assoc_id))
    ea_id = cur.fetchone()[0]
    db_connection.commit()
    
    # Reject
    emit_association_correction(db_connection, uuid.UUID(ea_id), 'REJECT')
    db_connection.commit()
    
    cur.execute("SELECT positive_evidence FROM associations WHERE id = %s", (assoc_id,))
    assert cur.fetchone()[0] == 0
    
    # Try adding existing link - should RESTORE
    add_human_association(db_connection, uuid.UUID(exp_id), uuid.UUID(src), uuid.UUID(tgt), AssociationType.CO_OCCURS_WITH)
    db_connection.commit()
    
    cur.execute("SELECT operation FROM experience_association_corrections WHERE experience_association_id = %s ORDER BY event_sequence DESC LIMIT 1", (ea_id,))
    assert cur.fetchone()[0] == 'RESTORE'
    
    cur.execute("SELECT positive_evidence FROM associations WHERE id = %s", (assoc_id,))
    assert cur.fetchone()[0] == 1

def test_add_active_existing_link_fails(db_connection):
    cur = db_connection.cursor()
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('test exp 3') RETURNING id")
    exp_id = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Eve_{uuid.uuid4().hex}",))
    src = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Frank_{uuid.uuid4().hex}",))
    tgt = cur.fetchone()[0]
    
    cur.execute("INSERT INTO associations (source_node_id, target_node_id, type, source_experience_id) VALUES (%s, %s, 'co_occurs_with', %s) RETURNING id", (src, tgt, exp_id))
    assoc_id = cur.fetchone()[0]
    cur.execute("INSERT INTO experience_associations (experience_id, association_id, is_positive) VALUES (%s, %s, true) RETURNING id", (exp_id, assoc_id))
    db_connection.commit()
    
    with pytest.raises(ValueError, match="Active existing link"):
        add_human_association(db_connection, uuid.UUID(exp_id), uuid.UUID(src), uuid.UUID(tgt), AssociationType.CO_OCCURS_WITH)

def test_assembly_member_correction(db_connection):
    cur = db_connection.cursor()
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('test') RETURNING id")
    exp_id = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Z_{uuid.uuid4().hex}",))
    node_id = cur.fetchone()[0]
    cur.execute("INSERT INTO assemblies (experience_id, context_summary) VALUES (%s, 'test context') RETURNING id", (exp_id,))
    asm_id = cur.fetchone()[0]
    cur.execute("INSERT INTO assembly_members (assembly_id, node_id, role, weight) VALUES (%s, %s, 'participant', 1.0) RETURNING id", (asm_id, node_id))
    mem_id = cur.fetchone()[0]
    db_connection.commit()
    
    # Reject
    emit_assembly_member_correction(db_connection, uuid.UUID(mem_id), 'REJECT')
    db_connection.commit()
    
    cur.execute("SELECT id FROM vw_active_assembly_members WHERE id = %s", (mem_id,))
    assert cur.fetchone() is None
    
    # Restore
    emit_assembly_member_correction(db_connection, uuid.UUID(mem_id), 'RESTORE')
    db_connection.commit()
    
    cur.execute("SELECT id FROM vw_active_assembly_members WHERE id = %s", (mem_id,))
    assert cur.fetchone() is not None
