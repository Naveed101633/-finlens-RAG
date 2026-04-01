"""Vector indexing for FinLens RAG system using Qdrant."""

import logging
from typing import List, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.config import get_settings
from ingestion.chunker import TextChunk

logger = logging.getLogger(__name__)


class QdrantIndexer:
    """Indexes text chunks and embeddings in Qdrant vector database."""
    
    def __init__(
        self, 
        host: str, 
        port: int, 
        collection_name: str, 
        embedding_dim: int = 384
    ):
        """Initialize the Qdrant indexer.
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of the collection to use
            embedding_dim: Dimension of the embedding vectors
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        
        logger.info(f"Connecting to Qdrant at {host}:{port}")
        from app.config import get_settings
        _settings = get_settings()
        self.client = QdrantClient(
        host=host,
        port=port,
        api_key=_settings.qdrant_api_key if _settings.qdrant_api_key else None,
        https=True if _settings.qdrant_api_key else False
    )
        logger.info(f"Connected to Qdrant, using collection: {collection_name}")
    
    def create_collection(self) -> None:
        """Create Qdrant collection if it does not exist.
        
        Uses cosine distance metric for similarity search.
        """
        try:
            # Check if collection already exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return
            
            # Create new collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            logger.info(
                f"Created collection '{self.collection_name}' with "
                f"dimension {self.embedding_dim} and COSINE distance"
            )
            
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise
    
    def index_chunks(
        self, 
        chunk_embeddings: List[Tuple[TextChunk, List[float]]]
    ) -> None:
        """Index text chunks with their embeddings in Qdrant.
        
        Args:
            chunk_embeddings: List of (chunk, embedding) tuples
        """
        logger.info(f"Indexing {len(chunk_embeddings)} chunks into '{self.collection_name}'")
        
        batch_size = 50
        total_indexed = 0
        
        for i in range(0, len(chunk_embeddings), batch_size):
            batch = chunk_embeddings[i:i + batch_size]
            points = []
            
            for chunk, embedding in batch:
                # Create point ID by hashing chunk_id
                point_id = abs(hash(chunk.chunk_id))  % (2**63)
                
                # Create payload with chunk metadata
                payload = {
                    "text": chunk.text,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "source_file": chunk.source_file,
                    "chunk_id": chunk.chunk_id,
                    "char_count": chunk.char_count
                }
                
                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            # Upload batch to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            total_indexed += len(points)
            logger.info(f"Indexed {total_indexed}/{len(chunk_embeddings)} chunks")
        
        logger.info(f"Completed indexing all {len(chunk_embeddings)} chunks")
    
    def get_collection_info(self) -> dict:
        """Get information about the collection.
        
        Returns:
            Dictionary containing collection metadata
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                "collection_name": self.collection_name,
                "total_points": collection_info.points_count,
                "embedding_dim": self.embedding_dim,
                "status": collection_info.status
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {
                "collection_name": self.collection_name,
                "total_points": 0,
                "embedding_dim": self.embedding_dim,
                "status": "error"
            }
