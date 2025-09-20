"""
Configuration Management

Handles application settings and environment variables.
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Google AI Configuration
    GOOGLE_API_KEY: str = Field(..., env="GOOGLE_API_KEY")
    GOOGLE_PROJECT_ID: Optional[str] = Field(None, env="GOOGLE_PROJECT_ID")
    
    # Model Configuration
    LLM_MODEL: str = Field("gemini-1.5-pro", env="LLM_MODEL")
    EMBEDDING_MODEL: str = Field("text-embedding-004", env="EMBEDDING_MODEL")
    
    # Vector Database Configuration
    VECTOR_DB_TYPE: str = Field("faiss", env="VECTOR_DB_TYPE")
    VECTOR_DB_PATH: str = Field("./vector_db/", env="VECTOR_DB_PATH")
    VECTOR_DIMENSION: int = Field(768, env="VECTOR_DIMENSION")
    
    # RAG Configuration
    RAG_FUSION_QUERIES: int = Field(3, env="RAG_FUSION_QUERIES")
    TOP_K_RETRIEVAL: int = Field(10, env="TOP_K_RETRIEVAL")
    CHUNK_SIZE: int = Field(500, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(50, env="CHUNK_OVERLAP")
    
    # API Configuration
    API_HOST: str = Field("0.0.0.0", env="API_HOST")
    API_PORT: int = Field(8000, env="API_PORT")
    DEBUG_MODE: bool = Field(True, env="DEBUG_MODE")
    
    # Logging Configuration
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field("logs/app.log", env="LOG_FILE")
    
    # Assets Configuration
    ASSETS_PATH: str = Field("./assets/", env="ASSETS_PATH")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


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