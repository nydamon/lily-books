"""Pipeline runner for end-to-end book modernization."""

import time
from typing import Dict, Any, Optional
from pathlib import Path

from .graph import compile_graph
from .models import FlowState
from .storage import save_state, load_state, append_log_entry, get_project_paths
from .config import ensure_directories


def run_pipeline(slug: str, book_id: int, chapters: Optional[list[int]] = None) -> Dict[str, Any]:
    """Run the complete book modernization pipeline.
    
    Args:
        slug: Project identifier
        book_id: Gutendex book ID
        chapters: Optional list of chapter numbers to process (None for all)
    
    Returns:
        Dictionary with results and metadata
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
            "chapters": None,
            "rewritten": None,
            "qa_text_ok": None,
            "audio_ok": None,
            "errors": []
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
        graph = compile_graph()
        result = graph.invoke(initial_state)
        
        # Calculate runtime
        runtime_sec = time.time() - start_time
        
        # Log pipeline completion
        append_log_entry(slug, {
            "action": "pipeline_completed",
            "runtime_sec": runtime_sec,
            "success": len(result.get("errors", [])) == 0,
            "errors": result.get("errors", [])
        })
        
        # Prepare result summary
        result_summary = {
            "slug": slug,
            "book_id": book_id,
            "success": len(result.get("errors", [])) == 0,
            "runtime_sec": runtime_sec,
            "errors": result.get("errors", []),
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
            "errors": [str(e)],
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
    
    return {
        "slug": slug,
        "state": state,
        "progress": progress,
        "completed_steps": sum(progress.values()),
        "total_steps": len(progress)
    }


def resume_pipeline(slug: str) -> Dict[str, Any]:
    """Resume a pipeline from its current state."""
    state = load_state(slug)
    if not state:
        raise ValueError(f"Project {slug} not found")
    
    # TODO: Implement resume logic
    # This would involve determining the last completed step and continuing from there
    
    return {
        "slug": slug,
        "message": "Pipeline resume not yet implemented",
        "current_state": state
    }

