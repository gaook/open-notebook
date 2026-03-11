"""ChromaDB 向量存储封装"""

import chromadb


class VectorStore:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)

    def get_collection(self, notebook_id: str):
        """每个笔记本一个 collection"""
        return self.client.get_or_create_collection(
            name=f"nb_{notebook_id}",
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        notebook_id: str,
        chunks: list[dict],
        embeddings: list[list[float]],
        doc_id: str,
    ):
        collection = self.get_collection(notebook_id)
        collection.add(
            ids=[f"{doc_id}_chunk_{i}" for i in range(len(chunks))],
            embeddings=embeddings,
            documents=[c["text"] for c in chunks],
            metadatas=[
                {"doc_id": doc_id, "chunk_index": c["index"]} for c in chunks
            ],
        )

    def query(
        self,
        notebook_id: str,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> dict:
        collection = self.get_collection(notebook_id)
        if collection.count() == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

    def delete_document(self, notebook_id: str, doc_id: str):
        collection = self.get_collection(notebook_id)
        collection.delete(where={"doc_id": doc_id})

    def delete_collection(self, notebook_id: str):
        name = f"nb_{notebook_id}"
        try:
            self.client.delete_collection(name)
        except ValueError:
            pass
