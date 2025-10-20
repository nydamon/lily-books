"""Pydantic data models for the book modernization pipeline."""

from typing import List, Literal, Optional, TypedDict, Dict, Any
from pydantic import BaseModel, Field


class PipelineError(Exception):
    """Base exception for pipeline failures."""
    def __init__(self, message: str, slug: str, node: str, context: dict = None):
        super().__init__(message)
        self.slug = slug
        self.node = node
        self.context = context or {}


class IngestError(PipelineError):
    """Raised when book ingestion fails."""
    pass


class ChapterizeError(PipelineError):
    """Raised when chapter splitting fails."""
    pass


class RewriteError(PipelineError):
    """Raised when text modernization fails."""
    pass


class QAError(PipelineError):
    """Raised when QA validation fails."""
    pass


class EPUBError(PipelineError):
    """Raised when EPUB generation fails."""
    pass


class TTSError(PipelineError):
    """Raised when TTS generation fails."""
    pass


class MasterError(PipelineError):
    """Raised when audio mastering fails."""
    pass


class PackageError(PipelineError):
    """Raised when final packaging fails."""
    pass


class QualityControl(BaseModel):
    """Per-book quality control overrides."""
    min_fidelity: Optional[int] = None
    target_fidelity: Optional[int] = None
    readability_range: Optional[tuple[float, float]] = None
    emphasis_severity: Optional[str] = None
    quote_severity: Optional[str] = None
    failure_mode: Optional[str] = None
    notes: Optional[str] = None  # For documenting why overrides were needed


class QAIssue(BaseModel):
    """A validation issue found during QA."""
    type: str
    description: str
    severity: Optional[Literal["low", "medium", "high", "critical"]] = "medium"
    span_original: Optional[str] = None
    span_modern: Optional[str] = None
    suggestion: Optional[str] = None


class QAReport(BaseModel):
    """Comprehensive QA report for a paragraph pair."""
    fidelity_score: Optional[int] = None
    readability_grade: Optional[float] = None
    readability_appropriate: Optional[bool] = None
    character_count_ratio: Optional[float] = None
    modernization_complete: Optional[bool] = None
    formatting_preserved: Optional[bool] = None  # quotes + italics
    tone_consistent: Optional[bool] = None
    quote_count_match: Optional[bool] = None
    emphasis_preserved: Optional[bool] = None
    literary_quality_maintained: Optional[bool] = None
    historical_accuracy_preserved: Optional[bool] = None
    issues: List[QAIssue] = Field(default_factory=list)
    retry_count: int = 0
    confidence: Optional[float] = None
    llm_reasoning: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    quality_control: Optional[QualityControl] = None


class ModernizedParagraph(BaseModel):
    """Single modernized paragraph from Writer chain."""
    modern: str = Field(description="Modernized version of the paragraph")


class WriterOutput(BaseModel):
    """Output schema for Writer chain - array of modernized paragraphs."""
    paragraphs: List[ModernizedParagraph] = Field(
        description="Array of modernized paragraphs in order"
    )


class CheckerOutput(BaseModel):
    """Comprehensive output schema for Checker chain QA validation."""
    fidelity_score: Optional[int] = Field(
        default=None,
        description="Fidelity score from 0-100. LLM determines appropriate scoring based on context."
    )
    readability_grade: Optional[float] = Field(
        default=None,
        description="Flesch-Kincaid grade level of modernized text. LLM balances accessibility with literary sophistication."
    )
    readability_appropriate: Optional[bool] = Field(
        default=None,
        description="Whether readability grade is appropriate for the target audience. LLM decides based on context."
    )
    modernization_complete: Optional[bool] = Field(
        default=None,
        description="Whether modernization achieves the intended goals. LLM evaluates based on literary context."
    )
    formatting_preserved: Optional[bool] = Field(
        default=None,
        description="Whether formatting elements are appropriately handled. LLM considers context and meaning preservation."
    )
    tone_consistent: Optional[bool] = Field(
        default=None,
        description="Whether the narrative voice matches the original. LLM evaluates literary authenticity."
    )
    quote_count_match: Optional[bool] = Field(
        default=None,
        description="Whether quotation handling is appropriate. LLM considers context and meaning preservation."
    )
    emphasis_preserved: Optional[bool] = Field(
        default=None,
        description="Whether emphasis markers are appropriately converted. LLM considers readability and meaning."
    )
    character_count_ratio: Optional[float] = Field(
        default=None,
        description="Ratio of modernized text length to original. LLM balances clarity with conciseness."
    )
    literary_quality_maintained: Optional[bool] = Field(
        default=None,
        description="Whether the artistic and intellectual quality is preserved. LLM evaluates literary merit."
    )
    historical_accuracy_preserved: Optional[bool] = Field(
        default=None,
        description="Whether period-appropriate elements are maintained. LLM considers historical context."
    )
    issues: List[QAIssue] = Field(
        default_factory=list,
        description="Detailed list of validation issues found, with specific examples and recommendations"
    )
    confidence: Optional[float] = Field(
        default=None,
        description="LLM confidence in the assessment (0.0-1.0)"
    )
    llm_reasoning: Optional[str] = Field(
        default=None,
        description="LLM's reasoning process and decision rationale"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional LLM insights and context-specific information"
    )


class PublishingMetadata(BaseModel):
    """Extended metadata for publishing."""
    title: str
    subtitle: Optional[str] = None
    author: str
    original_author: str  # For public domain works
    publisher: str = "Modernized Classics Press"
    publisher_url: Optional[str] = None
    publication_year: int = Field(default_factory=lambda: 2025)
    isbn_ebook: Optional[str] = None
    isbn_audiobook: Optional[str] = None
    
    # Marketing
    short_description: str  # 1-2 sentences
    long_description: str   # 200-300 words
    keywords: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    
    # Legal
    copyright_notice: str = Field(
        default="This modernized edition © {year} {publisher}. Original work in public domain."
    )
    modernization_disclaimer: str = Field(
        default="This edition features AI-assisted language modernization to make the text more accessible to contemporary readers while preserving the author's original meaning and style."
    )
    license: str = "All rights reserved"
    
    # Branding
    cover_style: str = "classic"  # Options: classic, modern, minimalist, whimsical classic, academic, artistic, nostalgic
    cover_prompt: Optional[str] = None  # For AI cover generation
    
    # Publisher branding
    publisher_logo: Optional[str] = None  # URL or path to publisher logo
    publisher_tagline: str = "Making Classic Literature Accessible to Modern Readers"
    series_name: Optional[str] = None  # e.g., "Modernized Classics Series"
    series_number: Optional[int] = None  # Position in series


class CoverDesign(BaseModel):
    """Cover design specifications."""
    image_url: Optional[str] = None  # AI-generated or external
    image_path: Optional[str] = None  # Local file path
    title: str
    subtitle: Optional[str] = None
    author: str
    publisher: str = "Modernized Classics Press"
    
    # Design specs
    width: int = 1600
    height: int = 2400
    format: str = "png"


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
    epub_path: Optional[str]
    epub_quality_score: Optional[int]
    
    # NEW FIELDS:
    publishing_metadata: Optional[PublishingMetadata]
    cover_design: Optional[CoverDesign]
    cover_path: Optional[str]
