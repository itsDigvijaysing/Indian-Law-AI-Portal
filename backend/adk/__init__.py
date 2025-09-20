"""ADK Package - Agent Development Kit for Indian Law AI Portal"""

from .base_agent import BaseAgent, AgentResponse, AgentRegistry
from .agents.domain_agents import (
    CriminalLawAgent,
    CivilLawAgent, 
    ConstitutionalLawAgent,
    GeneralLegalAgent
)

__all__ = [
    'BaseAgent',
    'AgentResponse', 
    'AgentRegistry',
    'CriminalLawAgent',
    'CivilLawAgent',
    'ConstitutionalLawAgent', 
    'GeneralLegalAgent'
]