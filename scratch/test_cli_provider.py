import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'brain')))
from antigravity_cli_provider import AntigravityCLIProvider
from extraction import NodeExtractionResult

provider = AntigravityCLIProvider()
system_prompt = (
    "You are a comprehensive semantic parser for Digital Self.\n"
    "Your goal is to achieve FULL SEMANTIC COVERAGE of the raw experience by extracting all explicitly stated information.\n"
    "1. COVERAGE: Extract ALL explicit info (PERSON, PLACE, OBJECT, EVENT, ACTION, EMOTION, THOUGHT, CONTEXT, TEMPORAL).\n"
    "   Do not stop after a few nodes. Do not over-summarize.\n"
    "2. EVENTS/ACTIONS: Extract verbs and events exactly as stated.\n"
    "3. QUALIFIERS: Preserve adjectives/qualifiers exactly (e.g., 'agak', 'sangat', 'lebih awal', 'sebentar').\n"
    "4. SUBJECTIVE: Extract explicit reactions, thoughts, or states. Do not infer unsupported emotions.\n"
    "5. TEMPORAL: Preserve explicit temporal info exactly. Do not invent exact timestamps.\n"
    "6. CONTEXT: Preserve explicit environments EXACTLY as stated.\n"
    "7. EVIDENCE: Every extracted item MUST contain exact evidence copied/normalized from the text. No evidence = no extraction.\n"
    "8. NO HALLUCINATION: Never invent motivations, emotions, relationships, locations, or events.\n"
    "9. NO UNKNOWN: Do not generate an 'unknown' node. Prefer omission over fabrication.\n"
    "10. MEANING IS CONSERVATIVE, COVERAGE IS COMPREHENSIVE: Do not invent meaning, but do not omit explicitly stated facts.\n"
    "Use only the provided Node types."
)

text = "hari ini aku nonton sakomoto days film seru anjai"

print(f"Testing extraction on: {text}")
result = provider.generate_structured(system_prompt, text, NodeExtractionResult)
print(f"Result: {result}")
