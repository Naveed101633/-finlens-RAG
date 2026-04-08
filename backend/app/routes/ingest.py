import logging
import shutil
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from qdrant_client import models

from ingestion.chunker import TextChunker
from ingestion.indexer import QdrantIndexer
from ingestion.loader import PDFLoader
from rag.pipeline import get_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ingest"])
UPLOAD_JOBS: dict[str, dict] = {}
UPLOAD_JOBS_LOCK = Lock()


def _update_upload_job(job_id: str, updates: dict) -> None:
	with UPLOAD_JOBS_LOCK:
		if job_id in UPLOAD_JOBS:
			UPLOAD_JOBS[job_id].update(updates)


def _process_upload_job(job_id: str, file_path: str, filename: str) -> None:
	try:
		_update_upload_job(job_id, {"status": "processing", "stage": "Loading pipeline"})
		pipeline = get_pipeline()
		embed_batch_size = max(16, int(pipeline.settings.ingest_embed_batch_size))
		upsert_batch_size = max(32, int(pipeline.settings.ingest_qdrant_upsert_batch_size))
		max_chunks_per_upload = max(200, int(pipeline.settings.ingest_max_chunks_per_upload))
		bm25_max_chunks = max(0, int(pipeline.settings.ingest_bm25_max_chunks_in_memory))

		_update_upload_job(job_id, {"stage": "Extracting text from PDF"})
		loader = PDFLoader(file_path)
		pages = loader.load()

		_update_upload_job(job_id, {"stage": "Chunking document"})
		chunker = TextChunker(
			chunk_size=pipeline.settings.chunk_size,
			chunk_overlap=pipeline.settings.chunk_overlap,
		)
		chunks = chunker.chunk_documents(pages)
		if not chunks:
			raise ValueError("No valid text chunks were extracted from this PDF")
		if len(chunks) > max_chunks_per_upload:
			_update_upload_job(
				job_id,
				{
					"stage": (
						f"Document too large, indexing first {max_chunks_per_upload} "
						f"of {len(chunks)} chunks"
					),
				},
			)
			chunks = chunks[:max_chunks_per_upload]

		_update_upload_job(job_id, {"stage": "Preparing vector index"})
		indexer = QdrantIndexer(
			host=pipeline.settings.qdrant_host,
			port=pipeline.settings.qdrant_port,
			collection_name=pipeline.settings.collection_name,
			embedding_dim=pipeline.embedder.get_embedding_dimension(),
		)
		indexer.create_collection()

		total_chunks = len(chunks)
		total_indexed = 0
		for i in range(0, total_chunks, embed_batch_size):
			batch_chunks = chunks[i:i + embed_batch_size]
			_update_upload_job(
				job_id,
				{
					"stage": f"Embedding/indexing chunks ({total_indexed}/{total_chunks})",
				},
			)
			batch_embeddings = pipeline.embedder.embed_chunks(batch_chunks)
			indexer.index_chunks(batch_embeddings, batch_size=upsert_batch_size)
			total_indexed += len(batch_chunks)

		_update_upload_job(job_id, {"stage": "Updating keyword index"})
		new_bm25_chunks = [
			{
				"text": chunk.text,
				"chunk_id": chunk.chunk_id,
				"page_number": chunk.page_number,
				"source_file": chunk.source_file,
				"chunk_index": chunk.chunk_index,
			}
			for chunk in chunks
		]
		if bm25_max_chunks > 0:
			existing_bm25 = pipeline.retriever.bm25_chunks or []
			combined_bm25 = existing_bm25 + new_bm25_chunks
			if len(combined_bm25) > bm25_max_chunks:
				combined_bm25 = combined_bm25[-bm25_max_chunks:]
			pipeline.retriever.build_bm25_index(combined_bm25)
		else:
			logger.info("BM25 in-memory update skipped by configuration")

		_update_upload_job(
			job_id,
			{
				"status": "completed",
				"stage": "Done",
				"filename": filename,
				"pages_loaded": len(pages),
				"chunks_created": len(chunks),
				"message": "Document uploaded and indexed successfully",
			},
		)
		logger.info("Upload and ingestion completed for: %s", filename)
	except Exception as exc:
		logger.exception("Error while processing background upload")
		_update_upload_job(
			job_id,
			{
				"status": "failed",
				"stage": "Failed",
				"error": str(exc),
			},
		)


@router.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> dict:
	"""Accept a PDF upload and process ingestion asynchronously."""
	if file.content_type != "application/pdf" or not (file.filename or "").lower().endswith(".pdf"):
		raise HTTPException(status_code=400, detail="Only PDF files are supported")

	try:
		logger.info("Starting upload for file: %s", file.filename)

		raw_dir = Path(__file__).parent.parent.parent.parent / "data" / "raw"
		raw_dir.mkdir(parents=True, exist_ok=True)

		destination = raw_dir / file.filename
		logger.info("Saving uploaded file to: %s", destination)
		with destination.open("wb") as buffer:
			shutil.copyfileobj(file.file, buffer)

		job_id = str(uuid4())
		with UPLOAD_JOBS_LOCK:
			UPLOAD_JOBS[job_id] = {
				"job_id": job_id,
				"status": "queued",
				"stage": "Queued",
				"filename": file.filename,
			}

		background_tasks.add_task(_process_upload_job, job_id, str(destination), file.filename or "")
		logger.info("Upload accepted for async processing: %s (job %s)", file.filename, job_id)
		return {
			"job_id": job_id,
			"status": "queued",
			"message": "Upload accepted. Processing started in background.",
		}
	except HTTPException:
		raise
	except Exception as exc:
		logger.exception("Error while processing upload")
		raise HTTPException(status_code=500, detail=str(exc)) from exc
	finally:
		await file.close()


@router.get("/upload-status/{job_id}")
def upload_status(job_id: str) -> dict:
	"""Return upload processing status for a job."""
	with UPLOAD_JOBS_LOCK:
		job = UPLOAD_JOBS.get(job_id)

	if not job:
		raise HTTPException(status_code=404, detail="Upload job not found")

	return job


@router.get("/documents")
def list_documents() -> dict:
	"""Return unique source files currently indexed in Qdrant."""
	try:
		pipeline = get_pipeline()
		points, _ = pipeline.retriever.client.scroll(
			collection_name=pipeline.settings.collection_name,
			limit=10000,
			with_payload=True,
			with_vectors=False,
		)

		documents = sorted(
			{
				point.payload.get("source_file")
				for point in points
				if point.payload and point.payload.get("source_file")
			}
		)

		return {"documents": documents, "total": len(documents)}
	except Exception as exc:
		logger.exception("Error while listing documents")
		raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/documents/{filename}")
def delete_document(filename: str) -> dict:
	"""Delete all indexed chunks for a source file and rebuild BM25 index."""
	try:
		pipeline = get_pipeline()

		logger.info("Deleting document from index: %s", filename)
		pipeline.retriever.client.delete(
			collection_name=pipeline.settings.collection_name,
			points_selector=models.Filter(
				must=[
					models.FieldCondition(
						key="source_file",
						match=models.MatchValue(value=filename),
					)
				]
			),
		)

		points, _ = pipeline.retriever.client.scroll(
			collection_name=pipeline.settings.collection_name,
			limit=10000,
			with_payload=True,
			with_vectors=False,
		)
		chunks = [
			{
				"text": point.payload["text"],
				"chunk_id": point.payload["chunk_id"],
				"page_number": point.payload["page_number"],
				"source_file": point.payload["source_file"],
				"chunk_index": point.payload["chunk_index"],
			}
			for point in points
		]
		pipeline.retriever.build_bm25_index(chunks)

		logger.info("Document deleted from index: %s", filename)
		return {
			"filename": filename,
			"status": "deleted",
			"message": f"{filename} removed from index",
		}
	except Exception as exc:
		logger.exception("Error while deleting document: %s", filename)
		raise HTTPException(status_code=500, detail=str(exc)) from exc
