from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
	"""Request payload for user queries."""

	question: str = Field(min_length=3, max_length=500)
	top_k: Optional[int] = Field(None, ge=1, le=50)


class CitationResponse(BaseModel):
	"""Citation details for retrieved evidence chunks."""

	page_number: int
	source_file: str
	chunk_id: str
	score: float


class QueryResponse(BaseModel):
	"""Response payload returned for a query."""

	answer: str
	citations: list[CitationResponse]
	query: str
	model_used: str


class HealthResponse(BaseModel):
	"""Health and pipeline status information."""

	status: str
	pipeline_info: dict
