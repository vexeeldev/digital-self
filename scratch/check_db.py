import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../brain"))

from api.deps import get_db

def test():
    db_gen = get_db()
    cur = next(db_gen).cursor()
    cur.execute("SELECT id, raw_text FROM experiences ORDER BY created_at DESC LIMIT 1")
    exp = cur.fetchone()
    print("Latest Exp:", exp)
    cur.execute("SELECT n.name FROM nodes n JOIN experience_nodes en ON n.id = en.node_id WHERE en.experience_id = %s", (exp[0],))
    print("Nodes:", [r[0] for r in cur.fetchall()])
    cur.execute("SELECT (SELECT name FROM nodes WHERE id=a.source_node_id), (SELECT name FROM nodes WHERE id=a.target_node_id) FROM associations a JOIN experience_associations ea ON a.id = ea.association_id WHERE ea.experience_id = %s", (exp[0],))
    print("Edges:", cur.fetchall())

test()
