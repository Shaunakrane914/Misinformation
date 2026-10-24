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
        return "UNASSESSED", "Source records mention disputed claims or synthetic-media concerns; keyword mentions do not establish a confirmed falsehood or measured misinformation risk."

    if len(unverified_claims) >= 2 and all(it.source_role == "COMMUNITY" for it in items):
        return "UNASSESSED", "The sampled community claims are unverified; source counts do not establish virality or calibrated misinformation risk."

    return "UNASSESSED", "Attributed reporting or standard critical discussion does not establish absence of misinformation; no proposition-level risk assessment was completed."


def detect_bot_amplification(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Stage 8C Trending Specialization:
    Detect coordinated inauthentic behavior, bot amplification, and copypasta campaigns.
    Examines burst cadence, verbatim text repetition across distinct handles, and suspicious account patterns.
    """
    if len(posts) < 2:
        return {
            "status": "INSUFFICIENT_SIGNALS",
            "amplification_risk": "NOMINAL",
            "coordination_score": 0,
            "burst_detected": False,
            "copypasta_clusters": 0,
            "indicators": ["Insufficient posts (<2) to evaluate cross-account coordination."]
        }

    indicators: List[str] = []
    suspicious_handles = 0
    import re
    from backend.agents.trending.temporal import parse_timestamp_epoch

    # 1. Suspicious handle syntax pattern (e.g. user1238491, bot_pulse99)
    bot_handle_regex = re.compile(r'^(?:user\d{4,}|bot_|[a-z]{4,}\d{5,}|anon_\d+)$', re.I)
    for p in posts:
        author = p.get("author", "").lstrip("@").strip()
        if bot_handle_regex.match(author):
            suspicious_handles += 1

    # 2. Text repetition (copypasta) check
    texts = []
    for p in posts:
        raw = p.get("content", p.get("title", p.get("snippet", "")))
        words = set(re.findall(r'[a-z]{3,}', raw.lower()))
        texts.append({"post": p, "words": words, "raw": raw})

    duplicate_pairs = 0
    n = len(texts)
    for i in range(n):
        for j in range(i + 1, n):
            w1 = texts[i]["words"]
            w2 = texts[j]["words"]
            if not w1 or not w2:
                continue
            jaccard = len(w1 & w2) / len(w1 | w2)
            if jaccard >= 0.70:
                duplicate_pairs += 1

    # 3. Time burst cadence (<15 minutes between distinct posts)
    epochs = [parse_timestamp_epoch(p.get("published_at", p.get("published", ""))) for p in posts]
    valid_epochs = sorted([ep for ep in epochs if ep > 0])
    burst_detected = False
    if len(valid_epochs) >= 3:
        span_sec = valid_epochs[-1] - valid_epochs[0]
        if span_sec < 900:  # <15 minutes
            burst_detected = True
            indicators.append(f"Posting burst: {len(valid_epochs)} items published within {int(span_sec)} seconds.")

    if duplicate_pairs > 0:
        indicators.append(f"Copypasta text reuse: {duplicate_pairs} pairwise near-duplicate content matches detected.")
    if suspicious_handles > 0:
        indicators.append(f"Account syntax anomaly: {suspicious_handles} posters match automated naming conventions.")

    # Calculate coordination score (0-100)
    score = 0
    if burst_detected:
        score += 35
    if duplicate_pairs >= 2:
        score += 40
    elif duplicate_pairs == 1:
        score += 25
    if suspicious_handles >= 2:
        score += 25
    elif suspicious_handles == 1:
        score += 15

    score = min(100, score)

    if score >= 65:
        risk = "HIGH_PATTERN_SIMILARITY"
    elif score >= 35:
        risk = "ELEVATED_SUSPICIOUS_ACTIVITY"
    else:
        risk = "NO_PATTERN_ESTABLISHED_IN_SAMPLE"

    return {
        "status": "ANALYSIS_COMPLETE",
        "automation_verified": False,
        "assessment_is_heuristic": True,
        "sampling_scope": "provided_public_records_only",
        "amplification_risk": risk,
        "coordination_score": score,
        "burst_detected": burst_detected,
        "copypasta_clusters": duplicate_pairs,
        "suspicious_handle_count": suspicious_handles,
        "indicators": indicators if indicators else ["The provided sample does not establish coordination or organic provenance."]
    }


def track_claim_mutations(seed_claim: str, variant_texts: List[str]) -> Dict[str, Any]:
    """
    Stage 8C Trending Specialization:
    Tracks lexical and sensational mutation hops from an initial seed claim into viral variants.
    Identifies additions of inflammatory modifiers (e.g. 'deadly', 'exposed', 'arrested', 'secret').
    """
    if not seed_claim or not variant_texts:
        return {
            "status": "INSUFFICIENT_DATA",
            "seed_claim": seed_claim,
            "mutations": [],
            "max_sensationalism_drift": 0.0
        }

    import re
    seed_clean = seed_claim.lower()
    seed_words = set(re.findall(r'[a-z]{3,}', seed_clean))

    inflammatory_lexicon = {
        "secret", "exposed", "deadly", "hoax", "banned", "arrested",
        "scandal", "leaked", "conspiracy", "admitted", "confessed", "illegal"
    }

    mutations: List[Dict[str, Any]] = []
    max_drift = 0.0

    for idx, var in enumerate(variant_texts):
        v_clean = var.lower()
        v_words = set(re.findall(r'[a-z]{3,}', v_clean))
        if not v_words:
            continue

        added_words = v_words - seed_words
        dropped_words = seed_words - v_words
        jaccard = len(seed_words & v_words) / len(seed_words | v_words) if (seed_words | v_words) else 1.0

        # Count added inflammatory markers
        inflammatory_added = [w for w in added_words if w in inflammatory_lexicon]
        drift_score = round(max(0.0, (1.0 - jaccard) * 0.6 + len(inflammatory_added) * 0.2), 2)
        if drift_score > max_drift:
            max_drift = drift_score

        mutations.append({
            "variant_id": f"mut_{idx+1:02d}",
            "variant_text": var,
            "similarity_to_seed": round(jaccard, 2),
            "added_terms": sorted(list(added_words))[:6],
            "dropped_terms": sorted(list(dropped_words))[:6],
            "inflammatory_modifiers_added": inflammatory_added,
            "drift_score": drift_score,
            "mutation_type": "INFLAMMATORY_ESCALATION" if inflammatory_added else ("LEXICAL_DRIFT" if jaccard < 0.6 else "MINOR_VARIANT")
        })

    return {
        "status": "ANALYSIS_COMPLETE",
        "seed_claim": seed_claim,
        "mutation_count": len(mutations),
        "mutations": mutations,
        "max_sensationalism_drift": max_drift,
        "assessment": (
            f"Analyzed {len(mutations)} narrative variants. Max sensationalism drift: {max_drift}. "
            + ("Inflammatory modifiers observed." if any(m["inflammatory_modifiers_added"] for m in mutations) else "Variants remain largely consistent with seed proposition.")
        )
    }

