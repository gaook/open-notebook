"""内容生成路由 — 摘要/FAQ/学习指南/时间线/翻译"""

import asyncio
import json
import re
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.database import get_conn
from app.models import GenerateRequest, GeneratedContentOut, SaveNoteRequest, UpdateTitleRequest

router = APIRouter(tags=["generate"])


async def _stream_with_timeout(aiter, timeout: float):
    """给 async generator 的每次 next 加超时保护。
    如果某次 next 超过 timeout 秒未返回，抛出 asyncio.TimeoutError。"""
    ait = aiter.__aiter__()
    while True:
        try:
            token = await asyncio.wait_for(ait.__anext__(), timeout=timeout)
            yield token
        except StopAsyncIteration:
            break

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
    "translate": {
        "title": "中文翻译",
        "prompt": "请将以下文档内容完整、准确地翻译为中文。要求：\n1. 保持原文的标题层级、列表、代码块等 Markdown 格式结构\n2. 专业术语翻译准确，首次出现时在括号内附注英文原文\n3. 数学公式保持 LaTeX 格式不翻译\n4. 译文应通顺自然，符合中文表达习惯\n5. 不要遗漏任何内容，完整翻译全文\n6. 文本中的 <!-- PAGE:N --> 标记是页码分隔符，请原样保留在翻译结果中，不要翻译或删除",
    },
}


def _split_text_into_chunks(text: str, max_chars: int = 6000) -> list[str]:
    """按段落边界切分文本为多段，每段不超过 max_chars"""
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current.strip())
            current = ""
        current += para + "\n\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


# 参考文献标题的常见写法
_REFERENCES_PATTERNS = re.compile(
    r"^(?:<!-- PAGE:\d+ -->\s*)?(?:Preprint\s*)?"
    r"(REFERENCES|References|Bibliography|BIBLIOGRAPHY|参考文献)\s*$",
    re.MULTILINE,
)


def _split_references(chunks: list[str]) -> list[dict]:
    """标记每个段是否属于参考文献区域，返回 [{text, is_refs}]。

    检测到 REFERENCES / Bibliography / 参考文献 标题后，该段及后续段
    标记为 is_refs=True，直到遇到附录 (APPENDIX / Theorem Proofs 等) 恢复正常翻译。
    """
    result = []
    in_refs = False
    appendix_re = re.compile(
        r"^(?:<!-- PAGE:\d+ -->\s*)?(?:Preprint\s*)?"
        r"(APPENDI|Appendi|附录|THEOREM PROOFS|Theorem Proofs|"
        r"SUPPLEMENTARY|Supplementary|A\s+THEOREM)",
        re.MULTILINE,
    )
    for chunk in chunks:
        if not in_refs and _REFERENCES_PATTERNS.search(chunk):
            in_refs = True
        if in_refs and appendix_re.search(chunk):
            # 附录内容仍需翻译，但可能和参考文献混在同一段
            # 简化处理：整段恢复翻译
            in_refs = False
        result.append({"text": chunk, "is_refs": in_refs})
    return result


_SKIP_TITLE_WORDS = {
    "preprint", "abstract", "introduction", "contents", "table of contents",
    "acknowledgments", "acknowledgements", "references", "appendix",
    "copyright", "draft", "manuscript", "arxiv", "submitted",
}


def _extract_title(text: str) -> str:
    """从文档文本中提取标题（跳过无意义的首行如 Preprint）"""
    candidates = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 跳过页码标记
        if line.startswith("<!-- PAGE:"):
            continue
        # 跳过文档分隔线 --- filename ---
        if line.startswith("---") and line.endswith("---"):
            continue
        # 去掉 Markdown 标题标记
        cleaned = re.sub(r"^#+\s*", "", line).strip()
        if not cleaned:
            continue
        # 跳过太短 (<=3字符) 或无意义的行
        if cleaned.lower() in _SKIP_TITLE_WORDS:
            continue
        if len(cleaned) <= 3:
            continue
        # 截断过长标题
        return cleaned[:80] if len(cleaned) > 80 else cleaned
    return "中文翻译"


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
        "SELECT filename, full_text, file_path, file_type FROM documents WHERE notebook_id = ? AND status = 'ready'",
        (notebook_id,),
    ).fetchall()
    conn.close()

    if not docs:
        raise HTTPException(status_code=400, detail="笔记本中没有已就绪的文档")

    # 构建完整文档内容
    doc_content = ""
    if body.type == "translate":
        # 翻译模式：使用带页码标记的文本
        from app.services.document_parser import parse_document_with_pages
        for doc in docs:
            file_path = doc["file_path"] if "file_path" in doc.keys() else None
            file_type = doc["file_type"] if "file_type" in doc.keys() else None
            if file_path and file_type:
                paged_text = parse_document_with_pages(file_path, file_type)
                doc_content += f"\n\n--- {doc['filename']} ---\n{paged_text}"
            else:
                doc_content += f"\n\n--- {doc['filename']} ---\n{doc['full_text']}"
    else:
        for doc in docs:
            doc_content += f"\n\n--- {doc['filename']} ---\n{doc['full_text']}"

    gen_config = GENERATE_PROMPTS[body.type]
    llm = LLMService(config.llm_base_url, config.llm_api_key, config.llm_model)
    content_id = uuid.uuid4().hex[:12]

    # 翻译模式：分段翻译，每段独立调用 LLM，带超时和错误恢复
    if body.type == "translate":
        # 提取文章标题
        article_title = _extract_title(doc_content)
        raw_chunks = _split_text_into_chunks(doc_content, max_chars=6000)
        tagged_chunks = _split_references(raw_chunks)
        total = len(tagged_chunks)
        MAX_RETRIES = 2  # 每段最多重试 2 次

        async def translate_stream():
            full_response = ""
            try:
                for i, chunk_info in enumerate(tagged_chunks):
                    chunk_text = chunk_info["text"]
                    is_refs = chunk_info["is_refs"]

                    # 进度提示
                    progress_msg = f"\n\n---\n**[翻译进度: {i+1}/{total}]**\n\n"
                    if i > 0:
                        full_response += progress_msg
                        yield f"data: {json.dumps({'type': 'chunk', 'content': progress_msg}, ensure_ascii=False)}\n\n"

                    # 参考文献段：直接保留原文，不调用 LLM
                    if is_refs:
                        refs_note = "\n\n> 📚 **参考文献部分，保留原文**\n\n"
                        full_response += refs_note + chunk_text
                        yield f"data: {json.dumps({'type': 'chunk', 'content': refs_note + chunk_text}, ensure_ascii=False)}\n\n"
                        continue

                    messages = [
                        {"role": "system", "content": gen_config["prompt"]},
                        {"role": "user", "content": chunk_text},
                    ]

                    chunk_success = False
                    for retry in range(MAX_RETRIES + 1):
                        try:
                            chunk_response = ""
                            async for token in _stream_with_timeout(
                                llm.chat_stream(messages, temperature=0.3),
                                timeout=60.0,  # 每个 token 最多等 60 秒
                            ):
                                chunk_response += token
                                full_response += token
                                yield f"data: {json.dumps({'type': 'chunk', 'content': token}, ensure_ascii=False)}\n\n"
                            chunk_success = True
                            break
                        except asyncio.TimeoutError:
                            warn_msg = f"\n\n> ⚠️ 第 {i+1} 段翻译超时"
                            if retry < MAX_RETRIES:
                                warn_msg += f"，正在重试 ({retry+1}/{MAX_RETRIES})...\n\n"
                            else:
                                warn_msg += "，已跳过此段。\n\n"
                            full_response += warn_msg
                            yield f"data: {json.dumps({'type': 'chunk', 'content': warn_msg}, ensure_ascii=False)}\n\n"
                        except Exception as chunk_err:
                            warn_msg = f"\n\n> ⚠️ 第 {i+1} 段翻译出错: {str(chunk_err)[:100]}"
                            if retry < MAX_RETRIES:
                                warn_msg += f"，正在重试 ({retry+1}/{MAX_RETRIES})...\n\n"
                            else:
                                warn_msg += "，已跳过此段。\n\n"
                            full_response += warn_msg
                            yield f"data: {json.dumps({'type': 'chunk', 'content': warn_msg}, ensure_ascii=False)}\n\n"

                # 保存
                conn2 = get_conn()
                conn2.execute(
                    "INSERT INTO generated_content (id, notebook_id, content_type, title, content) VALUES (?,?,?,?,?)",
                    (content_id, notebook_id, body.type, article_title, full_response),
                )
                conn2.commit()
                conn2.close()
                yield f"data: {json.dumps({'type': 'done', 'id': content_id, 'title': article_title}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(translate_stream(), media_type="text/event-stream")

    # 其他类型：单次调用（截断到 30000 字符）
    if len(doc_content) > 30000:
        doc_content = doc_content[:30000] + "\n\n[...文档内容过长，已截断...]"

    messages = [
        {"role": "system", "content": gen_config["prompt"]},
        {"role": "user", "content": doc_content},
    ]

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


@router.post("/notebooks/{notebook_id}/generated/note")
def save_note(notebook_id: str, body: SaveNoteRequest):
    conn = get_conn()
    nb = conn.execute("SELECT id FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
    if not nb:
        conn.close()
        raise HTTPException(status_code=404, detail="笔记本不存在")
    note_id = uuid.uuid4().hex[:12]
    conn.execute(
        "INSERT INTO generated_content (id, notebook_id, content_type, title, content) VALUES (?,?,?,?,?)",
        (note_id, notebook_id, "note", body.title, body.content),
    )
    conn.commit()
    conn.close()
    return {"id": note_id, "success": True}


@router.patch("/notebooks/{notebook_id}/generated/{item_id}/title")
def update_generated_title(notebook_id: str, item_id: str, body: UpdateTitleRequest):
    conn = get_conn()
    conn.execute(
        "UPDATE generated_content SET title = ? WHERE id = ? AND notebook_id = ?",
        (body.title.strip(), item_id, notebook_id),
    )
    conn.commit()
    conn.close()
    return {"success": True}


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
