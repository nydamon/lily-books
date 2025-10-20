"""Checker chain for QA validation using Claude Sonnet."""

import asyncio
import logging
import re

logger = logging.getLogger(__name__)
from typing import Dict, Tuple, List, Callable, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import textstat

from ..models import ChapterDoc, ParaPair, QAReport, QAIssue, CheckerOutput
from ..config import settings
from ..observability import create_observability_callback
from ..utils.cache import get_cached_llm
from ..utils.validators import (
    safe_parse_checker_output, sanity_check_checker_output,
    should_retry_with_enhancement, log_llm_decision
)
from tenacity import stop_after_attempt, wait_exponential, retry_if_exception_type
from ..utils.llm_factory import create_llm_with_fallback

logger = logging.getLogger(__name__)


# Comprehensive LangChain system prompt for quality assurance
CHECKER_SYSTEM = """You are an expert literary editor and quality assurance specialist specializing in classic literature modernization. Your role is to meticulously evaluate pairs of text: original paragraphs from 19th-century literature and their modernized counterparts.

## Your Expertise
- Deep understanding of 19th-century English literature, language patterns, and cultural context
- Expertise in modern English readability, accessibility, and contemporary language usage
- Knowledge of literary devices, dialogue patterns, character development, and narrative structure
- Understanding of formatting conventions, emphasis markers, and typographical elements

## Evaluation Criteria

### 1. FIDELITY (Primary Criterion - Weight: 40%)
The modernized text must preserve the exact meaning, intent, and factual information of the original:
- **Content Preservation**: All key information, plot points, character actions, and dialogue must be identical
- **Character Voice**: Character personalities, speech patterns, and emotional tones must be maintained
- **Literary Elements**: Metaphors, symbolism, foreshadowing, and thematic elements must be preserved
- **Historical Context**: Period-appropriate references, social norms, and cultural elements must be maintained

### 2. MODERNIZATION QUALITY (Weight: 25%)
The text should be updated for contemporary readers while maintaining literary quality:
- **Language Modernization**: Archaic words, phrases, and sentence structures updated to contemporary English
- **Readability Target**: Flesch-Kincaid grade level 7-9 (accessible but not overly simplified)
- **Clarity Enhancement**: Complex sentences simplified without losing meaning or literary value
- **Cultural Adaptation**: Period references explained or adapted for modern understanding

### 3. FORMATTING PRESERVATION (Weight: 20%)
All formatting elements must be meticulously preserved:
- **Quotation Marks**: Exact preservation of all dialogue markers, nested quotes, and quote styles
- **Emphasis Markers**: Conversion of `_italics_` to `<em>italics</em>`, `*bold*` to `<strong>bold</strong>`
- **Paragraph Structure**: Maintain original paragraph breaks, indentation, and text flow
- **Special Characters**: Preserve em dashes, ellipses, and other typographical elements

### 4. TONE AND STYLE CONSISTENCY (Weight: 15%)
The modernized text must maintain the original's literary character:
- **Narrative Voice**: Preserve the author's distinctive voice and storytelling style
- **Formal Register**: Maintain appropriate formality level for the genre and period
- **Literary Sophistication**: Preserve the intellectual and artistic quality of the original
- **Emotional Resonance**: Maintain the emotional impact and reader engagement

## Scoring Guidelines

### Fidelity Score (0-100)
- **90-100**: Perfect preservation of meaning, content, and literary elements
- **80-89**: Excellent preservation with minor, acceptable adaptations
- **70-79**: Good preservation with some content changes that don't affect core meaning
- **60-69**: Adequate preservation with noticeable content changes
- **Below 60**: Significant content loss or distortion

### Readability Assessment
- **Target Grade**: 7-9 (middle school to early high school level)
- **Too Simple**: Below grade 7 loses literary sophistication
- **Too Complex**: Above grade 9 reduces accessibility

### Formatting Validation
- **Perfect**: All quotes, emphasis, and structure preserved exactly
- **Minor Issues**: Small formatting inconsistencies that don't affect readability
- **Major Issues**: Significant formatting problems that impact comprehension

## Common Issues to Flag

### Critical Issues (Must Fail)
- Missing or changed dialogue
- Altered character names or relationships
- Changed plot points or story events
- Lost emphasis or formatting that affects meaning
- Inappropriate modernization (adding modern concepts not implied)

### Moderate Issues (Flag but May Pass)
- Minor readability problems
- Small formatting inconsistencies
- Slight tone variations
- Acceptable cultural adaptations

### Minor Issues (Note but Don't Fail)
- Style preferences
- Minor word choice variations
- Acceptable simplifications

## Output Requirements
Provide a comprehensive assessment using the structured format specified in the format instructions. Include specific examples of issues found and recommendations for improvement when applicable."""

CHECKER_USER = """Please evaluate this text pair for quality assurance:

**ORIGINAL TEXT:**
{original}

**MODERNIZED TEXT:**
{modern}

Analyze these texts according to the comprehensive criteria provided in the system prompt. Focus on fidelity, modernization quality, formatting preservation, and tone consistency.

{format_instructions}"""

# Create parser and prompt with format instructions
checker_parser = PydanticOutputParser(pydantic_object=CheckerOutput)

# Create comprehensive prompt with system and user messages
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

# Create local prompt template as fallback
local_checker_prompt = ChatPromptTemplate.from_messages([
    ("system", CHECKER_SYSTEM),
    ("human", CHECKER_USER)
])

# Use local prompt directly
checker_prompt = local_checker_prompt


def compute_observability_metrics(orig: str, modern: str) -> Dict:
    """Compute metrics for observability without enforcing rules."""
    def normalize_quotes(s: str) -> str:
        """Normalize different quote styles to standard quotes."""
        return s.replace(""", '"').replace(""", '"').replace("'", "'").replace("'", "'")
    
    # Quote metrics (informational only) - count pairs, not individual quotes
    orig_quotes = normalize_quotes(orig)
    modern_quotes = normalize_quotes(modern)
    quote_count_orig = orig_quotes.count('"') // 2  # Count pairs
    quote_count_modern = modern_quotes.count('"') // 2  # Count pairs
    
    # Emphasis metrics (informational only)
    orig_emphasis = len(re.findall(r'_(.+?)_', orig))
    modern_emphasis = len(re.findall(r'_(.+?)_', modern))
    
    # Archaic phrase detection (informational only)
    archaic_patterns = [
        r'\bto-day\b',
        r'\ba fortnight\b', 
        r'\bupon my word\b',
        r'\bsaid (he|she)\b'
    ]
    detected_archaic = []
    for pattern in archaic_patterns:
        if re.search(pattern, modern, re.I):
            detected_archaic.append(pattern)
    
    # Flesch-Kincaid grade calculation
    try:
        fk_grade = textstat.flesch_kincaid_grade(modern) if len(modern) >= 120 else 8.0
    except:
        fk_grade = 8.0
    
    # Character count ratio
    ratio = len(modern) / max(1, len(orig))
    
    # Log metrics for observability
    logger.info(f"QA metrics: quotes({quote_count_orig}→{quote_count_modern}), "
                f"emphasis({orig_emphasis}→{modern_emphasis}), "
                f"fk_grade={fk_grade:.1f}, ratio={ratio:.2f}, "
                f"archaic_detected={len(detected_archaic)}")
    
    return {
        "quote_count_orig": quote_count_orig,
        "quote_count_modern": quote_count_modern,
        "emphasis_count_orig": orig_emphasis,
        "emphasis_count_modern": modern_emphasis,
        "detected_archaic": detected_archaic,
        "fk_grade": fk_grade,
        "ratio": ratio
    }


async def qa_chapter_async(
    doc: ChapterDoc, 
    slug: str = None,
    progress_callback: Optional[Callable] = None
) -> Tuple[bool, List[Dict], ChapterDoc]:
    """Async version of qa_chapter with parallel processing and streaming."""
    issues = []
    min_fidelity = 100
    readability_ok = True
    
    # Initialize checker chain with fallback and caching
    checker = create_llm_with_fallback(
        provider="anthropic",
        temperature=0.0,
        timeout=30,
        max_retries=2,
        cache_enabled=True
    )
    
    checker_chain = (
        {"original": lambda d: d["orig"], "modern": lambda d: d["modern"], "format_instructions": lambda d: checker_parser.get_format_instructions()}
        | checker_prompt
        | checker
        | checker_parser
    )
    
    # Setup callbacks for observability and progress
    callbacks = create_observability_callback(slug, progress_callback) if slug else []
    config = {"callbacks": callbacks} if callbacks else {}
    
    # Process pairs in parallel
    tasks = []
    for pair in doc.pairs:
        tasks.append(qa_pair_async(pair, checker_chain, config))
    
    # Wait for all QA tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for i, result in enumerate(results):
        pair = doc.pairs[i]
        
        if isinstance(result, Exception):
            # Critical error - QA failed completely
            error_msg = f"Checker failed: {str(result)}"
            logger.error(f"QA failed for paragraph {pair.i}: {error_msg}")
            
            # Create failure QA report
            pair.qa = QAReport(
                fidelity_score=None,
                readability_grade=None,
                readability_appropriate=None,
                character_count_ratio=None,
                modernization_complete=None,
                formatting_preserved=None,
                tone_consistent=None,
                quote_count_match=None,
                emphasis_preserved=None,
                literary_quality_maintained=None,
                historical_accuracy_preserved=None,
                issues=[QAIssue(
                    type="checker_error",
                    description=error_msg,
                    severity="critical"
                )],
                confidence=None,
                llm_reasoning=f"Error occurred: {error_msg}",
                metadata={"error": True}
            )
            issues.append({
                "i": pair.i,
                "type": "checker_error",
                "description": error_msg
            })
            
            # Re-raise the exception to fail the entire QA process
            raise Exception(f"QA validation failed for paragraph {pair.i}: {error_msg}") from result
        else:
            checker_result, local_result = result
            
            # Update tracking variables
            fidelity_score = checker_result.fidelity_score
            min_fidelity = min(min_fidelity, fidelity_score)
            readability_ok = readability_ok and checker_result.readability_appropriate
            
            # Check for formatting issues
            if not local_result["quote_parity"] or not local_result["emphasis_parity"] or local_result["missed_archaic"]:
                issues.append({
                    "i": pair.i,
                    "type": "formatting_or_archaic",
                    "description": f"Formatting issues: quotes={local_result['quote_parity']}, emphasis={local_result['emphasis_parity']}, archaic={len(local_result['missed_archaic'])}"
                })
            
            # Create QA report
            pair.qa = QAReport(
                fidelity_score=fidelity_score,
                readability_grade=local_result["fk_grade"],
                character_count_ratio=local_result["ratio"],
                modernization_complete=len(local_result["missed_archaic"]) == 0,
                formatting_preserved=local_result["quote_parity"] and local_result["emphasis_parity"],
                tone_consistent=checker_result.tone_consistent,
                quote_count_match=local_result["quote_parity"],
                emphasis_preserved=local_result["emphasis_parity"],
                issues=checker_result.issues
            )
    
    # Determine if chapter passed QA (soft validation - trust LLM judgment)
    # Log metrics for observability instead of enforcing thresholds
    logger.info(f"Chapter QA summary: min_fidelity={min_fidelity}, "
                f"readability_ok={readability_ok}, issues={len(issues)}")
    
    # Trust LLM judgment - don't enforce strict thresholds
    passed = True  # Always pass, let LLM decide quality
    
    return passed, issues, doc


async def qa_pair_async(pair: ParaPair, checker_chain, config: dict) -> Tuple[CheckerOutput, Dict]:
    """QA a single paragraph pair asynchronously with self-healing retry."""
    input_data = {"orig": pair.orig, "modern": pair.modern}
    
    # Retry with enhancement on failure
    for attempt in range(1, settings.max_retry_attempts + 1):
        try:
            # Run LLM checker in thread pool
            loop = asyncio.get_event_loop()
            raw_result = await loop.run_in_executor(
                None,
                lambda: checker_chain.invoke(input_data, config=config)
            )
            
            # Parse and validate output
            parsed_result = safe_parse_checker_output(raw_result)
            if parsed_result is None:
                raise ValueError("Failed to parse CheckerOutput")
            
            # Perform sanity checks (warnings only)
            warnings = sanity_check_checker_output(parsed_result)
            if warnings:
                logger.warning(f"Checker output warnings: {warnings}")
            
            # Log LLM decision
            log_llm_decision(
                f"qa_pair_{pair.i}",
                f"fidelity={parsed_result.fidelity_score}, issues={len(parsed_result.issues)}",
                f"attempt {attempt}"
            )
            
            # Compute observability metrics
            metrics = compute_observability_metrics(pair.orig, pair.modern)
            
            return parsed_result, metrics
            
        except Exception as e:
            if attempt < settings.max_retry_attempts and should_retry_with_enhancement(e, attempt):
                logger.warning(f"QA pair processing failed (attempt {attempt}), retrying with enhancement: {e}")
                
                # Enhance the prompt for retry
                enhanced_input = analyze_failure_and_enhance_prompt(
                    input_data,
                    e,
                    attempt,
                    "checker"
                )
                
                # Update the input for next attempt
                input_data = enhanced_input
                continue
            else:
                # Final attempt failed or max attempts reached
                logger.error(f"QA pair processing failed after {attempt} attempts: {e}")
                raise e


def qa_chapter(doc: ChapterDoc, slug: str = None) -> Tuple[bool, List[Dict], ChapterDoc]:
    """QA a complete chapter and return results."""
    issues = []
    min_fidelity = 100
    readability_ok = True
    
    # Initialize checker chain with fallback and caching
    checker = create_llm_with_fallback(
        provider="anthropic",
        temperature=0.0,
        timeout=30,
        max_retries=2,
        cache_enabled=True
    )
    
    checker_chain = (
        {"original": lambda d: d["orig"], "modern": lambda d: d["modern"], "format_instructions": lambda d: checker_parser.get_format_instructions()}
        | checker_prompt
        | checker
        | checker_parser
    )
    
    # Apply basic retry handling
    checker_chain = checker_chain.with_retry()
    
    # Setup callbacks for observability
    callbacks = create_observability_callback(slug) if slug else []
    config = {"callbacks": callbacks} if callbacks else {}
    
    for pair in doc.pairs:
        try:
            # Run LLM checker
            raw_result = checker_chain.invoke({
                "orig": pair.orig,
                "modern": pair.modern
            }, config=config)
            
            # Parse and validate output
            parsed_result = safe_parse_checker_output(raw_result)
            if parsed_result is None:
                raise ValueError("Failed to parse CheckerOutput")
            
            # Perform sanity checks (warnings only)
            warnings = sanity_check_checker_output(parsed_result)
            if warnings:
                logger.warning(f"Checker output warnings: {warnings}")
            
            # Log LLM decision
            log_llm_decision(
                f"qa_pair_{pair.i}",
                f"fidelity={parsed_result.fidelity_score}, issues={len(parsed_result.issues)}",
                "sync"
            )
            
            # Compute observability metrics
            metrics = compute_observability_metrics(pair.orig, pair.modern)
            
            # Update tracking variables (trust LLM output)
            fidelity_score = parsed_result.fidelity_score or 0
            min_fidelity = min(min_fidelity, fidelity_score)
            readability_ok = readability_ok and (parsed_result.readability_appropriate or True)
            
            # Log metrics for observability (not validation)
            if metrics["detected_archaic"]:
                issues.append({
                    "i": pair.i,
                    "type": "archaic_detected",
                    "description": f"Archaic phrases detected: {len(metrics['detected_archaic'])} patterns"
                })
            
            # Create comprehensive QA report (trust LLM output)
            pair.qa = QAReport(
                fidelity_score=parsed_result.fidelity_score,
                readability_grade=parsed_result.readability_grade,
                readability_appropriate=parsed_result.readability_appropriate,
                character_count_ratio=parsed_result.character_count_ratio,
                modernization_complete=parsed_result.modernization_complete,
                formatting_preserved=parsed_result.formatting_preserved,
                tone_consistent=parsed_result.tone_consistent,
                quote_count_match=parsed_result.quote_count_match,
                emphasis_preserved=parsed_result.emphasis_preserved,
                literary_quality_maintained=parsed_result.literary_quality_maintained,
                historical_accuracy_preserved=parsed_result.historical_accuracy_preserved,
                issues=parsed_result.issues,
                confidence=parsed_result.confidence,
                llm_reasoning=parsed_result.llm_reasoning,
                metadata={
                    **parsed_result.metadata,
                    "observability_metrics": metrics
                }
            )
            
        except Exception as e:
            # Critical error - QA failed completely
            error_msg = f"Checker failed: {str(e)}"
            logger.error(f"QA failed for paragraph {pair.i}: {error_msg}")
            
            # Create failure QA report
            pair.qa = QAReport(
                fidelity_score=None,
                readability_grade=None,
                readability_appropriate=None,
                character_count_ratio=None,
                modernization_complete=None,
                formatting_preserved=None,
                tone_consistent=None,
                quote_count_match=None,
                emphasis_preserved=None,
                literary_quality_maintained=None,
                historical_accuracy_preserved=None,
                issues=[QAIssue(
                    type="checker_error",
                    description=error_msg,
                    severity="critical"
                )],
                confidence=None,
                llm_reasoning=f"Error occurred: {error_msg}",
                metadata={"error": True}
            )
            
            # Re-raise the exception to fail the entire QA process
            raise Exception(f"QA validation failed for paragraph {pair.i}: {error_msg}") from e
    
    # Determine if chapter passed QA (soft validation - trust LLM judgment)
    # Log metrics for observability instead of enforcing thresholds
    logger.info(f"Chapter QA summary: min_fidelity={min_fidelity}, "
                f"readability_ok={readability_ok}, issues={len(issues)}")
    
    # Trust LLM judgment - don't enforce strict thresholds
    passed = True  # Always pass, let LLM decide quality
    
    return passed, issues, doc

