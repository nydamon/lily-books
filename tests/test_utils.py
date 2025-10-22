"""Tests for utility modules."""

import pytest
from unittest.mock import patch, MagicMock
from lily_books.utils.tokens import (
    count_tokens, count_tokens_batch, get_context_window,
    validate_context_window, calculate_optimal_batch_size,
    log_token_usage
)
from lily_books.utils.validators import (
    safe_parse_writer_output, safe_parse_checker_output,
    sanity_check_writer_output, sanity_check_checker_output,
    should_retry_with_enhancement
)
from lily_books.utils.cache import SemanticCache, get_cached_llm
from lily_books.utils.llm_factory import (
    create_openai_llm_with_fallback, create_anthropic_llm_with_fallback,
    create_llm_with_fallback, get_model_info
)
from lily_books.utils.retry import (
    create_retry_decorator, create_rate_limit_retry_decorator,
    create_validation_retry_decorator, create_network_retry_decorator
)
from lily_books.models import WriterOutput, CheckerOutput, ModernizedParagraph, QAIssue


class TestTokenCounting:
    """Test token counting utilities."""
    
    def test_count_tokens(self):
        """Test basic token counting."""
        text = "Hello world"
        count = count_tokens(text, "gpt-4o")
        
        assert isinstance(count, int)
        assert count > 0
        assert count <= len(text)  # Tokens should be <= characters
    
    def test_count_tokens_batch(self):
        """Test batch token counting."""
        texts = ["Hello", "World", "Test"]
        counts = count_tokens_batch(texts, "gpt-4o")
        
        assert len(counts) == len(texts)
        assert all(isinstance(count, int) for count in counts)
        assert all(count > 0 for count in counts)
    
    def test_get_context_window(self):
        """Test context window retrieval."""
        gpt_window = get_context_window("gpt-4o")
        claude_window = get_context_window("anthropic/claude-sonnet-4.5")
        
        assert gpt_window == 128000
        assert claude_window == 200000
        
        # Test unknown model
        unknown_window = get_context_window("unknown-model")
        assert unknown_window == 128000  # Default
    
    def test_validate_context_window(self):
        """Test context window validation."""
        short_text = "Hello world"
        is_valid, token_count, max_tokens = validate_context_window(short_text, "gpt-4o")
        
        assert is_valid is True
        assert token_count > 0
        assert max_tokens > 0
        assert token_count <= max_tokens
    
    def test_validate_context_window_too_long(self):
        """Test context window validation with long text."""
        # Create a very long text (simulate)
        long_text = "word " * 100000  # Very long text
        
        with patch('src.lily_books.utils.tokens.count_tokens') as mock_count:
            mock_count.return_value = 150000  # Exceeds context window
            is_valid, token_count, max_tokens = validate_context_window(long_text, "gpt-4o")
            
            assert is_valid is False
            assert token_count == 150000
            assert max_tokens < 150000
    
    def test_calculate_optimal_batch_size(self):
        """Test optimal batch size calculation."""
        paragraphs = ["Short para"] * 10
        
        batch_size = calculate_optimal_batch_size(
            paragraphs, 
            model="gpt-4o",
            target_utilization=0.6,
            min_batch_size=1,
            max_batch_size=20
        )
        
        assert isinstance(batch_size, int)
        assert 1 <= batch_size <= 20
    
    def test_calculate_optimal_batch_size_empty(self):
        """Test batch size calculation with empty input."""
        batch_size = calculate_optimal_batch_size([], "gpt-4o")
        assert batch_size == 1  # min_batch_size


class TestValidators:
    """Test validation utilities."""
    
    def test_validate_writer_output(self):
        """Test WriterOutput validation."""
        output = WriterOutput(
            paragraphs=[
                ModernizedParagraph(modern="Modernized paragraph 1"),
                ModernizedParagraph(modern="Modernized paragraph 2")
            ]
        )
        
        is_valid, errors = validate_writer_output(output, 2)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_writer_output_count_mismatch(self):
        """Test WriterOutput validation with count mismatch."""
        output = WriterOutput(
            paragraphs=[
                ModernizedParagraph(modern="Only one paragraph")
            ]
        )
        
        is_valid, errors = validate_writer_output(output, 2)
        assert is_valid is False
        assert len(errors) > 0
        assert "count mismatch" in errors[0].lower()
    
    def test_validate_writer_output_empty_paragraph(self):
        """Test WriterOutput validation with empty paragraph."""
        output = WriterOutput(
            paragraphs=[
                ModernizedParagraph(modern=""),  # Empty paragraph
                ModernizedParagraph(modern="Valid paragraph")
            ]
        )
        
        is_valid, errors = validate_writer_output(output, 2)
        assert is_valid is False
        assert len(errors) > 0
        assert "empty" in errors[0].lower()
    
    def test_validate_checker_output(self):
        """Test CheckerOutput validation."""
        output = CheckerOutput(
            fidelity_score=95,
            readability_appropriate=True,
            formatting_preserved=True,
            tone_consistent=True,
            quote_count_match=True,
            emphasis_preserved=True,
            issues=[]
        )
        
        is_valid, errors = validate_checker_output(output)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_checker_output_invalid_score(self):
        """Test CheckerOutput validation with invalid score."""
        output = CheckerOutput(
            fidelity_score=150,  # Invalid score
            readability_appropriate=True,
            formatting_preserved=True,
            tone_consistent=True,
            quote_count_match=True,
            emphasis_preserved=True,
            issues=[]
        )
        
        is_valid, errors = validate_checker_output(output)
        assert is_valid is False
        assert len(errors) > 0
        assert "invalid fidelity score" in errors[0].lower()
    
    def test_validate_paragraph_pair(self):
        """Test paragraph pair validation."""
        orig = "Original text"
        modern = "Modernized text"
        
        is_valid, errors = validate_paragraph_pair(orig, modern)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_paragraph_pair_ratio_issues(self):
        """Test paragraph pair validation with ratio issues."""
        orig = "Short"
        modern = "This is a very long modernized version that significantly exceeds the original length"
        
        is_valid, errors = validate_paragraph_pair(orig, modern)
        assert is_valid is False
        assert len(errors) > 0
        assert "too long" in errors[0].lower()
    
    def test_validate_batch_consistency(self):
        """Test batch consistency validation."""
        originals = ["Text 1", "Text 2"]
        moderns = ["Modern 1", "Modern 2"]
        
        is_valid, errors = validate_batch_consistency(originals, moderns)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_batch_consistency_count_mismatch(self):
        """Test batch consistency validation with count mismatch."""
        originals = ["Text 1", "Text 2"]
        moderns = ["Modern 1"]  # Missing one
        
        is_valid, errors = validate_batch_consistency(originals, moderns)
        assert is_valid is False
        assert len(errors) > 0
        assert "mismatch" in errors[0].lower()
    
    def test_safe_validate_writer_output(self):
        """Test safe WriterOutput validation."""
        # Test with valid output
        valid_output = WriterOutput(
            paragraphs=[
                ModernizedParagraph(modern="Valid paragraph")
            ]
        )
        
        result = safe_validate_writer_output(valid_output, 1)
        assert isinstance(result, WriterOutput)
        assert len(result.paragraphs) == 1
        assert result.paragraphs[0].modern == "Valid paragraph"
    
    def test_safe_validate_writer_output_invalid(self):
        """Test safe WriterOutput validation with invalid input."""
        # Test with invalid input (wrong count)
        invalid_output = WriterOutput(
            paragraphs=[
                ModernizedParagraph(modern="Only one")
            ]
        )
        
        result = safe_validate_writer_output(invalid_output, 2)
        assert isinstance(result, WriterOutput)
        assert len(result.paragraphs) == 2
        # Should have fallback content
        assert "[Validation failed" in result.paragraphs[0].modern
    
    def test_safe_validate_checker_output(self):
        """Test safe CheckerOutput validation."""
        # Test with valid output
        valid_output = CheckerOutput(
            fidelity_score=95,
            readability_appropriate=True,
            formatting_preserved=True,
            tone_consistent=True,
            quote_count_match=True,
            emphasis_preserved=True,
            issues=[]
        )
        
        result = safe_validate_checker_output(valid_output)
        assert isinstance(result, CheckerOutput)
        assert result.fidelity_score == 95
    
    def test_safe_validate_checker_output_invalid(self):
        """Test safe CheckerOutput validation with invalid input."""
        # Test with invalid input
        invalid_output = CheckerOutput(
            fidelity_score=150,  # Invalid
            readability_appropriate=True,
            formatting_preserved=True,
            tone_consistent=True,
            quote_count_match=True,
            emphasis_preserved=True,
            issues=[]
        )
        
        result = safe_validate_checker_output(invalid_output)
        assert isinstance(result, CheckerOutput)
        assert result.fidelity_score == 50  # Fallback value


class TestCaching:
    """Test caching utilities."""
    
    def test_semantic_cache_initialization(self):
        """Test SemanticCache initialization."""
        cache = SemanticCache()
        
        # Should initialize without errors
        assert cache is not None
    
    @patch('src.lily_books.utils.cache.settings')
    def test_semantic_cache_disabled(self, mock_settings):
        """Test SemanticCache when caching is disabled."""
        mock_settings.cache_enabled = False
        
        cache = SemanticCache()
        assert cache.cache is None
    
    def test_get_cache_key(self):
        """Test cache key generation."""
        cache = SemanticCache()
        
        key1 = cache.get_cache_key("test prompt", "gpt-4o")
        key2 = cache.get_cache_key("test prompt", "gpt-4o")
        key3 = cache.get_cache_key("different prompt", "gpt-4o")
        
        assert key1 == key2  # Same prompt should generate same key
        assert key1 != key3  # Different prompts should generate different keys
        assert isinstance(key1, str)
        assert len(key1) > 0
    
    def test_cache_operations(self):
        """Test cache get/put operations."""
        cache = SemanticCache()
        
        # Test with disabled cache
        if cache.cache is None:
            result = cache.get("test prompt", "gpt-4o")
            assert result is None
            
            cache.put("test prompt", "gpt-4o", "test response")
            # Should not crash
    
    def test_get_cached_llm(self):
        """Test LLM caching wrapper."""
        from langchain_openai import ChatOpenAI
        
        mock_llm = ChatOpenAI(model="gpt-4o", api_key="test")
        
        with patch('src.lily_books.utils.cache.settings') as mock_settings:
            mock_settings.cache_enabled = False
            result = get_cached_llm(mock_llm)
            assert result == mock_llm  # Should return original when caching disabled


class TestLLMFactory:
    """Test LLM factory utilities."""
    
    @patch('src.lily_books.utils.llm_factory.settings')
    def test_create_openai_llm_with_fallback(self, mock_settings):
        """Test OpenAI LLM factory with fallback."""
        mock_settings.openai_model = "gpt-4o"
        mock_settings.openai_fallback_model = "gpt-4o-mini"
        mock_settings.openai_api_key = "test-key"
        
        with patch('src.lily_books.utils.llm_factory.ChatOpenAI') as mock_chat:
            with patch('src.lily_books.utils.llm_factory.RunnableWithFallbacks') as mock_fallback:
                mock_llm = MagicMock()
                mock_chat.return_value = mock_llm
                mock_fallback.return_value = MagicMock()
                
                result = create_openai_llm_with_fallback()
                
                assert mock_chat.call_count == 2  # Primary and fallback
                assert mock_fallback.called
    
    @patch('src.lily_books.utils.llm_factory.settings')
    def test_create_anthropic_llm_with_fallback(self, mock_settings):
        """Test Anthropic LLM factory with fallback."""
        mock_settings.anthropic_model = "anthropic/claude-haiku-4.5"
        mock_settings.anthropic_fallback_model = "anthropic/claude-sonnet-4.5"
        mock_settings.anthropic_api_key = "test-key"
        
        with patch('src.lily_books.utils.llm_factory.ChatAnthropic') as mock_chat:
            with patch('src.lily_books.utils.llm_factory.RunnableWithFallbacks') as mock_fallback:
                mock_llm = MagicMock()
                mock_chat.return_value = mock_llm
                mock_fallback.return_value = MagicMock()
                
                result = create_anthropic_llm_with_fallback()
                
                assert mock_chat.call_count == 2  # Primary and fallback
                assert mock_fallback.called
    
    def test_create_llm_with_fallback_invalid_provider(self):
        """Test LLM factory with invalid provider."""
        with pytest.raises(ValueError):
            create_llm_with_fallback("invalid-provider")
    
    @patch('src.lily_books.utils.llm_factory.settings')
    def test_get_model_info(self, mock_settings):
        """Test model info retrieval."""
        mock_settings.openai_model = "gpt-4o"
        mock_settings.openai_fallback_model = "gpt-4o-mini"
        mock_settings.anthropic_model = "anthropic/claude-haiku-4.5"
        mock_settings.anthropic_fallback_model = "anthropic/claude-sonnet-4.5"
        
        openai_info = get_model_info("openai")
        assert openai_info["primary"] == "gpt-4o"
        assert openai_info["fallback"] == "gpt-4o-mini"
        assert openai_info["provider"] == "openai"
        
        anthropic_info = get_model_info("anthropic")
        assert anthropic_info["primary"] == "anthropic/claude-haiku-4.5"
        assert anthropic_info["fallback"] == "claude-3-haiku"
        assert anthropic_info["provider"] == "anthropic"
        
        with pytest.raises(ValueError):
            get_model_info("invalid")


class TestRetry:
    """Test retry utilities."""
    
    def test_create_retry_decorator(self):
        """Test retry decorator creation."""
        decorator = create_retry_decorator(
            max_attempts=3,
            max_wait=30,
            base_wait=1.0,
            jitter=True
        )
        
        assert callable(decorator)
    
    def test_create_rate_limit_retry_decorator(self):
        """Test rate limit retry decorator creation."""
        decorator = create_rate_limit_retry_decorator()
        assert callable(decorator)
    
    def test_create_validation_retry_decorator(self):
        """Test validation retry decorator creation."""
        decorator = create_validation_retry_decorator()
        assert callable(decorator)
    
    def test_create_network_retry_decorator(self):
        """Test network retry decorator creation."""
        decorator = create_network_retry_decorator()
        assert callable(decorator)
    
    def test_retry_decorator_functionality(self):
        """Test retry decorator with a failing function."""
        call_count = 0
        
        @create_retry_decorator(max_attempts=2, max_wait=1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Test error")
        
        with pytest.raises(Exception):
            failing_function()
        
        assert call_count == 2  # Should retry once
    
    def test_retry_decorator_success(self):
        """Test retry decorator with a successful function."""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, max_wait=1)
        def successful_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt fails")
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count == 2
