import uuid
import pytest
from fastapi.testclient import TestClient
from api.main import app
import psycopg2
import os

client = TestClient(app)

DB_USER = os.getenv("DB_USER", "malakul-tech")
DB_NAME = os.getenv("DB_NAME", "digital_self")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")

def test_api_corrections():
    # Setup node and exp in db to test corrections
    conn = psycopg2.connect(user=DB_USER, dbname=DB_NAME, host=DB_HOST, port=DB_PORT)
    cur = conn.cursor()
    
    cur.execute("INSERT INTO experiences (raw_text) VALUES ('correction setup') RETURNING id")
    exp_id = cur.fetchone()[0]
    
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Subj_{uuid.uuid4().hex}",))
    subj_id = cur.fetchone()[0]
    
    cur.execute("INSERT INTO nodes (type, name) VALUES ('person', %s) RETURNING id", (f"Obj_{uuid.uuid4().hex}",))
    obj_id = cur.fetchone()[0]
    
    conn.commit()
    
    # 21. ADD works through API.
    res_add = client.post("/corrections/associations/add", json={
        "experience_id": str(exp_id),
        "source_node_id": str(subj_id),
        "target_node_id": str(obj_id),
        "association_type": "supports"
    })
    assert res_add.status_code == 201
    
    # Get the experience_association_id
    cur.execute("SELECT id, association_id FROM experience_associations WHERE experience_id = %s", (str(exp_id),))
    row = cur.fetchone()
    ea_id = row[0]
    assoc_id = row[1]
    
    # Check it is active
    cur.execute("SELECT count(*) FROM vw_active_experience_associations WHERE id = %s", (str(ea_id),))
    assert cur.fetchone()[0] == 1
    
    # 22. REJECT works through API.
    res_reject = client.post("/corrections/associations/reject", json={"association_id": str(ea_id)})
    assert res_reject.status_code == 200
    
    # 24. Rejected evidence does not appear as active.
    cur.execute("SELECT count(*) FROM vw_active_experience_associations WHERE id = %s", (str(ea_id),))
    assert cur.fetchone()[0] == 0
    
    # 23. RESTORE works through API.
    res_restore = client.post("/corrections/associations/restore", json={"association_id": str(ea_id)})
    assert res_restore.status_code == 200
    
    cur.execute("SELECT count(*) FROM vw_active_experience_associations WHERE id = %s", (str(ea_id),))
    assert cur.fetchone()[0] == 1
    
    conn.close()
