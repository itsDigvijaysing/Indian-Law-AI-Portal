"""
API Request/Response Models

Pydantic models for API request and response validation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Query Models
class QueryRequest(BaseModel):
    """Request model for legal queries"""
    query: str = Field(..., min_length=1, max_length=1000, description="Legal question or query")
    include_sources: bool = Field(True, description="Include source references in response")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of retrieval results")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What is the punishment for theft under IPC?",
                "include_sources": True,
                "max_results": 10
            }
        }


class SourceReference(BaseModel):
    """Model for source references in responses"""
    document: str = Field(..., description="Source document name")
    section: str = Field(..., description="Section or chapter in document")
    similarity_score: float = Field(..., ge=0, le=1, description="Similarity score")
    fusion_score: Optional[float] = Field(None, description="RAG Fusion score")


class QueryResponse(BaseModel):
    """Response model for legal queries"""
    answer: str = Field(..., description="AI-generated answer to the legal query")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in the answer")
    agent_type: str = Field(..., description="Type of legal agent that processed the query")
    sources: List[str] = Field(default=[], description="List of legal references")
    reasoning_steps: Optional[List[str]] = Field(None, description="Agent reasoning process")
    retrieved_documents: Optional[int] = Field(None, description="Number of documents retrieved")
    retrieval_sources: Optional[List[SourceReference]] = Field(None, description="Detailed source information")
    processing_time_ms: Optional[float] = Field(None, description="Query processing time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "answer": "According to Section 379 of the Indian Penal Code, theft is punishable with imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
                "confidence_score": 0.92,
                "agent_type": "Criminal Law",
                "sources": ["Section 379 - IPC", "Section 381 - IPC"],
                "reasoning_steps": [
                    "Identified criminal law query about theft",
                    "Retrieved relevant IPC sections",
                    "Applied criminal law reasoning",
                    "Formatted response with legal references"
                ],
                "retrieved_documents": 8,
                "processing_time_ms": 1250.5,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


# Document Management Models
class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""
    file_paths: List[str] = Field(..., description="List of file paths to process")
    force_reprocess: bool = Field(False, description="Force reprocessing even if already processed")
    
    class Config:
        schema_extra = {
            "example": {
                "file_paths": ["/assets/IPC.pdf", "/assets/CrPC.pdf"],
                "force_reprocess": False
            }
        }


class DocumentProcessingResult(BaseModel):
    """Result model for document processing"""
    file: str = Field(..., description="File path")
    chunks: Optional[int] = Field(None, description="Number of chunks created")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class DocumentUploadResponse(BaseModel):
    """Response model for document upload"""
    success: bool = Field(..., description="Whether the operation was successful")
    processed: List[DocumentProcessingResult] = Field(default=[], description="Successfully processed files")
    failed: List[DocumentProcessingResult] = Field(default=[], description="Failed to process files")
    total_chunks: int = Field(0, description="Total number of chunks added to database")
    processing_time_ms: float = Field(..., description="Total processing time")
    timestamp: datetime = Field(default_factory=datetime.now, description="Processing timestamp")


# System Status Models
class SystemHealth(BaseModel):
    """System health status model"""
    status: str = Field(..., description="Overall system status")
    ai_service_initialized: bool = Field(..., description="Whether AI service is initialized")
    vector_database_status: str = Field(..., description="Vector database status")
    total_documents: int = Field(0, description="Total documents in database")
    available_agents: int = Field(0, description="Number of available agents")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")


class SystemStatistics(BaseModel):
    """Detailed system statistics model"""
    initialized: bool = Field(..., description="System initialization status")
    vector_db: Dict[str, Any] = Field(default={}, description="Vector database statistics")
    agents: int = Field(0, description="Number of registered agents")
    models: Dict[str, str] = Field(default={}, description="AI models in use")
    configuration: Dict[str, Any] = Field(default={}, description="System configuration")
    uptime: Optional[str] = Field(None, description="System uptime")


# Error Models
class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Query processing failed due to invalid input",
                "status_code": 400,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


# Agent Models
class AgentInfo(BaseModel):
    """Information about a legal agent"""
    name: str = Field(..., description="Agent name")
    domain: str = Field(..., description="Legal domain specialty")
    keywords: List[str] = Field(default=[], description="Domain keywords")


class AgentListResponse(BaseModel):
    """Response model for listing available agents"""
    agents: List[AgentInfo] = Field(..., description="List of available agents")
    total_agents: int = Field(..., description="Total number of agents")


# Search and Filter Models
class SearchFilters(BaseModel):
    """Filters for search and retrieval"""
    document_types: Optional[List[str]] = Field(None, description="Filter by document types")
    agent_types: Optional[List[str]] = Field(None, description="Filter by agent types")
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1, description="Minimum confidence score")
    date_range: Optional[Dict[str, datetime]] = Field(None, description="Date range filter")


class AdvancedQueryRequest(QueryRequest):
    """Advanced query request with filters"""
    filters: Optional[SearchFilters] = Field(None, description="Additional search filters")
    explain_reasoning: bool = Field(False, description="Include detailed reasoning explanation")
    fusion_queries: Optional[int] = Field(None, ge=1, le=10, description="Number of RAG Fusion queries")


# Validation Models
class QueryValidation(BaseModel):
    """Query validation result"""
    is_valid: bool = Field(..., description="Whether the query is valid")
    issues: List[str] = Field(default=[], description="List of validation issues")
    suggestions: List[str] = Field(default=[], description="Suggestions for improvement")
    estimated_domain: Optional[str] = Field(None, description="Estimated legal domain")