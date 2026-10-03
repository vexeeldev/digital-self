import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from psycopg2.extensions import connection

from reasoning import ReasoningQuery, ReasoningEngine, Evidence, Inference
from learning import record_positive_evidence, record_negative_evidence

@dataclass(frozen=True)
class DecisionOption:
    id: str
    statement: str
    supporting_evidence: tuple
    contradicting_evidence: tuple
    score: float

@dataclass(frozen=True)
class Decision:
    id: str
    selected_option: str
    alternatives: tuple
    reasoning: object
    confidence: float
    provenance: tuple

@dataclass(frozen=True)
class Outcome:
    id: str
    decision_id: str
    observed_result: str
    evaluation: str
    evidence_weight: float
    provenance: tuple

def evaluate_decision(inferences: List[Inference]) -> Decision:
    """
    Evaluates reasoning inferences to produce a deterministic decision.
    Baseline formula: score = support_score - contradiction_score
    """
    options = []
    for inf in inferences:
        if inf.statement == "NO_SUFFICIENT_EVIDENCE":
            continue
            
        supp_score = sum(e.confidence for e in inf.supporting_evidence)
        con_score = sum(e.confidence for e in inf.contradicting_evidence)
        score = supp_score - con_score
        
        opt_id = uuid.uuid5(uuid.NAMESPACE_OID, inf.statement).hex
        opt = DecisionOption(
            id=opt_id,
            statement=inf.statement,
            supporting_evidence=inf.supporting_evidence,
            contradicting_evidence=inf.contradicting_evidence,
            score=score
        )
        options.append(opt)
        
    if not options:
        # NO_SUFFICIENT_EVIDENCE produces NO_DECISION
        return Decision(
            id=uuid.uuid5(uuid.NAMESPACE_OID, "NO_DECISION").hex,
            selected_option="NO_DECISION",
            alternatives=(),
            reasoning=inferences,
            confidence=0.0,
            provenance=()
        )
        
    # Sort deterministically: highest score first, then lexicographically by ID for tie-breaking
    options.sort(key=lambda o: (-o.score, o.id))
    selected = options[0]
    
    # Confidence represents confidence in the decision under current evidence: support / (support + contradiction)
    supp_score = sum(e.confidence for e in selected.supporting_evidence)
    con_score = sum(e.confidence for e in selected.contradicting_evidence)
    denom = supp_score + con_score
    confidence = (supp_score / denom) if denom > 0 else 0.0
    
    return Decision(
        id=uuid.uuid5(uuid.NAMESPACE_OID, selected.id).hex,
        selected_option=selected.statement,
        alternatives=tuple(options),
        reasoning=inferences,
        confidence=confidence,
        provenance=tuple(set(selected.supporting_evidence + selected.contradicting_evidence))
    )

def evaluate_outcome(decision: Decision, observed_result: str, evaluation: str, evidence_weight: float = 1.0) -> Outcome:
    """
    Represents what was observed after the decision.
    evaluation must be SUCCESS, PARTIAL, FAILURE, UNKNOWN.
    """
    if evaluation not in ("SUCCESS", "PARTIAL", "FAILURE", "UNKNOWN"):
        raise ValueError("Invalid evaluation category")
        
    return Outcome(
        id=uuid.uuid5(uuid.NAMESPACE_OID, decision.id + observed_result + evaluation).hex,
        decision_id=decision.id,
        observed_result=observed_result,
        evaluation=evaluation,
        evidence_weight=evidence_weight,
        provenance=decision.provenance
    )

def learn_from_outcome(conn: connection, outcome: Outcome) -> str:
    """
    Applies outcome evidence back to the existing mutable structures.
    Uses Stage 6 association learning formulas.
    """
    if outcome.evaluation in ("UNKNOWN", "PARTIAL"):
        return "NO_LEARNING_TARGET"
        
    # Identify target associations explicitly linked to the Decision's reasoning provenance
    targets = set()
    for ev in outcome.provenance:
        if ev.source_type == "BELIEF":
            # source_id format: subj_rel_obj
            parts = ev.source_id.split("_")
            if len(parts) >= 3:
                subj = parts[0]
                obj = parts[-1]
                rel = "_".join(parts[1:-1])
                
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT a.id FROM associations a
                        JOIN vw_active_experience_associations ea ON a.id = ea.association_id
                        WHERE a.source_node_id = %s AND a.target_node_id = %s AND a.type = %s
                        LIMIT 1
                    """, (subj, obj, rel))
                    row = cur.fetchone()
                    if row:
                        targets.add(row[0])
                        
    if not targets:
        return "NO_LEARNING_TARGET"
        
    # We create ONE experience to represent this outcome
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO experiences (raw_text)
            VALUES (%s)
            RETURNING id
        """, (f"Outcome Evaluation: {outcome.observed_result}",))
        exp_id = cur.fetchone()[0]
        
    is_positive = (outcome.evaluation == "SUCCESS")
    
    for assoc_id in targets:
        if is_positive:
            record_positive_evidence(conn, uuid.UUID(str(assoc_id)), uuid.UUID(exp_id), weight=outcome.evidence_weight)
        else:
            record_negative_evidence(conn, uuid.UUID(str(assoc_id)), uuid.UUID(exp_id), weight=outcome.evidence_weight)
            
    return "LEARNING_APPLIED"
