"""Test publishing features."""

import pytest
from pathlib import Path
from lily_books.chains.metadata_generator import generate_metadata
from lily_books.tools.cover_generator import generate_cover, generate_cover_template
from lily_books.models import PublishingMetadata, CoverDesign
from tests.fixtures.sample_chapter import get_sample_chapter_doc


def test_metadata_generation():
    """Test LLM metadata generation."""
    chapters = [get_sample_chapter_doc()]
    
    metadata = generate_metadata(
        original_title="Pride and Prejudice",
        original_author="Jane Austen",
        source="Project Gutenberg #1342",
        publisher="Test Publisher",
        chapters=chapters
    )
    
    assert metadata.title
    assert metadata.short_description
    assert len(metadata.long_description) > 100
    assert len(metadata.keywords) >= 5
    assert len(metadata.categories) >= 2


def test_cover_template_generation():
    """Test template-based cover generation."""
    metadata = PublishingMetadata(
        title="Test Book",
        author="Test Author",
        original_author="Test Author",
        short_description="A test book",
        long_description="A longer test description.",
        keywords=["test"],
        categories=["Fiction"]
    )
    
    # Use template (not AI)
    cover_design = generate_cover(
        metadata=metadata,
        slug="test-cover",
        use_ai=False
    )
    
    assert cover_design.image_path
    assert Path(cover_design.image_path).exists()


def test_publishing_metadata_model():
    """Test PublishingMetadata model validation."""
    metadata = PublishingMetadata(
        title="Test Book",
        author="Test Author",
        original_author="Test Author",
        short_description="A test book",
        long_description="A longer test description.",
        keywords=["test", "book"],
        categories=["Fiction", "Classics"]
    )
    
    assert metadata.title == "Test Book"
    assert metadata.author == "Test Author"
    assert metadata.publisher == "Modernized Classics Press"  # Default
    assert metadata.publication_year == 2025  # Default
    assert len(metadata.keywords) == 2
    assert len(metadata.categories) == 2


def test_cover_design_model():
    """Test CoverDesign model validation."""
    cover = CoverDesign(
        title="Test Book",
        author="Test Author",
        image_path="/path/to/cover.png"
    )
    
    assert cover.title == "Test Book"
    assert cover.author == "Test Author"
    assert cover.publisher == "Modernized Classics Press"  # Default
    assert cover.width == 1600  # Default
    assert cover.height == 2400  # Default
    assert cover.format == "png"  # Default
    assert cover.image_path == "/path/to/cover.png"


def test_cover_prompt_generation():
    """Test cover prompt generation."""
    from lily_books.tools.cover_generator import generate_cover_prompt
    
    metadata = PublishingMetadata(
        title="Alice's Adventures in Wonderland",
        author="Lewis Carroll",
        original_author="Lewis Carroll",
        short_description="A classic children's tale",
        long_description="Alice falls down a rabbit hole into a fantasy world.",
        keywords=["fantasy", "children", "adventure"],
        categories=["Children's Fiction", "Fantasy"]
    )
    
    prompt = generate_cover_prompt(metadata)
    
    assert "Alice's Adventures in Wonderland" in prompt
    assert "Lewis Carroll" in prompt
    assert "Modernized Student Edition" in prompt
    assert "fantasy" in prompt
    assert "children" in prompt
    assert "adventure" in prompt


def test_metadata_fallback():
    """Test metadata generation fallback when LLM fails."""
    # This test would require mocking the LLM to fail
    # For now, just test that the function handles empty chapters gracefully
    metadata = generate_metadata(
        original_title="Test Book",
        original_author="Test Author",
        source="Test Source",
        publisher="Test Publisher",
        chapters=[]  # Empty chapters
    )
    
    # Should return fallback metadata
    assert metadata.title
    assert metadata.short_description
    assert metadata.long_description
    assert len(metadata.keywords) > 0
    assert len(metadata.categories) > 0
