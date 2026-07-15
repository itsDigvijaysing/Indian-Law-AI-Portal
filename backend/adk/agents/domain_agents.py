"""
Domain-Specific Legal Agents

One config-driven DomainAgent per legal domain (the stage-2 router maps a query's
category to its domain). Each agent supplies routing keywords + a persona flavor
for the shared grounded-citation prompt in BaseAgent; prompt structure, grounding
rules, era handling and citation validation are all inherited.

Adding a domain = one row in DOMAINS. The registry's CATEGORY_AGENT maps
fine-grained categories to these domain names.
"""

from typing import List
from ..base_agent import BaseAgent


class DomainAgent(BaseAgent):
    """A legal-domain agent configured from a data row (name, keywords, flavor)."""

    def __init__(self, domain: str, keywords: List[str], flavor: str, llm_client=None):
        super().__init__(f"{domain} Agent", domain, llm_client)
        self.category_domain = domain          # matched by AgentRegistry.select_by_category
        self._keywords = keywords
        self._flavor = flavor
        self._always = not keywords            # empty keywords → catch-all (General)

    def get_domain_keywords(self) -> List[str]:
        return self._keywords

    def can_handle(self, query: str, retrieved_context: List[str]) -> bool:
        if self._always:
            return True
        hay = (query + " " + " ".join(retrieved_context)).lower()
        return any(kw in hay for kw in self._keywords)

    def get_prompt_flavor(self) -> str:
        return self._flavor


# domain -> (routing keywords, persona/instructions flavor)
DOMAINS = {
    "Criminal": (
        ["ipc", "bns", "bnss", "crpc", "criminal", "offence", "punishment", "bail", "arrest",
         "fir", "murder", "theft", "cheating", "assault", "rape", "kidnapping", "sanhita"],
        """You are an expert in Indian Criminal Law across both regimes:
- Bharatiya Nyaya Sanhita (BNS) 2023 + Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023 — the current law from 1 July 2024.
- The legacy Indian Penal Code (1860) + Code of Criminal Procedure (1973) — for offences/proceedings before that date.
Identify the offence or procedure; give the punishment and, where the sources contain both, the corresponding old-code and new-code provisions (e.g. IPC 302 ↔ BNS 103)."""),
    "Constitutional": (
        ["constitution", "fundamental right", "article", "writ", "amendment", "directive principle",
         "supreme court", "high court", "habeas corpus", "mandamus"],
        """You are an expert in Indian Constitutional Law and the Constitution of India.
Identify the Article or principle; explain fundamental rights, duties or directive principles with their scope, limitations and enforcement (writs, judicial review) as the sources state them."""),
    "Civil": (
        ["cpc", "civil procedure", "suit", "decree", "execution", "injunction", "limitation",
         "time barred", "specific performance", "plaint", "civil court", "motor", "accident"],
        """You are an expert in Indian Civil Procedure and civil remedies — the Code of Civil Procedure 1908 (including its Orders and Rules), the Limitation Act 1963, the Specific Relief Act 1963, and civil aspects of the Motor Vehicles Act.
Quote CPC provisions exactly as labelled (Sections OR Order/Rule); cover limitation periods, remedies and procedure where the sources state them."""),
    "Family": (
        ["marriage", "divorce", "maintenance", "succession", "inheritance", "coparcenary",
         "hindu marriage", "special marriage", "domestic violence", "custody", "dowry"],
        """You are an expert in Indian Family and Personal Law — the Hindu Marriage Act 1955, Hindu Succession Act 1956, Special Marriage Act 1954, and the Protection of Women from Domestic Violence Act 2005.
Identify the governing Act; explain grounds, procedure, maintenance, inheritance/coparcenary or protection reliefs as the sources provide them."""),
    "Commercial": (
        ["contract", "agreement", "breach", "cheque", "cheque bounce", "negotiable instrument",
         "section 138", "arbitration", "consumer", "specific relief", "damages", "guarantee"],
        """You are an expert in Indian Commercial Law — the Indian Contract Act 1872, Negotiable Instruments Act 1881 (cheque dishonour, s.138), Arbitration and Conciliation Act 1996, Specific Relief Act 1963, and Consumer Protection Act 2019.
Identify the governing Act; explain formation/breach, cheque-bounce liability, arbitration procedure, remedies or consumer rights and forums as the sources state them."""),
    "Property": (
        ["transfer of property", "sale of property", "mortgage", "lease", "gift deed",
         "immovable property", "easement", "lessor", "lessee"],
        """You are an expert in Indian Property Law — the Transfer of Property Act 1882.
Identify the mode of transfer (sale, mortgage, lease, gift, exchange) and explain the rights, obligations and formalities the sources describe; pair with civil procedure/limitation where relevant."""),
    "Digital": (
        ["information technology", "it act", "cybercrime", "hacking", "section 66", "data protection",
         "dpdp", "personal data", "data breach", "privacy", "electronic record", "online fraud"],
        """You are an expert in Indian Digital and Cyber Law — the Information Technology Act 2000, the Digital Personal Data Protection Act 2023 and its 2025 Rules.
Identify whether the issue is cybercrime/electronic-records (IT Act) or data-privacy (DPDP); explain offences, obligations, consent and enforcement as the sources state them."""),
    "Labour": (
        ["wages", "minimum wage", "bonus", "gratuity", "provident fund", "esi", "social security",
         "maternity benefit", "salary", "labour", "employee"],
        """You are an expert in Indian Labour Law — the Code on Wages 2019 and the Code on Social Security 2020.
Identify whether the issue is wages/bonus or social-security benefit (PF/ESI/gratuity/maternity); explain entitlements and obligations as the sources provide them."""),
    "Evidence": (
        ["evidence", "admissibility", "witness", "confession", "burden of proof", "presumption",
         "bsa", "sakshya", "indian evidence act", "electronic evidence"],
        """You are an expert in Indian Evidence Law across both regimes — the Bharatiya Sakshya Adhiniyam 2023 (current, from 1 July 2024) and the Indian Evidence Act 1872 (legacy, for earlier proceedings).
Explain admissibility, burden of proof, presumptions and treatment of electronic records; where the sources contain both, give the current and legacy provisions."""),
    "General Law": (
        [],  # catch-all fallback
        """You are a knowledgeable assistant for Indian legal matters across the Constitution, criminal, civil, personal, commercial, digital and labour law.
Identify which law or code governs the question and explain the provisions exactly as the sources label them."""),
}


def build_domain_agents(llm_client=None) -> List[DomainAgent]:
    """Instantiate one agent per domain (used by AIService._initialize_agents)."""
    return [DomainAgent(domain, kw, flavor, llm_client) for domain, (kw, flavor) in DOMAINS.items()]
