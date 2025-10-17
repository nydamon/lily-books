"""Configuration management using Pydantic settings."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: str
    anthropic_api_key: str
    elevenlabs_api_key: str
    
    # Model configurations
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-3-5-sonnet-latest"
    elevenlabs_voice_id: str = "Rachel"
    
    # Development settings
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


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

