"""
Digital Self — activation.py
Version: V2.1 — Initial Activation Engine

Implements the deterministic activation engine.
Reads activation parameters from params.yaml.
"""
import math
import uuid
from datetime import datetime
import yaml
from pathlib import Path
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor
from internal_state import InternalState

PARAMS_PATH = Path(__file__).parent / "params.yaml"

def load_params():
    with open(PARAMS_PATH, 'r') as f:
        return yaml.safe_load(f)

PARAMS = load_params()

# Learning params needed for recency decay
DECAY_LAMBDA = float(PARAMS['learning']['decay_lambda'])

# Activation params
ACTIVATION_THRESHOLD = float(PARAMS['activation']['threshold'])
W_RELEVANCE = float(PARAMS['activation']['weight_relevance'])
W_RECENCY = float(PARAMS['activation']['weight_recency'])
W_FREQUENCY = float(PARAMS['activation']['weight_frequency'])
W_ASSOCIATION = float(PARAMS['activation']['weight_association'])
MAX_DEPTH = int(PARAMS['activation']['max_depth'])
PROPAGATION_DECAY = float(PARAMS['activation']['propagation_decay'])
ASSEMBLY_PROPAGATION_DECAY = float(PARAMS['activation'].get('assembly_propagation_decay', 0.80))

W_STATE_ENERGY = float(PARAMS['activation'].get('weight_state_energy', 0.10))
W_STATE_STRESS = float(PARAMS['activation'].get('weight_state_stress', -0.10))
W_STATE_CURIOSITY = float(PARAMS['activation'].get('weight_state_curiosity', 0.15))

def calculate_recency(last_seen: datetime, current_time: datetime, decay_lambda: float = DECAY_LAMBDA) -> float:
    """
    Calculates recency score using exponential decay.
    Assumes timezone-aware datetimes.
    """
    delta_t = (current_time - last_seen).total_seconds() / 86400.0 # days
    if delta_t < 0:
        delta_t = 0.0
    recency = math.exp(-decay_lambda * delta_t)
    return max(0.0, min(1.0, recency))

def calculate_activation(relevance: float, recency: float, frequency: float, association_strength: float, state: InternalState = None) -> float:
    """
    Calculates total activation score using a simple weighted sum.
    If an InternalState is provided, modulates the base activation.
    Clamps the result to [0.0, 1.0].
    """
    raw_activation = (
        W_RELEVANCE * relevance +
        W_RECENCY * recency +
        W_FREQUENCY * frequency +
        W_ASSOCIATION * association_strength
    )
    
    if state is not None:
        state_modulation = (
            state.energy * W_STATE_ENERGY +
            state.stress * W_STATE_STRESS +
            state.curiosity * W_STATE_CURIOSITY
        )
        raw_activation += state_modulation
        
    return max(0.0, min(1.0, raw_activation))

def get_node_frequency_proxy(conn: connection, node_id: uuid.UUID) -> float:
    """
    Retrieves a frequency proxy for a node.
    For Phase 1, we use the number of experiences this node has appeared in,
    normalized to a 0.0 - 1.0 scale (arbitrarily capping at 10 experiences = 1.0).
    """
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM vw_active_experience_nodes WHERE node_id = %s", (str(node_id),))
        count = cur.fetchone()[0]
        
    return min(1.0, count / 10.0)

def activate_nodes(conn: connection, candidates: list[dict], current_time: datetime, state: InternalState = None) -> list[dict]:
    """
    Takes candidate nodes with contextual scores, calculates their activation (optionally modulated by InternalState),
    and returns those that meet the ACTIVATION_THRESHOLD.
    Does NOT update anything in the database (read-only process).
    """
    activated = []
    
    for cand in candidates:
        node_id = cand['node_id']
        last_seen = cand['last_seen']
        relevance = cand.get('relevance', 0.0)
        assoc_strength = cand.get('association_strength', 0.0)
        
        recency = calculate_recency(last_seen, current_time)
        freq = get_node_frequency_proxy(conn, node_id)
        
        act_score = calculate_activation(relevance, recency, freq, assoc_strength, state)
        
        if act_score >= ACTIVATION_THRESHOLD:
            activated.append({
                'node_id': node_id,
                'activation_score': act_score
            })
            
    return activated

def spread_activation(
    conn: connection, 
    seeds: dict[uuid.UUID, float], 
    max_depth: int = MAX_DEPTH, 
    propagation_decay: float = PROPAGATION_DECAY
) -> dict[uuid.UUID, float]:
    """
    Spreads activation deterministically through the association graph AND assembly structures.
    
    Inputs:
        seeds: dict mapping node_id to its initial activation score.
        max_depth: int limiting traversal depth.
        propagation_decay: float representing energy loss per hop for associations.
        
    Returns:
        dict mapping node_id to its final maximum activation score.
        Result may include nodes below threshold.
    """
    if max_depth < 0:
        return {}

    # activations stores the maximum activation reached for each node
    activations = {node_id: score for node_id, score in seeds.items()}
    
    # Track the maximum activation an assembly has been triggered with
    assembly_activations = {}
    
    # queue stores tuples of (node_id, current_depth)
    queue = [(node_id, 0) for node_id in seeds.keys()]
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        while queue:
            current_node, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
                
            current_activation = activations[current_node]
            if current_activation <= 0.0:
                continue
            
            # --- 1. Spread via Associations ---
            cur.execute(
                """
                SELECT target_node_id, strength 
                FROM associations 
                WHERE source_node_id = %s AND positive_evidence > 0
                """,
                (str(current_node),)
            )
            edges = cur.fetchall()
            
            for row in edges:
                target_id = uuid.UUID(row['target_node_id'])
                strength = float(row['strength'])
                
                propagated = current_activation * strength * propagation_decay
                
                # Check cycle & accumulation rule: max(existing, propagated)
                existing = activations.get(target_id, 0.0)
                
                if propagated > existing:
                    activations[target_id] = propagated
                    queue.append((target_id, depth + 1))
                    
            # --- 2. Spread via Assemblies ---
            cur.execute(
                """
                SELECT assembly_id, weight 
                FROM vw_active_assembly_members 
                WHERE node_id = %s
                """,
                (str(current_node),)
            )
            node_assemblies = cur.fetchall()
            
            for row in node_assemblies:
                asm_id = uuid.UUID(row['assembly_id'])
                source_weight = float(row['weight'])
                
                assembly_activation = current_activation * source_weight * ASSEMBLY_PROPAGATION_DECAY
                
                existing_asm_act = assembly_activations.get(asm_id, 0.0)
                if assembly_activation > existing_asm_act:
                    # We reached this assembly with a higher energy than before, process it
                    assembly_activations[asm_id] = assembly_activation
                    
                    cur.execute(
                        """
                        SELECT node_id, weight 
                        FROM vw_active_assembly_members 
                        WHERE assembly_id = %s AND node_id != %s
                        """,
                        (str(asm_id), str(current_node))
                    )
                    other_members = cur.fetchall()
                    
                    for m_row in other_members:
                        target_id = uuid.UUID(m_row['node_id'])
                        target_weight = float(m_row['weight'])
                        
                        propagated = assembly_activation * target_weight
                        
                        existing = activations.get(target_id, 0.0)
                        if propagated > existing:
                            activations[target_id] = propagated
                            queue.append((target_id, depth + 1))
                            
    return activations
