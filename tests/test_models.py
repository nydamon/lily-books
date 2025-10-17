"""Tests for Pydantic data models."""

import pytest
from src.lily_books.models import (
    QAIssue, QAReport, ParaPair, ChapterDoc, ChapterSplit, BookMetadata
)


def test_qa_issue():
    """Test QAIssue model."""
    issue = QAIssue(
        type="formatting",
        description="Missing quote",
        severity="medium"
    )
    
    assert issue.type == "formatting"
    assert issue.description == "Missing quote"
    assert issue.severity == "medium"
    assert issue.span_original is None
    assert issue.suggestion is None


def test_qa_report():
    """Test QAReport model."""
    report = QAReport(
        fidelity_score=95,
        readability_grade=8.5,
        character_count_ratio=1.2,
        modernization_complete=True,
        formatting_preserved=True,
        tone_consistent=True,
        quote_count_match=True,
        emphasis_preserved=True,
        retry_count=0
    )
    
    assert report.fidelity_score == 95
    assert report.readability_grade == 8.5
    assert report.character_count_ratio == 1.2
    assert report.modernization_complete is True
    assert len(report.issues) == 0


def test_para_pair():
    """Test ParaPair model."""
    pair = ParaPair(
        i=0,
        para_id="ch01_para000",
        orig="It is a truth universally acknowledged.",
        modern="It is a truth universally acknowledged."
    )
    
    assert pair.i == 0
    assert pair.para_id == "ch01_para000"
    assert pair.orig == "It is a truth universally acknowledged."
    assert pair.modern == "It is a truth universally acknowledged."
    assert pair.qa is None
    assert pair.notes is None


def test_chapter_split():
    """Test ChapterSplit model."""
    chapter = ChapterSplit(
        chapter=1,
        title="Chapter 1",
        paragraphs=[
            "It is a truth universally acknowledged.",
            "That a single man in possession of a good fortune."
        ]
    )
    
    assert chapter.chapter == 1
    assert chapter.title == "Chapter 1"
    assert len(chapter.paragraphs) == 2
    assert chapter.paragraphs[0] == "It is a truth universally acknowledged."


def test_chapter_doc():
    """Test ChapterDoc model."""
    pair1 = ParaPair(i=0, para_id="ch01_para000", orig="Original text", modern="Modern text")
    pair2 = ParaPair(i=1, para_id="ch01_para001", orig="More text", modern="More modern text")
    
    doc = ChapterDoc(
        chapter=1,
        title="Chapter 1",
        pairs=[pair1, pair2]
    )
    
    assert doc.chapter == 1
    assert doc.title == "Chapter 1"
    assert len(doc.pairs) == 2
    assert doc.pairs[0].para_id == "ch01_para000"


def test_book_metadata():
    """Test BookMetadata model."""
    metadata = BookMetadata(
        title="Pride and Prejudice (Modernized)",
        author="Jane Austen",
        public_domain_source="Project Gutenberg #1342"
    )
    
    assert metadata.title == "Pride and Prejudice (Modernized)"
    assert metadata.author == "Jane Austen"
    assert metadata.public_domain_source == "Project Gutenberg #1342"
    assert metadata.language == "en-US"
    assert metadata.voice["provider"] == "elevenlabs"
    assert metadata.acx["target_rms_db"] == -20


def test_model_serialization():
    """Test model serialization and deserialization."""
    issue = QAIssue(
        type="test",
        description="Test issue",
        severity="low"
    )
    
    # Test serialization
    data = issue.model_dump()
    assert data["type"] == "test"
    assert data["description"] == "Test issue"
    assert data["severity"] == "low"
    
    # Test deserialization
    restored = QAIssue(**data)
    assert restored.type == issue.type
    assert restored.description == issue.description
    assert restored.severity == issue.severity

