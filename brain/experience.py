import json
import uuid
from datetime import datetime
from psycopg2.extensions import connection

from models import ExperienceCreate, Experience

def save_experience(conn: connection, exp_in: ExperienceCreate) -> Experience:
    """
    Saves a raw experience to the database.
    
    Adheres to PRD V2.1 rules:
    - raw_text is stored exactly as is, without modification.
    - No LLM interpretation is performed here.
    - No nodes or associations are created here.
    - If occurred_at is provided, it is stored. Otherwise, it is NULL.
    """
    # Ensure raw_text is not blank (though Pydantic model already checks this)
    if not exp_in.raw_text.strip():
        raise ValueError("raw_text must not be blank")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO experiences (raw_text, occurred_at, metadata)
            VALUES (%s, %s, %s)
            RETURNING id, raw_text, occurred_at, created_at, metadata;
            """,
            (
                exp_in.raw_text,
                exp_in.occurred_at,
                json.dumps(exp_in.metadata)
            )
        )
        row = cur.fetchone()

    # row = (id, raw_text, occurred_at, created_at, metadata)
    return Experience(
        id=row[0],
        raw_text=row[1],
        occurred_at=row[2],
        created_at=row[3],
        metadata=row[4] if row[4] else {}
    )

def get_experience(conn: connection, exp_id: uuid.UUID) -> Experience | None:
    """
    Retrieves a raw experience from the database by its ID.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, raw_text, occurred_at, created_at, metadata
            FROM experiences
            WHERE id = %s;
            """,
            (str(exp_id),)
        )
        row = cur.fetchone()

    if not row:
        return None

    return Experience(
        id=row[0],
        raw_text=row[1],
        occurred_at=row[2],
        created_at=row[3],
        metadata=row[4] if row[4] else {}
    )
