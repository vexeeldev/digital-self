"""
Digital Self — belief.py
Version: V2.1 — Initial Belief Formation

Derives high-level Beliefs from Patterns deterministically.
Does NOT modify database schema or records.
"""

import uuid
from pydantic import BaseModel
from models import AssociationType
from pattern import Pattern

class Belief(BaseModel):
    """
    Derived in-memory representation of a Belief.
    A Belief is a direct generalization of a Pattern, without causal hallucination.
    """
    subject: uuid.UUID
    relationship_type: AssociationType
    object: uuid.UUID
    confidence: float
    strength: float
    positive_evidence: int
    negative_evidence: int
    supporting_experiences: list[uuid.UUID]
    source_pattern: Pattern

def form_beliefs(patterns: list[Pattern]) -> list[Belief]:
    """
    Forms Beliefs deterministically from Patterns.
    - Inherits properties identically.
    - Deduplicates identical patterns.
    - Allows contradictions (A -> likes -> B AND A -> dislikes -> B both form beliefs).
    """
    beliefs = []
    seen_identities = set()
    
    for pat in patterns:
        # Identity: subject + relationship_type + object
        identity = (pat.source_node_id, pat.relationship_type, pat.target_node_id)
        
        if identity in seen_identities:
            continue
            
        seen_identities.add(identity)
        
        belief = Belief(
            subject=pat.source_node_id,
            relationship_type=pat.relationship_type,
            object=pat.target_node_id,
            confidence=pat.confidence,
            strength=pat.association_strength,
            positive_evidence=pat.evidence_count,
            negative_evidence=pat.negative_evidence,
            supporting_experiences=pat.supporting_experiences,
            source_pattern=pat
        )
        beliefs.append(belief)
        
    return beliefs

class BeliefRevisionResult(BaseModel):
    previous_belief: Belief
    revised_belief: Belief
    evidence_delta: dict[str, int]
    changed: bool
    provenance: list[uuid.UUID]

def revise_belief(belief: Belief, updated_pattern: Pattern) -> BeliefRevisionResult:
    """
    Revises a belief deterministically based on an updated pattern.
    Produces a new revised belief object, leaving the previous belief intact.
    Raises ValueError if identity mismatch.
    """
    if (belief.subject != updated_pattern.source_node_id or
        belief.relationship_type != updated_pattern.relationship_type or
        belief.object != updated_pattern.target_node_id):
        raise ValueError("Identity mismatch: updated pattern does not match belief identity.")
        
    pos_delta = updated_pattern.evidence_count - belief.positive_evidence
    neg_delta = updated_pattern.negative_evidence - belief.negative_evidence
    changed = (pos_delta != 0 or neg_delta != 0 or belief.strength != updated_pattern.association_strength)
    
    pos_ev = updated_pattern.evidence_count
    neg_ev = updated_pattern.negative_evidence
    denominator = pos_ev + neg_ev
    if denominator == 0:
        new_confidence = 0.0
    else:
        new_confidence = max(0.0, min(1.0, pos_ev / denominator))
        
    combined_provenance = list(set(belief.supporting_experiences + updated_pattern.supporting_experiences))
    
    revised = Belief(
        subject=belief.subject,
        relationship_type=belief.relationship_type,
        object=belief.object,
        confidence=new_confidence,
        strength=updated_pattern.association_strength,
        positive_evidence=pos_ev,
        negative_evidence=neg_ev,
        supporting_experiences=combined_provenance,
        source_pattern=updated_pattern
    )
    
    return BeliefRevisionResult(
        previous_belief=belief,
        revised_belief=revised,
        evidence_delta={"positive": pos_delta, "negative": neg_delta},
        changed=changed,
        provenance=combined_provenance
    )

from pattern import AssemblyPattern, AssemblyMemberStruct

class AssemblyBelief(BaseModel):
    """
    Derived in-memory representation of an Assembly Belief.
    A Belief is a direct generalization of an Assembly Pattern, without causal hallucination.
    """
    configuration: list[AssemblyMemberStruct]
    confidence: float
    positive_evidence: int
    negative_evidence: int
    supporting_experiences: list[uuid.UUID]
    source_pattern: AssemblyPattern

def form_assembly_beliefs(patterns: list[AssemblyPattern]) -> list[AssemblyBelief]:
    """
    Forms AssemblyBeliefs deterministically from AssemblyPatterns.
    - Inherits properties identically.
    - Deduplicates identical patterns.
    """
    beliefs = []
    seen_identities = set()
    
    for pat in patterns:
        identity = tuple(pat.configuration)
        
        if identity in seen_identities:
            continue
            
        seen_identities.add(identity)
        
        belief = AssemblyBelief(
            configuration=pat.configuration,
            confidence=pat.confidence,
            positive_evidence=pat.evidence_count,
            negative_evidence=pat.negative_evidence,
            supporting_experiences=pat.supporting_experiences,
            source_pattern=pat
        )
        beliefs.append(belief)
        
    return beliefs

class AssemblyBeliefRevisionResult(BaseModel):
    previous_belief: AssemblyBelief
    revised_belief: AssemblyBelief
    evidence_delta: dict[str, int]
    changed: bool
    provenance: list[uuid.UUID]

def revise_assembly_belief(belief: AssemblyBelief, updated_pattern: AssemblyPattern) -> AssemblyBeliefRevisionResult:
    """
    Revises an assembly belief deterministically based on an updated pattern.
    """
    if tuple(belief.configuration) != tuple(updated_pattern.configuration):
        raise ValueError("Identity mismatch: updated pattern does not match belief identity.")
        
    pos_delta = updated_pattern.evidence_count - belief.positive_evidence
    neg_delta = updated_pattern.negative_evidence - belief.negative_evidence
    changed = (pos_delta != 0 or neg_delta != 0)
    
    pos_ev = updated_pattern.evidence_count
    neg_ev = updated_pattern.negative_evidence
    denominator = pos_ev + neg_ev
    if denominator == 0:
        new_confidence = 0.0
    else:
        new_confidence = max(0.0, min(1.0, pos_ev / denominator))
        
    combined_provenance = list(set(belief.supporting_experiences + updated_pattern.supporting_experiences))
    
    revised = AssemblyBelief(
        configuration=belief.configuration,
        confidence=new_confidence,
        positive_evidence=pos_ev,
        negative_evidence=neg_ev,
        supporting_experiences=combined_provenance,
        source_pattern=updated_pattern
    )
    
    return AssemblyBeliefRevisionResult(
        previous_belief=belief,
        revised_belief=revised,
        evidence_delta={"positive": pos_delta, "negative": neg_delta},
        changed=changed,
        provenance=combined_provenance
    )
