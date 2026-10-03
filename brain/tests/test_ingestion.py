import pytest
import psycopg2
from unittest.mock import MagicMock

from models import ExperienceCreate, NodeCreate, NodeType, AssociationCreate, AssociationType
from ingestion import ingest_experience
from extraction import NodeExtractionResult, ExtractedNode, AssociationExtractionResult, ExtractedAssociation
from assembly import AssemblyExtractionResult

@pytest.fixture
def db_conn():
    conn = psycopg2.connect("dbname=digital_self user=malakul-tech")
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()

def test_end_to_end_ingestion(db_conn):
    exp_create = ExperienceCreate(raw_text="Temanku tersandung di kantor dan kesal")
    exp, nodes, assocs, assembly = ingest_experience(db_conn, exp_create, llm_client=None)
    
    assert exp is not None
    assert len(nodes) == 4
    assert len(assocs) == 0
    assert assembly is not None
    assert len(assembly.members) == 4
    assert assembly.experience_id == exp.id
    
    with db_conn.cursor() as cur:
        cur.execute("SELECT node_id FROM experience_nodes WHERE experience_id = %s", (str(exp.id),))
        db_node_ids = {row[0] for row in cur.fetchall()}
        
        for m in assembly.members:
            assert str(m.node_id) in db_node_ids

# Mock for Agent
class MockAgentA:
    def __init__(self, config):
        self.instructions = config.system_instructions
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def chat(self, prompt):
        class MockResponse:
            def __init__(self, instructions):
                self.instructions = instructions
            async def structured_output(self):
                if "comprehensive semantic parser" in self.instructions:
                    return NodeExtractionResult(nodes=[
                        ExtractedNode(type=NodeType.PERSON, name="aku", confidence=1.0, evidence="aku"),
                        ExtractedNode(type=NodeType.PLACE, name="kampus", confidence=1.0, evidence="kampus"),
                        ExtractedNode(type=NodeType.OBJECT, name="laptop", confidence=1.0, evidence="laptop"),
                        ExtractedNode(type=NodeType.ACTION, name="datang", confidence=1.0, evidence="datang"),
                        ExtractedNode(type=NodeType.ACTION, name="duduk", confidence=1.0, evidence="duduk"),
                        ExtractedNode(type=NodeType.ACTION, name="membuka laptop", confidence=1.0, evidence="membuka"),
                        ExtractedNode(type=NodeType.CONCEPT, name="sepi", confidence=1.0, evidence="sepi")
                    ])
                elif "association extractor" in self.instructions:
                    return AssociationExtractionResult(associations=[])
                elif "Assembly Extractor" in self.instructions:
                    return AssemblyExtractionResult(context_summary="Test summary", confidence=1.0, members=[])
        return MockResponse(self.instructions)

def test_live_ollama_regression_test_a(db_conn, monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
    monkeypatch.setattr("antigravity_provider.Agent", MockAgentA)
    
    from llm_provider import get_llm_client
    provider = get_llm_client()
        
    raw_text = "Tadi pagi aku datang ke kampus lebih awal. Suasananya masih sepi dan aku duduk sebentar di depan kelas sambil membuka laptop."
    exp_create = ExperienceCreate(raw_text=raw_text)
    exp, nodes, assocs, assembly = ingest_experience(db_conn, exp_create, llm_client=provider)
    
    node_names = [n.name.lower() for n in nodes]
    
    def assert_in(term):
        assert any(term in n for n in node_names), f"Missing {term} in {node_names}"

    assert_in("aku")
    assert_in("kampus")
    assert_in("laptop")
    assert_in("datang")
    assert_in("duduk")
    assert_in("membuka laptop")
    assert_in("sepi")
    
    for term in ["visited", "calm", "solitude", "timestamp"]:
        assert not any(term in n for n in node_names), f"Hallucinated unsupported concept: {term} in {node_names}"

class MockAgentB:
    def __init__(self, config):
        self.instructions = config.system_instructions
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def chat(self, prompt):
        class MockResponse:
            def __init__(self, instructions):
                self.instructions = instructions
            async def structured_output(self):
                if "comprehensive semantic parser" in self.instructions:
                    return NodeExtractionResult(nodes=[
                        ExtractedNode(type=NodeType.PERSON, name="teman", confidence=1.0, evidence="teman"),
                        ExtractedNode(type=NodeType.OBJECT, name="sepatu", confidence=1.0, evidence="sepatu"),
                        ExtractedNode(type=NodeType.PLACE, name="kantor", confidence=1.0, evidence="kantor"),
                        ExtractedNode(type=NodeType.EVENT, name="tersandung", confidence=1.0, evidence="tersandung"),
                        ExtractedNode(type=NodeType.ACTION, name="mengambil", confidence=1.0, evidence="mengambil"),
                        ExtractedNode(type=NodeType.EMOTION, name="kesal", confidence=1.0, evidence="kesal")
                    ])
                elif "association extractor" in self.instructions:
                    return AssociationExtractionResult(associations=[])
                elif "Assembly Extractor" in self.instructions:
                    return AssemblyExtractionResult(context_summary="Test summary", confidence=1.0, members=[])
        return MockResponse(self.instructions)

def test_live_ollama_regression_test_b(db_conn, monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
    monkeypatch.setattr("antigravity_provider.Agent", MockAgentB)
    
    from llm_provider import get_llm_client
    provider = get_llm_client()
        
    raw_text = "Tadi di kantor temanku sepatunya agak bau. Aku biasa saja. Terus waktu mau mengambil sesuatu aku tersandung dan lumayan kesal."
    exp_create = ExperienceCreate(raw_text=raw_text)
    exp, nodes, assocs, assembly = ingest_experience(db_conn, exp_create, llm_client=provider)
    
    node_names = [n.name.lower() for n in nodes]
    
    def assert_in(term):
        assert any(term in n for n in node_names), f"Missing {term} in {node_names}"

    assert_in("teman")
    assert_in("kantor")
    assert_in("tersandung")
    assert_in("kesal")
    
    for term in ["visit", "strong smell", "uncomfortable"]:
        assert not any(term in n for n in node_names), f"Hallucinated unsupported concept: {term} in {node_names}"

class MockAgentC:
    def __init__(self, config):
        self.instructions = config.system_instructions
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def chat(self, prompt):
        class MockResponse:
            def __init__(self, instructions):
                self.instructions = instructions
            async def structured_output(self):
                if "comprehensive semantic parser" in self.instructions:
                    return NodeExtractionResult(nodes=[
                        ExtractedNode(type=NodeType.CONCEPT, name="program", confidence=1.0, evidence="program"),
                        ExtractedNode(type=NodeType.EVENT, name="error", confidence=1.0, evidence="error"),
                        ExtractedNode(type=NodeType.ACTION, name="mengubah", confidence=1.0, evidence="mengubah"),
                        ExtractedNode(type=NodeType.EMOTION, name="kesal", confidence=1.0, evidence="kesal")
                    ])
                elif "association extractor" in self.instructions:
                    return AssociationExtractionResult(associations=[])
                elif "Assembly Extractor" in self.instructions:
                    return AssemblyExtractionResult(context_summary="Test summary", confidence=1.0, members=[])
        return MockResponse(self.instructions)
        
def test_live_ollama_regression_test_c(db_conn, monkeypatch):
    monkeypatch.setenv("DIGITAL_SELF_LLM_PROVIDER", "antigravity")
    monkeypatch.setattr("antigravity_provider.Agent", MockAgentC)
    
    from llm_provider import get_llm_client
    provider = get_llm_client()
        
    raw_text = "Programku tiba-tiba error setelah aku mengubah satu bagian kode, dan aku lumayan kesal."
    exp_create = ExperienceCreate(raw_text=raw_text)
    exp, nodes, assocs, assembly = ingest_experience(db_conn, exp_create, llm_client=provider)
    
    node_names = [n.name.lower() for n in nodes]
    
    def assert_in(term):
        assert any(term in n for n in node_names), f"Missing {term} in {node_names}"

    assert_in("program")
    assert_in("error")
    assert_in("mengubah")
    assert_in("kesal")
    
    for term in ["hate programming", "frustrated developer"]:
        assert not any(term in n for n in node_names), f"Hallucinated unsupported concept: {term} in {node_names}"
