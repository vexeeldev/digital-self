import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extensions import connection

from api.schemas import CorrectionAdd, CorrectionUpdate
from api.deps import get_db
from models import AssociationType
from correction import add_human_association, emit_association_correction

router = APIRouter(prefix="/corrections", tags=["Corrections"])

@router.post("/associations/add", status_code=status.HTTP_201_CREATED)
def add_association_correction(request: CorrectionAdd, db: connection = Depends(get_db)):
    try:
        # We need to map string association type back to enum
        try:
            assoc_type = AssociationType(request.association_type)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid association type")
            
        add_human_association(
            conn=db,
            experience_id=request.experience_id,
            src_node=request.source_node_id,
            tgt_node=request.target_node_id,
            type=assoc_type
        )
        db.commit()
        return {"status": "SUCCESS"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/associations/reject")
def reject_association_correction(request: CorrectionUpdate, db: connection = Depends(get_db)):
    try:
        # emit expects experience_association_id. In the API we might pass it. 
        # But wait, request.association_id is actually experience_association_id for correction? 
        # Yes, emit_association_correction takes experience_association_id.
        emit_association_correction(db, request.association_id, "REJECT")
        db.commit()
        return {"status": "REJECTED"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/associations/restore")
def restore_association_correction(request: CorrectionUpdate, db: connection = Depends(get_db)):
    try:
        emit_association_correction(db, request.association_id, "RESTORE")
        db.commit()
        return {"status": "RESTORED"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
