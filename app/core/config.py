from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "RAG Document Retrieval API"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    chroma_persist_dir: str = "chroma_data"
    chroma_collection_name: str = "document_chunks"
    chroma_telemetry: bool = False

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 800
    chunk_overlap: int = 120
    default_top_k: int = 4
    max_context_chunks: int = 4

    generation_backend: str = "extractive"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"

    tesseract_cmd: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
