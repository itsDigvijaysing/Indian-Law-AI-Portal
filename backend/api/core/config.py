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
    config_dir = Path(__file__).parent
    project_root = config_dir.parent.parent.parent / ".env"
    if project_root.exists():
        return str(project_root)
    
    return ".env"  # Default fallback


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
    
    # Model Configuration
    LLM_MODEL: str = Field(default="gemini-2.0-flash")
    EMBEDDING_MODEL: str = Field(default="gemini-embedding-001")
    
    # Vector Database Configuration
    VECTOR_DB_TYPE: str = Field(default="faiss")
    VECTOR_DB_PATH: str = Field(default="./vector_db/")
    VECTOR_DIMENSION: int = Field(default=768)
    
    # RAG Configuration
    RAG_FUSION_QUERIES: int = Field(default=3)
    TOP_K_RETRIEVAL: int = Field(default=10)
    CHUNK_SIZE: int = Field(default=500)
    CHUNK_OVERLAP: int = Field(default=50)
    
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
    return Settings()


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
        
        # Check required API key
        if not settings.GOOGLE_API_KEY or settings.GOOGLE_API_KEY == "your_google_api_key_here":
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