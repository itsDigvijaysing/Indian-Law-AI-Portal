"""
Document Registry — legal-hierarchy metadata for every PDF in the corpus.

Single source of truth transcribed from the project's Indian-law hierarchy guide.
Powers three things:
  1. Per-chunk metadata (category / era / law_type / law_area) stamped at ingest.
  2. Era / validity grounding — the pre/post-1-July-2024 split for criminal,
     procedure and evidence law (the defining legal-RAG requirement: which norm
     was in force on which date).
  3. The two-stage router — classify a query to a CATEGORY, then scope retrieval
     to that category's documents PLUS its linked categories (recall-safe).

Registry keys are document stems (filename without .pdf), matched
whitespace-insensitively via `_norm` so trailing-space filenames still resolve.
"""

import re

# era values
PRE_2024 = "pre-2024"     # legacy law: IPC, CrPC, Indian Evidence Act
POST_2024 = "post-2024"   # new law from 1 July 2024: BNS, BNSS, BSA
CURRENT = "current"       # in-force, no era split (Constitution + civil/commercial/…)

# category -> the agent domain that frames its answers
CATEGORY_AGENT = {
    "Constitutional": "Constitutional",
    "Criminal": "Criminal",
    "Criminal Procedure": "Criminal",
    "Evidence": "Evidence",
    "Civil Procedure": "Civil",
    "Commercial": "Commercial",
    "Consumer": "Commercial",
    "Property": "Property",
    "Family": "Family",
    "Motor": "Civil",
    "Digital": "Digital",
    "Labour": "Labour",
}

# category -> related categories whose documents should ALSO be pulled into
# retrieval scope (encodes the guide's scenario→document routing table so
# cross-cutting queries keep their supporting statutes).
CATEGORY_ALSO_PULL = {
    "Constitutional": [],
    "Criminal": ["Criminal Procedure", "Evidence", "Constitutional"],
    "Criminal Procedure": ["Criminal", "Evidence", "Constitutional"],
    "Evidence": ["Criminal Procedure", "Civil Procedure"],
    "Civil Procedure": ["Commercial", "Property"],
    "Commercial": ["Civil Procedure", "Consumer"],
    "Consumer": ["Commercial", "Civil Procedure"],
    "Property": ["Civil Procedure", "Commercial"],
    "Family": ["Civil Procedure", "Criminal Procedure"],
    "Motor": ["Civil Procedure", "Criminal Procedure"],
    "Digital": ["Criminal", "Evidence"],
    "Labour": [],
}

# stem -> metadata. `kw` are routing keywords for the query classifier.
DOCUMENTS = {
    # --- Supreme law ---
    "Constitution_of_India": {
        "title": "Constitution of India", "category": "Constitutional", "era": CURRENT,
        "law_type": "substantive", "law_area": "fundamental rights, writs, constitutional validity",
        "kw": ["constitution", "fundamental right", "article", "writ", "habeas corpus", "mandamus",
               "certiorari", "quo warranto", "directive principle", "amendment", "part iii", "preamble"]},
    # --- Criminal (substantive) ---
    "Bharatiya_Nyaya_Sanhita_2023": {
        "title": "Bharatiya Nyaya Sanhita, 2023", "category": "Criminal", "era": POST_2024,
        "law_type": "substantive", "law_area": "offences and punishments (current criminal law)",
        "kw": ["bns", "bharatiya nyaya", "sanhita", "offence", "punishment", "crime", "murder",
               "theft", "cheating", "assault", "rape", "kidnapping", "culpable homicide"]},
    "Indian_Penal_Code_1860": {
        "title": "Indian Penal Code, 1860", "category": "Criminal", "era": PRE_2024,
        "law_type": "substantive", "law_area": "offences and punishments (legacy, pre-July 2024)",
        "kw": ["ipc", "indian penal code", "penal code", "offence", "punishment", "crime", "murder",
               "theft", "cheating", "defamation", "section 302", "section 420"]},
    # --- Criminal procedure ---
    "Bharatiya_Nagarik_Suraksha_Sanhita_2023": {
        "title": "Bharatiya Nagarik Suraksha Sanhita, 2023", "category": "Criminal Procedure", "era": POST_2024,
        "law_type": "procedural", "law_area": "arrest, bail, FIR, trial (current criminal procedure)",
        "kw": ["bnss", "nagarik suraksha", "arrest", "bail", "fir", "charge sheet", "remand",
               "cognizable", "bailable", "trial procedure", "anticipatory bail"]},
    "Code_of_Criminal_Procedure_1973": {
        "title": "Code of Criminal Procedure, 1973", "category": "Criminal Procedure", "era": PRE_2024,
        "law_type": "procedural", "law_area": "arrest, bail, FIR, trial (legacy, pre-July 2024)",
        "kw": ["crpc", "criminal procedure", "arrest", "bail", "fir", "section 438", "section 154",
               "anticipatory bail", "cognizable", "remand"]},
    # --- Evidence ---
    "THE BHARATIYA SAKSHYA ADHINIYAM, 2023": {
        "title": "Bharatiya Sakshya Adhiniyam, 2023", "category": "Evidence", "era": POST_2024,
        "law_type": "procedural", "law_area": "admissibility of evidence (current)",
        "kw": ["bsa", "sakshya", "adhiniyam", "evidence", "admissibility", "electronic record",
               "confession", "witness", "document evidence", "burden of proof"]},
    "THE INDIAN EVIDENCE ACT, 1872": {
        "title": "Indian Evidence Act, 1872", "category": "Evidence", "era": PRE_2024,
        "law_type": "procedural", "law_area": "admissibility of evidence (legacy, pre-July 2024)",
        "kw": ["indian evidence act", "evidence act", "evidence", "admissibility", "confession",
               "witness", "hearsay", "burden of proof", "presumption"]},
    # --- Civil procedure ---
    "Code_of_Civil_Procedure_1908": {
        "title": "Code of Civil Procedure, 1908", "category": "Civil Procedure", "era": CURRENT,
        "law_type": "procedural", "law_area": "civil suits, decrees, execution, injunctions",
        "kw": ["cpc", "civil procedure", "suit", "plaint", "decree", "execution", "order vii",
               "injunction", "civil court", "written statement", "summons"]},
    "THE LIMITATION ACT, 1963": {
        "title": "Limitation Act, 1963", "category": "Civil Procedure", "era": CURRENT,
        "law_type": "procedural", "law_area": "time limits to file suits; condonation of delay",
        "kw": ["limitation", "time barred", "time limit", "period of limitation", "condonation",
               "delay", "how long to file", "prescribed period", "how much time", "how long do i have",
               "deadline to file", "time to file a case"]},
    # --- Commercial ---
    "THE INDIAN CONTRACT ACT, 1872": {
        "title": "Indian Contract Act, 1872", "category": "Commercial", "era": CURRENT,
        "law_type": "substantive", "law_area": "contracts, agreements, breach, damages",
        "kw": ["contract", "agreement", "breach of contract", "consideration", "offer", "acceptance",
               "void agreement", "damages", "indemnity", "guarantee", "consent",
               "lent", "lend", "borrowed money", "repay", "loan", "recover money", "verbal agreement"]},
    "THE SPECIFIC RELIEF ACT, 1963": {
        "title": "Specific Relief Act, 1963", "category": "Commercial", "era": CURRENT,
        "law_type": "substantive", "law_area": "specific performance, injunctions, declaratory relief",
        "kw": ["specific relief", "specific performance", "injunction", "declaratory", "recovery of possession",
               "mandatory injunction", "perpetual injunction"]},
    "THE NEGOTIABLE INSTRUMENTS ACT, 1881": {
        "title": "Negotiable Instruments Act, 1881", "category": "Commercial", "era": CURRENT,
        "law_type": "substantive", "law_area": "cheques, cheque bounce (s.138), promissory notes",
        "kw": ["negotiable instrument", "cheque", "cheque bounce", "dishonour", "section 138",
               "promissory note", "bill of exchange", "bounced cheque", "insufficient funds"]},
    "THE ARBITRATION AND CONCILIATION ACT, 1996": {
        "title": "Arbitration and Conciliation Act, 1996", "category": "Commercial", "era": CURRENT,
        "law_type": "procedural", "law_area": "arbitration, arbitral awards, conciliation",
        "kw": ["arbitration", "arbitral", "arbitrator", "conciliation", "award", "section 11",
               "section 34", "arbitration clause", "seat of arbitration"]},
    # --- Consumer ---
    "THE CONSUMER PROTECTION ACT, 2019": {
        "title": "Consumer Protection Act, 2019", "category": "Consumer", "era": CURRENT,
        "law_type": "substantive", "law_area": "defective goods, service deficiency, consumer forums",
        "kw": ["consumer", "consumer protection", "defective", "service deficiency", "unfair trade",
               "consumer forum", "consumer commission", "refund", "e-commerce complaint"]},
    # --- Property ---
    "THE TRANSFER OF PROPERTY ACT, 1882": {
        "title": "Transfer of Property Act, 1882", "category": "Property", "era": CURRENT,
        "law_type": "substantive", "law_area": "sale, mortgage, lease, gift of immovable property",
        "kw": ["transfer of property", "sale of property", "mortgage", "lease", "gift deed",
               "immovable property", "easement", "charge", "lessor", "lessee",
               "landlord", "tenant", "evict", "eviction", "rent", "rented", "vacate premises"]},
    # --- Family / personal ---
    "The Hindu Marriage Act, 1955": {
        "title": "Hindu Marriage Act, 1955", "category": "Family", "era": CURRENT,
        "law_type": "substantive", "law_area": "Hindu marriage, divorce, maintenance",
        "kw": ["hindu marriage", "divorce", "maintenance", "restitution of conjugal", "judicial separation",
               "cruelty divorce", "desertion", "section 13", "mutual consent divorce"]},
    "THE HINDU SUCCESSION ACT, 1956": {
        "title": "Hindu Succession Act, 1956", "category": "Family", "era": CURRENT,
        "law_type": "substantive", "law_area": "Hindu inheritance, coparcenary, succession",
        "kw": ["hindu succession", "inheritance", "coparcenary", "daughter's share", "intestate",
               "class i heir", "succession", "will", "property inheritance"]},
    "THE SPECIAL MARRIAGE ACT, 1954": {
        "title": "Special Marriage Act, 1954", "category": "Family", "era": CURRENT,
        "law_type": "substantive", "law_area": "civil and inter-faith marriage",
        "kw": ["special marriage", "inter-religion marriage", "inter-faith marriage", "civil marriage",
               "court marriage", "registration of marriage", "register a marriage", "different religions",
               "inter-caste marriage"]},
    "protection_of_women_from_domestic_violence_act_2005": {
        "title": "Protection of Women from Domestic Violence Act, 2005", "category": "Family", "era": CURRENT,
        "law_type": "substantive", "law_area": "domestic violence, protection & residence orders",
        "kw": ["domestic violence", "protection order", "residence order", "dv act", "aggrieved woman",
               "monetary relief", "shared household"]},
    # --- Motor ---
    "THE MOTOR VEHICLES ACT, 1988": {
        "title": "Motor Vehicles Act, 1988", "category": "Motor", "era": CURRENT,
        "law_type": "substantive", "law_area": "road accidents, compensation, licensing, insurance",
        "kw": ["motor vehicle", "road accident", "accident compensation", "driving licence",
               "mact", "third party insurance", "hit and run", "challan", "traffic"]},
    # --- Digital ---
    "THE INFORMATION TECHNOLOGY ACT, 2000": {
        "title": "Information Technology Act, 2000", "category": "Digital", "era": CURRENT,
        "law_type": "substantive", "law_area": "cybercrime, electronic records, intermediary liability",
        "kw": ["information technology", "it act", "cybercrime", "hacking", "hacked", "section 66", "identity theft",
               "electronic record", "digital signature", "intermediary", "online fraud", "otp scam",
               "stole money online", "phishing"]},
    "The Digital Personal Data Protection Act, 2023": {
        "title": "Digital Personal Data Protection Act, 2023", "category": "Digital", "era": CURRENT,
        "law_type": "substantive", "law_area": "data privacy, consent, data fiduciaries",
        "kw": ["data protection", "dpdp", "personal data", "data privacy", "consent", "data fiduciary",
               "data principal", "data breach", "privacy"]},
    "The Digital Personal Data Protection Act, Extra Added 2025": {
        "title": "Digital Personal Data Protection Rules, 2025", "category": "Digital", "era": CURRENT,
        "law_type": "procedural", "law_area": "DPDP operational rules — consent managers, grievance",
        "kw": ["dpdp rules", "consent manager", "data localization", "grievance mechanism",
               "data protection rules"]},
    # --- Labour ---
    "The Code on Wages, 2019": {
        "title": "Code on Wages, 2019", "category": "Labour", "era": CURRENT,
        "law_type": "substantive", "law_area": "minimum wages, payment of wages, bonus",
        "kw": ["wages", "minimum wage", "payment of wages", "bonus", "salary", "code on wages",
               "wage dispute", "overtime"]},
    "The Code on Social Security, 2020": {
        "title": "Code on Social Security, 2020", "category": "Labour", "era": CURRENT,
        "law_type": "substantive", "law_area": "PF, ESI, gratuity, maternity benefit",
        "kw": ["social security", "provident fund", "pf", "esi", "gratuity", "maternity benefit",
               "pension", "employee benefit"]},
}


# Common lay concepts whose statute text does NOT contain the lay phrase, mapped
# to the exact (document stem, section label) that governs them — in BOTH eras
# where applicable. label_search guarantees these into retrieval so e.g.
# "anticipatory bail" reliably surfaces the current BNSS 482 AND legacy CrPC 438.
CONCEPT_SECTIONS = {
    "anticipatory bail": [
        ("Bharatiya_Nagarik_Suraksha_Sanhita_2023", "Section 482"),
        ("Code_of_Criminal_Procedure_1973", "Section 438"),
    ],
    "cheque bounce": [("THE NEGOTIABLE INSTRUMENTS ACT, 1881", "Section 138")],
    "cheque dishonour": [("THE NEGOTIABLE INSTRUMENTS ACT, 1881", "Section 138")],
    "first information report": [
        ("Bharatiya_Nagarik_Suraksha_Sanhita_2023", "Section 173"),
        ("Code_of_Criminal_Procedure_1973", "Section 154"),
    ],
    "fir": [
        ("Bharatiya_Nagarik_Suraksha_Sanhita_2023", "Section 173"),
        ("Code_of_Criminal_Procedure_1973", "Section 154"),
    ],
    "coparcenary": [("THE HINDU SUCCESSION ACT, 1956", "Section 6")],
    "specific performance": [("THE SPECIFIC RELIEF ACT, 1963", "Section 10")],
    "mutual consent divorce": [("The Hindu Marriage Act, 1955", "Section 13B")],
    "theft": [
        ("Bharatiya_Nyaya_Sanhita_2023", "Section 303"),
        ("Indian_Penal_Code_1860", "Section 379"),
    ],
    "oral agreement": [("THE INDIAN CONTRACT ACT, 1872", "Section 10")],
    "verbal agreement": [("THE INDIAN CONTRACT ACT, 1872", "Section 10")],
    "oral contract": [("THE INDIAN CONTRACT ACT, 1872", "Section 10")],
    "verbal contract": [("THE INDIAN CONTRACT ACT, 1872", "Section 10")],
}

# Concepts are matched on word boundaries, not as substrings: "fir" must not fire
# on "first"/"confirm"/"fire", and "theft" should still match "thefts".
_CONCEPT_PATTERNS = {
    concept: re.compile(rf"\b{re.escape(concept)}s?\b", re.IGNORECASE)
    for concept in CONCEPT_SECTIONS
}


def concept_sections(query: str):
    """(document_stem, section) pairs for any known lay concept named in the query."""
    q = query or ""
    hits = []
    for concept, refs in CONCEPT_SECTIONS.items():
        if _CONCEPT_PATTERNS[concept].search(q):
            hits.extend(refs)
    return hits


def _norm(stem: str) -> str:
    """Whitespace-insensitive registry key (handles trailing-space filenames).

    Deliberately CASE-SENSITIVE: registry keys are the real filename stems and
    are matched as written. Do not fold this into norm_doc_key below.
    """
    return re.sub(r"\s+", " ", (stem or "")).strip()


def norm_doc_key(stem: str) -> str:
    """Case-folded document stem, for comparing stems ACROSS sources.

    Retrieval compares stems that arrive from chunk metadata and from router
    scopes, where casing is not guaranteed, so this lowercases as well. Distinct
    from _norm above, which must stay case-sensitive for registry lookups.
    """
    return re.sub(r"\s+", " ", (stem or "")).strip().lower()


_BY_NORM = {_norm(k): v for k, v in DOCUMENTS.items()}


def is_registered(stem: str) -> bool:
    """Whether a document stem has a registry entry (whitespace-insensitive)."""
    return _norm(stem) in _BY_NORM


def get_doc_meta(stem: str) -> dict:
    """Registry row for a document stem, or a safe default for unknown docs."""
    meta = _BY_NORM.get(_norm(stem))
    if meta:
        return meta
    return {"title": "", "category": "General", "era": CURRENT,
            "law_type": "", "law_area": "", "kw": []}


def category_of(stem: str) -> str:
    return get_doc_meta(stem).get("category", "General")


def agent_for_category(category: str) -> str:
    return CATEGORY_AGENT.get(category, "General")


def documents_for_category(category: str) -> set:
    """Stems in this category PLUS its linked categories (recall-safe scope)."""
    cats = {category} | set(CATEGORY_ALSO_PULL.get(category, []))
    return {stem for stem, meta in DOCUMENTS.items() if meta["category"] in cats}


def all_categories() -> list:
    return sorted({m["category"] for m in DOCUMENTS.values()})


def all_stems() -> set:
    return set(DOCUMENTS.keys())
