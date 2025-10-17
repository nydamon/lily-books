"""Storage and persistence utilities for project data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .models import ChapterDoc, FlowState, BookMetadata
from .config import get_project_paths, ensure_directories


@dataclass
class ProjectPaths:
    """Standardized paths for a project."""
    base: Path
    source: Path
    work: Path
    rewrite: Path
    audio: Path
    audio_mastered: Path
    qa_text: Path
    qa_audio: Path
    deliverables: Path
    deliverables_ebook: Path
    deliverables_audio: Path
    meta: Path


def get_project_paths_dataclass(slug: str) -> ProjectPaths:
    """Get ProjectPaths dataclass for a project slug."""
    paths_dict = get_project_paths(slug)
    return ProjectPaths(**paths_dict)


def save_chapter_doc(slug: str, chapter_num: int, doc: ChapterDoc) -> Path:
    """Save ChapterDoc to JSON file."""
    paths = get_project_paths(slug)
    ensure_directories(slug)
    
    output_file = paths["rewrite"] / f"ch{chapter_num:02d}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(doc.model_dump(), f, indent=2, ensure_ascii=False)
    
    return output_file


def load_chapter_doc(slug: str, chapter_num: int) -> Optional[ChapterDoc]:
    """Load ChapterDoc from JSON file."""
    paths = get_project_paths(slug)
    input_file = paths["rewrite"] / f"ch{chapter_num:02d}.json"
    
    if not input_file.exists():
        return None
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ChapterDoc(**data)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error loading chapter {chapter_num}: {e}")
        return None


def save_state(slug: str, state: FlowState) -> Path:
    """Save FlowState to JSON file."""
    paths = get_project_paths(slug)
    ensure_directories(slug)
    
    output_file = paths["meta"] / "ingestion_state.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    return output_file


def load_state(slug: str) -> Optional[FlowState]:
    """Load FlowState from JSON file."""
    paths = get_project_paths(slug)
    input_file = paths["meta"] / "ingestion_state.json"
    
    if not input_file.exists():
        return None
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error loading state: {e}")
        return None


def append_log_entry(slug: str, entry: Dict[str, Any]) -> Path:
    """Append log entry to ingestion_log.jsonl."""
    paths = get_project_paths(slug)
    ensure_directories(slug)
    
    log_file = paths["meta"] / "ingestion_log.jsonl"
    
    # Add timestamp
    entry["timestamp"] = datetime.utcnow().isoformat()
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    return log_file


def save_chapters_jsonl(slug: str, chapters: List[Dict]) -> Path:
    """Save chapters list to JSONL file."""
    paths = get_project_paths(slug)
    ensure_directories(slug)
    
    output_file = paths["work"] / "chapters.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for chapter in chapters:
            f.write(json.dumps(chapter, ensure_ascii=False) + '\n')
    
    return output_file


def load_chapters_jsonl(slug: str) -> List[Dict]:
    """Load chapters list from JSONL file."""
    paths = get_project_paths(slug)
    input_file = paths["work"] / "chapters.jsonl"
    
    if not input_file.exists():
        return []
    
    chapters = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chapters.append(json.loads(line))
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error loading chapters: {e}")
    
    return chapters


def save_qa_issues(slug: str, chapter_num: int, issues: List[Dict]) -> Path:
    """Save QA issues to JSON file."""
    paths = get_project_paths(slug)
    ensure_directories(slug)
    
    output_file = paths["qa_text"] / f"ch{chapter_num:02d}-issues.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)
    
    return output_file


def load_qa_issues(slug: str, chapter_num: int) -> List[Dict]:
    """Load QA issues from JSON file."""
    paths = get_project_paths(slug)
    input_file = paths["qa_text"] / f"ch{chapter_num:02d}-issues.json"
    
    if not input_file.exists():
        return []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error loading QA issues for chapter {chapter_num}: {e}")
        return []


def save_book_metadata(slug: str, metadata: BookMetadata) -> Path:
    """Save book metadata to YAML file."""
    import yaml
    
    paths = get_project_paths(slug)
    ensure_directories(slug)
    
    output_file = paths["meta"] / "book.yaml"
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(metadata.model_dump(), f, default_flow_style=False, allow_unicode=True)
    
    return output_file


def load_book_metadata(slug: str) -> Optional[BookMetadata]:
    """Load book metadata from YAML file."""
    import yaml
    
    paths = get_project_paths(slug)
    input_file = paths["meta"] / "book.yaml"
    
    if not input_file.exists():
        return None
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return BookMetadata(**data)
    except (yaml.YAMLError, ValueError) as e:
        print(f"Error loading book metadata: {e}")
        return None


def save_raw_text(slug: str, text: str) -> Path:
    """Save raw text to file."""
    paths = get_project_paths(slug)
    ensure_directories(slug)
    
    output_file = paths["source"] / "original.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    return output_file


def load_raw_text(slug: str) -> Optional[str]:
    """Load raw text from file."""
    paths = get_project_paths(slug)
    input_file = paths["source"] / "original.txt"
    
    if not input_file.exists():
        return None
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading raw text: {e}")
        return None

