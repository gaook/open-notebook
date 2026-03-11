"""文档解析器 — 从 PDF/DOCX/TXT/MD 提取纯文本和图片"""

import base64
from pathlib import Path


def extract_pdf_images(file_path: str) -> list[dict]:
    """从 PDF 提取所有图片，返回 [{page, data_uri}]"""
    import fitz

    images = []
    doc = fitz.open(file_path)
    for page_num, page in enumerate(doc):
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                # 转为 RGB（如果是 CMYK 等）
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                # 跳过太小的图片（图标、装饰等）
                if pix.width < 50 or pix.height < 50:
                    continue
                png_data = pix.tobytes("png")
                b64 = base64.b64encode(png_data).decode("ascii")
                images.append({
                    "page": page_num + 1,
                    "width": pix.width,
                    "height": pix.height,
                    "data_uri": f"data:image/png;base64,{b64}",
                })
            except Exception:
                continue
    doc.close()
    return images


def parse_document(file_path: str, file_type: str) -> str:
    """提取文档纯文本内容"""
    if file_type == "pdf":
        return _parse_pdf(file_path)
    elif file_type == "docx":
        return _parse_docx(file_path)
    elif file_type in ("txt", "md"):
        return Path(file_path).read_text(encoding="utf-8")
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def parse_document_with_pages(file_path: str, file_type: str) -> str:
    """提取文档文本，PDF 会在每页开头加入 <!-- PAGE:N --> 标记"""
    if file_type == "pdf":
        return _parse_pdf(file_path, with_page_markers=True)
    # 非 PDF 无页码概念，直接返回
    return parse_document(file_path, file_type)


def _parse_pdf(file_path: str, with_page_markers: bool = False) -> str:
    """解析 PDF 文本，可选在每页开头插入页码标记"""
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    texts = []
    for i, page in enumerate(doc):
        if with_page_markers:
            texts.append(f"<!-- PAGE:{i+1} -->")
        texts.append(page.get_text("text"))
    doc.close()
    return "\n".join(texts)


def _parse_docx(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    texts = []
    for para in doc.paragraphs:
        if para.text.strip():
            texts.append(para.text)
    # 也提取表格内容
    for table in doc.tables:
        for row in table.rows:
            row_text = "\t".join(cell.text for cell in row.cells)
            if row_text.strip():
                texts.append(row_text)
    return "\n".join(texts)
