import logging

from app.routes.ingest import router as ingest_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.query import router as query_router
from rag.pipeline import get_pipeline

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
        "https://finlens-rag.vercel.app",      # ← Your current Vercel domain
        "https://*.vercel.app",               # ← Allows all Vercel subdomains (safe for future deploys)
    ],
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


@app.on_event("startup")
async def on_startup() -> None:
    """Warm up pipeline in background so healthcheck passes immediately."""
    import asyncio
    logger.info("FinLens API starting up")
    asyncio.create_task(warm_up_pipeline())

async def warm_up_pipeline():
    import asyncio
    await asyncio.sleep(2)
    try:
        get_pipeline()
        logger.info("Pipeline ready")
    except Exception as e:
        logger.error(f"Pipeline warmup failed: {e}")