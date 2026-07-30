"""
Agent Development Kit (ADK) - Base Agent Classes

This module provides the core infrastructure for building specialized
legal AI agents with domain-specific reasoning capabilities.

Agents receive NUMBERED SOURCE DICTS (see rag_fusion's retrieval result
contract) and produce answers grounded in them with inline [n] citations.
Citation validation, confidence scoring, and the structured citation table
happen afterwards in AIService._finalize_cited_response.
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


# One worked example anchors the citation format — few-shot markedly improves
# marker compliance from Llama-class models.
_CITATION_EXAMPLE = """EXAMPLE OF THE REQUIRED FORMAT:
  Sources given: [1] Indian Penal Code, 1860 — Section 379 (page 88): "Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both."
  Good answer: Theft is punishable with imprisonment of up to three years, or a fine, or both [1].
"""

REFUSAL_SENTENCE = "The provided legal documents do not contain sufficient information to answer this question."


class BaseAgent(ABC):
    """
    Abstract base class for all legal domain agents.

    Each agent specializes in a specific area of Indian law. Prompt structure,
    grounding rules, and citation format are shared here; subclasses supply
    only their domain flavor via get_prompt_flavor().
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
    def get_prompt_flavor(self) -> str:
        """Domain persona and domain-specific analysis guidance for the prompt."""
        pass

    def process_query(self, query: str, sources: List[Dict]) -> AgentResponse:
        """Generate a grounded, cited answer from numbered source dicts.

        LLM exceptions propagate to the caller — AIService owns error
        classification and still returns the retrieved sources on failure.
        """
        if self.llm_client is None:
            return self._build_no_llm_response(sources)

        prompt = self.build_grounded_prompt(query, sources)
        response = self.llm_client.generate_content(prompt)

        return AgentResponse(
            answer=response.text,
            confidence_score=0.0,  # finalized by AIService._finalize_cited_response
            sources=[],            # finalized by AIService._finalize_cited_response
            agent_type=self.domain,
            reasoning_steps=[
                f"Routed to {self.name}",
                f"Answer grounded in {len(sources)} numbered legal sources",
                "Inline [n] citations validated against the source list"
            ]
        )

    _ERA_TAG = {"pre-2024": "legacy, pre-1-July-2024", "post-2024": "current, from 1-July-2024"}

    def build_grounded_prompt(self, query: str, sources: List[Dict]) -> str:
        """Shared prompt skeleton: numbered provenance blocks + strict grounding rules."""
        blocks = []
        has_era_split = False
        for source in sources:
            header = f"[{source['id']}] {source.get('document_title') or source.get('document', '')}"
            # Category + validity era so the model can frame old-vs-new law correctly
            era = source.get('era', '')
            tags = [t for t in (source.get('category', ''), self._ERA_TAG.get(era)) if t]
            if tags:
                header += f" ({' · '.join(tags)})"
            if era in ("pre-2024", "post-2024"):
                has_era_split = True
            section = source.get('section', '')
            if section:
                header += f" — {section}"
            page_start = source.get('page_start') or 0
            page_end = source.get('page_end') or 0
            if page_start:
                header += f" (page {page_start})" if page_start == page_end else f" (pages {page_start}–{page_end})"
            blocks.append(f"{header}\n{source.get('text', '')}")
        sources_text = "\n\n".join(blocks)

        era_rule = ""
        if has_era_split:
            era_rule = (
                "\n9. VALIDITY / ERA: India's criminal, procedure and evidence law changed on "
                "1 July 2024 — the Bharatiya Nyaya Sanhita 2023 / Bharatiya Nagarik Suraksha "
                "Sanhita 2023 / Bharatiya Sakshya Adhiniyam 2023 replaced the Indian Penal Code "
                "1860 / CrPC 1973 / Indian Evidence Act 1872. If the query gives no incident date, "
                "lead with the CURRENT provision and also give the LEGACY one where the sources "
                "contain it, stating which applies to offences/proceedings before vs. from "
                "1 July 2024. If a date is given, apply the law in force on that date."
            )

        return f"""{self.get_prompt_flavor()}

NUMBERED LEGAL SOURCES (the ONLY material you may use):
{sources_text}

USER QUERY: {query}

STRICT GROUNDING RULES:
1. Answer ONLY from the numbered sources above — never from outside knowledge.
2. After every factual claim, cite the supporting source number(s) in square brackets, e.g. [1] or [2][4].
3. Cite only numbers that appear in the source list above. Never invent a citation.
4. Quote section/article numbers exactly as they appear in the sources. NEVER name a
   section, article or rule number that is not printed verbatim in the sources above,
   even if you believe you know the governing provision. If the sources do not contain
   the provision that governs the question, say which provisions they DO contain and
   state that the governing one is not in the sources. A recalled section number is a
   fabrication, not a citation.
4a. Penalties, prison terms, fines, time limits and other numbers must be copied from
   the source text exactly. Square brackets mark text substituted by amendment, so in
   "punished with [a term which may be extended to two years]" the term is two years.
   Never read a bracket marker or footnote digit as part of the number.
5. BE HELPFUL FIRST. If the sources address the question even PARTIALLY, answer directly
   with what they DO say and cite it — do NOT open with a disclaimer. Lead with the
   substantive answer; if some specific detail is not covered, add ONE short sentence at
   the END noting only that missing detail. Reserve the exact refusal sentence
   "{REFUSAL_SENTENCE}" (as the FIRST sentence) ONLY when the sources are genuinely
   unrelated to the question and you can extract nothing useful. Never guess or use
   outside knowledge, but a partial, well-cited answer is far better than a refusal.
6. Amendment footnotes ("Subs. by Act…", "Ins. by…") annotate only the exact
   provision they are attached to. Never present them as amendment history of a
   neighbouring provision. If a passage is a State Amendment (e.g. "West Bengal",
   "Maharashtra" amendments) or appendix material, say so explicitly; it is not
   the general law of India.
7. Write plainly. Do NOT use em dashes or en dashes ("—" / "–"). Use commas,
   periods, or "and" instead. Prefer short, clear sentences a non-lawyer understands.
8. BE BRIEF by default. Give a direct answer in 2 to 4 sentences: the key rule,
   the governing provision, and its [n] citation. Do NOT list every related section
   or add long background. Only give a longer, step-by-step or detailed answer if
   the user explicitly asks (e.g. "explain in detail", "steps", "everything about",
   "procedure"). When in doubt, keep it short.{era_rule}

{_CITATION_EXAMPLE}
A direct, brief answer first. Every factual claim carries its [n] citation.

RESPONSE:
"""

    def _build_no_llm_response(self, sources: List[Dict]) -> AgentResponse:
        """Informative response when no LLM is configured, using RAG results."""
        if sources:
            snippets = []
            for source in sources[:3]:
                text = source.get('text', '')
                snippet = text[:300].strip() + ("..." if len(text) > 300 else "")
                snippets.append(
                    f"**[{source.get('id', '?')}] {source.get('document_title', '')} — "
                    f"{source.get('section', '')}:** {snippet}"
                )
            answer = (
                "AI analysis is unavailable (no LLM API key configured). "
                f"The {min(3, len(sources))} most relevant passages from the legal documents:\n\n"
                + "\n\n".join(snippets)
                + "\n\nConfigure GROQ_API_KEY (or GOOGLE_API_KEY with LLM_PROVIDER=gemini) "
                  "in .env to enable AI-powered answers."
            )
            confidence = 0.3
        else:
            answer = (
                "AI analysis is unavailable (no LLM API key configured) and no relevant "
                "passages were found. Configure GROQ_API_KEY or GOOGLE_API_KEY in .env "
                "and ensure legal documents are ingested."
            )
            confidence = 0.0

        return AgentResponse(
            answer=answer,
            confidence_score=confidence,
            sources=[],
            agent_type=self.domain,
            reasoning_steps=[
                "LLM not available - returning raw retrieval results",
                f"Found {len(sources)} relevant passages",
                "Passages ranked by hybrid retrieval scoring"
            ]
        )


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

    def select_by_category(self, category: str) -> Optional[BaseAgent]:
        """Pick the agent whose domain matches the query's legal category
        (stage-2 router). Returns None if no agent claims that category."""
        if not category:
            return None
        try:
            from rag.document_registry import agent_for_category
        except ImportError:
            from ..rag.document_registry import agent_for_category
        want = agent_for_category(category)
        for agent in self.agents:
            if getattr(agent, 'category_domain', None) == want:
                return agent
        return None

    def get_all_agents(self) -> List[BaseAgent]:
        """Get list of all registered agents"""
        return self.agents.copy()
