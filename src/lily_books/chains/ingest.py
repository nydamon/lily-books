"""Ingestion chains for loading and chapterizing books."""

import re
import json
import requests
from typing import List
from langchain_core.runnables import RunnableLambda

from ..models import ChapterSplit


def load_gutendex(book_id: int) -> str:
    """Load raw text from Gutendex API."""
    md = requests.get(f"https://gutendex.com/books/{book_id}/").json()
    
    # Find the plain text URL
    text_url = None
    for format_key, format_data in md["formats"].items():
        if "text/plain" in format_key and "charset=utf-8" in format_key:
            text_url = format_data["url"]
            break
    
    if not text_url:
        raise ValueError(f"No plain text format found for book {book_id}")
    
    response = requests.get(text_url)
    response.raise_for_status()
    return response.text


def chapterize(text: str) -> List[ChapterSplit]:
    """Split text into chapters using regex patterns."""
    # Try to split on CHAPTER patterns first
    parts = re.split(r"\n\s*CHAPTER\s+([0-9IVXLC]+)(?:[^\n]*)?\s*\n", text, flags=re.I)
    
    if len(parts) <= 1:
        # No chapters found, treat as single chapter
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return [ChapterSplit(chapter=1, title="Chapter 1", paragraphs=paragraphs)]
    
    chapters = []
    preamble = parts[0]
    
    # Process chapter pairs (title, content)
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            chapter_num = parts[i]
            chapter_content = parts[i + 1]
            
            paragraphs = [p.strip() for p in chapter_content.split("\n\n") if p.strip()]
            chapters.append(ChapterSplit(
                chapter=len(chapters) + 1,
                title=f"Chapter {chapter_num}",
                paragraphs=paragraphs
            ))
    
    # Add preamble as chapter 0 if it has content
    if preamble.strip():
        preamble_paras = [p for p in preamble.split("\n\n") if p.strip()]
        chapters.insert(0, ChapterSplit(
            chapter=0,
            title="Preamble",
            paragraphs=preamble_paras
        ))
    
    return chapters


# LCEL Runnables
IngestChain = RunnableLambda(lambda x: load_gutendex(x["book_id"]))
ChapterizeChain = RunnableLambda(lambda x: chapterize(x["raw_text"]))
