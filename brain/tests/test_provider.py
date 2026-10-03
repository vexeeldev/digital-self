import pytest
from pydantic import BaseModel
from antigravity_provider import AntigravityProvider
from llm_provider import get_llm_client, OllamaProvider
from google.antigravity import LocalAgentConfig

class DummyResponseModel(BaseModel):
    field: str

class MockAgentResponse:
    async def structured_output(self):
        return DummyResponseModel(field="success")

class MockAgent:
    def __init__(self, config):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def chat(self, prompt):
        return MockAgentResponse()

def test_get_llm_client_antigravity(monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
    provider = get_llm_client()
    assert isinstance(provider, AntigravityProvider)
    assert provider.is_enabled()

def test_get_llm_client_ollama(monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "ollama")
    provider = get_llm_client()
    assert isinstance(provider, OllamaProvider)
    assert provider.is_enabled()

def test_antigravity_provider_success(monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
    provider = AntigravityProvider()
    
    # Mock the Agent to return structured output
    monkeypatch.setattr("antigravity_provider.Agent", MockAgent)
    
    result = provider.generate_structured("sys", "user", DummyResponseModel)
    assert result is not None
    assert result.field == "success"

def test_antigravity_provider_failure_fallback(monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
    provider = AntigravityProvider()
    
    class FailingMockAgent:
        def __init__(self, config):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def chat(self, prompt):
            raise ValueError("API error")
            
    monkeypatch.setattr("antigravity_provider.Agent", FailingMockAgent)
    
    result = provider.generate_structured("sys", "user", DummyResponseModel)
    assert result is None  # Should return None on failure, triggering fallback in extraction
