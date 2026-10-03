from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extensions import connection

from api.schemas import ReasoningRequest, ReasoningResponse, InferenceSchema, EvidenceSchema, ConflictSchema
from api.deps import get_db
from reasoning import ReasoningEngine, ReasoningQuery

router = APIRouter(prefix="/reasoning", tags=["Reasoning"])

def _serialize_evidence(ev):
    return EvidenceSchema(
        source_type=ev.source_type,
        source_id=ev.source_id,
        relevance=ev.relevance,
        confidence=ev.confidence,
        supporting_experiences=[str(e) for e in ev.supporting_experiences]
    )

@router.post("", response_model=ReasoningResponse)
def reason(request: ReasoningRequest, db: connection = Depends(get_db)):
    try:
        query = ReasoningQuery(text=request.query, context=request.context)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        
    engine = ReasoningEngine(db)
    
    try:
        ctx = engine.build_context(query)
        inferences = engine.reason(query)
        
        # We need to construct ReasoningResponse
        # To calculate global confidence, we could average inference confidences or return max.
        # But ReasoningResponse requires `confidence` - maybe just 0.0 or max
        # Wait, the prompt says "Return structured information such as... confidence: 0.0"
        global_confidence = max([inf.confidence for inf in inferences], default=0.0)
        global_provenance = set()
        for inf in inferences:
            global_provenance.update(inf.provenance)
            
        return ReasoningResponse(
            inferences=[
                InferenceSchema(
                    statement=inf.statement,
                    supporting_evidence=[_serialize_evidence(e) for e in inf.supporting_evidence],
                    contradicting_evidence=[_serialize_evidence(e) for e in inf.contradicting_evidence],
                    confidence=inf.confidence,
                    provenance=[str(p) for p in inf.provenance]
                ) for inf in inferences
            ],
            evidence=[], # Can be populated with all ctx.relevant_beliefs or empty
            conflicts=[
                ConflictSchema(
                    id=c.id,
                    belief_a_id=f"{c.belief_a.subject}_{c.belief_a.relationship_type.value}_{c.belief_a.object}",
                    belief_b_id=f"{c.belief_b.subject}_{c.belief_b.relationship_type.value}_{c.belief_b.object}",
                    subject_id=str(c.subject),
                    object_id=str(c.object)
                ) for c in ctx.conflicts
            ],
            confidence=global_confidence,
            provenance=[str(p) for p in global_provenance]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
