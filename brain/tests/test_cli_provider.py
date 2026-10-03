import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock
from pydantic import BaseModel
import sys
import os

# Add brain to sys path so we can import properly
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from antigravity_cli_provider import AntigravityCLIProvider

class MockModel(BaseModel):
    name: str
    age: int

@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity_cli")
    monkeypatch.setenv("DIGITAL_SELF_ANTIGRAVITY_COMMAND", "fake-agy")
    monkeypatch.setenv("DIGITAL_SELF_ANTIGRAVITY_MODEL", "fake-model")
    return AntigravityCLIProvider()

def test_successful_cli_response(provider, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps({
        "status": "SUCCESS",
        "structured_output": {"name": "Test", "age": 25}
    })
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    result = provider.generate_structured("sys", "usr", MockModel)
    
    assert result is not None
    assert result.name == "Test"
    assert result.age == 25
    
    # Verify correct arguments
    args = mock_run.call_args[0][0]
    assert args[0] == "fake-agy"
    assert "--model" in args
    model_idx = args.index("--model")
    assert args[model_idx + 1] == "fake-model"
    assert "-p" in args
    prompt_idx = args.index("-p")
    assert "sys\n\nExperience:\nusr" in args[prompt_idx + 1]

def test_non_zero_exit_code(provider, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "CLI failed"
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    result = provider.generate_structured("sys", "usr", MockModel)
    assert result is None

def test_timeout(provider, monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="fake-agy", timeout=120)
    monkeypatch.setattr(subprocess, "run", raise_timeout)
    
    result = provider.generate_structured("sys", "usr", MockModel)
    assert result is None

def test_empty_output(provider, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "   "
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    result = provider.generate_structured("sys", "usr", MockModel)
    assert result is None

def test_invalid_json(provider, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "{ invalid json"
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    result = provider.generate_structured("sys", "usr", MockModel)
    assert result is None

def test_invalid_pydantic_structure(provider, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps({
        "status": "SUCCESS",
        "structured_output": {"name": "Test", "age": "not-an-int"}
    })
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    result = provider.generate_structured("sys", "usr", MockModel)
    assert result is None

def test_fallback_to_response_string(provider, monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps({
        "status": "SUCCESS",
        "response": json.dumps({"name": "StringTest", "age": 30})
    })
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    result = provider.generate_structured("sys", "usr", MockModel)
    assert result is not None
    assert result.name == "StringTest"
    assert result.age == 30
