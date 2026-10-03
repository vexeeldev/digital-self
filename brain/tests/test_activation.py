"""
Tests for Initial Activation Engine (V2.1)
"""

import os
import uuid
import pytest
import psycopg2
from datetime import datetime, timezone, timedelta

from activation import (
    calculate_recency,
    calculate_activation,
    get_node_frequency_proxy,
    activate_nodes,
    ACTIVATION_THRESHOLD,
    W_RELEVANCE,
    W_RECENCY,
    W_FREQUENCY,
    W_ASSOCIATION,
    DECAY_LAMBDA
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

def test_calculate_recency():
    now = datetime.now(timezone.utc)
    
    # Same time -> 1.0
    assert calculate_recency(now, now, DECAY_LAMBDA) == 1.0
    
    # Past -> < 1.0
    past = now - timedelta(days=100)
    assert 0.0 < calculate_recency(past, now, DECAY_LAMBDA) < 1.0
    assert calculate_recency(past, now, 0.01) == pytest.approx(0.367879, abs=1e-4)
    
    # Future / Negative elapsed time -> clamped to 1.0
    future = now + timedelta(days=10)
    assert calculate_recency(future, now, DECAY_LAMBDA) == 1.0

def test_calculate_activation():
    # all zero -> zero
    assert calculate_activation(0.0, 0.0, 0.0, 0.0) == 0.0
    
    # all one -> one (assuming weights sum to 1.0)
    act = calculate_activation(1.0, 1.0, 1.0, 1.0)
    assert act == pytest.approx(W_RELEVANCE + W_RECENCY + W_FREQUENCY + W_ASSOCIATION, abs=1e-5)
    
    # mid values
    act = calculate_activation(0.5, 0.5, 0.5, 0.5)
    assert 0.0 < act < 1.0
    
    # out of bounds clamping check (if we artificially push it above 1)
    # the function clamps it
    clamped = calculate_activation(10.0, 10.0, 10.0, 10.0)
    assert clamped == 1.0
    
    # negative input bounds logic testing (should not be < 0)
    under = calculate_activation(-10.0, -10.0, -10.0, -10.0)
    assert under == 0.0

def test_frequency_proxy(db_connection):
    node_id = uuid.uuid4()
    exp_id1 = uuid.uuid4()
    exp_id2 = uuid.uuid4()
    
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id1), "text1"))
        cur.execute("INSERT INTO experiences (id, raw_text) VALUES (%s, %s)", (str(exp_id2), "text2"))
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', 'testnode')", (str(node_id),))
        
        cur.execute("INSERT INTO experience_nodes (experience_id, node_id) VALUES (%s, %s)", (str(exp_id1), str(node_id)))
        cur.execute("INSERT INTO experience_nodes (experience_id, node_id) VALUES (%s, %s)", (str(exp_id2), str(node_id)))
        
    freq = get_node_frequency_proxy(db_connection, node_id)
    assert freq == 0.2  # 2 / 10.0

def test_activate_nodes(db_connection):
    node_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # No experiences means freq = 0.0
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', 'cand')", (str(node_id),))
        
    candidates = [
        {
            'node_id': node_id,
            'last_seen': now,
            'relevance': 0.8,
            'association_strength': 0.5
        }
    ]
    
    # freq = 0.0
    # recency = 1.0
    # act = W_RELEVANCE * 0.8 + W_RECENCY * 1.0 + W_FREQUENCY * 0.0 + W_ASSOCIATION * 0.5
    expected = W_RELEVANCE * 0.8 + W_RECENCY * 1.0 + W_ASSOCIATION * 0.5
    
    activated = activate_nodes(db_connection, candidates, now)
    
    assert len(activated) == 1
    assert activated[0]['node_id'] == node_id
    assert activated[0]['activation_score'] == pytest.approx(expected, abs=1e-3)
    assert activated[0]['activation_score'] >= ACTIVATION_THRESHOLD
    
def test_activate_nodes_below_threshold(db_connection):
    node_id = uuid.uuid4()
    # Way in the past
    past = datetime.now(timezone.utc) - timedelta(days=1000)
    now = datetime.now(timezone.utc)
    
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO nodes (id, type, name) VALUES (%s, 'concept', 'cand2')", (str(node_id),))
        
    candidates = [
        {
            'node_id': node_id,
            'last_seen': past,
            'relevance': 0.0,
            'association_strength': 0.0
        }
    ]
    
    # freq = 0.0
    # recency ~ 0.0
    # rel = 0.0
    # assoc = 0.0
    # act ~ 0.0
    activated = activate_nodes(db_connection, candidates, now)
    
    assert len(activated) == 0

from internal_state import InternalState
from activation import W_STATE_ENERGY, W_STATE_STRESS, W_STATE_CURIOSITY

def test_activation_with_internal_state():
    state = InternalState(
        energy=0.8,
        stress=0.2,
        curiosity=0.5
    )
    
    # base
    base = W_RELEVANCE * 0.5 + W_RECENCY * 0.5 + W_FREQUENCY * 0.5 + W_ASSOCIATION * 0.5
    
    modulation = (0.8 * W_STATE_ENERGY) + (0.2 * W_STATE_STRESS) + (0.5 * W_STATE_CURIOSITY)
    
    act = calculate_activation(0.5, 0.5, 0.5, 0.5, state)
    
    assert act == pytest.approx(base + modulation, abs=1e-3)
    
def test_activation_state_bounds():
    state = InternalState(energy=1.0, stress=0.0, curiosity=1.0)
    # Even with high base, should clamp to 1.0
    act = calculate_activation(1.0, 1.0, 1.0, 1.0, state)
    assert act == 1.0
    
    state_low = InternalState(energy=0.0, stress=1.0, curiosity=0.0)
    # Even with low base, should clamp to 0.0
    act = calculate_activation(0.0, 0.0, 0.0, 0.0, state_low)
    assert act == 0.0
