"""
Agent Development Kit (ADK) - Base Agent Classes

This module provides the core infrastructure for building specialized 
legal AI agents with domain-specific reasoning capabilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from loguru import logger


class AgentResponse(BaseModel):
    """Standard response format for all agents"""
    answer: str
    confidence_score: float
    sources: List[str]
    agent_type: str
    reasoning_steps: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """
    Abstract base class for all legal domain agents.
    
    Each agent specializes in a specific area of Indian law and provides
    domain-specific reasoning and response formatting.
    """
    
    def __init__(self, name: str, domain: str, llm_client=None):
        self.name = name
        self.domain = domain
        self.llm_client = llm_client
        logger.info(f"Initialized {self.name} agent for {self.domain}")
    
    @abstractmethod
    def can_handle(self, query: str, retrieved_context: List[str]) -> bool:
        """
        Determine if this agent can handle the given query based on
        the query content and retrieved context.
        """
        pass
    
    @abstractmethod
    def get_domain_keywords(self) -> List[str]:
        """Return keywords that indicate this agent should handle the query"""
        pass
    
    @abstractmethod
    def process_query(self, query: str, retrieved_context: List[str]) -> AgentResponse:
        """
        Process the query using domain-specific logic and return a structured response.
        """
        pass
    
    def _build_prompt(self, query: str, context: List[str]) -> str:
        """Build a domain-specific prompt for the LLM"""
        context_text = "\n\n".join([f"Context {i+1}: {ctx}" for i, ctx in enumerate(context)])
        
        base_prompt = f"""
You are a specialized AI assistant for {self.domain} in Indian law.

RETRIEVED LEGAL CONTEXT:
{context_text}

USER QUERY: {query}

Instructions:
1. Answer based ONLY on the provided legal context
2. Provide specific section/article references
3. Use clear, accessible language
4. If the context doesn't contain relevant information, say so clearly
5. Structure your response with clear reasoning

RESPONSE:
"""
        return base_prompt
    
    def _calculate_confidence(self, query: str, context: List[str], response: str) -> float:
        """Calculate confidence score based on context relevance and response quality"""
        # Simple heuristic - can be enhanced with more sophisticated methods
        confidence = 0.5
        
        # Check if response contains specific legal references
        if any(keyword in response.lower() for keyword in ['section', 'article', 'ipc', 'cpc', 'crpc']):
            confidence += 0.2
        
        # Check if context seems relevant to domain
        domain_keywords = [kw.lower() for kw in self.get_domain_keywords()]
        context_text = " ".join(context).lower()
        matches = sum(1 for kw in domain_keywords if kw in context_text)
        confidence += min(0.3, matches * 0.1)
        
        return min(1.0, confidence)


class AgentRegistry:
    """Registry to manage and select appropriate agents for queries"""
    
    def __init__(self):
        self.agents: List[BaseAgent] = []
        logger.info("Initialized Agent Registry")
    
    def register_agent(self, agent: BaseAgent):
        """Register a new agent"""
        self.agents.append(agent)
        logger.info(f"Registered agent: {agent.name} for domain: {agent.domain}")
    
    def select_agent(self, query: str, retrieved_context: List[str]) -> Optional[BaseAgent]:
        """
        Select the most appropriate agent for the given query and context.
        Returns None if no suitable agent is found.
        """
        # Score each agent based on how well it can handle the query
        agent_scores = []
        
        for agent in self.agents:
            if agent.can_handle(query, retrieved_context):
                # Simple scoring based on keyword matches
                domain_keywords = [kw.lower() for kw in agent.get_domain_keywords()]
                query_lower = query.lower()
                context_lower = " ".join(retrieved_context).lower()
                
                score = 0
                for keyword in domain_keywords:
                    if keyword in query_lower:
                        score += 2
                    if keyword in context_lower:
                        score += 1
                
                agent_scores.append((agent, score))
        
        if not agent_scores:
            logger.warning(f"No suitable agent found for query: {query[:100]}...")
            return None
        
        # Return agent with highest score
        selected_agent = max(agent_scores, key=lambda x: x[1])[0]
        logger.info(f"Selected agent: {selected_agent.name} for query")
        return selected_agent
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get list of all registered agents"""
        return self.agents.copy()