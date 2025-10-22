"""LLM chain for generating publishing metadata."""

import logging
import json
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

from ..models import PublishingMetadata, ChapterDoc
from ..config import get_config
from ..observability import ChainTraceCallback
from ..tools.isbn_generator import generate_isbns_for_book
from ..utils.fail_fast import fail_fast_on_exception

logger = logging.getLogger(__name__)

# JSON output parser (more reliable than PydanticOutputParser)
metadata_parser = JsonOutputParser()

# Metadata generation prompt
METADATA_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert book marketer and publisher specializing in modernized classic literature.

Your task is to create compelling, SEO-optimized metadata for a modernized edition of a public domain classic.

Target audience:
- Students (grades 7-12)
- Teachers and educators
- General readers seeking accessible classics
- Audiobook listeners

The modernization preserves the original story, characters, and meaning while updating archaic language to contemporary English suitable for modern readers.

IMPORTANT: Return ONLY a valid JSON object with the following exact structure (no markdown, no wrapping):
{{
  "title": "string",
  "subtitle": "string or null",
  "author": "string",
  "original_author": "string",
  "publisher": "string",
  "publisher_url": "string or null",
  "publication_year": number,
  "isbn_ebook": "string or null",
  "isbn_audiobook": "string or null",
  "short_description": "string",
  "long_description": "string",
  "keywords": ["array", "of", "strings"],
  "categories": ["array", "of", "strings"],
  "copyright_notice": "string",
  "modernization_disclaimer": "string",
  "license": "string",
  "cover_style": "modern",
  "cover_prompt": "string"
}}

Generate professional, compelling metadata that will attract readers while accurately representing the modernized edition."""),
    ("user", """Generate publishing metadata for this book:

Original Title: {original_title}
Original Author: {original_author}
Public Domain Source: {source}
Publisher: {publisher}

Sample Content (first 2000 characters from Chapter 1):
{sample_text}

Total Chapters: {chapter_count}

IMPORTANT: Use your knowledge of "{original_title}" by {original_author} to inform the cover_prompt. The sample text provides context, but you should draw on the well-known historical setting, themes, and atmosphere of this classic work.

Requirements:
1. **Title**: Use the original title with "(Modernized Student Edition)" suffix
2. **Subtitle**: Optional descriptive subtitle (e.g., "A Modernized Student Edition")
3. **Short description**: 1-2 compelling sentences that hook the reader and explain the value
4. **Long description**: 200-300 words explaining:
   - What makes this modernized edition valuable
   - Why students and modern readers will appreciate it
   - What's preserved from the original
   - Specific benefits for teachers and students
5. **Keywords**: 8-12 relevant keywords for Amazon/retail search, including:
   - Book title and author
   - "modernized classic", "student edition"
   - Target audience terms
   - Educational/curriculum terms
6. **Categories**: 3-5 relevant book categories from major retailers
7. **Cover style**: Choose from "classic", "modern", "minimalist", "whimsical classic"
8. **Cover prompt**: CRITICAL - Create a detailed, book-specific visual description for AI cover generation that includes:
   - Historical time period and setting (e.g., "Regency-era England, 1810s", "Victorian London", "American South 1930s")
   - Key themes and symbols from the book (e.g., "social class, romance, pride", "justice, racism, childhood innocence")
   - Specific visual elements that represent the story (e.g., "grand estate, ballroom", "courtroom, oak tree", "lighthouse, sea")
   - Atmosphere and mood (e.g., "romantic, witty, elegant", "somber, reflective, hopeful")
   - Color palette suggestions based on the book's tone (e.g., "warm golds and greens for pastoral elegance", "muted grays and blues for melancholy")
   - NO generic descriptions - every element should be SPECIFIC to THIS book's content, characters, setting, and themes

   Example GOOD cover_prompt: "Regency-era English countryside estate, 1813. Elegant manor house with rolling green hills, representing themes of social class, romance, and personal growth. Atmosphere: witty, romantic, sophisticated. Color palette: warm golds, sage greens, ivory whites suggesting refinement and natural beauty. Symbolic elements: open book, quill pen, manor windows suggesting both constraint and possibility."

   Example BAD cover_prompt: "A classic book cover with elegant design" (too generic, no book-specific details)

Focus on educational value, accessibility, and preserving literary merit. Make it compelling and market-ready!""")
])

# Build chain with retry (lazy initialization)
def get_metadata_chain():
    """Get metadata generation chain with lazy initialization."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    config = get_config()
    logger.info(f"Creating metadata LLM with model: {config.openai_model}")
    # Use GPT-5-mini if configured
    # Use OpenRouter for all models
    llm = ChatOpenAI(
        model=config.openai_model,
        api_key=os.getenv('OPENROUTER_API_KEY'),
        base_url="https://openrouter.ai/api/v1",
        temperature=1.0,
        max_completion_tokens=2000
    ).with_retry(
        stop_after_attempt=config.llm_max_retries,
        wait_exponential_jitter=True
    )
    
    return (
        METADATA_PROMPT
        | llm
        | metadata_parser
    )


def generate_metadata(
    original_title: str,
    original_author: str,
    source: str,
    publisher: str,
    chapters: List[ChapterDoc],
    slug: str = None
) -> PublishingMetadata:
    """Generate publishing metadata using LLM.
    
    Args:
        original_title: Original book title
        original_author: Original author name
        source: Public domain source (e.g., "Project Gutenberg #1342")
        publisher: Publisher name
        chapters: List of chapter documents
        slug: Optional slug for callbacks
        
    Returns:
        PublishingMetadata object with generated content
    """
    # Extract sample text from first chapter - need substantial context for accurate cover prompts
    sample_text = ""
    if chapters and chapters[0].pairs:
        # Take first 15 paragraphs (up to 2000 chars) to give LLM enough context
        # to understand the book's time period, setting, themes, and characters
        sample_paragraphs = chapters[0].pairs[:15]
        sample_text = "\n\n".join([p.modern for p in sample_paragraphs])[:2000]
    
    # Prepare callbacks
    callbacks = []
    if slug:
        callbacks = [ChainTraceCallback(slug)]
    
    # Invoke chain
    try:
        # Get chain with lazy initialization
        chain = get_metadata_chain()

        raw_result = chain.invoke({
            "original_title": original_title,
            "original_author": original_author,
            "source": source,
            "publisher": publisher,
            "sample_text": sample_text,
            "chapter_count": len(chapters)
        }, config={"callbacks": callbacks})

        # Parse JSON result into PublishingMetadata
        # JsonOutputParser should return a dict, but handle edge cases
        if isinstance(raw_result, str):
            # If we got a string, the LLM may have returned raw JSON
            # Try to fix common JSON errors (semicolons instead of commas)
            try:
                raw_result = json.loads(raw_result)
            except json.JSONDecodeError:
                # Try to fix semicolon errors
                fixed_json = raw_result.replace(';"', ',"').replace(';\n', ',\n')
                raw_result = json.loads(fixed_json)

        if isinstance(raw_result, dict):
            # Check if wrapped in properties key
            if "properties" in raw_result and isinstance(raw_result["properties"], dict):
                metadata_dict = raw_result["properties"]
            else:
                metadata_dict = raw_result
        else:
            raise ValueError(f"Expected dict from metadata chain, got {type(raw_result)}")

        # Convert to PublishingMetadata object
        result = PublishingMetadata(**metadata_dict)

        # Generate ISBNs
        isbns = generate_isbns_for_book(slug or original_title.lower().replace(' ', '-'), original_title)
        result.isbn_ebook = isbns["ebook_isbn"]
        result.isbn_audiobook = isbns["audiobook_isbn"]

        logger.info(f"Generated metadata for {original_title}")
        return result
        
    except Exception as e:
        # Fail fast on any exception
        fail_fast_on_exception(e, f"metadata_generator")
        
        logger.error(f"Metadata generation failed: {e}")
        # Return minimal metadata as fallback
        return PublishingMetadata(
            title=f"{original_title} (Modernized Student Edition)",
            author=original_author,
            original_author=original_author,
            publisher=publisher,
            short_description=f"A modernized edition of {original_title} by {original_author}.",
            long_description=f"This modernized student edition of {original_title} updates archaic language for contemporary readers while preserving the original story and meaning.",
            keywords=["classic literature", "modernized", "student edition"],
            categories=["Literature & Fiction", "Classics"]
        )
