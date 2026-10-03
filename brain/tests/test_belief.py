"""
Tests for Initial Belief Formation (V2.1)
"""

import uuid
import pytest
from models import AssociationType
from pattern import Pattern
from belief import Belief, form_beliefs

def create_mock_pattern(src, tgt, rel, pos, neg, strength, confidence, exps):
    return Pattern(
        association_id=uuid.uuid4(),
        source_node_id=src,
        target_node_id=tgt,
        relationship_type=rel,
        evidence_count=pos,
        negative_evidence=neg,
        association_strength=strength,
        confidence=confidence,
        supporting_experiences=exps
    )

def test_pattern_yields_belief():
    src = uuid.uuid4()
    tgt = uuid.uuid4()
    exps = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    
    pat = create_mock_pattern(src, tgt, AssociationType.CO_OCCURS_WITH, 3, 1, 0.8, 0.75, exps)
    beliefs = form_beliefs([pat])
    
    assert len(beliefs) == 1
    b = beliefs[0]
    
    # Check inherited properties
    assert b.subject == src
    assert b.object == tgt
    assert b.relationship_type == AssociationType.CO_OCCURS_WITH
    assert b.positive_evidence == 3
    assert b.negative_evidence == 1
    assert b.strength == 0.8
    assert b.confidence == 0.75
    assert b.supporting_experiences == exps
    assert b.source_pattern == pat

def test_duplicate_patterns_deduplicated():
    src = uuid.uuid4()
    tgt = uuid.uuid4()
    
    pat1 = create_mock_pattern(src, tgt, AssociationType.CO_OCCURS_WITH, 3, 1, 0.8, 0.75, [])
    pat2 = create_mock_pattern(src, tgt, AssociationType.CO_OCCURS_WITH, 4, 0, 0.9, 1.0, [])
    
    beliefs = form_beliefs([pat1, pat2])
    # Should only keep the first one encountered
    assert len(beliefs) == 1
    assert beliefs[0].positive_evidence == 3

def test_direction_is_maintained():
    A = uuid.uuid4()
    B = uuid.uuid4()
    
    pat1 = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 3, 0, 0.5, 1.0, [])
    pat2 = create_mock_pattern(B, A, AssociationType.CO_OCCURS_WITH, 3, 0, 0.5, 1.0, [])
    
    beliefs = form_beliefs([pat1, pat2])
    # Different direction = different identity -> 2 beliefs
    assert len(beliefs) == 2

def test_contradictions_allowed():
    A = uuid.uuid4()
    B = uuid.uuid4()
    
    # e.g., using different relationships
    pat1 = create_mock_pattern(A, B, AssociationType.CAUSES, 3, 0, 0.5, 1.0, [])
    pat2 = create_mock_pattern(A, B, AssociationType.HAS_PROPERTY, 3, 0, 0.5, 1.0, [])
    
    beliefs = form_beliefs([pat1, pat2])
    # Different relationships = different identity -> 2 beliefs
    assert len(beliefs) == 2
    
def test_no_causal_hallucination():
    A = uuid.uuid4()
    B = uuid.uuid4()
    pat = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 3, 0, 0.5, 1.0, [])
    beliefs = form_beliefs([pat])
    
    assert beliefs[0].relationship_type == AssociationType.CO_OCCURS_WITH

def test_bounds_inherited():
    A = uuid.uuid4()
    B = uuid.uuid4()
    pat = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 3, 0, 1.0, 1.0, [])
    beliefs = form_beliefs([pat])
    
    assert 0.0 <= beliefs[0].confidence <= 1.0
    assert 0.0 <= beliefs[0].strength <= 1.0

from belief import form_assembly_beliefs, revise_assembly_belief
from pattern import AssemblyPattern, AssemblyMemberStruct

def create_mock_assembly_pattern(config_nodes, pos, neg, conf, exps):
    config = []
    for n in config_nodes:
        config.append(AssemblyMemberStruct(node_id=n, role='role', weight=1.0))
    return AssemblyPattern(
        configuration=config,
        evidence_count=pos,
        negative_evidence=neg,
        confidence=conf,
        supporting_experiences=exps
    )

def test_assembly_pattern_yields_assembly_belief():
    n1 = uuid.uuid4()
    n2 = uuid.uuid4()
    exps = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    
    pat = create_mock_assembly_pattern([n1, n2], 3, 0, 1.0, exps)
    beliefs = form_assembly_beliefs([pat])
    
    assert len(beliefs) == 1
    b = beliefs[0]
    
    assert len(b.configuration) == 2
    assert b.positive_evidence == 3
    assert b.negative_evidence == 0
    assert b.confidence == 1.0
    assert b.supporting_experiences == exps
    assert b.source_pattern == pat

def test_assembly_duplicate_patterns_deduplicated():
    n1 = uuid.uuid4()
    pat1 = create_mock_assembly_pattern([n1], 3, 0, 1.0, [])
    pat2 = create_mock_assembly_pattern([n1], 4, 0, 1.0, [])
    
    beliefs = form_assembly_beliefs([pat1, pat2])
    assert len(beliefs) == 1
    assert beliefs[0].positive_evidence == 3

def test_assembly_different_patterns_coexist():
    n1 = uuid.uuid4()
    n2 = uuid.uuid4()
    
    pat1 = create_mock_assembly_pattern([n1], 3, 0, 1.0, [])
    pat2 = create_mock_assembly_pattern([n1, n2], 3, 0, 1.0, [])
    
    beliefs = form_assembly_beliefs([pat1, pat2])
    assert len(beliefs) == 2

def test_revise_assembly_belief():
    n1 = uuid.uuid4()
    exp1 = uuid.uuid4()
    exp2 = uuid.uuid4()
    
    pat_old = create_mock_assembly_pattern([n1], 3, 0, 1.0, [exp1])
    pat_new = create_mock_assembly_pattern([n1], 4, 1, 0.8, [exp1, exp2])
    
    beliefs = form_assembly_beliefs([pat_old])
    b_old = beliefs[0]
    
    res = revise_assembly_belief(b_old, pat_new)
    
    assert res.changed is True
    assert res.revised_belief.positive_evidence == 4
    assert res.revised_belief.negative_evidence == 1
    assert res.revised_belief.confidence == 0.8
    assert len(res.revised_belief.supporting_experiences) == 2
    assert exp2 in res.revised_belief.supporting_experiences
