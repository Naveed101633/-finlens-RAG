import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from qdrant_client import models

from ingestion.chunker import TextChunker
from ingestion.indexer import QdrantIndexer
from ingestion.loader import PDFLoader
from rag.pipeline import get_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ingest"])
EMBED_INDEX_BATCH_SIZE = 96
QDRANT_UPSERT_BATCH_SIZE = 256


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
	"""Upload a PDF and run the full ingestion pipeline."""
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

		pipeline = get_pipeline()

		logger.info("Loading PDF pages")
		loader = PDFLoader(str(destination))
		pages = loader.load()

		logger.info("Chunking document text")
		chunker = TextChunker(
			chunk_size=pipeline.settings.chunk_size,
			chunk_overlap=pipeline.settings.chunk_overlap,
		)
		chunks = chunker.chunk_documents(pages)
		if not chunks:
			raise HTTPException(status_code=400, detail="No valid text chunks were extracted from this PDF")

		logger.info("Indexing chunks into existing Qdrant collection")
		indexer = QdrantIndexer(
			host=pipeline.settings.qdrant_host,
			port=pipeline.settings.qdrant_port,
			collection_name=pipeline.settings.collection_name,
			embedding_dim=pipeline.embedder.get_embedding_dimension(),
		)
		indexer.create_collection()

		logger.info("Embedding and indexing chunks in batches")
		total_indexed = 0
		for i in range(0, len(chunks), EMBED_INDEX_BATCH_SIZE):
			batch_chunks = chunks[i:i + EMBED_INDEX_BATCH_SIZE]
			batch_embeddings = pipeline.embedder.embed_chunks(batch_chunks)
			indexer.index_chunks(batch_embeddings, batch_size=QDRANT_UPSERT_BATCH_SIZE)
			total_indexed += len(batch_chunks)
			logger.info("Indexed batch: %s/%s chunks", total_indexed, len(chunks))

		# Keep BM25 in memory in sync without scrolling the whole collection every upload.
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
		existing_bm25 = pipeline.retriever.bm25_chunks or []
		pipeline.retriever.build_bm25_index(existing_bm25 + new_bm25_chunks)

		logger.info("Upload and ingestion completed for: %s", file.filename)
		return {
			"filename": file.filename,
			"pages_loaded": len(pages),
			"chunks_created": len(chunks),
			"status": "success",
			"message": "Document uploaded and indexed successfully",
		}
	except HTTPException:
		raise
	except Exception as exc:
		logger.exception("Error while processing upload")
		raise HTTPException(status_code=500, detail=str(exc)) from exc
	finally:
		await file.close()


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
