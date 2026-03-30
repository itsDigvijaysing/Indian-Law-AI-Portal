"""
Health Router

Handles health check and system status endpoints.
"""

from fastapi import APIRouter, Request
from datetime import datetime
from ..models.schemas import SystemHealth

router = APIRouter()


@router.get("/", response_model=SystemHealth)
async def health_check(request: Request) -> SystemHealth:
    """
    Basic health check endpoint.
    """
    ai_service = getattr(request.app.state, 'ai_service', None)
    
    # Determine overall status
    if ai_service and ai_service._initialized:
        status = "healthy"
        ai_initialized = True
        vector_status = "operational"
        total_docs = ai_service.vector_db.get_document_count() if ai_service.vector_db else 0
        agents = len(ai_service.agent_registry.get_all_agents()) if ai_service.agent_registry else 0
    else:
        status = "initializing"
        ai_initialized = False
        vector_status = "not_available"
        total_docs = 0
        agents = 0
    
    return SystemHealth(
        status=status,
        ai_service_initialized=ai_initialized,
        vector_database_status=vector_status,
        total_documents=total_docs,
        available_agents=agents
    )


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for basic connectivity testing.
    """
    return {"message": "pong", "timestamp": datetime.now().isoformat()}


@router.get("/ready")
async def readiness_check(request: Request):
    """
    Readiness check for deployment health monitoring.
    Returns 200 if the service is ready to handle requests.
    """
    from fastapi.responses import JSONResponse
    
    ai_service = getattr(request.app.state, 'ai_service', None)
    
    if ai_service and ai_service._initialized:
        return {"ready": True, "message": "Service is ready"}
    else:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "message": "Service is still initializing"}
        )


@router.get("/live")
async def liveness_check():
    """
    Liveness check for deployment health monitoring.
    Returns 200 if the service is alive (even if not fully ready).
    """
    return {"alive": True, "timestamp": datetime.now().isoformat()}