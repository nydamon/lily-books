"""Tests for self-healing retry logic."""

from unittest.mock import MagicMock, patch

from lily_books.config import settings
from lily_books.utils.retry import (
    analyze_failure_and_enhance_prompt,
    enhance_prompt_on_retry,
    enhance_qa_prompt_on_retry,
    retry_with_llm_enhancement,
)
from lily_books.utils.validators import (
    create_retry_prompt_enhancement,
    log_llm_decision,
)
from lily_books.utils.validators import (
    should_retry_with_enhancement as validator_should_retry,
)


def test_enhance_prompt_on_retry():
    """Test prompt enhancement for retry."""
    original_prompt = "Modernize this text: Hello world"
    error_context = {"error": "Failed to parse output", "type": "ValidationError"}

    enhanced = enhance_prompt_on_retry(original_prompt, error_context, 2, "writer")

    assert original_prompt in enhanced
    assert "RETRY ATTEMPT 2" in enhanced
    assert "Failed to parse output" in enhanced
    assert "ValidationError" in enhanced
    assert "Please focus on" in enhanced


def test_enhance_qa_prompt_on_retry():
    """Test QA prompt enhancement for retry."""
    original_prompt = "Assess this modernization"
    error_context = {"error": "Missing required fields", "type": "ValueError"}

    enhanced = enhance_qa_prompt_on_retry(original_prompt, error_context, 1)

    assert original_prompt in enhanced
    assert "RETRY ATTEMPT 1" in enhanced
    assert "Missing required fields" in enhanced
    assert "comprehensive assessment" in enhanced


def test_analyze_failure_and_enhance_prompt():
    """Test failure analysis and prompt enhancement."""
    original_input = {"prompt": "Test prompt", "data": "test"}
    error = ValueError("Test error")

    enhanced = analyze_failure_and_enhance_prompt(original_input, error, 2, "writer")

    assert enhanced["prompt"] != original_input["prompt"]
    assert enhanced["retry_attempt"] == 2
    assert enhanced["error_context"]["error"] == "Test error"
    assert enhanced["error_context"]["type"] == "ValueError"
    assert enhanced["data"] == "test"  # Original data preserved


def test_validator_should_retry():
    """Test retry decision logic."""
    # Test retry on validation errors
    error = ValueError("Validation failed")
    assert validator_should_retry(error, 1) is True

    # Test retry on parse errors
    error = TypeError("Cannot parse")
    assert validator_should_retry(error, 1) is True

    # Test no retry on system errors
    error = ConnectionError("Network timeout")
    assert validator_should_retry(error, 1) is False


def test_create_retry_prompt_enhancement():
    """Test retry prompt enhancement creation."""
    original_prompt = "Modernize this text"
    previous_error = "Output format invalid"

    # Test writer enhancement
    enhanced = create_retry_prompt_enhancement(
        original_prompt, previous_error, 2, "writer"
    )

    assert original_prompt in enhanced
    assert "RETRY ATTEMPT 2" in enhanced
    assert "Output format invalid" in enhanced
    assert "paragraphs are non-empty" in enhanced

    # Test checker enhancement
    enhanced = create_retry_prompt_enhancement(
        original_prompt, previous_error, 1, "checker"
    )

    assert original_prompt in enhanced
    assert "RETRY ATTEMPT 1" in enhanced
    assert "comprehensive assessment" in enhanced


@patch("lily_books.utils.validators.create_retry_prompt_enhancement")
def test_retry_with_llm_enhancement(mock_enhance):
    """Test LLM enhancement retry mechanism."""
    mock_enhance.return_value = "Enhanced prompt"

    mock_chain = MagicMock()
    mock_chain.return_value = {"result": "success"}

    input_data = {"prompt": "Original prompt", "data": "test"}
    previous_error = "Parse error"

    result = retry_with_llm_enhancement(
        mock_chain, input_data, previous_error, 2, "writer"
    )

    # Verify enhancement was called
    mock_enhance.assert_called_once_with("Original prompt", previous_error, 2, "writer")

    # Verify chain was called with enhanced input
    mock_chain.assert_called_once()
    call_args = mock_chain.call_args[0][0]
    assert call_args["prompt"] == "Enhanced prompt"
    assert call_args["data"] == "test"  # Original data preserved

    assert result == {"result": "success"}


def test_log_llm_decision():
    """Test LLM decision logging."""
    # This test mainly ensures the function doesn't crash
    log_llm_decision("test_context", "test_decision", "test_reasoning")

    # Test without reasoning
    log_llm_decision("test_context", "test_decision")


def test_retry_configuration():
    """Test retry configuration settings."""
    # Test default settings
    assert hasattr(settings, "max_retry_attempts")
    assert hasattr(settings, "self_healing_enabled")
    assert hasattr(settings, "retry_enhancement_strategy")

    # Test that settings are accessible
    assert isinstance(settings.max_retry_attempts, int)
    assert isinstance(settings.self_healing_enabled, bool)
    assert isinstance(settings.retry_enhancement_strategy, str)


def test_retry_with_different_error_types():
    """Test retry behavior with different error types."""
    # Test validation errors (should retry)
    validation_error = ValueError("Validation failed")
    assert validator_should_retry(validation_error, 1) is True

    # Test parse errors (should retry)
    parse_error = TypeError("Cannot parse")
    assert validator_should_retry(parse_error, 1) is True

    # Test system errors (should not retry)
    system_error = ConnectionError("Network timeout")
    assert validator_should_retry(system_error, 1) is False

    # Test timeout errors (should not retry)
    timeout_error = TimeoutError("Request timeout")
    assert validator_should_retry(timeout_error, 1) is False


def test_enhancement_strategies():
    """Test different enhancement strategies."""
    original_prompt = "Test prompt"
    error_context = {"error": "Test error", "type": "ValueError"}

    # Test progressive strategy
    enhanced = enhance_prompt_on_retry(original_prompt, error_context, 1, "writer")
    assert "Please focus on" in enhanced
    assert "best attempt" in enhanced

    # Test checker strategy
    enhanced = enhance_prompt_on_retry(original_prompt, error_context, 1, "checker")
    assert "comprehensive assessment" in enhanced
    assert "objectivity" in enhanced


def test_retry_attempt_numbering():
    """Test retry attempt numbering in enhancements."""
    original_prompt = "Test prompt"
    error_context = {"error": "Test error", "type": "ValueError"}

    # Test different attempt numbers
    for attempt in range(1, 4):
        enhanced = enhance_prompt_on_retry(
            original_prompt, error_context, attempt, "writer"
        )
        assert f"RETRY ATTEMPT {attempt}" in enhanced


def test_error_context_preservation():
    """Test that error context is preserved in enhancements."""
    original_prompt = "Test prompt"
    error_context = {"error": "Specific error message", "type": "SpecificErrorType"}

    enhanced = enhance_prompt_on_retry(original_prompt, error_context, 1, "writer")

    assert "Specific error message" in enhanced
    assert "SpecificErrorType" in enhanced


def test_chain_type_specific_guidance():
    """Test that enhancement provides chain-specific guidance."""
    original_prompt = "Test prompt"
    error_context = {"error": "Test error", "type": "ValueError"}

    # Writer-specific guidance
    writer_enhanced = enhance_prompt_on_retry(
        original_prompt, error_context, 1, "writer"
    )
    assert "paragraphs" in writer_enhanced
    assert "modernization" in writer_enhanced

    # Checker-specific guidance
    checker_enhanced = enhance_prompt_on_retry(
        original_prompt, error_context, 1, "checker"
    )
    assert "assessment" in checker_enhanced
    assert "evaluation" in checker_enhanced


def test_retry_with_empty_input():
    """Test retry behavior with empty input."""
    mock_chain = MagicMock()
    mock_chain.return_value = {"result": "success"}

    input_data = {}
    previous_error = "Test error"

    result = retry_with_llm_enhancement(
        mock_chain, input_data, previous_error, 1, "writer"
    )

    # Should still work with empty input
    mock_chain.assert_called_once()
    assert result == {"result": "success"}


def test_enhancement_with_special_characters():
    """Test enhancement with special characters in error messages."""
    original_prompt = "Test prompt"
    error_context = {"error": "Error with special chars: <>&\"'", "type": "ValueError"}

    enhanced = enhance_prompt_on_retry(original_prompt, error_context, 1, "writer")

    # Should handle special characters gracefully
    assert original_prompt in enhanced
    assert "RETRY ATTEMPT 1" in enhanced
