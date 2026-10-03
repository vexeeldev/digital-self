import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extensions import connection
from pydantic import BaseModel
from typing import List

from api.deps import get_db

router = APIRouter(prefix="/memory", tags=["Memory"])

class MemoryNodeResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    associations_count: int
@router.get("/graph")
def get_graph(experience_id: str | None = None, node_id: str | None = None, db: connection = Depends(get_db)):
    with db.cursor() as cur:
        if experience_id:
            cur.execute("""
                SELECT n.id, n.name, n.type 
                FROM nodes n
                JOIN vw_active_experience_nodes en ON n.id = en.node_id
                WHERE en.experience_id = %s
                GROUP BY n.id, n.name, n.type
            """, (experience_id,))
            nodes = [{"id": str(r[0]), "name": r[1], "type": r[2]} for r in cur.fetchall()]
            
            cur.execute("""
                SELECT a.id, a.source_node_id, a.target_node_id, a.type 
                FROM associations a
                JOIN vw_active_experience_associations ea ON a.id = ea.association_id
                WHERE ea.experience_id = %s
                GROUP BY a.id, a.source_node_id, a.target_node_id, a.type
            """, (experience_id,))
            edges = [{"id": str(r[0]), "source": str(r[1]), "target": str(r[2]), "type": r[3]} for r in cur.fetchall()]
            
        elif node_id:
            # fetch node and its immediate neighbors
            cur.execute("""
                SELECT id, name, type FROM nodes 
                WHERE id = %s OR id IN (
                    SELECT source_node_id FROM associations WHERE target_node_id = %s
                    UNION
                    SELECT target_node_id FROM associations WHERE source_node_id = %s
                )
            """, (node_id, node_id, node_id))
            nodes = [{"id": str(r[0]), "name": r[1], "type": r[2]} for r in cur.fetchall()]
            
            cur.execute("""
                SELECT id, source_node_id, target_node_id, type 
                FROM associations 
                WHERE source_node_id = %s OR target_node_id = %s
            """, (node_id, node_id))
            edges = [{"id": str(r[0]), "source": str(r[1]), "target": str(r[2]), "type": r[3]} for r in cur.fetchall()]
            
        else:
            # Global view: return all nodes
            cur.execute("""
                SELECT id, name, type 
                FROM nodes 
                ORDER BY last_seen DESC, activation DESC 
            """)
            nodes = [{"id": str(r[0]), "name": r[1], "type": r[2]} for r in cur.fetchall()]
            
            if nodes:
                node_ids = tuple(n["id"] for n in nodes)
                # Get associations only between these top nodes
                cur.execute("""
                    SELECT id, source_node_id, target_node_id, type 
                    FROM associations 
                    WHERE source_node_id IN %s AND target_node_id IN %s
                """, (node_ids, node_ids))
                edges = [{"id": str(r[0]), "source": str(r[1]), "target": str(r[2]), "type": r[3]} for r in cur.fetchall()]
            else:
                edges = []
            
    return {"nodes": nodes, "edges": edges}

@router.get("/{node_id}", response_model=MemoryNodeResponse)
def get_memory_node(node_id: uuid.UUID, db: connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT id, name, type FROM nodes WHERE id = %s", (str(node_id),))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
            
        cur.execute(
            "SELECT COUNT(*) FROM associations WHERE source_node_id = %s OR target_node_id = %s",
            (str(node_id), str(node_id))
        )
        assoc_count = cur.fetchone()[0]
        
    return MemoryNodeResponse(
        id=row[0],
        name=row[1],
        type=row[2],
        associations_count=assoc_count
    )
