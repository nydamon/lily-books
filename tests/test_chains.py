"""Tests for LangChain chains."""

import pytest
from unittest.mock import patch, MagicMock
from src.lily_books.chains.ingest import chapterize, load_gutendex
from src.lily_books.chains.writer import detect_type, rewrite_chapter
from src.lily_books.chains.checker import local_checks, qa_chapter
from tests.fixtures.sample_chapter import get_sample_chapter_split, get_sample_chapter_doc, get_sample_text


def test_detect_type():
    """Test paragraph type detection."""
    assert detect_type('"Hello," said he.') == "dialogue"
    assert detect_type("[Illustration]") == "illustration"
    assert detect_type("Dear Sir, I remain yours faithfully.") == "letter"
    assert detect_type("It was a dark and stormy night.") == "narrative"


def test_chapterize():
    """Test chapterization function."""
    text = get_sample_text()
    chapters = chapterize(text)
    
    assert len(chapters) == 2
    assert chapters[0].chapter == 1
    assert chapters[0].title == "Chapter 1"
    assert chapters[1].chapter == 2
    assert chapters[1].title == "Chapter 2"
    
    # Check that paragraphs are properly split
    assert len(chapters[0].paragraphs) >= 3
    assert "It is a truth universally acknowledged" in chapters[0].paragraphs[0]


def test_local_checks():
    """Test local validation checks."""
    orig = '"Hello," said he. "How are you?"'
    modern = '"Hello," he said. "How are you?"'
    
    result = local_checks(orig, modern)
    
    assert result["quote_parity"] is True
    assert result["emphasis_parity"] is True
    assert len(result["missed_archaic"]) == 0
    assert result["ratio"] > 0


def test_local_checks_quote_mismatch():
    """Test local checks with quote mismatch."""
    orig = '"Hello," said he. "How are you?"'
    modern = 'Hello, he said. How are you?'  # Missing quotes
    
    result = local_checks(orig, modern)
    
    assert result["quote_parity"] is False


def test_local_checks_emphasis_mismatch():
    """Test local checks with emphasis mismatch."""
    orig = "It was _very_ important."
    modern = "It was very important."  # Missing emphasis
    
    result = local_checks(orig, modern)
    
    assert result["emphasis_parity"] is False


@patch('src.lily_books.chains.ingest.requests.get')
def test_load_gutendex(mock_get):
    """Test Gutendex loading with mocked response."""
    # Mock the metadata response
    mock_metadata = MagicMock()
    mock_metadata.json.return_value = {
        "formats": {
            "text/plain; charset=utf-8": {"url": "http://example.com/text.txt"}
        }
    }
    
    # Mock the text response
    mock_text = MagicMock()
    mock_text.text = "Sample book text content"
    mock_text.raise_for_status.return_value = None
    
    mock_get.side_effect = [mock_metadata, mock_text]
    
    result = load_gutendex(123)
    
    assert result == "Sample book text content"
    assert mock_get.call_count == 2


@patch('src.lily_books.chains.writer.ChatOpenAI')
def test_rewrite_chapter(mock_chat_openai):
    """Test chapter rewriting with mocked LLM."""
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = [
        {"modern": "Modernized paragraph 1"},
        {"modern": "Modernized paragraph 2"}
    ]
    mock_chat_openai.return_value = mock_llm
    
    chapter_split = get_sample_chapter_split()
    chapter_split.paragraphs = [
        "Original paragraph 1",
        "Original paragraph 2"
    ]
    
    result = rewrite_chapter(chapter_split)
    
    assert isinstance(result, type(chapter_split).__bases__[0])  # ChapterDoc
    assert len(result.pairs) == 2
    assert result.pairs[0].orig == "Original paragraph 1"
    assert result.pairs[0].modern == "Modernized paragraph 1"


@patch('src.lily_books.chains.checker.ChatAnthropic')
def test_qa_chapter(mock_chat_anthropic):
    """Test chapter QA with mocked LLM."""
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = {
        "fidelity_score": 95,
        "readability_appropriate": True,
        "formatting_preserved": True,
        "tone_consistent": True,
        "quote_count_match": True,
        "emphasis_preserved": True,
        "issues": []
    }
    mock_chat_anthropic.return_value = mock_llm
    
    chapter_doc = get_sample_chapter_doc()
    
    passed, issues, updated_doc = qa_chapter(chapter_doc)
    
    assert isinstance(passed, bool)
    assert isinstance(issues, list)
    assert isinstance(updated_doc, type(chapter_doc))
    assert len(updated_doc.pairs) == len(chapter_doc.pairs)
    
    # Check that QA reports were added
    for pair in updated_doc.pairs:
        assert pair.qa is not None
        assert pair.qa.fidelity_score == 95


def test_qa_chapter_error_handling():
    """Test QA chapter error handling."""
    # Create a chapter doc with invalid data to trigger errors
    chapter_doc = get_sample_chapter_doc()
    chapter_doc.pairs[0].orig = ""  # Empty original text
    
    # This should not crash
    passed, issues, updated_doc = qa_chapter(chapter_doc)
    
    assert isinstance(passed, bool)
    assert isinstance(issues, list)
    assert isinstance(updated_doc, type(chapter_doc))

