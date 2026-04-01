import logging

from fastapi import APIRouter, HTTPException

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
		pipeline = get_pipeline()
		return HealthResponse(status="ok", pipeline_info=pipeline.get_pipeline_info())
	except Exception as exc:
		logger.exception("Error while processing /health endpoint")
		return HealthResponse(status="error", pipeline_info={"error": str(exc)})
