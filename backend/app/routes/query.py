import logging

from fastapi import APIRouter, HTTPException
from qdrant_client import QdrantClient

from app.config import get_settings
from app.models.schemas import (
	CitationResponse,
	HealthResponse,
	QueryRequest,
	QueryResponse,
)
from rag.pipeline import get_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_documents(request: QueryRequest) -> QueryResponse:
	"""Run a RAG query and return the answer with citations."""
	logger.info("Incoming query question: %s", request.question)

	try:
		pipeline = get_pipeline()
		generated_answer = pipeline.query(request.question, request.top_k)

		citations = [CitationResponse(**citation) for citation in generated_answer.citations]

		return QueryResponse(
			answer=generated_answer.answer,
			citations=citations,
			query=generated_answer.query,
			model_used=generated_answer.model_used,
		)
	except Exception as exc:
		logger.exception("Error while processing /query endpoint")
		raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
	"""Return health status and pipeline metadata."""
	try:
		settings = get_settings()
		client = QdrantClient(
			host=settings.qdrant_host,
			port=settings.qdrant_port,
			api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
			https=True if settings.qdrant_api_key else False,
		)
		collection_exists = client.collection_exists(settings.collection_name)
		return HealthResponse(
			status="ok",
			pipeline_info={
				"collection_name": settings.collection_name,
				"qdrant_host": settings.qdrant_host,
				"collection_exists": collection_exists,
			},
		)
	except Exception as exc:
		logger.exception("Error while processing /health endpoint")
		return HealthResponse(status="error", pipeline_info={"error": str(exc)})
