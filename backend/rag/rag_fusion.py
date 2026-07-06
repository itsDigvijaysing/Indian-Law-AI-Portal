"""
RAG Fusion Query Reformulation Module

Implements RAG Fusion technique to generate multiple query variations
for improved retrieval coverage.

RETRIEVAL RESULT CONTRACT
-------------------------
Every retriever fused here — the built-in vector search, the BM25 keyword
search, and any future source registered via RAGFusionRetriever's
``extra_retrievers`` — is a ``callable(query: str, top_k: int) -> List[Dict]``
whose result dicts carry:

    chunk_id: str            unique id ("<document>::<n>" for PDF chunks)
    text: str                the passage text
    document: str            source document stem
    document_title: str      display title ("Indian Penal Code, 1860")
    section: str             real legal label ("Section 302", "Order VII Rule 1")
    legal_sections: List[str] references found inside the passage
    page_start, page_end: int  1-based PDF pages (0 when unknown)
    similarity_score: float  0..1, retriever-relative
    rank: int                1-based rank within that retriever's results
    type: str                "pdf" today; a future web retriever sets "web"
                             and supplies url/domain in place of pages

A web-search leg plugs in later by appending one more callable to
``extra_retrievers`` — the RRF fusion and everything downstream is agnostic.
"""

import re
from typing import List, Dict, Any
from loguru import logger


def _norm_doc(stem: str) -> str:
    """Whitespace-insensitive document stem (matches trailing-space filenames)."""
    return re.sub(r'\s+', ' ', (stem or '')).strip().lower()


class QueryReformulator:
    """Generates multiple reformulations of user queries using RAG Fusion technique"""
    
    def __init__(self, llm_client=None, num_reformulations: int = 3):
        self.llm_client = llm_client
        self.num_reformulations = num_reformulations
        logger.info(f"QueryReformulator initialized with {num_reformulations} reformulations")
    
    def reformulate_query(self, original_query: str, num_reformulations: int = None) -> List[str]:
        """
        Generate multiple reformulations of the original query.
        Returns list including the original query plus reformulations.

        num_reformulations overrides the instance default per call — callers
        must NOT mutate self.num_reformulations (shared across requests).
        """
        count = num_reformulations if num_reformulations is not None else self.num_reformulations
        try:
            reformulations = [original_query]  # Always include original

            if self.llm_client:
                # Use LLM for intelligent reformulation
                llm_reformulations = self._llm_reformulate(original_query, count)
                reformulations.extend(llm_reformulations)

            # Add rule-based reformulations as backup
            rule_based = self._rule_based_reformulate(original_query, count)
            reformulations.extend(rule_based)

            # Remove duplicates while preserving order
            unique_reformulations = []
            seen = set()
            for query in reformulations:
                query_normalized = query.lower().strip()
                if query_normalized not in seen:
                    unique_reformulations.append(query)
                    seen.add(query_normalized)

            # Ensure we have the desired number of reformulations
            final_reformulations = unique_reformulations[:count + 1]
            
            logger.info(f"Generated {len(final_reformulations)} query reformulations")
            return final_reformulations
            
        except Exception as e:
            logger.error(f"Error in query reformulation: {e}")
            return [original_query]  # Return original if reformulation fails
    
    def _llm_reformulate(self, query: str, count: int = None) -> List[str]:
        """Use LLM to generate intelligent query reformulations"""
        count = count if count is not None else self.num_reformulations
        prompt = f"""
You are an expert in Indian legal queries. Generate {count} different reformulations of the following legal query. Each reformulation should:

1. Maintain the core legal intent
2. Use different legal terminology or phrasing
3. Be relevant for searching Indian legal documents
4. Cover different aspects or angles of the same question

Original Query: "{query}"

Generate {count} reformulations as a numbered list:
"""

        try:
            response = self.llm_client.generate_content(prompt)
            reformulations = self._parse_llm_response(response.text)
            return reformulations[:count]

        except Exception as e:
            logger.error(f"Error in LLM reformulation: {e}")
            return []
    
    def _parse_llm_response(self, response_text: str) -> List[str]:
        """Parse reformulations from LLM response"""
        reformulations = []
        
        # Look for numbered list items
        lines = response_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            # Match patterns like "1. query", "1) query", or "• query"
            match = re.match(r'^(?:\d+[.)]\s*|[•-]\s*)(.*)', line)
            if match:
                reformulation = match.group(1).strip()
                if reformulation and len(reformulation) > 10:  # Filter out very short responses
                    reformulations.append(reformulation)
        
        return reformulations
    
    def _rule_based_reformulate(self, query: str, count: int = None) -> List[str]:
        """Generate reformulations using rule-based patterns"""
        count = count if count is not None else self.num_reformulations
        reformulations = []
        query_lower = query.lower()
        
        # Legal terminology transformations
        transformations = [
            # IPC variations
            ("ipc", "indian penal code"),
            ("indian penal code", "ipc"),
            ("section", "provision"),
            ("provision", "section"),

            # Procedure variations
            ("crpc", "criminal procedure code"),
            ("cpc", "civil procedure code"),
            ("criminal procedure", "crpc"),
            ("civil procedure", "cpc"),

            # BNS/BNSS ↔ IPC/CrPC cross-code mappings
            ("bns", "bharatiya nyaya sanhita"),
            ("bharatiya nyaya sanhita", "bns"),
            ("bnss", "bharatiya nagarik suraksha sanhita"),
            ("bharatiya nagarik suraksha sanhita", "bnss"),
            ("ipc", "bharatiya nyaya sanhita"),
            ("bns", "indian penal code"),
            ("crpc", "bharatiya nagarik suraksha sanhita"),
            ("bnss", "criminal procedure code"),

            # Legal concept variations
            ("punishment", "penalty"),
            ("penalty", "punishment"),
            ("offense", "crime"),
            ("crime", "offense"),
            ("bail", "release on bail"),
            ("arrest", "apprehension"),

            # Common lay term -> statutory phrasing, so a query surfaces the
            # provision in BOTH the legacy and current codes even though the
            # statute text uses different words (e.g. "anticipatory bail" is a
            # common-law term; CrPC 438 / BNSS 482 are both titled "direction for
            # grant of bail to person apprehending arrest").
            ("anticipatory bail", "bail to person apprehending arrest"),
            ("cheque bounce", "dishonour of cheque for insufficiency of funds"),
            ("fir", "information in cognizable cases first information report"),
            ("coparcenary", "daughter coparcener rights in property"),

            # Question reformulations
            ("what is", "explain"),
            ("explain", "what is"),
            ("how", "what is the procedure for"),
            ("can i", "is it legal to"),
            ("is it legal", "what does the law say about")
        ]
        
        # Apply transformations
        for old_term, new_term in transformations:
            if old_term in query_lower:
                new_query = query_lower.replace(old_term, new_term)
                reformulations.append(new_query.capitalize())
        
        # Add contextual reformulations
        if any(term in query_lower for term in ["punishment", "penalty", "sentence"]):
            reformulations.append(f"What are the legal consequences of {query_lower.replace('what is the punishment for', '').strip()}")
        
        if any(term in query_lower for term in ["procedure", "process", "how to"]):
            reformulations.append(f"Legal procedure for {query_lower.replace('what is the procedure for', '').strip()}")
        
        if "section" in query_lower and any(code in query_lower for code in ["ipc", "crpc", "cpc"]):
            reformulations.append(f"Provisions related to {query_lower}")

        return reformulations[:count]


class RAGFusionRetriever:
    """Implements RAG Fusion for enhanced document retrieval"""

    def __init__(self, vector_db, embedding_generator, query_reformulator: QueryReformulator,
                 extra_retrievers=None, reranker=None, rerank_candidates: int = 24):
        self.vector_db = vector_db
        self.embedding_generator = embedding_generator
        self.query_reformulator = query_reformulator
        # Extra ranked sources fused via RRF alongside the vector reformulations.
        # See the module docstring for the result contract; this is where a
        # future web retriever plugs in.
        self.extra_retrievers = list(extra_retrievers or [])
        self.reranker = reranker  # optional sentence-transformers CrossEncoder
        self.rerank_candidates = rerank_candidates
        logger.info(
            f"RAGFusionRetriever initialized "
            f"(extra_retrievers={len(self.extra_retrievers)}, reranker={'on' if reranker else 'off'})"
        )

    def retrieve(self, query: str, top_k: int = 10, num_reformulations: int = None,
                 reformulations: List[str] = None, preferred_documents: set = None) -> List[Dict]:
        """
        Retrieve documents using RAG Fusion approach:
        1. Generate query reformulations
        2. Search with each reformulation
        3. Fuse and rank results

        num_reformulations is a per-call override (advanced queries) — passed
        through instead of mutating the shared reformulator. Callers that need
        the reformulations in their response pass a precomputed list via
        `reformulations` so retrieval uses the very same ones (and the LLM
        reformulation call happens once, not twice).

        preferred_documents (stage-2 router): stems for the query's legal
        category + linked categories. Chunks in that set are BOOSTED and
        guaranteed into the rerank pool — NEVER hard-excluded — so scoping
        improves precision without ever losing a cross-cutting statute.
        """
        preferred_documents = preferred_documents or set()
        try:
            # Step 1: Generate query reformulations
            reformulated_queries = reformulations or self.query_reformulator.reformulate_query(query, num_reformulations)
            logger.info(f"Using {len(reformulated_queries)} query variations")
            
            # Step 2: Retrieve for each reformulation
            all_results = {}  # Use dict to track unique documents
            
            for i, ref_query in enumerate(reformulated_queries):
                # Generate embedding for reformulated query
                query_embedding = self.embedding_generator.generate_embedding(ref_query)
                
                # Search vector database
                results = self.vector_db.search(query_embedding, top_k * 2)  # Get more for fusion
                
                # Add results to collection with source tracking
                for result in results:
                    chunk_id = result.get('chunk_id', '')
                    if chunk_id not in all_results:
                        result['reformulation_matches'] = []
                        result['fusion_scores'] = []
                        all_results[chunk_id] = result
                    
                    # Track which reformulation matched this result
                    all_results[chunk_id]['reformulation_matches'].append({
                        'query': ref_query,
                        'rank': result.get('rank', 999),
                        'similarity': result.get('similarity_score', 0)
                    })

            # Step 2b: Extra retrievers (BM25 today, web search tomorrow) run once
            # with the ORIGINAL query — reformulations help dense recall, while
            # keyword search's value is exact matching on what the user typed.
            # Their ranked lists fuse like one more reformulation.
            for retriever in self.extra_retrievers:
                try:
                    extra_results = retriever(query, top_k * 2)
                except Exception as e:
                    logger.error(f"Extra retriever failed: {e}")
                    continue
                for result in extra_results:
                    chunk_id = result.get('chunk_id', '')
                    if chunk_id not in all_results:
                        result['reformulation_matches'] = []
                        result['fusion_scores'] = []
                        all_results[chunk_id] = result
                    # Propagate an exact-match flag even when the chunk was also
                    # found by vector search (otherwise the label_hit is lost and
                    # the pin below never fires).
                    if result.get('label_hit'):
                        all_results[chunk_id]['label_hit'] = True
                    all_results[chunk_id]['reformulation_matches'].append({
                        'query': f"keyword:{query}",
                        'rank': result.get('rank', 999),
                        'similarity': result.get('similarity_score', 0)
                    })
                    # Remember the best extra-retriever rank: RRF favors chunks
                    # found by several vector reformulations, so a keyword/label
                    # hit found by only ONE list needs a guaranteed seat in the
                    # rerank candidate pool (see below).
                    prior = all_results[chunk_id].get('extra_rank', 999)
                    all_results[chunk_id]['extra_rank'] = min(prior, result.get('rank', 999))

            # Step 3: Apply fusion ranking (+ category boost)
            fused_results = self._apply_fusion_ranking(list(all_results.values()))
            if preferred_documents:
                # Soft boost — 25% lift for in-category chunks. Enough to lift a
                # near-miss into the head, never enough to bury a strong
                # out-of-category hit (recall-safe). Compare whitespace-normalized:
                # two corpus files carry trailing spaces in their stem, so exact
                # equality would silently exclude them from their own category.
                preferred_norm = {_norm_doc(d) for d in preferred_documents}
                for r in fused_results:
                    if _norm_doc(r.get('document', '')) in preferred_norm:
                        r['fusion_score'] *= 1.25
                        r['in_category'] = True
            fused_results.sort(key=lambda x: x['fusion_score'], reverse=True)

            # Step 4: Optional cross-encoder rerank. Candidates = fused head PLUS
            # each extra retriever's top hits AND any in-category chunk — a chunk
            # found only by keyword/label or living in the routed category can
            # fall outside the head yet be exactly what was asked for; the
            # reranker judges the pool on merit.
            if self.reranker is None:
                final_results = fused_results[:top_k]
            else:
                head_size = max(self.rerank_candidates, top_k)
                head = fused_results[:head_size]
                guaranteed = [r for r in fused_results[head_size:]
                              if r.get('extra_rank', 999) <= 8 or r.get('in_category')]
                final_results = self._rerank(query, head + guaranteed[:16], top_k)

            # Exact matches (named section OR known lay-concept → provision) are
            # authoritative domain knowledge, not fuzzy hits — the reranker must
            # not drop them. Pin any label_hit chunk into the final list.
            label_hits = [r for r in fused_results if r.get('label_hit')]
            if label_hits:
                have = {r.get('chunk_id') for r in final_results}
                missing = [r for r in label_hits if r.get('chunk_id') not in have]
                if missing:
                    # Prepend missing exact hits; keep total at top_k
                    final_results = missing + [r for r in final_results
                                               if r.get('chunk_id') not in
                                               {m.get('chunk_id') for m in missing}]
                    final_results = final_results[:max(top_k, len(missing))]

            logger.info(f"RAG Fusion returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in RAG Fusion retrieval: {e}")
            # Fallback to simple retrieval
            query_embedding = self.embedding_generator.generate_embedding(query)
            return self.vector_db.search(query_embedding, top_k)
    
    def _rerank(self, query: str, candidates: List[Dict], top_k: int) -> List[Dict]:
        """Cross-encoder rerank of the candidate pool; falls back to fusion order on any error."""
        if not candidates:
            return []
        try:
            # Score against label + text: statute body text never names its own
            # act or provision ("11. Rejection of plaint…" doesn't contain
            # "Order VII Rule 11"), so label-style queries would demote the very
            # chunk they name if the cross-encoder saw only the body.
            pairs = [
                (query, f"{c.get('document_title', '')} — {c.get('section', '')}: {c.get('text', '')}")
                for c in candidates
            ]
            scores = self.reranker.predict(pairs)
            for candidate, score in zip(candidates, scores):
                candidate['rerank_score'] = float(score)
            candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
            return candidates[:top_k]
        except Exception as e:
            logger.error(f"Reranking failed, using fusion order: {e}")
            return candidates[:top_k]

    def _apply_fusion_ranking(self, results: List[Dict]) -> List[Dict]:
        """Apply reciprocal rank fusion (RRF) to combine results from multiple queries"""
        for result in results:
            matches = result.get('reformulation_matches', [])
            
            if not matches:
                result['fusion_score'] = 0
                continue
            
            # Calculate RRF score
            rrf_score = 0
            k = 60  # RRF parameter
            
            for match in matches:
                rank = match.get('rank', 999)
                rrf_score += 1 / (k + rank)
            
            # Normalize by number of queries that found this result
            result['fusion_score'] = rrf_score
            result['query_coverage'] = len(matches)  # How many reformulations found this
            
            # Add diversity bonus for results found by multiple reformulations
            if len(matches) > 1:
                result['fusion_score'] *= (1 + 0.1 * len(matches))  # 10% bonus per additional match
        
        return results
    
    def get_fusion_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        """Get statistics about the fusion process"""
        if not results:
            return {}
        
        total_matches = sum(len(r.get('reformulation_matches', [])) for r in results)
        avg_coverage = sum(r.get('query_coverage', 0) for r in results) / len(results)
        
        coverage_distribution = {}
        for result in results:
            coverage = result.get('query_coverage', 0)
            coverage_distribution[coverage] = coverage_distribution.get(coverage, 0) + 1
        
        return {
            'total_unique_results': len(results),
            'total_matches_across_queries': total_matches,
            'average_query_coverage': avg_coverage,
            'coverage_distribution': coverage_distribution,
            'max_fusion_score': max(r.get('fusion_score', 0) for r in results),
            'min_fusion_score': min(r.get('fusion_score', 0) for r in results)
        }