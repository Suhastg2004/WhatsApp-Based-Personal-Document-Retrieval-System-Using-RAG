from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.services.chunker import chunk_text
from app.services.document_parser import DocumentParser
from app.services.embedder import EmbeddingService
from app.services.simple_vector_store import SimpleVectorStore


class IngestionService:
    def __init__(
        self,
        parser: DocumentParser,
        embedder: EmbeddingService,
        store: SimpleVectorStore,
        upload_dir: Path,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self._parser = parser
        self._embedder = embedder
        self._store = store
        self._upload_dir = upload_dir
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def ingest_files(self, files: list[UploadFile]) -> tuple[int, list[str]]:
        all_items: list[dict] = []
        document_ids: list[str] = []

        for file in files:
            document_id = str(uuid4())
            destination = self._upload_dir / f"{document_id}_{file.filename}"
            content = await file.read()
            destination.write_bytes(content)

            parsed = self._parser.parse_file(destination, document_id)
            chunks = chunk_text(parsed.text, self._chunk_size, self._chunk_overlap)
            vectors = self._embedder.embed_texts(chunks)

            for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False)):
                all_items.append(
                    {
                        "document_id": parsed.document_id,
                        "source": parsed.source,
                        "chunk_index": idx,
                        "text": chunk,
                        "vector": vector,
                    }
                )

            document_ids.append(parsed.document_id)

        inserted = self._store.insert_chunks(all_items)
        return inserted, document_ids
