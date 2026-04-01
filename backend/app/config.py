from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings

# This finds the .env file no matter where Python is run from
ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    google_api_key: str
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    collection_name: str = "finlens_reports"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    gemini_model: str = "gemini-2.5-flash"
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k_retrieval: int = 20
    top_k_rerank: int = 5

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()