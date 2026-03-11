"""文档上传/解析/删除路由"""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks

from app.database import get_conn
from app.models import DocumentOut

router = APIRouter(tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

EXTENSION_MAP = {".pdf": "pdf", ".txt": "txt", ".md": "md", ".docx": "docx"}


def _get_file_type(filename: str, content_type: str) -> str:
    """从文件名或 content_type 推断文件类型"""
    ext = Path(filename).suffix.lower()
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]
    if content_type in ALLOWED_TYPES:
        return ALLOWED_TYPES[content_type]
    raise ValueError(f"不支持的文件类型: {filename}")


def _process_document(doc_id: str, notebook_id: str, file_path: str, file_type: str):
    """后台任务：解析、分块、嵌入文档"""
    from app.services.document_parser import parse_document
    from app.services.chunker import chunk_text
    from app.main import config, vector_store, get_embedding_service
    embedding_service = get_embedding_service()

    conn = get_conn()
    try:
        # 解析文本
        full_text = parse_document(file_path, file_type)
        if not full_text.strip():
            conn.execute(
                "UPDATE documents SET status='error', error_msg='文档内容为空' WHERE id=?",
                (doc_id,),
            )
            conn.commit()
            return

        # 分块
        chunks = chunk_text(full_text, config.chunk_size, config.chunk_overlap)

        # 嵌入
        texts = [c["text"] for c in chunks]
        embeddings = embedding_service.embed_texts(texts)

        # 存入向量库
        vector_store.add_chunks(notebook_id, chunks, embeddings, doc_id)

        # 更新数据库
        conn.execute(
            "UPDATE documents SET full_text=?, chunk_count=?, status='ready' WHERE id=?",
            (full_text, len(chunks), doc_id),
        )
        conn.commit()
    except Exception as e:
        conn.execute(
            "UPDATE documents SET status='error', error_msg=? WHERE id=?",
            (str(e)[:500], doc_id),
        )
        conn.commit()
    finally:
        conn.close()


@router.get("/notebooks/{notebook_id}/documents")
def list_documents(notebook_id: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM documents WHERE notebook_id = ? ORDER BY created_at DESC",
        (notebook_id,),
    ).fetchall()
    conn.close()
    return {
        "documents": [
            DocumentOut(
                id=r["id"],
                filename=r["filename"],
                file_type=r["file_type"],
                file_size=r["file_size"],
                chunk_count=r["chunk_count"],
                status=r["status"],
                error_msg=r["error_msg"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    }


@router.post("/notebooks/{notebook_id}/documents")
async def upload_document(
    notebook_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    # 验证笔记本存在
    conn = get_conn()
    nb = conn.execute("SELECT id FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
    if not nb:
        conn.close()
        raise HTTPException(status_code=404, detail="笔记本不存在")

    # 验证文件类型
    try:
        file_type = _get_file_type(file.filename, file.content_type)
    except ValueError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

    # 保存文件
    doc_id = uuid.uuid4().hex[:12]
    from app.main import config

    upload_dir = Path(config.data_dir) / "uploads" / notebook_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{doc_id}_{file.filename}"

    content = await file.read()
    file_path.write_bytes(content)

    # 创建数据库记录
    conn.execute(
        "INSERT INTO documents (id, notebook_id, filename, file_type, file_size, file_path) VALUES (?,?,?,?,?,?)",
        (doc_id, notebook_id, file.filename, file_type, len(content), str(file_path)),
    )
    conn.commit()
    conn.close()

    # 后台处理
    background_tasks.add_task(_process_document, doc_id, notebook_id, str(file_path), file_type)

    return DocumentOut(
        id=doc_id,
        filename=file.filename,
        file_type=file_type,
        file_size=len(content),
        chunk_count=0,
        status="processing",
        created_at="",
    )


@router.delete("/notebooks/{notebook_id}/documents/{doc_id}")
def delete_document(notebook_id: str, doc_id: str):
    from app.main import vector_store

    conn = get_conn()
    row = conn.execute("SELECT * FROM documents WHERE id = ? AND notebook_id = ?", (doc_id, notebook_id)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除文件
    file_path = Path(row["file_path"])
    if file_path.exists():
        file_path.unlink()

    # 删除数据库记录
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

    # 删除向量
    if vector_store:
        vector_store.delete_document(notebook_id, doc_id)

    return {"success": True}
