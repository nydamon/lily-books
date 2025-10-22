"""Writer chain for modernizing text using GPT-4o."""

import asyncio
import logging
from typing import List, Callable, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, BaseOutputParser

from ..models import ChapterSplit, ChapterDoc, ParaPair, WriterOutput
from ..config import settings
from .. import observability
from ..utils import tokens, llm_factory

# Ensure legacy module path works for older tests (src.lily_books...)
import sys as _sys
_sys.modules.setdefault("src.lily_books.chains.writer", _sys.modules[__name__])
from tenacity import stop_after_attempt, wait_exponential, retry_if_exception_type
from ..utils.validators import (
    safe_parse_writer_output, sanity_check_writer_output,
    should_retry_with_enhancement, log_llm_decision
)
from ..utils.retry import analyze_failure_and_enhance_prompt

create_observability_callback = observability.create_observability_callback
create_llm_with_fallback = llm_factory.create_llm_with_fallback
calculate_optimal_batch_size = tokens.calculate_optimal_batch_size
log_token_usage = tokens.log_token_usage
validate_context_window = tokens.validate_context_window

from ..utils.fail_fast import check_llm_response, FAIL_FAST_ENABLED, fail_fast_on_exception
from ..utils.debug_logger import log_step, update_activity, check_for_hang, debug_function, debug_async_function
import re

logger = logging.getLogger(__name__)


def clean_modernized_text(text: str) -> str:
    """Remove metadata prefixes from modernized text."""
    # Remove PARA X [TYPE=...]: prefix
    cleaned = re.sub(r'^PARA \d+ \[TYPE=[^\]]+\]:\s*', '', text, flags=re.MULTILINE)
    return cleaned.strip()


def strip_markdown_code_blocks(text: str) -> str:
    """Remove markdown code blocks and extract JSON from LLM output.

    Some LLMs wrap JSON in ```json ... ``` blocks or add commentary.
    This function extracts the JSON object reliably.
    """
    # Remove markdown code blocks if present
    cleaned = text
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()

    # Find the JSON object - it starts with { and ends with }
    # This handles cases where LLM adds commentary before or after the JSON
    start_idx = cleaned.find('{')
    if start_idx == -1:
        # No JSON found, return original (will likely fail parsing, but that's expected)
        return text.strip()

    # Find the matching closing brace
    brace_count = 0
    end_idx = start_idx
    for i in range(start_idx, len(cleaned)):
        if cleaned[i] == '{':
            brace_count += 1
        elif cleaned[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break

    return cleaned[start_idx:end_idx]


# Ultra-simplified LangChain system prompt for literary modernization (GPT-5-mini compatible)
WRITER_SYSTEM = """Modernize classic text to contemporary English while preserving meaning, dialogue, and structure. Convert _italics_ to <em>italics</em>. Target grade level 7-9. Never add modern concepts.

IMPORTANT: Return ONLY raw JSON without markdown code blocks. Do NOT wrap your response in ```json ... ```"""

WRITER_USER = """Modernize this text to contemporary English:

{joined}

{format_instructions}"""

# Simplified format instructions for GPT-5-mini
GPT5_MINI_FORMAT_INSTRUCTIONS = """Return just the modernized text, one paragraph per line."""

# Create parser and prompt with format instructions
writer_parser = PydanticOutputParser(pydantic_object=WriterOutput)

# Create comprehensive prompt with system and user messages
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

# Create local prompt template as fallback
local_writer_prompt = ChatPromptTemplate.from_messages([
    ("system", WRITER_SYSTEM),
    ("human", WRITER_USER)
])

# Use local prompt directly
writer_prompt = local_writer_prompt

# Module-level chain reference for backward compatibility in tests
writer_chain = None


def _build_writer_chain(trace_name: Optional[str] = None):
    """Construct writer chain and expose it globally for compatibility."""
    global writer_chain

    logger.debug("_build_writer_chain start: writer_chain=%s", type(writer_chain))

    patched_chain = None
    try:
        from unittest.mock import Mock

        if writer_chain is not None and isinstance(writer_chain, Mock):
            patched_chain = writer_chain
    except Exception:
        patched_chain = None

    if patched_chain is not None:
        logger.debug("_build_writer_chain using patched writer_chain (mock)")
        patched_chain.invoke = patched_chain  # type: ignore[attr-defined]
        writer_chain = patched_chain
        return patched_chain

    kwargs = {
        "provider": "openai",
        "temperature": 0.2,
        "timeout": 30,
        "max_retries": 2,
        "cache_enabled": True,
    }
    if trace_name is not None:
        kwargs["trace_name"] = trace_name

    writer_llm = create_llm_with_fallback(**kwargs)

    # Create a function to strip markdown from LLM output before parsing
    def clean_llm_output(llm_response):
        """Strip markdown code blocks from LLM response."""
        # Get the content from the LLM response
        content = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
        # Strip markdown and return for parsing
        return strip_markdown_code_blocks(content)

    chain = (
        {"joined": lambda d: d["joined"], "format_instructions": lambda d: get_format_instructions_for_model()}
        | writer_prompt
        | writer_llm
        | clean_llm_output
        | writer_parser
    )

    writer_chain = chain
    return chain

def get_format_instructions_for_model():
    """Get format instructions for OpenRouter models."""
    return writer_parser.get_format_instructions()

# Removed GPT-5-mini specific functions - using OpenRouter only


def detect_type(para: str) -> str:
    """Classify paragraph type for specialized handling."""
    para = para.strip()
    
    if para.startswith('"') and para.count('"') >= 2:
        return "dialogue"
    if para.startswith("[Illustration"):
        return "illustration"
    if "Dear " in para or "I remain, " in para:
        return "letter"
    return "narrative"


def split_paragraphs(text: str) -> List[str]:
    """Split text into proper paragraphs, handling illustrations and Windows line endings."""
    # Normalize line endings (handle \r\n, \r, and \n)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split on double newlines first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # Further split long paragraphs that might contain multiple sentences
    split_paragraphs = []
    for para in paragraphs:
        if para.startswith('[Illustration'):
            # Keep illustration markers as separate paragraphs
            split_paragraphs.append(para)
        elif len(para) > 500 and '. ' in para:
            # Split long paragraphs on sentence boundaries
            sentences = para.split('. ')
            current_para = sentences[0]
            for sentence in sentences[1:]:
                if len(current_para + '. ' + sentence) > 300:
                    split_paragraphs.append(current_para + '.')
                    current_para = sentence
                else:
                    current_para += '. ' + sentence
            if current_para:
                split_paragraphs.append(current_para)
        else:
            split_paragraphs.append(para)
    
    return split_paragraphs

@debug_async_function
async def rewrite_chapter_async(
    ch: ChapterSplit, 
    slug: str = None, 
    progress_callback: Optional[Callable] = None
) -> ChapterDoc:
    """Async version of rewrite_chapter with parallel processing and streaming."""
    logger.info(f"Starting async rewrite for chapter {ch.chapter} with {len(ch.paragraphs)} paragraphs")
    
    pairs = []
    batch = []
    batch_indices = []
    
    # Split paragraphs properly
    split_paras = split_paragraphs('\n\n'.join(ch.paragraphs))
    
    # Calculate optimal batch size based on token counts
    # Force small batches (max 3 paragraphs) for faster OpenRouter API responses
    batch_size = calculate_optimal_batch_size(
        split_paras, 
        model=settings.openai_model,
        target_utilization=0.2,  # Further reduced to 0.2 for smaller batches
        min_batch_size=1,
        max_batch_size=3  # Reduced to 3 for fastest API responses
    )
    
    logger.info(f"Chapter {ch.chapter}: {len(split_paras)} paragraphs, batch_size={batch_size}")
    
    writer_chain = _build_writer_chain(
        trace_name=f"writer_async_ch{ch.chapter}_{slug}" if slug else f"writer_async_ch{ch.chapter}"
    )

    # Retry handled by manual retry loop in process_batch functions
    # No need for additional .with_retry() layer

    # Setup callbacks for observability and progress
    callbacks = create_observability_callback(slug, progress_callback) if slug else []
    config = {"callbacks": callbacks} if callbacks else {}
    
    # Process paragraphs in parallel batches
    log_step("rewrite_chapter_async.batch_setup", 
             total_paragraphs=len(split_paras), 
             batch_size=batch_size)
    update_activity("rewrite_chapter_async batch setup")
    
    tasks = []
    for i, para in enumerate(split_paras):
        batch.append(f"PARA {i} [TYPE={detect_type(para)}]: {para}")
        batch_indices.append(i)
        
        # Process batch when full or at end
        if len(batch) == batch_size or i == len(split_paras) - 1:
            log_step("rewrite_chapter_async.batch_ready", 
                     batch_number=len(tasks), 
                     batch_size=len(batch))
            logger.info(f"Chapter {ch.chapter}: Creating batch {len(tasks)+1} with {len(batch)} paragraphs")
            update_activity(f"rewrite_chapter_async batch {len(tasks)}")
            joined = "\n\n".join(batch)
            
            # Validate context window before processing
            is_valid, token_count, max_tokens = validate_context_window(
                joined, settings.openai_model, safety_margin=0.3
            )
            
            if not is_valid:
                # Fallback: process smaller batches sequentially
                for single_para, orig_idx in zip(batch, batch_indices):
                    tasks.append(process_single_paragraph_async(
                        single_para,
                        [orig_idx],
                        ch,
                        writer_chain,
                        config,
                        split_paras
                    ))
            else:
                # Process batch asynchronously
                tasks.append(process_batch_async(
                    batch, batch_indices, ch, writer_chain, config, split_paras
                ))
            
            # Reset batch
            batch = []
            batch_indices = []
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    for result in results:
        if isinstance(result, Exception):
            # Handle errors gracefully
            continue
        pairs.extend(result)
    
    return ChapterDoc(chapter=ch.chapter, title=ch.title, pairs=pairs)


async def process_batch_async(
    batch: List[str], 
    batch_indices: List[int], 
    ch: ChapterSplit, 
    writer_chain, 
    config: dict, 
    split_paras: List[str]
) -> List[ParaPair]:
    """Process a batch of paragraphs asynchronously with self-healing retry."""
    logger.info(f"Starting async batch processing for chapter {ch.chapter}, batch size: {len(batch)}")
    
    joined = "\n\n".join(batch)
    
    # Log token usage
    log_token_usage(joined, settings.openai_model, f"rewrite_chapter_{ch.chapter}")
    
    # Retry with enhancement on failure
    for attempt in range(1, settings.max_retry_attempts + 1):
        try:
            logger.info(f"Async batch processing attempt {attempt} for chapter {ch.chapter}")
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            # Use LangChain chain via OpenRouter
            raw_output = await loop.run_in_executor(
                None, 
                lambda: writer_chain.invoke({"joined": joined}, config=config)
            )
            
            # Parse and validate output
            parsed_output = safe_parse_writer_output(raw_output)
            if parsed_output is None:
                raise ValueError("Failed to parse WriterOutput")
            
            # Perform sanity checks (warnings only)
            warnings = sanity_check_writer_output(parsed_output)
            if warnings:
                logger.warning(f"Writer output warnings: {warnings}")
            
            # Log LLM decision
            log_llm_decision(
                f"batch_rewrite_ch{ch.chapter}",
                f"processed {len(parsed_output.paragraphs)} paragraphs",
                f"attempt {attempt}"
            )
            
            # Create pairs
            pairs = []
            for j, paragraph in enumerate(parsed_output.paragraphs):
                if j < len(batch_indices):
                    orig_idx = batch_indices[j]
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=split_paras[orig_idx],
                        modern=clean_modernized_text(paragraph.modern)
                    ))
            
            return pairs
            
        except Exception as e:
            # Fail fast on any exception
            fail_fast_on_exception(e, f"writer_chain processing")
            
            if attempt < settings.max_retry_attempts and should_retry_with_enhancement(e, attempt):
                logger.warning(f"Batch processing failed (attempt {attempt}), retrying with enhancement: {e}")
                
                # Enhance the prompt for retry
                enhanced_input = analyze_failure_and_enhance_prompt(
                    {"joined": joined},
                    e,
                    attempt,
                    "writer"
                )
                
                # Update the input for next attempt
                joined = enhanced_input["joined"]
                continue
            else:
                # Final attempt failed or max attempts reached
                logger.error(f"Batch processing failed after {attempt} attempts: {e}")
                
                # Create pairs with original text and error note
                pairs = []
                for j, orig_idx in enumerate(batch_indices):
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=split_paras[orig_idx],
                        modern=split_paras[orig_idx],
                        notes=f"Modernization failed after {attempt} attempts: {str(e)}"
                    ))
                return pairs
    
    # This should never be reached, but just in case
    return []


async def process_single_paragraph_async(
    single_para: str, 
    batch_indices: List[int], 
    ch: ChapterSplit, 
    writer_chain, 
    config: dict, 
    split_paras: List[str]
) -> List[ParaPair]:
    """Process a single paragraph asynchronously with self-healing retry."""
    # Retry with enhancement on failure
    for attempt in range(1, settings.max_retry_attempts + 1):
        try:
            loop = asyncio.get_event_loop()
            # Use LangChain chain via OpenRouter
            raw_output = await loop.run_in_executor(
                None, 
                lambda: writer_chain.invoke({"joined": single_para}, config=config)
            )
            
            # Parse and validate output
            parsed_output = safe_parse_writer_output(raw_output)
            if parsed_output is None:
                raise ValueError("Failed to parse WriterOutput")
            
            # Perform sanity checks (warnings only)
            warnings = sanity_check_writer_output(parsed_output)
            if warnings:
                logger.warning(f"Single paragraph output warnings: {warnings}")
            
            # Log LLM decision
            log_llm_decision(
                f"single_rewrite_ch{ch.chapter}",
                f"processed {len(parsed_output.paragraphs)} paragraphs",
                f"attempt {attempt}"
            )
            
            # Create pairs
            pairs = []
            for j, paragraph in enumerate(parsed_output.paragraphs):
                if j < len(batch_indices):
                    orig_idx = batch_indices[j]
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=split_paras[orig_idx],
                        modern=clean_modernized_text(paragraph.modern)
                    ))
            return pairs
            
        except Exception as e:
            # Fail fast on any exception
            fail_fast_on_exception(e, f"writer_chain processing")
            
            if attempt < settings.max_retry_attempts and should_retry_with_enhancement(e, attempt):
                logger.warning(f"Single paragraph processing failed (attempt {attempt}), retrying with enhancement: {e}")
                
                # Enhance the prompt for retry
                enhanced_input = analyze_failure_and_enhance_prompt(
                    {"joined": single_para},
                    e,
                    attempt,
                    "writer"
                )
                
                # Update the input for next attempt
                single_para = enhanced_input["joined"]
                continue
            else:
                # Final attempt failed or max attempts reached
                logger.error(f"Single paragraph processing failed after {attempt} attempts: {e}")
                
                # Create pairs with original text and error note
                pairs = []
                for j, orig_idx in enumerate(batch_indices):
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=split_paras[orig_idx],
                        modern=split_paras[orig_idx],
                        notes=f"Modernization failed after {attempt} attempts: {str(e)}"
                    ))
                return pairs
    
    # This should never be reached, but just in case
    return []


def process_batch_sync(
    batch: List[str], 
    batch_indices: List[int], 
    ch: ChapterSplit, 
    writer_chain, 
    config: dict, 
    split_paras: List[str]
) -> List[ParaPair]:
    """Process a batch of paragraphs synchronously with self-healing retry."""
    joined = "\n\n".join(batch)
    
    # Retry with enhancement on failure
    for attempt in range(1, settings.max_retry_attempts + 1):
        try:
            # Use LangChain chain via OpenRouter
            logger.info(f"Processing batch with {len(batch)} paragraphs, attempt {attempt}")
            logger.info("Using LangChain writer chain via OpenRouter")
            raw_output = writer_chain.invoke({"joined": joined}, config=config)
            logger.info(f"LangChain writer chain completed, output type: {type(raw_output)}")
            
            # Fail-fast check for empty response
            from ..utils.fail_fast import check_llm_response
            check_llm_response(raw_output, f"writer_chain batch processing (attempt {attempt})")
            
            # Parse and validate output
            parsed_output = safe_parse_writer_output(raw_output)
            if parsed_output is None:
                raise ValueError("Failed to parse WriterOutput")
            
            # Perform sanity checks (warnings only)
            warnings = sanity_check_writer_output(parsed_output)
            if warnings:
                logger.warning(f"Writer output warnings: {warnings}")
            
            # Log LLM decision
            log_llm_decision(
                f"batch_rewrite_ch{ch.chapter}",
                f"processed {len(parsed_output.paragraphs)} paragraphs",
                f"attempt {attempt}"
            )
            
            # Create pairs
            pairs = []
            for j, paragraph in enumerate(parsed_output.paragraphs):
                if j < len(batch_indices):
                    orig_idx = batch_indices[j]
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=split_paras[orig_idx],
                        modern=clean_modernized_text(paragraph.modern)
                    ))
            
            return pairs
            
        except Exception as e:
            # Fail fast on any exception
            fail_fast_on_exception(e, f"writer_chain processing")
            
            if attempt < settings.max_retry_attempts and should_retry_with_enhancement(e, attempt):
                logger.warning(f"Batch processing failed (attempt {attempt}), retrying with enhancement: {e}")
                
                # Enhance the prompt for retry
                enhanced_input = analyze_failure_and_enhance_prompt(
                    {"joined": joined},
                    e,
                    attempt,
                    "writer"
                )
                
                # Update the input for next attempt
                joined = enhanced_input["joined"]
                continue
            else:
                # Final attempt failed or max attempts reached
                logger.error(f"Batch processing failed after {attempt} attempts: {e}")
                
                # Create pairs with original text and error note
                pairs = []
                for j, orig_idx in enumerate(batch_indices):
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=split_paras[orig_idx],
                        modern=split_paras[orig_idx],
                        notes=f"Modernization failed after {attempt} attempts: {str(e)}"
                    ))
                return pairs
    
    # This should never be reached, but just in case
    return []


def process_single_paragraph_sync(
    single_para: str, 
    batch_indices: List[int], 
    ch: ChapterSplit, 
    writer_chain, 
    config: dict, 
    split_paras: List[str]
) -> List[ParaPair]:
    """Process a single paragraph synchronously with self-healing retry."""
    # Retry with enhancement on failure
    for attempt in range(1, settings.max_retry_attempts + 1):
        try:
            # Use LangChain chain via OpenRouter
            raw_output = writer_chain.invoke({"joined": single_para}, config=config)
            
            # Fail-fast check for empty response
            from ..utils.fail_fast import check_llm_response
            check_llm_response(raw_output, f"writer_chain single paragraph processing (attempt {attempt})")
            
            # Parse and validate output
            parsed_output = safe_parse_writer_output(raw_output)
            if parsed_output is None:
                raise ValueError("Failed to parse WriterOutput")
            
            # Perform sanity checks (warnings only)
            warnings = sanity_check_writer_output(parsed_output)
            if warnings:
                logger.warning(f"Single paragraph output warnings: {warnings}")
            
            # Log LLM decision
            log_llm_decision(
                f"single_rewrite_ch{ch.chapter}",
                f"processed {len(parsed_output.paragraphs)} paragraphs",
                f"attempt {attempt}"
            )
            
            # Create pairs
            pairs = []
            for j, paragraph in enumerate(parsed_output.paragraphs):
                if j < len(batch_indices):
                    orig_idx = batch_indices[j]
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=split_paras[orig_idx],
                        modern=clean_modernized_text(paragraph.modern)
                    ))
            return pairs
            
        except Exception as e:
            # Fail fast on any exception
            fail_fast_on_exception(e, f"writer_chain processing")
            
            if attempt < settings.max_retry_attempts and should_retry_with_enhancement(e, attempt):
                logger.warning(f"Single paragraph processing failed (attempt {attempt}), retrying with enhancement: {e}")
                
                # Enhance the prompt for retry
                enhanced_input = analyze_failure_and_enhance_prompt(
                    {"joined": single_para},
                    e,
                    attempt,
                    "writer"
                )
                
                # Update the input for next attempt
                single_para = enhanced_input["joined"]
                continue
            else:
                # Final attempt failed or max attempts reached
                logger.error(f"Single paragraph processing failed after {attempt} attempts: {e}")
                
                # Create pairs with original text and error note
                pairs = []
                for j, orig_idx in enumerate(batch_indices):
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=split_paras[orig_idx],
                        modern=split_paras[orig_idx],
                        notes=f"Modernization failed after {attempt} attempts: {str(e)}"
                    ))
                return pairs
    
    # This should never be reached, but just in case
    return []


def rewrite_chapter(ch: ChapterSplit, slug: str = None) -> ChapterDoc:
    """Rewrite a chapter using batched processing."""
    pairs = []
    batch = []
    batch_indices = []
    
    # Split paragraphs properly
    split_paras = split_paragraphs('\n\n'.join(ch.paragraphs))
    
    # Calculate optimal batch size based on token counts
    # Force small batches (max 3 paragraphs) for faster OpenRouter API responses
    batch_size = calculate_optimal_batch_size(
        split_paras, 
        model=settings.openai_model,
        target_utilization=0.2,  # Further reduced to 0.2 for smaller batches
        min_batch_size=1,
        max_batch_size=3  # Reduced to 3 for fastest API responses
    )
    
    logger.info(f"Chapter {ch.chapter}: {len(split_paras)} paragraphs, batch_size={batch_size}")
    
    writer_chain = _build_writer_chain(
        trace_name=f"writer_sync_ch{ch.chapter}_{slug}" if slug else f"writer_sync_ch{ch.chapter}"
    )

    # Retry handled by manual retry loop in process_batch functions
    # No need for additional .with_retry() layer

    # Setup callbacks for observability
    callbacks = create_observability_callback(slug) if slug else []
    config = {"callbacks": callbacks} if callbacks else {}
    
    for i, para in enumerate(split_paras):
        batch.append(f"PARA {i} [TYPE={detect_type(para)}]: {para}")
        batch_indices.append(i)
        
        # Process batch when full or at end
        if len(batch) == batch_size or i == len(split_paras) - 1:
            joined = "\n\n".join(batch)
            
            # Validate context window before processing
            is_valid, token_count, max_tokens = validate_context_window(
                joined, settings.openai_model, safety_margin=0.3
            )
            
            if not is_valid:
                # Process smaller batches with retry
                for single_para, orig_idx in zip(batch, batch_indices):
                    batch_pairs = process_single_paragraph_sync(
                        single_para,
                        [orig_idx],
                        ch,
                        writer_chain,
                        config,
                        split_paras
                    )
                    pairs.extend(batch_pairs)
                
                # Reset batch and continue
                batch = []
                batch_indices = []
                continue
            
            # Log token usage
            log_token_usage(joined, settings.openai_model, f"rewrite_chapter_{ch.chapter}")
            
            # Process batch with retry
            batch_pairs = process_batch_sync(
                batch, batch_indices, ch, writer_chain, config, split_paras
            )
            pairs.extend(batch_pairs)
            
            # Reset batch
            batch = []
            batch_indices = []
    
    return ChapterDoc(chapter=ch.chapter, title=ch.title, pairs=pairs)
