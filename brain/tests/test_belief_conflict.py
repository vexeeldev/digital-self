import uuid
import pytest
from models import AssociationType
from pattern import Pattern, AssemblyPattern
from belief import Belief, form_beliefs, AssemblyBelief
from conflict import detect_conflicts, detect_assembly_conflicts, _generate_conflict_id

def make_belief(sub: uuid.UUID, obj: uuid.UUID, rel: AssociationType, conf: float = 0.8, exps=None):
    if exps is None:
        exps = [uuid.uuid4()]
    return Belief(
        subject=sub,
        relationship_type=rel,
        object=obj,
        confidence=conf,
        strength=0.5,
        positive_evidence=1,
        negative_evidence=0,
        supporting_experiences=exps,
        source_pattern=Pattern(
            association_id=uuid.uuid4(),
            source_node_id=sub,
            target_node_id=obj,
            relationship_type=rel,
            evidence_count=1,
            negative_evidence=0,
            association_strength=0.5,
            confidence=conf,
            supporting_experiences=exps
        )
    )

def test_basic_detection():
    sub = uuid.uuid4()
    obj = uuid.uuid4()
    b1 = make_belief(sub, obj, AssociationType.SUPPORTS)
    b2 = make_belief(sub, obj, AssociationType.CONTRADICTS)
    
    # 1. Opposing beliefs create one conflict
    conflicts = detect_conflicts([b1, b2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "OPPOSING_RELATIONSHIP"

def test_same_relationship_no_conflict():
    sub = uuid.uuid4()
    obj = uuid.uuid4()
    b1 = make_belief(sub, obj, AssociationType.SUPPORTS)
    b2 = make_belief(sub, obj, AssociationType.SUPPORTS)
    assert len(detect_conflicts([b1, b2])) == 0

def test_different_subject_no_conflict():
    obj = uuid.uuid4()
    b1 = make_belief(uuid.uuid4(), obj, AssociationType.SUPPORTS)
    b2 = make_belief(uuid.uuid4(), obj, AssociationType.CONTRADICTS)
    assert len(detect_conflicts([b1, b2])) == 0

def test_different_object_no_conflict():
    sub = uuid.uuid4()
    b1 = make_belief(sub, uuid.uuid4(), AssociationType.SUPPORTS)
    b2 = make_belief(sub, uuid.uuid4(), AssociationType.CONTRADICTS)
    assert len(detect_conflicts([b1, b2])) == 0

def test_unconfigured_relationship_no_conflict():
    sub = uuid.uuid4()
    obj = uuid.uuid4()
    # CO_OCCURS_WITH and SIMILAR_TO are not opposing in OPPOSING_RELATIONSHIPS
    b1 = make_belief(sub, obj, AssociationType.CO_OCCURS_WITH)
    b2 = make_belief(sub, obj, AssociationType.SIMILAR_TO)
    assert len(detect_conflicts([b1, b2])) == 0

def test_symmetry_and_identity():
    sub = uuid.uuid4()
    obj = uuid.uuid4()
    b1 = make_belief(sub, obj, AssociationType.SUPPORTS)
    b2 = make_belief(sub, obj, AssociationType.CONTRADICTS)
    
    id1 = _generate_conflict_id(b1, b2)
    id2 = _generate_conflict_id(b2, b1)
    
    # 6. Input order does not change conflict identity
    assert id1 == id2
    
    # 7. Reversed beliefs do not create duplicate conflicts
    conflicts_fwd = detect_conflicts([b1, b2])
    conflicts_rev = detect_conflicts([b2, b1])
    
    assert len(conflicts_fwd) == 1
    assert len(conflicts_rev) == 1
    
    # 8. Same input produces same conflict ID
    assert conflicts_fwd[0].id == conflicts_rev[0].id

def test_ordering_determinism():
    sub = uuid.uuid4()
    obj = uuid.uuid4()
    b1 = make_belief(sub, obj, AssociationType.SUPPORTS)
    b2 = make_belief(sub, obj, AssociationType.CONTRADICTS)
    
    sub2 = uuid.uuid4()
    obj2 = uuid.uuid4()
    b3 = make_belief(sub2, obj2, AssociationType.BEFORE)
    b4 = make_belief(sub2, obj2, AssociationType.AFTER)
    
    # 9. Different input ordering produces same result
    # 10. Output ordering is deterministic
    conflicts1 = detect_conflicts([b1, b2, b3, b4])
    conflicts2 = detect_conflicts([b4, b3, b2, b1])
    
    assert [c.id for c in conflicts1] == [c.id for c in conflicts2]

def test_confidence_immutability():
    sub = uuid.uuid4()
    obj = uuid.uuid4()
    b1 = make_belief(sub, obj, AssociationType.SUPPORTS, conf=0.9)
    b2 = make_belief(sub, obj, AssociationType.CONTRADICTS, conf=0.1)
    
    conflicts = detect_conflicts([b1, b2])
    # 11. Conflict does not modify belief confidence
    assert b1.confidence == 0.9
    assert b2.confidence == 0.1
    # 12. Low-confidence vs high-confidence beliefs still conflict structurally
    assert len(conflicts) == 1

def test_provenance_preservation():
    sub = uuid.uuid4()
    obj = uuid.uuid4()
    exps1 = [uuid.uuid4(), uuid.uuid4()]
    exps2 = [uuid.uuid4()]
    
    b1 = make_belief(sub, obj, AssociationType.SUPPORTS, exps=exps1)
    b2 = make_belief(sub, obj, AssociationType.CONTRADICTS, exps=exps2)
    
    conflicts = detect_conflicts([b1, b2])
    conflict = conflicts[0]
    
    # Canonical sorting means b1 might be belief_a or belief_b depending on uuid hex,
    # but the sets of experiences must match the respective belief.
    assert conflict.supporting_experiences_a == tuple(sorted(conflict.belief_a.supporting_experiences))
    assert conflict.supporting_experiences_b == tuple(sorted(conflict.belief_b.supporting_experiences))
    
    # 13, 14, 15: Provenance is preserved and not mutated
    assert len(conflict.supporting_experiences_a) + len(conflict.supporting_experiences_b) == 3

def test_multiple_conflicts():
    sub = uuid.uuid4()
    obj = uuid.uuid4()
    # 18. Multiple contradictory beliefs can coexist
    b1 = make_belief(sub, obj, AssociationType.SUPPORTS)
    b2 = make_belief(sub, obj, AssociationType.CONTRADICTS)
    b3 = make_belief(sub, obj, AssociationType.WEAKENS)
    
    # SUPPORTS vs CONTRADICTS, and SUPPORTS vs WEAKENS
    conflicts = detect_conflicts([b1, b2, b3])
    
    # 19. Multiple independent conflicts can coexist
    assert len(conflicts) == 2
    
    # 20. No conflict automatically resolves another conflict
    # They are just descriptive representation.

def test_assembly_beliefs():
    # 25, 26: Verify AssemblyBelief behavior
    # Assembly beliefs are structural and have no opposing relationship.
    # We document and test that detect_assembly_conflicts returns empty.
    ab = AssemblyBelief(
        configuration=[],
        confidence=0.5,
        positive_evidence=1,
        negative_evidence=0,
        supporting_experiences=[],
        source_pattern=AssemblyPattern(configuration=[], evidence_count=1, negative_evidence=0, confidence=0.5, supporting_experiences=[])
    )
    conflicts = detect_assembly_conflicts([ab, ab])
    assert conflicts == []

# Active evidence testing requires the database integration
from correction import add_human_association, emit_association_correction
from pattern import form_patterns
import os
import psycopg2

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

def test_active_evidence_integration(db_connection):
    cur = db_connection.cursor()
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('e1') RETURNING id")
    e1 = cur.fetchone()[0]
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('e2') RETURNING id")
    e2 = cur.fetchone()[0]
    
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"S_{uuid.uuid4().hex}",))
    sub = cur.fetchone()[0]
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"O_{uuid.uuid4().hex}",))
    obj = cur.fetchone()[0]
    db_connection.commit()
    
    # 16. Rejected evidence is not treated as active support
    # A SUPPORTS B
    assoc_supports = add_human_association(db_connection, uuid.UUID(e1), uuid.UUID(sub), uuid.UUID(obj), AssociationType.SUPPORTS)
    # A CONTRADICTS B
    assoc_contradicts = add_human_association(db_connection, uuid.UUID(e2), uuid.UUID(sub), uuid.UUID(obj), AssociationType.CONTRADICTS)
    db_connection.commit()
    
    patterns = form_patterns(db_connection, minimum_evidence=1)
    beliefs = form_beliefs(patterns)
    conflicts = [c for c in detect_conflicts(beliefs) if str(c.subject) == str(sub)]
    assert len(conflicts) == 1
    
    # Reject SUPPORTS
    cur.execute("SELECT id FROM experience_associations WHERE experience_id = %s", (str(e1),))
    ea_supports = cur.fetchone()[0]
    emit_association_correction(db_connection, uuid.UUID(ea_supports), "REJECT")
    db_connection.commit()
    
    patterns_rejected = form_patterns(db_connection, minimum_evidence=1)
    beliefs_rejected = form_beliefs(patterns_rejected)
    conflicts_rejected = [c for c in detect_conflicts(beliefs_rejected) if str(c.subject) == str(sub)]
    assert len(conflicts_rejected) == 0 # No conflict anymore because SUPPORTS is inactive
    
    # 17. RESTORE correctly makes evidence available again
    emit_association_correction(db_connection, uuid.UUID(ea_supports), "RESTORE")
    db_connection.commit()
    
    patterns_restored = form_patterns(db_connection, minimum_evidence=1)
    beliefs_restored = form_beliefs(patterns_restored)
    conflicts_restored = [c for c in detect_conflicts(beliefs_restored) if str(c.subject) == str(sub)]
    assert len(conflicts_restored) == 1 # Conflict is back
