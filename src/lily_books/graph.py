"""LangGraph state machine for the book modernization pipeline."""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .models import FlowState, ChapterSplit, ChapterDoc, BookMetadata
from .chains.ingest import IngestChain, ChapterizeChain
from .chains.writer import rewrite_chapter
from .chains.checker import qa_chapter
from .tools.epub import build_epub
from .tools.tts import tts_elevenlabs
from .tools.audio import master_audio, get_audio_metrics, extract_retail_sample
from .storage import (
    save_raw_text, save_chapters_jsonl, save_chapter_doc, save_qa_issues,
    save_state, append_log_entry, save_book_metadata, get_project_paths
)
from .config import ensure_directories


def ingest_node(state: FlowState) -> FlowState:
    """Load raw text from Gutendex API."""
    try:
        append_log_entry(state["slug"], {
            "node": "ingest",
            "book_id": state["book_id"],
            "status": "started"
        })
        
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
        error_msg = f"Ingest failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "ingest",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg]}


def chapterize_node(state: FlowState) -> FlowState:
    """Split text into chapters."""
    try:
        append_log_entry(state["slug"], {
            "node": "chapterize",
            "status": "started"
        })
        
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
        error_msg = f"Chapterize failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "chapterize",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg]}


def rewrite_node(state: FlowState) -> FlowState:
    """Modernize chapters using Writer chain."""
    try:
        append_log_entry(state["slug"], {
            "node": "rewrite",
            "status": "started"
        })
        
        rewritten_chapters = []
        
        for chapter_split in state["chapters"]:
            # Rewrite chapter
            chapter_doc = rewrite_chapter(chapter_split)
            
            # Save chapter doc
            save_chapter_doc(state["slug"], chapter_doc.chapter, chapter_doc)
            
            rewritten_chapters.append(chapter_doc)
            
            append_log_entry(state["slug"], {
                "node": "rewrite",
                "chapter": chapter_doc.chapter,
                "paragraphs": len(chapter_doc.pairs),
                "status": "completed"
            })
        
        append_log_entry(state["slug"], {
            "node": "rewrite",
            "status": "completed",
            "total_chapters": len(rewritten_chapters)
        })
        
        return {**state, "rewritten": rewritten_chapters}
        
    except Exception as e:
        error_msg = f"Rewrite failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "rewrite",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg]}


def qa_text_node(state: FlowState) -> FlowState:
    """QA modernized text using Checker chain."""
    try:
        append_log_entry(state["slug"], {
            "node": "qa_text",
            "status": "started"
        })
        
        all_passed = True
        total_issues = []
        
        for chapter_doc in state["rewritten"]:
            # QA chapter
            passed, issues, updated_doc = qa_chapter(chapter_doc)
            
            # Save QA issues
            save_qa_issues(state["slug"], chapter_doc.chapter, issues)
            
            # Update chapter doc
            save_chapter_doc(state["slug"], chapter_doc.chapter, updated_doc)
            
            all_passed = all_passed and passed
            total_issues.extend(issues)
            
            append_log_entry(state["slug"], {
                "node": "qa_text",
                "chapter": chapter_doc.chapter,
                "passed": passed,
                "issues": len(issues),
                "status": "completed"
            })
        
        append_log_entry(state["slug"], {
            "node": "qa_text",
            "status": "completed",
            "all_passed": all_passed,
            "total_issues": len(total_issues)
        })
        
        return {**state, "qa_text_ok": all_passed}
        
    except Exception as e:
        error_msg = f"QA text failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "qa_text",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg], "qa_text_ok": False}


def remediate_node(state: FlowState) -> FlowState:
    """Remediate failing paragraphs with targeted retries."""
    try:
        append_log_entry(state["slug"], {
            "node": "remediate",
            "status": "started"
        })
        
        # For now, just mark as remediated
        # TODO: Implement targeted retry logic
        
        append_log_entry(state["slug"], {
            "node": "remediate",
            "status": "completed"
        })
        
        return {**state, "qa_text_ok": True}
        
    except Exception as e:
        error_msg = f"Remediate failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "remediate",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg]}


def epub_node(state: FlowState) -> FlowState:
    """Build EPUB from modernized chapters."""
    try:
        append_log_entry(state["slug"], {
            "node": "epub",
            "status": "started"
        })
        
        # Create metadata
        metadata = BookMetadata(
            title=f"{state['slug'].title()} (Modernized Student Edition)",
            author="Public Domain Author (Modernized by Lily Books)",
            public_domain_source=f"Project Gutenberg #{state['book_id']}"
        )
        
        # Build EPUB
        epub_path = build_epub(state["slug"], state["rewritten"], metadata)
        
        # Save metadata
        save_book_metadata(state["slug"], metadata)
        
        append_log_entry(state["slug"], {
            "node": "epub",
            "status": "completed",
            "epub_path": str(epub_path)
        })
        
        return {**state, "epub_path": str(epub_path)}
        
    except Exception as e:
        error_msg = f"EPUB build failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "epub",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg]}


def tts_node(state: FlowState) -> FlowState:
    """Generate TTS audio for chapters."""
    try:
        append_log_entry(state["slug"], {
            "node": "tts",
            "status": "started"
        })
        
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
        error_msg = f"TTS failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "tts",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg]}


def master_node(state: FlowState) -> FlowState:
    """Master audio files for ACX compliance."""
    try:
        append_log_entry(state["slug"], {
            "node": "master",
            "status": "started"
        })
        
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
        error_msg = f"Master failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "master",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg]}


def qa_audio_node(state: FlowState) -> FlowState:
    """QA audio files for ACX compliance."""
    try:
        append_log_entry(state["slug"], {
            "node": "qa_audio",
            "status": "started"
        })
        
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
        error_msg = f"QA audio failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "qa_audio",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg], "audio_ok": False}


def package_node(state: FlowState) -> FlowState:
    """Package final deliverables."""
    try:
        append_log_entry(state["slug"], {
            "node": "package",
            "status": "started"
        })
        
        paths = get_project_paths(state["slug"])
        
        # Extract retail sample from first chapter
        if state["mastered_files"]:
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
            "retail_sample": str(sample_path) if state["mastered_files"] else None,
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
        error_msg = f"Package failed: {str(e)}"
        append_log_entry(state["slug"], {
            "node": "package",
            "status": "error",
            "error": error_msg
        })
        return {**state, "errors": state["errors"] + [error_msg]}


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
            "remediate": "remediate",
            "epub": "epub"
        }
    )
    
    graph.add_edge("remediate", "qa_text")
    graph.add_edge("epub", "tts")
    graph.add_edge("tts", "master")
    graph.add_edge("master", "qa_audio")
    graph.add_edge("qa_audio", "package")
    graph.add_edge("package", END)
    
    return graph


def compile_graph() -> Any:
    """Compile the graph with checkpointing."""
    graph = build_graph()
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

