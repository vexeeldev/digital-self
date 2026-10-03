"""
Tests for Initial Belief Revision (V2.1)
"""

import uuid
import pytest
from models import AssociationType
from pattern import Pattern
from belief import Belief, form_beliefs, revise_belief, BeliefRevisionResult

def create_mock_pattern(src, tgt, rel, pos, neg, strength, exps):
    denominator = pos + neg
    confidence = (pos / denominator) if denominator > 0 else 0.0
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

def test_positive_evidence_increase():
    A = uuid.uuid4()
    B = uuid.uuid4()
    exp1 = uuid.uuid4()
    exp2 = uuid.uuid4()
    
    pat1 = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 3, 0, 0.6, [exp1])
    b1 = form_beliefs([pat1])[0]
    
    assert b1.confidence == 1.0
    assert b1.positive_evidence == 3
    
    # New pattern with more positive evidence
    pat2 = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 4, 0, 0.7, [exp2])
    
    rev_res = revise_belief(b1, pat2)
    
    # Previous unchanged (immutability)
    assert rev_res.previous_belief == b1
    assert b1.positive_evidence == 3
    
    # Revised
    assert rev_res.changed is True
    assert rev_res.evidence_delta['positive'] == 1
    assert rev_res.evidence_delta['negative'] == 0
    assert rev_res.revised_belief.positive_evidence == 4
    assert rev_res.revised_belief.confidence == 1.0
    assert rev_res.revised_belief.strength == 0.7
    
    # Provenance
    assert exp1 in rev_res.provenance
    assert exp2 in rev_res.provenance
    assert len(rev_res.provenance) == 2

def test_negative_evidence_increase():
    A = uuid.uuid4()
    B = uuid.uuid4()
    
    pat1 = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 3, 0, 0.6, [])
    b1 = form_beliefs([pat1])[0]
    
    pat2 = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 3, 1, 0.6, [])
    rev_res = revise_belief(b1, pat2)
    
    assert rev_res.evidence_delta['negative'] == 1
    assert rev_res.evidence_delta['positive'] == 0
    assert rev_res.revised_belief.confidence == 0.75
    assert rev_res.revised_belief.negative_evidence == 1

def test_identity_mismatch_rejected():
    A = uuid.uuid4()
    B = uuid.uuid4()
    C = uuid.uuid4()
    
    pat1 = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 3, 0, 0.6, [])
    b1 = form_beliefs([pat1])[0]
    
    # Mismatch Object
    pat2 = create_mock_pattern(A, C, AssociationType.CO_OCCURS_WITH, 4, 0, 0.7, [])
    
    with pytest.raises(ValueError, match="Identity mismatch"):
        revise_belief(b1, pat2)
        
def test_zero_denominator():
    A = uuid.uuid4()
    B = uuid.uuid4()
    
    pat1 = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 3, 0, 0.6, [])
    b1 = form_beliefs([pat1])[0]
    
    pat2 = create_mock_pattern(A, B, AssociationType.CO_OCCURS_WITH, 0, 0, 0.0, [])
    
    rev_res = revise_belief(b1, pat2)
    assert rev_res.revised_belief.confidence == 0.0
    
def test_contradiction_does_not_mutate_other_beliefs():
    A = uuid.uuid4()
    B = uuid.uuid4()
    
    pat1 = create_mock_pattern(A, B, AssociationType.HAS_PROPERTY, 3, 0, 0.6, [])
    b1 = form_beliefs([pat1])[0]
    
    # We update a contradictory belief (different relation)
    pat2_dislikes = create_mock_pattern(A, B, AssociationType.CAUSES, 4, 0, 0.8, [])
    
    # Trying to update 'has_property' with 'causes' pattern raises identity error
    with pytest.raises(ValueError):
        revise_belief(b1, pat2_dislikes)
