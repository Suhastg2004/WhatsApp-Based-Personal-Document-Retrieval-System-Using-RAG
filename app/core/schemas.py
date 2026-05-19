from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class IngestResponse(BaseModel):
    files_processed: int
    chunks_indexed: int
    document_ids: list[str]


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceChunk(BaseModel):
    document_id: str
    source: str
    chunk_index: int
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
