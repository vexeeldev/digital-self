import json
import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel
import urllib.error

from llm_provider import OllamaProvider

class DummyResponseModel(BaseModel):
    name: str
    age: int

@pytest.fixture
def provider():
    # Force provider to be enabled for tests
    with patch("os.getenv", side_effect=lambda k, d: "ollama" if k == "DIGITAL_SELF_LLM_PROVIDER" else d):
        yield OllamaProvider()

@patch("urllib.request.urlopen")
def test_ollama_client_sends_correct_request(mock_urlopen, provider):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "message": {"content": '{"name": "Alice", "age": 30}'}
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = provider.generate_structured("System", "User", DummyResponseModel)
    
    assert result is not None
    assert result.name == "Alice"
    assert result.age == 30
    
    # Verify request payload
    req = mock_urlopen.call_args[0][0]
    payload = json.loads(req.data.decode("utf-8"))
    
    assert payload["model"] == "llama3:latest"
    assert payload["messages"][0]["content"] == "System"
    assert payload["messages"][1]["content"] == "User"
    assert "format" in payload
    assert payload["format"]["title"] == "DummyResponseModel"

@patch("urllib.request.urlopen")
def test_invalid_json_rejected(mock_urlopen, provider):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "message": {"content": '{invalid json}'}
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = provider.generate_structured("System", "User", DummyResponseModel)
    
    assert result is None

@patch("urllib.request.urlopen")
def test_schema_invalid_output_rejected(mock_urlopen, provider):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "message": {"content": '{"name": "Alice", "age": "thirty"}'} # age should be int
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = provider.generate_structured("System", "User", DummyResponseModel)
    
    assert result is None

@patch("urllib.request.urlopen")
def test_ollama_timeout_returns_none(mock_urlopen, provider):
    mock_urlopen.side_effect = urllib.error.URLError("Timeout")
    
    result = provider.generate_structured("System", "User", DummyResponseModel)
    
    assert result is None

def test_ollama_disabled():
    with patch("os.getenv", side_effect=lambda k, d: "none" if k == "DIGITAL_SELF_LLM_PROVIDER" else d):
        provider = OllamaProvider()
        result = provider.generate_structured("System", "User", DummyResponseModel)
        assert result is None
