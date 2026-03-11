"""文本分块 — 递归字符分割策略"""

import re


def chunk_text(
    text: str, chunk_size: int = 512, chunk_overlap: int = 64
) -> list[dict]:
    """
    将文本分割成重叠的块。

    策略：
    1. 按段落分割（\\n\\n）
    2. 长段落按句子分割（。！？.!?\\n）
    3. 合并小段直到接近 chunk_size
    4. 相邻块有 chunk_overlap 字符的重叠
    """
    if not text.strip():
        return []

    # 按段落分割
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    # 将长段落进一步按句子分割
    segments = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            segments.append(para)
        else:
            sentences = re.split(r"(?<=[。！？.!?\n])", para)
            sentences = [s.strip() for s in sentences if s.strip()]
            segments.extend(sentences)

    # 合并小段，形成 chunks
    chunks = []
    current = ""

    for seg in segments:
        if len(current) + len(seg) + 1 <= chunk_size:
            current = f"{current}\n{seg}" if current else seg
        else:
            if current:
                chunks.append(current)
            # 如果单个 segment 超过 chunk_size，硬截断
            if len(seg) > chunk_size:
                for i in range(0, len(seg), chunk_size - chunk_overlap):
                    chunks.append(seg[i : i + chunk_size])
                current = ""
            else:
                current = seg

    if current:
        chunks.append(current)

    # 添加重叠
    result = []
    for i, chunk in enumerate(chunks):
        # 如果不是第一个块，从前一个块尾部取 overlap
        if i > 0 and chunk_overlap > 0:
            prev_tail = chunks[i - 1][-chunk_overlap:]
            # 只在不重复时添加
            if not chunk.startswith(prev_tail):
                chunk = prev_tail + chunk

        result.append({"text": chunk, "index": i})

    return result
