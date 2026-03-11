"""Pydantic 请求/响应模型"""

from pydantic import BaseModel


# ---- 笔记本 ----

class NotebookCreate(BaseModel):
    title: str = "未命名笔记本"
    description: str = ""


class NotebookUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class NotebookOut(BaseModel):
    id: str
    title: str
    description: str
    doc_count: int = 0
    message_count: int = 0
    created_at: str
    updated_at: str


# ---- 文档 ----

class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_msg: str | None = None
    created_at: str


# ---- 对话 ----

class ChatRequest(BaseModel):
    message: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: str | None = None
    created_at: str


# ---- 内容生成 ----

class GenerateRequest(BaseModel):
    type: str  # summary | faq | study_guide | timeline


class GeneratedContentOut(BaseModel):
    id: str
    content_type: str
    title: str
    content: str = ""
    created_at: str


# ---- 设置 ----

class SettingsOut(BaseModel):
    llm_base_url: str
    llm_model: str
    llm_api_key_set: bool
    embedding_provider: str
    embedding_model: str


class SettingsUpdate(BaseModel):
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
