"""EPUB generation tool using ebooklib."""

import html
import re
import logging
from pathlib import Path
from typing import List
from ebooklib import epub
from langchain_core.tools import tool

from ..models import ChapterDoc, BookMetadata, ParaPair
from ..config import get_project_paths

logger = logging.getLogger(__name__)


def filter_empty_paragraphs(pairs: List[ParaPair]) -> List[ParaPair]:
    """Filter out empty or invalid paragraphs."""
    valid_pairs = []
    for pair in pairs:
        if pair.modern and pair.modern.strip():
            # Check for meaningful content (not just whitespace or placeholders)
            if len(pair.modern.strip()) > 10 and not pair.modern.strip().startswith('['):
                valid_pairs.append(pair)
            else:
                logger.warning(f"Skipping paragraph {pair.i}: content too short or placeholder")
        else:
            logger.warning(f"Skipping paragraph {pair.i}: empty content")
    
    return valid_pairs


def escape_html(text: str) -> str:
    """Escape HTML entities and convert emphasis markers."""
    # First escape HTML entities
    escaped = html.escape(text)
    
    # Convert _text_ to <em>text</em>
    emphasis_pattern = r'_(.+?)_'
    emphasized = re.sub(emphasis_pattern, r'<em>\1</em>', escaped)
    
    return emphasized


def build_epub(slug: str, chapters: List[ChapterDoc], metadata: BookMetadata) -> Path:
    """Build EPUB3 file from modernized chapters."""
    from ..config import ensure_directories
    ensure_directories(slug)
    paths = get_project_paths(slug)
    
    # Create EPUB book
    book = epub.EpubBook()
    
    # Set metadata
    book.set_identifier(f"lily-books-{slug}")
    book.set_title(metadata.title)
    book.set_language(metadata.language)
    book.add_author(metadata.author)
    
    # Create CSS first
    style = """
    body {
        font-family: Georgia, serif;
        line-height: 1.6;
        margin: 2em;
        background-color: #fefefe;
        color: #333;
    }
    h1 {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5em;
        margin-bottom: 1em;
    }
    p {
        margin-bottom: 1em;
        text-align: justify;
    }
    em {
        font-style: italic;
        color: #7f8c8d;
    }
    """
    nav_css = epub.EpubItem(
        uid="nav_css",
        file_name="style/nav.css",
        media_type="text/css",
        content=style
    )
    book.add_item(nav_css)
    
    # Add cover page
    cover_html = f"""
    <html>
    <head>
        <title>{metadata.title}</title>
    </head>
    <body>
        <h1>{metadata.title}</h1>
        <h2>by {metadata.author}</h2>
        <p><em>Modernized Student Edition</em></p>
        <p>Source: {metadata.public_domain_source}</p>
    </body>
    </html>
    """
    cover_page = epub.EpubHtml(
        title="Cover",
        file_name="cover.xhtml",
        lang=metadata.language
    )
    cover_page.content = cover_html
    book.add_item(cover_page)
    
    # Create spine and toc
    spine = ["cover"]
    toc = []
    
    # Process each chapter
    for chapter_doc in chapters:
        if not chapter_doc.pairs:
            logger.warning(f"Skipping empty chapter: {chapter_doc.title}")
            continue
        
        # Filter out empty paragraphs
        valid_pairs = filter_empty_paragraphs(chapter_doc.pairs)
        if not valid_pairs:
            logger.warning(f"Skipping chapter with no valid paragraphs: {chapter_doc.title}")
            continue
            
        # Create chapter HTML
        chapter_html = f"""
        <html>
        <head>
            <title>{chapter_doc.title}</title>
        </head>
        <body>
            <h1>{chapter_doc.title}</h1>
        """
        
        # Add each paragraph
        for pair in valid_pairs:
            modern_text = escape_html(pair.modern)
            chapter_html += f"<p>{modern_text}</p>\n"
        
        chapter_html += "</body></html>"
        
        # Create EpubHtml object
        chapter_file = epub.EpubHtml(
            title=chapter_doc.title,
            file_name=f"chapter_{chapter_doc.chapter:02d}.xhtml",
            lang=metadata.language
        )
        chapter_file.content = chapter_html
        chapter_file.add_item(nav_css)  # Link CSS to chapter
        
        # Add to book
        book.add_item(chapter_file)
        spine.append(chapter_file)
        
        # Add to TOC
        toc.append(chapter_file)
    
    # Set spine
    book.spine = spine
    
    # Create NCX (table of contents)
    book.toc = toc
    
    # Add navigation
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Write EPUB file
    output_path = paths["deliverables_ebook"] / f"{slug}.epub"
    epub.write_epub(str(output_path), book, {})
    
    return output_path


@tool
def epub_builder_tool(slug: str, chapters_json: str, metadata_json: str) -> str:
    """Build EPUB from modernized chapters.
    
    Args:
        slug: Project slug identifier
        chapters_json: JSON string of ChapterDoc list
        metadata_json: JSON string of BookMetadata
    
    Returns:
        Path to generated EPUB file
    """
    import json
    
    # Parse inputs
    chapters_data = json.loads(chapters_json)
    metadata_data = json.loads(metadata_json)
    
    # Convert to Pydantic models
    chapters = [ChapterDoc(**ch) for ch in chapters_data]
    metadata = BookMetadata(**metadata_data)
    
    # Build EPUB
    output_path = build_epub(slug, chapters, metadata)
    
    return str(output_path)
