"""EPUB generation tool using ebooklib."""

import html
import re
import logging
from pathlib import Path
from typing import List
from ebooklib import epub
from langchain_core.tools import tool

from ..models import ChapterDoc, BookMetadata, ParaPair, PublishingMetadata
from ..config import get_project_paths

logger = logging.getLogger(__name__)


def filter_empty_paragraphs(pairs: List[ParaPair]) -> List[ParaPair]:
    """Filter out empty or invalid paragraphs."""
    valid_pairs = []
    for pair in pairs:
        if pair.modern and pair.modern.strip():
            # Check for meaningful content (not just whitespace or placeholders)
            modern_text = pair.modern.strip()
            
            # Skip validation failures
            if '[Validation failed' in modern_text:
                logger.warning(f"Skipping paragraph {pair.i}: validation failure")
                continue
                
            # Skip empty or very short content (but allow short meaningful text)
            if len(modern_text) < 3:
                logger.warning(f"Skipping paragraph {pair.i}: content too short")
                continue
                
            # Skip placeholder patterns
            if modern_text.startswith('[') and modern_text.endswith(']'):
                logger.warning(f"Skipping paragraph {pair.i}: placeholder pattern")
                continue
                
            valid_pairs.append(pair)
        else:
            logger.warning(f"Skipping paragraph {pair.i}: empty content")
    
    return valid_pairs


def escape_html(text: str) -> str:
    """Escape HTML entities but preserve emphasis tags already converted by writer.

    The writer chain already converts _italics_ to <em>italics</em>, so we need to:
    1. Protect existing <em> and </em> tags
    2. Escape dangerous HTML
    3. Restore the protected emphasis tags
    """
    # Protect existing <em> and </em> tags by replacing with placeholders
    text = text.replace('<em>', '___EMPHASIS_OPEN___')
    text = text.replace('</em>', '___EMPHASIS_CLOSE___')

    # Now escape HTML entities (will not affect our placeholders)
    escaped = html.escape(text)

    # Restore the emphasis tags
    escaped = escaped.replace('___EMPHASIS_OPEN___', '<em>')
    escaped = escaped.replace('___EMPHASIS_CLOSE___', '</em>')

    # Also convert any remaining _text_ patterns (fallback for un-modernized text)
    emphasis_pattern = r'_(.+?)_'
    escaped = re.sub(emphasis_pattern, r'<em>\1</em>', escaped)

    return escaped


def create_copyright_page(metadata: PublishingMetadata) -> str:
    """Generate copyright page HTML."""
    year = metadata.publication_year
    
    html = f"""
    <html>
    <head>
        <title>Copyright</title>
    </head>
    <body>
        <h2>Copyright</h2>
        
        <p><strong>{metadata.title}</strong></p>
        <p>Modernized Edition</p>
        
        <p>{metadata.copyright_notice.format(year=year, publisher=metadata.publisher)}</p>
        
        <p>Original work by {metadata.original_author}</p>
        
        <p><strong>ISBN (ebook):</strong> {metadata.isbn_ebook or 'Not assigned'}</p>
        
        <h3>About This Edition</h3>
        <p>{metadata.modernization_disclaimer}</p>
        
        <p><strong>Publisher:</strong> {metadata.publisher}</p>
        {f'<p><strong>Website:</strong> {metadata.publisher_url}</p>' if metadata.publisher_url else ''}
        
        <p><strong>Published:</strong> {year}</p>
        
        <p style="margin-top: 2em; font-size: 0.9em; color: #666;">
        {metadata.license}
        </p>
    </body>
    </html>
    """
    return html


def create_about_page(metadata: PublishingMetadata) -> str:
    """Generate 'About This Edition' page."""
    html = f"""
    <html>
    <head>
        <title>About This Edition</title>
    </head>
    <body>
        <h2>About This Modernized Edition</h2>
        
        <p>{metadata.long_description}</p>
        
        <h3>What's Different?</h3>
        <p>This edition updates archaic language and phrasing to make the text more accessible to contemporary readers, including:</p>
        <ul>
            <li>Simplified vocabulary where original terms are no longer in common use</li>
            <li>Updated sentence structures for modern readability</li>
            <li>Clarified pronouns and references</li>
            <li>Preserved original dialogue and character voices</li>
        </ul>
        
        <h3>What's Preserved?</h3>
        <p>We maintain complete fidelity to:</p>
        <ul>
            <li>The original plot and story structure</li>
            <li>Character names, relationships, and development</li>
            <li>Historical and cultural context</li>
            <li>The author's literary style and tone</li>
            <li>All original dialogue and quoted material</li>
        </ul>
        
        <p><em>This edition is ideal for students, educators, and readers who want to experience classic literature in a more accessible format.</em></p>
    </body>
    </html>
    """
    return html


def create_back_matter(metadata: PublishingMetadata, slug: str) -> str:
    """Generate back matter (other titles, call-to-action)."""
    html = f"""
    <html>
    <head>
        <title>More from {metadata.publisher}</title>
    </head>
    <body>
        <h2>Enjoy This Book?</h2>
        
        <p>If you found this modernized edition helpful, please consider:</p>
        <ul>
            <li><strong>Leaving a review</strong> to help other readers discover it</li>
            <li><strong>Sharing it</strong> with students, teachers, and book lovers</li>
            <li><strong>Exploring our other titles</strong> in the Modernized Classics series</li>
        </ul>
        
        <h3>About {metadata.publisher}</h3>
        <p>{metadata.publisher_tagline}</p>
        <p>We're dedicated to making classic literature accessible to modern readers through careful, thoughtful modernization that preserves the beauty and meaning of the original works.</p>
        
        {f'<p><strong>Series:</strong> {metadata.series_name}' if metadata.series_name else ''}
        {f'<p><strong>Volume:</strong> {metadata.series_number}' if metadata.series_number else ''}
        
        {f'<p>Visit us at: {metadata.publisher_url}</p>' if metadata.publisher_url else ''}
        
        <h3>Coming Soon</h3>
        <p><em>More modernized classics for students and lifelong learners.</em></p>
        
        <p style="margin-top: 3em; text-align: center; font-size: 0.9em; color: #666;">
        Thank you for reading!
        </p>
    </body>
    </html>
    """
    return html


def build_epub(
    slug: str, 
    chapters: List[ChapterDoc], 
    metadata: BookMetadata,
    publishing_metadata: PublishingMetadata = None,
    cover_path: Path = None
) -> Path:
    """Build EPUB3 file from modernized chapters.
    
    Args:
        slug: Project slug
        chapters: List of modernized chapters
        metadata: Basic book metadata
        publishing_metadata: Extended publishing metadata (optional)
        cover_path: Path to cover image (optional)
    """
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
    
    # Add cover image if provided
    if cover_path and cover_path.exists():
        with open(cover_path, 'rb') as f:
            cover_image = epub.EpubItem(
                uid="cover_image",
                file_name="images/cover.png",
                media_type="image/png",
                content=f.read()
            )
            book.add_item(cover_image)
            # Don't use set_cover() as it creates duplicate files
    
    # Create comprehensive CSS styling
    style = """
    body {
        font-family: Georgia, "Times New Roman", serif;
        line-height: 1.6;
        margin: 2em;
        background-color: #fefefe;
        color: #333;
        font-size: 1.1em;
    }
    
    h1 {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5em;
        margin-bottom: 1em;
        font-size: 1.8em;
        font-weight: bold;
        text-align: center;
    }
    
    h2 {
        color: #34495e;
        margin-top: 2em;
        margin-bottom: 1em;
        font-size: 1.4em;
        font-weight: bold;
    }
    
    h3 {
        color: #34495e;
        margin-top: 1.5em;
        margin-bottom: 0.8em;
        font-size: 1.2em;
        font-weight: bold;
    }
    
    p {
        margin-bottom: 1em;
        text-align: justify;
        text-indent: 1.5em;
    }
    
    /* Don't indent first paragraph after headings */
    h1 + p, h2 + p, h3 + p {
        text-indent: 0;
    }
    
    em {
        font-style: italic;
        color: #7f8c8d;
        font-weight: normal;
    }
    
    strong {
        font-weight: bold;
        color: #2c3e50;
    }
    
    blockquote {
        margin: 1.5em 2em;
        padding: 1em;
        background-color: #f8f9fa;
        border-left: 4px solid #3498db;
        font-style: italic;
        text-indent: 0;
    }
    
    /* Dialogue styling */
    p:has(> em:first-child) {
        text-indent: 0;
        margin-left: 2em;
    }
    
    /* Chapter titles */
    .chapter-title {
        text-align: center;
        font-size: 1.6em;
        margin: 2em 0 1em 0;
        color: #2c3e50;
        font-weight: bold;
    }
    
    /* Copyright and about pages */
    .copyright-page {
        text-align: center;
        margin: 3em 0;
    }
    
    .copyright-page h1 {
        border: none;
        margin-bottom: 2em;
    }
    
    .copyright-page p {
        text-align: center;
        text-indent: 0;
        margin: 1em 0;
    }
    
    /* Back matter */
    .back-matter {
        margin-top: 3em;
    }
    
    .back-matter h3 {
        color: #3498db;
        border-bottom: 1px solid #bdc3c7;
        padding-bottom: 0.3em;
    }
    
    .back-matter ul {
        margin: 1em 0;
        padding-left: 2em;
    }
    
    .back-matter li {
        margin: 0.5em 0;
        text-indent: 0;
    }
    
    /* Responsive design */
    @media (max-width: 600px) {
        body {
            margin: 1em;
            font-size: 1em;
        }
        
        h1 {
            font-size: 1.5em;
        }
        
        h2 {
            font-size: 1.3em;
        }
        
        blockquote {
            margin: 1em 1em;
        }
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
        <link href="style/nav.css" rel="stylesheet" type="text/css"/>
    </head>
    <body class="copyright-page">
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
    
    # Add copyright page
    if publishing_metadata:
        copyright_html = create_copyright_page(publishing_metadata)
        copyright_page = epub.EpubHtml(
            title="Copyright",
            file_name="copyright.xhtml",
            lang=metadata.language
        )
        copyright_page.content = copyright_html
        copyright_page.add_item(nav_css)
        book.add_item(copyright_page)
        spine.append(copyright_page)
        
        # Add "About This Edition" page
        about_html = create_about_page(publishing_metadata)
        about_page = epub.EpubHtml(
            title="About This Edition",
            file_name="about.xhtml",
            lang=metadata.language
        )
        about_page.content = about_html
        about_page.add_item(nav_css)
        book.add_item(about_page)
        spine.append(about_page)
        toc.append(about_page)  # Include in TOC
    
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
            <link href="style/nav.css" rel="stylesheet" type="text/css"/>
        </head>
        <body>
            <h1 class="chapter-title">{chapter_doc.title}</h1>
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
    
    # Add back matter
    if publishing_metadata:
        back_html = create_back_matter(publishing_metadata, slug)
        back_page = epub.EpubHtml(
            title=f"More from {publishing_metadata.publisher}",
            file_name="back_matter.xhtml",
            lang=metadata.language
        )
        back_page.content = back_html
        back_page.add_item(nav_css)
        book.add_item(back_page)
        spine.append(back_page)
        toc.append(back_page)
    
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
