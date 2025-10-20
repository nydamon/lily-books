"""Ingestion chains for loading and chapterizing books."""

import re
import json
import requests
import logging
from typing import List, Optional
from langchain_core.runnables import RunnableLambda

from ..models import ChapterSplit
from ..config import settings

logger = logging.getLogger(__name__)


def load_gutendex(book_id: int) -> str:
    """Load raw text from Gutendex API with basic sanity checks."""
    try:
        response = requests.get(f"https://gutendex.com/books/{book_id}/", timeout=30)
        response.raise_for_status()
        md = response.json()
    except Exception as e:
        raise ValueError(f"Failed to load book metadata for ID {book_id}: {str(e)}")
    
    # Find the plain text URL
    text_url = None
    for format_key, format_url in md["formats"].items():
        if "text/plain" in format_key:
            text_url = format_url
            break
    
    if not text_url:
        raise ValueError(f"No plain text format found for book {book_id}")
    
    try:
        response = requests.get(text_url, timeout=60)
        response.raise_for_status()
        text = response.text
        
        # Basic sanity checks
        if len(text) < 1000:
            logger.warning(f"Text content is very short ({len(text)} chars) for book {book_id}")
        
        if len(text) > 10_000_000:  # 10MB limit
            logger.warning(f"Text content is very long ({len(text)} chars) for book {book_id}")
        
        # Check for basic text quality
        if not any(char.isalpha() for char in text[:1000]):
            logger.warning(f"Text content appears to lack alphabetic characters for book {book_id}")
        
        logger.info(f"Loaded text for book {book_id}: {len(text)} chars")
        return text
        
    except Exception as e:
        raise ValueError(f"Failed to load text content for book {book_id}: {str(e)}")


def chapterize(text: str) -> List[ChapterSplit]:
    """Split text into chapters using regex patterns with LLM fallback."""
    # Try to split on CHAPTER patterns first
    parts = re.split(r"\n\s*CHAPTER\s+([0-9IVXLC]+)(?:[^\n]*)?\s*\n", text, flags=re.I)
    
    if len(parts) <= 1:
        # No chapters found, try LLM-based detection if enabled
        if settings.use_llm_for_structure:
            logger.info("No chapters found with regex, attempting LLM-based chapter detection")
            chapters = llm_detect_chapters(text)
            if chapters:
                return chapters
        
        # Fallback: treat as single chapter
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            logger.warning("No paragraphs found in text")
            return []
        
        logger.info(f"Treating as single chapter with {len(paragraphs)} paragraphs")
        return [ChapterSplit(chapter=1, title="Chapter 1", paragraphs=paragraphs)]
    
    chapters = []
    preamble = parts[0]
    
    # Process chapter pairs (title, content)
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            chapter_num = parts[i]
            chapter_content = parts[i + 1]
            
            paragraphs = [p.strip() for p in chapter_content.split("\n\n") if p.strip()]
            if not paragraphs:
                logger.warning(f"Chapter {chapter_num} has no paragraphs, skipping")
                continue
            
            chapters.append(ChapterSplit(
                chapter=len(chapters) + 1,
                title=f"Chapter {chapter_num}",
                paragraphs=paragraphs
            ))
    
    # Skip preamble - it's just Project Gutenberg metadata
    # Only include actual book chapters
    
    logger.info(f"Detected {len(chapters)} chapters using regex patterns")
    return chapters


def llm_detect_chapters(text: str) -> Optional[List[ChapterSplit]]:
    """Use LLM to intelligently detect chapter boundaries."""
    if not settings.use_llm_for_structure:
        return None
    
    try:
        from ..utils.llm_factory import create_llm_with_fallback
        
        # Create a simple LLM for chapter detection
        llm = create_llm_with_fallback(
            provider="openai",
            temperature=0.1,
            timeout=30,
            max_retries=2,
            cache_enabled=True
        )
        
        # Simple prompt for chapter detection
        prompt = f"""
        Analyze this literary text and identify chapter boundaries. Return a JSON list of chapter objects with:
        - chapter: number (starting from 1)
        - title: chapter title
        - start_text: first few words of the chapter
        - end_text: last few words of the chapter
        
        Text to analyze:
        {text[:5000]}...
        
        Return only valid JSON, no other text.
        """
        
        response = llm.invoke(prompt)
        
        # Try to parse the response
        import json
        try:
            chapters_data = json.loads(response.content)
            chapters = []
            
            for i, ch_data in enumerate(chapters_data):
                chapters.append(ChapterSplit(
                    chapter=i + 1,
                    title=ch_data.get("title", f"Chapter {i + 1}"),
                    paragraphs=[f"Chapter content starting with: {ch_data.get('start_text', '')}"]
                ))
            
            logger.info(f"LLM detected {len(chapters)} chapters")
            return chapters
            
        except json.JSONDecodeError:
            logger.warning("LLM chapter detection returned invalid JSON")
            return None
            
    except Exception as e:
        logger.warning(f"LLM chapter detection failed: {e}")
        return None


# LCEL Runnables
IngestChain = RunnableLambda(lambda x: load_gutendex(x["book_id"]))
ChapterizeChain = RunnableLambda(lambda x: chapterize(x["raw_text"]))
