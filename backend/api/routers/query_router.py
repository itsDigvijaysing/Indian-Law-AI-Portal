"""
Query Router

Handles legal query processing endpoints.
"""

import json
import time
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from loguru import logger

from ..models.schemas import QueryRequest, QueryResponse, AdvancedQueryRequest
from ..core.ai_service import AIService
from ..core.config import get_settings
from ..core.rate_limiter import get_rate_limiter
from ..dependencies import get_ai_service, enforce_daily_limit, safe_error_detail


router = APIRouter()


def _to_query_response(result: Dict[str, Any], processing_time_ms: float) -> QueryResponse:
    """Map an AIService result dict onto the wire response.

    The advanced-only keys (reformulated_queries, fusion_statistics,
    applied_filters) are absent from the plain /query result and resolve to
    None, which is what that endpoint already returned.
    """
    return QueryResponse(
        answer=result.get('answer', ''),
        confidence_score=result.get('confidence_score', 0.0),
        agent_type=result.get('agent_type', 'Unknown'),
        sources=result.get('sources', []),
        reasoning_steps=result.get('reasoning_steps'),
        retrieved_documents=result.get('retrieved_documents'),
        retrieval_sources=result.get('retrieval_sources'),
        detected_category=result.get('detected_category'),
        reformulated_queries=result.get('reformulated_queries'),
        fusion_statistics=result.get('fusion_statistics'),
        applied_filters=result.get('applied_filters'),
        processing_time_ms=processing_time_ms
    )


@router.get("/usage")
async def usage_status() -> Dict[str, Any]:
    """Current global daily quota — powers the frontend's live 'N left today'
    counter and the rate-limit modal. Does not consume quota."""
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED:
        return {"enabled": False}
    status = await get_rate_limiter().status()
    return {"enabled": True, **status}


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(enforce_daily_limit)])
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

        result = await ai_service.process_query(query_request.query)

        processing_time = (time.time() - start_time) * 1000
        response = _to_query_response(result, processing_time)

        logger.info(f"Query processed successfully in {processing_time:.2f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=safe_error_detail("Error processing legal query", e)
        )


@router.post("/query/stream", dependencies=[Depends(enforce_daily_limit)])
async def stream_legal_query(
    query_request: QueryRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> StreamingResponse:
    """
    Stream a legal query answer over Server-Sent Events.

    Event order:
    1. `sources` — the numbered citation table (sent first so the UI can
       live-link [n] chips as tokens arrive)
    2. `token`  — answer text deltas
    3. `done`   — finalized answer, validated citations, confidence
    """
    start_time = time.time()

    async def event_stream():
        try:
            async for event, data in ai_service.stream_query(query_request.query):
                if event == 'done':
                    data['processing_time_ms'] = (time.time() - start_time) * 1000
                yield f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
        except Exception as e:
            logger.error(f"Error streaming query: {e}")
            msg = safe_error_detail("Error processing legal query", e)
            yield f"event: error\ndata: {json.dumps({'error': msg})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        # no-transform stops proxies (incl. the CRA dev proxy) from gzip-buffering
        # the stream, which would hold all tokens until the response completes
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.post("/query/advanced", response_model=QueryResponse, dependencies=[Depends(enforce_daily_limit)])
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

        filters_dict = query_request.filters.model_dump() if query_request.filters else None

        result = await ai_service.process_advanced_query(
            query=query_request.query,
            filters=filters_dict,
            fusion_queries=query_request.fusion_queries,
            explain_reasoning=query_request.explain_reasoning,
            confidence_threshold=filters_dict.get('confidence_threshold') if filters_dict else None
        )

        processing_time = (time.time() - start_time) * 1000
        response = _to_query_response(result, processing_time)

        logger.info(f"Advanced query processed in {processing_time:.2f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Error processing advanced query: {e}")
        raise HTTPException(
            status_code=500,
            detail=safe_error_detail("Error processing advanced legal query", e)
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
            detail=safe_error_detail("Error retrieving agent information", e)
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
        if any(term in query_lower for term in ['ipc', 'criminal', 'theft', 'murder', 'punishment', 'bns', 'bnss', 'bharatiya nyaya', 'sanhita']):
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
            detail=safe_error_detail("Error validating query", e)
        )