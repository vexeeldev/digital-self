import hashlib
import uuid
from typing import Set, Dict, List, Tuple
from dataclasses import dataclass
from models import AssociationType
from belief import Belief, AssemblyBelief

# Explicit deterministic opposition configuration.
# Only relationships explicitly declared here can create a conflict.
OPPOSING_RELATIONSHIPS: Dict[AssociationType, Set[AssociationType]] = {
    AssociationType.SUPPORTS: {AssociationType.CONTRADICTS, AssociationType.WEAKENS},
    AssociationType.CONTRADICTS: {AssociationType.SUPPORTS},
    AssociationType.WEAKENS: {AssociationType.SUPPORTS},
    AssociationType.BEFORE: {AssociationType.AFTER},
    AssociationType.AFTER: {AssociationType.BEFORE},
    AssociationType.PART_OF: {AssociationType.CONTAINS},
    AssociationType.CONTAINS: {AssociationType.PART_OF},
}

@dataclass(frozen=True)
class BeliefConflict:
    id: str
    belief_a: Belief
    belief_b: Belief
    conflict_type: str
    subject: uuid.UUID
    object: uuid.UUID
    supporting_experiences_a: tuple
    supporting_experiences_b: tuple

def _generate_conflict_id(b1: Belief, b2: Belief) -> str:
    """
    Generates a deterministic ID for a conflict pair.
    The ID is symmetric: A vs B has the same ID as B vs A.
    """
    # Create canonical representations of each belief for hashing
    b1_repr = f"{b1.subject}_{b1.relationship_type.value}_{b1.object}"
    b2_repr = f"{b2.subject}_{b2.relationship_type.value}_{b2.object}"
    
    # Sort them to ensure symmetry
    pair = sorted([b1_repr, b2_repr])
    combined = f"{pair[0]}::vs::{pair[1]}"
    
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def detect_conflicts(beliefs: List[Belief]) -> List[BeliefConflict]:
    """
    Detects structural conflicts between beliefs.
    Operates on a list of active beliefs.
    """
    conflicts = []
    seen_ids = set()
    
    # Group by subject and object
    # Identity: A belief conflicts with another if they have the same subject and object
    # but their relationship_types are explicitly opposing.
    for i in range(len(beliefs)):
        for j in range(i + 1, len(beliefs)):
            b1 = beliefs[i]
            b2 = beliefs[j]
            
            # 1. Subject and object must match exactly
            if b1.subject != b2.subject or b1.object != b2.object:
                continue
                
            # 2. Check explicitly configured opposition
            rel_1 = b1.relationship_type
            rel_2 = b2.relationship_type
            
            opposing_to_1 = OPPOSING_RELATIONSHIPS.get(rel_1, set())
            
            if rel_2 in opposing_to_1:
                conflict_id = _generate_conflict_id(b1, b2)
                
                # Prevent duplicates
                if conflict_id in seen_ids:
                    continue
                seen_ids.add(conflict_id)
                
                # Sort beliefs deterministically to ensure output symmetry
                b1_repr = f"{b1.subject}_{b1.relationship_type.value}_{b1.object}"
                b2_repr = f"{b2.subject}_{b2.relationship_type.value}_{b2.object}"
                
                canonical_b1, canonical_b2 = (b1, b2) if b1_repr < b2_repr else (b2, b1)
                
                conflict = BeliefConflict(
                    id=conflict_id,
                    belief_a=canonical_b1,
                    belief_b=canonical_b2,
                    conflict_type="OPPOSING_RELATIONSHIP",
                    subject=canonical_b1.subject,
                    object=canonical_b1.object,
                    supporting_experiences_a=tuple(sorted(canonical_b1.supporting_experiences)),
                    supporting_experiences_b=tuple(sorted(canonical_b2.supporting_experiences))
                )
                conflicts.append(conflict)
                
    # Sort conflicts deterministically
    conflicts.sort(key=lambda c: c.id)
    return conflicts

def detect_assembly_conflicts(assembly_beliefs: List[AssemblyBelief]) -> List:
    """
    Detects conflicts between Assembly Beliefs.
    Note: Stage 17 AssemblyBelief is purely structural (nodes, roles, weights).
    It contains no opposing relationship field. 
    Therefore, AssemblyBelief conflict detection is not applicable yet.
    Returns an empty list.
    """
    return []
