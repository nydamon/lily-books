"""LLM-driven validation utilities with self-healing capabilities."""

import logging
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from ..models import WriterOutput, CheckerOutput, ModernizedParagraph
from ..config import settings

logger = logging.getLogger(__name__)


def safe_parse_writer_output(output: Any) -> Optional[WriterOutput]:
    """
    Safely parse WriterOutput from LLM response.
    
    Args:
        output: Raw output from LLM
    
    Returns:
        Parsed WriterOutput or None if parsing fails
    """
    try:
        if isinstance(output, WriterOutput):
            return output
        elif isinstance(output, dict):
            return WriterOutput(**output)
        else:
            logger.warning(f"Unexpected WriterOutput type: {type(output)}")
            return None
    except (ValidationError, TypeError, ValueError) as e:
        logger.error(f"Failed to parse WriterOutput: {e}")
        return None


def safe_parse_checker_output(output: Any) -> Optional[CheckerOutput]:
    """
    Safely parse CheckerOutput from LLM response.
    
    Args:
        output: Raw output from LLM
    
    Returns:
        Parsed CheckerOutput or None if parsing fails
    """
    try:
        if isinstance(output, CheckerOutput):
            return output
        elif isinstance(output, dict):
            # Clean up malformed issues before parsing
            cleaned_output = clean_checker_output(output)
            return CheckerOutput(**cleaned_output)
        else:
            logger.warning(f"Unexpected CheckerOutput type: {type(output)}")
            return None
    except (ValidationError, TypeError, ValueError) as e:
        logger.error(f"Failed to parse CheckerOutput: {e}")
        return None


def clean_checker_output(output: dict) -> dict:
    """
    Clean malformed CheckerOutput data before parsing.
    
    Args:
        output: Raw output dictionary
    
    Returns:
        Cleaned output dictionary
    """
    cleaned = output.copy()
    
    # Clean up issues list
    if 'issues' in cleaned and isinstance(cleaned['issues'], list):
        cleaned_issues = []
        for issue in cleaned['issues']:
            if isinstance(issue, dict):
                # Skip issues with empty type or missing description
                if (issue.get('type') and 
                    issue.get('description') and 
                    len(issue.get('type', '').strip()) > 0 and
                    len(issue.get('description', '').strip()) > 0):
                    cleaned_issues.append(issue)
                else:
                    logger.warning(f"Skipping malformed issue: {issue}")
            else:
                logger.warning(f"Skipping non-dict issue: {issue}")
        
        cleaned['issues'] = cleaned_issues
    
    return cleaned


def sanity_check_writer_output(output: WriterOutput) -> List[str]:
    """
    Perform basic sanity checks on WriterOutput.
    
    Args:
        output: WriterOutput to check
    
    Returns:
        List of warnings (not errors - LLM decides quality)
    """
    warnings = []
    
    # Check for completely empty output
    if not output.paragraphs:
        warnings.append("No paragraphs in output")
        return warnings
    
    # Check for completely empty paragraphs (structural issue)
    for i, paragraph in enumerate(output.paragraphs):
        if not paragraph.modern or paragraph.modern.strip() == "":
            warnings.append(f"Empty paragraph at index {i}")
    
    # Log metrics for observability (not validation)
    total_chars = sum(len(p.modern) for p in output.paragraphs)
    avg_length = total_chars / len(output.paragraphs) if output.paragraphs else 0
    
    logger.info(f"Writer output metrics: {len(output.paragraphs)} paragraphs, "
                f"{total_chars} total chars, {avg_length:.1f} avg length")
    
    return warnings


def sanity_check_checker_output(output: CheckerOutput) -> List[str]:
    """
    Perform basic sanity checks on CheckerOutput.
    
    Args:
        output: CheckerOutput to check
    
    Returns:
        List of warnings (not errors - LLM decides quality)
    """
    warnings = []
    
    # Log metrics for observability (not validation)
    logger.info(f"Checker output metrics: fidelity={output.fidelity_score}, "
                f"readability={output.readability_grade}, issues={len(output.issues)}")
    
    # Check for extreme values (informational only)
    if output.fidelity_score is not None:
        if output.fidelity_score < 0 or output.fidelity_score > 100:
            warnings.append(f"Fidelity score outside typical range: {output.fidelity_score}")
    
    if output.readability_grade is not None:
        if output.readability_grade < 0 or output.readability_grade > 20:
            warnings.append(f"Readability grade outside typical range: {output.readability_grade}")
    
    return warnings


def create_retry_prompt_enhancement(
    original_prompt: str, 
    previous_error: str, 
    attempt: int,
    output_type: str = "writer"
) -> str:
    """
    Create enhanced prompt for retry based on previous failure.
    
    Args:
        original_prompt: Original prompt that failed
        previous_error: Error message from previous attempt
        attempt: Current attempt number (1-based)
        output_type: Type of output ("writer" or "checker")
    
    Returns:
        Enhanced prompt with specific guidance
    """
    if output_type == "writer":
        enhancement = f"""
        
        RETRY ATTEMPT {attempt}: Previous attempt failed with: {previous_error}
        
        Please focus on:
        1. Ensuring all paragraphs are non-empty and meaningful
        2. Maintaining proper paragraph structure
        3. Preserving all content from the original text
        4. Following the modernization guidelines precisely
        
        If you encounter any issues, please provide your best attempt rather than failing.
        """
    else:  # checker
        enhancement = f"""
        
        RETRY ATTEMPT {attempt}: Previous attempt failed with: {previous_error}
        
        Please focus on:
        1. Providing a comprehensive assessment
        2. Ensuring all required fields are present
        3. Being specific about any issues found
        4. Maintaining objectivity in your evaluation
        
        Provide your best assessment even if some aspects are challenging to evaluate.
        """
    
    return original_prompt + enhancement


def log_llm_decision(context: str, decision: Any, reasoning: Optional[str] = None) -> None:
    """
    Log LLM decision for observability.
    
    Args:
        context: Context of the decision
        decision: The decision made by LLM
        reasoning: Optional reasoning from LLM
    """
    logger.info(f"LLM Decision [{context}]: {decision}")
    if reasoning:
        logger.debug(f"LLM Reasoning [{context}]: {reasoning}")


def should_retry_with_enhancement(
    error: Exception, 
    attempt: int, 
    max_attempts: int = None
) -> bool:
    """
    Determine if we should retry with enhanced prompt.
    
    Args:
        error: The error that occurred
        attempt: Current attempt number
        max_attempts: Maximum attempts allowed
    
    Returns:
        True if should retry
    """
    if max_attempts is None:
        max_attempts = settings.max_retry_attempts
    
    if attempt >= max_attempts:
        return False
    
    # Retry on parse errors, validation errors, but not on system errors
    if isinstance(error, (ValidationError, TypeError, ValueError)):
        return True
    
    # Don't retry on system-level errors
    if "timeout" in str(error).lower() or "connection" in str(error).lower():
        return False
    
    return True
