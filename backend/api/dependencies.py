"""
Shared API Dependencies

Common FastAPI dependencies used across routers.
"""

from fastapi import HTTPException, Request
from .core.ai_service import AIService


def get_ai_service(request: Request) -> AIService:
    """Dependency to get AI service from app state"""
    if not hasattr(request.app.state, 'ai_service'):
        raise HTTPException(status_code=503, detail="AI service not available")
    return request.app.state.ai_service
