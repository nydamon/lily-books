"""Pipeline runner for end-to-end book modernization with Langfuse observability."""

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .chains.checker import qa_chapter
from .chains.writer import rewrite_chapter
from .config import ensure_directories, get_config, validate_audio_dependencies
from .graph import compile_graph, qa_text_node_async, rewrite_node_async
from .models import FlowState, PipelineError
from .storage import (
    append_log_entry,
    clear_chapter_failure,
    get_project_paths,
    load_chapter_failures,
    load_state,
    save_chapter_doc,
    save_state,
)
from .utils.auth_validator_openrouter import validate_pipeline_auth
from .utils.debug_logger import log_trace_link, set_trace_context
from .utils.fail_fast import disable_fail_fast, enable_fail_fast, fail_fast_on_exception
from .utils.health_check import create_health_check
from .utils.langfuse_tracer import (
    flush_langfuse,
    trace_node,
    trace_pipeline,
    track_error,
)
from .utils.ssl_fix import fix_ssl_certificates


async def run_pipeline_async(
    slug: str,
    book_id: int,
    chapters: list[int] | None = None,
    progress_callback: Callable | None = None,
) -> dict[str, Any]:
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

    config = get_config()
    # Reset fail-fast state unless explicitly enabled
    disable_fail_fast()
    if config.fail_fast_enabled:
        enable_fail_fast()

    # Fix SSL certificates first
    logger.info("Fixing SSL certificates...")
    ssl_success = fix_ssl_certificates()
    if not ssl_success:
        logger.error("SSL certificate fix failed. Pipeline cannot proceed.")
        return {
            "success": False,
            "error": "SSL certificate fix failed",
            "runtime_sec": time.time() - start_time,
        }

    # Validate authentication
    logger.info("Validating authentication services...")
    auth_success = validate_pipeline_auth()
    if not auth_success:
        logger.error("Authentication validation failed. Pipeline cannot proceed.")
        return {
            "success": False,
            "error": "Authentication validation failed",
            "runtime_sec": time.time() - start_time,
        }

    # Validate audio dependencies if enabled
    try:
        validate_audio_dependencies()
    except (ImportError, ValueError) as e:
        logger.error(f"Audio dependency validation failed: {e}")
        return {
            "success": False,
            "error": f"Audio dependency validation failed: {e}",
            "runtime_sec": time.time() - start_time,
        }

    # Initialize health monitoring
    create_health_check(slug)

    # Start Langfuse tracing session
    with trace_pipeline(
        slug=slug,
        book_id=book_id,
        chapters=chapters,
        metadata={"mode": "async", "parallel": True},
    ) as trace:
        # Set trace context for debug logging
        if trace:
            set_trace_context(trace_id=trace.id if hasattr(trace, "id") else None)
            log_trace_link(f"pipeline_async_{slug}")

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
                "audio_ok": None,
            }

            # Save initial state
            save_state(slug, initial_state)

            # Log pipeline start
            append_log_entry(
                slug,
                {
                    "action": "pipeline_started_async",
                    "book_id": book_id,
                    "chapters": chapters,
                    "start_time": time.time(),
                },
            )

            # Run pipeline steps with async processing
            state = initial_state

            # Step 1: Ingest (synchronous)
            with trace_node(trace, "ingest", slug):
                from .chains.ingest import IngestChain

                raw_text = IngestChain.invoke({"book_id": book_id})
                state["raw_text"] = raw_text

            # Step 2: Chapterize (synchronous)
            with trace_node(trace, "chapterize", slug):
                from .chains.ingest import ChapterizeChain

                chapters_data = ChapterizeChain.invoke({"raw_text": raw_text})
                state["chapters"] = chapters_data

                # Filter chapters if specified
                if chapters is not None:
                    original_count = len(state["chapters"])
                    state["chapters"] = [
                        ch for ch in state["chapters"] if ch.chapter in chapters
                    ]
                    logger.info(
                        f"Filtered chapters: {original_count} -> {len(state['chapters'])} (requested: {chapters})"
                    )

            # Step 3: Rewrite (async with parallel processing)
            with trace_node(
                trace,
                "rewrite",
                slug,
                metadata={"chapter_count": len(state["chapters"])},
            ):
                if progress_callback:
                    progress_callback({"step": "rewrite", "status": "started"})

                state = await rewrite_node_async(state, progress_callback)

            # Step 4: QA Text (async with parallel processing)
            with trace_node(trace, "qa_text", slug):
                if progress_callback:
                    progress_callback({"step": "qa_text", "status": "started"})

                state = await qa_text_node_async(state, progress_callback)

            # Step 5: Metadata Generation (synchronous)
            with trace_node(trace, "metadata", slug):
                if progress_callback:
                    progress_callback({"step": "metadata", "status": "started"})

                from .graph import metadata_node

                state = metadata_node(state)

            # Step 6: Cover Generation (synchronous)
            with trace_node(trace, "cover", slug):
                if progress_callback:
                    progress_callback({"step": "cover", "status": "started"})

                from .graph import cover_node

                state = cover_node(state)

            # Step 7: EPUB (synchronous)
            with trace_node(trace, "epub", slug):
                if progress_callback:
                    progress_callback({"step": "epub", "status": "started"})

                from .graph import epub_node

                state = epub_node(state)

            # Calculate runtime
            runtime_sec = time.time() - start_time

            # Log pipeline completion
            append_log_entry(
                slug,
                {
                    "action": "pipeline_completed_async",
                    "runtime_sec": runtime_sec,
                    "success": True,
                },
            )

            if progress_callback:
                progress_callback({"step": "complete", "status": "completed"})

            # Flush Langfuse events
            flush_langfuse()

            # Prepare result summary
            result_summary = {
                "slug": slug,
                "book_id": book_id,
                "success": True,
                "runtime_sec": runtime_sec,
                "deliverables": {
                    "epub_path": state.get("epub_path"),
                    "cover_path": state.get("cover_path"),
                    "audio_chapters": 0,  # Not processed in this async version
                    "retail_sample": False,
                },
                "qa_summary": {
                    "text_qa_passed": state.get("qa_text_ok", False),
                    "audio_qa_passed": False,
                },
            }

            return result_summary

        except PipelineError as e:
            # Track error in Langfuse
            track_error(
                trace,
                e,
                {
                    "node": e.node,
                    "context": e.context,
                    "slug": slug,
                    "book_id": book_id,
                },
            )

            runtime_sec = time.time() - start_time

            # Log pipeline failure with context
            append_log_entry(
                slug,
                {
                    "action": "pipeline_failed_async",
                    "runtime_sec": runtime_sec,
                    "error": str(e),
                    "node": e.node,
                    "context": e.context,
                },
            )

            if progress_callback:
                progress_callback(
                    {"step": "error", "status": "failed", "error": str(e)}
                )

            flush_langfuse()

            return {
                "slug": slug,
                "book_id": book_id,
                "success": False,
                "runtime_sec": runtime_sec,
                "error": str(e),
                "failed_node": e.node,
                "context": e.context,
                "deliverables": {},
                "qa_summary": {},
            }

        except Exception as e:
            # Track error in Langfuse
            track_error(trace, e, {"slug": slug, "book_id": book_id, "mode": "async"})

            # Fail fast on any exception
            fail_fast_on_exception(e, "run_pipeline_async")

            runtime_sec = time.time() - start_time

            # Log pipeline failure
            append_log_entry(
                slug,
                {
                    "action": "pipeline_failed_async",
                    "runtime_sec": runtime_sec,
                    "error": str(e),
                },
            )

            if progress_callback:
                progress_callback(
                    {"step": "error", "status": "failed", "error": str(e)}
                )

            flush_langfuse()

            return {
                "slug": slug,
                "book_id": book_id,
                "success": False,
                "runtime_sec": runtime_sec,
                "error": str(e),
                "deliverables": {},
                "qa_summary": {},
            }


def run_pipeline(
    slug: str, book_id: int, chapters: list[int] | None = None
) -> dict[str, Any]:
    """Run the complete book modernization pipeline with Langfuse tracing.

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

    # Start Langfuse tracing session
    with trace_pipeline(
        slug=slug,
        book_id=book_id,
        chapters=chapters,
        metadata={"mode": "sync", "parallel": False},
    ) as trace:
        # Set trace context for debug logging
        if trace:
            set_trace_context(trace_id=trace.id if hasattr(trace, "id") else None)
            log_trace_link(f"pipeline_sync_{slug}")

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
                "audio_ok": None,
            }

            # Save initial state
            save_state(slug, initial_state)

            # Log pipeline start
            append_log_entry(
                slug,
                {
                    "action": "pipeline_started",
                    "book_id": book_id,
                    "chapters": chapters,
                    "start_time": time.time(),
                },
            )

            # Store chapter filter in initial state so nodes can access it
            initial_state["requested_chapters"] = chapters

            # Compile and run graph
            graph = compile_graph(slug)
            # Use unique thread_id when filtering chapters to avoid checkpoint conflicts
            thread_id = (
                f"{slug}_chapters_{'_'.join(map(str, chapters))}" if chapters else slug
            )
            logger.info(f"Using thread_id: {thread_id}")

            result = graph.invoke(
                initial_state, config={"configurable": {"thread_id": thread_id}}
            )

            # Calculate runtime
            runtime_sec = time.time() - start_time

            # Log pipeline completion
            append_log_entry(
                slug,
                {
                    "action": "pipeline_completed",
                    "runtime_sec": runtime_sec,
                    "success": True,
                },
            )

            # Flush Langfuse events
            flush_langfuse()

            # Prepare result summary
            result_summary = {
                "slug": slug,
                "book_id": book_id,
                "success": True,
                "runtime_sec": runtime_sec,
                "rewritten": result.get("rewritten", []),
                "deliverables": {
                    "epub_path": result.get("epub_path"),
                    "epub_quality_score": result.get("epub_quality_score"),
                    "audio_chapters": len(result.get("mastered_files", [])),
                    "retail_sample": result.get("package_complete", False),
                },
                "qa_summary": {
                    "text_qa_passed": result.get("qa_text_ok", False),
                    "audio_qa_passed": result.get("audio_ok", False),
                },
            }

            return result_summary

        except PipelineError as e:
            # Track error in Langfuse
            track_error(
                trace,
                e,
                {
                    "node": e.node,
                    "context": e.context,
                    "slug": slug,
                    "book_id": book_id,
                },
            )

            runtime_sec = time.time() - start_time

            # Log pipeline failure with context
            append_log_entry(
                slug,
                {
                    "action": "pipeline_failed",
                    "runtime_sec": runtime_sec,
                    "error": str(e),
                    "node": e.node,
                    "context": e.context,
                },
            )

            flush_langfuse()

            return {
                "slug": slug,
                "book_id": book_id,
                "success": False,
                "runtime_sec": runtime_sec,
                "error": str(e),
                "failed_node": e.node,
                "context": e.context,
                "deliverables": {},
                "qa_summary": {},
            }

        except Exception as e:
            # Track error in Langfuse
            track_error(trace, e, {"slug": slug, "book_id": book_id, "mode": "sync"})

            # Fail fast on any exception
            fail_fast_on_exception(e, "run_pipeline_async")

            runtime_sec = time.time() - start_time

            # Log pipeline failure
            append_log_entry(
                slug,
                {
                    "action": "pipeline_failed",
                    "runtime_sec": runtime_sec,
                    "error": str(e),
                },
            )

            flush_langfuse()

            return {
                "slug": slug,
                "book_id": book_id,
                "success": False,
                "runtime_sec": runtime_sec,
                "error": str(e),
                "deliverables": {},
                "qa_summary": {},
            }


def run_chapter_only(slug: str, chapter_num: int) -> dict[str, Any]:
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
        "message": "Single chapter processing not yet implemented",
    }


def get_pipeline_status(slug: str) -> dict[str, Any]:
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
        "epub": Path(paths["deliverables_ebook"]).exists()
        and len(list(Path(paths["deliverables_ebook"]).glob("*.epub"))) > 0,
        "audio": len(list(Path(paths["audio"]).glob("ch*.wav"))) > 0,
        "mastered": len(list(Path(paths["audio_mastered"]).glob("ch*.mp3"))) > 0,
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
            "epub": len(list(Path(paths["deliverables_ebook"]).glob("*.epub")))
            if Path(paths["deliverables_ebook"]).exists()
            else 0,
            "audio": len(list(Path(paths["audio"]).glob("ch*.wav"))),
            "mastered": len(list(Path(paths["audio_mastered"]).glob("ch*.mp3"))),
        },
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

    print("\nArtifacts:")
    artifacts = status["artifacts"]
    print(f"  EPUB: {artifacts['epub']} files")
    print(f"  Audio: {artifacts['audio']} files")
    print(f"  Mastered: {artifacts['mastered']} files")

    if status["failed_chapters"]:
        print(f"\nFailed Chapters ({status['failed_chapter_count']}):")
        for failure in status["failed_chapters"]:
            print(
                f"  Chapter {failure['chapter']}: {failure['stage']} - {failure['error'][:50]}..."
            )

    print(f"\nRecommendation: {status['recommendation']}")

    if status["recommendation"] == "remediate_chapters":
        print("  Run: remediate_chapters(slug)")
    elif status["recommendation"] == "resume_pipeline":
        print("  Run: resume_pipeline(slug)")
    elif status["recommendation"] == "ready_to_start":
        print("  Run: run_pipeline(slug, book_id)")


def remediate_chapters(
    slug: str, chapter_nums: list[int] | None = None
) -> dict[str, Any]:
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
            "remediated": [],
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
                still_failing.append(
                    {"chapter": chapter_num, "error": "Chapter data not found"}
                )
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
                still_failing.append(
                    {
                        "chapter": chapter_num,
                        "error": f"QA failed with {len(issues)} issues",
                    }
                )

            append_log_entry(
                slug,
                {
                    "action": "chapter_remediated",
                    "chapter": chapter_num,
                    "passed": passed,
                    "issues": len(issues),
                },
            )

        except Exception as e:
            # Fail fast on any exception
            fail_fast_on_exception(e, "remediate_chapters")

            still_failing.append({"chapter": chapter_num, "error": str(e)})
            append_log_entry(
                slug,
                {
                    "action": "chapter_remediation_failed",
                    "chapter": chapter_num,
                    "error": str(e),
                },
            )

    return {
        "slug": slug,
        "success": len(still_failing) == 0,
        "remediated": remediated,
        "still_failing": still_failing,
    }


def resume_pipeline(slug: str) -> dict[str, Any]:
    """Resume a pipeline from its current state."""
    state = load_state(slug)
    if not state:
        raise ValueError(f"Project {slug} not found")

    start_time = time.time()

    try:
        # Compile graph with checkpointing
        graph = compile_graph(slug)

        # Resume from last checkpoint
        result = graph.invoke(state, config={"configurable": {"thread_id": slug}})

        # Calculate runtime
        runtime_sec = time.time() - start_time

        # Log pipeline resumption
        append_log_entry(
            slug,
            {"action": "pipeline_resumed", "runtime_sec": runtime_sec, "success": True},
        )

        return {
            "slug": slug,
            "success": True,
            "runtime_sec": runtime_sec,
            "deliverables": {
                "epub_path": result.get("epub_path"),
                "audio_chapters": len(result.get("mastered_files", [])),
                "retail_sample": result.get("package_complete", False),
            },
            "qa_summary": {
                "text_qa_passed": result.get("qa_text_ok", False),
                "audio_qa_passed": result.get("audio_ok", False),
            },
        }

    except PipelineError as e:
        runtime_sec = time.time() - start_time

        append_log_entry(
            slug,
            {
                "action": "pipeline_resume_failed",
                "runtime_sec": runtime_sec,
                "error": str(e),
                "node": e.node,
                "context": e.context,
            },
        )

        return {
            "slug": slug,
            "success": False,
            "runtime_sec": runtime_sec,
            "error": str(e),
            "failed_node": e.node,
            "context": e.context,
        }

    except Exception as e:
        runtime_sec = time.time() - start_time

        append_log_entry(
            slug,
            {
                "action": "pipeline_resume_failed",
                "runtime_sec": runtime_sec,
                "error": str(e),
            },
        )

        return {
            "slug": slug,
            "success": False,
            "runtime_sec": runtime_sec,
            "error": str(e),
        }
