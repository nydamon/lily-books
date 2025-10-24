"""Pydantic data models for the book modernization pipeline."""

from typing import Any, Literal, TypedDict

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


class CoverError(PipelineError):
    """Raised when cover generation fails."""

    pass


class QualityControl(BaseModel):
    """Per-book quality control overrides."""

    min_fidelity: int | None = None
    target_fidelity: int | None = None
    readability_range: tuple[float, float] | None = None
    emphasis_severity: str | None = None
    quote_severity: str | None = None
    failure_mode: str | None = None
    notes: str | None = None  # For documenting why overrides were needed


class QAIssue(BaseModel):
    """A validation issue found during QA."""

    type: str
    description: str
    severity: Literal["low", "medium", "high", "critical"] | None = "medium"
    span_original: str | None = None
    span_modern: str | None = None
    suggestion: str | None = None


class QAReport(BaseModel):
    """Comprehensive QA report for a paragraph pair."""

    fidelity_score: int | None = None
    readability_grade: float | None = None
    readability_appropriate: bool | None = None
    character_count_ratio: float | None = None
    modernization_complete: bool | None = None
    formatting_preserved: bool | None = None  # quotes + italics
    tone_consistent: bool | None = None
    quote_count_match: bool | None = None
    emphasis_preserved: bool | None = None
    literary_quality_maintained: bool | None = None
    historical_accuracy_preserved: bool | None = None
    issues: list[QAIssue] = Field(default_factory=list)
    retry_count: int = 0
    confidence: float | None = None
    llm_reasoning: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParaPair(BaseModel):
    """Original and modernized paragraph pair with QA results."""

    i: int
    para_id: str
    orig: str
    modern: str
    qa: QAReport | None = None
    notes: str | None = None


class ChapterDoc(BaseModel):
    """Complete chapter with modernized paragraph pairs."""

    chapter: int
    title: str
    pairs: list[ParaPair]


class ChapterSplit(BaseModel):
    """Raw chapter split with original paragraphs."""

    chapter: int
    title: str
    paragraphs: list[str]


class BookMetadata(BaseModel):
    """Book metadata from meta/book.yaml."""

    title: str
    author: str
    public_domain_source: str
    language: str = "en-US"
    voice: dict = Field(
        default_factory=lambda: {
            "provider": "fish_audio",
            "reference_id": "",  # Optional: Custom voice model ID from Fish Audio
            "rate": "standard",
        }
    )
    acx: dict = Field(
        default_factory=lambda: {
            "target_rms_db": -20,
            "peak_db_max": -3,
            "noise_floor_db_max": -60,
        }
    )
    retail_sample: dict = Field(
        default_factory=lambda: {"chapter": 1, "start_sec": 30, "duration_sec": 180}
    )
    pricing: dict = Field(
        default_factory=lambda: {"ebook_usd": 2.99, "audiobook_usd": 9.95}
    )
    quality_control: QualityControl | None = None


class ModernizedParagraph(BaseModel):
    """Single modernized paragraph from Writer chain."""

    modern: str = Field(description="Modernized version of the paragraph")


class WriterOutput(BaseModel):
    """Output schema for Writer chain - array of modernized paragraphs."""

    paragraphs: list[ModernizedParagraph] = Field(
        description="Array of modernized paragraphs in order"
    )


class CheckerOutput(BaseModel):
    """Comprehensive output schema for Checker chain QA validation."""

    fidelity_score: int | None = Field(
        default=None,
        description="Fidelity score from 0-100. LLM determines appropriate scoring based on context.",
    )
    readability_grade: float | None = Field(
        default=None,
        description="Flesch-Kincaid grade level of modernized text. LLM balances accessibility with literary sophistication.",
    )
    readability_appropriate: bool | None = Field(
        default=None,
        description="Whether readability grade is appropriate for the target audience. LLM decides based on context.",
    )
    modernization_complete: bool | None = Field(
        default=None,
        description="Whether modernization achieves the intended goals. LLM evaluates based on literary context.",
    )
    formatting_preserved: bool | None = Field(
        default=None,
        description="Whether formatting elements are appropriately handled. LLM considers context and meaning preservation.",
    )
    tone_consistent: bool | None = Field(
        default=None,
        description="Whether the narrative voice matches the original. LLM evaluates literary authenticity.",
    )
    quote_count_match: bool | None = Field(
        default=None,
        description="Whether quotation handling is appropriate. LLM considers context and meaning preservation.",
    )
    emphasis_preserved: bool | None = Field(
        default=None,
        description="Whether emphasis markers are appropriately converted. LLM considers readability and meaning.",
    )
    character_count_ratio: float | None = Field(
        default=None,
        description="Ratio of modernized text length to original. LLM balances clarity with conciseness.",
    )
    literary_quality_maintained: bool | None = Field(
        default=None,
        description="Whether the artistic and intellectual quality is preserved. LLM evaluates literary merit.",
    )
    historical_accuracy_preserved: bool | None = Field(
        default=None,
        description="Whether period-appropriate elements are maintained. LLM considers historical context.",
    )
    issues: list[QAIssue] = Field(
        default_factory=list,
        description="Detailed list of validation issues found, with specific examples and recommendations",
    )
    confidence: float | None = Field(
        default=None, description="LLM confidence in the assessment (0.0-1.0)"
    )
    llm_reasoning: str | None = Field(
        default=None, description="LLM's reasoning process and decision rationale"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional LLM insights and context-specific information",
    )


class PublishingMetadata(BaseModel):
    """Extended metadata for publishing."""

    title: str
    subtitle: str | None = None
    author: str
    original_author: str  # For public domain works
    publisher: str = "Modernized Classics Press"
    publisher_url: str | None = None
    publication_year: int = Field(default_factory=lambda: 2025)
    isbn_ebook: str | None = None
    isbn_audiobook: str | None = None

    # Marketing
    short_description: str  # 1-2 sentences
    long_description: str  # 200-300 words
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)

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
    cover_prompt: str | None = None  # For AI cover generation

    # Publisher branding
    publisher_logo: str | None = None  # URL or path to publisher logo
    publisher_tagline: str = "Making Classic Literature Accessible to Modern Readers"
    series_name: str | None = None  # e.g., "Modernized Classics Series"
    series_number: int | None = None  # Position in series


class CoverDesign(BaseModel):
    """Cover design specifications."""

    image_url: str | None = None  # AI-generated or external
    image_path: str | None = None  # Local file path
    title: str
    subtitle: str | None = None
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
    rewritten: list[ChapterDoc] | None
    qa_text_ok: bool | None
    audio_ok: bool | None
    epub_path: str | None
    epub_quality_score: int | None
    requested_chapters: list[int] | None  # Chapter filter from CLI
    audio_files: list[dict] | None  # Audio files from TTS
    mastered_files: list[dict] | None  # Mastered audio files

    # NEW FIELDS:
    publishing_metadata: PublishingMetadata | None
    cover_design: CoverDesign | None
    cover_path: str | None
