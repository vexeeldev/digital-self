import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'brain'))
import json
import subprocess
from extraction import NodeExtractionResult

schema = json.dumps(NodeExtractionResult.model_json_schema())
prompt = "Reply strictly with the JSON data matching the schema. DO NOT use any tools. Experience: Tadi pagi aku minum kopi."

args = [
    "agy", "-p", prompt,
    "--model", "gemini-3.8-flash-medium",
    "--output-format", "json",
    "--json-schema", schema
]

result = subprocess.run(args, capture_output=True, text=True)
print(f"RC: {result.returncode}")
print(f"STDOUT:\n{result.stdout}")
print(f"STDERR:\n{result.stderr}")
