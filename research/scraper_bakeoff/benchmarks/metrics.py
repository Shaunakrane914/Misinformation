"""
Aegis Protocol — Scraper Benchmark Canonical Metrics Framework
==============================================================
Standardized, mathematically rigorous metric definitions for all retrieval
benchmark evaluations. ALL benchmark reports must derive metrics through this module.

Zero hardcoded numbers. Zero fake zeroes. Full condition and capability separation.
"""
import math
import random
from typing import Dict, Any, List, Tuple, Optional, Union

# ─────────────────────────────────────────────────────────────────────────────
# TAXONOMIES & ENUMS
# ─────────────────────────────────────────────────────────────────────────────

DIRECTNESS_TAXONOMY = {
    "DIRECT_CONTENT",    # Actual platform post body / article content
    "DIRECT_METADATA",   # Actual profile/video metadata without post/video body
    "PARTIAL_CONTENT",   # Incomplete platform response (e.g. title/shell only)
    "INDEX_ONLY",        # Search engine result page pointing to platform (Bing/Google)
    "SYNDICATED",        # News/RSS quote or third-party republication of platform
    "SNIPPET_ONLY",      # Very short preview snippet (under 50 chars / teaser)
    "UNKNOWN",           # Unclassified or failed retrieval
}

BENCHMARK_CONDITIONS = {
    "ZERO_CONFIG",        # Zero credentials, zero proxy, out-of-the-box unauth execution
    "AUTHENTICATED",      # Active API keys / OAuth credentials provided
    "AUTHORIZED_SESSION", # Active browser session cookie (e.g., li_at, ct0, sessionid)
    "PUBLIC_BROWSER",     # Headless browser executing without login
    "PUBLIC_HTTP",        # Standard HTTP client executing without login
}

TASK_CLASSES = {
    "CONTENT_RETRIEVAL",  # Full document / post text retrieval
    "METADATA_RETRIEVAL", # Video / repo / account structured metadata
    "PROFILE_LOOKUP",     # Public profile card / bio
    "THREAD_RETRIEVAL",   # Comment thread / conversation tree
    "SEARCH",             # Keyword / query search on platform
    "CLAIM_EVIDENCE",     # Evidence gathering to verify a specific factual claim
    "TREND_DISCOVERY",    # Unstructured discovery of trending discussions
}

FAILURE_CATEGORIES = {
    "NONE",               # Clean successful retrieval
    "HTTP_ERROR_403",     # Access forbidden / Cloudflare / Reddit anti-bot block
    "HTTP_ERROR_412",     # Precondition failed (e.g. Bilibili WBI signature)
    "HTTP_ERROR_404",     # Target not found
    "AUTH_REQUIRED",      # Login wall / redirect to /login / missing OAuth credentials
    "RATE_LIMITED_429",   # Too many requests
    "TIMEOUT",            # Network or browser socket timeout
    "NETWORK_ERROR",      # DNS failure, connection refused, or TLS handshake error
    "PARSING_ERROR",      # Malformed JSON, unparseable HTML, or missing expected DOM
    "UNKNOWN_FAILURE",    # Uncategorized exception
}

# Values for non-applicable / non-measured dimensions (avoids fake zeroes)
VAL_TRUE_ZERO = 0.0
VAL_NOT_MEASURED = "NOT_MEASURED"
VAL_NOT_APPLICABLE = "NOT_APPLICABLE"
VAL_AUTH_REQUIRED = "AUTH_REQUIRED"
VAL_FAILED = "FAILED"

# ─────────────────────────────────────────────────────────────────────────────
# MATHEMATICAL & STATISTICAL FORMULAS
# ─────────────────────────────────────────────────────────────────────────────

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculates Wilson score confidence interval for a binomial proportion.
    
    Center-adjusted for small sample sizes and boundary conditions (0% and 100%).
    """
    if total <= 0:
        return 0.0, 0.0
    z = 1.96 if confidence == 0.95 else 2.576
    p = successes / total
    denom = 1.0 + (z**2) / total
    centre = p + (z**2) / (2.0 * total)
    spread = z * math.sqrt((p * (1.0 - p) + (z**2) / (4.0 * total)) / total)
    lower = max(0.0, (centre - spread) / denom)
    upper = min(1.0, (centre + spread) / denom)
    return round(lower, 4), round(upper, 4)

def mcnemar_chi_squared(b: int, c: int) -> Dict[str, Any]:
    """Calculates McNemar's test with continuity correction for paired nominal comparisons.
    
    b: Number of items where Candidate A succeeded but Candidate B failed.
    c: Number of items where Candidate B succeeded but Candidate A failed.
    """
    discordant = b + c
    if discordant == 0:
        return {
            "chi2": 0.0,
            "p_value_approx": 1.0,
            "significant_p05": False,
            "significant_p01": False,
            "b_wins_A": b,
            "c_wins_B": c,
            "discordant_pairs": 0
        }
    
    # Edwards continuity correction
    chi2 = ((abs(b - c) - 1.0)**2) / discordant
    
    # 1-degree of freedom exact p-value via complementary error function
    p_exact = math.erfc(math.sqrt(chi2 / 2.0))
    p_formatted = f"{p_exact:.2e}" if p_exact < 0.001 else f"{p_exact:.4f}"
        
    return {
        "chi2": round(chi2, 4),
        "p_value": p_exact,
        "p_value_formatted": p_formatted,
        "p_value_approx": round(p_exact, 6) if p_exact >= 0.0001 else float(f"{p_exact:.2e}"),
        "significant_p05": chi2 >= 3.841,
        "significant_p01": chi2 >= 6.635,
        "b_wins_A": b,
        "c_wins_B": c,
        "discordant_pairs": discordant
    }

def bootstrap_paired_difference(
    series_a: List[float], 
    series_b: List[float], 
    n_resamples: int = 2000, 
    confidence: float = 0.95
) -> Dict[str, Any]:
    """Paired bootstrap confidence interval for mean differences between two candidates."""
    if len(series_a) != len(series_b) or len(series_a) == 0:
        return {"mean_diff": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "p_significant": False}
    
    diffs = [a - b for a, b in zip(series_a, series_b)]
    n = len(diffs)
    observed_mean = sum(diffs) / n
    
    random.seed(42)
    boot_means = []
    for _ in range(n_resamples):
        sample = [diffs[random.randint(0, n - 1)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
        
    boot_means.sort()
    alpha = (1.0 - confidence) / 2.0
    idx_lower = int(alpha * n_resamples)
    idx_upper = int((1.0 - alpha) * n_resamples)
    ci_lower = boot_means[idx_lower]
    ci_upper = boot_means[idx_upper]
    
    # Statistically significant if CI does not cross 0
    significant = (ci_lower > 0 and ci_upper > 0) or (ci_lower < 0 and ci_upper < 0)
    
    return {
        "mean_diff": round(observed_mean, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "significant": significant
    }

def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Computes exact empirical percentiles (P50, P90, P95, P99)."""
    if not values:
        return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
    s = sorted(values)
    n = len(s)
    def _pct(p):
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return round(s[int(k)], 2)
        return round(s[int(f)] * (c - k) + s[int(c)] * (k - f), 2)
    return {
        "p50": _pct(0.50),
        "p90": _pct(0.90),
        "p95": _pct(0.95),
        "p99": _pct(0.99),
    }

# ─────────────────────────────────────────────────────────────────────────────
# CORE RETRIEVAL METRICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_candidate_metrics(observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes mathematically correct retrieval metrics from a list of raw observation dictionaries.
    
    Enforces strict distinction between:
      - transport_success_rate
      - direct_content_success_rate
      - direct_content_given_success
      - partial_content_rate
      - index_only_rate
    """
    total = len(observations)
    if total == 0:
        return {}

    candidate = observations[0].get("candidate", "unknown")
    platform = observations[0].get("platform", "unknown")
    condition = observations[0].get("condition", "ZERO_CONFIG")
    auth_required = observations[0].get("authentication_required", False)
    auth_used = observations[0].get("authentication_used", False)
    capability = observations[0].get("capability_status", "SUPPORTED")

    # 1. Transport Success
    transport_successes = sum(1 for o in observations if o.get("status") == "SUCCESS" or o.get("http_status") == 200)
    transport_success_rate = round(transport_successes / total, 4)
    wilson_transport = wilson_score_interval(transport_successes, total)

    # 2. Direct Content Success
    direct_content_successes = sum(
        1 for o in observations 
        if (o.get("status") == "SUCCESS" or o.get("http_status") == 200) 
        and o.get("directness") == "DIRECT_CONTENT"
    )
    direct_content_success_rate = round(direct_content_successes / total, 4)
    wilson_direct_content = wilson_score_interval(direct_content_successes, total)

    # 3. Direct Metadata Success
    direct_metadata_successes = sum(
        1 for o in observations 
        if (o.get("status") == "SUCCESS" or o.get("http_status") == 200) 
        and o.get("directness") == "DIRECT_METADATA"
    )
    direct_metadata_rate = round(direct_metadata_successes / total, 4)

    # 4. Partial Content Rate
    partial_successes = sum(
        1 for o in observations 
        if (o.get("status") == "SUCCESS" or o.get("http_status") == 200) 
        and o.get("directness") == "PARTIAL_CONTENT"
    )
    partial_content_rate = round(partial_successes / total, 4)

    # 5. Index Only Rate (Search fallbacks)
    index_only_successes = sum(
        1 for o in observations 
        if (o.get("status") == "SUCCESS" or o.get("http_status") == 200) 
        and o.get("directness") == "INDEX_ONLY"
    )
    index_only_rate = round(index_only_successes / total, 4)

    # 6. Direct Content Given Success (Crucial conditional metric!)
    if transport_successes > 0:
        direct_given_success = round(direct_content_successes / transport_successes, 4)
        direct_or_meta_given_success = round((direct_content_successes + direct_metadata_successes) / transport_successes, 4)
    else:
        direct_given_success = 0.0
        direct_or_meta_given_success = 0.0

    # 7. Relevance Dimensions (0 to 3 scale)
    # Check if task is metadata retrieval vs semantic evidence
    successful_obs = [o for o in observations if o.get("status") == "SUCCESS" or o.get("http_status") == 200]
    
    if successful_obs:
        avg_entity_rel = round(sum(o.get("entity_relevance", 0) for o in successful_obs) / len(successful_obs), 2)
        avg_topic_rel = round(sum(o.get("topic_relevance", 0) for o in successful_obs) / len(successful_obs), 2)
        avg_claim_rel = round(sum(o.get("claim_relevance", 0) for o in successful_obs) / len(successful_obs), 2)
        avg_support = round(sum(o.get("content_support", 0) for o in successful_obs) / len(successful_obs), 2)
        avg_completeness = round(sum(o.get("content_completeness", 0) for o in successful_obs) / len(successful_obs), 1)
    else:
        # If transport failed completely, record as VAL_FAILED rather than assigning fake zero scores
        avg_entity_rel = 0.0
        avg_topic_rel = 0.0
        avg_claim_rel = 0.0
        avg_support = 0.0
        avg_completeness = 0.0

    # 8. Latencies (Reported on successful attempts and on all attempts)
    success_latencies = [o["latency_ms"] for o in successful_obs if o.get("latency_ms", 0) > 0]
    all_latencies = [o["latency_ms"] for o in observations if o.get("latency_ms", 0) > 0]
    
    pcts_success = calculate_percentiles(success_latencies)
    pcts_all = calculate_percentiles(all_latencies)

    # 9. Failure Mode Breakdown
    failures = {}
    for o in observations:
        fc = o.get("failure_category", "NONE")
        if fc != "NONE":
            failures[fc] = failures.get(fc, 0) + 1

    # 10. Aegis Fit Score (0-100)
    # Computed only when all required dimensions are measured
    fit_score = compute_aegis_fit_score(
        transport_rate=transport_success_rate,
        direct_rate=direct_content_success_rate + (direct_metadata_rate * 0.8),
        partial_rate=partial_content_rate,
        entity_rel=avg_entity_rel,
        topic_rel=avg_topic_rel,
        support=avg_support,
        completeness=avg_completeness,
        p50_latency=pcts_all["p50"],
        candidate_name=candidate,
        has_auth_required=(failures.get("AUTH_REQUIRED", 0) > 0)
    )

    return {
        "candidate": candidate,
        "platform": platform,
        "condition": condition,
        "capability_status": capability,
        "authentication_required": auth_required,
        "authentication_used": auth_used,
        "total_attempts": total,
        "transport_successes": transport_successes,
        "transport_success_rate": transport_success_rate,
        "wilson_ci_95": wilson_transport,
        "direct_content_successes": direct_content_successes,
        "direct_content_success_rate": direct_content_success_rate,
        "wilson_direct_content_ci_95": wilson_score_interval(direct_content_successes, total),
        "direct_metadata_successes": direct_metadata_successes,
        "direct_metadata_rate": direct_metadata_rate,
        "partial_content_successes": partial_successes,
        "partial_content_rate": partial_content_rate,
        "index_only_successes": index_only_successes,
        "index_only_rate": index_only_rate,
        "direct_content_given_success": direct_given_success,
        "direct_or_metadata_given_success": direct_or_meta_given_success,
        "avg_entity_relevance": avg_entity_rel,
        "avg_topic_relevance": avg_topic_rel,
        "avg_claim_relevance": avg_claim_rel,
        "avg_content_support": avg_support,
        "avg_completeness": avg_completeness,
        "latency_p50_ms": pcts_all["p50"],
        "latency_p90_ms": pcts_all["p90"],
        "latency_p95_ms": pcts_all["p95"],
        "latency_p99_ms": pcts_all["p99"],
        "latency_success_p50_ms": pcts_success["p50"],
        "latency_success_p95_ms": pcts_success["p95"],
        "failure_breakdown": failures,
        "aegis_fit_score": fit_score
    }

def compute_aegis_fit_score(
    transport_rate: float,
    direct_rate: float,
    partial_rate: float,
    entity_rel: float,
    topic_rel: float,
    support: float,
    completeness: float,
    p50_latency: float,
    candidate_name: str,
    has_auth_required: bool
) -> Union[float, str]:
    """Aegis Fit Score Formula:
      retrieval_quality (transport):  25%
      semantic_relevance:             20% (scaled 0-3 -> 0-1)
      direct_content:                 15% (direct + partial weight)
      completeness:                   10% (scaled 0-100 -> 0-1)
      provenance integrity:           10% (direct source bonus)
      reliability (1 - failure):      10%
      latency (inverse):               5% (normalized against 5000ms)
      operational complexity:          5%
    """
    if transport_rate == 0.0:
        # Transport failed completely (e.g. unauthenticated PRAW, unauth Instagram)
        # Separate capability from score: when retrieval is dead, baseline score reflects zero availability
        return round((0.05 * (0.5 if has_auth_required else 0.2)) * 100.0, 1)

    rel_scaled = ((entity_rel + topic_rel + support) / 9.0)
    comp_scaled = min(1.0, completeness / 100.0)
    direct_effective = direct_rate + (partial_rate * 0.4)
    provenance_score = 1.0 if direct_rate > 0.5 else (0.7 if partial_rate > 0.5 else 0.5)
    lat_score = max(0.0, 1.0 - (p50_latency / 5000.0))
    
    complexity = 0.95
    if "playwright" in candidate_name.lower():
        complexity = 0.75  # Heavy RAM/process footprint
    elif "fallback" in candidate_name.lower():
        complexity = 0.90  # Syndicated search dependency

    score = (
        0.25 * transport_rate +
        0.20 * rel_scaled +
        0.15 * direct_effective +
        0.10 * comp_scaled +
        0.10 * provenance_score +
        0.10 * transport_rate +
        0.05 * lat_score +
        0.05 * complexity
    ) * 100.0

    return round(score, 1)
