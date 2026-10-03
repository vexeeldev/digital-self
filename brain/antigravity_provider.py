import os
import asyncio
import logging
from pydantic import BaseModel
from google.antigravity import Agent, LocalAgentConfig

logger = logging.getLogger(__name__)

class AntigravityProvider:
    def __init__(self):
        self.provider = os.getenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
        
    def is_enabled(self) -> bool:
        return self.provider.lower() == "antigravity"
        
    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> BaseModel | None:
        if not self.is_enabled():
            return None
            
        try:
            return asyncio.run(self._generate_structured_async(system_prompt, user_prompt, response_model))
        except Exception as e:
            logger.error(f"AntigravityProvider error: {e}")
            return None

    async def _generate_structured_async(self, system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> BaseModel | None:
        config = LocalAgentConfig(
            response_schema=response_model,
            system_instructions=system_prompt
        )
        # Using a context manager ensures the agent session is cleanly closed
        async with Agent(config) as agent:
            response = await agent.chat(user_prompt)
            data = await response.structured_output()
            return data
