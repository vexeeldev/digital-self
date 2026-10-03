"""
Tests for Initial Spreading Activation Engine (V2.1)
"""

import os
import uuid
import pytest
import psycopg2

from activation import (
    spread_activation,
    MAX_DEPTH,
    PROPAGATION_DECAY,
    ACTIVATION_THRESHOLD
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

def setup_graph(conn):
    """
    Creates a simple chain and cycle graph for testing:
    A -> B (str=0.5)
    B -> C (str=0.4)
    C -> A (str=0.3) # Cycle
    A -> D (str=0.0) # Zero strength
    E -> C (str=0.8) # Multiple paths to C
    """
    exp_id = uuid.uuid4()
    n_a = uuid.uuid4()
    n_b = uuid.uuid4()
    n_c = uuid.uuid4()
    n_d = uuid.uuid4()
    n_e = uuid.uuid4()
    
    with conn.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, 'graph')", (str(exp_id),))
        
        for n_id, name in zip([n_a, n_b, n_c, n_d, n_e], ['A', 'B', 'C', 'D', 'E']):
            cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', %s)", (str(n_id), name))
            
        def add_edge(src, tgt, strength):
            cur.execute(
                """
                INSERT INTO associations (source_node_id, target_node_id, type, strength, source_experience_id)
                VALUES (%s, %s, 'co_occurs_with', %s, %s)
                """,
                (str(src), str(tgt), strength, str(exp_id))
            )
            
        add_edge(n_a, n_b, 0.5)
        add_edge(n_b, n_c, 0.4)
        add_edge(n_c, n_a, 0.3)
        add_edge(n_a, n_d, 0.0)
        add_edge(n_e, n_c, 0.8)
        
    return {
        'A': n_a,
        'B': n_b,
        'C': n_c,
        'D': n_d,
        'E': n_e
    }

def test_spread_formula_and_max_depth(db_connection):
    nodes = setup_graph(db_connection)
    A, B, C = nodes['A'], nodes['B'], nodes['C']
    
    seeds = {A: 0.8}
    
    # max_depth = 0
    res0 = spread_activation(db_connection, seeds, max_depth=0, propagation_decay=0.5)
    assert len(res0) == 1
    assert res0[A] == 0.8
    
    # max_depth = 1
    res1 = spread_activation(db_connection, seeds, max_depth=1, propagation_decay=0.5)
    assert len(res1) == 2
    assert res1[A] == 0.8
    assert res1[B] == pytest.approx(0.2, abs=1e-5) # 0.8 * 0.5 * 0.5 = 0.2
    assert C not in res1
    
    # max_depth = 2
    res2 = spread_activation(db_connection, seeds, max_depth=2, propagation_decay=0.5)
    assert len(res2) == 3
    assert res2[A] == 0.8
    assert res2[B] == pytest.approx(0.2, abs=1e-5)
    assert res2[C] == pytest.approx(0.04, abs=1e-5) # 0.2 * 0.4 * 0.5 = 0.04

def test_cycle_handling(db_connection):
    nodes = setup_graph(db_connection)
    A, B, C = nodes['A'], nodes['B'], nodes['C']
    
    seeds = {A: 0.8}
    
    # Let it run deep, it should naturally terminate because propagated < existing
    res = spread_activation(db_connection, seeds, max_depth=10, propagation_decay=0.5)
    
    # If it didn't infinite loop, it finishes.
    assert A in res
    assert res[A] == 0.8 # Cycle back to A yields 0.04 * 0.3 * 0.5 = 0.006, which is < 0.8

def test_multiple_seeds_max(db_connection):
    nodes = setup_graph(db_connection)
    B, E, C = nodes['B'], nodes['E'], nodes['C']
    
    # Path B -> C (str 0.4)
    # Path E -> C (str 0.8)
    
    seeds = {B: 1.0, E: 1.0}
    
    res = spread_activation(db_connection, seeds, max_depth=2, propagation_decay=0.5)
    
    # From B: 1.0 * 0.4 * 0.5 = 0.2
    # From E: 1.0 * 0.8 * 0.5 = 0.4
    # Max should be 0.4
    assert res[C] == pytest.approx(0.4, abs=1e-5)

def test_direction_and_zero_strength(db_connection):
    nodes = setup_graph(db_connection)
    A, B, D = nodes['A'], nodes['B'], nodes['D']
    
    # Direction: B -> A doesn't exist directly. At depth 1, A shouldn't be reached.
    res = spread_activation(db_connection, {B: 1.0}, max_depth=1, propagation_decay=0.5)
    assert A not in res
    
    # Zero strength: A -> D is 0.0
    res2 = spread_activation(db_connection, {A: 1.0}, max_depth=2, propagation_decay=0.5)
    assert res2.get(D, 0.0) == 0.0

def test_read_only_and_deterministic(db_connection):
    nodes = setup_graph(db_connection)
    A = nodes['A']
    
    res1 = spread_activation(db_connection, {A: 0.8}, max_depth=3, propagation_decay=0.5)
    res2 = spread_activation(db_connection, {A: 0.8}, max_depth=3, propagation_decay=0.5)
    
    assert res1 == res2
    
    # Check DB was not modified (strength still 0.5)
    with db_connection.cursor() as cur:
        cur.execute("SELECT strength FROM associations WHERE source_node_id = %s", (str(A),))
        strengths = [float(r[0]) for r in cur.fetchall()]
        assert 0.5 in strengths
        
def test_no_associations(db_connection):
    # Seed a node with no outgoing associations
    isolated_node = uuid.uuid4()
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', 'iso')", (str(isolated_node),))
        
    res = spread_activation(db_connection, {isolated_node: 1.0}, max_depth=2)
    assert len(res) == 1
    assert res[isolated_node] == 1.0

def test_spread_assembly_activation(db_connection):
    exp_id = uuid.uuid4()
    n_a = uuid.uuid4()
    n_b = uuid.uuid4()
    n_c = uuid.uuid4()
    asm_id = uuid.uuid4()
    
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, 'assembly text')", (str(exp_id),))
        for n_id, name in zip([n_a, n_b, n_c], ['A', 'B', 'C']):
            cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', %s)", (str(n_id), name))
            
        # Create an Assembly representing [A, B, C]
        cur.execute("INSERT INTO assemblies (id, experience_id, context_summary) VALUES (%s, %s, 'test')", (str(asm_id), str(exp_id)))
        
        # Add members
        for n_id in [n_a, n_b, n_c]:
            cur.execute("INSERT INTO assembly_members (assembly_id, node_id, role, weight) VALUES (%s, %s, 'participant', 1.0)", (str(asm_id), str(n_id)))
            
    # Seed A. A has no explicit associations to B or C.
    # But because they are in the same assembly, spreading should activate B and C.
    res = spread_activation(db_connection, {n_a: 1.0}, max_depth=2)
    
    # Assembly activation: 1.0 * 1.0 (weight) * 0.8 (decay) = 0.8
    # Target activation: 0.8 * 1.0 (weight) = 0.8
    assert n_b in res
    assert res[n_b] == pytest.approx(0.8, abs=1e-3)
    assert n_c in res
    assert res[n_c] == pytest.approx(0.8, abs=1e-3)

def test_spread_assembly_cycle(db_connection):
    exp_id = uuid.uuid4()
    n_a = uuid.uuid4()
    n_b = uuid.uuid4()
    asm_id = uuid.uuid4()
    
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, 'assembly cycle')", (str(exp_id),))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', 'A')", (str(n_a),))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', 'B')", (str(n_b),))
        
        cur.execute("INSERT INTO assemblies (id, experience_id, context_summary) VALUES (%s, %s, 'test')", (str(asm_id), str(exp_id)))
        cur.execute("INSERT INTO assembly_members (assembly_id, node_id, role, weight) VALUES (%s, %s, 'r1', 1.0)", (str(asm_id), str(n_a)))
        cur.execute("INSERT INTO assembly_members (assembly_id, node_id, role, weight) VALUES (%s, %s, 'r2', 1.0)", (str(asm_id), str(n_b)))
        
        # Add Association B -> A
        cur.execute(
            """
            INSERT INTO associations (source_node_id, target_node_id, type, strength, source_experience_id)
            VALUES (%s, %s, 'co_occurs_with', 0.5, %s)
            """,
            (str(n_b), str(n_a), str(exp_id))
        )
        
    res = spread_activation(db_connection, {n_a: 1.0}, max_depth=10)
    
    # Path: A (1.0) -> Assembly (0.8) -> B (0.8)
    # B (0.8) -> Assoc (0.5 * 0.5) = 0.2 -> A
    # Max A is 1.0. Max B is 0.8.
    # Algorithm should terminate gracefully.
    assert res[n_a] == 1.0
    assert res[n_b] == pytest.approx(0.8, abs=1e-3)
