"""
Domain-Specific Legal Agents

This module contains specialized agents for different areas of Indian law.
Each agent has domain expertise and can provide specialized reasoning.
"""

from typing import List
from ..base_agent import BaseAgent, AgentResponse
from loguru import logger


class CriminalLawAgent(BaseAgent):
    """Specialized agent for Criminal Law (IPC, CrPC, etc.)"""
    
    def __init__(self, llm_client=None):
        super().__init__("Criminal Law Agent", "Criminal Law", llm_client)
    
    def get_domain_keywords(self) -> List[str]:
        return [
            "ipc", "indian penal code", "criminal", "crime", "theft", "murder",
            "assault", "kidnapping", "fraud", "cheating", "crpc", "criminal procedure",
            "bail", "arrest", "investigation", "trial", "punishment", "sentence",
            "cognizable", "non-cognizable", "bailable", "non-bailable",
            "bns", "bharatiya nyaya sanhita", "bharatiya nyaya",
            "bnss", "bharatiya nagarik suraksha sanhita", "bharatiya nagarik suraksha",
            "sanhita", "nagarik suraksha"
        ]
    
    def can_handle(self, query: str, retrieved_context: List[str]) -> bool:
        query_lower = query.lower()
        context_text = " ".join(retrieved_context).lower()
        
        keywords = self.get_domain_keywords()
        return any(keyword in query_lower or keyword in context_text for keyword in keywords)
    
    def process_query(self, query: str, retrieved_context: List[str]) -> AgentResponse:
        if self.llm_client is None:
            return self._build_no_llm_response(retrieved_context)
        
        prompt = self._build_criminal_law_prompt(query, retrieved_context)
        
        try:
            # Use Google Generative AI
            response = self.llm_client.generate_content(prompt)
            answer = response.text
            
            confidence = self._calculate_confidence(query, retrieved_context, answer)
            sources = self._extract_sources(retrieved_context)
            
            return AgentResponse(
                answer=answer,
                confidence_score=confidence,
                sources=sources,
                agent_type="Criminal Law",
                reasoning_steps=[
                    "Analyzed query for criminal law indicators",
                    "Retrieved relevant IPC/CrPC sections",
                    "Applied criminal law reasoning",
                    "Formatted response with legal references"
                ]
            )
        
        except Exception as e:
            logger.error(f"Error in Criminal Law Agent: {e}")
            return AgentResponse(
                answer="I encountered an error processing this criminal law query. Please try again.",
                confidence_score=0.0,
                sources=[],
                agent_type="Criminal Law"
            )
    
    def _build_criminal_law_prompt(self, query: str, context: List[str]) -> str:
        context_text = "\n\n".join([f"Legal Text {i+1}: {ctx}" for i, ctx in enumerate(context)])
        
        return f"""
You are an expert in Indian Criminal Law, specializing in:
- Bharatiya Nyaya Sanhita (BNS), 2023 — replaced the Indian Penal Code (IPC) effective July 1, 2024
- Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 — replaced the Criminal Procedure Code (CrPC) effective July 1, 2024
- The legacy IPC (1860) and CrPC (1973) — still relevant for pre-2024 cases

LEGAL CONTEXT FROM OFFICIAL SOURCES:
{context_text}

USER QUERY: {query}

Instructions for Criminal Law Analysis:
1. Identify the specific criminal offense or procedure in question
2. Reference exact section numbers from the applicable code (BNS/BNSS for current law, IPC/CrPC for legacy matters)
3. When possible, mention the corresponding section in both old and new codes for reference
4. Explain the elements of the offense (if applicable)
5. Mention punishment/penalty details with section references
6. Clarify procedural aspects (bailable/non-bailable, cognizable/non-cognizable)
7. Use precise legal terminology while keeping explanations clear

Format your response with:
- Direct answer to the query
- Relevant section numbers and their provisions (specify which code: BNS/BNSS or IPC/CrPC)
- Practical implications
- Any important procedural notes

RESPONSE:
"""


class CivilLawAgent(BaseAgent):
    """Specialized agent for Civil Law (CPC, Contract Law, etc.)"""
    
    def __init__(self, llm_client=None):
        super().__init__("Civil Law Agent", "Civil Law", llm_client)
    
    def get_domain_keywords(self) -> List[str]:
        return [
            "cpc", "civil procedure code", "civil", "contract", "agreement", 
            "property", "tort", "damages", "injunction", "suit", "plaintiff",
            "defendant", "decree", "judgment", "appeal", "revision", "limitation",
            "specific performance", "breach of contract", "property rights"
        ]
    
    def can_handle(self, query: str, retrieved_context: List[str]) -> bool:
        query_lower = query.lower()
        context_text = " ".join(retrieved_context).lower()
        
        keywords = self.get_domain_keywords()
        return any(keyword in query_lower or keyword in context_text for keyword in keywords)
    
    def process_query(self, query: str, retrieved_context: List[str]) -> AgentResponse:
        if self.llm_client is None:
            return self._build_no_llm_response(retrieved_context)

        prompt = self._build_civil_law_prompt(query, retrieved_context)
        
        try:
            response = self.llm_client.generate_content(prompt)
            answer = response.text
            
            confidence = self._calculate_confidence(query, retrieved_context, answer)
            sources = self._extract_sources(retrieved_context)
            
            return AgentResponse(
                answer=answer,
                confidence_score=confidence,
                sources=sources,
                agent_type="Civil Law",
                reasoning_steps=[
                    "Identified civil law domain",
                    "Analyzed relevant CPC/contract provisions",
                    "Applied civil procedure reasoning",
                    "Structured response with legal precedents"
                ]
            )
        
        except Exception as e:
            logger.error(f"Error in Civil Law Agent: {e}")
            return AgentResponse(
                answer="I encountered an error processing this civil law query. Please try again.",
                confidence_score=0.0,
                sources=[],
                agent_type="Civil Law"
            )
    
    def _build_civil_law_prompt(self, query: str, context: List[str]) -> str:
        context_text = "\n\n".join([f"Legal Text {i+1}: {ctx}" for i, ctx in enumerate(context)])
        
        return f"""
You are an expert in Indian Civil Law, specializing in the Civil Procedure Code (CPC), Contract Law, and Civil Rights.

LEGAL CONTEXT FROM OFFICIAL SOURCES:
{context_text}

USER QUERY: {query}

Instructions for Civil Law Analysis:
1. Identify the civil law matter (contract, property, procedure, etc.)
2. Reference relevant CPC sections or civil law provisions
3. Explain the legal principles involved
4. Discuss remedies available (damages, injunction, specific performance)
5. Mention limitation periods if applicable
6. Clarify procedural requirements

Format your response with:
- Clear answer addressing the civil matter
- Relevant section references
- Available legal remedies
- Procedural guidance
- Practical considerations

RESPONSE:
"""


class ConstitutionalLawAgent(BaseAgent):
    """Specialized agent for Constitutional Law"""
    
    def __init__(self, llm_client=None):
        super().__init__("Constitutional Law Agent", "Constitutional Law", llm_client)
    
    def get_domain_keywords(self) -> List[str]:
        return [
            "constitution", "fundamental rights", "directive principles", "article",
            "amendment", "supreme court", "high court", "judicial review",
            "separation of powers", "federalism", "emergency", "president",
            "parliament", "legislature", "executive", "judiciary", "writ",
            "habeas corpus", "mandamus", "certiorari", "prohibition", "quo warranto"
        ]
    
    def can_handle(self, query: str, retrieved_context: List[str]) -> bool:
        query_lower = query.lower()
        context_text = " ".join(retrieved_context).lower()
        
        keywords = self.get_domain_keywords()
        return any(keyword in query_lower or keyword in context_text for keyword in keywords)
    
    def process_query(self, query: str, retrieved_context: List[str]) -> AgentResponse:
        if self.llm_client is None:
            return self._build_no_llm_response(retrieved_context)

        prompt = self._build_constitutional_prompt(query, retrieved_context)
        
        try:
            response = self.llm_client.generate_content(prompt)
            answer = response.text
            
            confidence = self._calculate_confidence(query, retrieved_context, answer)
            sources = self._extract_sources(retrieved_context)
            
            return AgentResponse(
                answer=answer,
                confidence_score=confidence,
                sources=sources,
                agent_type="Constitutional Law",
                reasoning_steps=[
                    "Identified constitutional law issue",
                    "Analyzed relevant constitutional articles",
                    "Applied constitutional principles",
                    "Referenced fundamental rights/duties"
                ]
            )
        
        except Exception as e:
            logger.error(f"Error in Constitutional Law Agent: {e}")
            return AgentResponse(
                answer="I encountered an error processing this constitutional law query. Please try again.",
                confidence_score=0.0,
                sources=[],
                agent_type="Constitutional Law"
            )
    
    def _build_constitutional_prompt(self, query: str, context: List[str]) -> str:
        context_text = "\n\n".join([f"Constitutional Text {i+1}: {ctx}" for i, ctx in enumerate(context)])
        
        return f"""
You are an expert in Indian Constitutional Law with deep knowledge of the Constitution of India.

CONSTITUTIONAL CONTEXT FROM OFFICIAL SOURCES:
{context_text}

USER QUERY: {query}

Instructions for Constitutional Analysis:
1. Identify the constitutional provision or principle involved
2. Reference specific articles of the Constitution
3. Explain fundamental rights, duties, or directive principles
4. Discuss the scope and limitations
5. Mention relevant Supreme Court interpretations if evident
6. Clarify the constitutional framework

Format your response with:
- Direct constitutional answer
- Specific article references
- Fundamental rights/duties implications
- Constitutional principles
- Enforcement mechanisms

RESPONSE:
"""


# Default/General Agent for queries that don't fit specific domains
class GeneralLegalAgent(BaseAgent):
    """General legal agent for queries that don't fit specific domains"""
    
    def __init__(self, llm_client=None):
        super().__init__("General Legal Agent", "General Law", llm_client)
    
    def get_domain_keywords(self) -> List[str]:
        return ["law", "legal", "act", "section", "regulation", "rule", "provision"]
    
    def can_handle(self, query: str, retrieved_context: List[str]) -> bool:
        # This agent can handle any query as a fallback
        return True
    
    def process_query(self, query: str, retrieved_context: List[str]) -> AgentResponse:
        if self.llm_client is None:
            return self._build_no_llm_response(retrieved_context)
        
        prompt = self._build_general_prompt(query, retrieved_context)
        
        try:
            response = self.llm_client.generate_content(prompt)
            answer = response.text
            
            confidence = self._calculate_confidence(query, retrieved_context, answer)
            sources = self._extract_sources(retrieved_context)
            
            return AgentResponse(
                answer=answer,
                confidence_score=confidence,
                sources=sources,
                agent_type="General Legal",
                reasoning_steps=[
                    "Applied general legal reasoning",
                    "Analyzed available legal context",
                    "Provided comprehensive legal response"
                ]
            )
        
        except Exception as e:
            logger.error(f"Error in General Legal Agent: {e}")
            return AgentResponse(
                answer="I encountered an error processing this legal query. Please try again.",
                confidence_score=0.0,
                sources=[],
                agent_type="General Legal"
            )
    
    def _build_general_prompt(self, query: str, context: List[str]) -> str:
        context_text = "\n\n".join([f"Legal Reference {i+1}: {ctx}" for i, ctx in enumerate(context)])
        
        return f"""
You are a knowledgeable AI assistant for Indian legal matters.

LEGAL CONTEXT FROM OFFICIAL SOURCES:
{context_text}

USER QUERY: {query}

Instructions:
1. Answer based on the provided legal context
2. Provide relevant section or act references
3. Explain legal concepts clearly
4. Structure your response logically
5. If information is insufficient, state limitations clearly

RESPONSE:
"""