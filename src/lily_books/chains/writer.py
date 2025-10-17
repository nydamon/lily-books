"""Writer chain for modernizing text using GPT-4o."""

from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..models import ChapterSplit, ChapterDoc, ParaPair
from ..config import settings


# Prompt templates from spec
WRITER_SYSTEM = """You are a literary modernization specialist for 19th-century English.
MANDATORY:
- Preserve quotation marks, dialogue structure, character names.
- Preserve legal terms (entail, rectory).
- Preserve emphasis markers _like this_.
- No modern idioms not implied by the original.
TARGET: FK grade 7–9; 110–140% length."""

WRITER_USER = """Modernize each paragraph; keep order and counts identical.
For TYPE=dialogue: preserve all quotes. For TYPE=letter: keep formal structure and asides.
If input is [Illustration], return exactly [Illustration].

Text:
{joined}

Constraints: quote/italics parity; 'entail' not replaced; avoid 'kick out' (prefer 'turn out').

Respond JSON array only: [{{"modern":"..."}}, ...]
"""

writer_prompt = PromptTemplate.from_template(WRITER_USER)


def detect_type(para: str) -> str:
    """Classify paragraph type for specialized handling."""
    para = para.strip()
    
    if para.startswith('"') and para.count('"') >= 2:
        return "dialogue"
    if para == "[Illustration]":
        return "illustration"
    if "Dear " in para or "I remain, " in para:
        return "letter"
    return "narrative"


def rewrite_chapter(ch: ChapterSplit) -> ChapterDoc:
    """Rewrite a chapter using batched processing."""
    pairs = []
    batch = []
    batch_indices = []
    batch_size = 8
    
    # Initialize LLM chain
    writer = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.2,
        api_key=settings.openai_api_key
    )
    writer_chain = (
        {"joined": lambda d: d["joined"]} 
        | writer_prompt 
        | writer 
        | JsonOutputParser()
    )
    
    for i, para in enumerate(ch.paragraphs):
        batch.append(f"PARA {i} [TYPE={detect_type(para)}]: {para}")
        batch_indices.append(i)
        
        # Process batch when full or at end
        if len(batch) == batch_size or i == len(ch.paragraphs) - 1:
            joined = "\n\n".join(batch)
            
            try:
                output = writer_chain.invoke({"joined": joined})
                
                for j, item in enumerate(output):
                    if j < len(batch_indices):
                        orig_idx = batch_indices[j]
                        pairs.append(ParaPair(
                            i=orig_idx,
                            para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                            orig=ch.paragraphs[orig_idx],
                            modern=item["modern"]
                        ))
                        
            except Exception as e:
                # Fallback: keep original text
                for j, orig_idx in enumerate(batch_indices):
                    pairs.append(ParaPair(
                        i=orig_idx,
                        para_id=f"ch{ch.chapter:02d}_para{orig_idx:03d}",
                        orig=ch.paragraphs[orig_idx],
                        modern=ch.paragraphs[orig_idx],
                        notes=f"Error during modernization: {str(e)}"
                    ))
            
            # Reset batch
            batch = []
            batch_indices = []
    
    return ChapterDoc(chapter=ch.chapter, title=ch.title, pairs=pairs)

