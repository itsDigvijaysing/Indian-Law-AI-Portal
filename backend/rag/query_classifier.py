"""
Query Classifier — stage 1 of the two-stage router.

Deterministic keyword/label classifier over the document registry. No LLM call
by default (retrieval already makes one for reformulation). Returns the query's
best legal CATEGORY plus a confidence and an era hint; the caller turns the
category into a preferred-document scope via document_registry.

Output dict:
  category       best-guess legal category (or None if nothing matched)
  confidence     0..1 separation between the top and runner-up category
  era_intent     'pre-2024' | 'post-2024' | None (present both)
  cross_cutting  True when the query spans domains (caller should NOT scope)
  scores         top-3 {category: score} for debugging
"""

import re
from collections import defaultdict

try:
    from .document_registry import DOCUMENTS
except ImportError:
    from document_registry import DOCUMENTS

# Aggregate routing keywords per category from the registry.
_CATEGORY_KW = defaultdict(list)
for _stem, _meta in DOCUMENTS.items():
    _CATEGORY_KW[_meta["category"]].extend(_meta.get("kw", []))

_LEGACY_CUES = ("ipc", "crpc", "indian evidence act", "before 2024", "pre-2024",
                "old law", "earlier law", "prior to july 2024", "1860", "1973")
_CURRENT_CUES = ("bns", "bnss", "bsa", "bharatiya", "sakshya", "new law",
                 "after 2024", "current criminal law", "2023 act")


def _era_intent(q: str):
    legacy = any(c in q for c in _LEGACY_CUES)
    current = any(c in q for c in _CURRENT_CUES)
    if legacy and not current:
        return "pre-2024"
    if current and not legacy:
        return "post-2024"
    return None  # neither, or both mentioned → present both provisions


def classify(query: str) -> dict:
    q = (query or "").lower()
    scores = defaultdict(float)
    for cat, kws in _CATEGORY_KW.items():
        for kw in kws:
            if kw in q:
                # multi-word keywords are stronger signals than single tokens
                scores[cat] += 1.0 + 0.5 * kw.count(" ")

    if not scores:
        return {"category": None, "confidence": 0.0, "era_intent": _era_intent(q),
                "cross_cutting": True, "scores": {}}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_cat, top_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    confidence = (top_score - second) / top_score if top_score else 0.0
    return {
        "category": top_cat,
        "confidence": round(confidence, 2),
        "era_intent": _era_intent(q),
        # a near-tie between the top two categories means the query is genuinely
        # cross-cutting; don't narrow the scope in that case.
        "cross_cutting": confidence < 0.34,
        "scores": dict(ranked[:3]),
    }
