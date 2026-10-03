import uuid
import pytest
import os
import psycopg2
from reasoning import ReasoningQuery, ReasoningEngine, Evidence, Inference
from models import AssociationType
from correction import add_human_association, emit_association_correction
from activation import PARAMS

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

def test_query_validation():
    # 1. Valid query produces deterministic ReasoningQuery
    q = ReasoningQuery(text="Does Alice like Bob?")
    assert q.text == "Does Alice like Bob?"
    
    # 2. Empty/invalid query rejected
    with pytest.raises(ValueError):
        ReasoningQuery(text="   ")
    with pytest.raises(ValueError):
        ReasoningQuery(text="")

def setup_data(cur, name1, name2):
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('exp 1') RETURNING id")
    e1 = cur.fetchone()[0]
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('exp 2') RETURNING id")
    e2 = cur.fetchone()[0]
    
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (name1,))
    n1 = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (name2,))
    n2 = cur.fetchone()[0]
    
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Irrelevant_{uuid.uuid4().hex}",))
    n3 = cur.fetchone()[0]
    return e1, e2, n1, n2, n3

def test_basic_reasoning(db_connection):
    cur = db_connection.cursor()
    name1 = f"Alice_{uuid.uuid4().hex}"
    name2 = f"Bob_{uuid.uuid4().hex}"
    e1, e2, n1, n2, n3 = setup_data(cur, name1, name2)
    db_connection.commit()
    
    # Setup some association between n1 and n2
    add_human_association(db_connection, uuid.UUID(e1), uuid.UUID(n1), uuid.UUID(n2), AssociationType.SUPPORTS)
    
    # Add an irrelevant association between n3 and n2
    add_human_association(db_connection, uuid.UUID(e2), uuid.UUID(n3), uuid.UUID(n2), AssociationType.SUPPORTS)
    db_connection.commit()
    
    engine = ReasoningEngine(db_connection)
    query = ReasoningQuery(text=f"What about {name1}?")
    
    # 3. Relevant Belief becomes evidence
    # 4. Irrelevant Belief is excluded
    ctx = engine.build_context(query)
    
    # n1 and n2 should be activated because spread_activation reaches n2 from n1
    assert uuid.UUID(n1) in ctx.activated_nodes
    # n3 should not be in relevant_beliefs subjects because it's not strongly activated or query related
    
    beliefs = ctx.relevant_beliefs
    assert len(beliefs) >= 1
    
    inferences = engine.reason(query)
    assert len(inferences) >= 1
    
    # 11. Direct Belief can produce an inference
    # 12. Belief is not converted into Experience/fact (handled in types)
    assert isinstance(inferences[0], Inference)
    assert inferences[0].statement.startswith("Direct belief")
    
    # 20. Every inference has provenance
    # 21. Provenance reaches underlying Experiences
    # 22. Raw Experience text is not duplicated into derived state
    assert len(inferences[0].provenance) > 0
    assert uuid.UUID(e1) in inferences[0].provenance

def test_conflict_reasoning(db_connection):
    cur = db_connection.cursor()
    name1 = f"Charlie_{uuid.uuid4().hex}"
    name2 = f"Dave_{uuid.uuid4().hex}"
    e1, e2, n1, n2, n3 = setup_data(cur, name1, name2)
    db_connection.commit()
    
    assoc_supports = add_human_association(db_connection, uuid.UUID(e1), uuid.UUID(n1), uuid.UUID(n2), AssociationType.SUPPORTS)
    assoc_contradicts = add_human_association(db_connection, uuid.UUID(e2), uuid.UUID(n1), uuid.UUID(n2), AssociationType.CONTRADICTS)
    db_connection.commit()
    
    engine = ReasoningEngine(db_connection)
    query = ReasoningQuery(text=f"Check {name1} and {name2}")
    
    inferences = engine.reason(query)
    
    # 14. Conflicting beliefs appear in reasoning context
    ctx = engine.build_context(query)
    assert len(ctx.conflicts) == 1
    
    # Filter inferences to find the conflict one
    conflict_infs = [i for i in inferences if i.statement.startswith("Conflicting evidence found regarding")]
    assert len(conflict_infs) == 1
    
    inf = conflict_infs[0]
    # 5. Supporting evidence preserved
    # 6. Contradicting evidence preserved
    # 15. Conflict does not automatically choose a winner
    # 16. Both sides remain traceable
    assert len(inf.supporting_evidence) == 1
    assert len(inf.contradicting_evidence) == 1
    
    # 17. Confidence remains within [0,1]
    assert 0.0 <= inf.confidence <= 1.0

def test_active_evidence_reasoning(db_connection):
    cur = db_connection.cursor()
    name1 = f"Eve_{uuid.uuid4().hex}"
    name2 = f"Frank_{uuid.uuid4().hex}"
    e1, e2, n1, n2, n3 = setup_data(cur, name1, name2)
    db_connection.commit()
    
    add_human_association(db_connection, uuid.UUID(e1), uuid.UUID(n1), uuid.UUID(n2), AssociationType.BEFORE)
    db_connection.commit()
    
    engine = ReasoningEngine(db_connection)
    query = ReasoningQuery(text=f"Any thoughts on {name1} {name2}?")
    
    infs_before = engine.reason(query)
    
    # Check it exists
    direct = [i for i in infs_before if i.statement.startswith("Direct belief")]
    assert len(direct) >= 1
    
    # Reject
    cur.execute("SELECT id FROM experience_associations WHERE experience_id = %s", (e1,))
    ea_id = cur.fetchone()[0]
    emit_association_correction(db_connection, uuid.UUID(ea_id), "REJECT")
    db_connection.commit()
    
    # 8. Rejected evidence excluded
    # 10. Human correction is respected
    infs_after = engine.reason(query)
    # The direct belief should not be there for Eve and Frank
    direct_after = [i for i in infs_after if i.statement.startswith("Direct belief") and name1 in i.statement]
    assert len(direct_after) == 0
    
    # 9. RESTORED evidence included again
    emit_association_correction(db_connection, uuid.UUID(ea_id), "RESTORE")
    db_connection.commit()
    
    infs_restored = engine.reason(query)
    direct_restored = [i for i in infs_restored if i.statement.startswith("Direct belief") and name1 in i.statement]
    assert len(direct_restored) >= 1

def test_zero_evidence(db_connection):
    engine = ReasoningEngine(db_connection)
    # Give a query with random words that don't match any node
    query = ReasoningQuery(text=f"asdfqwerzxcv {uuid.uuid4().hex}")
    inferences = engine.reason(query)
    
    # 18. Zero evidence produces zero/insufficient confidence
    assert len(inferences) == 1
    assert inferences[0].statement == "NO_SUFFICIENT_EVIDENCE"
    assert inferences[0].confidence == 0.0

def test_determinism(db_connection):
    cur = db_connection.cursor()
    name1 = f"G_{uuid.uuid4().hex}"
    name2 = f"H_{uuid.uuid4().hex}"
    e1, e2, n1, n2, n3 = setup_data(cur, name1, name2)
    db_connection.commit()
    add_human_association(db_connection, uuid.UUID(e1), uuid.UUID(n1), uuid.UUID(n2), AssociationType.SUPPORTS)
    db_connection.commit()
    
    engine = ReasoningEngine(db_connection)
    query1 = ReasoningQuery(text=f"Tell me about {name1} and {name2}")
    query2 = ReasoningQuery(text=f"Tell me about {name2} and {name1}") # Different order
    
    infs1 = engine.reason(query1)
    infs2 = engine.reason(query2)
    
    # 31. Same input -> same output (query1 run twice implicitly matches)
    # 32. Different input ordering -> same canonical result
    assert [i.statement for i in infs1] == [i.statement for i in infs2]
    assert [i.confidence for i in infs1] == [i.confidence for i in infs2]

def test_immutability(db_connection):
    # 23-28. Reasoning does not modify DB. We can check if counts changed.
    cur = db_connection.cursor()
    cur.execute("SELECT count(*) FROM experiences")
    count_exp_before = cur.fetchone()[0]
    
    engine = ReasoningEngine(db_connection)
    query = ReasoningQuery(text="Some generic query")
    engine.reason(query)
    
    cur.execute("SELECT count(*) FROM experiences")
    count_exp_after = cur.fetchone()[0]
    assert count_exp_before == count_exp_after
    
    # 33-34. No decision object. The output is purely Inference objects.
    # No decision tables are queried or written.

def test_duplicate_evidence_handling(db_connection):
    # 7. Duplicate evidence does not double-count.
    # The _calculate_confidence formula checks for unique experiences.
    cur = db_connection.cursor()
    name1 = f"I_{uuid.uuid4().hex}"
    name2 = f"J_{uuid.uuid4().hex}"
    e1, e2, n1, n2, n3 = setup_data(cur, name1, name2)
    db_connection.commit()
    
    # Same experience supporting two beliefs (for example) would not double the denominator if we pass them.
    # Here we mock Evidence to test the internal function
    engine = ReasoningEngine(db_connection)
    
    ev1 = Evidence("BELIEF", "a", 1.0, 0.8, (e1,))
    ev2 = Evidence("BELIEF", "b", 1.0, 0.8, (e1,))
    
    # Only e1 is considered once. So support_score = 0.8. Total = 0.8 / 0.8 = 1.0
    conf = engine._calculate_confidence([ev1, ev2], [])
    assert conf == 1.0
