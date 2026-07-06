"""
FastAPI Application Main Module

Main entry point for the Indian Law AI Portal API.
"""

import os
import sys

# Add parent directory to path for imports when running directly
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger

# Handle imports for both module and direct execution
try:
    from .api.routers import query_router, admin_router, health_router
    from .api.core.config import get_settings
    from .api.core.ai_service import AIService
except ImportError:
    from api.routers import query_router, admin_router, health_router
    from api.core.config import get_settings
    from api.core.ai_service import AIService


# Global AI service instance
ai_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global ai_service
    
    # Startup
    logger.info("Starting Indian Law AI Portal API...")
    settings = get_settings()
    
    try:
        # Initialize AI service
        ai_service = AIService()
        await ai_service.initialize()
        
        # Store in app state
        app.state.ai_service = ai_service
        
        logger.info("API startup completed successfully")
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Indian Law AI Portal API...")
        if ai_service:
            await ai_service.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Indian Law AI Portal",
    description="AI-powered legal query assistant for Indian laws using RAG and agentic AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers — carry BOTH "error" and "detail": the frontend (and
# FastAPI convention) read `detail`, while `error` predates that and may have
# other consumers. 422 validation errors keep FastAPI's default shape.
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "detail": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "Internal server error", "status_code": 500}
    )


# Include routers
app.include_router(health_router.router, prefix="/health", tags=["Health"])
app.include_router(query_router.router, prefix="/api/v1", tags=["Query"])
app.include_router(admin_router.router, prefix="/api/v1/admin", tags=["Admin"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Indian Law AI Portal API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    # Load .env file from project root
    from dotenv import load_dotenv
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(project_root, ".env"))
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG_MODE,
        log_level=settings.LOG_LEVEL.lower()
    )