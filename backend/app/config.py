from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings

# This finds the .env file no matter where Python is run from
ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    google_api_key: str
    qdrant_host: str = "localhost"
    qdrant_api_key: str = ""
    qdrant_port: int = 6333
    collection_name: str = "finlens_reports"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-3.1-flash-lite-preview"
    chunk_size: int = 512
    chunk_overlap: int = 50
    ingest_embed_batch_size: int = 64
    ingest_qdrant_upsert_batch_size: int = 128
    ingest_max_chunks_per_upload: int = 1200
    ingest_bm25_max_chunks_in_memory: int = 2000
    top_k_retrieval: int = 20
    top_k_rerank: int = 5

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()