import os
import json
import logging
import subprocess
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class AntigravityCLIProvider:
    def __init__(self):
        self.provider = os.getenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity_cli")
        self.command = os.getenv("DIGITAL_SELF_ANTIGRAVITY_COMMAND", "agy")
        self.model = os.getenv("DIGITAL_SELF_ANTIGRAVITY_MODEL", "gemini-3.8-flash-medium")
        self.timeout = int(os.getenv("DIGITAL_SELF_ANTIGRAVITY_TIMEOUT", "120"))
        
    def is_enabled(self) -> bool:
        return self.provider.lower() == "antigravity_cli"
        
    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> BaseModel | None:
        if not self.is_enabled():
            return None
            
        schema_dict = response_model.model_json_schema()
        schema_str = json.dumps(schema_dict)
        
        full_prompt = f"{system_prompt}\n\nExperience:\n{user_prompt}\n\nCRITICAL INSTRUCTION: Reply STRICTLY with the final JSON data matching the requested schema. DO NOT use any tools, actions, or commands. Act as a pure JSON API endpoint."
        
        args = [
            self.command,
            "-p", full_prompt,
            "--model", self.model,
            "--output-format", "json",
            "--json-schema", schema_str
        ]
        
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Antigravity CLI error (exit code {result.returncode}): {result.stderr}")
                return None
                
            stdout = result.stdout.strip()
            if not stdout:
                logger.error("Antigravity CLI returned empty output.")
                return None
                
            try:
                wrapper = json.loads(stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Antigravity CLI wrapper JSON: {e}\nRaw output: {stdout}")
                return None
                
            if wrapper.get("status") != "SUCCESS":
                logger.error(f"Antigravity CLI returned non-success status: {wrapper.get('status')}")
                return None
                
            structured_data = wrapper.get("structured_output")
            
            if structured_data is None:
                # Fallback to parsing the string 'response' if structured_output is missing
                response_str = wrapper.get("response", "")
                
                # Find all potential JSON objects in the response string
                decoder = json.JSONDecoder()
                pos = 0
                objs = []
                while pos < len(response_str):
                    while pos < len(response_str) and response_str[pos].isspace():
                        pos += 1
                    if pos == len(response_str):
                        break
                    if response_str[pos] == '{':
                        try:
                            obj, idx = decoder.raw_decode(response_str[pos:])
                            objs.append(obj)
                            pos += idx
                        except json.JSONDecodeError:
                            pos += 1
                    else:
                        pos += 1
                
                # Try to validate each object, return the first one that succeeds
                if objs:
                    last_error = None
                    for obj in objs:
                        try:
                            return response_model.model_validate(obj)
                        except ValidationError as e:
                            last_error = e
                            continue
                    logger.error(f"Pydantic validation failed for inner response. Last error: {last_error}\nJSON was: {objs}")
                else:
                    logger.error(f"Failed to find valid JSON in inner response: {response_str}")
                return None
            
            try:
                return response_model.model_validate(structured_data)
            except ValidationError as e:
                logger.error(f"Pydantic validation failed on LLM output: {e}\nData: {structured_data}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Antigravity CLI timed out after {self.timeout} seconds.")
            return None
        except FileNotFoundError:
            logger.error(f"Antigravity CLI command '{self.command}' not found.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error running Antigravity CLI: {e}")
            return None
