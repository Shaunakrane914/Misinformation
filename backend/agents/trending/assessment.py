"""
Aegis Protocol — Trending Assessment & Misinformation Risk
==========================================================
Deterministic sentiment quantification and misinformation risk evaluation.
Enforces strict separation: negative criticism/reviews are NOT misinformation.
"""

from typing import Any, Dict, List, Tuple
from backend.agents.trending.models import TrendEvidence


def compute_cluster_sentiment(items: List[TrendEvidence]) -> Tuple[str, int]:
    """Calculate sentiment independently from misinformation."""
    pos_words = ["success", "record", "celebrates", "praise", "milestone", "excited", "stellar", "love", "hit", "blockbuster"]
    neg_words = ["flop", "disaster", "criticism", "backlash", "boycott", "angry", "poor", "loss", "bad", "terrible"]

    score = 0
    for it in items:
        t = (it.title + " " + it.snippet).lower()
        pos_c = sum(1 for w in pos_words if w in t)
        neg_c = sum(1 for w in neg_words if w in t)
        score += (pos_c * 20) - (neg_c * 25)

    bounded = max(-100, min(100, score))
    if bounded > 20:
        label = "POSITIVE"
    elif bounded < -20:
        label = "NEGATIVE"
    elif abs(bounded) <= 20 and len(items) > 3:
        label = "MIXED"
    else:
        label = "NEUTRAL"

    return label, bounded


def evaluate_misinformation_risk(
    items: List[TrendEvidence],
    claims: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """
    Evaluate misinformation risk.
    CRITICAL: Negative sentiment or movie criticism is NOT misinformation.
    """
    unverified_claims = [c for c in claims if c.get("status") == "UNVERIFIED"]
    contradicted_claims = [c for c in claims if c.get("status") == "CONTRADICTED"]
    all_text = " ".join([it.title + " " + it.snippet for it in items]).lower()

    deepfake_flag = any(w in all_text for w in ["deepfake", "ai clone", "fake voice", "synthetic video", "manipulated video"])
    hoax_flag = any(w in all_text for w in ["death hoax", "fake news", "fabricated statement", "forged"])

    if deepfake_flag or hoax_flag or len(contradicted_claims) > 0:
        return "HIGH", "Circulating claims involve confirmed falsehoods, hoaxes, or synthetic media allegations."

    if len(unverified_claims) >= 2 and all(it.source_role == "COMMUNITY" for it in items):
        return "MEDIUM", "Viral claims circulating solely across community social nodes without credible primary corroboration."

    return "LOW", "Circulating discourse is supported by credible reporting or constitutes standard critical discussion."
