"""Text chunking for FinLens RAG system."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from ingestion.loader import DocumentPage

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text from a document page."""
    
    chunk_id: str
    text: str
    page_number: int
    chunk_index: int
    char_count: int
    source_file: str


class TextChunker:
    """Splits document pages into overlapping text chunks."""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        """Initialize the text chunker.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        
        logger.info(
            f"Initialized TextChunker with chunk_size={chunk_size}, "
            f"chunk_overlap={chunk_overlap}"
        )
    
    def chunk_page(self, page: DocumentPage) -> List[TextChunk]:
        """Split a document page into overlapping text chunks.
        
        Args:
            page: DocumentPage to split into chunks
            
        Returns:
            List of TextChunk objects
        """
        text = page.text
        chunks: List[TextChunk] = []
        
        if len(text) < 100:
            logger.debug(
                f"Skipping page {page.page_number} from {page.source_file}: "
                f"text too short ({len(text)} characters)"
            )
            return chunks
        
        # Remove .pdf extension from source_file for chunk_id
        source_name = Path(page.source_file).stem
        
        chunk_index = 0
        start = 0
        
        while start < len(text):
            # Determine end position for this chunk
            end = start + self.chunk_size
            
            # Extract chunk text
            chunk_text = text[start:end]
            
            # Only create chunk if it meets minimum size requirement
            if len(chunk_text) >= 100:
                chunk_id = f"{source_name}_page{page.page_number}_chunk{chunk_index}"
                
                chunk = TextChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    char_count=len(chunk_text),
                    source_file=page.source_file
                )
                chunks.append(chunk)
                
                logger.debug(
                    f"Created chunk {chunk_id}: {len(chunk_text)} characters"
                )
                
                chunk_index += 1
            
            # Move start position for next chunk with overlap
            # If this was the last chunk (end >= len(text)), we're done
            if end >= len(text):
                break
            
            # Calculate next start position with overlap
            start = end - self.chunk_overlap
        
        logger.debug(
            f"Page {page.page_number} from {page.source_file}: "
            f"created {len(chunks)} chunks"
        )
        
        return chunks
    
    def chunk_documents(self, pages: List[DocumentPage]) -> List[TextChunk]:
        """Split multiple document pages into chunks.
        
        Args:
            pages: List of DocumentPage objects to chunk
            
        Returns:
            Flat list of all TextChunk objects from all pages
        """
        logger.info(f"Chunking {len(pages)} pages")
        
        all_chunks: List[TextChunk] = []
        
        for page in pages:
            page_chunks = self.chunk_page(page)
            all_chunks.extend(page_chunks)
        
        logger.info(
            f"Completed chunking: {len(all_chunks)} total chunks "
            f"from {len(pages)} pages"
        )
        
        return all_chunks
    
    def get_stats(self, chunks: List[TextChunk]) -> dict:
        """Calculate statistics for a list of chunks.
        
        Args:
            chunks: List of TextChunk objects
            
        Returns:
            Dictionary containing chunk statistics
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
                "total_characters": 0
            }
        
        chunk_sizes = [chunk.char_count for chunk in chunks]
        total_characters = sum(chunk_sizes)
        
        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": total_characters // len(chunks),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "total_characters": total_characters
        }
