"""Tests for async pipeline functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from lily_books.runner import run_pipeline_async
from lily_books.chains.writer import rewrite_chapter_async
from lily_books.chains.checker import qa_chapter_async
from lily_books.models import ChapterSplit, ChapterDoc, ParaPair


class TestAsyncPipeline:
    """Test async pipeline functionality."""
    
    @pytest.mark.asyncio
    async def test_run_pipeline_async_success(self):
        """Test successful async pipeline run."""
        mock_progress_callback = Mock()
        
        with patch('lily_books.runner.ensure_directories'):
            with patch('lily_books.runner.save_state'):
                with patch('lily_books.runner.append_log_entry'):
                    with patch('lily_books.chains.ingest.IngestChain') as mock_ingest:
                        with patch('lily_books.chains.ingest.ChapterizeChain') as mock_chapterize:
                            with patch('lily_books.graph.rewrite_node_async') as mock_rewrite:
                                with patch('lily_books.graph.qa_text_node_async') as mock_qa:
                                    with patch('lily_books.graph.epub_node') as mock_epub:
                                        # Setup mocks
                                        mock_ingest.invoke.return_value = "raw text"
                                        mock_chapterize.invoke.return_value = []
                                        mock_rewrite.return_value = {"rewritten": []}
                                        mock_qa.return_value = {"qa_text_ok": True}
                                        mock_epub.return_value = {"epub_path": "test.epub"}
                                        
                                        result = await run_pipeline_async(
                                            "test-slug", 
                                            1342, 
                                            chapters=[0, 1],
                                            progress_callback=mock_progress_callback
                                        )
                                        
                                        assert result["success"] is True
                                        assert result["slug"] == "test-slug"
                                        assert result["book_id"] == 1342
                                        assert "runtime_sec" in result
                                        
                                        # Verify progress callback was called
                                        assert mock_progress_callback.called
    
    @pytest.mark.asyncio
    async def test_run_pipeline_async_failure(self):
        """Test async pipeline failure handling."""
        with patch('lily_books.runner.ensure_directories'):
            with patch('lily_books.runner.save_state'):
                with patch('lily_books.runner.append_log_entry'):
                    with patch('lily_books.chains.ingest.IngestChain') as mock_ingest:
                        mock_ingest.invoke.side_effect = Exception("Ingest failed")
                        
                        result = await run_pipeline_async("test-slug", 1342)
                        
                        assert result["success"] is False
                        assert "error" in result
                        assert result["error"] == "Ingest failed"


class TestAsyncWriter:
    """Test async writer functionality."""
    
    @pytest.mark.asyncio
    async def test_rewrite_chapter_async_success(self):
        """Test successful async chapter rewriting."""
        chapter_split = ChapterSplit(
            chapter=1,
            title="Test Chapter",
            paragraphs=["Test paragraph 1", "Test paragraph 2"]
        )
        
        mock_progress_callback = Mock()
        
        with patch('lily_books.chains.writer.create_llm_with_fallback') as mock_llm:
            with patch('lily_books.chains.writer.create_observability_callback'):
                with patch('lily_books.chains.writer.calculate_optimal_batch_size', return_value=2):
                    with patch('lily_books.chains.writer.validate_context_window', return_value=(True, 1000, 2000)):
                        with patch('lily_books.chains.writer.process_batch_async') as mock_process_batch:
                            with patch('lily_books.chains.writer.process_single_paragraph_async') as mock_process_single:
                                # Mock the LLM chain
                                mock_chain = Mock()
                                mock_chain.invoke.return_value = Mock()
                                mock_llm.return_value = mock_chain
                                
                                # Mock async functions to return completed results
                                from lily_books.models import ParaPair
                                mock_para_pair = ParaPair(i=0, para_id="ch01_para000", orig="Original", modern="Modernized")
                                mock_process_batch.return_value = [mock_para_pair]
                                mock_process_single.return_value = [mock_para_pair]
                                
                                result = await rewrite_chapter_async(
                                    chapter_split, 
                                    "test-slug", 
                                    mock_progress_callback
                                )
                                
                                assert isinstance(result, ChapterDoc)
                                assert result.chapter == 1
                                assert result.title == "Test Chapter"
    
    @pytest.mark.asyncio
    async def test_rewrite_chapter_async_with_errors(self):
        """Test async chapter rewriting with errors."""
        chapter_split = ChapterSplit(
            chapter=1,
            title="Test Chapter",
            paragraphs=["Test paragraph"]
        )
        
        with patch('lily_books.chains.writer.create_llm_with_fallback'):
            with patch('lily_books.chains.writer.create_observability_callback'):
                with patch('lily_books.chains.writer.calculate_optimal_batch_size', return_value=1):
                    with patch('lily_books.chains.writer.validate_context_window', return_value=(True, 1000, 2000)):
                        with patch('lily_books.chains.writer.process_batch_async') as mock_process_batch:
                            with patch('lily_books.chains.writer.process_single_paragraph_async') as mock_process_single:
                                # Mock async functions to return exceptions
                                mock_process_batch.return_value = Exception("Processing error")
                                mock_process_single.return_value = Exception("Processing error")
                                
                                result = await rewrite_chapter_async(chapter_split, "test-slug")
                                
                                assert isinstance(result, ChapterDoc)
                                assert result.chapter == 1


class TestAsyncChecker:
    """Test async checker functionality."""
    
    @pytest.mark.asyncio
    async def test_qa_chapter_async_success(self):
        """Test successful async chapter QA."""
        chapter_doc = ChapterDoc(
            chapter=1,
            title="Test Chapter",
            pairs=[
                ParaPair(i=0, para_id="ch01_para000", orig="Original", modern="Modernized")
            ]
        )
        
        mock_progress_callback = Mock()
        
        with patch('lily_books.chains.checker.create_llm_with_fallback') as mock_llm:
            with patch('lily_books.chains.checker.create_observability_callback'):
                with patch('lily_books.chains.checker.qa_pair_async') as mock_qa_pair:
                    # Mock the LLM chain
                    mock_chain = Mock()
                    mock_chain.invoke.return_value = Mock()
                    mock_llm.return_value = mock_chain
                    
                    # Mock qa_pair_async to return successful results
                    from lily_books.models import CheckerOutput
                    mock_checker_output = CheckerOutput(
                        fidelity_score=95,
                        readability_grade=8.0,
                        readability_appropriate=True,
                        character_count_ratio=1.1,
                        modernization_complete=True,
                        formatting_preserved=True,
                        tone_consistent=True,
                        quote_count_match=True,
                        emphasis_preserved=True,
                        issues=[]
                    )
                    mock_result = (mock_checker_output, {
                        "quote_parity": True, 
                        "emphasis_parity": True, 
                        "missed_archaic": [],
                        "fk_grade": 8.0,
                        "ratio": 1.1
                    })
                    mock_qa_pair.return_value = mock_result
                    
                    passed, issues, updated_doc = await qa_chapter_async(
                        chapter_doc, 
                        slug="test-slug", 
                        progress_callback=mock_progress_callback
                    )
                    
                    assert isinstance(passed, bool)
                    assert isinstance(issues, list)
                    assert isinstance(updated_doc, ChapterDoc)
    
    @pytest.mark.asyncio
    async def test_qa_chapter_async_with_errors(self):
        """Test async chapter QA with errors."""
        chapter_doc = ChapterDoc(
            chapter=1,
            title="Test Chapter",
            pairs=[
                ParaPair(i=0, para_id="ch01_para000", orig="Original", modern="Modernized")
            ]
        )
        
        with patch('lily_books.chains.checker.create_llm_with_fallback'):
            with patch('lily_books.chains.checker.create_observability_callback'):
                with patch('lily_books.chains.checker.qa_pair_async') as mock_qa_pair:
                    # Mock qa_pair_async to return an exception
                    mock_qa_pair.return_value = Exception("QA error")
                    
                    passed, issues, updated_doc = await qa_chapter_async(chapter_doc, slug="test-slug")
                    
                    assert passed is False
                    assert len(issues) > 0
                    assert isinstance(updated_doc, ChapterDoc)


class TestAsyncObservability:
    """Test async observability functionality."""
    
    def test_streaming_progress_callback(self):
        """Test streaming progress callback."""
        from lily_books.observability import StreamingProgressCallback
        
        mock_callback = Mock()
        progress_handler = StreamingProgressCallback("test-slug", mock_callback)
        
        # Test chain start
        progress_handler.on_chain_start(
            {"name": "test-chain"}, 
            {"input": "test"}, 
            run_id="test-run"
        )
        
        assert mock_callback.called
        call_args = mock_callback.call_args[0][0]
        assert call_args["status"] == "started"
        assert call_args["chain"] == "test-chain"
    
    def test_streaming_progress_callback_error(self):
        """Test streaming progress callback error handling."""
        from lily_books.observability import StreamingProgressCallback
        
        mock_callback = Mock()
        progress_handler = StreamingProgressCallback("test-slug", mock_callback)
        
        # Test chain error
        progress_handler.on_chain_error(
            Exception("Test error"), 
            run_id="test-run"
        )
        
        assert mock_callback.called
        call_args = mock_callback.call_args[0][0]
        assert call_args["status"] == "error"
        assert "Test error" in call_args["error"]
