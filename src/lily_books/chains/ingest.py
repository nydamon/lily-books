"""Ingestion chains for loading and chapterizing books."""

import re
import json
import requests
from typing import List
from langchain_core.runnables import RunnableLambda

from ..models import ChapterSplit


def load_gutendex(book_id: int) -> str:
    """Load raw text from Gutendex API."""
    # Test mode for demo purposes
    if book_id == 9999:
        return """CHAPTER 1

It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.

However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters.

"My dear Mr. Bennet," said his lady to him one day, "have you heard that Netherfield Park is let at last?"

Mr. Bennet replied that he had not.

"But it is," returned she; "for Mrs. Long has just been here, and she told me all about it."

Mr. Bennet made no answer.

"Do you not want to know who has taken it?" cried his wife impatiently.

"You want to tell me, and I have no objection to hearing it."

This was invitation enough.

CHAPTER 2

Mr. Bennet was among the earliest of those who waited on Mr. Bingley.

He had always intended to visit him, though to the last always assuring his wife that he should not go; and till the evening after the visit was paid she had no knowledge of it.

It was then disclosed in the following manner. Observing his second daughter employed in trimming a hat, he suddenly addressed her with:

"I hope Mr. Bingley will like it, Lizzy."

"We are not in a way to know what Mr. Bingley likes," said her mother resentfully, "since we are not to visit."

"But you forget, mamma," said Elizabeth, "that we shall meet him at the assemblies, and that Mrs. Long has promised to introduce him."

"I do not believe Mrs. Long will do any such thing. She has two nieces of her own. She is a selfish, hypocritical woman, and I have no opinion of her."

"No more have I," said Mr. Bennet; "and I am glad to find that you do not depend on her serving you."

Mrs. Bennet deigned not to make any reply, but, unable to contain herself, began scolding one of her daughters."""
    
    try:
        response = requests.get(f"https://gutendex.com/books/{book_id}/", timeout=10)
        response.raise_for_status()
        
        # Check if response is HTML (API error)
        if response.headers.get('content-type', '').startswith('text/html'):
            raise ValueError(f"Gutendex API returned HTML instead of JSON for book {book_id}")
        
        md = response.json()
        
        # Find the plain text URL
        text_url = None
        for format_key, format_data in md["formats"].items():
            if "text/plain" in format_key and "charset=utf-8" in format_key:
                text_url = format_data["url"]
                break
        
        if not text_url:
            raise ValueError(f"No plain text format found for book {book_id}")
        
        text_response = requests.get(text_url, timeout=30)
        text_response.raise_for_status()
        return text_response.text
        
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch book {book_id} from Gutendex: {str(e)}")
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"Unexpected error loading book {book_id}: {str(e)}")


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

