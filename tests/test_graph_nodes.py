"""Tests for graph nodes with new LangChain features."""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path
from lily_books.graph import (
    rewrite_node, qa_text_node, ingest_node, chapterize_node
)
from lily_books.models import FlowState, ChapterSplit, ChapterDoc, ParaPair, QAReport
from lily_books.storage import save_chapter_doc, load_chapter_doc
import sys
sys.path.append(str(Path(__file__).parent))
from fixtures.sample_chapter import get_sample_chapter_split, get_sample_chapter_doc


def test_rewrite_node_skip_completed_chapters():
    """Test that rewrite_node skips already-completed chapters."""
    with tempfile.TemporaryDirectory() as temp_dir:
        slug = "test-skip"
        
        # Create a sample chapter split
        chapter_split = ChapterSplit(
            chapter=1,
            title="Chapter 1",
            paragraphs=["Original paragraph 1", "Original paragraph 2"]
        )
        
        # Create a sample chapter doc (already completed)
        chapter_doc = ChapterDoc(
            chapter=1,
            title="Chapter 1",
            pairs=[
                ParaPair(i=0, para_id="ch01_para000", orig="Original paragraph 1", modern="Modernized paragraph 1"),
                ParaPair(i=1, para_id="ch01_para001", orig="Original paragraph 2", modern="Modernized paragraph 2")
            ]
        )
        
        # Mock the project paths
        with patch('src.lily_books.graph.get_project_paths') as mock_paths:
            mock_paths.return_value = {
                "rewrite": Path(temp_dir),
                "meta": Path(temp_dir)
            }
            
            # Save the chapter doc first
            save_chapter_doc(slug, 1, chapter_doc)
            
            # Mock the rewrite_chapter function to ensure it's not called
            with patch('src.lily_books.graph.rewrite_chapter') as mock_rewrite:
                mock_rewrite.side_effect = Exception("Should not be called")
                
                # Create state
                state: FlowState = {
                    "slug": slug,
                    "book_id": 123,
                    "paths": {},
                    "raw_text": None,
                    "chapters": [chapter_split],
                    "rewritten": None,
                    "qa_text_ok": None,
                    "audio_ok": None
                }
                
                # Run rewrite_node
                result = rewrite_node(state)
                
                # Verify the chapter was skipped (not rewritten)
                assert mock_rewrite.called is False
                assert len(result["rewritten"]) == 1
                assert result["rewritten"][0].chapter == 1


def test_qa_text_node_skip_completed_qa():
    """Test that qa_text_node skips already-QA'd chapters."""
    with tempfile.TemporaryDirectory() as temp_dir:
        slug = "test-skip-qa"
        
        # Create a chapter doc with QA already completed
        chapter_doc = ChapterDoc(
            chapter=1,
            title="Chapter 1",
            pairs=[
                ParaPair(
                    i=0,
                    para_id="ch01_para000",
                    orig="Original paragraph 1",
                    modern="Modernized paragraph 1",
                    qa=QAReport()
                )
            ]
        )
        
        # Mock the project paths
        with patch('src.lily_books.graph.get_project_paths') as mock_paths:
            mock_paths.return_value = {
                "qa_text": Path(temp_dir),
                "meta": Path(temp_dir)
            }
            
            # Mock the qa_chapter function to ensure it's not called
            with patch('src.lily_books.graph.qa_chapter') as mock_qa:
                mock_qa.side_effect = Exception("Should not be called")
                
                # Create state
                state: FlowState = {
                    "slug": slug,
                    "book_id": 123,
                    "paths": {},
                    "raw_text": None,
                    "chapters": None,
                    "rewritten": [chapter_doc],
                    "qa_text_ok": None,
                    "audio_ok": None
                }
                
                # Run qa_text_node
                result = qa_text_node(state)
                
                # Verify the chapter was skipped (not QA'd)
                assert mock_qa.called is False
                assert result["qa_text_ok"] is not None


def test_rewrite_node_with_fallback_models():
    """Test rewrite_node with fallback model configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        slug = "test-fallback"
        
        chapter_split = ChapterSplit(
            chapter=1,
            title="Chapter 1",
            paragraphs=["Test paragraph"]
        )
        
        # Mock the LLM factory
        with patch('src.lily_books.chains.writer.create_llm_with_fallback') as mock_factory:
            mock_llm = MagicMock()
            mock_factory.return_value = mock_llm
            
            # Mock the chain
            with patch('src.lily_books.chains.writer.writer_chain') as mock_chain:
                mock_chain.return_value = {
                    "paragraphs": [{"modern": "Modernized paragraph"}]
                }
                
                # Mock project paths
                with patch('src.lily_books.graph.get_project_paths') as mock_paths:
                    mock_paths.return_value = {
                        "rewrite": Path(temp_dir),
                        "meta": Path(temp_dir)
                    }
                    
                    # Create state
                    state: FlowState = {
                        "slug": slug,
                        "book_id": 123,
                        "paths": {},
                        "raw_text": None,
                        "chapters": [chapter_split],
                        "rewritten": None,
                        "qa_text_ok": None,
                        "audio_ok": None
                    }
                    
                    # Run rewrite_node
                    result = rewrite_node(state)
                    
                    # Verify fallback model factory was called
                    mock_factory.assert_called_once_with(
                        provider="openai",
                        temperature=0.2,
                        timeout=30,
                        max_retries=2,
                        cache_enabled=True
                    )


def test_qa_text_node_with_fallback_models():
    """Test qa_text_node with fallback model configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        slug = "test-fallback-qa"
        
        chapter_doc = ChapterDoc(
            chapter=1,
            title="Chapter 1",
            pairs=[
                ParaPair(
                    i=0, 
                    para_id="ch01_para000", 
                    orig="Original paragraph", 
                    modern="Modernized paragraph"
                )
            ]
        )
        
        # Mock the LLM factory
        with patch('src.lily_books.chains.checker.create_llm_with_fallback') as mock_factory:
            mock_llm = MagicMock()
            mock_factory.return_value = mock_llm
            
            # Mock the chain
            with patch('src.lily_books.chains.checker.checker_chain') as mock_chain:
                mock_chain.return_value = {
                    "fidelity_score": 95,
                    "readability_appropriate": True,
                    "formatting_preserved": True,
                    "tone_consistent": True,
                    "quote_count_match": True,
                    "emphasis_preserved": True,
                    "issues": []
                }
                
                # Mock project paths
                with patch('src.lily_books.graph.get_project_paths') as mock_paths:
                    mock_paths.return_value = {
                        "qa_text": Path(temp_dir),
                        "meta": Path(temp_dir)
                    }
                    
                    # Create state
                    state: FlowState = {
                        "slug": slug,
                        "book_id": 123,
                        "paths": {},
                        "raw_text": None,
                        "chapters": None,
                        "rewritten": [chapter_doc],
                        "qa_text_ok": None,
                        "audio_ok": None
                    }
                    
                    # Run qa_text_node
                    result = qa_text_node(state)
                    
                    # Verify fallback model factory was called
                    mock_factory.assert_called_once_with(
                        provider="anthropic",
                        temperature=0.0,
                        timeout=30,
                        max_retries=2,
                        cache_enabled=True
                    )


def test_rewrite_node_token_validation():
    """Test rewrite_node with token validation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        slug = "test-tokens"
        
        # Create a chapter with very long paragraphs to test token validation
        long_paragraphs = ["Very long paragraph " * 1000] * 5  # Simulate long text
        chapter_split = ChapterSplit(
            chapter=1,
            title="Chapter 1",
            paragraphs=long_paragraphs
        )
        
        # Mock token validation to return invalid
        with patch('src.lily_books.chains.writer.validate_context_window') as mock_validate:
            mock_validate.return_value = (False, 150000, 100000)  # Exceeds context window
            
            # Mock the LLM factory and chain
            with patch('src.lily_books.chains.writer.create_llm_with_fallback') as mock_factory:
                mock_llm = MagicMock()
                mock_factory.return_value = mock_llm
                
                with patch('src.lily_books.chains.writer.writer_chain') as mock_chain:
                    mock_chain.return_value = {
                        "paragraphs": [{"modern": "Fallback paragraph"}]
                    }
                    
                    # Mock project paths
                    with patch('src.lily_books.graph.get_project_paths') as mock_paths:
                        mock_paths.return_value = {
                            "rewrite": Path(temp_dir),
                            "meta": Path(temp_dir)
                        }
                        
                        # Create state
                        state: FlowState = {
                            "slug": slug,
                            "book_id": 123,
                            "paths": {},
                            "raw_text": None,
                            "chapters": [chapter_split],
                            "rewritten": None,
                            "qa_text_ok": None,
                            "audio_ok": None
                        }
                        
                        # Run rewrite_node
                        result = rewrite_node(state)
                        
                        # Verify token validation was called
                        assert mock_validate.called
                        assert len(result["rewritten"]) == 1


def test_rewrite_node_adaptive_batching():
    """Test rewrite_node with adaptive batch sizing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        slug = "test-batching"
        
        # Create multiple paragraphs
        paragraphs = [f"Paragraph {i}" for i in range(10)]
        chapter_split = ChapterSplit(
            chapter=1,
            title="Chapter 1",
            paragraphs=paragraphs
        )
        
        # Mock batch size calculation
        with patch('src.lily_books.chains.writer.calculate_optimal_batch_size') as mock_batch:
            mock_batch.return_value = 3  # Smaller batch size
            
            # Mock the LLM factory and chain
            with patch('src.lily_books.chains.writer.create_llm_with_fallback') as mock_factory:
                mock_llm = MagicMock()
                mock_factory.return_value = mock_llm
                
                with patch('src.lily_books.chains.writer.writer_chain') as mock_chain:
                    mock_chain.return_value = {
                        "paragraphs": [{"modern": f"Modernized paragraph {i}"} for i in range(3)]
                    }
                    
                    # Mock project paths
                    with patch('src.lily_books.graph.get_project_paths') as mock_paths:
                        mock_paths.return_value = {
                            "rewrite": Path(temp_dir),
                            "meta": Path(temp_dir)
                        }
                        
                        # Create state
                        state: FlowState = {
                            "slug": slug,
                            "book_id": 123,
                            "paths": {},
                            "raw_text": None,
                            "chapters": [chapter_split],
                            "rewritten": None,
                            "qa_text_ok": None,
                            "audio_ok": None
                        }
                        
                        # Run rewrite_node
                        result = rewrite_node(state)
                        
                        # Verify batch size calculation was called
                        mock_batch.assert_called_once()
                        assert len(result["rewritten"]) == 1


def test_observability_integration():
    """Test that observability callbacks are used in nodes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        slug = "test-observability"
        
        chapter_split = ChapterSplit(
            chapter=1,
            title="Chapter 1",
            paragraphs=["Test paragraph"]
        )
        
        # Mock observability callback creation
        with patch('src.lily_books.chains.writer.create_observability_callback') as mock_callback:
            mock_callback.return_value = [MagicMock()]
            
            # Mock the LLM factory and chain
            with patch('src.lily_books.chains.writer.create_llm_with_fallback') as mock_factory:
                mock_llm = MagicMock()
                mock_factory.return_value = mock_llm
                
                with patch('src.lily_books.chains.writer.writer_chain') as mock_chain:
                    mock_chain.return_value = {
                        "paragraphs": [{"modern": "Modernized paragraph"}]
                    }
                    
                    # Mock project paths
                    with patch('src.lily_books.graph.get_project_paths') as mock_paths:
                        mock_paths.return_value = {
                            "rewrite": Path(temp_dir),
                            "meta": Path(temp_dir)
                        }
                        
                        # Create state
                        state: FlowState = {
                            "slug": slug,
                            "book_id": 123,
                            "paths": {},
                            "raw_text": None,
                            "chapters": [chapter_split],
                            "rewritten": None,
                            "qa_text_ok": None,
                            "audio_ok": None
                        }
                        
                        # Run rewrite_node
                        result = rewrite_node(state)
                        
                        # Verify observability callback was created
                        mock_callback.assert_called_once_with(slug)
