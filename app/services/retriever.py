"""RAG 检索器 — 组合向量搜索与文档元数据"""

from app.services.vector_store import VectorStore
from app.services.embeddings import EmbeddingProvider
from app.database import get_conn


class Retriever:
    def __init__(self, vector_store: VectorStore, embeddings: EmbeddingProvider):
        self.vector_store = vector_store
        self.embeddings = embeddings

    def retrieve(
        self, notebook_id: str, query: str, top_k: int = 5
    ) -> list[dict]:
        """检索与查询最相关的文档块"""
        query_embedding = self.embeddings.embed_query(query)
        results = self.vector_store.query(notebook_id, query_embedding, n_results=top_k)

        if not results["documents"][0]:
            return []

        # 查询文档文件名
        doc_ids = set(m["doc_id"] for m in results["metadatas"][0])
        conn = get_conn()
        filenames = {}
        for doc_id in doc_ids:
            row = conn.execute(
                "SELECT filename FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            if row:
                filenames[doc_id] = row["filename"]
        conn.close()

        retrieved = []
        for i, text in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            retrieved.append({
                "text": text,
                "doc_id": meta["doc_id"],
                "chunk_index": meta["chunk_index"],
                "score": 1 - distance,  # cosine distance → similarity
                "filename": filenames.get(meta["doc_id"], "未知文档"),
            })

        return retrieved
