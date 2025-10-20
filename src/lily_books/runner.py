"""Pipeline runner for end-to-end book modernization."""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from .graph import compile_graph, rewrite_node_async, qa_text_node_async
from .models import FlowState, PipelineError
from .storage import (
    save_state, load_state, append_log_entry, get_project_paths,
    load_chapter_failures, clear_chapter_failure, load_chapter_doc, save_chapter_doc
)
from .config import ensure_directories
from .chains.writer import rewrite_chapter
from .chains.checker import qa_chapter


async def run_pipeline_async(
    slug: str, 
    book_id: int, 
    chapters: Optional[List[int]] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """Run the complete book modernization pipeline asynchronously with parallel processing.
    
    Args:
        slug: Project identifier
        book_id: Gutendex book ID
        chapters: Optional list of chapter numbers to process (None for all)
        progress_callback: Optional callback for progress updates
    
    Returns:
        Dictionary with results and metadata
        
    Note:
        This async version processes chapters in parallel for better performance.
        Timeouts should be enforced externally (systemd, k8s, or calling code)
        as Unix signals don't work on Windows and can't be nested.
    """
    start_time = time.time()
    
    try:
        # Ensure directories exist
        ensure_directories(slug)
        
        # Initialize state
        initial_state: FlowState = {
            "slug": slug,
            "book_id": book_id,
            "paths": {},
            "raw_text": None,
            "chapters": None,
            "rewritten": None,
            "qa_text_ok": None,
            "audio_ok": None
        }
        
        # Save initial state
        save_state(slug, initial_state)
        
        # Log pipeline start
        append_log_entry(slug, {
            "action": "pipeline_started_async",
            "book_id": book_id,
            "chapters": chapters,
            "start_time": time.time()
        })
        
        # Run pipeline steps with async processing
        state = initial_state
        
        # Step 1: Ingest (synchronous)
        from .chains.ingest import IngestChain
        raw_text = IngestChain.invoke({"book_id": book_id})
        state["raw_text"] = raw_text
        
        # Step 2: Chapterize (synchronous)
        from .chains.ingest import ChapterizeChain
        chapters_data = ChapterizeChain.invoke({"raw_text": raw_text})
        state["chapters"] = chapters_data
        
        # Filter chapters if specified
        if chapters is not None:
            state["chapters"] = [ch for ch in state["chapters"] if ch.chapter in chapters]
        
        # Step 3: Rewrite (async with parallel processing)
        if progress_callback:
            progress_callback({"step": "rewrite", "status": "started"})
        
        state = await rewrite_node_async(state, progress_callback)
        
        # Step 4: QA Text (async with parallel processing)
        if progress_callback:
            progress_callback({"step": "qa_text", "status": "started"})
        
        state = await qa_text_node_async(state, progress_callback)
        
        # Step 5: EPUB (synchronous)
        if progress_callback:
            progress_callback({"step": "epub", "status": "started"})
        
        from .graph import epub_node
        state = epub_node(state)
        
        # Calculate runtime
        runtime_sec = time.time() - start_time
        
        # Log pipeline completion
        append_log_entry(slug, {
            "action": "pipeline_completed_async",
            "runtime_sec": runtime_sec,
            "success": True
        })
        
        if progress_callback:
            progress_callback({"step": "complete", "status": "completed"})
        
        # Prepare result summary
        result_summary = {
            "slug": slug,
            "book_id": book_id,
            "success": True,
            "runtime_sec": runtime_sec,
            "deliverables": {
                "epub_path": state.get("epub_path"),
                "audio_chapters": 0,  # Not processed in this async version
                "retail_sample": False
            },
            "qa_summary": {
                "text_qa_passed": state.get("qa_text_ok", False),
                "audio_qa_passed": False
            }
        }
        
        return result_summary
        
    except PipelineError as e:
        runtime_sec = time.time() - start_time
        
        # Log pipeline failure with context
        append_log_entry(slug, {
            "action": "pipeline_failed_async",
            "runtime_sec": runtime_sec,
            "error": str(e),
            "node": e.node,
            "context": e.context
        })
        
        if progress_callback:
            progress_callback({"step": "error", "status": "failed", "error": str(e)})
        
        return {
            "slug": slug,
            "book_id": book_id,
            "success": False,
            "runtime_sec": runtime_sec,
            "error": str(e),
            "failed_node": e.node,
            "context": e.context,
            "deliverables": {},
            "qa_summary": {}
        }
    
    except Exception as e:
        runtime_sec = time.time() - start_time
        
        # Log pipeline failure
        append_log_entry(slug, {
            "action": "pipeline_failed_async",
            "runtime_sec": runtime_sec,
            "error": str(e)
        })
        
        if progress_callback:
            progress_callback({"step": "error", "status": "failed", "error": str(e)})
        
        return {
            "slug": slug,
            "book_id": book_id,
            "success": False,
            "runtime_sec": runtime_sec,
            "error": str(e),
            "deliverables": {},
            "qa_summary": {}
        }


def run_pipeline(slug: str, book_id: int, chapters: Optional[list[int]] = None) -> Dict[str, Any]:
    """Run the complete book modernization pipeline.
    
    Args:
        slug: Project identifier
        book_id: Gutendex book ID
        chapters: Optional list of chapter numbers to process (None for all)
    
    Returns:
        Dictionary with results and metadata
        
    Note:
        Timeouts should be enforced externally (systemd, k8s, or calling code)
        as Unix signals don't work on Windows and can't be nested.
    """
    start_time = time.time()
    
    try:
        # Ensure directories exist
        ensure_directories(slug)
        
        # Initialize state
        initial_state: FlowState = {
            "slug": slug,
            "book_id": book_id,
            "paths": {},
            "raw_text": None,
            "chapters": None,
            "rewritten": None,
            "qa_text_ok": None,
            "audio_ok": None
        }
        
        # Save initial state
        save_state(slug, initial_state)
        
        # Log pipeline start
        append_log_entry(slug, {
            "action": "pipeline_started",
            "book_id": book_id,
            "chapters": chapters,
            "start_time": time.time()
        })
        
        # Compile and run graph
        graph = compile_graph(slug)
        result = graph.invoke(initial_state, config={"configurable": {"thread_id": slug}})
        
        # Calculate runtime
        runtime_sec = time.time() - start_time
        
        # Log pipeline completion
        append_log_entry(slug, {
            "action": "pipeline_completed",
            "runtime_sec": runtime_sec,
            "success": True
        })
        
        # Prepare result summary
        result_summary = {
            "slug": slug,
            "book_id": book_id,
            "success": True,
            "runtime_sec": runtime_sec,
            "deliverables": {
                "epub_path": result.get("epub_path"),
                "audio_chapters": len(result.get("mastered_files", [])),
                "retail_sample": result.get("package_complete", False)
            },
            "qa_summary": {
                "text_qa_passed": result.get("qa_text_ok", False),
                "audio_qa_passed": result.get("audio_ok", False)
            }
        }
        
        return result_summary
        
    except PipelineError as e:
        runtime_sec = time.time() - start_time
        
        # Log pipeline failure with context
        append_log_entry(slug, {
            "action": "pipeline_failed",
            "runtime_sec": runtime_sec,
            "error": str(e),
            "node": e.node,
            "context": e.context
        })
        
        return {
            "slug": slug,
            "book_id": book_id,
            "success": False,
            "runtime_sec": runtime_sec,
            "error": str(e),
            "failed_node": e.node,
            "context": e.context,
            "deliverables": {},
            "qa_summary": {}
        }
    
    except Exception as e:
        runtime_sec = time.time() - start_time
        
        # Log pipeline failure
        append_log_entry(slug, {
            "action": "pipeline_failed",
            "runtime_sec": runtime_sec,
            "error": str(e)
        })
        
        return {
            "slug": slug,
            "book_id": book_id,
            "success": False,
            "runtime_sec": runtime_sec,
            "error": str(e),
            "deliverables": {},
            "qa_summary": {}
        }


def run_chapter_only(slug: str, chapter_num: int) -> Dict[str, Any]:
    """Run pipeline for a single chapter only."""
    # Load existing state
    state = load_state(slug)
    if not state:
        raise ValueError(f"Project {slug} not found. Run full pipeline first.")
    
    # TODO: Implement single chapter processing
    # This would involve running only the rewrite and QA steps for the specified chapter
    
    return {
        "slug": slug,
        "chapter": chapter_num,
        "success": True,
        "message": "Single chapter processing not yet implemented"
    }


def get_pipeline_status(slug: str) -> Dict[str, Any]:
    """Get current pipeline status and progress."""
    state = load_state(slug)
    if not state:
        return {"status": "not_found"}
    
    paths = get_project_paths(slug)
    
    # Check which files exist to determine progress
    progress = {
        "ingest": Path(paths["source"] / "original.txt").exists(),
        "chapterize": Path(paths["work"] / "chapters.jsonl").exists(),
        "rewrite": len(list(Path(paths["rewrite"]).glob("ch*.json"))) > 0,
        "epub": Path(paths["deliverables_ebook"]).exists() and len(list(Path(paths["deliverables_ebook"]).glob("*.epub"))) > 0,
        "audio": len(list(Path(paths["audio"]).glob("ch*.wav"))) > 0,
        "mastered": len(list(Path(paths["audio_mastered"]).glob("ch*.mp3"))) > 0
    }
    
    # Load failed chapters
    failed_chapters = load_chapter_failures(slug)
    
    # Check checkpoint DB
    checkpoint_db = paths["meta"] / "checkpoints.db"
    checkpoint_exists = checkpoint_db.exists()
    
    # Determine last successful node based on progress
    last_node = None
    if progress["mastered"]:
        last_node = "master"
    elif progress["audio"]:
        last_node = "tts"
    elif progress["epub"]:
        last_node = "epub"
    elif progress["rewrite"]:
        last_node = "rewrite"
    elif progress["chapterize"]:
        last_node = "chapterize"
    elif progress["ingest"]:
        last_node = "ingest"
    
    # Determine recommendation
    recommendation = "ready_to_start"
    if failed_chapters:
        recommendation = "remediate_chapters"
    elif checkpoint_exists and last_node:
        recommendation = "resume_pipeline"
    elif progress["mastered"]:
        recommendation = "complete"
    
    return {
        "slug": slug,
        "status": "active" if state else "not_found",
        "state": state,
        "progress": progress,
        "completed_steps": sum(progress.values()),
        "total_steps": len(progress),
        "last_node": last_node,
        "checkpoint_exists": checkpoint_exists,
        "failed_chapters": failed_chapters,
        "failed_chapter_count": len(failed_chapters),
        "recommendation": recommendation,
        "artifacts": {
            "epub": len(list(Path(paths["deliverables_ebook"]).glob("*.epub"))) if Path(paths["deliverables_ebook"]).exists() else 0,
            "audio": len(list(Path(paths["audio"]).glob("ch*.wav"))),
            "mastered": len(list(Path(paths["audio_mastered"]).glob("ch*.mp3")))
        }
    }


def print_status(slug: str) -> None:
    """Print pipeline status in a readable format."""
    status = get_pipeline_status(slug)
    
    if status["status"] == "not_found":
        print(f"Project '{slug}' not found")
        return
    
    print(f"\n=== Pipeline Status: {slug} ===")
    print(f"Status: {status['status']}")
    print(f"Last Node: {status['last_node'] or 'none'}")
    print(f"Checkpoint: {'exists' if status['checkpoint_exists'] else 'none'}")
    print(f"Progress: {status['completed_steps']}/{status['total_steps']} steps")
    
    print(f"\nArtifacts:")
    artifacts = status['artifacts']
    print(f"  EPUB: {artifacts['epub']} files")
    print(f"  Audio: {artifacts['audio']} files")
    print(f"  Mastered: {artifacts['mastered']} files")
    
    if status['failed_chapters']:
        print(f"\nFailed Chapters ({status['failed_chapter_count']}):")
        for failure in status['failed_chapters']:
            print(f"  Chapter {failure['chapter']}: {failure['stage']} - {failure['error'][:50]}...")
    
    print(f"\nRecommendation: {status['recommendation']}")
    
    if status['recommendation'] == "remediate_chapters":
        print("  Run: remediate_chapters(slug)")
    elif status['recommendation'] == "resume_pipeline":
        print("  Run: resume_pipeline(slug)")
    elif status['recommendation'] == "ready_to_start":
        print("  Run: run_pipeline(slug, book_id)")


def remediate_chapters(slug: str, chapter_nums: Optional[List[int]] = None) -> Dict[str, Any]:
    """Remediate failed chapters by rerunning rewrite+QA for specific chapters."""
    # Load failed chapters if none specified
    if chapter_nums is None:
        failures = load_chapter_failures(slug)
        chapter_nums = [f["chapter"] for f in failures]
    
    if not chapter_nums:
        return {
            "slug": slug,
            "success": True,
            "message": "No chapters to remediate",
            "remediated": []
        }
    
    remediated = []
    still_failing = []
    
    for chapter_num in chapter_nums:
        try:
            # Load chapter split (need to reconstruct from chapters.jsonl)
            from .storage import load_chapters_jsonl
            chapters_data = load_chapters_jsonl(slug)
            
            # Find the chapter data
            chapter_data = None
            for ch_data in chapters_data:
                if ch_data["chapter"] == chapter_num:
                    chapter_data = ch_data
                    break
            
            if not chapter_data:
                still_failing.append({"chapter": chapter_num, "error": "Chapter data not found"})
                continue
            
            # Convert to ChapterSplit object
            from .models import ChapterSplit
            chapter_split = ChapterSplit(**chapter_data)
            
            # Rerun rewrite
            chapter_doc = rewrite_chapter(chapter_split, slug)
            save_chapter_doc(slug, chapter_doc.chapter, chapter_doc)
            
            # Rerun QA
            passed, issues, updated_doc = qa_chapter(chapter_doc, slug=slug)
            save_chapter_doc(slug, chapter_doc.chapter, updated_doc)
            
            # Clear from failures if successful
            if passed:
                clear_chapter_failure(slug, chapter_num)
                remediated.append(chapter_num)
            else:
                still_failing.append({"chapter": chapter_num, "error": f"QA failed with {len(issues)} issues"})
            
            append_log_entry(slug, {
                "action": "chapter_remediated",
                "chapter": chapter_num,
                "passed": passed,
                "issues": len(issues)
            })
            
        except Exception as e:
            still_failing.append({"chapter": chapter_num, "error": str(e)})
            append_log_entry(slug, {
                "action": "chapter_remediation_failed",
                "chapter": chapter_num,
                "error": str(e)
            })
    
    return {
        "slug": slug,
        "success": len(still_failing) == 0,
        "remediated": remediated,
        "still_failing": still_failing
    }


def resume_pipeline(slug: str) -> Dict[str, Any]:
    """Resume a pipeline from its current state."""
    state = load_state(slug)
    if not state:
        raise ValueError(f"Project {slug} not found")
    
    start_time = time.time()
    
    try:
        # Compile graph with checkpointing
        graph = compile_graph(slug)
        
        # Resume from last checkpoint
        result = graph.invoke(
            state, 
            config={"configurable": {"thread_id": slug}}
        )
        
        # Calculate runtime
        runtime_sec = time.time() - start_time
        
        # Log pipeline resumption
        append_log_entry(slug, {
            "action": "pipeline_resumed",
            "runtime_sec": runtime_sec,
            "success": True
        })
        
        return {
            "slug": slug,
            "success": True,
            "runtime_sec": runtime_sec,
            "deliverables": {
                "epub_path": result.get("epub_path"),
                "audio_chapters": len(result.get("mastered_files", [])),
                "retail_sample": result.get("package_complete", False)
            },
            "qa_summary": {
                "text_qa_passed": result.get("qa_text_ok", False),
                "audio_qa_passed": result.get("audio_ok", False)
            }
        }
        
    except PipelineError as e:
        runtime_sec = time.time() - start_time
        
        append_log_entry(slug, {
            "action": "pipeline_resume_failed",
            "runtime_sec": runtime_sec,
            "error": str(e),
            "node": e.node,
            "context": e.context
        })
        
        return {
            "slug": slug,
            "success": False,
            "runtime_sec": runtime_sec,
            "error": str(e),
            "failed_node": e.node,
            "context": e.context
        }
    
    except Exception as e:
        runtime_sec = time.time() - start_time
        
        append_log_entry(slug, {
            "action": "pipeline_resume_failed",
            "runtime_sec": runtime_sec,
            "error": str(e)
        })
        
        return {
            "slug": slug,
            "success": False,
            "runtime_sec": runtime_sec,
            "error": str(e)
        }

