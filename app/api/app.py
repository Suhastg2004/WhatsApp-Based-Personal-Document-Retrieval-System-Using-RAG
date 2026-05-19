from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.core.config import get_settings
from app.core.schemas import HealthResponse, IngestResponse, QueryRequest, QueryResponse, SourceChunk
from app.services.embeddings import EmbeddingService
from app.services.ingestion import IngestionService
from app.services.parsing import DocumentParser
from app.services.rag import RAGEngine
from app.storage.chroma_store import ChromaVectorStore

settings = get_settings()
app = FastAPI(title=settings.app_name)

upload_dir = Path("uploads")

store = ChromaVectorStore(
    persist_dir=settings.chroma_persist_dir,
    collection_name=settings.chroma_collection_name,
)
embedder = EmbeddingService(model_name=settings.embedding_model_name)
parser = DocumentParser(tesseract_cmd=settings.tesseract_cmd)
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


@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>RAG Playground</title>
    <style>
      body { font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; margin: 32px; }
      h1 { margin-bottom: 4px; }
      .panel { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
      textarea { width: 100%; min-height: 120px; }
      button { padding: 8px 14px; }
      .row { display: flex; gap: 12px; flex-wrap: wrap; }
      .row > * { flex: 1; }
      .status { color: #555; font-size: 14px; }
      pre { white-space: pre-wrap; background: #f7f7f7; padding: 12px; border-radius: 6px; }
    </style>
  </head>
  <body>
    <h1>RAG Playground</h1>
    <p class="status">Upload documents, then ask a question to validate responses end-to-end.</p>

    <div class="panel">
      <h2>1) Upload Files</h2>
      <input id="fileInput" type="file" multiple />
      <button id="uploadBtn">Upload</button>
      <p class="status" id="uploadStatus"></p>
    </div>

    <div class="panel">
      <h2>2) Ask a Question</h2>
      <textarea id="question" placeholder="Ask a question about the uploaded documents..."></textarea>
      <div class="row">
        <input id="topK" type="number" min="1" max="20" value="4" />
        <button id="askBtn">Ask</button>
      </div>
      <h3>Answer</h3>
      <pre id="answer"></pre>
      <h3>Sources</h3>
      <pre id="sources"></pre>
    </div>

    <script>
      const uploadBtn = document.getElementById("uploadBtn");
      const askBtn = document.getElementById("askBtn");
      const uploadStatus = document.getElementById("uploadStatus");
      const answerEl = document.getElementById("answer");
      const sourcesEl = document.getElementById("sources");

      uploadBtn.addEventListener("click", async () => {
        const files = document.getElementById("fileInput").files;
        if (!files || files.length === 0) {
          uploadStatus.textContent = "Select at least one file.";
          return;
        }
        const data = new FormData();
        for (const file of files) {
          data.append("files", file);
        }
        uploadStatus.textContent = "Uploading...";
        const res = await fetch("/ingest/files", { method: "POST", body: data });
        const payload = await res.json();
        if (!res.ok) {
          uploadStatus.textContent = payload.detail || "Upload failed.";
          return;
        }
        uploadStatus.textContent = `Uploaded ${payload.files_processed} files, indexed ${payload.chunks_indexed} chunks.`;
      });

      askBtn.addEventListener("click", async () => {
        const question = document.getElementById("question").value.trim();
        if (!question) {
          answerEl.textContent = "Enter a question.";
          return;
        }
        const topK = Number(document.getElementById("topK").value || 4);
        answerEl.textContent = "Thinking...";
        sourcesEl.textContent = "";
        const res = await fetch("/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, top_k: topK }),
        });
        const payload = await res.json();
        if (!res.ok) {
          answerEl.textContent = payload.detail || "Query failed.";
          return;
        }
        answerEl.textContent = payload.answer;
        sourcesEl.textContent = JSON.stringify(payload.sources, null, 2);
      });
    </script>
  </body>
</html>
"""


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
