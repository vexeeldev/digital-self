import os
import json
import logging
import urllib.request
import urllib.error
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class OllamaProvider:
    def __init__(self):
        self.provider = os.getenv("DIGITAL_SELF_LLM_PROVIDER", "ollama")
        self.base_url = os.getenv("DIGITAL_SELF_OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("DIGITAL_SELF_OLLAMA_MODEL", "llama3:latest")
        
    def is_enabled(self) -> bool:
        return self.provider.lower() == "ollama"
        
    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> BaseModel | None:
        if not self.is_enabled():
            return None
            
        url = f"{self.base_url}/api/chat"
        
        # We can pass the pydantic schema to Ollama (supported in 0.3+ formats)
        schema = response_model.model_json_schema()
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "format": schema,
            "stream": False,
            "options": {
                "temperature": 0.1 # Low temperature for extraction
            }
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        try:
            logger.info(f"Ollama extraction request: model={self.model}")
            with urllib.request.urlopen(req, timeout=120.0) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                content = result.get("message", {}).get("content")
                if not content:
                    logger.warning("Ollama returned empty content.")
                    return None
                    
                parsed_json = json.loads(content)
                validated_model = response_model.model_validate(parsed_json)
                return validated_model
                
        except urllib.error.URLError as e:
            logger.error(f"Ollama connection error: {e}")
            return None
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Ollama schema validation error: {e}")
            return None
        except Exception as e:
            logger.error(f"Ollama unknown error: {e}")
            return None

def get_llm_client():
    provider_name = os.getenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity_cli").lower()
    if provider_name == "antigravity":
        from antigravity_provider import AntigravityProvider
        return AntigravityProvider()
    elif provider_name == "antigravity_cli":
        from antigravity_cli_provider import AntigravityCLIProvider
        return AntigravityCLIProvider()
    return OllamaProvider()
