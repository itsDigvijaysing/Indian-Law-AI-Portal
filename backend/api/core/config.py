"""
Configuration Management

Handles application settings and environment variables.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _find_env_file() -> str:
    """Find .env file - check current dir, then parent (project root)"""
    current = Path.cwd() / ".env"
    if current.exists():
        return str(current)

    # Check parent directory (when running from backend/)
    parent = Path.cwd().parent / ".env"
    if parent.exists():
        return str(parent)

    # Check relative to this file's location
    project_root_env = _PROJECT_ROOT / ".env"
    if project_root_env.exists():
        return str(project_root_env)

    return ".env"  # Default fallback


def _resolve_project_path(value: str) -> str:
    """Resolve relative paths against the project root, leaving absolute paths alone."""
    p = Path(value)
    if p.is_absolute():
        return str(p)
    return str((_PROJECT_ROOT / p).resolve())


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        case_sensitive=True,
        extra="ignore"
    )
    
    # Google AI Configuration
    GOOGLE_API_KEY: str = Field(default="your_google_api_key_here")
    GOOGLE_PROJECT_ID: Optional[str] = Field(default=None)

    # Groq Configuration
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # Model Configuration
    LLM_PROVIDER: str = Field(default="gemini")  # "gemini" or "groq"
    LLM_MODEL: str = Field(default="gemini-2.0-flash")
    EMBEDDING_MODEL: str = Field(default="gemini-embedding-001")
    
    # Vector Database Configuration
    # (index dimension comes from the embedding model at runtime, not config)
    VECTOR_DB_TYPE: str = Field(default="faiss")
    VECTOR_DB_PATH: str = Field(default="./vector_db/")
    
    # RAG Configuration
    RAG_FUSION_QUERIES: int = Field(default=3)
    TOP_K_RETRIEVAL: int = Field(default=10)
    CHUNK_SIZE: int = Field(default=500)
    CHUNK_OVERLAP: int = Field(default=50)

    # Retrieval quality
    RERANK_ENABLED: bool = Field(default=True)
    RERANK_MODEL: str = Field(default="cross-encoder/ms-marco-MiniLM-L6-v2")
    RERANK_CANDIDATES: int = Field(default=24)
    CITED_SOURCES_K: int = Field(default=8)

    # Two-stage category router (classify query -> scope retrieval to that
    # legal category's documents). Soft boost, never hard-exclude.
    CATEGORY_ROUTING_ENABLED: bool = Field(default=True)
    CLASSIFIER_MIN_CONFIDENCE: float = Field(default=0.3)
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    DEBUG_MODE: bool = Field(default=True)
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/app.log")
    
    # Assets Configuration
    ASSETS_PATH: str = Field(default="./assets/")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.VECTOR_DB_PATH = _resolve_project_path(settings.VECTOR_DB_PATH)
    settings.ASSETS_PATH = _resolve_project_path(settings.ASSETS_PATH)
    settings.LOG_FILE = _resolve_project_path(settings.LOG_FILE)
    return settings


def setup_logging(settings: Settings):
    """Setup application logging"""
    import logging
    from loguru import logger
    
    # Remove default handler
    logger.remove()
    
    # Console handler
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File handler (ensure directory exists)
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days"
    )
    
    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}, File: {settings.LOG_FILE}")


def validate_environment():
    """Validate required environment variables and configurations"""
    try:
        settings = get_settings()

        # Check the API key for the configured provider
        provider = (settings.LLM_PROVIDER or "gemini").lower()
        if provider == "groq":
            if not settings.GROQ_API_KEY:
                raise ValueError("LLM_PROVIDER=groq requires GROQ_API_KEY to be set")
        elif not settings.GOOGLE_API_KEY or settings.GOOGLE_API_KEY == "your_google_api_key_here":
            raise ValueError("GOOGLE_API_KEY is required and must be set to a valid API key")
        
        # Check assets directory
        if not os.path.exists(settings.ASSETS_PATH):
            os.makedirs(settings.ASSETS_PATH, exist_ok=True)
            print(f"Created assets directory: {settings.ASSETS_PATH}")
        
        # Check vector database directory
        if not os.path.exists(settings.VECTOR_DB_PATH):
            os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
            print(f"Created vector database directory: {settings.VECTOR_DB_PATH}")
        
        return True
        
    except Exception as e:
        print(f"Environment validation failed: {e}")
        return False