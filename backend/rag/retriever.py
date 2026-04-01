"""Vector search retrieval for FinLens RAG system."""

import logging
from dataclasses import dataclass
from typing import List

import numpy as np
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient
from qdrant_client import models

from ingestion.embedder import Embedder

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a search result from vector database."""
    
    chunk_id: str
    text: str
    page_number: int
    source_file: str
    score: float
    chunk_index: int


class Retriever:
    """Retrieves relevant chunks from Qdrant vector database."""
    
    def __init__(
        self,
        qdrant_host: str,
        qdrant_port: int,
        collection_name: str,
        embedder: Embedder
    ):
        """Initialize the retriever.
        
        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            collection_name: Name of the collection to search
            embedder: Embedder instance for query embedding
        """
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.embedder = embedder
        
        logger.info(f"Initializing Retriever with Qdrant at {qdrant_host}:{qdrant_port}")
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.bm25_index = None
        self.bm25_chunks = []
        logger.info(f"Retriever connected to collection: {collection_name}")
    
    def search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        """Search for relevant chunks using vector similarity.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of SearchResult objects sorted by score descending
        """
        logger.info(f"Searching for query: '{query}' (top_k={top_k})")
        
        # Embed the query
        query_embedding = self.embedder.embed_text(query)
        
        # Search Qdrant
        search_results = self.client.query_points(
    collection_name=self.collection_name,
    query=query_embedding,
    limit=top_k
    ).points
        
        # Map results to SearchResult objects
        results = []
        for result in search_results:
            search_result = SearchResult(
                chunk_id=result.payload["chunk_id"],
                text=result.payload["text"],
                page_number=result.payload["page_number"],
                source_file=result.payload["source_file"],
                score=result.score,
                chunk_index=result.payload["chunk_index"]
            )
            results.append(search_result)
        
        logger.info(f"Found {len(results)} results")
        
        # Results are already sorted by score descending from Qdrant
        return results
    
    def search_with_filter(
        self,
        query: str,
        source_file: str,
        top_k: int = 20
    ) -> List[SearchResult]:
        """Search for relevant chunks filtered by source file.
        
        Args:
            query: Search query text
            source_file: Source file to filter by
            top_k: Number of results to return
            
        Returns:
            List of SearchResult objects sorted by score descending
        """
        logger.info(
            f"Searching for query: '{query}' filtered by source_file='{source_file}' (top_k={top_k})"
        )
        
        # Embed the query
        query_embedding = self.embedder.embed_text(query)
        
        # Create filter for source_file
        search_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="source_file",
                    match=models.MatchValue(value=source_file)
                )
            ]
        )
        
        # Search Qdrant with filter
        search_results = self.client.query_points(
    collection_name=self.collection_name,
    query=query_embedding,
    query_filter=search_filter,
    limit=top_k
    ).points
        
        # Map results to SearchResult objects
        results = []
        for result in search_results:
            search_result = SearchResult(
                chunk_id=result.payload["chunk_id"],
                text=result.payload["text"],
                page_number=result.payload["page_number"],
                source_file=result.payload["source_file"],
                score=result.score,
                chunk_index=result.payload["chunk_index"]
            )
            results.append(search_result)
        
        logger.info(f"Found {len(results)} results for source_file '{source_file}'")
        
        # Results are already sorted by score descending from Qdrant
        return results

    def build_bm25_index(self, chunks: list[dict]) -> None:
        """Build BM25 index from chunks for keyword retrieval."""
        tokenized_corpus = [chunk["text"].split() for chunk in chunks]
        self.bm25_index = BM25Okapi(tokenized_corpus)
        self.bm25_chunks = chunks
        logger.info(f"BM25 index built with {len(chunks)} documents")

    def bm25_search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        """Search indexed chunks using BM25 keyword scoring."""
        if self.bm25_index is None:
            logger.warning("BM25 index is not built. Returning empty BM25 results")
            return []

        query_tokens = query.split()
        scores = self.bm25_index.get_scores(query_tokens)

        if len(scores) == 0:
            return []

        top_indices = np.argsort(scores)[::-1][:top_k]
        max_score = float(np.max(scores)) if len(scores) > 0 else 0.0

        results: list[SearchResult] = []
        for idx in top_indices:
            raw_score = float(scores[idx])
            normalized_score = (raw_score / max_score) if max_score > 0 else 0.0
            chunk = self.bm25_chunks[int(idx)]

            results.append(
                SearchResult(
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    page_number=chunk.get("page_number", 0),
                    source_file=chunk.get("source_file", ""),
                    score=normalized_score,
                    chunk_index=chunk.get("chunk_index", 0),
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def hybrid_search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        logger.info("Hybrid search combining semantic and BM25 results")

        # If no documents indexed return empty
        if self.bm25_index is None or len(self.bm25_chunks) == 0:
            logger.warning("No documents indexed. Returning empty results.")
            return []

        semantic_results = self.search(query, top_k=top_k * 2)
        bm25_results = self.bm25_search(query, top_k=top_k * 2)

        rrf_k = 60
        fused_scores: dict[str, float] = {}
        best_by_chunk: dict[str, SearchResult] = {}

        for rank, result in enumerate(semantic_results, start=1):
            fused_scores[result.chunk_id] = fused_scores.get(result.chunk_id, 0.0) + (1.0 / (rrf_k + rank))
            if result.chunk_id not in best_by_chunk:
                best_by_chunk[result.chunk_id] = result

        for rank, result in enumerate(bm25_results, start=1):
            fused_scores[result.chunk_id] = fused_scores.get(result.chunk_id, 0.0) + (1.0 / (rrf_k + rank))
            if result.chunk_id not in best_by_chunk:
                best_by_chunk[result.chunk_id] = result

        ranked_chunk_ids = sorted(fused_scores.keys(), key=lambda chunk_id: fused_scores[chunk_id], reverse=True)[:top_k]

        hybrid_results: list[SearchResult] = []
        for chunk_id in ranked_chunk_ids:
            base = best_by_chunk[chunk_id]
            hybrid_results.append(
                SearchResult(
                    chunk_id=base.chunk_id,
                    text=base.text,
                    page_number=base.page_number,
                    source_file=base.source_file,
                    score=fused_scores[chunk_id],
                    chunk_index=base.chunk_index,
                )
            )

        return hybrid_results
