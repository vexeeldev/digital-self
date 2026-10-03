import pytest
from models import ExperienceCreate, NodeType, AssociationType
from ingestion import ingest_experience
from extraction import NodeExtractionResult, ExtractedNode, AssociationExtractionResult, ExtractedAssociation
from assembly import AssemblyExtractionResult
import psycopg2

@pytest.fixture
def db_conn():
    conn = psycopg2.connect("dbname=digital_self user=malakul-tech")
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()

class MockCoverageAgent:
    def __init__(self, config):
        self.instructions = config.system_instructions
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def chat(self, prompt):
        class MockResponse:
            def __init__(self, instructions, prompt_text):
                self.instructions = instructions
                self.prompt_text = prompt_text
            async def structured_output(self):
                if "comprehensive semantic parser" in self.instructions:
                    if "kemarin" in self.prompt_text.lower():
                        return NodeExtractionResult(nodes=[
                            ExtractedNode(type=NodeType.ACTION, name="berlari kencang", confidence=1.0, evidence="berlari kencang"),
                            ExtractedNode(type=NodeType.CONCEPT, name="kemarin sore", confidence=1.0, evidence="kemarin sore"),
                            ExtractedNode(type=NodeType.EMOTION, name="sangat lelah", confidence=1.0, evidence="sangat lelah"),
                            ExtractedNode(type=NodeType.CONCEPT, name="hujan deras", confidence=1.0, evidence="hujan deras")
                        ])
                    else:
                        return NodeExtractionResult(nodes=[
                            ExtractedNode(type=NodeType.PERSON, name="dia", confidence=1.0, evidence="dia"),
                            ExtractedNode(type=NodeType.ACTION, name="berbicara pelan", confidence=1.0, evidence="berbicara pelan"),
                            ExtractedNode(type=NodeType.EMOTION, name="agak ragu", confidence=1.0, evidence="agak ragu")
                        ])
                elif "association extractor" in self.instructions:
                    return AssociationExtractionResult(associations=[])
                elif "Assembly Extractor" in self.instructions:
                    return AssemblyExtractionResult(context_summary="Summary", confidence=1.0, members=[])
        return MockResponse(self.instructions, prompt)

def test_extraction_coverage_temporal_and_qualifiers(db_conn, monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
    monkeypatch.setattr("antigravity_provider.Agent", MockCoverageAgent)
    from llm_provider import get_llm_client
    
    raw_text = "Kemarin sore aku berlari kencang saat hujan deras dan merasa sangat lelah."
    exp_create = ExperienceCreate(raw_text=raw_text)
    exp, nodes, assocs, assembly = ingest_experience(db_conn, exp_create, get_llm_client())
    
    node_names = [n.name for n in nodes]
    node_types = {n.name: n.type for n in nodes}
    
    # Verify temporal information is extracted
    assert "kemarin sore" in node_names
    # Depending on schema, it might map to CONCEPT if TEMPORAL isn't available, but we assert it exists
    
    # Verify qualifiers are preserved
    assert "berlari kencang" in node_names
    assert "sangat lelah" in node_names
    
    # Verify context
    assert "hujan deras" in node_names

def test_extraction_coverage_actions_and_thoughts(db_conn, monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
    monkeypatch.setattr("antigravity_provider.Agent", MockCoverageAgent)
    from llm_provider import get_llm_client
    
    raw_text = "Dia berbicara pelan dan aku merasa agak ragu."
    exp_create = ExperienceCreate(raw_text=raw_text)
    exp, nodes, assocs, assembly = ingest_experience(db_conn, exp_create, get_llm_client())
    
    node_names = [n.name for n in nodes]
    
    # Verify action extraction
    assert "berbicara pelan" in node_names
    
    # Verify subjective/thought extraction with qualifiers
    assert "agak ragu" in node_names
