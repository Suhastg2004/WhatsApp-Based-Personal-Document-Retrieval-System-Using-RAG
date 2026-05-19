from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any
from uuid import uuid4

if os.getenv("ANONYMIZED_TELEMETRY") is None:
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
if os.getenv("CHROMA_TELEMETRY") is None:
    os.environ["CHROMA_TELEMETRY"] = "false"

import chromadb


@dataclass
class RetrievedChunk:
    document_id: str
    source: str
    chunk_index: int
    text: str
    score: float


class ChromaVectorStore:
    def __init__(self, persist_dir: str, collection_name: str) -> None:
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = None

    def close(self) -> None:
        # Chroma's PersistentClient does not require explicit close.
        self._collection = None

    def ensure_collection(self) -> None:
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def insert_chunks(self, items: list[dict]) -> int:
        if not items:
            return 0

        if self._collection is None:
            self.ensure_collection()

        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []

        for item in items:
            ids.append(str(uuid4()))
            documents.append(item["text"])
            embeddings.append(item["vector"])
            metadatas.append(
                {
                    "document_id": item["document_id"],
                    "source": item["source"],
                    "chunk_index": int(item["chunk_index"]),
                }
            )

        self._collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    def search(self, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
        if self._collection is None:
            self.ensure_collection()

        result = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        if not documents or not metadatas or not distances:
            return []

        retrieved: list[RetrievedChunk] = []
        for text, metadata, distance in zip(documents, metadatas, distances, strict=False):
            if metadata is None:
                continue
            score = 1.0 - float(distance)
            retrieved.append(
                RetrievedChunk(
                    document_id=str(metadata.get("document_id", "")),
                    source=str(metadata.get("source", "")),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    text=str(text),
                    score=score,
                )
            )

        retrieved.sort(key=lambda item: item.score, reverse=True)
        return retrieved[:top_k]
