"""内容生成路由 — 摘要/FAQ/学习指南/时间线"""

import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.database import get_conn
from app.models import GenerateRequest, GeneratedContentOut

router = APIRouter(tags=["generate"])

GENERATE_PROMPTS = {
    "summary": {
        "title": "文档摘要",
        "prompt": "请为以下文档内容生成一份结构化摘要。使用 Markdown 格式，包含主要主题、关键要点和核心结论。",
    },
    "faq": {
        "title": "常见问题",
        "prompt": "请根据以下文档内容，生成一份常见问题与解答（FAQ）列表。每个问题应该针对文档中的关键信息，解答应该准确且简洁。使用 Markdown 格式。",
    },
    "study_guide": {
        "title": "学习指南",
        "prompt": "请根据以下文档内容，生成一份学习指南。包含学习目标、关键概念、重点难点、以及理解检查问题。使用 Markdown 格式。",
    },
    "timeline": {
        "title": "时间线",
        "prompt": "请根据以下文档内容，提取所有关键事件和时间节点，按时间顺序排列生成一份时间线。如果没有明确的时间信息，按逻辑顺序排列。使用 Markdown 格式。",
    },
}


@router.post("/notebooks/{notebook_id}/generate")
async def generate_content(notebook_id: str, body: GenerateRequest):
    from app.main import config
    from app.services.llm import LLMService

    if body.type not in GENERATE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"不支持的生成类型: {body.type}")

    # 获取笔记本所有文档文本
    conn = get_conn()
    nb = conn.execute("SELECT id FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
    if not nb:
        conn.close()
        raise HTTPException(status_code=404, detail="笔记本不存在")

    docs = conn.execute(
        "SELECT filename, full_text FROM documents WHERE notebook_id = ? AND status = 'ready'",
        (notebook_id,),
    ).fetchall()
    conn.close()

    if not docs:
        raise HTTPException(status_code=400, detail="笔记本中没有已就绪的文档")

    # 构建完整文档内容（截断以适应上下文窗口）
    doc_content = ""
    for doc in docs:
        doc_content += f"\n\n--- {doc['filename']} ---\n{doc['full_text']}"

    # 截断到约 30000 字符（大约 30k tokens 中文）
    if len(doc_content) > 30000:
        doc_content = doc_content[:30000] + "\n\n[...文档内容过长，已截断...]"

    gen_config = GENERATE_PROMPTS[body.type]
    messages = [
        {"role": "system", "content": gen_config["prompt"]},
        {"role": "user", "content": doc_content},
    ]

    llm = LLMService(config.llm_base_url, config.llm_api_key, config.llm_model)
    content_id = uuid.uuid4().hex[:12]

    async def event_stream():
        full_response = ""
        try:
            async for chunk in llm.chat_stream(messages, temperature=0.3):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

            # 保存生成内容
            conn2 = get_conn()
            conn2.execute(
                "INSERT INTO generated_content (id, notebook_id, content_type, title, content) VALUES (?,?,?,?,?)",
                (content_id, notebook_id, body.type, gen_config["title"], full_response),
            )
            conn2.commit()
            conn2.close()

            yield f"data: {json.dumps({'type': 'done', 'id': content_id, 'title': gen_config['title']}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/notebooks/{notebook_id}/generated")
def list_generated(notebook_id: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, content_type, title, created_at FROM generated_content WHERE notebook_id = ? ORDER BY created_at DESC",
        (notebook_id,),
    ).fetchall()
    conn.close()
    return {
        "items": [
            GeneratedContentOut(
                id=r["id"],
                content_type=r["content_type"],
                title=r["title"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    }


@router.get("/notebooks/{notebook_id}/generated/{item_id}")
def get_generated(notebook_id: str, item_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM generated_content WHERE id = ? AND notebook_id = ?",
        (item_id, notebook_id),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="内容不存在")
    return GeneratedContentOut(
        id=row["id"],
        content_type=row["content_type"],
        title=row["title"],
        content=row["content"],
        created_at=row["created_at"],
    )


@router.delete("/notebooks/{notebook_id}/generated/{item_id}")
def delete_generated(notebook_id: str, item_id: str):
    conn = get_conn()
    conn.execute(
        "DELETE FROM generated_content WHERE id = ? AND notebook_id = ?",
        (item_id, notebook_id),
    )
    conn.commit()
    conn.close()
    return {"success": True}
