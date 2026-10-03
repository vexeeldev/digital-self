import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_api_reasoning():
    # Insert some seed data to make sure reasoning works properly
    # We will just do a simple reasoning request
    # 6. Valid query returns structured reasoning.
    response = client.post("/reasoning", json={"query": "Test query without matches", "context": {}})
    assert response.status_code == 200
    data = response.json()
    
    assert "inferences" in data
    assert "evidence" in data
    assert "conflicts" in data
    
    # 7. Invalid query rejected.
    response_invalid = client.post("/reasoning", json={"query": "", "context": {}})
    assert response_invalid.status_code == 422
    
    # 8. Provenance returned.
    assert "provenance" in data
    
    # 9. Conflicts returned.
    assert type(data["conflicts"]) == list
