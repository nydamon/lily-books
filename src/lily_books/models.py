"""Pydantic data models for the book modernization pipeline."""

from typing import List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field


class QAIssue(BaseModel):
    """A validation issue found during QA."""
    type: str
    description: str
    severity: Literal["low", "medium", "high"]
    span_original: Optional[str] = None
    span_modern: Optional[str] = None
    suggestion: Optional[str] = None


class QAReport(BaseModel):
    """QA report for a paragraph pair."""
    fidelity_score: int = 0
    readability_grade: float = 0.0
    character_count_ratio: float = 0.0
    modernization_complete: bool = False
    formatting_preserved: bool = False  # quotes + italics
    tone_consistent: bool = False
    quote_count_match: bool = False
    emphasis_preserved: bool = False
    issues: List[QAIssue] = Field(default_factory=list)
    retry_count: int = 0


class ParaPair(BaseModel):
    """Original and modernized paragraph pair with QA results."""
    i: int
    para_id: str
    orig: str
    modern: str
    qa: Optional[QAReport] = None
    notes: Optional[str] = None


class ChapterDoc(BaseModel):
    """Complete chapter with modernized paragraph pairs."""
    chapter: int
    title: str
    pairs: List[ParaPair]


class ChapterSplit(BaseModel):
    """Raw chapter split with original paragraphs."""
    chapter: int
    title: str
    paragraphs: List[str]


class BookMetadata(BaseModel):
    """Book metadata from meta/book.yaml."""
    title: str
    author: str
    public_domain_source: str
    language: str = "en-US"
    voice: dict = Field(default_factory=lambda: {
        "provider": "elevenlabs",
        "voice_id": "Rachel",
        "rate": "standard"
    })
    acx: dict = Field(default_factory=lambda: {
        "target_rms_db": -20,
        "peak_db_max": -3,
        "noise_floor_db_max": -60
    })
    retail_sample: dict = Field(default_factory=lambda: {
        "chapter": 1,
        "start_sec": 30,
        "duration_sec": 180
    })
    pricing: dict = Field(default_factory=lambda: {
        "ebook_usd": 2.99,
        "audiobook_usd": 9.95
    })


class FlowState(TypedDict):
    """LangGraph state for the pipeline."""
    slug: str
    book_id: int | None
    paths: dict
    raw_text: str | None
    chapters: list[ChapterSplit] | None
    rewritten: list[str] | None
    qa_text_ok: bool | None
    audio_ok: bool | None
    errors: list[str]

