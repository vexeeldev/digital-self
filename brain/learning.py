"""
Digital Self — learning.py
Version: V2.1 — Initial Association Learning

Implements learning rules for updating association strength
based on positive and negative evidence.
"""

import uuid
import math
import yaml
from pathlib import Path
from psycopg2.extensions import connection

PARAMS_PATH = Path(__file__).parent / "params.yaml"

def load_params():
    with open(PARAMS_PATH, 'r') as f:
        return yaml.safe_load(f)

PARAMS = load_params()
ALPHA = float(PARAMS['learning']['alpha'])
BETA = float(PARAMS['learning']['beta'])
DECAY_LAMBDA = float(PARAMS['learning']['decay_lambda'])

def _update_association_strength(
    conn: connection, 
    assoc_id: uuid.UUID, 
    exp_id: uuid.UUID, 
    weight: float, 
    is_positive: bool
):
    """
    Atomic update of association strength and evidence counts.
    """
    if weight <= 0:
        raise ValueError("Evidence weight must be > 0")

    with conn.cursor() as cur:
        # 1. Establish provenance bridge and prevent double-counting.
        # If this exact experience already contributed to this association with ANY polarity,
        # it is ignored to prevent inflating evidence artificially.
        cur.execute(
            """
            INSERT INTO experience_associations (experience_id, association_id, is_positive)
            VALUES (%s, %s, %s)
            ON CONFLICT (experience_id, association_id) DO NOTHING
            RETURNING id;
            """,
            (str(exp_id), str(assoc_id), is_positive)
        )
        is_new_evidence = cur.fetchone() is not None
        
        if not is_new_evidence:
            # We already processed evidence from this experience for this association.
            return

        # 2. Lock row for atomic update
        cur.execute(
            """
            SELECT strength, positive_evidence, negative_evidence 
            FROM associations 
            WHERE id = %s FOR UPDATE;
            """,
            (str(assoc_id),)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Association {assoc_id} not found")

        s_old = float(row[0])
        pos_count = int(row[1])
        neg_count = int(row[2])

        # 3. Apply formulas
        if is_positive:
            s_new = s_old + ALPHA * weight * (1.0 - s_old)
            pos_count += 1
        else:
            s_new = s_old - BETA * weight * s_old
            neg_count += 1

        # 4. Enforce bounds
        s_new = max(0.0, min(1.0, s_new))

        # 5. Save back
        cur.execute(
            """
            UPDATE associations 
            SET strength = %s, positive_evidence = %s, negative_evidence = %s, updated_at = now()
            WHERE id = %s;
            """,
            (s_new, pos_count, neg_count, str(assoc_id))
        )

def replay_association_learning(conn: connection, assoc_id: uuid.UUID):
    """
    Deterministically recalculates derived association strength and evidence counts
    based on the current Active Evidence set. Reuses exact Stage 6 learning formulas.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM associations WHERE id = %s FOR UPDATE;", (str(assoc_id),))
        
        cur.execute(
            """
            SELECT ea.is_positive
            FROM vw_active_experience_associations ea
            JOIN experiences e ON ea.experience_id = e.id
            WHERE ea.association_id = %s
            ORDER BY e.created_at ASC, ea.id ASC
            """,
            (str(assoc_id),)
        )
        rows = cur.fetchall()

        s_new = 0.100  # Default strength from schema
        pos_count = 0
        neg_count = 0
        weight = 1.0  # Exact Stage 6 weight resolution

        for row in rows:
            is_pos = row[0]
            if is_pos:
                s_new = s_new + ALPHA * weight * (1.0 - s_new)
                pos_count += 1
            else:
                s_new = s_new - BETA * weight * s_new
                neg_count += 1
                
        s_new = max(0.0, min(1.0, s_new))
        
        cur.execute(
            """
            UPDATE associations 
            SET strength = %s, positive_evidence = %s, negative_evidence = %s, updated_at = now()
            WHERE id = %s;
            """,
            (s_new, pos_count, neg_count, str(assoc_id))
        )

def record_positive_evidence(conn: connection, assoc_id: uuid.UUID, exp_id: uuid.UUID, weight: float = 1.0):
    """
    Record positive evidence supporting an association.
    Formula: s_new = s_old + alpha * w * (1 - s_old)
    """
    _update_association_strength(conn, assoc_id, exp_id, weight, is_positive=True)

def record_negative_evidence(conn: connection, assoc_id: uuid.UUID, exp_id: uuid.UUID, weight: float = 1.0):
    """
    Record negative evidence weakening an association.
    Formula: s_new = s_old - beta * w * s_old
    """
    _update_association_strength(conn, assoc_id, exp_id, weight, is_positive=False)

def apply_decay(strength: float, decay_lambda: float, elapsed_time: float) -> float:
    """
    Decay formula: s_new = s_old * exp(-lambda * delta_t)
    where delta_t is typically elapsed days.
    """
    if elapsed_time < 0:
        elapsed_time = 0.0
    s_new = strength * math.exp(-decay_lambda * elapsed_time)
    return max(0.0, min(1.0, s_new))
