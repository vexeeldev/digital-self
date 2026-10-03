import uuid
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_api_decisions_and_outcomes():
    # 11. Valid reasoning produces Decision.
    response = client.post("/decisions", json={"query": "Test decision", "context": {}})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "selected_option" in data
    
    # 12. Insufficient evidence remains representable.
    # Since there is no data for "Test decision", it should return NO_DECISION
    assert data["selected_option"] == "NO_DECISION"
    
    # 13. Decision provenance preserved.
    assert "provenance" in data
    
    dec_id = data["id"]
    
    # Outcome API Tests
    # 14. SUCCESS accepted.
    res_success = client.post("/outcomes", json={"decision_id": dec_id, "observed_result": "Success outcome", "evaluation": "SUCCESS"})
    assert res_success.status_code == 201
    assert res_success.json()["evaluation"] == "SUCCESS"
    
    # 15. FAILURE accepted.
    res_fail = client.post("/outcomes", json={"decision_id": dec_id, "observed_result": "Fail outcome", "evaluation": "FAILURE"})
    assert res_fail.status_code == 201
    
    # 16. PARTIAL accepted.
    res_partial = client.post("/outcomes", json={"decision_id": dec_id, "observed_result": "Partial outcome", "evaluation": "PARTIAL"})
    assert res_partial.status_code == 201
    
    # 17. UNKNOWN accepted.
    res_unk = client.post("/outcomes", json={"decision_id": dec_id, "observed_result": "Unknown outcome", "evaluation": "UNKNOWN"})
    assert res_unk.status_code == 201
    
    # 18. Invalid evaluation rejected.
    res_inv = client.post("/outcomes", json={"decision_id": dec_id, "observed_result": "Invalid outcome", "evaluation": "INVALID"})
    assert res_inv.status_code == 422
    
    # 19. Outcome triggers existing learning path.
    # We can verify it returns learning_result string. 
    # For a NO_DECISION, provenance is empty, so learning_result will be NO_LEARNING_TARGET
    assert res_success.json()["learning_result"] in ["NO_LEARNING_TARGET", "LEARNING_APPLIED"]
    
    # 20. Provenance preserved.
    assert "provenance" in res_success.json()
