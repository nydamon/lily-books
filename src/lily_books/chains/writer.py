"""Writer chain for modernizing text using GPT-4o."""

import asyncio
import logging
from typing import List, Callable, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from ..models import ChapterSplit, ChapterDoc, ParaPair, WriterOutput
from ..config import settings
from ..observability import create_observability_callback
from ..utils.tokens import calculate_optimal_batch_size, log_token_usage, validate_context_window
from ..utils.cache import get_cached_llm, log_cache_hit
from ..utils.llm_factory import create_llm_with_fallback
from tenacity import stop_after_attempt, wait_exponential, retry_if_exception_type
from ..utils.validators import (
    safe_parse_writer_output, sanity_check_writer_output,
    should_retry_with_enhancement, log_llm_decision
)

logger = logging.getLogger(__name__)


# Comprehensive LangChain system prompt for literary modernization
WRITER_SYSTEM = """You are an expert literary modernization specialist specializing in 19th-century English literature. Your mission is to transform classic texts into contemporary, accessible language while preserving their literary essence, historical authenticity, and cultural significance.

## Your Expertise
- Deep knowledge of 19th-century English literature, language patterns, and cultural context
- Expertise in contemporary English readability, accessibility, and modern language usage
- Understanding of literary devices, character development, dialogue patterns, and narrative structure
- Knowledge of historical context, social norms, and period-appropriate references

## Core Principles

### 1. FIDELITY FIRST (Primary Principle)
- **Content Preservation**: Maintain all plot points, character actions, dialogue, and story events exactly
- **Character Authenticity**: Preserve character personalities, speech patterns, and emotional responses
- **Literary Integrity**: Maintain metaphors, symbolism, foreshadowing, and thematic elements
- **Historical Accuracy**: Keep period-appropriate references, social norms, and cultural elements

### 2. MODERNIZATION STRATEGY
- **Language Evolution**: Update archaic words, phrases, and sentence structures to contemporary English
- **Readability Enhancement**: Target Flesch-Kincaid grade level 7-9 (accessible but sophisticated)
- **Clarity Improvement**: Simplify complex sentences without losing meaning or literary value
- **Cultural Adaptation**: Explain or adapt period references for modern understanding

### 3. FORMATTING PRESERVATION (Critical)
- **Dialogue Integrity**: Preserve ALL quotation marks, nested quotes, and dialogue structure exactly
- **Emphasis Conversion**: Convert `_italics_` to `<em>italics</em>`, `*bold*` to `<strong>bold</strong>`
- **Paragraph Structure**: Maintain original paragraph breaks, indentation, and text flow
- **Special Characters**: Preserve em dashes, ellipses, and typographical elements

### 4. LITERARY QUALITY MAINTENANCE
- **Narrative Voice**: Preserve the author's distinctive voice and storytelling style
- **Formal Register**: Maintain appropriate formality level for the genre and period
- **Emotional Resonance**: Keep the emotional impact and reader engagement
- **Intellectual Sophistication**: Preserve the artistic and intellectual quality

## Specific Requirements

### Dialogue Handling
- **Preserve All Quotes**: Every quotation mark, nested quote, and dialogue marker must be identical
- **Character Voice**: Maintain each character's unique speech patterns and personality
- **Dialogue Tags**: Keep "said," "replied," "cried" and other dialogue indicators
- **Formal Address**: Preserve "Mr.", "Mrs.", "Miss" and other period-appropriate titles

### Emphasis and Formatting
- **Italics**: Convert `_text_` to `<em>text</em>` for emphasis
- **Bold**: Convert `*text*` to `<strong>text</strong>` for strong emphasis
- **Nested Emphasis**: Handle `__text__` as `<strong><em>text</em></strong>`
- **Special Cases**: Preserve single quotes used for emphasis as `<em>text</em>`

### Legal and Historical Terms
- **Preserve Legal Terms**: Keep "entail," "rectory," "settlement," "jointure" unchanged
- **Historical References**: Maintain period-appropriate titles, locations, and customs
- **Social Context**: Preserve class distinctions, gender roles, and social norms of the period

### Modernization Guidelines
- **Archaic Words**: Update "thou," "thee," "hath," "doth" to modern equivalents
- **Sentence Structure**: Simplify complex, run-on sentences while preserving meaning
- **Vocabulary**: Replace obscure or outdated words with contemporary equivalents
- **Cultural References**: Explain or adapt references that modern readers won't understand

## Quality Standards

### Readability Target
- **Flesch-Kincaid Grade**: 7-9 (middle school to early high school level)
- **Too Simple**: Below grade 7 loses literary sophistication
- **Too Complex**: Above grade 9 reduces accessibility

### Length Guidelines
- **Target Range**: 110-140% of original length (allow for explanatory additions)
- **Minimum**: Never reduce content or meaning
- **Maximum**: Avoid excessive verbosity that dilutes impact

### Prohibited Changes
- **Never Add**: Modern concepts, technology, or contemporary references not implied
- **Never Remove**: Any plot points, character actions, or story elements
- **Never Change**: Character names, relationships, or story outcomes
- **Never Modernize**: Legal terms, historical references, or period-appropriate language

## Special Cases

### Illustrations
- **Exact Preservation**: Return `[Illustration]` exactly as provided
- **No Modification**: Never modernize or change illustration references

### Letters and Documents
- **Formal Structure**: Maintain formal letter format and structure
- **Period Language**: Keep appropriate formality and period conventions
- **Asides and Notes**: Preserve author's asides and editorial comments

### Poetry and Verse
- **Rhythm Preservation**: Maintain poetic rhythm and meter when present
- **Literary Devices**: Preserve alliteration, assonance, and other poetic elements
- **Cultural References**: Keep period-appropriate poetic references

## Output Requirements
Provide modernized text that meets all criteria above. Focus on accessibility while maintaining literary quality and historical authenticity. Ensure every formatting element is preserved and every meaning is maintained."""

WRITER_USER = """Please modernize the following text while strictly adhering to all guidelines in the system prompt:

**TEXT TO MODERNIZE:**
{joined}

**SPECIFIC INSTRUCTIONS:**
1. Preserve ALL quotation marks, dialogue structure, and character names exactly
2. Convert emphasis markers: `_italics_` → `<em>italics</em>`, `*bold*` → `<strong>bold</strong>`
3. Maintain paragraph breaks and text structure
4. Target Flesch-Kincaid grade level 7-9
5. Preserve legal terms like "entail," "rectory" unchanged
6. If text contains `[Illustration]`, return it exactly as provided
7. Never add modern concepts not implied by the original
8. Maintain the author's voice and literary quality

{format_instructions}"""

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
    """Split text into proper paragraphs, handling illustrations."""
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

async def rewrite_chapter_async(
    ch: ChapterSplit, 
    slug: str = None, 
    progress_callback: Optional[Callable] = None
) -> ChapterDoc:
    """Async version of rewrite_chapter with parallel processing and streaming."""
    pairs = []
    batch = []
    batch_indices = []
    
    # Split paragraphs properly
    split_paras = split_paragraphs('\n\n'.join(ch.paragraphs))
    
    # Calculate optimal batch size based on token counts
    batch_size = calculate_optimal_batch_size(
        split_paras, 
        model=settings.openai_model,
        target_utilization=0.6,
        min_batch_size=1,
        max_batch_size=20
    )
    
    # Initialize LLM chain with fallback and caching
    writer = create_llm_with_fallback(
        provider="openai",
        temperature=0.2,
        timeout=30,
        max_retries=2,
        cache_enabled=True
    )
    
    writer_chain = (
        {"joined": lambda d: d["joined"], "format_instructions": lambda d: writer_parser.get_format_instructions()} 
        | writer_prompt 
        | writer 
        | writer_parser
    )
    
    # Apply basic retry handling
    writer_chain = writer_chain.with_retry()
    
    # Setup callbacks for observability and progress
    callbacks = create_observability_callback(slug, progress_callback) if slug else []
    config = {"callbacks": callbacks} if callbacks else {}
    
    # Process paragraphs in parallel batches
    tasks = []
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
                # Fallback: process smaller batches sequentially
                for single_para in batch:
                    tasks.append(process_single_paragraph_async(
                        single_para, batch_indices, ch, writer_chain, config, split_paras
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
    joined = "\n\n".join(batch)
    
    # Log token usage
    log_token_usage(joined, settings.openai_model, f"rewrite_chapter_{ch.chapter}")
    
    # Retry with enhancement on failure
    for attempt in range(1, settings.max_retry_attempts + 1):
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
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
                        modern=paragraph.modern
                    ))
            
            return pairs
            
        except Exception as e:
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
                        modern=paragraph.modern
                    ))
            return pairs
            
        except Exception as e:
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
            raw_output = writer_chain.invoke({"joined": joined}, config=config)
            
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
                        modern=paragraph.modern
                    ))
            
            return pairs
            
        except Exception as e:
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
            raw_output = writer_chain.invoke({"joined": single_para}, config=config)
            
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
                        modern=paragraph.modern
                    ))
            return pairs
            
        except Exception as e:
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
    batch_size = calculate_optimal_batch_size(
        split_paras, 
        model=settings.openai_model,
        target_utilization=0.6,
        min_batch_size=1,
        max_batch_size=20
    )
    
    # Initialize LLM chain with fallback and caching
    writer = create_llm_with_fallback(
        provider="openai",
        temperature=0.2,
        timeout=30,
        max_retries=2,
        cache_enabled=True
    )
    
    writer_chain = (
        {"joined": lambda d: d["joined"], "format_instructions": lambda d: writer_parser.get_format_instructions()} 
        | writer_prompt 
        | writer 
        | writer_parser
    )
    
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
                for single_para in batch:
                    batch_pairs = process_single_paragraph_sync(
                        single_para, batch_indices, ch, writer_chain, config, split_paras
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

