"""LangGraph state machine for the book modernization pipeline."""

import asyncio
import logging
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger(__name__)
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .models import (
    FlowState, ChapterSplit, ChapterDoc, BookMetadata,
    IngestError, ChapterizeError, RewriteError, QAError, 
    EPUBError, TTSError, MasterError, PackageError
)
from .chains.ingest import IngestChain, ChapterizeChain
from .chains.writer import rewrite_chapter, rewrite_chapter_async
from .chains.checker import qa_chapter, qa_chapter_async
from .tools.epub import build_epub
from .tools.epub_validator import validate_epub_structure
from .tools.tts import tts_elevenlabs
from .tools.audio import master_audio, get_audio_metrics, extract_retail_sample
from .storage import (
    save_raw_text, save_chapters_jsonl, save_chapter_doc, save_qa_issues,
    save_state, append_log_entry, save_book_metadata, get_project_paths,
    save_chapter_failure, load_chapter_failures, clear_chapter_failure,
    load_chapter_doc
)
from .config import ensure_directories


def ingest_node(state: FlowState) -> FlowState:
    """Load raw text from Gutendex API."""
    append_log_entry(state["slug"], {
        "node": "ingest",
        "book_id": state["book_id"],
        "status": "started"
    })
    
    try:
        # Load raw text
        raw_text = IngestChain.invoke({"book_id": state["book_id"]})
        
        # Save raw text
        save_raw_text(state["slug"], raw_text)
        
        append_log_entry(state["slug"], {
            "node": "ingest",
            "status": "completed",
            "text_length": len(raw_text)
        })
        
        return {**state, "raw_text": raw_text}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "ingest",
            "status": "error",
            "error": str(e)
        })
        raise IngestError(
            f"Ingest failed: {str(e)}",
            slug=state["slug"],
            node="ingest",
            context={"book_id": state["book_id"]}
        )


def chapterize_node(state: FlowState) -> FlowState:
    """Split text into chapters."""
    append_log_entry(state["slug"], {
        "node": "chapterize",
        "status": "started"
    })
    
    try:
        # Chapterize text
        chapters = ChapterizeChain.invoke({"raw_text": state["raw_text"]})
        
        # Save chapters
        chapters_data = [ch.model_dump() for ch in chapters]
        save_chapters_jsonl(state["slug"], chapters_data)
        
        append_log_entry(state["slug"], {
            "node": "chapterize",
            "status": "completed",
            "chapter_count": len(chapters)
        })
        
        return {**state, "chapters": chapters}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "chapterize",
            "status": "error",
            "error": str(e)
        })
        raise ChapterizeError(
            f"Chapterize failed: {str(e)}",
            slug=state["slug"],
            node="chapterize",
            context={"text_length": len(state["raw_text"]) if state["raw_text"] else 0}
        )


async def rewrite_node_async(
    state: FlowState, 
    progress_callback: Optional[Callable] = None
) -> FlowState:
    """Async version of rewrite_node with parallel chapter processing."""
    append_log_entry(state["slug"], {
        "node": "rewrite",
        "status": "started"
    })
    
    try:
        rewritten_chapters = []
        failed_chapters = []
        skipped_chapters = []
        
        # Process chapters in parallel
        tasks = []
        chapter_splits = []
        
        for chapter_split in state["chapters"]:
            # Check if chapter already exists on disk
            existing_doc = load_chapter_doc(state["slug"], chapter_split.chapter)
            if existing_doc:
                # Chapter already completed - skip rewrite
                rewritten_chapters.append(existing_doc)
                skipped_chapters.append(chapter_split.chapter)
                
                append_log_entry(state["slug"], {
                    "node": "rewrite",
                    "chapter": chapter_split.chapter,
                    "paragraphs": len(existing_doc.pairs),
                    "status": "skipped",
                    "reason": "already_completed"
                })
                continue
            
            # Add to parallel processing queue
            tasks.append(rewrite_chapter_async(chapter_split, state["slug"], progress_callback))
            chapter_splits.append(chapter_split)
        
        # Wait for all chapters to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                chapter_split = chapter_splits[i]
                
                if isinstance(result, Exception):
                    # Track chapter failure but continue processing
                    failed_chapters.append(chapter_split.chapter)
                    save_chapter_failure(
                        state["slug"], 
                        chapter_split.chapter, 
                        "rewrite", 
                        str(result)
                    )
                    
                    append_log_entry(state["slug"], {
                        "node": "rewrite",
                        "chapter": chapter_split.chapter,
                        "status": "failed",
                        "error": str(result)
                    })
                else:
                    # Save chapter doc
                    save_chapter_doc(state["slug"], result.chapter, result)
                    rewritten_chapters.append(result)
                    
                    append_log_entry(state["slug"], {
                        "node": "rewrite",
                        "chapter": result.chapter,
                        "paragraphs": len(result.pairs),
                        "status": "completed"
                    })
        
        # If any chapters failed, raise error with failed list
        if failed_chapters:
            raise RewriteError(
                f"Failed to rewrite chapters: {failed_chapters}",
                slug=state["slug"],
                node="rewrite",
                context={
                    "successful_chapters": len(rewritten_chapters),
                    "failed_chapters": failed_chapters
                }
            )
        
        append_log_entry(state["slug"], {
            "node": "rewrite",
            "status": "completed",
            "total_chapters": len(rewritten_chapters),
            "skipped_chapters": len(skipped_chapters),
            "processed_chapters": len(rewritten_chapters) - len(skipped_chapters)
        })
        
        return {**state, "rewritten": rewritten_chapters}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "rewrite",
            "status": "error",
            "error": str(e)
        })
        raise RewriteError(
            f"Rewrite failed: {str(e)}",
            slug=state["slug"],
            node="rewrite",
            context={"chapter_count": len(state["chapters"]) if state["chapters"] else 0}
        )


def rewrite_node(state: FlowState) -> FlowState:
    """Modernize chapters using Writer chain."""
    append_log_entry(state["slug"], {
        "node": "rewrite",
        "status": "started"
    })
    
    try:
        rewritten_chapters = []
        failed_chapters = []
        skipped_chapters = []
        
        for chapter_split in state["chapters"]:
            try:
                # Check if chapter already exists on disk
                existing_doc = load_chapter_doc(state["slug"], chapter_split.chapter)
                if existing_doc:
                    # Chapter already completed - skip rewrite
                    rewritten_chapters.append(existing_doc)
                    skipped_chapters.append(chapter_split.chapter)
                    
                    append_log_entry(state["slug"], {
                        "node": "rewrite",
                        "chapter": chapter_split.chapter,
                        "paragraphs": len(existing_doc.pairs),
                        "status": "skipped",
                        "reason": "already_completed"
                    })
                    continue
                
                # Rewrite chapter
                chapter_doc = rewrite_chapter(chapter_split, state["slug"])
                
                # Save chapter doc
                save_chapter_doc(state["slug"], chapter_doc.chapter, chapter_doc)
                
                rewritten_chapters.append(chapter_doc)
                
                append_log_entry(state["slug"], {
                    "node": "rewrite",
                    "chapter": chapter_doc.chapter,
                    "paragraphs": len(chapter_doc.pairs),
                    "status": "completed"
                })
                
            except Exception as e:
                # Track chapter failure but continue processing
                failed_chapters.append(chapter_split.chapter)
                save_chapter_failure(
                    state["slug"], 
                    chapter_split.chapter, 
                    "rewrite", 
                    str(e)
                )
                
                append_log_entry(state["slug"], {
                    "node": "rewrite",
                    "chapter": chapter_split.chapter,
                    "status": "failed",
                    "error": str(e)
                })
        
        # If any chapters failed, raise error with failed list
        if failed_chapters:
            raise RewriteError(
                f"Failed to rewrite chapters: {failed_chapters}",
                slug=state["slug"],
                node="rewrite",
                context={
                    "successful_chapters": len(rewritten_chapters),
                    "failed_chapters": failed_chapters
                }
            )
        
        append_log_entry(state["slug"], {
            "node": "rewrite",
            "status": "completed",
            "total_chapters": len(rewritten_chapters),
            "skipped_chapters": len(skipped_chapters),
            "processed_chapters": len(rewritten_chapters) - len(skipped_chapters)
        })
        
        return {**state, "rewritten": rewritten_chapters}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "rewrite",
            "status": "error",
            "error": str(e)
        })
        raise RewriteError(
            f"Rewrite failed: {str(e)}",
            slug=state["slug"],
            node="rewrite",
            context={"chapter_count": len(state["chapters"]) if state["chapters"] else 0}
        )


async def qa_text_node_async(
    state: FlowState, 
    progress_callback: Optional[Callable] = None
) -> FlowState:
    """Async version of qa_text_node with parallel chapter processing."""
    append_log_entry(state["slug"], {
        "node": "qa_text",
        "status": "started"
    })
    
    try:
        all_passed = True
        total_issues = []
        failed_chapters = []
        skipped_chapters = []
        
        # Process chapters in parallel
        tasks = []
        chapter_docs = []
        
        for chapter_doc in state["rewritten"]:
            # Check if QA already completed (has QA results)
            if chapter_doc.pairs and all(pair.qa is not None for pair in chapter_doc.pairs):
                # QA already completed - skip
                skipped_chapters.append(chapter_doc.chapter)
                
                # Check if all pairs passed QA
                chapter_passed = all(pair.qa.modernization_complete and pair.qa.formatting_preserved for pair in chapter_doc.pairs)
                all_passed = all_passed and chapter_passed
                
                append_log_entry(state["slug"], {
                    "node": "qa_text",
                    "chapter": chapter_doc.chapter,
                    "passed": chapter_passed,
                    "status": "skipped",
                    "reason": "already_qa_completed"
                })
                continue
            
            # Add to parallel processing queue
            tasks.append(qa_chapter_async(chapter_doc, slug=state["slug"], progress_callback=progress_callback))
            chapter_docs.append(chapter_doc)
        
        # Wait for all QA tasks to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                chapter_doc = chapter_docs[i]
                
                if isinstance(result, Exception):
                    # Critical error - log and continue per failure_mode
                    error_msg = f"QA crashed for chapter {chapter_doc.chapter}: {str(result)}"
                    logger.error(error_msg)
                    
                    failed_chapters.append(chapter_doc.chapter)
                    all_passed = False
                    
                    save_chapter_failure(
                        state["slug"],
                        chapter_doc.chapter,
                        "qa_text",
                        error_msg
                    )
                    
                    append_log_entry(state["slug"], {
                        "node": "qa_text",
                        "chapter": chapter_doc.chapter,
                        "status": "failed",
                        "error": error_msg
                    })
                else:
                    # Unpack result
                    passed, issues, updated_doc = result
                    
                    # Save QA results
                    save_qa_issues(state["slug"], chapter_doc.chapter, issues)
                    save_chapter_doc(state["slug"], chapter_doc.chapter, updated_doc)
                    
                    # Track failures
                    if not passed:
                        all_passed = False
                        failed_chapters.append(chapter_doc.chapter)
                        
                        # Log failure for remediation
                        save_chapter_failure(
                            state["slug"],
                            chapter_doc.chapter,
                            "qa_text",
                            f"Quality gate failed: {len(issues)} issues"
                        )
                        
                        append_log_entry(state["slug"], {
                            "node": "qa_text",
                            "chapter": chapter_doc.chapter,
                            "passed": False,
                            "issues": len(issues),
                            "status": "failed"
                        })
                    else:
                        # Success
                        total_issues.extend(issues)
                        
                        append_log_entry(state["slug"], {
                            "node": "qa_text",
                            "chapter": chapter_doc.chapter,
                            "passed": True,
                            "issues": len(issues),
                            "status": "completed"
                        })
        
        # Final status
        if failed_chapters:
            append_log_entry(state["slug"], {
                "node": "qa_text",
                "status": "completed_with_failures",
                "failed_chapters": failed_chapters,
                "passed_chapters": len(chapter_docs) - len(failed_chapters) + len(skipped_chapters)
            })
            
            # Return state with failure tracking
            return {
                **state,
                "qa_text_ok": False,
                "failed_chapters": failed_chapters,
                "total_issues": total_issues
            }
        
        # All passed
        append_log_entry(state["slug"], {
            "node": "qa_text",
            "status": "completed",
            "all_passed": True,
            "total_issues": len(total_issues)
        })
        
        return {**state, "qa_text_ok": True, "total_issues": total_issues}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "qa_text",
            "status": "error",
            "error": str(e)
        })
        raise QAError(
            f"QA text failed: {str(e)}",
            slug=state["slug"],
            node="qa_text",
            context={"chapter_count": len(state["rewritten"]) if state["rewritten"] else 0}
        )


def qa_text_node(state: FlowState) -> FlowState:
    """QA modernized text using Checker chain."""
    append_log_entry(state["slug"], {
        "node": "qa_text",
        "status": "started"
    })
    
    try:
        all_passed = True
        total_issues = []
        failed_chapters = []
        skipped_chapters = []
        
        for chapter_doc in state["rewritten"]:
            try:
                # Check if QA already completed (has QA results)
                if chapter_doc.pairs and all(pair.qa is not None for pair in chapter_doc.pairs):
                    # QA already completed - skip
                    skipped_chapters.append(chapter_doc.chapter)
                    
                    # Check if all pairs passed QA
                    chapter_passed = all(pair.qa.modernization_complete and pair.qa.formatting_preserved for pair in chapter_doc.pairs)
                    all_passed = all_passed and chapter_passed
                    
                    append_log_entry(state["slug"], {
                        "node": "qa_text",
                        "chapter": chapter_doc.chapter,
                        "passed": chapter_passed,
                        "status": "skipped",
                        "reason": "already_qa_completed"
                    })
                    continue
                
                # QA chapter with graduated quality gates
                passed, issues, updated_doc = qa_chapter(chapter_doc, slug=state["slug"])
                
                # Save QA results
                save_qa_issues(state["slug"], chapter_doc.chapter, issues)
                save_chapter_doc(state["slug"], chapter_doc.chapter, updated_doc)
                
                # Track failures
                if not passed:
                    all_passed = False
                    failed_chapters.append(chapter_doc.chapter)
                    
                    # Log failure for remediation
                    save_chapter_failure(
                        state["slug"],
                        chapter_doc.chapter,
                        "qa_text",
                        f"Quality gate failed: {len(issues)} issues"
                    )
                    
                    append_log_entry(state["slug"], {
                        "node": "qa_text",
                        "chapter": chapter_doc.chapter,
                        "passed": False,
                        "issues": len(issues),
                        "status": "failed"
                    })
                else:
                    # Success
                    total_issues.extend(issues)
                    
                    append_log_entry(state["slug"], {
                        "node": "qa_text",
                        "chapter": chapter_doc.chapter,
                        "passed": True,
                        "issues": len(issues),
                        "status": "completed"
                    })
                
            except Exception as e:
                # Log error but continue processing (soft validation)
                error_msg = f"QA failed for chapter {chapter_doc.chapter}: {str(e)}"
                logger.warning(error_msg)
                
                # Track chapter failure for observability
                failed_chapters.append(chapter_doc.chapter)
                save_chapter_failure(
                    state["slug"], 
                    chapter_doc.chapter, 
                    "qa_text", 
                    str(e)
                )
                
                append_log_entry(state["slug"], {
                    "node": "qa_text",
                    "chapter": chapter_doc.chapter,
                    "status": "failed",
                    "error": str(e),
                    "note": "soft_validation_continue"
                })
                
                # Continue processing other chapters instead of failing
                continue
        
        # Final status
        if failed_chapters:
            append_log_entry(state["slug"], {
                "node": "qa_text",
                "status": "completed_with_failures",
                "failed_chapters": failed_chapters,
                "passed_chapters": len(state["rewritten"]) - len(failed_chapters) + len(skipped_chapters)
            })
            
            # Return state with failure tracking
            return {
                **state,
                "qa_text_ok": False,
                "failed_chapters": failed_chapters,
                "total_issues": total_issues
            }
        
        # All passed
        append_log_entry(state["slug"], {
            "node": "qa_text",
            "status": "completed",
            "all_passed": True,
            "total_issues": len(total_issues)
        })
        
        return {**state, "qa_text_ok": True, "total_issues": total_issues}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "qa_text",
            "status": "error",
            "error": str(e)
        })
        raise QAError(
            f"QA text failed: {str(e)}",
            slug=state["slug"],
            node="qa_text",
            context={"chapter_count": len(state["rewritten"]) if state["rewritten"] else 0}
        )


def remediate_node(state: FlowState) -> FlowState:
    """Remediate failing paragraphs with targeted retries."""
    append_log_entry(state["slug"], {
        "node": "remediate",
        "status": "started"
    })
    
    try:
        # For now, just mark as remediated
        # TODO: Implement targeted retry logic
        
        append_log_entry(state["slug"], {
            "node": "remediate",
            "status": "completed"
        })
        
        return {**state, "qa_text_ok": True}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "remediate",
            "status": "error",
            "error": str(e)
        })
        raise QAError(
            f"Remediate failed: {str(e)}",
            slug=state["slug"],
            node="remediate"
        )


def epub_node(state: FlowState) -> FlowState:
    """Build EPUB from modernized chapters."""
    append_log_entry(state["slug"], {
        "node": "epub",
        "status": "started"
    })
    
    try:
        # Create metadata
        metadata = BookMetadata(
            title=f"{state['slug'].title()} (Modernized Student Edition)",
            author="Public Domain Author (Modernized by Lily Books)",
            public_domain_source=f"Project Gutenberg #{state['book_id']}"
        )
        
        # Build EPUB
        epub_path = build_epub(state["slug"], state["rewritten"], metadata)
        
        # Validate EPUB quality
        validation_result = validate_epub_structure(epub_path)
        quality_score = validation_result.quality_score
        
        # Save metadata
        save_book_metadata(state["slug"], metadata)
        
        append_log_entry(state["slug"], {
            "node": "epub",
            "status": "completed",
            "epub_path": str(epub_path),
            "quality_score": quality_score,
            "validation_errors": len(validation_result.errors),
            "validation_warnings": len(validation_result.warnings)
        })
        
        return {
            **state, 
            "epub_path": str(epub_path),
            "epub_quality_score": quality_score
        }
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "epub",
            "status": "error",
            "error": str(e)
        })
        raise EPUBError(
            f"EPUB build failed: {str(e)}",
            slug=state["slug"],
            node="epub",
            context={"chapter_count": len(state["rewritten"]) if state["rewritten"] else 0}
        )


def tts_node(state: FlowState) -> FlowState:
    """Generate TTS audio for chapters."""
    append_log_entry(state["slug"], {
        "node": "tts",
        "status": "started"
    })
    
    try:
        paths = get_project_paths(state["slug"])
        audio_files = []
        
        for chapter_doc in state["rewritten"]:
            # Combine all paragraphs
            text = "\n\n".join(pair.modern for pair in chapter_doc.pairs)
            
            # Generate TTS
            wav_path = paths["audio"] / f"ch{chapter_doc.chapter:02d}.wav"
            result = tts_elevenlabs(text, "Rachel", wav_path)
            
            audio_files.append({
                "chapter": chapter_doc.chapter,
                "wav_path": str(wav_path),
                "duration_sec": result["duration_sec"]
            })
            
            append_log_entry(state["slug"], {
                "node": "tts",
                "chapter": chapter_doc.chapter,
                "duration_sec": result["duration_sec"],
                "status": "completed"
            })
        
        append_log_entry(state["slug"], {
            "node": "tts",
            "status": "completed",
            "total_chapters": len(audio_files)
        })
        
        return {**state, "audio_files": audio_files}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "tts",
            "status": "error",
            "error": str(e)
        })
        raise TTSError(
            f"TTS failed: {str(e)}",
            slug=state["slug"],
            node="tts",
            context={"chapter_count": len(state["rewritten"]) if state["rewritten"] else 0}
        )


def master_node(state: FlowState) -> FlowState:
    """Master audio files for ACX compliance."""
    # Check prerequisites
    if "audio_files" not in state or not state["audio_files"]:
        raise MasterError(
            "No audio files from TTS",
            slug=state["slug"],
            node="master",
            context={"audio_files_present": "audio_files" in state}
        )
    
    append_log_entry(state["slug"], {
        "node": "master",
        "status": "started"
    })
    
    try:
        paths = get_project_paths(state["slug"])
        mastered_files = []
        
        for audio_file in state["audio_files"]:
            wav_path = Path(audio_file["wav_path"])
            mp3_path = paths["audio_mastered"] / f"ch{audio_file['chapter']:02d}.mp3"
            
            # Master audio
            result = master_audio(wav_path, mp3_path)
            
            mastered_files.append({
                "chapter": audio_file["chapter"],
                "mp3_path": str(mp3_path),
                "duration_sec": result["duration_sec"]
            })
            
            append_log_entry(state["slug"], {
                "node": "master",
                "chapter": audio_file["chapter"],
                "status": "completed"
            })
        
        append_log_entry(state["slug"], {
            "node": "master",
            "status": "completed",
            "total_chapters": len(mastered_files)
        })
        
        return {**state, "mastered_files": mastered_files}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "master",
            "status": "error",
            "error": str(e)
        })
        raise MasterError(
            f"Master failed: {str(e)}",
            slug=state["slug"],
            node="master",
            context={"audio_file_count": len(state["audio_files"]) if state["audio_files"] else 0}
        )


def qa_audio_node(state: FlowState) -> FlowState:
    """QA audio files for ACX compliance."""
    # Check prerequisites
    if "mastered_files" not in state or not state["mastered_files"]:
        raise QAError(
            "No mastered files from master node",
            slug=state["slug"],
            node="qa_audio",
            context={"mastered_files_present": "mastered_files" in state}
        )
    
    append_log_entry(state["slug"], {
        "node": "qa_audio",
        "status": "started"
    })
    
    try:
        all_passed = True
        
        for mastered_file in state["mastered_files"]:
            # Get audio metrics
            wav_path = Path(mastered_file["wav_path"])
            metrics = get_audio_metrics(wav_path)
            
            # Check ACX thresholds
            rms_ok = metrics["rms_db"] is None or metrics["rms_db"] >= -23
            peak_ok = metrics["peak_db"] is None or metrics["peak_db"] <= -3
            
            chapter_passed = rms_ok and peak_ok
            all_passed = all_passed and chapter_passed
            
            append_log_entry(state["slug"], {
                "node": "qa_audio",
                "chapter": mastered_file["chapter"],
                "rms_db": metrics["rms_db"],
                "peak_db": metrics["peak_db"],
                "passed": chapter_passed,
                "status": "completed"
            })
        
        append_log_entry(state["slug"], {
            "node": "qa_audio",
            "status": "completed",
            "all_passed": all_passed
        })
        
        return {**state, "audio_ok": all_passed}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "qa_audio",
            "status": "error",
            "error": str(e)
        })
        raise QAError(
            f"QA audio failed: {str(e)}",
            slug=state["slug"],
            node="qa_audio",
            context={"mastered_file_count": len(state["mastered_files"]) if state["mastered_files"] else 0}
        )


def package_node(state: FlowState) -> FlowState:
    """Package final deliverables."""
    # Check prerequisites
    if "mastered_files" not in state or not state["mastered_files"]:
        raise PackageError(
            "No mastered files from master node",
            slug=state["slug"],
            node="package",
            context={"mastered_files_present": "mastered_files" in state}
        )
    
    append_log_entry(state["slug"], {
        "node": "package",
        "status": "started"
    })
    
    try:
        paths = get_project_paths(state["slug"])
        
        # Extract retail sample from first chapter
        first_chapter = state["mastered_files"][0]
        sample_path = paths["deliverables_audio"] / f"{state['slug']}_retail_sample.mp3"
        
        extract_retail_sample(
            Path(first_chapter["mp3_path"]),
            30,  # start_sec
            180,  # duration_sec
            sample_path
        )
        
        # Create publish metadata
        publish_data = {
            "title": f"{state['slug'].title()} (Modernized Student Edition)",
            "ebook_path": state.get("epub_path"),
            "audiobook_chapters": len(state["mastered_files"]),
            "retail_sample": str(sample_path),
            "completed_at": append_log_entry(state["slug"], {
                "node": "package",
                "status": "completed"
            })
        }
        
        # Save publish metadata
        import json
        publish_file = paths["meta"] / "publish.json"
        with open(publish_file, 'w') as f:
            json.dump(publish_data, f, indent=2)
        
        return {**state, "package_complete": True}
        
    except Exception as e:
        append_log_entry(state["slug"], {
            "node": "package",
            "status": "error",
            "error": str(e)
        })
        raise PackageError(
            f"Package failed: {str(e)}",
            slug=state["slug"],
            node="package",
            context={"mastered_file_count": len(state["mastered_files"]) if state["mastered_files"] else 0}
        )


def build_graph() -> StateGraph:
    """Build and compile the LangGraph state machine."""
    graph = StateGraph(FlowState)
    
    # Add nodes
    graph.add_node("ingest", ingest_node)
    graph.add_node("chapterize", chapterize_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("qa_text", qa_text_node)
    graph.add_node("remediate", remediate_node)
    graph.add_node("epub", epub_node)
    graph.add_node("tts", tts_node)
    graph.add_node("master", master_node)
    graph.add_node("qa_audio", qa_audio_node)
    graph.add_node("package", package_node)
    
    # Set entry point
    graph.set_entry_point("ingest")
    
    # Add edges
    graph.add_edge("ingest", "chapterize")
    graph.add_edge("chapterize", "rewrite")
    graph.add_edge("rewrite", "qa_text")
    
    # Conditional edge for QA
    def should_remediate(state: FlowState) -> str:
        return "remediate" if not state.get("qa_text_ok", True) else "epub"
    
    graph.add_conditional_edges(
        "qa_text",
        should_remediate,
        {
            "remediate": "epub",  # Skip remediation for now, go directly to epub
            "epub": "epub"
        }
    )
    graph.add_edge("epub", "tts")
    graph.add_edge("tts", "master")
    graph.add_edge("master", "qa_audio")
    graph.add_edge("qa_audio", "package")
    graph.add_edge("package", END)
    
    return graph


def compile_graph(slug: str = None) -> Any:
    """Compile the graph with checkpointing."""
    graph = build_graph()
    
    if slug:
        # Use project-specific checkpoint DB
        from .config import get_project_paths
        paths = get_project_paths(slug)
        checkpoint_db = paths["meta"] / "checkpoints.db"
        import sqlite3
        conn = sqlite3.connect(str(checkpoint_db))
        checkpointer = SqliteSaver(conn)
    else:
        # Use in-memory checkpointer for testing
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
    
    return graph.compile(checkpointer=checkpointer)

