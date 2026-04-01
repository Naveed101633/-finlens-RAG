"""Text embedding for FinLens RAG system."""

import logging
import time
from typing import List, Tuple

from sentence_transformers import SentenceTransformer

from ingestion.chunker import TextChunk

logger = logging.getLogger(__name__)


class Embedder:
    """Generates embeddings for text chunks using SentenceTransformer models."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the embedder with a SentenceTransformer model.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        logger.info(f"Loading embedding model: {model_name}")
        start_time = time.time()
        
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.2f} seconds")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector as a list of floats
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_chunks(
        self, 
        chunks: List[TextChunk]
    ) -> List[Tuple[TextChunk, List[float]]]:
        """Generate embeddings for multiple text chunks in batches.
        
        Args:
            chunks: List of TextChunk objects to embed
            
        Returns:
            List of (chunk, embedding) tuples
        """
        logger.info(f"Embedding {len(chunks)} chunks")
        
        batch_size = 32
        results: List[Tuple[TextChunk, List[float]]] = []
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_texts = [chunk.text for chunk in batch_chunks]
            
            # Generate embeddings for the batch
            embeddings = self.model.encode(
                batch_texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Convert to list of floats and pair with chunks
            for chunk, embedding in zip(batch_chunks, embeddings):
                results.append((chunk, embedding.tolist()))
            
            # Log progress every 100 chunks
            if (i + batch_size) % 100 == 0 or (i + batch_size) >= len(chunks):
                processed = min(i + batch_size, len(chunks))
                logger.info(f"Embedded {processed}/{len(chunks)} chunks")
        
        logger.info(f"Completed embedding all {len(chunks)} chunks")
        
        return results
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors.
        
        Returns:
            Integer dimension of the embedding vectors
        """
        return self.model.get_sentence_embedding_dimension()
