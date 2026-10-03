"""
Digital Self — models.py
Version: V2.1 — Initial Technical Contract
Based on: PRD V1, PRD V2, PRD V2.1

Domain models using Pydantic V2.
These models mirror the schema defined in schema.sql.

Scope: Three foundational entities only.
  - Experience         : Immutable raw experience record
  - Node               : Concept/entity discovered from an experience
  - Association        : Typed, weighted relationship between two nodes
  - ExperienceAssociation : Provenance bridge record

Out of scope (not implemented until foundation is validated):
  - Pattern, Belief, Decision, Assembly, InternalState
  - Reasoning engine, LLM pipeline, consolidation engine

PRD Principles reflected in these models:
  [P1] raw_text stored as-is — no modification in the model layer.
  [P2] Association.source_experience_id is required (provenance, not optional).
  [P3] occurred_at is Optional[datetime] — user may not specify when it happened.
  [P4] AI-derived fields (confidence, activation) are floats with bounded ranges.
  [P5] positive_evidence and negative_evidence coexist (contradiction model).
  [P6] Association.type defaults to 'co_occurs_with', not 'causes'.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Utility
# =============================================================================

def _now_utc() -> datetime:
    """Return the current time in UTC. Used as a default factory."""
    return datetime.now(tz=timezone.utc)


# =============================================================================
# Enums
# Mirrors the PostgreSQL ENUM types defined in schema.sql.
# =============================================================================

class NodeType(str, Enum):
    """
    Semantic type of a node.
    Defined in PRD V1 §5.8 and PRD V2.1 §5.
    """
    PERSON  = "person"
    PLACE   = "place"
    OBJECT  = "object"
    EVENT   = "event"
    EMOTION = "emotion"
    ACTION  = "action"
    CONCEPT = "concept"


class AssociationType(str, Enum):
    """
    Relationship taxonomy for associations.
    Defined in PRD V2 §7.

    [P6] Default for AI-inferred associations: CO_OCCURS_WITH.
    Causal relationships require stronger or explicit evidence (PRD V2 §8).
    """
    # Causal / correlational
    CAUSES          = "causes"
    CORRELATES_WITH = "correlates_with"
    CO_OCCURS_WITH  = "co_occurs_with"   # Safe default — do not promote to CAUSES easily

    # Temporal
    BEFORE   = "before"
    AFTER    = "after"
    DURING   = "during"
    OVERLAPS = "overlaps"

    # Compositional
    PART_OF  = "part_of"
    CONTAINS = "contains"

    # Taxonomic
    INSTANCE_OF  = "instance_of"
    IS_A         = "is_a"
    HAS_PROPERTY = "has_property"

    # Situational
    LOCATED_AT = "located_at"
    INVOLVES   = "involves"

    # Epistemic
    SIMILAR_TO  = "similar_to"
    CONTRADICTS = "contradicts"
    SUPPORTS    = "supports"
    WEAKENS     = "weakens"

    # Fallback
    ASSOCIATED_WITH = "associated_with"


# =============================================================================
# Bounded float type alias
# PRD specifies confidence and activation in range [0.0, 1.0].
# Pydantic's Field(..., ge=0.0, le=1.0) enforces this at runtime.
# =============================================================================

def _bounded_float(default: float) -> Any:
    """Helper for fields constrained to [0.0, 1.0]."""
    return Field(default=default, ge=0.0, le=1.0)


# =============================================================================
# Experience
# PRD V1 §5.1, PRD V2 §5, PRD V2.1 §4
# =============================================================================

class ExperienceCreate(BaseModel):
    """
    Input model for creating a new Experience.
    Used when the user submits a raw experience to the system.

    Only accepts fields that come from the user.
    System-generated fields (id, created_at) are not accepted here.
    """
    # [P1] The user's exact words — never modified by the system.
    raw_text: str = Field(..., min_length=1, description="Exact text of the experience as submitted by the user.")

    # [P3] When the experience actually happened.
    # Optional: user may not know or may not specify a time.
    occurred_at: Optional[datetime] = Field(
        default=None,
        description="When the experience actually occurred. May differ from created_at."
    )

    # Unstructured additional context.
    # PRD V2.1 does not specify internal structure of metadata.
    # JSONB in the database; dict here.
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional unstructured metadata (location, activity context, etc.)."
    )

    @field_validator("raw_text")
    @classmethod
    def raw_text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_text must not be blank or whitespace only.")
        return v


class Experience(BaseModel):
    """
    Full Experience record as stored in the database.
    Includes system-generated fields (id, created_at).
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    # [P1] Immutable raw experience text.
    raw_text: str

    # [P3] When the experience actually happened (user-specified or inferred).
    occurred_at: Optional[datetime] = None

    # [P3] When this record was created in the system.
    created_at: datetime = Field(default_factory=_now_utc)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# =============================================================================
# Node
# PRD V1 §5.8, PRD V2 §10, PRD V2.1 §5
# =============================================================================

class NodeCreate(BaseModel):
    """
    Input model for creating a new Node.
    Used when the interpretation layer identifies a new concept from an experience.

    Note: initial confidence should be moderate (0.5) because the node was
    just discovered from a single experience — not yet confirmed by multiple.
    """
    type: NodeType = Field(..., description="Semantic type of this node.")

    name: str = Field(..., min_length=1, description="Canonical name of this node (e.g., 'Office', 'Annoyance').")

    # [P4] Moderate default — one experience is not enough to be highly confident.
    confidence: float = _bounded_float(0.500)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank or whitespace only.")
        return v


class Node(BaseModel):
    """
    Full Node record as stored in the database.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    type: NodeType

    # Canonical name. Not necessarily unique (entity resolution is out of scope for V2.1).
    name: str

    # [P4] How confident the system is that this node is correctly identified.
    confidence: float = _bounded_float(0.500)

    # Current activation level. Decays over time per params.yaml decay_lambda.
    activation: float = _bounded_float(0.000)

    # When this node was first observed from any experience.
    first_seen: datetime = Field(default_factory=_now_utc)

    # When this node was most recently referenced.
    last_seen: datetime = Field(default_factory=_now_utc)

    @model_validator(mode="after")
    def last_seen_not_before_first_seen(self) -> "Node":
        if self.last_seen < self.first_seen:
            raise ValueError("last_seen must not be earlier than first_seen.")
        return self

    model_config = {"from_attributes": True}


# =============================================================================
# Association
# PRD V1 §5.9, PRD V2 §7, §11, §12, PRD V2.1 §6
# =============================================================================

class AssociationCreate(BaseModel):
    """
    Input model for creating a new Association.
    Used when the system detects a relationship between two nodes
    based on a specific experience.

    source_experience_id is REQUIRED — no association without provenance (PRD V2 §2).
    """
    source_node_id: uuid.UUID = Field(..., description="The 'from' node in the relationship.")
    target_node_id: uuid.UUID = Field(..., description="The 'to' node in the relationship.")

    # [P6] Default is CO_OCCURS_WITH — safest inference without explicit evidence.
    # Use CAUSES only when the user explicitly states causality.
    type: AssociationType = Field(
        default=AssociationType.CO_OCCURS_WITH,
        description="Relationship type. Defaults to co_occurs_with."
    )

    # Initial strength. Low by default — a single observation is weak evidence.
    strength: float = _bounded_float(0.100)

    # [P4] Initial confidence. Moderate — one experience is not conclusive.
    confidence: float = _bounded_float(0.500)

    # [P2] PROVENANCE REQUIRED: The experience that created this association.
    source_experience_id: uuid.UUID = Field(
        ...,
        description="The experience that caused this association to be created. Required."
    )

    @model_validator(mode="after")
    def nodes_are_different(self) -> "AssociationCreate":
        if self.source_node_id == self.target_node_id:
            raise ValueError("source_node_id and target_node_id must be different.")
        return self


class Association(BaseModel):
    """
    Full Association record as stored in the database.

    NOTE on positive_evidence / negative_evidence:
      PRD V2 §11 lists these explicitly in the Association Data Model.
      PRD V2.1 §6 does not repeat them but PRD V1 §4.4 ("Contradictions Are Allowed")
      and PRD V2 §15 (Contradiction Model) require them to be tracked.
      Their inclusion here is not scope creep — it is a requirement of the core model.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    source_node_id: uuid.UUID
    target_node_id: uuid.UUID

    # [P6] Relationship type. Defaults to CO_OCCURS_WITH.
    type: AssociationType = AssociationType.CO_OCCURS_WITH

    # How strong this relationship is believed to be. Range: [0.0, 1.0].
    # Updated via: s_new = s_old + α × w × (1 - s_old) for positive evidence.
    # Updated via: s_new = s_old - β × w × s_old for negative evidence.
    # Decays via:  s_new = s_old × exp(-λ × Δt)
    strength: float = _bounded_float(0.100)

    # [P4] How confident the system is in this association. Range: [0.0, 1.0].
    # Distinct from strength (see PRD V2 §14).
    confidence: float = _bounded_float(0.500)

    # [P5] Count of experiences that SUPPORTED this relationship.
    positive_evidence: int = Field(default=1, ge=0)

    # [P5] Count of experiences that CONTRADICTED this relationship.
    # Contradictions are stored, not erased (PRD V1 §4.4).
    negative_evidence: int = Field(default=0, ge=0)

    # [P2] The first experience that created this association.
    source_experience_id: uuid.UUID

    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)

    @model_validator(mode="after")
    def nodes_are_different(self) -> "Association":
        if self.source_node_id == self.target_node_id:
            raise ValueError("source_node_id and target_node_id must be different.")
        return self

    model_config = {"from_attributes": True}


# =============================================================================
# ExperienceAssociation (Provenance Bridge)
# PRD V2 §11, PRD V1 §4.3, PRD V2 §50
# =============================================================================

class ExperienceAssociationCreate(BaseModel):
    """
    Input model for creating a provenance link between an experience and an association.
    Used when an experience contributes evidence (positive or negative) to an association.
    """
    experience_id:  uuid.UUID = Field(..., description="The experience providing evidence.")
    association_id: uuid.UUID = Field(..., description="The association receiving the evidence.")

    # True if this experience strengthened the association.
    # False if this experience contradicted or weakened it.
    is_positive: bool = Field(
        default=True,
        description="Whether this experience supports (True) or contradicts (False) the association."
    )


class ExperienceAssociation(BaseModel):
    """
    Full provenance bridge record as stored in the database.
    Links an experience to an association and records whether it was supporting
    or contradicting evidence.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    experience_id:  uuid.UUID
    association_id: uuid.UUID
    is_positive:    bool = True
    created_at:     datetime = Field(default_factory=_now_utc)

    model_config = {"from_attributes": True}


# =============================================================================
# ExperienceNode (Node Provenance Bridge)
# =============================================================================

class ExperienceNodeCreate(BaseModel):
    """
    Input model for creating a provenance link between an experience and a node.
    """
    experience_id: uuid.UUID = Field(..., description="The experience from which the node was extracted.")
    node_id:       uuid.UUID = Field(..., description="The node that was extracted.")


class ExperienceNode(BaseModel):
    """
    Full provenance bridge record for nodes as stored in the database.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    experience_id: uuid.UUID
    node_id:       uuid.UUID
    created_at:    datetime = Field(default_factory=_now_utc)

    model_config = {"from_attributes": True}

# =============================================================================
# Assembly
# =============================================================================

class AssemblyMember(BaseModel):
    id: uuid.UUID
    assembly_id: uuid.UUID
    node_id: uuid.UUID
    role: str
    weight: float = _bounded_float(1.0)
    created_at: datetime

class Assembly(BaseModel):
    id: uuid.UUID
    experience_id: uuid.UUID
    context_summary: str
    confidence: float = _bounded_float(0.5)
    created_at: datetime
    members: list[AssemblyMember] = Field(default_factory=list)

class ExtractedAssemblyMember(BaseModel):
    node_name: str = Field(..., description="The exact canonical name of the node from the provided list")
    role: str = Field(..., description="The role of the node in this episode")
    weight: float = Field(..., ge=0.0, le=1.0, description="Significance of this node in the episode")

class AssemblyExtractionResult(BaseModel):
    context_summary: str = Field(..., description="A short summary of the holistic context of the episode")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this interpretation")
    members: list[ExtractedAssemblyMember] = Field(..., description="List of nodes participating in this episode")

# =============================================================================
# END OF MODELS
# =============================================================================
