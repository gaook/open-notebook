"""RAG 对话路由 — SSE 流式"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.database import get_conn
from app.models import ChatRequest, MessageOut

router = APIRouter(tags=["chat"])


@router.get("/notebooks/{notebook_id}/chat/history")
def get_chat_history(notebook_id: str, limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE notebook_id = ? ORDER BY id DESC LIMIT ?",
        (notebook_id, limit),
    ).fetchall()
    conn.close()
    messages = [
        MessageOut(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            sources=r["sources"],
            created_at=r["created_at"],
        )
        for r in reversed(rows)
    ]
    return {"messages": messages}


@router.post("/notebooks/{notebook_id}/chat")
async def chat(notebook_id: str, body: ChatRequest):
    from app.main import config, vector_store, get_embedding_service
    embedding_service = get_embedding_service()
    from app.services.retriever import Retriever
    from app.services.llm import LLMService

    # 验证笔记本
    conn = get_conn()
    nb = conn.execute("SELECT id FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
    if not nb:
        conn.close()
        raise HTTPException(status_code=404, detail="笔记本不存在")

    # 保存用户消息
    conn.execute(
        "INSERT INTO messages (notebook_id, role, content) VALUES (?, 'user', ?)",
        (notebook_id, body.message),
    )
    conn.commit()

    # 更新笔记本时间戳
    conn.execute(
        "UPDATE notebooks SET updated_at = datetime('now') WHERE id = ?",
        (notebook_id,),
    )
    conn.commit()

    # 检索相关文档块
    retriever = Retriever(vector_store, embedding_service)
    retrieved = retriever.retrieve(notebook_id, body.message, top_k=config.top_k)

    # 获取最近对话历史
    recent = conn.execute(
        "SELECT role, content FROM messages WHERE notebook_id = ? ORDER BY id DESC LIMIT 10",
        (notebook_id,),
    ).fetchall()
    conn.close()
    history = [{"role": r["role"], "content": r["content"]} for r in reversed(recent)]

    # 构建提示词
    context = ""
    sources_data = []
    if retrieved:
        for i, r in enumerate(retrieved):
            context += f"\n[来源{i + 1}: {r['filename']}]\n{r['text']}\n"
            sources_data.append({
                "doc_id": r["doc_id"],
                "filename": r["filename"],
                "snippet": r["text"][:100],
            })

    system_prompt = """你是一个智能笔记本助手。请根据以下参考资料回答用户的问题。

规则：
1. 仅根据提供的参考资料回答，不要编造信息
2. 如果参考资料中没有相关信息，请明确说明
3. 引用来源时使用 [来源N] 格式标注
4. 回答使用中文"""

    if context:
        system_prompt += f"\n\n参考资料：{context}"
    else:
        system_prompt += "\n\n（当前笔记本没有上传文档，请基于你的知识回答）"

    messages = [{"role": "system", "content": system_prompt}]
    # 添加历史（不含刚插入的用户消息，因为已在 history 末尾）
    messages.extend(history)

    # 流式生成
    llm = LLMService(config.llm_base_url, config.llm_api_key, config.llm_model)

    async def event_stream():
        full_response = ""
        try:
            async for chunk in llm.chat_stream(messages):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

            # 发送来源信息
            if sources_data:
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data}, ensure_ascii=False)}\n\n"

            # 保存助手消息
            conn2 = get_conn()
            conn2.execute(
                "INSERT INTO messages (notebook_id, role, content, sources) VALUES (?, 'assistant', ?, ?)",
                (notebook_id, full_response, json.dumps(sources_data, ensure_ascii=False) if sources_data else None),
            )
            conn2.commit()
            msg_id = conn2.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
            conn2.close()

            yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/notebooks/{notebook_id}/chat/history")
def clear_chat_history(notebook_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM messages WHERE notebook_id = ?", (notebook_id,))
    conn.commit()
    conn.close()
    return {"success": True}
