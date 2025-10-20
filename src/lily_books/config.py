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
    openai_model: str = "openai/gpt-5"
    openai_fallback_model: str = "openai/gpt-5-mini"
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
