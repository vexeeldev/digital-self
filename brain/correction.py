import uuid
from psycopg2.extensions import connection
from models import AssociationType
from learning import replay_association_learning

def emit_association_correction(conn: connection, exp_assoc_id: uuid.UUID, operation: str) -> uuid.UUID:
    """
    Appends a correction event (REJECT or RESTORE).
    The operation is transactional.
    Active Evidence is folded after the event.
    Affected derived learning state is deterministically replayed.
    The event must not commit if recalculation fails.
    """
    if operation not in ('REJECT', 'RESTORE'):
        raise ValueError("Invalid operation for emit_association_correction, expected REJECT or RESTORE.")

    with conn.cursor() as cur:
        # Check if the target exists
        cur.execute("SELECT association_id FROM experience_associations WHERE id = %s", (str(exp_assoc_id),))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Target experience_association {exp_assoc_id} does not exist.")
        assoc_id = row[0]

        # Determine current folded state
        cur.execute("SELECT id FROM vw_active_experience_associations WHERE id = %s", (str(exp_assoc_id),))
        is_active = cur.fetchone() is not None

        if operation == 'REJECT' and not is_active:
            raise ValueError("Cannot REJECT an already inactive/rejected link.")
        if operation == 'RESTORE' and is_active:
            raise ValueError("Cannot RESTORE an already active link.")

        # Emit correction event
        cur.execute(
            """
            INSERT INTO experience_association_corrections (experience_association_id, operation, actor)
            VALUES (%s, %s, 'human') RETURNING id
            """,
            (str(exp_assoc_id), operation)
        )
        correction_id = cur.fetchone()[0]

    # Replay affected learning
    replay_association_learning(conn, assoc_id)

    return uuid.UUID(correction_id)

def emit_assembly_member_correction(conn: connection, assembly_member_id: uuid.UUID, operation: str) -> uuid.UUID:
    if operation not in ('REJECT', 'RESTORE'):
        raise ValueError("Invalid operation, expected REJECT or RESTORE.")
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM assembly_members WHERE id = %s", (str(assembly_member_id),))
        if not cur.fetchone():
            raise ValueError(f"Target assembly_member {assembly_member_id} does not exist.")
            
        cur.execute("SELECT id FROM vw_active_assembly_members WHERE id = %s", (str(assembly_member_id),))
        is_active = cur.fetchone() is not None
        
        if operation == 'REJECT' and not is_active:
            raise ValueError("Cannot REJECT an already inactive/rejected link.")
        if operation == 'RESTORE' and is_active:
            raise ValueError("Cannot RESTORE an already active link.")
            
        cur.execute(
            """
            INSERT INTO assembly_member_corrections (assembly_member_id, operation, actor)
            VALUES (%s, %s, 'human') RETURNING id
            """,
            (str(assembly_member_id), operation)
        )
        correction_id = cur.fetchone()[0]
    return uuid.UUID(correction_id)

def add_human_association(conn: connection, experience_id: uuid.UUID, src_node: uuid.UUID, tgt_node: uuid.UUID, type: AssociationType) -> uuid.UUID:
    """
    State machine:
    - New provenance link: create link -> emit ADD -> replay
    - Rejected existing link: emit RESTORE -> replay
    - Active existing link: raise Duplicate/Error
    """
    with conn.cursor() as cur:
        # Check if the global canonical association exists
        cur.execute(
            """
            SELECT id FROM associations
            WHERE source_node_id = %s AND target_node_id = %s AND type = %s
            """,
            (str(src_node), str(tgt_node), type.value)
        )
        row = cur.fetchone()
        if not row:
            # We must create the global canonical association first (with source_experience_id = this exp)
            cur.execute(
                """
                INSERT INTO associations (source_node_id, target_node_id, type, source_experience_id, strength, confidence)
                VALUES (%s, %s, %s, %s, 0.100, 1.000) RETURNING id
                """,
                (str(src_node), str(tgt_node), type.value, str(experience_id))
            )
            assoc_id = cur.fetchone()[0]
        else:
            assoc_id = row[0]

        # Check existing provenance link
        cur.execute(
            """
            SELECT id FROM experience_associations
            WHERE experience_id = %s AND association_id = %s
            """,
            (str(experience_id), str(assoc_id))
        )
        link_row = cur.fetchone()

        if not link_row:
            # New provenance link
            cur.execute(
                """
                INSERT INTO experience_associations (experience_id, association_id, is_positive)
                VALUES (%s, %s, true) RETURNING id
                """,
                (str(experience_id), str(assoc_id))
            )
            exp_assoc_id = cur.fetchone()[0]
            
            cur.execute(
                """
                INSERT INTO experience_association_corrections (experience_association_id, operation, actor)
                VALUES (%s, 'ADD', 'human')
                """,
                (str(exp_assoc_id),)
            )
        else:
            exp_assoc_id = link_row[0]
            # Existing link, check if active
            cur.execute("SELECT id FROM vw_active_experience_associations WHERE id = %s", (str(exp_assoc_id),))
            if cur.fetchone():
                raise ValueError("Active existing link: Duplicate/Error.")
            else:
                # Rejected existing link, RESTORE
                cur.execute(
                    """
                    INSERT INTO experience_association_corrections (experience_association_id, operation, actor)
                    VALUES (%s, 'RESTORE', 'human')
                    """,
                    (str(exp_assoc_id),)
                )

    # Replay
    replay_association_learning(conn, assoc_id)

    return uuid.UUID(assoc_id)
