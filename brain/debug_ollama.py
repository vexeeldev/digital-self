import os
from pydantic import BaseModel
from models import NodeType
from llm_provider import OllamaProvider
from pydantic import Field

class ExtractedNode(BaseModel):
    type: NodeType = Field(..., description="Semantic type of this node.")
    name: str = Field(..., min_length=1, description="The EXACT word or short phrase from the text representing this node. Must be in Indonesian as written in the text.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this extraction.")
    evidence: str = Field(..., description="The exact sentence/phrase from the text that proves this node exists.")

class NodeExtractionResult(BaseModel):
    nodes: list[ExtractedNode]

provider = OllamaProvider()

system_prompt = (
    "You are a strict data extractor for Digital Self.\n"
    "CRITICAL RULE: DO NOT TRANSLATE. DO NOT SUMMARIZE. DO NOT INFER.\n"
    "Your ONLY job is to copy exact words/phrases from the text into the JSON.\n"
    "If the text says 'tersandung', the node name MUST be 'tersandung'.\n"
    "If the text says 'sepatu', the node name MUST be 'sepatu'.\n"
    "If the text says 'teman', the node name MUST be 'teman'.\n"
    "If the text says 'kesal', the node name MUST be 'kesal'.\n"
    "Do NOT output English unless the original text is in English.\n"
    "Do NOT output 'visit friend's office'. Output the exact place: 'kantor temanku'.\n"
    "Extract 1. Entities (person, object, place) 2. Events/Actions 3. Emotions.\n"
    "Every extracted item MUST be a verbatim substring of the text."
)

text = "Tadi di kantor temanku sepatunya agak bau. Aku biasa saja. Terus waktu mau mengambil sesuatu aku tersandung dan lumayan kesal."

print("Calling Ollama...")
result = provider.generate_structured(system_prompt, text, NodeExtractionResult)
print(result)
