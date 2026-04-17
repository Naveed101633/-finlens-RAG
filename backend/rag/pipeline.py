"""RAG pipeline orchestration for FinLens."""

import logging
from functools import lru_cache

from app.config import Settings, get_settings
from ingestion.embedder import Embedder
from rag.retriever import Retriever
from rag.generator import Generator, GeneratedAnswer

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Orchestrates the complete RAG pipeline: retrieval + generation."""
    
    def __init__(self, settings: Settings):
        """Initialize the RAG pipeline with all components.
        
        Args:
            settings: Application settings instance
        """
        logger.info("Initializing FinLens RAG Pipeline components")
        
        # Initialize embedder
        self.embedder = Embedder(model_name=settings.embedding_model)
        
        # Initialize retriever
        self.retriever = Retriever(
            qdrant_host=settings.qdrant_host,
            qdrant_port=settings.qdrant_port,
            collection_name=settings.collection_name,
            embedder=self.embedder
        )

        # On first deployment the collection may not exist yet; treat that as a valid empty state.
        try:
            collection_exists = self.retriever.client.collection_exists(settings.collection_name)
        except Exception as exc:
            logger.warning("Could not verify collection existence: %s", exc)
            collection_exists = False

        if collection_exists:
            logger.info(
                "Collection '%s' exists. BM25 will be updated during uploads; "
                "semantic retrieval is available immediately.",
                settings.collection_name,
            )
        else:
            logger.info(
                "Collection '%s' not found yet; upload flow will create it on first document.",
                settings.collection_name,
            )
        
        # Initialize generator
        self.generator = Generator(
            api_key=settings.google_api_key,
            model=settings.gemini_model,
            fallback_model=settings.gemini_fallback_model,
        )
        
        # Store settings for reference
        self.settings = settings
        
        logger.info("FinLens RAG Pipeline initialized")
    
    def query(self, question: str, top_k: int = None) -> GeneratedAnswer:
        """Process a query through the complete RAG pipeline.
        
        Args:
            question: User's question
            top_k: Number of chunks to retrieve (uses settings.top_k_retrieval if None)
            
        Returns:
            GeneratedAnswer with answer, citations, and metadata
        """
        # Use settings default if top_k not specified
        if top_k is None:
            top_k = self.settings.top_k_retrieval
        
        logger.info(f"Processing query: '{question}' with top_k={top_k}")
        
        # Retrieve relevant chunks
        search_results = self.retriever.hybrid_search(question, top_k=top_k)
        
        # Generate answer from retrieved context
        answer = self.generator.generate(question, search_results)
        
        logger.info(f"Query completed, answer length: {len(answer.answer)} characters")
        
        return answer
    
    def get_pipeline_info(self) -> dict:
        """Get information about the pipeline configuration.
        
        Returns:
            Dictionary containing pipeline metadata
        """
        return {
            "embedding_model": self.settings.embedding_model,
            "gemini_model": self.settings.gemini_model,
            "collection_name": self.settings.collection_name,
            "qdrant_host": self.settings.qdrant_host,
            "status": "ready"
        }


@lru_cache
def get_pipeline() -> RAGPipeline:
    """Get cached RAG pipeline instance.
    
    Returns:
        Cached RAGPipeline instance
    """
    return RAGPipeline(get_settings())
