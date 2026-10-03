"""
Digital Self — consolidation.py
Version: V2.1 — Initial Memory Consolidation

Implements deterministic memory consolidation based on historical evidence.
Does NOT modify database schema or records.
"""

from enum import Enum
from datetime import datetime
from activation import calculate_recency, DECAY_LAMBDA

class MemoryState(Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    ARCHIVED = "ARCHIVED"

def determine_memory_state(
    last_seen: datetime, 
    current_time: datetime, 
    frequency: int, 
    decay_lambda: float = DECAY_LAMBDA
) -> MemoryState:
    """
    Determines the memory consolidation state based on historical evidence.
    Rule baseline:
      - recency < 0.05: ARCHIVED (very old, unused memory)
      - recency >= 0.70: HOT (recently used or new memory)
      - recency >= 0.30 and frequency >= 2: WARM (moderately recent, repeated)
      - else: COLD (rarely used or fading)
    """
    recency = calculate_recency(last_seen, current_time, decay_lambda)
    
    if recency < 0.05:
        return MemoryState.ARCHIVED
        
    if recency >= 0.70:
        return MemoryState.HOT
        
    if recency >= 0.30 and frequency >= 2:
        return MemoryState.WARM
        
    return MemoryState.COLD
