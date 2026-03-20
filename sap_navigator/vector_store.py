from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

from sap_navigator.models import DocumentChunk, RetrievalResult
from sap_navigator.providers import EmbeddingProvider


@dataclass(slots=True)
class VectorStoreStats:
    chunk_count: int
    metadata: dict


class PersistentVectorStore:
    def __init__(
        self,
        *,
        vector_dir: Path,
        collection_name: str,
        embedding_provider: EmbeddingProvider,
        embedding_signature: str,
    ) -> None:
        self.vector_dir = vector_dir
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
        self.embedding_signature = embedding_signature
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.vector_dir))

    def replace_collection(self, chunks: list[DocumentChunk]) -> VectorStoreStats:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:  # noqa: BLE001
            pass

        collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"embedding_signature": self.embedding_signature},
        )
        self._upsert(collection, chunks)
        return self.stats()

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> VectorStoreStats:
        collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"embedding_signature": self.embedding_signature},
        )
        self._upsert(collection, chunks)
        return self.stats()

    def search(self, query: str, *, top_k: int) -> list[RetrievalResult]:
        try:
            collection = self.client.get_collection(self.collection_name)
        except Exception:  # noqa: BLE001
            return []
        embedding = self.embedding_provider.embed_query(query)
        result = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        return [
            RetrievalResult(
                chunk_id=chunk_id,
                content=content,
                metadata=metadata or {},
                distance=distance,
            )
            for chunk_id, content, metadata, distance in zip(ids, documents, metadatas, distances, strict=False)
        ]

    def stats(self) -> VectorStoreStats:
        try:
            collection = self.client.get_collection(self.collection_name)
        except Exception:  # noqa: BLE001
            return VectorStoreStats(chunk_count=0, metadata={})
        return VectorStoreStats(chunk_count=collection.count(), metadata=collection.metadata or {})

    def _upsert(self, collection: Collection, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return

        embeddings = self.embedding_provider.embed_documents([chunk.content for chunk in chunks])
        collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
            embeddings=embeddings,
        )
