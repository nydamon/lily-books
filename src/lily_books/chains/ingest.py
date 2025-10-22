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


def strip_markdown_code_blocks(text: str) -> str:
    """Remove markdown code blocks from LLM output.

    Some LLMs wrap JSON in ```json ... ``` blocks which breaks parsing.
    This function strips those markers.
    """
    # Remove ```json at start and ``` at end
    cleaned = re.sub(r'^\s*```json\s*', '', text, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()


def clean_gutenberg_content(text: str) -> str:
    """
    Remove Project Gutenberg boilerplate and illustration placeholders.
    
    Args:
        text: Raw text content
    
    Returns:
        Cleaned text with Gutenberg content and illustrations removed
    """
    # Remove illustration placeholders
    illustration_patterns = [
        r'\[Illustration[^\]]*\]',  # [Illustration], [Illustration: description], etc.
        r'\[ILLUSTRATION[^\]]*\]',  # Uppercase variants
        r'\[Fig\.\s*\d+[^\]]*\]',   # Figure references
        r'\[Plate\s*\d+[^\]]*\]',   # Plate references
        r'\[Image[^\]]*\]',         # Generic image references
    ]
    
    cleaned_text = text
    removed_count = 0
    
    for pattern in illustration_patterns:
        matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
        if matches:
            removed_count += len(matches)
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} illustration placeholders")
    
    # Remove Project Gutenberg header (everything before "*** START OF")
    start_markers = [
        r'\*\*\* START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\*]*\*\*\*',
        r'\*\*\*START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\*]*\*\*\*',
    ]
    
    for marker in start_markers:
        match = re.search(marker, cleaned_text, re.IGNORECASE)
        if match:
            # Keep everything after the marker
            cleaned_text = cleaned_text[match.end():]
            logger.info("Removed Project Gutenberg header")
            break
    
    # Remove Project Gutenberg footer (everything after "*** END OF")
    end_markers = [
        r'\*\*\* END OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\*]*\*\*\*',
        r'\*\*\*END OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\*]*\*\*\*',
    ]
    
    for marker in end_markers:
        match = re.search(marker, cleaned_text, re.IGNORECASE)
        if match:
            # Keep everything before the marker
            cleaned_text = cleaned_text[:match.start()]
            logger.info("Removed Project Gutenberg footer")
            break
    
    # Clean up multiple blank lines
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    # Clean up leading/trailing whitespace
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text


def load_gutendex(book_id: int) -> str:
    """Load raw text from Gutendex API with basic sanity checks and retry logic."""
    import time
    max_retries = 3
    retry_delay = 5
    
    # Retry metadata fetch
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching book metadata (attempt {attempt}/{max_retries})...")
            response = requests.get(f"https://gutendex.com/books/{book_id}/", timeout=60)
            response.raise_for_status()
            md = response.json()
            break
        except Exception as e:
            if attempt == max_retries:
                raise ValueError(f"Failed to load book metadata for ID {book_id} after {max_retries} attempts: {str(e)}")
            logger.warning(f"Metadata fetch attempt {attempt} failed: {e}, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    
    # Find the plain text URL
    text_url = None
    for format_key, format_url in md["formats"].items():
        if "text/plain" in format_key:
            text_url = format_url
            break
    
    if not text_url:
        raise ValueError(f"No plain text format found for book {book_id}")
    
    # Retry text content fetch
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching book text content (attempt {attempt}/{max_retries})...")
            response = requests.get(text_url, timeout=90)
            response.raise_for_status()
            text = response.text
            break
        except Exception as e:
            if attempt == max_retries:
                raise ValueError(f"Failed to load text content for book {book_id} after {max_retries} attempts: {str(e)}")
            logger.warning(f"Text fetch attempt {attempt} failed: {e}, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    
    # Basic sanity checks
    if len(text) < 1000:
        logger.warning(f"Text content is very short ({len(text)} chars) for book {book_id}")
    
    if len(text) > 10_000_000:  # 10MB limit
        logger.warning(f"Text content is very long ({len(text)} chars) for book {book_id}")
    
    # Check for basic text quality
    if not any(char.isalpha() for char in text[:1000]):
        logger.warning(f"Text content appears to lack alphabetic characters for book {book_id}")
    
    # Clean Project Gutenberg content and illustration placeholders
    text = clean_gutenberg_content(text)
    
    logger.info(f"Loaded text for book {book_id}: {len(text)} chars")
    return text


def chapterize(text: str) -> List[ChapterSplit]:
    """Split text into chapters using regex patterns with LLM fallback."""
    # Normalize line endings (handle both \r\n and \n)
    text = text.replace('\r\n', '\n')

    # Try to split on CHAPTER patterns first
    # Pattern 1: "CHAPTER" followed by number/Roman numeral: "CHAPTER I", "CHAPTER 1", etc.
    parts = re.split(r"\n\s*CHAPTER\s+([0-9IVXLC]+)(?:[^\n]*)?\s*\n", text, flags=re.I)

    # Pattern 2: Standalone valid Roman numerals on their own line (for books like Great Gatsby)
    # Only match valid chapter Roman numerals I-XX (1-20), not random letter sequences
    if len(parts) <= 1:
        # Match valid Roman numerals: I, II, III, IV, V, VI, VII, VIII, IX, X, XI, XII, etc.
        # Requires blank line before and after to avoid matching mid-sentence
        parts = re.split(r"\n\s*\n\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX)\s*\n\s*\n", text)
    
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
            # Strip markdown code blocks before parsing
            cleaned_content = strip_markdown_code_blocks(response.content)
            chapters_data = json.loads(cleaned_content)
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
