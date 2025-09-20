"""
RAG Fusion Query Reformulation Module

Implements RAG Fusion technique to generate multiple query variations
for improved retrieval coverage.
"""

import re
from typing import List, Dict, Any
import google.generativeai as genai
from loguru import logger


class QueryReformulator:
    """Generates multiple reformulations of user queries using RAG Fusion technique"""
    
    def __init__(self, llm_client=None, num_reformulations: int = 3):
        self.llm_client = llm_client
        self.num_reformulations = num_reformulations
        logger.info(f"QueryReformulator initialized with {num_reformulations} reformulations")
    
    def reformulate_query(self, original_query: str) -> List[str]:
        """
        Generate multiple reformulations of the original query.
        Returns list including the original query plus reformulations.
        """
        try:
            reformulations = [original_query]  # Always include original
            
            if self.llm_client:
                # Use LLM for intelligent reformulation
                llm_reformulations = self._llm_reformulate(original_query)
                reformulations.extend(llm_reformulations)
            
            # Add rule-based reformulations as backup
            rule_based = self._rule_based_reformulate(original_query)
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
            final_reformulations = unique_reformulations[:self.num_reformulations + 1]
            
            logger.info(f"Generated {len(final_reformulations)} query reformulations")
            return final_reformulations
            
        except Exception as e:
            logger.error(f"Error in query reformulation: {e}")
            return [original_query]  # Return original if reformulation fails
    
    def _llm_reformulate(self, query: str) -> List[str]:
        """Use LLM to generate intelligent query reformulations"""
        prompt = f"""
You are an expert in Indian legal queries. Generate {self.num_reformulations} different reformulations of the following legal query. Each reformulation should:

1. Maintain the core legal intent
2. Use different legal terminology or phrasing
3. Be relevant for searching Indian legal documents
4. Cover different aspects or angles of the same question

Original Query: "{query}"

Generate {self.num_reformulations} reformulations as a numbered list:
"""
        
        try:
            response = self.llm_client.generate_content(prompt)
            reformulations = self._parse_llm_response(response.text)
            return reformulations[:self.num_reformulations]
            
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
    
    def _rule_based_reformulate(self, query: str) -> List[str]:
        """Generate reformulations using rule-based patterns"""
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
            
            # Legal concept variations
            ("punishment", "penalty"),
            ("penalty", "punishment"),
            ("offense", "crime"),
            ("crime", "offense"),
            ("bail", "release on bail"),
            ("arrest", "apprehension"),
            
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
        
        return reformulations[:self.num_reformulations]


class RAGFusionRetriever:
    """Implements RAG Fusion for enhanced document retrieval"""
    
    def __init__(self, vector_db, embedding_generator, query_reformulator: QueryReformulator):
        self.vector_db = vector_db
        self.embedding_generator = embedding_generator
        self.query_reformulator = query_reformulator
        logger.info("RAGFusionRetriever initialized")
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Retrieve documents using RAG Fusion approach:
        1. Generate query reformulations
        2. Search with each reformulation
        3. Fuse and rank results
        """
        try:
            # Step 1: Generate query reformulations
            reformulated_queries = self.query_reformulator.reformulate_query(query)
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
            
            # Step 3: Apply fusion ranking
            fused_results = self._apply_fusion_ranking(list(all_results.values()))
            
            # Step 4: Return top_k results
            final_results = sorted(fused_results, key=lambda x: x['fusion_score'], reverse=True)[:top_k]
            
            logger.info(f"RAG Fusion returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in RAG Fusion retrieval: {e}")
            # Fallback to simple retrieval
            query_embedding = self.embedding_generator.generate_embedding(query)
            return self.vector_db.search(query_embedding, top_k)
    
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