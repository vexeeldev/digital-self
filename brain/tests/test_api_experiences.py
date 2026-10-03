import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_api_experiences():
    # 1. POST Experience succeeds.
    response = client.post("/experiences", json={"raw_text": "Api Test Experience"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    
    # 2. Raw text preserved exactly.
    assert data["raw_text"] == "Api Test Experience"
    exp_id = data["id"]
    
    # 3. GET Experience returns same immutable data.
    response_get = client.get(f"/experiences/{exp_id}")
    assert response_get.status_code == 200
    assert response_get.json()["raw_text"] == "Api Test Experience"
    
    # 4. Invalid Experience rejected.
    response_invalid = client.post("/experiences", json={"raw_text": "   "}) # Empty string should be rejected by DB or engine
    assert response_invalid.status_code == 422
    
    # 5. No update/delete endpoint exists.
    response_put = client.put(f"/experiences/{exp_id}", json={"raw_text": "modify"})
    assert response_put.status_code == 405 # Method Not Allowed
    
    response_delete = client.delete(f"/experiences/{exp_id}")
    assert response_delete.status_code == 405
