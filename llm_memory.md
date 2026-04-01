# Indian Law AI Portal - LLM Memory

## Project Status: COMPLETE (Phase 6 - Final Polish)

## Architecture Overview
- **Backend**: Python FastAPI with ADK (Agent Development Kit) + RAG Fusion (FAISS)
- **Frontend**: React 18 with component architecture, react-markdown, Axios
- **AI**: Google Gemini API + Sentence Transformers for embeddings
- **Law Documents**: 6 official PDFs (Constitution, BNS, BNSS, IPC, CrPC, CPC)

## Key Components
1. **ADK Agents**: Criminal (BNS+IPC), Civil (CPC), Constitutional, General Legal
2. **RAG Pipeline**: Document Processor -> Embeddings -> FAISS -> RAG Fusion with cross-code reformulation
3. **API**: FastAPI with query, query/advanced, admin, health endpoints
4. **Frontend**: 7 components (Header, SystemStatus, QueryForm, ResponseDisplay, QueryHistory, DocumentManager, Footer)

## Law Documents in assets/
- Constitution_of_India.pdf (268 pages, indiacode.nic.in)
- Bharatiya_Nyaya_Sanhita_2023.pdf (112 pages, replaced IPC, effective Jul 2024)
- Bharatiya_Nagarik_Suraksha_Sanhita_2023.pdf (279 pages, replaced CrPC, effective Jul 2024)
- Indian_Penal_Code_1860.pdf (119 pages, legacy)
- Code_of_Criminal_Procedure_1973.pdf (263 pages, legacy)
- Code_of_Civil_Procedure_1908.pdf (316 pages, current law)

## Changes Made (Full Project Enhancement)

### Phase 1: BNS/BNSS New Law Support
- Added BNS/BNSS keywords to CriminalLawAgent in domain_agents.py
- Updated criminal law prompts to reference both old and new codes with cross-mapping
- Added BNS/BNSS terms to base_agent.py confidence keywords
- Added cross-code reformulation rules in rag_fusion.py (IPC<->BNS, CrPC<->BNSS)
- Added BNS/BNSS domain detection in query_router.py validate endpoint
- Added BNS/BNSS to document_processor.py identify_document_type()

### Phase 2: Auto-Ingestion on Startup
- Added _auto_ingest_documents() to ai_service.py
- Compares PDF stems in assets/ against vector DB metadata
- Only processes new/unprocessed files
- Called as step 8 in initialize()

### Phase 3: Advanced Query Endpoint
- Implemented process_advanced_query() in ai_service.py
- Supports: custom fusion_queries count, document_type filtering, confidence_threshold, explain_reasoning
- Wired POST /query/advanced in query_router.py
- Added reformulated_queries, fusion_statistics, applied_filters to QueryResponse schema

### Phase 4: Better Error Messages
- No-LLM fallback now returns RAG context snippets (first 3 passages, 300 chars each) via _build_no_llm_response() in BaseAgent
- Confidence 0.3 instead of 0.0 for retrieval-only responses
- Error classification in process_query: quota vs connection vs generic
- Added llm_status to statistics endpoint

### Phase 5: Frontend Component Split & UI Overhaul
- Split monolithic App.js (245 lines) into 7 focused components
- Header.js: gradient header with LLM status badge
- SystemStatus.js: 4-item status grid
- QueryForm.js: textarea, submit, advanced mode (fusion queries slider, confidence threshold, reasoning toggle)
- ResponseDisplay.js: react-markdown rendering, retrieval sources with score bars, legal refs, reasoning, fusion details
- QueryHistory.js: local-state sidebar, max 20 items, click to re-query
- DocumentManager.js: lists ingested PDFs, re-process button via admin API
- Footer.js: disclaimer footer
- App.js: layout orchestrator with sidebar grid (280px + 1fr), mobile-responsive
- App.css: layout styles with responsive breakpoint at 900px
- index.css: CSS custom properties (:root variables)
- Installed react-markdown dependency
- Updated example queries to include BNS/BNSS

### Earlier Fixes (Polish Pass)
- Critical OCR bug: text.replace('0','O') destroying section numbers -> removed
- Pydantic v2: .dict() -> .model_dump()
- Removed unused imports across multiple files
- Extracted shared get_ai_service dependency to api/dependencies.py
- Fixed redundant embedding dimension logic

## How to Run
```bash
# Quick start
./start_dev.sh

# Manual
cd backend && python main.py    # Terminal 1 (auto-ingests PDFs on first run)
cd frontend && npm start        # Terminal 2
```

## Access Points
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Configuration
Edit `.env` with your Google API key for full functionality:
```
GOOGLE_API_KEY=your_actual_key_here
```

## Known Limitations
- google.generativeai deprecation warning (functional, migration optional)
- Embeddings require valid API key for Google models; falls back to sentence-transformers
- First startup with 6 PDFs takes several minutes for ingestion

---
*Last Updated: 2026-04-01 - Full project enhancement complete (Phases 1-6)*
