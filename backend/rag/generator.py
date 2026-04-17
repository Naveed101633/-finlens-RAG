"""Answer generation for FinLens RAG system using Gemini."""

import logging
import time
from dataclasses import dataclass
from typing import List

#import google.generativeai as genai
from google import genai
from rag.retriever import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class GeneratedAnswer:
    """Represents a generated answer with citations."""
    
    answer: str
    citations: List[dict]
    query: str
    model_used: str


class Generator:
    """Generates answers using Gemini LLM based on retrieved context."""

    RETRYABLE_ERROR_MARKERS = (
        "503",
        "unavailable",
        "resource exhausted",
        "429",
        "deadline exceeded",
        "timeout",
    )

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        """Normalize model names from env/config to Gemini API expected format."""
        raw = (model or "").strip()
        cleaned = raw.lstrip("=").strip()

        if cleaned.startswith("models/"):
            cleaned = cleaned[len("models/") :]

        return cleaned or "gemini-2.5-flash"

    @classmethod
    def _is_retryable_error(cls, error: Exception) -> bool:
        message = str(error).lower()
        return any(marker in message for marker in cls.RETRYABLE_ERROR_MARKERS)

    def _generate_with_model(self, model_name: str, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", fallback_model: str = "gemini-3.1-flash-lite-preview"):
        """Initialize the generator with Gemini API.
        
        Args:
            api_key: Google API key for Gemini
            model: Name of the Gemini model to use
            fallback_model: Backup model to use when the primary model is overloaded
        """
        self.model_name = self._normalize_model_name(model)
        self.fallback_model_name = self._normalize_model_name(fallback_model)
        
        if self.model_name != (model or ""):
            logger.warning("Normalized Gemini model name from '%s' to '%s'", model, self.model_name)
        if self.fallback_model_name != (fallback_model or ""):
            logger.warning(
                "Normalized Gemini fallback model name from '%s' to '%s'",
                fallback_model,
                self.fallback_model_name,
            )

        logger.info(
            "Configuring Gemini API with model: %s (fallback: %s)",
            self.model_name,
            self.fallback_model_name,
        )
        self.client = genai.Client(api_key=api_key)
        logger.info("Generator initialized successfully")
    
    def generate(
        self,
        query: str,
        search_results: List[SearchResult]
    ) -> GeneratedAnswer:
        """Generate an answer based on query and retrieved context.
        
        Args:
            query: User's question
            search_results: List of SearchResult objects from retrieval
            
        Returns:
            GeneratedAnswer with answer text, citations, and metadata
        """
        if not search_results:
            return GeneratedAnswer(
                answer="No documents are currently indexed. Please upload a financial report first.",
                citations=[],
                query=query,
                model_used=self.model_name
            )
        
        logger.info(f"Generating answer for query: '{query}'")
        
        # Build context from search results
        context_parts = []
        for result in search_results:
            context_part = f"[Source: {result.source_file}, Page {result.page_number}]\n{result.text}\n---"
            context_parts.append(context_part)
        
        context = "\n".join(context_parts)
        
        # Build prompt with strict instructions
        prompt = f"""You are a financial document analysis assistant. Answer the user's question based ONLY on the provided context from financial documents.

INSTRUCTIONS:
1. Answer ONLY using information from the provided context below
2. Cite your sources inline using the format: (Source: filename, Page X)
3. If the answer cannot be found in the provided context, respond with "The information is not found in the provided documents."
4. Be precise and factual
5. Do not add information from outside the provided context

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:"""

        try:
            answer = ""
            used_model_name = self.model_name
            model_attempts = [self.model_name]
            if self.fallback_model_name and self.fallback_model_name not in model_attempts:
                model_attempts.append(self.fallback_model_name)

            last_error: Exception | None = None
            for attempt_index, model_name in enumerate(model_attempts, start=1):
                for retry_index in range(3):
                    try:
                        answer = self._generate_with_model(model_name, prompt)
                        used_model_name = model_name
                        logger.info(
                            "Generated answer of length %s characters using %s",
                            len(answer),
                            model_name,
                        )
                        break
                    except Exception as exc:
                        last_error = exc
                        if not self._is_retryable_error(exc) or retry_index == 2:
                            logger.warning(
                                "Gemini attempt failed for model %s (attempt %s, retry %s): %s",
                                model_name,
                                attempt_index,
                                retry_index + 1,
                                exc,
                            )
                            break

                        backoff_seconds = 2 ** retry_index
                        logger.warning(
                            "Transient Gemini error for model %s, retrying in %s seconds: %s",
                            model_name,
                            backoff_seconds,
                            exc,
                        )
                        time.sleep(backoff_seconds)

                if answer:
                    break

            if not answer and last_error is not None:
                raise last_error

        except Exception as e:
            logger.error(f"Error generating answer with Gemini: {e}")
            used_model_name = self.fallback_model_name or self.model_name
            answer = (
                "The answer service is temporarily busy. "
                "Please try again in a moment."
            )
        
        # Extract top 3 citations by score
        top_results = sorted(search_results, key=lambda x: x.score, reverse=True)[:3]
        citations = [
            {
                "page_number": result.page_number,
                "source_file": result.source_file,
                "chunk_id": result.chunk_id,
                "score": result.score
            }
            for result in top_results
        ]
        
        # Create GeneratedAnswer object
        generated_answer = GeneratedAnswer(
            answer=answer,
            citations=citations,
            query=query,
            model_used=used_model_name,
        )
        
        return generated_answer
