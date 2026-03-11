"""笔记本 CRUD 路由"""

import uuid
from fastapi import APIRouter, HTTPException

from app.database import get_conn
from app.models import NotebookCreate, NotebookUpdate, NotebookOut

router = APIRouter(tags=["notebooks"])


@router.get("/notebooks")
def list_notebooks():
    conn = get_conn()
    rows = conn.execute("""
        SELECT n.*,
               COUNT(DISTINCT d.id) as doc_count,
               COUNT(DISTINCT m.id) as message_count
        FROM notebooks n
        LEFT JOIN documents d ON d.notebook_id = n.id
        LEFT JOIN messages m ON m.notebook_id = n.id
        GROUP BY n.id
        ORDER BY n.updated_at DESC
    """).fetchall()
    conn.close()
    return {
        "notebooks": [
            NotebookOut(
                id=r["id"],
                title=r["title"],
                description=r["description"],
                doc_count=r["doc_count"],
                message_count=r["message_count"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]
    }


@router.post("/notebooks")
def create_notebook(body: NotebookCreate):
    nb_id = uuid.uuid4().hex[:12]
    conn = get_conn()
    conn.execute(
        "INSERT INTO notebooks (id, title, description) VALUES (?, ?, ?)",
        (nb_id, body.title, body.description),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM notebooks WHERE id = ?", (nb_id,)).fetchone()
    conn.close()
    return NotebookOut(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/notebooks/{notebook_id}")
def get_notebook(notebook_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="笔记本不存在")
    doc_count = conn.execute(
        "SELECT COUNT(*) as c FROM documents WHERE notebook_id = ?", (notebook_id,)
    ).fetchone()["c"]
    msg_count = conn.execute(
        "SELECT COUNT(*) as c FROM messages WHERE notebook_id = ?", (notebook_id,)
    ).fetchone()["c"]
    conn.close()
    return NotebookOut(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        doc_count=doc_count,
        message_count=msg_count,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.put("/notebooks/{notebook_id}")
def update_notebook(notebook_id: str, body: NotebookUpdate):
    conn = get_conn()
    row = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="笔记本不存在")

    title = body.title if body.title is not None else row["title"]
    desc = body.description if body.description is not None else row["description"]

    conn.execute(
        "UPDATE notebooks SET title=?, description=?, updated_at=datetime('now') WHERE id=?",
        (title, desc, notebook_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
    conn.close()
    return NotebookOut(
        id=updated["id"],
        title=updated["title"],
        description=updated["description"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )


@router.delete("/notebooks/{notebook_id}")
def delete_notebook(notebook_id: str):
    from app.main import vector_store

    conn = get_conn()
    row = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="笔记本不存在")
    conn.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
    conn.commit()
    conn.close()

    # 删除向量集合
    if vector_store:
        vector_store.delete_collection(notebook_id)

    return {"success": True}
