"""
Tests for Initial Memory Consolidation (V2.1)
"""

import math
from datetime import datetime, timezone, timedelta
import pytest

from consolidation import MemoryState, determine_memory_state

def test_determine_memory_state_hot():
    now = datetime.now(timezone.utc)
    # recency = 1.0 (>= 0.70)
    assert determine_memory_state(now, now, frequency=1, decay_lambda=0.01) == MemoryState.HOT

def test_determine_memory_state_warm():
    now = datetime.now(timezone.utc)
    # Let's target recency = 0.5. delta_t = -ln(0.5) / 0.01 = 69.3 days
    delta_days = -math.log(0.5) / 0.01
    past = now - timedelta(days=delta_days)
    
    # recency ~ 0.5, frequency = 2 -> WARM
    assert determine_memory_state(past, now, frequency=2, decay_lambda=0.01) == MemoryState.WARM
    
def test_determine_memory_state_cold_due_to_frequency():
    now = datetime.now(timezone.utc)
    delta_days = -math.log(0.5) / 0.01
    past = now - timedelta(days=delta_days)
    
    # recency ~ 0.5, frequency = 1 -> COLD
    assert determine_memory_state(past, now, frequency=1, decay_lambda=0.01) == MemoryState.COLD

def test_determine_memory_state_cold_due_to_recency():
    now = datetime.now(timezone.utc)
    # recency between 0.05 and 0.30. Let's aim for 0.20
    delta_days = -math.log(0.20) / 0.01
    past = now - timedelta(days=delta_days)
    
    # recency ~ 0.20 -> COLD regardless of frequency
    assert determine_memory_state(past, now, frequency=10, decay_lambda=0.01) == MemoryState.COLD

def test_determine_memory_state_archived():
    now = datetime.now(timezone.utc)
    # recency < 0.05. Let's aim for 0.04
    delta_days = -math.log(0.04) / 0.01
    past = now - timedelta(days=delta_days)
    
    # recency ~ 0.04 -> ARCHIVED
    assert determine_memory_state(past, now, frequency=100, decay_lambda=0.01) == MemoryState.ARCHIVED

def test_current_time_before_last_seen():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=10)
    # recency should clamp delta_t < 0 to 0.0 -> recency 1.0 -> HOT
    assert determine_memory_state(future, now, frequency=1, decay_lambda=0.01) == MemoryState.HOT

def test_boundaries():
    now = datetime.now(timezone.utc)
    
    # Boundary 0.05
    d_005 = -math.log(0.05) / 0.01
    past_slightly_older = now - timedelta(days=d_005 + 1)
    assert determine_memory_state(past_slightly_older, now, 10, 0.01) == MemoryState.ARCHIVED
    
    past_slightly_newer = now - timedelta(days=d_005 - 1)
    assert determine_memory_state(past_slightly_newer, now, 10, 0.01) == MemoryState.COLD
    
    # Boundary 0.30
    d_030 = -math.log(0.30) / 0.01
    past_older_030 = now - timedelta(days=d_030 + 1)
    assert determine_memory_state(past_older_030, now, 10, 0.01) == MemoryState.COLD
    
    past_newer_030 = now - timedelta(days=d_030 - 1)
    assert determine_memory_state(past_newer_030, now, 10, 0.01) == MemoryState.WARM
    
    # Boundary 0.70
    d_070 = -math.log(0.70) / 0.01
    past_older_070 = now - timedelta(days=d_070 + 1)
    # Should be WARM (freq=10)
    assert determine_memory_state(past_older_070, now, 10, 0.01) == MemoryState.WARM
    
    past_newer_070 = now - timedelta(days=d_070 - 1)
    assert determine_memory_state(past_newer_070, now, 1, 0.01) == MemoryState.HOT
