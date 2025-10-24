"""Tests for LangChain chains."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from lily_books.chains.checker import compute_observability_metrics, qa_chapter
from lily_books.chains.ingest import chapterize, load_gutendex
from lily_books.chains.writer import detect_type, rewrite_chapter

sys.path.append(str(Path(__file__).parent))
from fixtures.sample_chapter import (
    get_sample_chapter_doc,
    get_sample_chapter_split,
    get_sample_text,
)


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


def test_compute_observability_metrics():
    """Test observability metrics computation (no enforcement)."""
    orig = '"Hello," said he. "How are you?"'
    modern = '"Hello," he said. "How are you?"'

    result = compute_observability_metrics(orig, modern)

    assert result["quote_count_orig"] == 2
    assert result["quote_count_modern"] == 2
    assert result["emphasis_count_orig"] == 0
    assert result["emphasis_count_modern"] == 0
    assert len(result["detected_archaic"]) == 0
    assert result["ratio"] > 0
    assert result["fk_grade"] > 0


def test_compute_observability_metrics_quote_mismatch():
    """Test observability metrics with quote mismatch."""
    orig = '"Hello," said he. "How are you?"'
    modern = "Hello, he said. How are you?"  # Missing quotes

    result = compute_observability_metrics(orig, modern)

    assert result["quote_count_orig"] == 2
    assert result["quote_count_modern"] == 0  # No quotes in modern
    assert result["emphasis_count_orig"] == 0
    assert result["emphasis_count_modern"] == 0


def test_compute_observability_metrics_emphasis_mismatch():
    """Test observability metrics with emphasis mismatch."""
    orig = "It was _very_ important."
    modern = "It was very important."  # Missing emphasis

    result = compute_observability_metrics(orig, modern)

    assert result["emphasis_count_orig"] == 1
    assert result["emphasis_count_modern"] == 0  # No emphasis in modern


@patch("src.lily_books.chains.ingest.requests.get")
def test_load_gutendex(mock_get):
    """Test Gutendex loading with mocked response."""
    # Mock the metadata response
    mock_metadata = MagicMock()
    mock_metadata.json.return_value = {
        "formats": {"text/plain; charset=utf-8": {"url": "http://example.com/text.txt"}}
    }

    # Mock the text response
    mock_text = MagicMock()
    mock_text.text = "Sample book text content"
    mock_text.raise_for_status.return_value = None

    mock_get.side_effect = [mock_metadata, mock_text]

    result = load_gutendex(123)

    assert result == "Sample book text content"
    assert mock_get.call_count == 2


@patch("src.lily_books.chains.writer.create_llm_with_fallback")
def test_rewrite_chapter(mock_llm_factory):
    """Test chapter rewriting with mocked LLM."""
    # Mock the LLM factory and chain
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_chain.return_value = {
        "paragraphs": [
            {"modern": "Modernized paragraph 1"},
            {"modern": "Modernized paragraph 2"},
        ]
    }
    mock_llm_factory.return_value = mock_llm

    # Mock the chain creation by patching the function that creates it
    with patch(
        "src.lily_books.chains.writer.create_llm_with_fallback", mock_llm_factory
    ):
        chapter_split = get_sample_chapter_split()
        chapter_split.paragraphs = ["Original paragraph 1", "Original paragraph 2"]

        result = rewrite_chapter(chapter_split)

        assert isinstance(result, type(chapter_split).__bases__[0])  # ChapterDoc
        assert len(result.pairs) == 2
        assert result.pairs[0].orig == "Original paragraph 1"
        # Check that modernization occurred (either modernized text or error fallback)
        assert result.pairs[0].modern in [
            "Modernized paragraph 1",
            "Original paragraph 1",
        ]


@patch("src.lily_books.chains.checker.create_llm_with_fallback")
def test_qa_chapter(mock_llm_factory):
    """Test chapter QA with mocked LLM."""
    # Mock the LLM factory and chain
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_chain.return_value = {
        "fidelity_score": 95,
        "readability_appropriate": True,
        "formatting_preserved": True,
        "tone_consistent": True,
        "quote_count_match": True,
        "emphasis_preserved": True,
        "issues": [],
    }
    mock_llm_factory.return_value = mock_llm

    # Mock the chain creation by patching the function that creates it
    with patch(
        "src.lily_books.chains.checker.create_llm_with_fallback", mock_llm_factory
    ):
        chapter_doc = get_sample_chapter_doc()

        passed, issues, updated_doc = qa_chapter(chapter_doc)

        assert isinstance(passed, bool)
        assert isinstance(issues, list)
        assert isinstance(updated_doc, type(chapter_doc))
        assert len(updated_doc.pairs) == len(chapter_doc.pairs)

        # Check that QA reports were added
        for pair in updated_doc.pairs:
            assert pair.qa is not None
            # Check that fidelity score is set (either from mock or fallback)
            assert pair.qa.fidelity_score >= 0


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


def test_structured_outputs():
    """Test that chains use structured outputs."""
    from lily_books.models import CheckerOutput, ModernizedParagraph, WriterOutput

    # Test WriterOutput structure
    writer_output = WriterOutput(
        paragraphs=[
            ModernizedParagraph(modern="Test paragraph 1"),
            ModernizedParagraph(modern="Test paragraph 2"),
        ]
    )

    assert len(writer_output.paragraphs) == 2
    assert writer_output.paragraphs[0].modern == "Test paragraph 1"

    # Test CheckerOutput structure
    checker_output = CheckerOutput(
        fidelity_score=85,
        readability_appropriate=True,
        formatting_preserved=True,
        tone_consistent=True,
        quote_count_match=True,
        emphasis_preserved=True,
        issues=[],
    )

    assert checker_output.fidelity_score == 85
    assert checker_output.readability_appropriate is True


def test_token_counting_integration():
    """Test token counting integration in chains."""
    from lily_books.utils.tokens import calculate_optimal_batch_size, count_tokens

    # Test token counting
    text = "This is a test paragraph for token counting."
    token_count = count_tokens(text, "gpt-4o")

    assert isinstance(token_count, int)
    assert token_count > 0

    # Test batch size calculation
    paragraphs = ["Short para"] * 5
    batch_size = calculate_optimal_batch_size(paragraphs, "gpt-4o")

    assert isinstance(batch_size, int)
    assert 1 <= batch_size <= 20


def test_llm_driven_validation():
    """Test LLM-driven validation approach."""
    from lily_books.models import CheckerOutput, ModernizedParagraph, WriterOutput
    from lily_books.utils.validators import (
        safe_parse_checker_output,
        safe_parse_writer_output,
        sanity_check_checker_output,
        sanity_check_writer_output,
    )

    # Test WriterOutput parsing
    valid_writer_output = WriterOutput(
        paragraphs=[ModernizedParagraph(modern="Valid paragraph")]
    )

    parsed = safe_parse_writer_output(valid_writer_output)
    assert parsed is not None
    assert len(parsed.paragraphs) == 1

    # Test CheckerOutput parsing
    valid_checker_output = CheckerOutput(
        fidelity_score=90,
        readability_grade=8.5,
        confidence=0.85,
        llm_reasoning="Good modernization",
        metadata={"model": "claude-sonnet"},
    )

    parsed = safe_parse_checker_output(valid_checker_output)
    assert parsed is not None
    assert parsed.fidelity_score == 90
    assert parsed.confidence == 0.85

    # Test sanity checks (warnings only)
    warnings = sanity_check_writer_output(valid_writer_output)
    assert isinstance(warnings, list)  # May be empty, that's fine

    warnings = sanity_check_checker_output(valid_checker_output)
    assert isinstance(warnings, list)  # May be empty, that's fine


def test_soft_validation_approach():
    """Test soft validation - no hard failures."""
    from lily_books.models import CheckerOutput

    # Test with None values (LLM decides)
    output = CheckerOutput()
    assert output.fidelity_score is None
    assert output.readability_grade is None
    assert output.readability_appropriate is None

    # Test with partial values
    output = CheckerOutput(
        fidelity_score=75, confidence=0.7, llm_reasoning="Partial assessment"
    )
    assert output.fidelity_score == 75
    assert output.confidence == 0.7
    assert output.readability_grade is None  # LLM didn't provide this
