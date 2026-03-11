"""配置加载模块 — 读取 config.toml"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # LLM
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:7b"
    # 嵌入
    embedding_provider: str = "local"  # "local" | "api"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    # 服务器
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5
    # 存储
    data_dir: str = "data"


def load_config(path: str = "config.toml") -> Config:
    """从 TOML 文件加载配置，缺失字段使用默认值"""
    config = Config()
    config_path = Path(path)

    if not config_path.exists():
        # 尝试从示例配置复制
        example = Path("config.example.toml")
        if example.exists():
            config_path.write_text(example.read_text())
        else:
            return config

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # LLM
    llm = data.get("llm", {})
    config.llm_base_url = llm.get("base_url", config.llm_base_url)
    config.llm_api_key = llm.get("api_key", config.llm_api_key)
    config.llm_model = llm.get("model", config.llm_model)

    # 嵌入
    emb = data.get("embedding", {})
    config.embedding_provider = emb.get("provider", config.embedding_provider)
    config.embedding_model = emb.get("model", config.embedding_model)
    config.embedding_base_url = emb.get("base_url", config.embedding_base_url)
    config.embedding_api_key = emb.get("api_key", config.embedding_api_key)

    # 服务器
    srv = data.get("server", {})
    config.server_host = srv.get("host", config.server_host)
    config.server_port = srv.get("port", config.server_port)

    # RAG
    rag = data.get("rag", {})
    config.chunk_size = rag.get("chunk_size", config.chunk_size)
    config.chunk_overlap = rag.get("chunk_overlap", config.chunk_overlap)
    config.top_k = rag.get("top_k", config.top_k)

    # 存储
    storage = data.get("storage", {})
    config.data_dir = storage.get("data_dir", config.data_dir)

    return config


def save_config(config: Config, path: str = "config.toml"):
    """将配置写回 TOML 文件"""
    content = f"""[llm]
base_url = "{config.llm_base_url}"
api_key = "{config.llm_api_key}"
model = "{config.llm_model}"

[embedding]
provider = "{config.embedding_provider}"
model = "{config.embedding_model}"
base_url = "{config.embedding_base_url}"
api_key = "{config.embedding_api_key}"

[server]
host = "{config.server_host}"
port = {config.server_port}

[rag]
chunk_size = {config.chunk_size}
chunk_overlap = {config.chunk_overlap}
top_k = {config.top_k}
"""
    Path(path).write_text(content)
