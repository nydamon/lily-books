"""Tests for soft validation approach in graph nodes."""

from unittest.mock import MagicMock, patch

import pytest
from lily_books.chains.checker import qa_chapter
from lily_books.graph import qa_text_node
from lily_books.models import ChapterDoc, ParaPair, QAReport


def test_qa_text_node_soft_validation():
    """Test that qa_text_node uses soft validation."""
    # Create mock state
    state = {
        "slug": "test-book",
        "rewritten": [
            ChapterDoc(
                chapter=1,
                title="Chapter 1",
                pairs=[
                    ParaPair(
                        i=0,
                        para_id="ch01_para000",
                        orig="Original text",
                        modern="Modernized text",
                    )
                ],
            )
        ],
    }

    # Mock the qa_chapter function to return success
    with patch("lily_books.graph.qa_chapter") as mock_qa:
        mock_qa.return_value = (True, [], state["rewritten"][0])

        # Mock storage functions
        with patch("lily_books.graph.save_qa_issues"), patch(
            "lily_books.graph.save_chapter_doc"
        ), patch("lily_books.graph.append_log_entry"):
            result = qa_text_node(state)

            # Should always pass with soft validation
            assert result["qa_text_ok"] is True
            mock_qa.assert_called_once()


def test_qa_chapter_soft_validation():
    """Test that qa_chapter uses soft validation."""
    # Create test chapter doc
    chapter_doc = ChapterDoc(
        chapter=1,
        title="Chapter 1",
        pairs=[
            ParaPair(
                i=0,
                para_id="ch01_para000",
                orig="Original text",
                modern="Modernized text",
            )
        ],
    )

    # Mock the checker chain
    with patch(
        "lily_books.chains.checker.create_llm_with_fallback"
    ) as mock_llm_factory:
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.return_value = CheckerOutput(
            fidelity_score=85, confidence=0.8, llm_reasoning="Good modernization"
        )
        mock_llm_factory.return_value = mock_llm

        with patch("lily_books.chains.checker.checker_chain", mock_chain), patch(
            "lily_books.chains.checker.create_observability_callback"
        ):
            passed, issues, updated_doc = qa_chapter(chapter_doc)

            # Should always pass with soft validation
            assert passed is True
            assert isinstance(issues, list)
            assert isinstance(updated_doc, ChapterDoc)

            # Check that QA reports were added
            for pair in updated_doc.pairs:
                assert pair.qa is not None
                assert isinstance(pair.qa, QAReport)


def test_qa_chapter_with_none_values():
    """Test qa_chapter with None values from LLM."""
    # Create test chapter doc
    chapter_doc = ChapterDoc(
        chapter=1,
        title="Chapter 1",
        pairs=[
            ParaPair(
                i=0,
                para_id="ch01_para000",
                orig="Original text",
                modern="Modernized text",
            )
        ],
    )

    # Mock the checker chain to return None values
    with patch(
        "lily_books.chains.checker.create_llm_with_fallback"
    ) as mock_llm_factory:
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.return_value = CheckerOutput()  # All None values
        mock_llm_factory.return_value = mock_llm

        with patch("lily_books.chains.checker.checker_chain", mock_chain), patch(
            "lily_books.chains.checker.create_observability_callback"
        ):
            passed, issues, updated_doc = qa_chapter(chapter_doc)

            # Should still pass with soft validation
            assert passed is True
            assert isinstance(issues, list)
            assert isinstance(updated_doc, ChapterDoc)

            # Check that QA reports were added with None values
            for pair in updated_doc.pairs:
                assert pair.qa is not None
                assert pair.qa.fidelity_score is None
                assert pair.qa.confidence is None
                assert pair.qa.llm_reasoning is None


def test_qa_chapter_error_handling():
    """Test qa_chapter error handling with soft validation."""
    # Create test chapter doc
    chapter_doc = ChapterDoc(
        chapter=1,
        title="Chapter 1",
        pairs=[
            ParaPair(
                i=0,
                para_id="ch01_para000",
                orig="Original text",
                modern="Modernized text",
            )
        ],
    )

    # Mock the checker chain to raise an error
    with patch(
        "lily_books.chains.checker.create_llm_with_fallback"
    ) as mock_llm_factory:
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.side_effect = Exception("Test error")
        mock_llm_factory.return_value = mock_llm

        with patch("lily_books.chains.checker.checker_chain", mock_chain), patch(
            "lily_books.chains.checker.create_observability_callback"
        ):
            # Should not crash, but should handle error gracefully
            with pytest.raises(Exception):
                qa_chapter(chapter_doc)


def test_qa_text_node_continues_on_failure():
    """Test that qa_text_node continues processing on individual failures."""
    # Create mock state with multiple chapters
    state = {
        "slug": "test-book",
        "rewritten": [
            ChapterDoc(
                chapter=1,
                title="Chapter 1",
                pairs=[
                    ParaPair(
                        i=0,
                        para_id="ch01_para000",
                        orig="Original text",
                        modern="Modernized text",
                    )
                ],
            ),
            ChapterDoc(
                chapter=2,
                title="Chapter 2",
                pairs=[
                    ParaPair(
                        i=0,
                        para_id="ch02_para000",
                        orig="More text",
                        modern="More modernized text",
                    )
                ],
            ),
        ],
    }

    # Mock qa_chapter to fail on first chapter, succeed on second
    def mock_qa_side_effect(doc, slug=None):
        if doc.chapter == 1:
            raise Exception("Chapter 1 failed")
        else:
            return (True, [], doc)

    with patch("lily_books.graph.qa_chapter", side_effect=mock_qa_side_effect), patch(
        "lily_books.graph.save_qa_issues"
    ), patch("lily_books.graph.save_chapter_doc"), patch(
        "lily_books.graph.save_chapter_failure"
    ), patch(
        "lily_books.graph.append_log_entry"
    ):
        result = qa_text_node(state)

        # Should still pass overall (soft validation)
        assert result["qa_text_ok"] is True


def test_qa_text_node_logging():
    """Test that qa_text_node logs appropriately."""
    # Create mock state
    state = {
        "slug": "test-book",
        "rewritten": [
            ChapterDoc(
                chapter=1,
                title="Chapter 1",
                pairs=[
                    ParaPair(
                        i=0,
                        para_id="ch01_para000",
                        orig="Original text",
                        modern="Modernized text",
                    )
                ],
            )
        ],
    }

    # Mock the qa_chapter function
    with patch("lily_books.graph.qa_chapter") as mock_qa:
        mock_qa.return_value = (True, [], state["rewritten"][0])

        # Mock storage functions
        with patch("lily_books.graph.save_qa_issues"), patch(
            "lily_books.graph.save_chapter_doc"
        ), patch("lily_books.graph.append_log_entry") as mock_log:
            result = qa_text_node(state)

            # Should log completion
            assert mock_log.call_count >= 2  # Started and completed
            assert result["qa_text_ok"] is True


def test_soft_validation_philosophy():
    """Test that soft validation philosophy is maintained."""
    # Test that models accept None values without validation errors
    from lily_books.models import CheckerOutput, QAReport

    # Test CheckerOutput with all None values
    output = CheckerOutput()
    assert output.fidelity_score is None
    assert output.readability_grade is None
    assert output.readability_appropriate is None
    assert output.formatting_preserved is None
    assert output.tone_consistent is None
    assert output.quote_count_match is None
    assert output.emphasis_preserved is None
    assert output.literary_quality_maintained is None
    assert output.historical_accuracy_preserved is None
    assert output.confidence is None
    assert output.llm_reasoning is None
    assert output.metadata == {}
    assert output.issues == []

    # Test QAReport with all None values
    report = QAReport()
    assert report.fidelity_score is None
    assert report.readability_grade is None
    assert report.readability_appropriate is None
    assert report.character_count_ratio is None
    assert report.modernization_complete is None
    assert report.formatting_preserved is None
    assert report.tone_consistent is None
    assert report.quote_count_match is None
    assert report.emphasis_preserved is None
    assert report.literary_quality_maintained is None
    assert report.historical_accuracy_preserved is None
    assert report.confidence is None
    assert report.llm_reasoning is None
    assert report.metadata == {}
    assert report.issues == []
    assert report.retry_count == 0


def test_observability_vs_validation():
    """Test that observability metrics are computed without enforcement."""
    from lily_books.chains.checker import compute_observability_metrics

    # Test with mismatched quotes
    orig = '"Hello," said he. "How are you?"'
    modern = "Hello, he said. How are you?"  # Missing quotes

    metrics = compute_observability_metrics(orig, modern)

    # Should compute metrics without enforcing rules
    assert metrics["quote_count_orig"] == 2
    assert metrics["quote_count_modern"] == 0
    assert metrics["emphasis_count_orig"] == 0
    assert metrics["emphasis_count_modern"] == 0
    assert len(metrics["detected_archaic"]) == 0
    assert metrics["ratio"] > 0
    assert metrics["fk_grade"] > 0

    # Should not raise any validation errors
    assert isinstance(metrics, dict)
    assert "quote_count_orig" in metrics
    assert "quote_count_modern" in metrics
    assert "emphasis_count_orig" in metrics
    assert "emphasis_count_modern" in metrics
    assert "detected_archaic" in metrics
    assert "fk_grade" in metrics
    assert "ratio" in metrics
