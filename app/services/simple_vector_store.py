import json
import sqlite3
from dataclasses import dataclass

import numpy as np

@dataclass
class RetrievedChunk:
    document_id: str
    source: str
    chunk_index: int
    text: str
    score: float


class SimpleVectorStore:
    def __init__(self, db_path: str, table_name: str) -> None:
        self._table_name = table_name
        self._conn = sqlite3.connect(db_path, check_same_thread=False)

    def close(self) -> None:
        self._conn.close()

    def ensure_collection(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                source TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                vector TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def insert_chunks(self, items: list[dict]) -> int:
        if not items:
            return 0

        cursor = self._conn.cursor()
        cursor.executemany(
            f"""
            INSERT INTO {self._table_name} (document_id, source, chunk_index, text, vector)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    item["document_id"],
                    item["source"],
                    int(item["chunk_index"]),
                    item["text"],
                    json.dumps(item["vector"]),
                )
                for item in items
            ],
        )
        self._conn.commit()
        return len(items)

    def search(self, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
        cursor = self._conn.cursor()
        cursor.execute(
            f"""
            SELECT document_id, source, chunk_index, text, vector
            FROM {self._table_name}
            """
        )
        rows = cursor.fetchall()

        if not rows:
            return []

        query = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []

        scored: list[RetrievedChunk] = []
        for row in rows:
            vec = np.array(json.loads(row[4]), dtype=np.float32)
            denom = np.linalg.norm(vec) * query_norm
            if denom == 0:
                score = 0.0
            else:
                score = float(np.dot(query, vec) / denom)

            scored.append(
                RetrievedChunk(
                    document_id=str(row[0]),
                    source=str(row[1]),
                    chunk_index=int(row[2]),
                    text=str(row[3]),
                    score=score,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]