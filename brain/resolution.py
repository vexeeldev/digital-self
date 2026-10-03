"""
Digital Self - resolution.py
Version: V2.1 Initial Entity Resolution Engine
"""

import uuid
import enum
from pydantic import BaseModel
from psycopg2.extensions import connection
import psycopg2.errors

from models import NodeType

class MatchType(str, enum.Enum):
    EXACT_CANONICAL = "EXACT_CANONICAL"
    EXACT_ALIAS = "EXACT_ALIAS"
    NONE = "NONE"

class NodeResolutionResult(BaseModel):
    node_id: uuid.UUID
    is_new: bool
    match_type: MatchType
    canonical_name: str
    node_type: NodeType

def resolve_node(
    conn: connection,
    mention: str,
    node_type: NodeType,
    confidence: float = 0.5
) -> NodeResolutionResult:
    """
    Resolves a raw mention to a canonical node identity.
    Enforces deterministic matching (Rule 1 & 2) and type-safety.
    Handles concurrent insertions gracefully.
    """
    mention_clean = mention.strip()
    if not mention_clean:
        raise ValueError("Mention cannot be empty or whitespace.")

    if not isinstance(confidence, (int, float)) or confidence < 0.0 or confidence > 1.0:
        raise ValueError("Confidence must be between 0.0 and 1.0")

    with conn.cursor() as cur:
        # Rule 1: EXACT_CANONICAL match
        cur.execute(
            """
            SELECT id, name FROM nodes
            WHERE lower(name) = lower(%s) AND type = %s
            LIMIT 1;
            """,
            (mention_clean, node_type.value)
        )
        row = cur.fetchone()
        if row:
            return NodeResolutionResult(
                node_id=row[0],
                is_new=False,
                match_type=MatchType.EXACT_CANONICAL,
                canonical_name=row[1],
                node_type=node_type
            )
            
        # Rule 2: EXACT_ALIAS match
        cur.execute(
            """
            SELECT n.id, n.name FROM node_aliases a
            JOIN nodes n ON a.node_id = n.id
            WHERE lower(a.alias_name) = lower(%s) AND a.node_type = %s
            LIMIT 1;
            """,
            (mention_clean, node_type.value)
        )
        row = cur.fetchone()
        if row:
            return NodeResolutionResult(
                node_id=row[0],
                is_new=False,
                match_type=MatchType.EXACT_ALIAS,
                canonical_name=row[1],
                node_type=node_type
            )

        # Rule 3: CREATE NEW
        try:
            cur.execute("SAVEPOINT resolve_node_sp;")
            cur.execute(
                """
                INSERT INTO nodes (type, name, confidence)
                VALUES (%s, %s, %s)
                RETURNING id, name;
                """,
                (node_type.value, mention_clean, confidence)
            )
            row = cur.fetchone()
            cur.execute("RELEASE SAVEPOINT resolve_node_sp;")
            return NodeResolutionResult(
                node_id=row[0],
                is_new=True,
                match_type=MatchType.NONE,
                canonical_name=row[1],
                node_type=node_type
            )
        except psycopg2.errors.UniqueViolation:
            cur.execute("ROLLBACK TO SAVEPOINT resolve_node_sp;")
            
            # Race condition: someone else created it
            cur.execute(
                """
                SELECT id, name FROM nodes
                WHERE lower(name) = lower(%s) AND type = %s
                LIMIT 1;
                """,
                (mention_clean, node_type.value)
            )
            row = cur.fetchone()
            if row:
                return NodeResolutionResult(
                    node_id=row[0],
                    is_new=False,
                    match_type=MatchType.EXACT_CANONICAL,
                    canonical_name=row[1],
                    node_type=node_type
                )
            
            cur.execute(
                """
                SELECT n.id, n.name FROM node_aliases a
                JOIN nodes n ON a.node_id = n.id
                WHERE lower(a.alias_name) = lower(%s) AND a.node_type = %s
                LIMIT 1;
                """,
                (mention_clean, node_type.value)
            )
            row = cur.fetchone()
            if row:
                return NodeResolutionResult(
                    node_id=row[0],
                    is_new=False,
                    match_type=MatchType.EXACT_ALIAS,
                    canonical_name=row[1],
                    node_type=node_type
                )
            
            raise RuntimeError("UniqueViolation occurred but node not found.")

def add_alias(
    conn: connection,
    canonical_node_id: uuid.UUID,
    alias: str,
    node_type: NodeType
) -> None:
    """
    Registers an alias to a canonical node securely.
    """
    alias_clean = alias.strip()
    if not alias_clean:
        raise ValueError("Alias cannot be empty or whitespace.")
        
    with conn.cursor() as cur:
        # Avoid creating alias identical to a canonical node of the same type
        cur.execute(
            """
            SELECT id FROM nodes
            WHERE lower(name) = lower(%s) AND type = %s
            LIMIT 1;
            """,
            (alias_clean, node_type.value)
        )
        if cur.fetchone():
            raise ValueError("Alias name is already taken by a canonical node of the same type.")

        try:
            cur.execute("SAVEPOINT add_alias_sp;")
            cur.execute(
                """
                INSERT INTO node_aliases (node_id, alias_name, node_type)
                VALUES (%s, %s, %s);
                """,
                (str(canonical_node_id), alias_clean, node_type.value)
            )
            cur.execute("RELEASE SAVEPOINT add_alias_sp;")
        except psycopg2.errors.UniqueViolation:
            cur.execute("ROLLBACK TO SAVEPOINT add_alias_sp;")
            # Unique constraint on alias_name + node_type
            raise ValueError("Alias is already registered for this node type.")
