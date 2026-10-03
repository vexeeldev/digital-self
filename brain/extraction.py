"""
Digital Self — extraction.py
Version: V2.1 — Initial Technical Contract

Handles the extraction of nodes (concepts/entities) from raw experiences.
Uses LLM strictly as an interpreter for extraction.
"""

import uuid
from psycopg2.extensions import connection
from pydantic import BaseModel, Field

from models import (
    NodeCreate, Node, NodeType, Experience,
    AssociationCreate, Association, AssociationType
)
from resolution import resolve_node

from pydantic import BaseModel, Field, AliasChoices, model_validator

class ExtractedNode(BaseModel):
    type: str = Field(..., description="Semantic type of this node.")
    name: str = Field(..., validation_alias=AliasChoices("name", "value"), min_length=1, description="The EXACT word or short phrase from the text representing this node. Must be exactly as written in the text.")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in this extraction.")
    evidence: str = Field(..., description="The exact sentence/phrase from the text that proves this node exists.")

    @model_validator(mode='before')
    @classmethod
    def normalize_type(cls, data: dict):
        if 'type' in data and isinstance(data['type'], str):
            t = data['type'].lower()
            if t in ('temporal', 'thought', 'context'):
                data['type'] = 'concept'
            else:
                data['type'] = t
        return data

class NodeExtractionResult(BaseModel):
    """Structured output expected from the LLM."""
    nodes: list[ExtractedNode]

def extract_nodes(exp: Experience, llm_client=None) -> list[NodeCreate]:
    """
    Extracts candidate nodes from an Experience using an LLM.
    
    Rules enforced:
    - Only extracts concepts/entities/events/emotions/actions.
    - No summarization, rewriting, beliefs, or causality.
    - Returns structured output mirroring NodeCreate.
    """
    if not exp.raw_text.strip():
        return []

    # Real LLM implementation
    if llm_client is not None and getattr(llm_client, "is_enabled", lambda: False)():
        # Inject the timestamp context
        time_context = exp.created_at.strftime('%Y-%m-%d %H:%M:%S') if exp.created_at else "Unknown"
        
        system_prompt = (
            "You are a comprehensive semantic parser for Digital Self.\n"
            f"CURRENT DATETIME OF THIS EXPERIENCE: {time_context}\n"
            "Your goal is to achieve FULL SEMANTIC COVERAGE of the raw experience by extracting all explicitly stated information.\n"
            "1. COVERAGE: Extract ALL explicit info. Valid types: person, place, object, event, action, emotion, concept.\n"
            "   Do not stop after a few nodes. Do not over-summarize.\n"
            "2. EVENTS/ACTIONS: Extract verbs and events exactly as stated.\n"
            "3. QUALIFIERS: Preserve adjectives/qualifiers exactly (e.g., 'agak', 'sangat', 'lebih awal', 'sebentar').\n"
            "4. SUBJECTIVE: Extract explicit reactions, thoughts, or states as 'concept' or 'emotion'. Do not infer unsupported emotions.\n"
            "5. TEMPORAL/CONTEXT: When you encounter relative time (e.g. 'hari ini', 'kemarin', 'tadi pagi'), extract it as a 'concept' BUT append the specific date/time from the CURRENT DATETIME to disambiguate it (e.g., 'hari ini (2026-10-02)'). Preserve other explicit context exactly as 'concept'.\n"
            "6. EVIDENCE: Every extracted item MUST contain exact evidence copied/normalized from the text. No evidence = no extraction.\n"
            "7. NO HALLUCINATION: Never invent motivations, emotions, relationships, locations, or events.\n"
            "8. NO UNKNOWN: Do not generate an 'unknown' node. Prefer omission over fabrication.\n"
            "9. MEANING IS CONSERVATIVE, COVERAGE IS COMPREHENSIVE: Do not invent meaning, but do not omit explicitly stated facts.\n"
            "IMPORTANT JSON FORMATTING: You must output a 'name' field for the node (do NOT use 'value'). You must include 'confidence'.\n"
            "Use ONLY the provided valid types (lowercase)."
        )
        try:
            result = llm_client.generate_structured(system_prompt, exp.raw_text, NodeExtractionResult)
            if result is not None:
                # Map back string to NodeType Enum safely
                nodes_out = []
                for n in result.nodes:
                    try:
                        node_type = NodeType(n.type)
                    except ValueError:
                        node_type = NodeType.CONCEPT
                    nodes_out.append(NodeCreate(type=node_type, name=n.name.strip().lower(), confidence=n.confidence))
                return nodes_out
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Node extraction failed: {e}")
            
        # If a real provider is enabled but failed, return empty instead of deterministic fallback
        return []

    # Mock/Fake implementation for testing and fallback
    text = exp.raw_text.lower()
    if "kantor" in text and "kesal" in text:
        return [
            NodeCreate(type=NodeType.PERSON, name="teman", confidence=0.92),
            NodeCreate(type=NodeType.PLACE, name="kantor", confidence=0.97),
            NodeCreate(type=NodeType.EVENT, name="tersandung", confidence=0.91),
            NodeCreate(type=NodeType.EMOTION, name="kesal", confidence=0.95),
        ]
    elif "empty" in text:
        return []
    elif "invalid" in text:
        # Simulate LLM returning invalid type (Pydantic will raise ValidationError if we tried to parse it)
        # Here we just raise a generic error to simulate LLM failure
        raise RuntimeError("LLM parsing error")
        
    return []

def save_extracted_nodes(conn: connection, exp_id: uuid.UUID, nodes_in: list[NodeCreate]) -> list[Node]:
    """
    Saves candidate nodes to the database and establishes provenance back to the Experience.
    Uses Entity Resolution to avoid duplicating concepts.
    Does not modify the Experience.
    """
    saved_nodes = []
    import psycopg2.errors
    with conn.cursor() as cur:
        for node_in in nodes_in:
            res = resolve_node(conn, node_in.name, node_in.type, node_in.confidence)
            
            # Fetch full node info
            cur.execute(
                """
                SELECT id, type, name, confidence, activation, first_seen, last_seen
                FROM nodes WHERE id = %s;
                """,
                (str(res.node_id),)
            )
            row = cur.fetchone()
            node = Node(
                id=row[0], type=row[1], name=row[2], confidence=row[3],
                activation=row[4], first_seen=row[5], last_seen=row[6]
            )
            saved_nodes.append(node)
            
            # Provenance Bridge: Link node to experience
            try:
                cur.execute("SAVEPOINT bridge_sp;")
                cur.execute(
                    """
                    INSERT INTO experience_nodes (experience_id, node_id)
                    VALUES (%s, %s);
                    """,
                    (str(exp_id), str(node.id))
                )
                cur.execute("RELEASE SAVEPOINT bridge_sp;")
            except psycopg2.errors.UniqueViolation:
                cur.execute("ROLLBACK TO SAVEPOINT bridge_sp;")
            
    return saved_nodes


class ExtractedAssociation(BaseModel):
    """An association extracted by the LLM, referencing nodes by their names."""
    source_node_name: str = Field(..., validation_alias=AliasChoices("source_node_name", "source_node", "source", "source_name"), description="Name of the source node")
    target_node_name: str = Field(..., validation_alias=AliasChoices("target_node_name", "target_node", "target", "target_name"), description="Name of the target node")
    type: str = Field(..., description="Relationship type from the taxonomy")
    confidence: float = Field(1.0, description="Confidence level (0.0 to 1.0) that this relationship is supported by the experience")
    evidence: str = Field(..., description="Brief explanation from the text why this association exists")

    @model_validator(mode='before')
    @classmethod
    def normalize_type(cls, data: dict):
        if 'type' in data and isinstance(data['type'], str):
            data['type'] = data['type'].lower()
        return data

class AssociationExtractionResult(BaseModel):
    associations: list[ExtractedAssociation]

def extract_associations(exp: Experience, nodes: list[Node], llm_client=None) -> list[AssociationCreate]:
    """
    Extracts associations between nodes based purely on the experience.
    """
    if not exp.raw_text.strip() or len(nodes) < 2:
        return []

    node_dict = {n.name.lower(): n for n in nodes}
    node_names_str = ", ".join(node_dict.keys())

    extracted = []
    # Real LLM implementation
    if llm_client is not None and getattr(llm_client, "is_enabled", lambda: False)():
        system_prompt = (
            f"You are an association extractor. Extract relationships between the nodes.\n"
            f"Available nodes: [{node_names_str}]\n"
            f"Rules:\n"
            f"- MUST use EXACT node names from the available list. Do not alter spelling, spaces, or words.\n"
            f"- EXTRACT ALL VALID RELATIONSHIPS. Do not leave nodes disconnected if they clearly relate semantically.\n"
            f"- DO NOT invent relationships that have no basis in the text, but DO extract 'is_a', 'has_property', 'involves', 'located_at' generously if implied.\n"
            f"- Use 'co_occurs_with' as a fallback. Use 'causes' ONLY if explicit causality exists.\n"
            f"- Connect as many nodes as logically possible to build a dense, fully connected graph.\n"
            f"- Confidence must be between 0.0 and 1.0."
        )
        try:
            result = llm_client.generate_structured(system_prompt, exp.raw_text, AssociationExtractionResult)
            if result is not None:
                extracted = result.associations
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Association extraction failed: {e}")
            
        if not extracted:
            return []

    if not extracted:
        # Mock/Fake implementation fallback
        text = exp.raw_text.lower()
        if "sepatu" in text and "bau" in text:
            extracted = [
                ExtractedAssociation(source_node_name="teman", target_node_name="sepatu", type=AssociationType.INVOLVES, confidence=0.8, evidence="Temanku sepatunya bau"),
                ExtractedAssociation(source_node_name="sepatu", target_node_name="bau", type=AssociationType.HAS_PROPERTY, confidence=0.9, evidence="Sepatunya agak bau"),
                ExtractedAssociation(source_node_name="teman", target_node_name="kantor", type=AssociationType.LOCATED_AT, confidence=0.95, evidence="Tadi di kantor temanku"),
            ]
        elif "invalid" in text:
            raise RuntimeError("LLM parsing error")

    # Map extracted names back to Node IDs
    associations = []
    def find_node(name: str):
        name = name.lower().strip()
        if name in node_dict:
            return node_dict[name]
        for k, v in node_dict.items():
            if name in k or k in name:
                return v
        return None

    for ext in extracted:
        src = find_node(ext.source_node_name)
        tgt = find_node(ext.target_node_name)
        
        # Parse association type safely
        try:
            assoc_type = AssociationType(ext.type)
        except ValueError:
            assoc_type = AssociationType.CO_OCCURS_WITH

        # Only valid nodes from the context, and no self-loops
        if src and tgt and src.id != tgt.id:
            try:
                assoc = AssociationCreate(
                    source_node_id=src.id,
                    target_node_id=tgt.id,
                    type=assoc_type,
                    confidence=ext.confidence,
                    source_experience_id=exp.id
                )
                associations.append(assoc)
            except ValueError:
                # Catch validation errors (like out of bounds confidence) and ignore
                pass

    return associations

def save_extracted_associations(conn: connection, exp_id: uuid.UUID, associations_in: list[AssociationCreate]) -> list[Association]:
    """
    Saves associations to the database and establishes provenance back to the Experience.
    Handles duplicate directed associations gracefully.
    """
    saved_associations = []
    with conn.cursor() as cur:
        for assoc_in in associations_in:
            # Insert or ignore duplicate
            cur.execute(
                """
                INSERT INTO associations (source_node_id, target_node_id, type, confidence, source_experience_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (source_node_id, target_node_id, type) DO NOTHING
                RETURNING id, source_node_id, target_node_id, type, strength, confidence, positive_evidence, negative_evidence, source_experience_id, created_at, updated_at;
                """,
                (str(assoc_in.source_node_id), str(assoc_in.target_node_id), assoc_in.type.value, assoc_in.confidence, str(exp_id))
            )
            row = cur.fetchone()
            
            if row:
                # Brand new association
                assoc_id = row[0]
                assoc = Association(
                    id=row[0], source_node_id=row[1], target_node_id=row[2], type=row[3],
                    strength=row[4], confidence=row[5], positive_evidence=row[6],
                    negative_evidence=row[7], source_experience_id=row[8],
                    created_at=row[9], updated_at=row[10]
                )
                saved_associations.append(assoc)
            else:
                # Duplicate association exists, fetch its ID
                cur.execute(
                    """
                    SELECT id FROM associations 
                    WHERE source_node_id = %s AND target_node_id = %s AND type = %s;
                    """,
                    (str(assoc_in.source_node_id), str(assoc_in.target_node_id), assoc_in.type.value)
                )
                exist_row = cur.fetchone()
                if exist_row:
                    assoc_id = exist_row[0]
                else:
                    continue # Should not happen unless deleted concurrently

            # Establish provenance bridge in experience_associations
            # Use ON CONFLICT DO NOTHING in case it already exists
            cur.execute(
                """
                INSERT INTO experience_associations (experience_id, association_id, is_positive)
                VALUES (%s, %s, %s)
                ON CONFLICT (experience_id, association_id) DO NOTHING;
                """,
                (str(exp_id), str(assoc_id), True)
            )

    return saved_associations
