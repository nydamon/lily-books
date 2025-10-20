"""Configuration management using Pydantic settings."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Philosophy: Trust LLM judgment over deterministic rules.
    - llm_validation_mode="trust": Remove all quality threshold enforcement
    - self_healing_enabled=True: Retry with enhanced prompts instead of failing
    - llm_quality_advisor_enabled=True: Use LLM to review its own outputs
    - use_llm_for_structure=True: Let LLM handle chapter detection, chunking
    """
    
    # API Keys
    openai_api_key: str
    openrouter_api_key: str
    elevenlabs_api_key: str
    
    # Model configurations
    # GPT-5 Mini: https://platform.openai.com/docs/models/gpt-5-mini
    openai_model: str = "gpt-5-mini"
    openai_fallback_model: str = "gpt-4o-mini"
    anthropic_model: str = "anthropic/claude-haiku-4.5"
    anthropic_fallback_model: str = "anthropic/claude-sonnet-4.5"
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # Sarah
    
    # Development settings
    debug: bool = False
    log_level: str = "INFO"
    
    # Retry settings
    llm_max_retries: int = 3
    llm_retry_max_wait: int = 60
    
    # LLM-driven validation settings
    llm_validation_mode: str = "trust"  # "strict", "hybrid", "trust"
    self_healing_enabled: bool = True
    max_retry_attempts: int = 3
    retry_enhancement_strategy: str = "progressive"  # "progressive", "aggressive", "conservative"
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
    
    # Langfuse settings
    langfuse_enabled: bool = True
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    
    # Publishing options
    use_ai_covers: bool = False  # Set to True to use DALL-E
    publisher_name: str = "Modernized Classics Press"
    publisher_url: str = ""
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


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


def get_quality_settings(slug: str) -> dict:
    """Get quality settings with per-book overrides from book.yaml."""
    from .storage import load_book_metadata
    
    # Start with global defaults
    quality_config = {
        "min_fidelity": settings.qa_min_fidelity,
        "target_fidelity": settings.qa_target_fidelity,
        "readability_range": (settings.qa_min_readability_grade, settings.qa_max_readability_grade),
        "emphasis_severity": settings.qa_emphasis_severity,
        "quote_severity": settings.qa_quote_severity,
        "failure_mode": settings.qa_failure_mode
    }
    
    # Check for book-specific overrides
    metadata = load_book_metadata(slug)
    if metadata and hasattr(metadata, 'quality_control') and metadata.quality_control:
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

