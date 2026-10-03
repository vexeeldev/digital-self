import uuid
import pytest
import math
from models import Node, NodeType
from internal_state import InternalState, update_internal_state

def create_mock_emotion_node(name: str) -> Node:
    return Node(
        id=uuid.uuid4(),
        type=NodeType.EMOTION,
        name=name,
        confidence=1.0,
        activation=1.0
    )

def test_initial_state_valid():
    state = InternalState()
    assert state.energy == 0.5
    assert state.stress == 0.5
    assert state.curiosity == 0.5

def test_positive_emotional_signal():
    params = {"internal_state": {"decay_rate": 0.0, "emotion_influence": 0.1}}
    prev = InternalState(energy=0.5, stress=0.5, curiosity=0.5)
    exp_id = uuid.uuid4()
    
    # "senang": stress -1.0, energy 0.8, curiosity 0.5
    nodes = [create_mock_emotion_node("senang")]
    
    res = update_internal_state(prev, exp_id, nodes, params)
    
    assert math.isclose(res.new_state.stress, 0.4)
    assert math.isclose(res.new_state.energy, 0.58)
    assert math.isclose(res.new_state.curiosity, 0.55)
    assert res.changed_dimensions["stress"] < 0
    assert res.changed_dimensions["energy"] > 0
    assert res.experience_id == exp_id

def test_negative_emotional_signal():
    params = {"internal_state": {"decay_rate": 0.0, "emotion_influence": 0.1}}
    prev = InternalState(energy=0.5, stress=0.5, curiosity=0.5)
    
    # "kesal": stress 1.0, energy -0.5
    nodes = [create_mock_emotion_node("kesal")]
    res = update_internal_state(prev, uuid.uuid4(), nodes, params)
    
    assert math.isclose(res.new_state.stress, 0.6)
    assert math.isclose(res.new_state.energy, 0.45)

def test_neutral_experience_applies_decay():
    params = {"internal_state": {"decay_rate": 0.05, "emotion_influence": 0.1}}
    prev = InternalState(energy=0.8, stress=0.2, curiosity=0.5)
    
    # No emotion nodes
    res = update_internal_state(prev, uuid.uuid4(), [], params)
    
    # Energy decays towards 0.5 (0.8 - 0.05 = 0.75)
    assert math.isclose(res.new_state.energy, 0.75)
    # Stress decays towards 0.5 (0.2 + 0.05 = 0.25)
    assert math.isclose(res.new_state.stress, 0.25)
    # Curiosity is already 0.5, no decay
    assert math.isclose(res.new_state.curiosity, 0.5)
    
def test_state_clamp_lower_bound():
    params = {"internal_state": {"decay_rate": 0.0, "emotion_influence": 1.0}} # huge influence
    prev = InternalState(energy=0.1, stress=0.1)
    
    # "sedih" has energy -1.0
    nodes = [create_mock_emotion_node("sedih")]
    res = update_internal_state(prev, uuid.uuid4(), nodes, params)
    
    assert res.new_state.energy == 0.0 # Clamped

def test_state_clamp_upper_bound():
    params = {"internal_state": {"decay_rate": 0.0, "emotion_influence": 1.0}}
    prev = InternalState(energy=0.9, stress=0.9)
    
    # "kesal" has stress +1.0
    nodes = [create_mock_emotion_node("kesal")]
    res = update_internal_state(prev, uuid.uuid4(), nodes, params)
    
    assert res.new_state.stress == 1.0 # Clamped

def test_previous_state_immutable():
    params = {"internal_state": {"decay_rate": 0.0, "emotion_influence": 0.1}}
    prev = InternalState(energy=0.5, stress=0.5)
    nodes = [create_mock_emotion_node("kesal")]
    
    res = update_internal_state(prev, uuid.uuid4(), nodes, params)
    
    assert prev.stress == 0.5
    assert res.new_state.stress == 0.6
    assert res.previous_state is prev

def test_contradictory_sequential_signals():
    params = {"internal_state": {"decay_rate": 0.0, "emotion_influence": 0.1}}
    prev = InternalState(energy=0.5, stress=0.5)
    
    # Both "kesal" (stress+1) and "senang" (stress-1)
    nodes = [
        create_mock_emotion_node("kesal"),
        create_mock_emotion_node("senang")
    ]
    
    res = update_internal_state(prev, uuid.uuid4(), nodes, params)
    # Net stress delta = 0
    assert res.new_state.stress == 0.5
    # Net energy delta = -0.5 + 0.8 = 0.3 * 0.1 = 0.03
    assert math.isclose(res.new_state.energy, 0.53)

def test_unknown_emotion_treated_as_neutral():
    params = {"internal_state": {"decay_rate": 0.05, "emotion_influence": 0.1}}
    prev = InternalState(energy=0.8, stress=0.5)
    
    nodes = [create_mock_emotion_node("emotion_tidak_dikenal")]
    res = update_internal_state(prev, uuid.uuid4(), nodes, params)
    
    # Should only apply decay
    assert math.isclose(res.new_state.energy, 0.75)
    assert res.new_state.stress == 0.5
