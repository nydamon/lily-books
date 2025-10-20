"""LLM chain for generating publishing metadata."""

import logging
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from ..models import PublishingMetadata, ChapterDoc
from ..config import get_config
from ..observability import ChainTraceCallback
from ..tools.isbn_generator import generate_isbns_for_book

logger = logging.getLogger(__name__)

# Pydantic output parser
metadata_parser = PydanticOutputParser(pydantic_object=PublishingMetadata)

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

{format_instructions}

Generate professional, compelling metadata that will attract readers while accurately representing the modernized edition."""),
    ("user", """Generate publishing metadata for this book:

Original Title: {original_title}
Original Author: {original_author}
Public Domain Source: {source}
Publisher: {publisher}

Sample Content (first 500 words):
{sample_text}

Total Chapters: {chapter_count}

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
8. **Cover prompt**: Detailed description for AI cover generation

Focus on educational value, accessibility, and preserving literary merit. Make it compelling and market-ready!""")
])

# Build chain with retry
config = get_config()
llm = ChatOpenAI(
    model=config.openai_model,
    temperature=1.0,  # GPT-5-mini only supports default temperature (1.0)
    max_completion_tokens=2000  # GPT-5-mini uses max_completion_tokens
).with_retry(
    stop_after_attempt=config.llm_max_retries,
    wait_exponential_jitter=True
)

metadata_chain = (
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
    # Extract sample text from first chapter
    sample_text = ""
    if chapters and chapters[0].pairs:
        sample_paragraphs = chapters[0].pairs[:5]  # First 5 paragraphs
        sample_text = "\n\n".join([p.modern for p in sample_paragraphs])[:500]
    
    # Prepare callbacks
    callbacks = []
    if slug:
        callbacks = [ChainTraceCallback(slug)]
    
    # Invoke chain
    try:
        result = metadata_chain.invoke({
            "original_title": original_title,
            "original_author": original_author,
            "source": source,
            "publisher": publisher,
            "sample_text": sample_text,
            "chapter_count": len(chapters),
            "format_instructions": metadata_parser.get_format_instructions()
        }, config={"callbacks": callbacks})
        
        # Generate ISBNs
        isbns = generate_isbns_for_book(slug or original_title.lower().replace(' ', '-'), original_title)
        result.isbn_ebook = isbns["ebook_isbn"]
        result.isbn_audiobook = isbns["audiobook_isbn"]
        
        logger.info(f"Generated metadata for {original_title}")
        return result
        
    except Exception as e:
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
