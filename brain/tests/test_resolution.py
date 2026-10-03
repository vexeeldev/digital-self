import pytest
import uuid
import psycopg2
from psycopg2.extensions import connection

from models import NodeType, Experience, NodeCreate
from resolution import resolve_node, MatchType, add_alias
from extraction import save_extracted_nodes
from experience import save_experience

@pytest.fixture
def db_conn():
    conn = psycopg2.connect("dbname=digital_self user=malakul-tech")
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()

def test_resolve_exact_canonical(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    assert res1.is_new is True
    assert res1.match_type == MatchType.NONE
    
    res2 = resolve_node(db_conn, "Office", NodeType.PLACE)
    assert res2.is_new is False
    assert res2.match_type == MatchType.EXACT_CANONICAL
    assert res2.node_id == res1.node_id

def test_resolve_case_insensitive_canonical(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    res2 = resolve_node(db_conn, "oFFiCe", NodeType.PLACE)
    assert res2.is_new is False
    assert res2.match_type == MatchType.EXACT_CANONICAL
    assert res2.node_id == res1.node_id

def test_resolve_exact_alias(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    add_alias(db_conn, res1.node_id, "kantor", NodeType.PLACE)
    
    res2 = resolve_node(db_conn, "kantor", NodeType.PLACE)
    assert res2.is_new is False
    assert res2.match_type == MatchType.EXACT_ALIAS
    assert res2.node_id == res1.node_id
    assert res2.canonical_name == "Office"

def test_resolve_case_insensitive_alias(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    add_alias(db_conn, res1.node_id, "kantor", NodeType.PLACE)
    
    res2 = resolve_node(db_conn, "KANTOR", NodeType.PLACE)
    assert res2.is_new is False
    assert res2.match_type == MatchType.EXACT_ALIAS
    assert res2.node_id == res1.node_id

def test_create_new_node(db_conn):
    res = resolve_node(db_conn, "Novel Concept", NodeType.CONCEPT)
    assert res.is_new is True
    assert res.match_type == MatchType.NONE

def test_same_name_different_type(db_conn):
    res1 = resolve_node(db_conn, "Apple", NodeType.OBJECT)
    res2 = resolve_node(db_conn, "Apple", NodeType.CONCEPT)
    assert res1.node_id != res2.node_id
    assert res1.is_new is True
    assert res2.is_new is True

def test_alias_collision(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    add_alias(db_conn, res1.node_id, "kantor", NodeType.PLACE)
    
    res2 = resolve_node(db_conn, "Home", NodeType.PLACE)
    with pytest.raises(ValueError, match="already registered"):
        add_alias(db_conn, res2.node_id, "kantor", NodeType.PLACE)

def test_duplicate_alias_same_node(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    add_alias(db_conn, res1.node_id, "kantor", NodeType.PLACE)
    with pytest.raises(ValueError, match="already registered"):
        add_alias(db_conn, res1.node_id, "kantor", NodeType.PLACE)

def test_empty_whitespace_mention_rejected(db_conn):
    with pytest.raises(ValueError):
        resolve_node(db_conn, "", NodeType.PLACE)
    with pytest.raises(ValueError):
        resolve_node(db_conn, "   ", NodeType.PLACE)

def test_deterministic_behavior(db_conn):
    # Multiple calls with identical input yield identical output
    r1 = resolve_node(db_conn, "Test", NodeType.EVENT)
    r2 = resolve_node(db_conn, "test", NodeType.EVENT)
    r3 = resolve_node(db_conn, "TEST", NodeType.EVENT)
    assert r1.node_id == r2.node_id == r3.node_id
    assert not r2.is_new and not r3.is_new

from models import NodeType, Experience, NodeCreate, ExperienceCreate

def test_existing_experience_remains_unchanged(db_conn):
    exp = save_experience(db_conn, ExperienceCreate(raw_text="Pergi ke kantor"))
    nodes_in = [NodeCreate(type=NodeType.PLACE, name="kantor", confidence=0.9)]
    saved = save_extracted_nodes(db_conn, exp.id, nodes_in)
    
    with db_conn.cursor() as cur:
        cur.execute("SELECT raw_text FROM experiences WHERE id = %s", (str(exp.id),))
        text = cur.fetchone()[0]
        assert text == "Pergi ke kantor"

def test_experience_nodes_provenance(db_conn):
    exp1 = save_experience(db_conn, ExperienceCreate(raw_text="I went to the Office"))
    exp2 = save_experience(db_conn, ExperienceCreate(raw_text="Aku pergi ke kantor"))
    
    nodes1 = [NodeCreate(type=NodeType.PLACE, name="Office", confidence=0.9)]
    saved1 = save_extracted_nodes(db_conn, exp1.id, nodes1)
    office_node = saved1[0]
    
    add_alias(db_conn, office_node.id, "kantor", NodeType.PLACE)
    
    nodes2 = [NodeCreate(type=NodeType.PLACE, name="kantor", confidence=0.9)]
    saved2 = save_extracted_nodes(db_conn, exp2.id, nodes2)
    
    assert saved2[0].id == office_node.id
    
    # Check provenance
    with db_conn.cursor() as cur:
        cur.execute("SELECT experience_id FROM experience_nodes WHERE node_id = %s", (str(office_node.id),))
        exp_ids = {row[0] for row in cur.fetchall()}
        assert str(exp1.id) in exp_ids
        assert str(exp2.id) in exp_ids

def test_canonical_name_never_replaced(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    add_alias(db_conn, res1.node_id, "kantor", NodeType.PLACE)
    
    res2 = resolve_node(db_conn, "kantor", NodeType.PLACE)
    assert res2.canonical_name == "Office"

def test_alias_pointing_to_canonical(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    add_alias(db_conn, res1.node_id, "kantor", NodeType.PLACE)
    
    with db_conn.cursor() as cur:
        cur.execute("SELECT node_id FROM node_aliases WHERE alias_name = 'kantor'")
        assert cur.fetchone()[0] == str(res1.node_id)

def test_alias_name_taken_by_canonical(db_conn):
    res1 = resolve_node(db_conn, "Office", NodeType.PLACE)
    # Trying to add an alias that already exists as a canonical node
    with pytest.raises(ValueError, match="already taken"):
        add_alias(db_conn, res1.node_id, "Office", NodeType.PLACE)
