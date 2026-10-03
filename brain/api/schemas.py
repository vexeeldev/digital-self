from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID

class ExperienceCreate(BaseModel):
    raw_text: str

class ExperienceResponse(BaseModel):
    id: UUID
    raw_text: str
    occurred_at: Optional[str]
    created_at: str

class EvidenceSchema(BaseModel):
    source_type: str
    source_id: str
    relevance: float
    confidence: float
    supporting_experiences: List[str]

class InferenceSchema(BaseModel):
    statement: str
    supporting_evidence: List[EvidenceSchema]
    contradicting_evidence: List[EvidenceSchema]
    confidence: float
    provenance: List[str]

class ConflictSchema(BaseModel):
    id: str
    belief_a_id: str
    belief_b_id: str
    subject_id: str
    object_id: str

class ReasoningRequest(BaseModel):
    query: str
    context: Dict[str, Any] = Field(default_factory=dict)

class ReasoningResponse(BaseModel):
    inferences: List[InferenceSchema]
    evidence: List[EvidenceSchema]
    conflicts: List[ConflictSchema]
    confidence: float
    provenance: List[str]

class DecisionOptionSchema(BaseModel):
    id: str
    statement: str
    supporting_evidence: List[EvidenceSchema]
    contradicting_evidence: List[EvidenceSchema]
    score: float

class DecisionResponse(BaseModel):
    id: str
    selected_option: str
    alternatives: List[DecisionOptionSchema]
    confidence: float
    provenance: List[str]

class OutcomeCreate(BaseModel):
    decision_id: str
    observed_result: str
    evaluation: str

class OutcomeResponse(BaseModel):
    id: str
    decision_id: str
    observed_result: str
    evaluation: str
    evidence_weight: float
    provenance: List[str]
    learning_result: str

class CorrectionAdd(BaseModel):
    experience_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    association_type: str

class CorrectionUpdate(BaseModel):
    association_id: UUID
