"""
Admin Router

Handles administrative endpoints for document management and system control.
"""

import os
import time
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request, Depends
from loguru import logger

from ..models.schemas import (
    DocumentUploadRequest, DocumentUploadResponse, SystemStatistics,
    DocumentProcessingResult
)
from ..core.ai_service import AIService
from ..core.config import get_settings
from ..dependencies import get_ai_service


router = APIRouter()


@router.post("/documents/process", response_model=DocumentUploadResponse)
async def process_documents(
    request: DocumentUploadRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> DocumentUploadResponse:
    """
    Process legal documents and add them to the vector database.
    
    This endpoint:
    1. Processes PDF documents from specified file paths
    2. Extracts and chunks the text
    3. Generates embeddings
    4. Adds to vector database for search
    """
    start_time = time.time()
    settings = get_settings()

    # FAISS flat has no per-document delete, so force_reprocess cannot be
    # honored in place — be honest about the one supported path.
    if request.force_reprocess:
        raise HTTPException(
            status_code=409,
            detail=(
                "Re-processing in place would duplicate chunks (FAISS flat cannot delete "
                "per document). Full rebuild required: stop the backend, delete "
                "vector_db/indian_law_db.index and vector_db/indian_law_db.metadata, "
                "then restart — auto-ingest rebuilds all documents."
            )
        )

    try:
        logger.info(f"Processing {len(request.file_paths)} documents")
        
        # Validate file paths
        validated_paths = []
        for file_path in request.file_paths:
            # Convert relative paths to absolute paths
            if not os.path.isabs(file_path):
                abs_path = os.path.join(settings.ASSETS_PATH, file_path)
            else:
                abs_path = file_path
            
            if not os.path.exists(abs_path):
                logger.warning(f"File not found: {abs_path}")
                continue
            
            if not abs_path.lower().endswith('.pdf'):
                logger.warning(f"Skipping non-PDF file: {abs_path}")
                continue
            
            validated_paths.append(abs_path)
        
        if not validated_paths:
            raise HTTPException(
                status_code=400,
                detail="No valid PDF files found in the specified paths"
            )
        
        # Process documents
        result = await ai_service.add_documents(validated_paths)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Build response
        response = DocumentUploadResponse(
            success=len(result["failed"]) == 0,
            processed=[
                DocumentProcessingResult(
                    file=item["file"],
                    chunks=item["chunks"]
                ) for item in result["processed"]
            ],
            failed=[
                DocumentProcessingResult(
                    file=item["file"],
                    error=item["error"]
                ) for item in result["failed"]
            ],
            skipped=[
                DocumentProcessingResult(
                    file=item["file"]
                ) for item in result.get("skipped", [])
            ],
            total_chunks=result["total_chunks"],
            processing_time_ms=processing_time
        )
        
        logger.info(f"Document processing completed in {processing_time:.2f}ms")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing documents: {str(e)}"
        )


@router.get("/documents/list")
async def list_available_documents() -> Dict[str, Any]:
    """
    List available PDF documents in the assets directory.
    """
    try:
        settings = get_settings()
        assets_path = settings.ASSETS_PATH
        
        if not os.path.exists(assets_path):
            return {"documents": [], "total": 0, "assets_path": assets_path}
        
        documents = []
        for file in os.listdir(assets_path):
            if file.lower().endswith('.pdf'):
                file_path = os.path.join(assets_path, file)
                file_stats = os.stat(file_path)
                
                documents.append({
                    "filename": file,
                    "path": file_path,
                    "size_bytes": file_stats.st_size,
                    "size_mb": round(file_stats.st_size / (1024 * 1024), 2),
                    "modified_time": file_stats.st_mtime
                })
        
        return {
            "documents": documents,
            "total": len(documents),
            "assets_path": assets_path
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )


@router.get("/statistics", response_model=SystemStatistics)
async def get_system_statistics(
    ai_service: AIService = Depends(get_ai_service)
) -> SystemStatistics:
    """
    Get detailed system statistics and health information.
    """
    try:
        stats = await ai_service.get_statistics()
        
        response = SystemStatistics(
            initialized=stats.get("initialized", False),
            llm_status=stats.get("llm_status", "unknown"),
            llm_message=stats.get("llm_message", ""),
            vector_db=stats.get("vector_db", {}),
            agents=stats.get("agents", 0),
            models=stats.get("models", {}),
            configuration=stats.get("configuration", {})
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving system statistics: {str(e)}"
        )


@router.post("/database/clear")
async def clear_vector_database(
    ai_service: AIService = Depends(get_ai_service),
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Clear the vector database (DANGEROUS - requires confirmation).
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Database clear operation requires explicit confirmation (confirm=true)"
        )
    
    try:
        logger.warning("Clearing vector database - all processed documents will be lost")
        
        if ai_service.vector_db:
            ai_service.vector_db.clear()
            logger.info("Vector database cleared successfully")
            
            return {
                "success": True,
                "message": "Vector database cleared successfully",
                "warning": "All processed documents have been removed from the database"
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Vector database not available"
            )
            
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing vector database: {str(e)}"
        )


@router.post("/database/save")
async def save_vector_database(
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Manually save the vector database to disk.
    """
    try:
        settings = get_settings()
        
        if ai_service.vector_db:
            db_path = os.path.join(settings.VECTOR_DB_PATH, "indian_law_db")
            ai_service.vector_db.save_index(db_path)
            
            return {
                "success": True,
                "message": "Vector database saved successfully",
                "path": db_path
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Vector database not available"
            )
            
    except Exception as e:
        logger.error(f"Error saving database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error saving vector database: {str(e)}"
        )


@router.post("/system/reinitialize")
async def reinitialize_system(
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Reinitialize the AI system (useful after configuration changes).
    """
    try:
        logger.info("Reinitializing AI system...")
        
        # Cleanup current state
        await ai_service.cleanup()
        
        # Reinitialize
        await ai_service.initialize()
        
        return {
            "success": True,
            "message": "AI system reinitialized successfully"
        }
        
    except Exception as e:
        logger.error(f"Error reinitializing system: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reinitializing system: {str(e)}"
        )