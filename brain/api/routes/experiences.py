import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extensions import connection

from api.schemas import ExperienceCreate, ExperienceResponse
from api.deps import get_db
from ingestion import ingest_experience
from llm_provider import get_llm_client

router = APIRouter(prefix="/experiences", tags=["Experiences"])

@router.post("", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
def create_experience(request: ExperienceCreate, db: connection = Depends(get_db)):
    try:
        from experience import ExperienceCreate as EngineExperienceCreate
        llm_client = get_llm_client()
        exp_tuple = ingest_experience(db, EngineExperienceCreate(raw_text=request.raw_text), llm_client=llm_client)
        exp_id = exp_tuple[0].id
        db.commit()
        
        # We need to fetch the newly created experience to return it
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, raw_text, occurred_at, created_at FROM experiences WHERE id = %s",
                (str(exp_id),)
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=500, detail="Failed to retrieve created experience")
            
        return ExperienceResponse(
            id=row[0],
            raw_text=row[1],
            occurred_at=row[2].isoformat() if row[2] else None,
            created_at=row[3].isoformat() if row[3] else None
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{experience_id}", response_model=ExperienceResponse)
def get_experience(experience_id: uuid.UUID, db: connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, raw_text, occurred_at, created_at FROM experiences WHERE id = %s",
            (str(experience_id),)
        )
        row = cur.fetchone()
        
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
        
    return ExperienceResponse(
        id=row[0],
        raw_text=row[1],
        occurred_at=row[2].isoformat() if row[2] else None,
        created_at=row[3].isoformat() if row[3] else None
    )

@router.get("", response_model=list[ExperienceResponse])
def list_experiences(db: connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, raw_text, occurred_at, created_at FROM experiences ORDER BY created_at DESC LIMIT 50"
        )
        rows = cur.fetchall()
        
    return [
        ExperienceResponse(
            id=row[0],
            raw_text=row[1],
            occurred_at=row[2].isoformat() if row[2] else None,
            created_at=row[3].isoformat() if row[3] else None
        )
        for row in rows
    ]

@router.delete("/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(experience_id: uuid.UUID, db: connection = Depends(get_db)):
    with db.cursor() as cur:
        # Check if exists
        cur.execute("SELECT id FROM experiences WHERE id = %s", (str(experience_id),))
        if not cur.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")
            
        try:
            # 1. Delete assemblies and their members
            cur.execute("DELETE FROM assembly_members WHERE assembly_id IN (SELECT id FROM assemblies WHERE experience_id = %s)", (str(experience_id),))
            cur.execute("DELETE FROM assemblies WHERE experience_id = %s", (str(experience_id),))
            
            # 2. Delete associations where source_experience_id matches
            # First delete their bridges
            cur.execute("DELETE FROM experience_associations WHERE association_id IN (SELECT id FROM associations WHERE source_experience_id = %s)", (str(experience_id),))
            cur.execute("DELETE FROM associations WHERE source_experience_id = %s", (str(experience_id),))
            
            # 3. Delete experience_associations for this experience
            cur.execute("DELETE FROM experience_associations WHERE experience_id = %s", (str(experience_id),))
            
            # 4. Delete experience_nodes for this experience
            cur.execute("DELETE FROM experience_nodes WHERE experience_id = %s", (str(experience_id),))
            
            # 5. Finally delete the experience
            cur.execute("DELETE FROM experiences WHERE id = %s", (str(experience_id),))
            
            # 6. Clean up orphans
            cur.execute("DELETE FROM associations WHERE id NOT IN (SELECT association_id FROM experience_associations)")
            cur.execute("DELETE FROM assembly_members WHERE node_id NOT IN (SELECT node_id FROM experience_nodes)")
            cur.execute("DELETE FROM nodes WHERE id NOT IN (SELECT node_id FROM experience_nodes)")
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    return None
