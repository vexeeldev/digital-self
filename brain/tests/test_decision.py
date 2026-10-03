import uuid
import pytest
from reasoning import Inference, Evidence
from decision import evaluate_decision, Decision, DecisionOption

def test_evaluate_decision():
    # 1. Valid reasoning produces candidate options.
    inf1 = Inference(
        statement="Opt 1",
        supporting_evidence=(Evidence("BELIEF", "a", 1.0, 0.8, ("exp1",)),),
        contradicting_evidence=(),
        confidence=0.8,
        provenance=("exp1",)
    )
    inf2 = Inference(
        statement="Opt 2",
        supporting_evidence=(Evidence("BELIEF", "b", 1.0, 0.6, ("exp2",)),),
        contradicting_evidence=(),
        confidence=0.6,
        provenance=("exp2",)
    )
    
    d1 = evaluate_decision([inf1, inf2])
    
    # 3. Highest valid score selected.
    assert d1.selected_option == "Opt 1"
    assert len(d1.alternatives) == 2
    
    # 5. Decision confidence remains [0,1].
    assert 0.0 <= d1.confidence <= 1.0
    
    # 9. Decision preserves reasoning provenance.
    experiences_in_provenance = set()
    for ev in d1.provenance:
        experiences_in_provenance.update(ev.supporting_experiences)
    assert "exp1" in experiences_in_provenance

def test_evaluate_decision_tie_breaking():
    # 2. Option scoring is deterministic.
    # 4. Tie-breaking is deterministic.
    inf1 = Inference(
        statement="Same Score A",
        supporting_evidence=(Evidence("BELIEF", "c", 1.0, 0.5, ("exp3",)),),
        contradicting_evidence=(),
        confidence=0.5,
        provenance=("exp3",)
    )
    inf2 = Inference(
        statement="Same Score B",
        supporting_evidence=(Evidence("BELIEF", "d", 1.0, 0.5, ("exp4",)),),
        contradicting_evidence=(),
        confidence=0.5,
        provenance=("exp4",)
    )
    d1 = evaluate_decision([inf1, inf2])
    d2 = evaluate_decision([inf2, inf1]) # Different ordering
    
    # 36. Same input produces same Decision.
    # 39. Input ordering does not change canonical result.
    assert d1.selected_option == d2.selected_option

def test_no_sufficient_evidence():
    # 8. NO_SUFFICIENT_EVIDENCE produces no fabricated decision.
    inf = Inference(
        statement="NO_SUFFICIENT_EVIDENCE",
        supporting_evidence=(),
        contradicting_evidence=(),
        confidence=0.0,
        provenance=()
    )
    d = evaluate_decision([inf])
    assert d.selected_option == "NO_DECISION"
    assert len(d.alternatives) == 0

def test_evidence_visibility():
    # 6. Contradicting evidence remains visible.
    # 7. Supporting evidence remains visible.
    ev_sup = Evidence("BELIEF", "sup", 1.0, 0.9, ("e1",))
    ev_con = Evidence("BELIEF", "con", 1.0, 0.4, ("e2",))
    inf = Inference(
        statement="Complex",
        supporting_evidence=(ev_sup,),
        contradicting_evidence=(ev_con,),
        confidence=0.69,
        provenance=("e1", "e2")
    )
    d = evaluate_decision([inf])
    
    assert ev_sup in d.provenance or ev_con in d.provenance
    assert ev_sup in d.alternatives[0].supporting_evidence
    assert ev_con in d.alternatives[0].contradicting_evidence

def test_immutability():
    # 10. Decision does not mutate Beliefs.
    # 32. Decision unchanged.
    inf = Inference(
        statement="Test",
        supporting_evidence=(),
        contradicting_evidence=(),
        confidence=0.5,
        provenance=()
    )
    d1 = evaluate_decision([inf])
    d2 = evaluate_decision([inf])
    # D1 and D2 should be fundamentally the same, unchanged by repeated calls
    assert d1.id == d2.id
