"""
AI Service Module

Central service that coordinates all AI components:
- Document processing and embedding
- Vector database operations
- Agent-based query processing
- RAG Fusion retrieval
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from loguru import logger


class _GroqResponse:
    """Mimics google.generativeai response shape (.text)."""
    def __init__(self, text: str):
        self.text = text


class GroqLLMClient:
    """Adapter giving Groq's chat-completions API the same .generate_content(prompt).text shape the agents expect."""

    def __init__(self, api_key: str, model: str):
        from groq import Groq
        self._client = Groq(api_key=api_key)
        self._model = model

    def generate_content(self, prompt: str) -> _GroqResponse:
        completion = self._client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self._model,
            temperature=0.3,
            max_tokens=2048,
        )
        return _GroqResponse(completion.choices[0].message.content or "")

# Handle imports for both module and direct execution
try:
    from .config import get_settings
    from ...adk import AgentRegistry, CriminalLawAgent, CivilLawAgent, ConstitutionalLawAgent, GeneralLegalAgent
    from ...rag import (
        DocumentProcessor, EmbeddingGenerator, DocumentEmbedder, 
        VectorDatabase, QueryReformulator, RAGFusionRetriever
    )
except ImportError:
    from api.core.config import get_settings
    from adk import AgentRegistry, CriminalLawAgent, CivilLawAgent, ConstitutionalLawAgent, GeneralLegalAgent
    from rag import (
        DocumentProcessor, EmbeddingGenerator, DocumentEmbedder, 
        VectorDatabase, QueryReformulator, RAGFusionRetriever
    )


class AIService:
    """Main AI service orchestrating all components"""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm_client = None
        self.embedding_generator = None
        self.document_embedder = None
        self.vector_db = None
        self.agent_registry = None
        self.query_reformulator = None
        self.rag_retriever = None
        self.document_processor = None
        self._initialized = False
        
        logger.info("AIService instance created")
    
    async def initialize(self):
        """Initialize all AI components"""
        if self._initialized:
            logger.warning("AIService already initialized")
            return
        
        try:
            logger.info("Initializing AI Service components...")
            
            # 1. Initialize Google AI client (optional - can work without)
            await self._initialize_llm_client()
            
            # 2. Initialize embedding components
            await self._initialize_embedding_components()
            
            # 3. Initialize vector database
            await self._initialize_vector_database()
            
            # 4. Initialize agents (can work with None llm_client for basic functions)
            await self._initialize_agents()
            
            # 5. Initialize RAG components
            await self._initialize_rag_components()
            
            # 6. Initialize document processor
            await self._initialize_document_processor()
            
            # 7. Load existing data if available
            await self._load_existing_data()

            # Mark initialized before auto-ingest so add_documents() can run.
            self._initialized = True

            # 8. Auto-ingest new documents from assets
            await self._auto_ingest_documents()
            
            if self.llm_client:
                logger.info("AI Service initialization completed successfully (full mode)")
            else:
                logger.info("AI Service initialization completed (limited mode - no LLM)")
                logger.info("Add your Google API key to .env to enable full features")
            
        except Exception as e:
            logger.error(f"Error initializing AI Service: {e}")
            raise
    
    async def _initialize_llm_client(self):
        """Initialize the LLM client (Groq or Gemini, per LLM_PROVIDER)."""
        provider = (self.settings.LLM_PROVIDER or "gemini").lower()
        try:
            if provider == "groq":
                if not self.settings.GROQ_API_KEY:
                    logger.warning("LLM_PROVIDER=groq but GROQ_API_KEY is empty. LLM features will be limited.")
                    self.llm_client = None
                    return
                self.llm_client = GroqLLMClient(self.settings.GROQ_API_KEY, self.settings.GROQ_MODEL)
                logger.info(f"LLM client initialized: groq/{self.settings.GROQ_MODEL}")
                return

            # Default: Gemini
            if not self.settings.GOOGLE_API_KEY or self.settings.GOOGLE_API_KEY == "your_google_api_key_here":
                logger.warning("Google API key not configured. LLM features will be limited.")
                logger.warning("Please set GOOGLE_API_KEY in your .env file")
                self.llm_client = None
                return

            genai.configure(api_key=self.settings.GOOGLE_API_KEY)
            self.llm_client = genai.GenerativeModel(self.settings.LLM_MODEL)
            logger.info(f"LLM client initialized: gemini/{self.settings.LLM_MODEL}")

        except Exception as e:
            logger.warning(f"Could not initialize LLM client ({provider}): {e}")
            logger.warning("The API will start but LLM features will be limited.")
            self.llm_client = None
    
    async def _initialize_embedding_components(self):
        """Initialize embedding generator and document embedder"""
        try:
            # Determine embedding model type and name
            # Google models: text-embedding-*, gemini-embedding-*, embedding-*
            embedding_model = self.settings.EMBEDDING_MODEL
            if (embedding_model.startswith("text-embedding") or 
                embedding_model.startswith("gemini-embedding") or
                embedding_model.startswith("embedding")):
                model_type = "google"
                model_name = embedding_model
            else:
                model_type = "sentence-transformers"
                model_name = embedding_model
            
            self.embedding_generator = EmbeddingGenerator(
                model_type=model_type,
                model_name=model_name
            )
            
            self.document_embedder = DocumentEmbedder(self.embedding_generator)
            
            logger.info(f"Embedding components initialized: {model_type}/{model_name}")
            
        except Exception as e:
            logger.error(f"Error initializing embedding components: {e}")
            raise
    
    async def _initialize_vector_database(self):
        """Initialize vector database"""
        try:
            dimension = self.embedding_generator.get_embedding_dimension()
            self.vector_db = VectorDatabase(
                dimension=dimension,
                index_type="flat"  # Start with simple flat index
            )
            
            logger.info(f"Vector database initialized with dimension: {dimension}")
            
        except Exception as e:
            logger.error(f"Error initializing vector database: {e}")
            raise
    
    async def _initialize_agents(self):
        """Initialize agent registry and domain-specific agents"""
        try:
            self.agent_registry = AgentRegistry()
            
            # Register domain-specific agents
            criminal_agent = CriminalLawAgent(self.llm_client)
            civil_agent = CivilLawAgent(self.llm_client)
            constitutional_agent = ConstitutionalLawAgent(self.llm_client)
            general_agent = GeneralLegalAgent(self.llm_client)
            
            self.agent_registry.register_agent(criminal_agent)
            self.agent_registry.register_agent(civil_agent)
            self.agent_registry.register_agent(constitutional_agent)
            self.agent_registry.register_agent(general_agent)
            
            logger.info(f"Agent registry initialized with {len(self.agent_registry.get_all_agents())} agents")
            
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            raise
    
    async def _initialize_rag_components(self):
        """Initialize RAG Fusion components"""
        try:
            self.query_reformulator = QueryReformulator(
                llm_client=self.llm_client,
                num_reformulations=self.settings.RAG_FUSION_QUERIES
            )
            
            self.rag_retriever = RAGFusionRetriever(
                vector_db=self.vector_db,
                embedding_generator=self.embedding_generator,
                query_reformulator=self.query_reformulator
            )
            
            logger.info("RAG Fusion components initialized")
            
        except Exception as e:
            logger.error(f"Error initializing RAG components: {e}")
            raise
    
    async def _initialize_document_processor(self):
        """Initialize document processor"""
        try:
            self.document_processor = DocumentProcessor(
                chunk_size=self.settings.CHUNK_SIZE,
                chunk_overlap=self.settings.CHUNK_OVERLAP
            )
            
            logger.info("Document processor initialized")
            
        except Exception as e:
            logger.error(f"Error initializing document processor: {e}")
            raise
    
    async def _load_existing_data(self):
        """Load existing vector database if available"""
        try:
            db_path = os.path.join(self.settings.VECTOR_DB_PATH, "indian_law_db")
            if os.path.exists(f"{db_path}.index") and os.path.exists(f"{db_path}.metadata"):
                success = self.vector_db.load_index(db_path)
                if success:
                    logger.info(f"Loaded existing vector database: {self.vector_db.get_document_count()} documents")
                else:
                    logger.warning("Failed to load existing vector database")
            else:
                logger.info("No existing vector database found - starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    async def _auto_ingest_documents(self):
        """Auto-detect and ingest new PDFs from assets directory on startup"""
        assets_path = self.settings.ASSETS_PATH
        if not os.path.exists(assets_path):
            logger.info("Assets directory not found, skipping auto-ingestion")
            return

        pdf_files = [f for f in os.listdir(assets_path) if f.lower().endswith('.pdf')]
        if not pdf_files:
            logger.info("No PDF files found in assets directory")
            return

        # Determine which documents are already ingested
        existing_docs = set()
        if self.vector_db and self.vector_db.metadata:
            for meta in self.vector_db.metadata:
                existing_docs.add(meta.get('document', ''))

        # Find new files not yet in the vector DB
        new_files = []
        for pdf_file in pdf_files:
            stem = Path(pdf_file).stem
            if stem not in existing_docs:
                new_files.append(os.path.join(assets_path, pdf_file))

        if not new_files:
            logger.info(f"All {len(pdf_files)} PDFs already ingested")
            return

        logger.info(f"Auto-ingesting {len(new_files)} new PDF documents...")
        try:
            result = await self.add_documents(new_files)
            logger.info(
                f"Auto-ingestion complete: {len(result['processed'])} processed, "
                f"{len(result['failed'])} failed, {result['total_chunks']} chunks"
            )
        except Exception as e:
            logger.error(f"Error during auto-ingestion: {e}")

    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Main query processing pipeline:
        1. Use RAG Fusion to retrieve relevant documents
        2. Select appropriate agent
        3. Generate response
        """
        if not self._initialized:
            raise RuntimeError("AI Service not initialized")
        
        try:
            logger.info(f"Processing query: {query[:100]}...")
            
            # Step 1: Retrieve relevant documents using RAG Fusion
            retrieved_docs = self.rag_retriever.retrieve(
                query=query,
                top_k=self.settings.TOP_K_RETRIEVAL
            )
            
            # Step 2: Extract context text
            context_texts = [doc.get('text', '') for doc in retrieved_docs]
            
            # Step 3: Select appropriate agent
            selected_agent = self.agent_registry.select_agent(query, context_texts)
            
            if not selected_agent:
                # Fallback to general agent
                agents = self.agent_registry.get_all_agents()
                selected_agent = next((a for a in agents if a.name == "General Legal Agent"), None)
            
            # Step 4: Generate response using selected agent
            if selected_agent:
                response = selected_agent.process_query(query, context_texts)
                
                # Add retrieval metadata
                response_dict = response.model_dump()
                response_dict['retrieved_documents'] = len(retrieved_docs)
                response_dict['retrieval_sources'] = [
                    {
                        'document': doc.get('document', ''),
                        'section': doc.get('section', ''),
                        'similarity_score': doc.get('similarity_score', 0),
                        'fusion_score': doc.get('fusion_score', 0)
                    }
                    for doc in retrieved_docs[:5]  # Top 5 sources
                ]
                
                logger.info(f"Query processed successfully by {selected_agent.name}")
                return response_dict
            
            else:
                logger.error("No suitable agent found for query")
                return {
                    "answer": "I apologize, but I couldn't find a suitable legal expert to handle your query. Please try rephrasing your question.",
                    "confidence_score": 0.0,
                    "sources": [],
                    "agent_type": "None",
                    "error": "No suitable agent found"
                }
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            error_str = str(e).lower()
            if any(term in error_str for term in ['quota', 'resourceexhausted', '429', 'rate limit']):
                message = "API quota exceeded. Your retrieved documents are still available but AI analysis is temporarily unavailable."
            elif any(term in error_str for term in ['connection', 'timeout', 'unreachable', 'dns']):
                message = "Could not reach the AI service. Please check your network connection and try again."
            else:
                message = f"An error occurred while processing your query ({type(e).__name__}). Please try again later."
            return {
                "answer": message,
                "confidence_score": 0.0,
                "sources": [],
                "agent_type": "Error",
                "error": str(e)
            }
    
    async def process_advanced_query(
        self,
        query: str,
        filters: Optional[Dict] = None,
        fusion_queries: Optional[int] = None,
        explain_reasoning: bool = False,
        confidence_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Advanced query processing with filters, custom fusion, and reasoning.
        """
        if not self._initialized:
            raise RuntimeError("AI Service not initialized")

        try:
            logger.info(f"Processing advanced query: {query[:100]}...")

            # Temporarily override fusion query count if specified
            original_num = self.query_reformulator.num_reformulations
            if fusion_queries is not None:
                self.query_reformulator.num_reformulations = fusion_queries

            try:
                # Step 1: Retrieve documents
                retrieved_docs = self.rag_retriever.retrieve(
                    query=query,
                    top_k=self.settings.TOP_K_RETRIEVAL
                )

                # Capture reformulated queries for explain mode
                reformulated = self.query_reformulator.reformulate_query(query) if explain_reasoning else None
            finally:
                # Restore original fusion count
                self.query_reformulator.num_reformulations = original_num

            # Step 2: Apply document type filters
            if filters and filters.get('document_types'):
                allowed_types = set(filters['document_types'])
                retrieved_docs = [
                    doc for doc in retrieved_docs
                    if doc.get('document', '') in allowed_types
                ]

            # Step 3: Extract context and select agent
            context_texts = [doc.get('text', '') for doc in retrieved_docs]
            selected_agent = self.agent_registry.select_agent(query, context_texts)
            if not selected_agent:
                agents = self.agent_registry.get_all_agents()
                selected_agent = next((a for a in agents if a.name == "General Legal Agent"), None)

            # Step 4: Generate response
            if selected_agent:
                response = selected_agent.process_query(query, context_texts)
                response_dict = response.model_dump()

                # Confidence threshold warning
                if confidence_threshold and response_dict.get('confidence_score', 0) < confidence_threshold:
                    response_dict['answer'] += (
                        f"\n\n**Note:** The confidence score ({response_dict['confidence_score']:.1%}) "
                        f"is below the requested threshold ({confidence_threshold:.1%})."
                    )

                # Add retrieval metadata
                response_dict['retrieved_documents'] = len(retrieved_docs)
                response_dict['retrieval_sources'] = [
                    {
                        'document': doc.get('document', ''),
                        'section': doc.get('section', ''),
                        'similarity_score': doc.get('similarity_score', 0),
                        'fusion_score': doc.get('fusion_score', 0)
                    }
                    for doc in retrieved_docs[:5]
                ]

                # Add advanced metadata
                if explain_reasoning:
                    response_dict['reformulated_queries'] = reformulated
                    response_dict['fusion_statistics'] = self.rag_retriever.get_fusion_statistics(retrieved_docs)

                if filters:
                    response_dict['applied_filters'] = filters

                logger.info(f"Advanced query processed by {selected_agent.name}")
                return response_dict

            return {
                "answer": "No suitable agent found. Please try rephrasing your question.",
                "confidence_score": 0.0,
                "sources": [],
                "agent_type": "None"
            }

        except Exception as e:
            logger.error(f"Error processing advanced query: {e}")
            return {
                "answer": "An error occurred while processing your advanced query.",
                "confidence_score": 0.0,
                "sources": [],
                "agent_type": "Error",
                "error": str(e)
            }

    async def add_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process and add new documents to the vector database"""
        if not self._initialized:
            raise RuntimeError("AI Service not initialized")
        
        try:
            results = {"processed": [], "failed": [], "total_chunks": 0}
            
            for file_path in file_paths:
                try:
                    logger.info(f"Processing document: {file_path}")
                    
                    # Process document
                    chunks = self.document_processor.process_document(file_path)
                    if not chunks:
                        results["failed"].append({"file": file_path, "error": "No text extracted"})
                        continue
                    
                    # Generate embeddings
                    enriched_chunks = self.document_embedder.embed_chunks(chunks)
                    
                    # Add to vector database
                    self.vector_db.add_documents(enriched_chunks)
                    
                    results["processed"].append({
                        "file": file_path,
                        "chunks": len(enriched_chunks)
                    })
                    results["total_chunks"] += len(enriched_chunks)
                    
                    logger.info(f"Successfully processed {file_path}: {len(enriched_chunks)} chunks")
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    results["failed"].append({"file": file_path, "error": str(e)})
            
            # Save updated database
            if results["total_chunks"] > 0:
                db_path = os.path.join(self.settings.VECTOR_DB_PATH, "indian_law_db")
                self.vector_db.save_index(db_path)
                logger.info("Vector database saved")
            
            return results
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        if not self._initialized:
            return {"error": "AI Service not initialized"}
        
        try:
            stats = {
                "initialized": self._initialized,
                "llm_status": "active" if self.llm_client else "not_configured",
                "llm_message": "" if self.llm_client else "Add GOOGLE_API_KEY to .env for full AI features",
                "vector_db": self.vector_db.get_statistics() if self.vector_db else {},
                "agents": len(self.agent_registry.get_all_agents()) if self.agent_registry else 0,
                "models": {
                    "llm": self.settings.LLM_MODEL,
                    "embedding": self.settings.EMBEDDING_MODEL
                },
                "configuration": {
                    "chunk_size": self.settings.CHUNK_SIZE,
                    "top_k_retrieval": self.settings.TOP_K_RETRIEVAL,
                    "rag_fusion_queries": self.settings.RAG_FUSION_QUERIES
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.vector_db and self._initialized:
                # Save vector database before cleanup
                db_path = os.path.join(self.settings.VECTOR_DB_PATH, "indian_law_db")
                self.vector_db.save_index(db_path)
                logger.info("Vector database saved during cleanup")
            
            self._initialized = False
            logger.info("AI Service cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")