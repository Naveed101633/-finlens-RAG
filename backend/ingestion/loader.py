"""PDF document loader for FinLens RAG system."""

import logging
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class DocumentPage:
    """Represents a single page from a PDF document."""
    
    page_number: int
    text: str
    char_count: int
    source_file: str


class PDFLoader:
    """Loads and extracts text from PDF documents using PyMuPDF."""
    
    def __init__(self, file_path: str):
        """Initialize the PDF loader.
        
        Args:
            file_path: Path to the PDF file to load
        """
        self.file_path = Path(file_path)
        self._pages: list[DocumentPage] = []
        self._total_pages = 0
        self._skipped_pages = 0
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        logger.info(f"Initialized PDFLoader for: {self.file_path.name}")
    
    def load(self) -> list[DocumentPage]:
        """Load and extract text from all pages in the PDF.
        
        Returns:
            List of DocumentPage objects containing extracted text
        """
        logger.info(f"Loading PDF: {self.file_path}")
        
        self._pages = []
        self._skipped_pages = 0
        
        try:
            doc = fitz.open(self.file_path)
            self._total_pages = len(doc)
            
            logger.info(f"Processing {self._total_pages} pages from {self.file_path.name}")
            
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                text = page.get_text()
                
                # Strip whitespace
                text = text.strip()
                char_count = len(text)
                
                # Skip pages with less than 50 characters
                if char_count < 50:
                    self._skipped_pages += 1
                    logger.debug(f"Skipping page {page_idx + 1} (only {char_count} characters)")
                    continue
                
                page_number = page_idx + 1  # 1-based page numbering
                doc_page = DocumentPage(
                    page_number=page_number,
                    text=text,
                    char_count=char_count,
                    source_file=self.file_path.name
                )
                self._pages.append(doc_page)
                
                logger.debug(f"Loaded page {page_number}: {char_count} characters")
            
            doc.close()
            
            logger.info(
                f"Completed loading {self.file_path.name}: "
                f"{len(self._pages)} pages loaded, {self._skipped_pages} pages skipped"
            )
            
        except Exception as e:
            logger.error(f"Error loading PDF {self.file_path}: {e}")
            raise
        
        return self._pages
    
    def get_stats(self) -> dict:
        """Get statistics about the loaded PDF.
        
        Returns:
            Dictionary containing loading statistics
        """
        total_characters = sum(page.char_count for page in self._pages)
        
        return {
            "total_pages": self._total_pages,
            "loaded_pages": len(self._pages),
            "skipped_pages": self._skipped_pages,
            "total_characters": total_characters,
            "source_file": self.file_path.name
        }


def load_pdf(file_path: str) -> list[DocumentPage]:
    """Convenience function to load a PDF document.
    
    Args:
        file_path: Path to the PDF file to load
        
    Returns:
        List of DocumentPage objects containing extracted text
    """
    loader = PDFLoader(file_path)
    return loader.load()
