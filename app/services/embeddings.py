"""嵌入模型抽象层 — 支持本地 sentence-transformers 和 API"""

from __future__ import annotations
import httpx


class EmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


class LocalEmbedding(EmbeddingProvider):
    """使用 sentence-transformers 本地模型"""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        from sentence_transformers import SentenceTransformer
        print(f"加载嵌入模型: {model_name} ...")
        self.model = SentenceTransformer(model_name)
        print("嵌入模型加载完成")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


class APIEmbedding(EmbeddingProvider):
    """使用 OpenAI 兼容的嵌入 API"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": texts},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


def create_embedding_service(config) -> EmbeddingProvider:
    if config.embedding_provider == "api":
        return APIEmbedding(
            base_url=config.embedding_base_url,
            api_key=config.embedding_api_key,
            model=config.embedding_model,
        )
    return LocalEmbedding(config.embedding_model)
