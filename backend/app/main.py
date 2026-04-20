import logging
import os

from app.routes.ingest import router as ingest_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.query import router as query_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
	title="FinLens API",
	description="AI-powered financial report analyst for PSX listed companies",
	version="1.0.0",
)

default_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://finlens-rag.vercel.app",
]

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(default_cors_origins)).split(",")
    if origin.strip()
]

cors_origin_regex = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"https://.*\.(vercel\.app|replit\.dev|replit\.app)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)
app.include_router(ingest_router)

@app.get("/")
def root() -> dict:
	"""Root endpoint with API metadata."""
	return {"message": "FinLens API", "version": "1.0.0", "docs": "/docs"}