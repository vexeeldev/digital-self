"""
Digital Self - internal_state.py
Version: V2.1 Initial Internal State Engine
"""

import uuid
from pydantic import BaseModel, Field
from models import Node, NodeType

# Hardcoded emotion mapping because we cannot use LLM or Embeddings
# to deterministically infer valence/arousal from text in V2.1.
# This represents a technical limitation documented in the report.
EMOTION_MAP = {
    "kesal": {"stress": 1.0, "energy": -0.5, "curiosity": -0.2},
    "marah": {"stress": 1.0, "energy": 0.5, "curiosity": -0.2},
    "senang": {"stress": -1.0, "energy": 0.8, "curiosity": 0.5},
    "penasaran": {"stress": 0.0, "energy": 0.5, "curiosity": 1.0},
    "sedih": {"stress": 0.5, "energy": -1.0, "curiosity": -0.5},
    "lelah": {"stress": 0.2, "energy": -1.0, "curiosity": -0.5},
    "biasa": {"stress": -0.2, "energy": 0.0, "curiosity": 0.0}
}

class InternalState(BaseModel):
    energy: float = Field(default=0.5, ge=0.0, le=1.0)
    stress: float = Field(default=0.5, ge=0.0, le=1.0)
    curiosity: float = Field(default=0.5, ge=0.0, le=1.0)

class InternalStateUpdateResult(BaseModel):
    previous_state: InternalState
    new_state: InternalState
    experience_id: uuid.UUID
    changed_dimensions: dict[str, float]

def update_internal_state(
    previous_state: InternalState,
    experience_id: uuid.UUID,
    emotion_nodes: list[Node],
    params: dict
) -> InternalStateUpdateResult:
    """
    Deterministically updates the internal state based on emotional signals.
    """
    decay = params.get("internal_state", {}).get("decay_rate", 0.05)
    influence = params.get("internal_state", {}).get("emotion_influence", 0.10)
    
    # Calculate net delta from all emotion nodes
    net_energy = 0.0
    net_stress = 0.0
    net_curiosity = 0.0
    
    for node in emotion_nodes:
        if node.type == NodeType.EMOTION:
            emotion_name = node.name.lower()
            if emotion_name in EMOTION_MAP:
                mapping = EMOTION_MAP[emotion_name]
                net_energy += mapping.get("energy", 0.0)
                net_stress += mapping.get("stress", 0.0)
                net_curiosity += mapping.get("curiosity", 0.0)
                
    # Decay pushes value towards baseline 0.5
    def apply_decay(val: float) -> float:
        if val > 0.5:
            return max(0.5, val - decay)
        elif val < 0.5:
            return min(0.5, val + decay)
        return val

    def calc_new(old: float, net: float) -> float:
        decayed = apply_decay(old)
        updated = decayed + (net * influence)
        return max(0.0, min(1.0, updated))

    new_energy = calc_new(previous_state.energy, net_energy)
    new_stress = calc_new(previous_state.stress, net_stress)
    new_curiosity = calc_new(previous_state.curiosity, net_curiosity)
    
    new_state = InternalState(
        energy=new_energy,
        stress=new_stress,
        curiosity=new_curiosity
    )
    
    changed = {
        "energy": new_energy - previous_state.energy,
        "stress": new_stress - previous_state.stress,
        "curiosity": new_curiosity - previous_state.curiosity
    }
    
    return InternalStateUpdateResult(
        previous_state=previous_state,
        new_state=new_state,
        experience_id=experience_id,
        changed_dimensions=changed
    )
