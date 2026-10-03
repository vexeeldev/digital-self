from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extensions import connection

from api.schemas import ReasoningRequest, DecisionResponse, DecisionOptionSchema, EvidenceSchema
from api.deps import get_db
from reasoning import ReasoningEngine, ReasoningQuery
from decision import evaluate_decision

router = APIRouter(prefix="/decisions", tags=["Decisions"])

def _serialize_evidence(ev):
    return EvidenceSchema(
        source_type=ev.source_type,
        source_id=ev.source_id,
        relevance=ev.relevance,
        confidence=ev.confidence,
        supporting_experiences=[str(e) for e in ev.supporting_experiences]
    )

@router.post("", response_model=DecisionResponse)
def make_decision(request: ReasoningRequest, db: connection = Depends(get_db)):
    try:
        query = ReasoningQuery(text=request.query, context=request.context)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        
    engine = ReasoningEngine(db)
    
    try:
        engine.build_context(query)
        inferences = engine.reason(query)
        
        # Call the existing decision service
        decision = evaluate_decision(inferences)
        
        return DecisionResponse(
            id=decision.id,
            selected_option=decision.selected_option,
            alternatives=[
                DecisionOptionSchema(
                    id=opt.id,
                    statement=opt.statement,
                    supporting_evidence=[_serialize_evidence(e) for e in opt.supporting_evidence],
                    contradicting_evidence=[_serialize_evidence(e) for e in opt.contradicting_evidence],
                    score=opt.score
                ) for opt in decision.alternatives
            ],
            confidence=decision.confidence,
            provenance=[str(p) for p in decision.provenance]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
