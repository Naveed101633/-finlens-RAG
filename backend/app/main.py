import logging

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://finlens-rag.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
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