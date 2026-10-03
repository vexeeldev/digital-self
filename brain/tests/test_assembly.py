import pytest
import uuid
from pydantic import ValidationError

from models import ExperienceCreate, NodeCreate, NodeType, ExtractedAssemblyMember, AssemblyExtractionResult
from experience import save_experience
from extraction import save_extracted_nodes
from assembly import extract_assembly, save_assembly

@pytest.fixture
def db_conn():
    import psycopg2
    conn = psycopg2.connect("dbname=digital_self user=malakul-tech")
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()

def test_extract_assembly_empty(db_conn):
    exp = save_experience(db_conn, ExperienceCreate(raw_text="Valid text but no nodes extracted"))
    res = extract_assembly(exp, [])
    assert res.context_summary == "Empty episode"
    assert len(res.members) == 0

def test_extract_assembly_mock(db_conn):
    exp = save_experience(db_conn, ExperienceCreate(raw_text="Temanku tersandung di kantor dan kesal"))
    nodes_in = [
        NodeCreate(type=NodeType.PERSON, name="teman", confidence=0.9),
        NodeCreate(type=NodeType.PLACE, name="kantor", confidence=0.9),
        NodeCreate(type=NodeType.EVENT, name="tersandung", confidence=0.9),
        NodeCreate(type=NodeType.EMOTION, name="kesal", confidence=0.9),
    ]
    saved_nodes = save_extracted_nodes(db_conn, exp.id, nodes_in)
    
    res = extract_assembly(exp, saved_nodes)
    assert res.confidence == 0.9
    assert len(res.members) == 4
    
def test_save_assembly_and_provenance(db_conn):
    exp = save_experience(db_conn, ExperienceCreate(raw_text="Temanku tersandung di kantor dan kesal"))
    nodes_in = [
        NodeCreate(type=NodeType.PERSON, name="teman", confidence=0.9),
        NodeCreate(type=NodeType.PLACE, name="kantor", confidence=0.9),
        NodeCreate(type=NodeType.EVENT, name="tersandung", confidence=0.9),
    ]
    saved_nodes = save_extracted_nodes(db_conn, exp.id, nodes_in)
    
    extraction = AssemblyExtractionResult(
        context_summary="Test context",
        confidence=0.8,
        members=[
            ExtractedAssemblyMember(node_name="teman", role="actor", weight=0.9),
            ExtractedAssemblyMember(node_name="kantor", role="location", weight=0.5),
        ]
    )
    
    assembly = save_assembly(db_conn, exp.id, extraction, saved_nodes)
    
    assert assembly.experience_id == exp.id
    assert assembly.context_summary == "Test context"
    assert assembly.confidence == 0.8
    assert len(assembly.members) == 2
    
    with db_conn.cursor() as cur:
        cur.execute("SELECT node_id FROM assembly_members WHERE assembly_id = %s", (str(assembly.id),))
        node_ids = {row[0] for row in cur.fetchall()}
        assert str(saved_nodes[0].id) in node_ids
        assert str(saved_nodes[1].id) in node_ids
        
def test_duplicate_experience_rejected(db_conn):
    exp = save_experience(db_conn, ExperienceCreate(raw_text="Generic text"))
    nodes_in = [NodeCreate(type=NodeType.CONCEPT, name="concept1", confidence=0.9)]
    saved_nodes = save_extracted_nodes(db_conn, exp.id, nodes_in)
    
    extraction1 = AssemblyExtractionResult(
        context_summary="Context 1",
        confidence=0.5,
        members=[ExtractedAssemblyMember(node_name="concept1", role="role1", weight=0.5)]
    )
    
    assembly1 = save_assembly(db_conn, exp.id, extraction1, saved_nodes)
    
    extraction2 = AssemblyExtractionResult(
        context_summary="Context 2",
        confidence=0.6,
        members=[ExtractedAssemblyMember(node_name="concept1", role="role2", weight=0.8)]
    )
    
    with pytest.raises(ValueError, match="already exists"):
        save_assembly(db_conn, exp.id, extraction2, saved_nodes)
    
    with db_conn.cursor() as cur:
        # Check only 1 assembly exists for this experience and it's the first one
        cur.execute("SELECT id, context_summary FROM assemblies WHERE experience_id = %s", (str(exp.id),))
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "Context 1"
        
        # Check members remain unchanged
        cur.execute("SELECT role, weight FROM assembly_members WHERE assembly_id = %s", (str(rows[0][0]),))
        mem_rows = cur.fetchall()
        assert len(mem_rows) == 1
        assert mem_rows[0][0] == "role1"
        
def test_duplicate_member_rejected(db_conn):
    exp = save_experience(db_conn, ExperienceCreate(raw_text="Duplicate test"))
    nodes_in = [NodeCreate(type=NodeType.CONCEPT, name="concept1", confidence=0.9)]
    saved_nodes = save_extracted_nodes(db_conn, exp.id, nodes_in)
    
    extraction = AssemblyExtractionResult(
        context_summary="Context 1",
        confidence=0.5,
        members=[
            ExtractedAssemblyMember(node_name="concept1", role="role1", weight=0.5),
            ExtractedAssemblyMember(node_name="concept1", role="role2", weight=0.8) # Duplicate node_name
        ]
    )
    
    with pytest.raises(ValueError, match="Duplicate node 'concept1' in Assembly"):
        save_assembly(db_conn, exp.id, extraction, saved_nodes)
    
def test_invalid_node_rollback(db_conn):
    exp = save_experience(db_conn, ExperienceCreate(raw_text="Invalid node test"))
    nodes_in = [NodeCreate(type=NodeType.CONCEPT, name="concept1", confidence=0.9)]
    saved_nodes = save_extracted_nodes(db_conn, exp.id, nodes_in)
    
    extraction = AssemblyExtractionResult(
        context_summary="Context 1",
        confidence=0.5,
        members=[
            ExtractedAssemblyMember(node_name="concept1", role="role1", weight=0.5),
            ExtractedAssemblyMember(node_name="hallucinated", role="role2", weight=0.8)
        ]
    )
    
    with pytest.raises(ValueError, match="Hallucinated node 'hallucinated' not found in available_nodes"):
        save_assembly(db_conn, exp.id, extraction, saved_nodes)
    
    with db_conn.cursor() as cur:
        # Verify transaction was aborted or at least nothing was inserted
        cur.execute("SELECT count(*) FROM assemblies WHERE experience_id = %s", (str(exp.id),))
        assert cur.fetchone()[0] == 0

def test_member_must_belong_to_experience(db_conn):
    # Setup two different experiences
    exp1 = save_experience(db_conn, ExperienceCreate(raw_text="Text one"))
    exp2 = save_experience(db_conn, ExperienceCreate(raw_text="Text two"))
    
    # Extract nodes for exp1
    saved_nodes1 = save_extracted_nodes(db_conn, exp1.id, [NodeCreate(type=NodeType.CONCEPT, name="concept_one", confidence=0.9)])
    
    # Extract nodes for exp2
    saved_nodes2 = save_extracted_nodes(db_conn, exp2.id, [NodeCreate(type=NodeType.CONCEPT, name="concept_two", confidence=0.9)])
    
    # Attempt to create an assembly for exp1 using a node from exp2
    extraction = AssemblyExtractionResult(
        context_summary="Cross-pollination test",
        confidence=0.5,
        members=[
            ExtractedAssemblyMember(node_name="concept_two", role="infiltrator", weight=0.5)
        ]
    )
    
    # saved_nodes passed here must include concept_two for it to pass the available_nodes check
    with pytest.raises(ValueError, match="Provenance mismatch: Node 'concept_two'"):
        save_assembly(db_conn, exp1.id, extraction, saved_nodes2)

def test_confidence_and_weight_bounds():
    with pytest.raises(ValidationError):
        ExtractedAssemblyMember(node_name="test", role="role", weight=1.5)
        
    with pytest.raises(ValidationError):
        ExtractedAssemblyMember(node_name="test", role="role", weight=-0.1)

    with pytest.raises(ValidationError):
        AssemblyExtractionResult(context_summary="ctx", confidence=1.5, members=[])
        
    with pytest.raises(ValidationError):
        AssemblyExtractionResult(context_summary="ctx", confidence=-0.1, members=[])
