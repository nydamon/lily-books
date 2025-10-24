"""Configuration management using Pydantic settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    LLM-Driven Pipeline Philosophy:
    - llm_validation_mode="trust": Use quality thresholds as targets, not hard failures
    - self_healing_enabled=True: Retry with enhanced prompts instead of immediate failure
    - llm_quality_advisor_enabled=True: Use LLM to review and improve its own outputs
    - use_llm_for_structure=True: Let LLM handle chapter detection and text chunking

    Note: Quality thresholds (qa_min_fidelity, qa_target_fidelity, etc.) serve as:
    - Targets for optimization
    - Triggers for remediation when self_healing_enabled=True
    - Logging/monitoring benchmarks
    They do NOT cause hard pipeline failures when llm_validation_mode="trust"
    """

    model_config = {
        "extra": "ignore",  # Ignore extra env vars (legacy keys like OPENAI_API_KEY)
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    # API Keys
    openrouter_api_key: str  # Required: OpenRouter for all LLM access (GPT, Claude)
    fish_api_key: str | None = None
    ideogram_api_key: str | None = None  # Required for Ideogram cover generation

    # Model configurations - OpenRouter only
    # GPT-4o-mini and Claude 4.5 Haiku via OpenRouter: https://openrouter.ai/models
    openai_model: str = "openai/gpt-4o-mini"
    openai_fallback_model: str = "openai/gpt-4o-mini"
    anthropic_model: str = "anthropic/claude-haiku-4.5"
    anthropic_fallback_model: str = "anthropic/claude-sonnet-4.5"

    # Fish Audio TTS settings
    fish_reference_id: str = ""  # Optional: Custom voice model ID
    use_audio_transcription: bool = True

    # Development settings
    debug: bool = False
    fail_fast_enabled: bool = False
    log_level: str = "INFO"

    # Retry settings
    llm_max_retries: int = 3
    llm_retry_max_wait: int = 120  # Increased from 60 to 120 seconds

    # Pipeline timeout settings (seconds)
    chapter_processing_timeout: int = 300  # 5 minutes per chapter
    qa_processing_timeout: int = 180  # 3 minutes per QA check

    # LLM-driven validation settings
    llm_validation_mode: str = "trust"  # "strict", "hybrid", "trust"
    self_healing_enabled: bool = True
    max_retry_attempts: int = 3
    retry_enhancement_strategy: str = (
        "progressive"  # "progressive", "aggressive", "conservative"
    )
    llm_quality_advisor_enabled: bool = True
    use_llm_for_structure: bool = True

    # Quality control thresholds
    qa_min_fidelity: int = 85  # Strict threshold for sellable quality
    qa_target_fidelity: int = 92  # Target mean fidelity
    qa_min_readability_grade: float = 5.0  # Minimum FK grade
    qa_max_readability_grade: float = 12.0  # Maximum FK grade
    qa_target_min_grade: float = 7.0  # Target minimum
    qa_target_max_grade: float = 9.0  # Target maximum
    qa_emphasis_severity: str = "high"  # critical/high/medium/low
    qa_quote_severity: str = "high"  # critical/high/medium/low
    qa_failure_mode: str = "continue_with_log"  # continue_with_log/fail_fast

    # Caching settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    cache_type: str = "memory"  # "memory" or "redis"
    redis_url: str = "redis://localhost:6379"

    # Langfuse observability settings
    langfuse_enabled: bool = True
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Publishing options
    use_ai_covers: bool = True  # Ideogram AI cover generation (required)
    publisher_name: str = "Modernized Classics Press"
    publisher_url: str = ""

    # Pipeline feature toggles
    enable_qa_review: bool = True  # Enable/disable QA text validation
    enable_audio: bool = False  # Enable/disable audio generation


def get_project_paths(slug: str) -> dict[str, Path]:
    """Get standardized paths for a project slug."""
    base_dir = Path("books") / slug

    return {
        "base": base_dir,
        "source": base_dir / "source",
        "work": base_dir / "work",
        "rewrite": base_dir / "work" / "rewrite",
        "audio": base_dir / "work" / "audio",
        "audio_mastered": base_dir / "work" / "audio_mastered",
        "qa_text": base_dir / "work" / "qa" / "text",
        "qa_audio": base_dir / "work" / "qa" / "audio",
        "deliverables": base_dir / "deliverables",
        "deliverables_ebook": base_dir / "deliverables" / "ebook",
        "deliverables_audio": base_dir / "deliverables" / "audio",
        "meta": base_dir / "meta",
    }


def ensure_directories(slug: str) -> None:
    """Create all necessary directories for a project."""
    paths = get_project_paths(slug)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


def get_config() -> Settings:
    """Get the global configuration instance."""
    return settings


def validate_audio_dependencies() -> None:
    """Validate that Fish Audio SDK is available when audio is enabled.

    Raises:
        ImportError: If ENABLE_AUDIO=true but Fish Audio SDK is not installed
        ValueError: If ENABLE_AUDIO=true but FISH_API_KEY is not configured
    """
    if not settings.enable_audio:
        return

    try:
        from lily_books.tools.tts import Session, TTSRequest

        if Session is None or TTSRequest is None:
            raise ImportError()
    except ImportError:
        raise ImportError(
            "Fish Audio SDK required when ENABLE_AUDIO=true. "
            "Install with: poetry add fish-audio-sdk"
        )

    if not settings.fish_api_key:
        raise ValueError(
            "FISH_API_KEY required when ENABLE_AUDIO=true. "
            "Set FISH_API_KEY in .env or disable ENABLE_AUDIO."
        )


def get_quality_settings(slug: str) -> dict:
    """Get quality settings with per-book overrides from book.yaml."""
    from .storage import load_book_metadata

    # Start with global defaults
    quality_config = {
        "min_fidelity": settings.qa_min_fidelity,
        "target_fidelity": settings.qa_target_fidelity,
        "readability_range": (
            settings.qa_min_readability_grade,
            settings.qa_max_readability_grade,
        ),
        "emphasis_severity": settings.qa_emphasis_severity,
        "quote_severity": settings.qa_quote_severity,
        "failure_mode": settings.qa_failure_mode,
    }

    # Check for book-specific overrides
    metadata = load_book_metadata(slug)
    if metadata and hasattr(metadata, "quality_control") and metadata.quality_control:
        # Override with book-specific settings
        qc = metadata.quality_control
        if qc.min_fidelity is not None:
            quality_config["min_fidelity"] = qc.min_fidelity
        if qc.target_fidelity is not None:
            quality_config["target_fidelity"] = qc.target_fidelity
        if qc.readability_range is not None:
            quality_config["readability_range"] = qc.readability_range
        if qc.emphasis_severity is not None:
            quality_config["emphasis_severity"] = qc.emphasis_severity
        if qc.quote_severity is not None:
            quality_config["quote_severity"] = qc.quote_severity
        if qc.failure_mode is not None:
            quality_config["failure_mode"] = qc.failure_mode

    return quality_config
