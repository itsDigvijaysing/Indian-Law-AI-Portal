"""
AI Service Module

Central service that coordinates all AI components:
- Document processing and embedding
- Vector database operations
- Agent-based query processing
- RAG Fusion retrieval
"""

import os
import re
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from loguru import logger


# Handle imports for both module and direct execution
try:
    from .config import get_settings, VECTOR_DB_NAME
    from .llm_clients import GroqLLMClient
    from ...adk import AgentRegistry
    from ...rag import (
        DocumentProcessor, EmbeddingGenerator, DocumentEmbedder,
        VectorDatabase, QueryReformulator, RAGFusionRetriever
    )
except ImportError:
    from api.core.config import get_settings, VECTOR_DB_NAME
    from api.core.llm_clients import GroqLLMClient
    from adk import AgentRegistry
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

            # Every component below tolerates a None llm_client and degrades to
            # retrieval-only, so a missing API key never blocks startup.
            await self._initialize_llm_client()
            await self._initialize_embedding_components()
            await self._initialize_vector_database()
            await self._initialize_agents()
            await self._initialize_rag_components()
            await self._initialize_document_processor()
            await self._load_existing_data()

            # Mark initialized before auto-ingest so add_documents() can run.
            self._initialized = True
            await self._auto_ingest_documents()

            if self.llm_client:
                logger.info("AI Service initialization completed successfully (full mode)")
            else:
                logger.info("AI Service initialization completed (limited mode - no LLM)")
                logger.info("Set GROQ_API_KEY (or GOOGLE_API_KEY with LLM_PROVIDER=gemini) in .env to enable full features")
            
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
            # Google's hosted models are the text-embedding-*, gemini-embedding-*
            # and embedding-* families; anything else is a local ST model.
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
                index_type="flat",
                embedding_model=self.settings.EMBEDDING_MODEL
            )
            
            logger.info(f"Vector database initialized with dimension: {dimension}")
            
        except Exception as e:
            logger.error(f"Error initializing vector database: {e}")
            raise
    
    async def _initialize_agents(self):
        """Initialize agent registry with one domain agent per legal domain."""
        try:
            self.agent_registry = AgentRegistry()

            try:
                from ...adk.agents.domain_agents import build_domain_agents
            except ImportError:
                from adk.agents.domain_agents import build_domain_agents
            for agent in build_domain_agents(self.llm_client):
                self.agent_registry.register_agent(agent)

            logger.info(f"Agent registry initialized with {len(self.agent_registry.get_all_agents())} domain agents")
            
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
            
            reranker = None
            if self.settings.RERANK_ENABLED:
                try:
                    from sentence_transformers import CrossEncoder
                    reranker = CrossEncoder(self.settings.RERANK_MODEL)
                    logger.info(f"CrossEncoder reranker loaded: {self.settings.RERANK_MODEL}")
                except Exception as e:
                    logger.warning(f"Could not load reranker ({e}); continuing without reranking")

            self.rag_retriever = RAGFusionRetriever(
                vector_db=self.vector_db,
                embedding_generator=self.embedding_generator,
                query_reformulator=self.query_reformulator,
                extra_retrievers=[self.vector_db.keyword_search, self.vector_db.label_search],
                reranker=reranker,
                rerank_candidates=self.settings.RERANK_CANDIDATES
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
            db_path = os.path.join(self.settings.VECTOR_DB_PATH, VECTOR_DB_NAME)
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

        # Registry-coverage guard: every PDF should have legal-hierarchy metadata,
        # or its chunks route as "General" (no category/era grounding).
        try:
            from ...rag.document_registry import is_registered
        except ImportError:
            from rag.document_registry import is_registered
        unregistered = [f for f in pdf_files if not is_registered(Path(f).stem)]
        if unregistered:
            logger.warning(
                f"{len(unregistered)} PDF(s) have no document_registry entry and will route as "
                f"'General' (no category/era metadata): {unregistered}. Add them to "
                f"backend/rag/document_registry.py."
            )

        existing_docs = set()
        if self.vector_db and self.vector_db.metadata:
            for meta in self.vector_db.metadata:
                existing_docs.add(meta.get('document', ''))

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

    # Detects the grounded-refusal sentence the shared prompt mandates
    _REFUSAL_MARKER = "do not contain sufficient information"

    # A provision number asserted in prose ("Section 66A", "Article 21", "Rule 14")
    _PROVISION_RE = re.compile(
        r'\b(?:Sections?|Articles?|Rules?)\s+(\d+[A-Z]{0,2})\b', re.IGNORECASE
    )

    @classmethod
    def _supported_provisions(cls, sources: List[Dict]) -> set:
        """Provision numbers that genuinely occur in the retrieved sources.

        Collected from each source's own label, its legal_sections metadata, and
        any provision named inside its text, including bare statute headings
        ("303. Theft.—"), which is how India Code prints the provision itself.
        """
        supported = set()
        for source in sources:
            blob = f"{source.get('section') or ''}\n{source.get('text') or ''}"
            for ref in source.get('legal_sections') or []:
                blob += f"\n{ref}"
            for match in cls._PROVISION_RE.finditer(blob):
                supported.add(match.group(1).upper())
            for match in re.finditer(r'(?:^|\s)(\d+[A-Z]{0,2})\.\s*[A-Z(]', blob):
                supported.add(match.group(1).upper())
        return supported

    @classmethod
    def _unsupported_provisions(cls, answer: str, sources: List[Dict]) -> List[str]:
        """Provision numbers the answer asserts that no retrieved source contains.

        The [n] validator only proves a marker points at a real source, not that
        the provision named beside it exists. Models recall famous section
        numbers from training (IT Act 66A, struck down in 2015 and absent from
        this corpus) and attach them to a neighbouring source's marker, which
        reads as a citation but is a fabrication.
        """
        claimed = {m.group(1).upper() for m in cls._PROVISION_RE.finditer(answer)}
        return sorted(claimed - cls._supported_provisions(sources))

    def _number_sources(self, retrieved_docs: List[Dict]) -> List[Dict]:
        """Top-K retrieved docs become the numbered citation set [1]..[K]."""
        top = retrieved_docs[:self.settings.CITED_SOURCES_K]
        return [{**doc, 'id': i + 1} for i, doc in enumerate(top)]

    @staticmethod
    def _source_ref(source: Dict) -> Dict:
        """Shape a numbered source dict into the SourceReference payload."""
        return {
            'id': source.get('id'),
            'document': source.get('document', ''),
            'document_title': source.get('document_title', ''),
            'section': source.get('section', ''),
            'category': source.get('category', ''),
            'era': source.get('era', ''),
            'similarity_score': source.get('similarity_score', 0),
            'fusion_score': source.get('fusion_score', 0),
            'rerank_score': source.get('rerank_score'),
            'snippet': source.get('text', '')[:300],
            'page_start': source.get('page_start') or None,
            'page_end': source.get('page_end') or None,
            'legal_sections': source.get('legal_sections', []),
            'type': source.get('type', 'pdf'),
            'cited': source.get('cited', False),
        }

    @staticmethod
    def _strip_dashes(text: str) -> str:
        """Remove em/en dashes (the 'AI writing' tell). Guaranteed clean output.
        Dash after punctuation collapses into it; numeric ranges become hyphens;
        a dash before a new clause becomes a period; everything else a comma."""
        # Odd unicode hyphens (non-breaking, figure) → plain hyphen first.
        text = text.replace('‑', '-').replace('‒', '-').replace('‐', '-')
        text = re.sub(r'([.,:;!?])\s*[—–]\s*', r'\1 ', text)   # "theft.—Whoever" → "theft. Whoever"
        text = re.sub(r'(\d)\s*[–—]\s*(\d)', r'\1-\2', text)   # ranges "10–11" → "10-11"
        text = re.sub(r'\s*[—–]\s+([A-Z(])', r'. \1', text)    # " — Whoever" (new clause) → ". Whoever"
        text = re.sub(r'\s*[—–]\s*', ', ', text)               # remaining → comma
        return text

    def _finalize_cited_response(self, response_dict: Dict, sources: List[Dict]):
        """Validate [n] markers, mark cited sources, and score confidence honestly."""
        answer = self._strip_dashes(response_dict.get('answer', '') or '')

        # Normalize marker variants the model might emit: [Source 3], [ 3 ] → [3]
        answer = re.sub(r'\[\s*(?:source|ref(?:erence)?)\s*(\d+)\s*\]', r'[\1]', answer, flags=re.IGNORECASE)
        answer = re.sub(r'\[\s*(\d+)\s*\]', r'[\1]', answer)
        # Expand grouped citation forms: [1, 2] → [1][2]; ranges [1-3] → [1][2][3].
        # Only when ALL numbers are plausible citation ids (≤ 50) — leaves quoted
        # legal literals like "[1950, 27]" (a citation) vs "[2019-2020]" (a year
        # range) alone; the latter's numbers exceed the source count and stay text.
        def _expand_group(m):
            nums = [n.strip() for n in re.split(r'[,;]', m.group(1))]
            if all(int(n) <= 50 for n in nums):
                return ''.join(f'[{n}]' for n in nums)
            return m.group(0)
        answer = re.sub(r'\[(\d+(?:\s*[,;]\s*\d+)+)\]', _expand_group, answer)
        answer = re.sub(
            r'\[(\d+)\s*[-–]\s*(\d+)\]',
            lambda m: ''.join(f'[{i}]' for i in range(int(m.group(1)), int(m.group(2)) + 1))
            if int(m.group(1)) < int(m.group(2)) <= min(int(m.group(1)) + 10, 50) else m.group(0),
            answer
        )

        valid_ids = {source['id'] for source in sources}
        # Near-range numbers are hallucinated citations and get stripped; anything
        # well above the source count is quoted legal text — law-report years
        # "[1963]", judgment paragraph cites "[99]" — and must be left intact.
        strip_ceiling = (max(valid_ids) if valid_ids else 0) + 12
        cited_ids = set()

        def _validate(match):
            n = int(match.group(1))
            if n in valid_ids:
                cited_ids.add(n)
                return match.group(0)
            if n <= strip_ceiling:
                return ''  # a citation attempt at a source that doesn't exist
            return match.group(0)

        answer = re.sub(r'\[(\d+)\]', _validate, answer)

        # Bracket-only detection misses a model that names a source's exact
        # section in prose without a marker (e.g. "Section 302 IPC provides...").
        # That reads as "uncited" and craters confidence even though the answer
        # is correctly grounded. Give each such source a second chance: if its
        # section label is asserted verbatim and nothing already sits there,
        # insert the missing [n] so it counts as cited and the frontend's
        # chip-to-card jump still has a marker to find.
        #
        # The trailing lookahead is LOAD-BEARING: section labels are prefixes of
        # one another ("Section 13" inside "Section 138"/"Section 13B"/"Section
        # 13-A", "Section 6" inside "Section 60"). Matching without it spliced a
        # marker INTO the number — "Section 138" rendered as "Section 13[1]8",
        # showing the reader a wrong section and crediting the wrong source.
        for source in sources:
            if source['id'] in cited_ids:
                continue
            label = source.get('section', '')
            if not label or label in ('Front matter', 'Full-Document'):
                continue
            match = re.search(rf'\b{re.escape(label)}(?![\w\-])', answer, re.IGNORECASE)
            if not match:
                continue
            tail = answer[match.end():match.end() + 6]
            if re.match(r'\s*\[\d+\]', tail):
                continue  # a marker already sits here for some other source
            answer = answer[:match.end()] + f'[{source["id"]}]' + answer[match.end():]
            cited_ids.add(source['id'])

        response_dict['answer'] = answer
        for source in sources:
            source['cited'] = source['id'] in cited_ids

        # Legal references now come from cited chunks' real metadata,
        # replacing the old regex scrape of context text.
        references = []
        for source in sources:
            if not source['cited']:
                continue
            label = source.get('section', '')
            if label and label not in ('Front matter', 'Full-Document'):
                references.append(f"{label} ({source.get('document', '')})")
            for legal_ref in source.get('legal_sections', [])[:2]:
                references.append(f"{legal_ref} ({source.get('document', '')})")
        response_dict['sources'] = list(dict.fromkeys(references))[:8]

        # Citation-driven confidence: refusals score low, uncited answers are
        # suspect, cited answers scale with citation count and source similarity.
        # The prompt mandates refusals START with the sentinel sentence — only
        # check the head, so a mid-answer hedging sentence ("the documents do
        # not contain X, however…") can't crush a fully cited answer.
        if self._REFUSAL_MARKER in answer[:160].lower():
            confidence = 0.15
        elif not cited_ids:
            confidence = 0.35
        else:
            cited_sources = [s for s in sources if s['cited']]
            mean_similarity = sum(s.get('similarity_score', 0) for s in cited_sources) / len(cited_sources)
            confidence = min(0.95, 0.35 + 0.07 * len(cited_ids) + 0.2 * mean_similarity)

        # An answer naming a provision no source contains is not grounded, however
        # well its [n] markers validate. Surface it and cap the score so a
        # fabricated section number can never be presented with confidence.
        unsupported = self._unsupported_provisions(answer, sources)
        if unsupported:
            logger.warning(
                f"Unsupported provision(s) asserted, not in retrieved sources: "
                f"{', '.join(unsupported)}"
            )
            confidence = min(confidence, 0.3)
        response_dict['unsupported_references'] = unsupported

        response_dict['confidence_score'] = round(confidence, 3)

    @staticmethod
    def _classify_llm_error(error_str: str) -> str:
        """User-facing message for an LLM/provider failure."""
        error_lower = error_str.lower()
        if any(term in error_lower for term in ['quota', 'resourceexhausted', '429', 'rate limit']):
            return "The AI provider's rate limit was hit, so no answer could be generated."
        if any(term in error_lower for term in ['connection', 'timeout', 'unreachable', 'dns']):
            return "Could not reach the AI service. Please check your network connection and try again."
        return "An error occurred while generating the answer. Please try again later."

    @staticmethod
    def _coverage_areas() -> List[str]:
        """Legal areas the corpus covers (from the registry — single source of truth)."""
        try:
            from ...rag.document_registry import all_categories
        except ImportError:
            from rag.document_registry import all_categories
        return all_categories()

    def _refusal_response(self) -> Dict[str, Any]:
        """Grounded refusal when retrieval finds nothing — no LLM call, no guessing."""
        return {
            "answer": (
                "The provided legal documents do not contain information to answer this question. "
                "This portal is grounded strictly in official Indian statutes covering: "
                + ", ".join(self._coverage_areas()) + " law."
            ),
            "confidence_score": 0.0,
            "sources": [],
            "agent_type": "None",
            "retrieved_documents": 0,
            "retrieval_sources": [],
        }

    # Meta / capability questions ("what can you do", "which laws do you cover") are
    # NOT legal questions — grounded retrieval would answer them with irrelevant
    # statute text at false-high confidence. Detect and answer honestly instead.
    # Every alternative is END-ANCHORED so a meta phrase used as a PREFIX of a real
    # legal query ("how do you work OUT the limitation period", "what can I ask FOR
    # as damages") does NOT trigger — only when the meta phrase ends the question.
    _META_RE = re.compile(
        r'(?:'
        r'what can you (?:do|help(?: me)?(?: with)?|answer)'
        r'|what (?:areas|kinds|types|type|categories) of law (?:do|can) you(?:\s+\w+)*'
        r'|which (?:areas|laws|acts|statutes|documents) (?:do|can) you (?:cover|handle|answer|help|support)'
        r'|(?:what are |describe |tell me )?your capabilit\w*'
        r'|who are you'
        r'|what (?:is|are) (?:this|you)(?: portal| tool| system| app| assistant)?'
        r'|how (?:do|does) (?:you|this|it) work'
        r'|what can i (?:ask|query)(?: you| about)?'
        r'|what do you (?:do|know)(?: about yourself)?'
        r')[\s?.!]*$',
        re.IGNORECASE)

    def _is_meta_query(self, query: str) -> bool:
        return bool(self._META_RE.search((query or "").strip()))

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Collapse whitespace and drop trailing ?/!/. so 'X' and 'X?' reach the
        classifier, reformulator and retriever as identical text. Without this,
        a bare trailing '?' was enough to send the LLM-driven query reformulation
        (rag_fusion.QueryReformulator) down a different path, changing which
        chunks got retrieved and producing a materially different answer."""
        q = re.sub(r'\s+', ' ', (query or '')).strip()
        return re.sub(r'[?!.]+$', '', q).strip()

    def _capability_response(self) -> Dict[str, Any]:
        """Honest description of what the portal can do — not a grounded legal answer."""
        areas = self._coverage_areas()
        answer = (
            "I answer questions about **Indian law**, grounded strictly in 25 official statutes "
            "(no internet sources). I cover these areas: " + ", ".join(areas) + ".\n\n"
            "Every answer cites the exact section and page of the source statute, and for criminal, "
            "procedure and evidence questions I give both the current law (BNS/BNSS/BSA 2023) and the "
            "legacy law (IPC/CrPC/Indian Evidence Act) with the 1 July 2024 cut-over. Ask a specific "
            "question — e.g. *\"What is the punishment for cheque bounce?\"* or *\"What are the grounds "
            "for divorce under the Hindu Marriage Act?\"* If the statutes don't cover it, I'll say so "
            "rather than guess."
        )
        return {
            "answer": answer,
            "confidence_score": 0.9,
            "sources": [],
            "agent_type": "Assistant",
            "detected_category": "Capabilities",
            "retrieved_documents": 0,
            "retrieval_sources": [],
        }

    def _select_agent(self, query: str, context_texts: List[str], category: str = None):
        # Stage-2 router first: the query's legal category picks its domain agent.
        if category:
            selected = self.agent_registry.select_by_category(category)
            if selected:
                return selected
        selected = self.agent_registry.select_agent(query, context_texts)
        if not selected:
            agents = self.agent_registry.get_all_agents()
            selected = next((a for a in agents if a.domain == "General Law"), None)
        return selected

    def _route(self, query: str):
        """Stage 1 of the router: classify → preferred-document scope + category.

        Returns (preferred_documents, route_meta). Empty set = full-corpus
        fallback (routing off, low confidence, or cross-cutting).
        """
        route_meta = {"category": None, "era_intent": None}
        if not self.settings.CATEGORY_ROUTING_ENABLED:
            return set(), route_meta
        try:
            from ...rag.query_classifier import classify
            from ...rag.document_registry import documents_for_category
        except ImportError:
            from rag.query_classifier import classify
            from rag.document_registry import documents_for_category
        c = classify(query)
        route_meta = {"category": c.get("category"), "era_intent": c.get("era_intent")}
        if (c.get("category") and not c.get("cross_cutting")
                and c.get("confidence", 0) >= self.settings.CLASSIFIER_MIN_CONFIDENCE):
            preferred = documents_for_category(c["category"])
            logger.info(f"Router: '{query[:50]}' → {c['category']} "
                        f"(conf {c['confidence']}, {len(preferred)} docs in scope)")
            return preferred, route_meta
        logger.info(f"Router: '{query[:50]}' → no scope (cat={c.get('category')}, "
                    f"conf={c.get('confidence')}, cross_cutting={c.get('cross_cutting')})")
        return set(), route_meta

    def prepare_query_context(self, query: str):
        """Shared front half of both query paths: route → retrieve → number → agent.

        Returns (sources, retrieved_count, agent, route_meta) or None when
        retrieval found nothing. Synchronous and CPU-heavy — call via
        asyncio.to_thread.
        """
        preferred, route_meta = self._route(query)
        retrieved_docs = self.rag_retriever.retrieve(
            query=query,
            top_k=self.settings.TOP_K_RETRIEVAL,
            preferred_documents=preferred
        )
        if not retrieved_docs:
            return None
        sources = self._number_sources(retrieved_docs)
        context_texts = [source.get('text', '') for source in sources]
        agent = self._select_agent(query, context_texts, route_meta.get("category"))
        return sources, len(retrieved_docs), agent, route_meta

    def _stream_llm_text(self, prompt: str):
        """Yield answer deltas from whichever LLM client is configured."""
        if hasattr(self.llm_client, 'generate_content_stream'):
            yield from self.llm_client.generate_content_stream(prompt)
        else:
            # Gemini's GenerativeModel supports stream=True natively
            for chunk in self.llm_client.generate_content(prompt, stream=True):
                text = getattr(chunk, 'text', '') or ''
                if text:
                    yield text

    async def stream_query(self, query: str):
        """Async generator for the SSE endpoint.

        Yields (event, payload) tuples in order: 'sources' first (so the UI can
        live-link [n] chips as tokens arrive), then 'token' deltas, then 'done'
        with the finalized citations and confidence.
        """
        if not self._initialized:
            raise RuntimeError("AI Service not initialized")
        query = self._normalize_query(query)

        # Meta / capability question → honest description, not a grounded legal answer
        if self._is_meta_query(query):
            cap = self._capability_response()
            yield ('sources', {'retrieval_sources': [], 'retrieved_documents': 0,
                               'agent_type': cap['agent_type'], 'detected_category': 'Capabilities'})
            yield ('token', {'text': cap['answer']})
            yield ('done', cap)
            return

        prep = await asyncio.to_thread(self.prepare_query_context, query)
        if prep is None:
            refusal = self._refusal_response()
            yield ('sources', {'retrieval_sources': [], 'retrieved_documents': 0,
                               'agent_type': refusal['agent_type']})
            yield ('token', {'text': refusal['answer']})
            yield ('done', refusal)
            return

        sources, retrieved_count, agent, route_meta = prep
        yield ('sources', {
            'retrieval_sources': [self._source_ref(s) for s in sources],
            'retrieved_documents': retrieved_count,
            'agent_type': agent.domain if agent else 'General Law',
            'detected_category': route_meta.get('category'),
        })

        if agent is None or agent.llm_client is None:
            fallback = agent._build_no_llm_response(sources).model_dump() if agent else self._refusal_response()
            fallback['retrieved_documents'] = retrieved_count
            fallback['retrieval_sources'] = [self._source_ref(s) for s in sources]
            yield ('token', {'text': fallback['answer']})
            yield ('done', fallback)
            return

        prompt = agent.build_grounded_prompt(query, sources)

        # Bridge the synchronous LLM stream onto the event loop via a queue.
        # The stop event is essential: when the SSE client disconnects, Starlette
        # closes this generator (GeneratorExit at a yield) — without it the
        # producer thread would keep consuming the full Groq generation, burning
        # quota and occupying a default-executor worker.
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        stop = threading.Event()

        def _producer():
            try:
                for delta in self._stream_llm_text(prompt):
                    if stop.is_set():
                        break
                    loop.call_soon_threadsafe(queue.put_nowait, ('delta', delta))
                loop.call_soon_threadsafe(queue.put_nowait, ('end', None))
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, ('error', str(e)))

        producer_future = loop.run_in_executor(None, _producer)

        parts: List[str] = []
        stream_error = None
        try:
            while True:
                kind, payload = await queue.get()
                if kind == 'delta':
                    parts.append(payload)
                    yield ('token', {'text': payload})
                elif kind == 'end':
                    break
                else:
                    stream_error = payload
                    break
            await producer_future
        finally:
            stop.set()

        if stream_error is not None:
            logger.error(f"Streaming LLM call failed: {stream_error}")
            message = self._classify_llm_error(stream_error)
            if sources:
                message += " The retrieved source passages below are still valid."
            partial = ''.join(parts)
            yield ('done', {
                'answer': (partial + "\n\n" if partial else "") + message,
                'confidence_score': 0.0,
                'sources': [],
                'agent_type': 'Error',
                'error': stream_error,
                'retrieved_documents': retrieved_count,
                'retrieval_sources': [self._source_ref(s) for s in sources],
            })
            return

        response_dict = {
            'answer': ''.join(parts),
            'agent_type': agent.domain,
            'reasoning_steps': agent.grounded_reasoning_steps(len(sources)),
        }
        self._finalize_cited_response(response_dict, sources)
        response_dict['retrieved_documents'] = retrieved_count
        response_dict['retrieval_sources'] = [self._source_ref(s) for s in sources]
        yield ('done', response_dict)

    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Main query processing pipeline:
        1. Hybrid retrieval (RAG Fusion + BM25, optional rerank)
        2. Number top-K sources as the citation set
        3. Agent generates a grounded answer with [n] citations
        4. Citations validated, confidence scored
        """
        if not self._initialized:
            raise RuntimeError("AI Service not initialized")
        query = self._normalize_query(query)

        retrieved_count = 0
        sources: List[Dict] = []
        try:
            logger.info(f"Processing query: {query[:100]}...")

            # Meta / capability question → honest description, not a grounded legal answer
            if self._is_meta_query(query):
                return self._capability_response()

            # Off the event loop: retrieval and reranking are CPU-heavy.
            prep = await asyncio.to_thread(self.prepare_query_context, query)

            # Local-first grounding: nothing retrieved → explicit refusal, no LLM call
            if prep is None:
                logger.info("No documents retrieved - returning grounded refusal")
                return self._refusal_response()

            sources, retrieved_count, selected_agent, route_meta = prep
            if not selected_agent:
                logger.error("No suitable agent found for query")
                return {
                    "answer": "I apologize, but I couldn't find a suitable legal expert to handle your query. Please try rephrasing your question.",
                    "confidence_score": 0.0,
                    "sources": [],
                    "agent_type": "None",
                    "error": "No suitable agent found"
                }

            response = await asyncio.to_thread(selected_agent.process_query, query, sources)

            # The no-LLM fallback embeds "[1] Title —" headers that are NOT
            # citations — finalizing it would count them and inflate confidence.
            response_dict = response.model_dump()
            if selected_agent.llm_client is not None:
                self._finalize_cited_response(response_dict, sources)
            response_dict['retrieved_documents'] = retrieved_count
            response_dict['retrieval_sources'] = [self._source_ref(s) for s in sources]
            response_dict['detected_category'] = route_meta.get('category')

            logger.info(f"Query processed successfully by {selected_agent.name}")
            return response_dict

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            message = self._classify_llm_error(str(e))
            if sources:
                message += " The retrieved source passages below are still valid."
            return {
                "answer": message,
                "confidence_score": 0.0,
                "sources": [],
                "agent_type": "Error",
                "error": str(e),
                "retrieved_documents": retrieved_count,
                "retrieval_sources": [self._source_ref(s) for s in sources],
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
        query = self._normalize_query(query)

        retrieved_docs: List[Dict] = []
        sources: List[Dict] = []
        try:
            logger.info(f"Processing advanced query: {query[:100]}...")

            # Meta / capability question → honest description (same as /query)
            if self._is_meta_query(query):
                return self._capability_response()

            # Off the event loop: retrieval includes an LLM reformulation call,
            # embeddings, BM25 and the reranker. fusion_queries is passed
            # per-call, never by mutating the shared reformulator (concurrent
            # requests would race on it). An explicit document_types filter
            # overrides the auto-router.
            preferred, route_meta = (set(), {"category": None}) if (
                filters and filters.get('document_types')) else self._route(query)

            def _advanced_retrieve():
                # In explain mode, reformulate ONCE and hand the same list to
                # retrieval — the response field must show what was actually used.
                reformulated_queries = (
                    self.query_reformulator.reformulate_query(query, fusion_queries)
                    if explain_reasoning else None
                )
                docs = self.rag_retriever.retrieve(
                    query=query,
                    top_k=self.settings.TOP_K_RETRIEVAL,
                    num_reformulations=fusion_queries,
                    reformulations=reformulated_queries,
                    preferred_documents=preferred
                )
                return docs, reformulated_queries

            retrieved_docs, reformulated = await asyncio.to_thread(_advanced_retrieve)

            if filters and filters.get('document_types'):
                allowed_types = set(filters['document_types'])
                retrieved_docs = [
                    doc for doc in retrieved_docs
                    if doc.get('document', '') in allowed_types
                ]

            # Local-first grounding: nothing retrieved → explicit refusal, no LLM call
            if not retrieved_docs:
                refusal = self._refusal_response()
                if filters:
                    refusal['applied_filters'] = filters
                return refusal

            sources = self._number_sources(retrieved_docs)
            context_texts = [source.get('text', '') for source in sources]
            selected_agent = self._select_agent(query, context_texts, route_meta.get('category'))

            if selected_agent:
                response = await asyncio.to_thread(selected_agent.process_query, query, sources)
                response_dict = response.model_dump()

                # Skipped for the no-LLM fallback: its "[n] Title" headers are not citations.
                if selected_agent.llm_client is not None:
                    self._finalize_cited_response(response_dict, sources)
                response_dict['retrieved_documents'] = len(retrieved_docs)
                response_dict['retrieval_sources'] = [self._source_ref(s) for s in sources]
                response_dict['detected_category'] = route_meta.get('category')

                if confidence_threshold and response_dict.get('confidence_score', 0) < confidence_threshold:
                    response_dict['answer'] += (
                        f"\n\n**Note:** The confidence score ({response_dict['confidence_score']:.1%}) "
                        f"is below the requested threshold ({confidence_threshold:.1%})."
                    )

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
                "error": str(e),
                "retrieved_documents": len(retrieved_docs),
                "retrieval_sources": [self._source_ref(s) for s in sources],
            }

    async def add_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process and add new documents to the vector database.

        Files whose stem is already in the database are skipped — FAISS flat has
        no per-document delete, so re-processing would duplicate chunks. The
        only supported re-ingest is the full rebuild (delete vector_db/, restart).
        """
        if not self._initialized:
            raise RuntimeError("AI Service not initialized")

        try:
            results = {"processed": [], "failed": [], "skipped": [], "total_chunks": 0}
            existing_docs = {meta.get('document', '') for meta in (self.vector_db.metadata or [])}

            for file_path in file_paths:
                stem = Path(file_path).stem
                if stem in existing_docs:
                    logger.info(f"Skipping already-ingested document: {file_path}")
                    results["skipped"].append({"file": file_path})
                    continue
                # Guards duplicates WITHIN this request too, not just vs the DB
                existing_docs.add(stem)
                try:
                    logger.info(f"Processing document: {file_path}")

                    # PDF parsing and embedding are CPU-heavy: keep them off the event loop.
                    chunks = await asyncio.to_thread(self.document_processor.process_document, file_path)
                    if not chunks:
                        results["failed"].append({"file": file_path, "error": "No text extracted"})
                        continue

                    enriched_chunks = await asyncio.to_thread(self.document_embedder.embed_chunks, chunks)
                    await asyncio.to_thread(self.vector_db.add_documents, enriched_chunks)

                    results["processed"].append({
                        "file": file_path,
                        "chunks": len(enriched_chunks)
                    })
                    results["total_chunks"] += len(enriched_chunks)

                    logger.info(f"Successfully processed {file_path}: {len(enriched_chunks)} chunks")

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    results["failed"].append({"file": file_path, "error": str(e)})
            
            if results["total_chunks"] > 0:
                db_path = os.path.join(self.settings.VECTOR_DB_PATH, VECTOR_DB_NAME)
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
            provider = (self.settings.LLM_PROVIDER or "gemini").lower()
            if provider == "groq":
                llm_model = f"groq/{self.settings.GROQ_MODEL}"
                llm_hint = "Add GROQ_API_KEY to .env for full AI features"
            else:
                llm_model = f"gemini/{self.settings.LLM_MODEL}"
                llm_hint = "Add GOOGLE_API_KEY to .env for full AI features"

            stats = {
                "initialized": self._initialized,
                "llm_status": "active" if self.llm_client else "not_configured",
                "llm_message": "" if self.llm_client else llm_hint,
                "vector_db": self.vector_db.get_statistics() if self.vector_db else {},
                "agents": len(self.agent_registry.get_all_agents()) if self.agent_registry else 0,
                "models": {
                    "llm": llm_model,
                    "embedding": self.settings.EMBEDDING_MODEL,
                    "reranker": self.settings.RERANK_MODEL if self.settings.RERANK_ENABLED else "disabled"
                },
                "configuration": {
                    "chunk_size": self.settings.CHUNK_SIZE,
                    "top_k_retrieval": self.settings.TOP_K_RETRIEVAL,
                    "rag_fusion_queries": self.settings.RAG_FUSION_QUERIES,
                    "cited_sources_k": self.settings.CITED_SOURCES_K
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
                db_path = os.path.join(self.settings.VECTOR_DB_PATH, VECTOR_DB_NAME)
                self.vector_db.save_index(db_path)
                logger.info("Vector database saved during cleanup")
            
            self._initialized = False
            logger.info("AI Service cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")