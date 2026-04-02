"""Text embedding for FinLens RAG system using FastEmbed."""

import logging
import time
from typing import List, Tuple

from fastembed import TextEmbedding

from ingestion.chunker import TextChunk

logger = logging.getLogger(__name__)


class Embedder:
    """Generates embeddings using FastEmbed ONNX runtime — no PyTorch required."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        logger.info(f"Loading embedding model: {model_name}")
        start_time = time.time()
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.2f} seconds")

    def embed_text(self, text: str) -> List[float]:
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()

    def embed_chunks(
        self,
        chunks: List[TextChunk]
    ) -> List[Tuple[TextChunk, List[float]]]:
        logger.info(f"Embedding {len(chunks)} chunks")
        texts = [chunk.text for chunk in chunks]
        embeddings = list(self.model.embed(texts))
        results = [
            (chunk, emb.tolist())
            for chunk, emb in zip(chunks, embeddings)
        ]
        logger.info(f"Completed embedding all {len(chunks)} chunks")
        return results

    def get_embedding_dimension(self) -> int:
        return 384