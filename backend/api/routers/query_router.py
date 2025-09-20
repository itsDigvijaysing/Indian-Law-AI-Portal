"""
Query Router

Handles legal query processing endpoints.
"""

import time
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request, Depends
from loguru import logger

from ..models.schemas import QueryRequest, QueryResponse, AdvancedQueryRequest, ErrorResponse
from ..core.ai_service import AIService


router = APIRouter()


def get_ai_service(request: Request) -> AIService:
    """Dependency to get AI service from app state"""
    if not hasattr(request.app.state, 'ai_service'):
        raise HTTPException(status_code=503, detail="AI service not available")
    return request.app.state.ai_service


@router.post("/query", response_model=QueryResponse)
async def process_legal_query(
    query_request: QueryRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> QueryResponse:
    """
    Process a legal query and return AI-generated response.
    
    This endpoint:
    1. Validates the input query
    2. Uses RAG Fusion to retrieve relevant legal documents
    3. Selects appropriate domain expert agent
    4. Generates comprehensive legal response
    """
    start_time = time.time()
    
    try:
        logger.info(f"Received query: {query_request.query[:100]}...")
        
        # Process query through AI service
        result = await ai_service.process_query(query_request.query)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Build response
        response = QueryResponse(
            answer=result.get('answer', ''),
            confidence_score=result.get('confidence_score', 0.0),
            agent_type=result.get('agent_type', 'Unknown'),
            sources=result.get('sources', []),
            reasoning_steps=result.get('reasoning_steps'),
            retrieved_documents=result.get('retrieved_documents'),
            retrieval_sources=result.get('retrieval_sources'),
            processing_time_ms=processing_time
        )
        
        logger.info(f"Query processed successfully in {processing_time:.2f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing legal query: {str(e)}"
        )


@router.post("/query/advanced", response_model=QueryResponse)
async def process_advanced_query(
    query_request: AdvancedQueryRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> QueryResponse:
    """
    Process an advanced legal query with additional options and filters.
    
    Supports:
    - Custom RAG Fusion query count
    - Document type filtering
    - Detailed reasoning explanation
    - Confidence thresholds
    """
    start_time = time.time()
    
    try:
        logger.info(f"Received advanced query: {query_request.query[:100]}...")
        
        # TODO: Implement advanced filtering logic
        # For now, process as regular query
        result = await ai_service.process_query(query_request.query)
        
        processing_time = (time.time() - start_time) * 1000
        
        response = QueryResponse(
            answer=result.get('answer', ''),
            confidence_score=result.get('confidence_score', 0.0),
            agent_type=result.get('agent_type', 'Unknown'),
            sources=result.get('sources', []),
            reasoning_steps=result.get('reasoning_steps'),
            retrieved_documents=result.get('retrieved_documents'),
            retrieval_sources=result.get('retrieval_sources'),
            processing_time_ms=processing_time
        )
        
        logger.info(f"Advanced query processed in {processing_time:.2f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Error processing advanced query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing advanced legal query: {str(e)}"
        )


@router.get("/agents")
async def list_available_agents(
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Get list of available legal domain agents.
    """
    try:
        if not ai_service.agent_registry:
            raise HTTPException(status_code=503, detail="Agent registry not available")
        
        agents = ai_service.agent_registry.get_all_agents()
        
        agent_info = []
        for agent in agents:
            agent_info.append({
                "name": agent.name,
                "domain": agent.domain,
                "keywords": agent.get_domain_keywords()[:10]  # Limit keywords for API response
            })
        
        return {
            "agents": agent_info,
            "total_agents": len(agents)
        }
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving agent information: {str(e)}"
        )


@router.post("/validate")
async def validate_query(
    query_request: QueryRequest
) -> Dict[str, Any]:
    """
    Validate a legal query without processing it.
    
    Checks for:
    - Query length and content
    - Legal domain classification
    - Potential issues or suggestions
    """
    try:
        query = query_request.query.strip()
        
        validation_result = {
            "is_valid": True,
            "issues": [],
            "suggestions": [],
            "estimated_domain": None
        }
        
        # Basic validation
        if len(query) < 10:
            validation_result["is_valid"] = False
            validation_result["issues"].append("Query is too short. Please provide more details.")
        
        if len(query) > 1000:
            validation_result["issues"].append("Query is very long. Consider breaking it into smaller questions.")
        
        # Domain estimation
        query_lower = query.lower()
        if any(term in query_lower for term in ['ipc', 'criminal', 'theft', 'murder', 'punishment']):
            validation_result["estimated_domain"] = "Criminal Law"
        elif any(term in query_lower for term in ['cpc', 'civil', 'contract', 'property', 'suit']):
            validation_result["estimated_domain"] = "Civil Law"
        elif any(term in query_lower for term in ['constitution', 'fundamental rights', 'article']):
            validation_result["estimated_domain"] = "Constitutional Law"
        else:
            validation_result["estimated_domain"] = "General Law"
        
        # Suggestions
        if '?' not in query:
            validation_result["suggestions"].append("Consider phrasing your query as a question for better results.")
        
        if not any(term in query_lower for term in ['section', 'act', 'law', 'legal', 'code']):
            validation_result["suggestions"].append("Include specific legal terms like 'section', 'act', or 'code' for more precise results.")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error validating query: {str(e)}"
        )