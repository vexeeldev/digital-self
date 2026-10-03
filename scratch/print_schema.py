import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'brain')))
from extraction import NodeExtractionResult

print(json.dumps(NodeExtractionResult.model_json_schema(), indent=2))
