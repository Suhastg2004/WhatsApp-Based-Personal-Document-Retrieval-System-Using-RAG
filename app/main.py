from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.config import get_settings
from app.schemas import HealthResponse, IngestResponse, QueryRequest, QueryResponse, SourceChunk
from app.services.document_parser import DocumentParser
from app.services.embedder import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.rag_engine import RAGEngine
from app.services.simple_vector_store import SimpleVectorStore

settings = get_settings()
app = FastAPI(title=settings.app_name)

upload_dir = Path("uploads")

store = SimpleVectorStore(
    db_path=settings.sqlite_db_path,
    table_name=settings.sqlite_table_name,
)
embedder = EmbeddingService(model_name=settings.embedding_model_name)
parser = DocumentParser()
ingestor = IngestionService(
    parser=parser,
    embedder=embedder,
    store=store,
    upload_dir=upload_dir,
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
)
rag_engine = RAGEngine(
    backend=settings.generation_backend,
    groq_api_key=settings.groq_api_key,
    groq_model=settings.groq_model,
    max_context_chunks=settings.max_context_chunks,
)


@app.on_event("startup")
def on_startup() -> None:
    store.ensure_collection()


@app.on_event("shutdown")
def on_shutdown() -> None:
    store.close()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/ingest/files", response_model=IngestResponse)
async def ingest_files(files: list[UploadFile] = File(...)) -> IngestResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    try:
        chunks_indexed, document_ids = await ingestor.ingest_files(files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    return IngestResponse(
        files_processed=len(files),
        chunks_indexed=chunks_indexed,
        document_ids=document_ids,
    )


@app.post("/query", response_model=QueryResponse)
def query_documents(payload: QueryRequest) -> QueryResponse:
    top_k = payload.top_k or settings.default_top_k

    try:
        query_vector = embedder.embed_query(payload.question)
        matches = store.search(query_vector, top_k)
        answer = rag_engine.answer_question(payload.question, matches)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc

    sources = [
        SourceChunk(
            document_id=item.document_id,
            source=item.source,
            chunk_index=item.chunk_index,
            text=item.text,
            score=item.score,
        )
        for item in matches
    ]

    return QueryResponse(answer=answer, sources=sources)
