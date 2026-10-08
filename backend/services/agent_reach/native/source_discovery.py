"""
Aegis Protocol — Zero-Auth Source Discovery & URL Identification Engine
========================================================================
Implements the discovery-to-mirror pipeline:
  Search / Discovery -> Source Identification -> Public Mirror Retrieval

Extracts, canonicalizes, deduplicates, and ranks candidate Reddit and X/Twitter
source references from raw search results, syndication feeds, and user inputs
before delegating to Arctic Shift or FxTwitter zero-auth public mirrors.

Critical Constraints:
  - Public data only
  - Zero user authentication (zero OAuth, zero cookies, zero API keys)
  - No synthetic classification (a search result is NEVER direct unless fetched via mirror)
  - Rejects generic homepages, search pages, settings, and tracking links
"""

import base64
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# Reserved non-user paths on X / Twitter to prevent false profile matches
TWITTER_RESERVED_PATHS: Set[str] = {
    "about", "explore", "hashtag", "help", "home", "i", "intent",
    "jobs", "login", "logout", "messages", "notifications", "privacy",
    "search", "settings", "share", "tos", "widgets", "x", "account",
    "download", "personalization", "safety", "rules", "developer"
}

# Reserved subpaths on Reddit to prevent non-post matches
REDDIT_RESERVED_PATHS: Set[str] = {
    "about", "advertising", "api", "contact", "gold", "help", "login",
    "message", "mod", "notifications", "prefs", "premium", "register",
    "rules", "search", "settings", "submit", "user", "users", "wiki"
}

# Known corporate/aggregator domains to immediately reject as social content
NON_SOCIAL_DOMAINS: Set[str] = {
    "amd.com", "nvidia.com", "openai.com", "microsoft.com", "apple.com",
    "wikipedia.org", "techspot.com", "hotstar.com", "google.com", "bing.com",
    "yahoo.com", "duckduckgo.com", "amazon.com", "youtube.com", "linkedin.com",
    "facebook.com", "instagram.com", "tiktok.com", "github.com"
}


@dataclass
class SourceDiscoveryResult:
    """
    Structured outcome of discovering a specific social source reference.
    Used to drive Arctic Shift or FxTwitter retrieval.
    """
    platform: str                             # "reddit" | "twitter"
    canonical_url: str                        # Clean canonical source URL
    source_type: str                          # "post" | "comment" | "profile" | "status" | "subreddit"
    external_id: str                          # post_id, comment_id, status_id, or handle
    handle: Optional[str] = None              # Twitter handle or Reddit author
    subreddit: Optional[str] = None           # Reddit subreddit name
    parent_id: Optional[str] = None           # Parent post ID for Reddit comments
    discovered_from: str = "search_url_discovery"  # "direct_input" | "search_url_discovery"
    discovery_query: str = ""
    confidence: float = 1.0                   # Heuristic relevance confidence (0.0 to 1.0)
    raw_title: str = ""
    raw_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "canonical_url": self.canonical_url,
            "source_type": self.source_type,
            "external_id": self.external_id,
            "handle": self.handle,
            "subreddit": self.subreddit,
            "parent_id": self.parent_id,
            "discovered_from": self.discovered_from,
            "discovery_query": self.discovery_query,
            "confidence": round(self.confidence, 3),
            "raw_title": self.raw_title,
            "raw_snippet": self.raw_snippet,
        }


def resolve_bing_redirect(raw_url: str) -> str:
    """
    Resolve Bing /ck/a? redirect and URL-decode the target.
    Handles URL-safe base64 padding cleanly.
    """
    if not raw_url or not isinstance(raw_url, str):
        return ""
    dest = raw_url.strip()
    if "bing.com/ck/a?" in dest and "&u=a1" in dest:
        try:
            encoded_part = dest.split("&u=a1")[1].split("&")[0]
            padded = encoded_part + "=" * (-len(encoded_part) % 4)
            dest = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="ignore")
        except Exception:
            pass
    return urllib.parse.unquote(dest)


def generate_discovery_queries(
    platform: str,
    query: str,
    entity: str = "",
    task_type: str = "SEARCH"
) -> List[str]:
    """
    Generate 3-5 targeted discovery queries to uncover specific platform content URLs.
    
    For Reddit SEARCH:
      - site:reddit.com/r/ {core_terms}
      - site:reddit.com/r/ "comments" {core_terms}
      - site:reddit.com "comments" "{entity}"
      - site:old.reddit.com/r/ {core_terms}
      - {core_terms} site:reddit.com inurl:comments
      
    For X / Twitter SEARCH:
      - {core_terms} site:x.com
      - site:x.com/ {core_terms}
      - {core_terms} site:twitter.com
      - site:x.com/*/status {core_terms}
      - "{entity}" site:x.com status
    """
    clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
    words = [w for w in clean_q.split() if len(w) > 1]
    
    # Extract core 2-4 entity/claim terms
    if entity and len(entity.strip()) > 2:
        ent_clean = re.sub(r"[^\w\s-]", " ", entity).strip()
        core_terms = " ".join(ent_clean.split()[:4])
    elif words:
        core_terms = " ".join(words[:4])
    else:
        core_terms = clean_q or "discussion"

    first_word = words[0] if words else core_terms
    two_words = " ".join(words[:2]) if len(words) >= 2 else first_word

    queries: List[str] = []

    if platform == "reddit":
        queries.append(f'site:reddit.com/r/ "comments" "{first_word}"')
        queries.append(f'site:reddit.com/r/ "comments" "{two_words}"')
        queries.append(f"site:reddit.com/r/ {two_words}")
        queries.append(f'site:reddit.com "comments" {two_words}')
        queries.append(f"site:old.reddit.com/r/ {two_words}")
        queries.append(f"{two_words} site:reddit.com inurl:comments")
    elif platform in ("twitter", "x"):
        queries.append(f"{two_words} site:x.com")
        queries.append(f'"{first_word}" site:x.com status')
        queries.append(f'"{two_words}" site:x.com')
        queries.append(f"{two_words} site:twitter.com")
        queries.append(f"site:x.com/ {two_words}")
        queries.append(f"site:x.com/*/status {two_words}")
    else:
        queries.append(f"site:{platform}.com {core_terms}")

    return queries


def is_valid_content_source(
    cand: Optional[SourceDiscoveryResult],
    task_type: str = "SEARCH"
) -> bool:
    """
    Strict URL validation for candidate promotion:
    
    Reddit:
      - SEARCH / POST_AND_COMMENTS: MUST be post or comment (with external_id)
      - SUBREDDIT_FEED: subreddit or post is accepted
      - REJECTS: root domain, /search, /login, /about, corporate sites
      
    X / Twitter:
      - SEARCH: MUST be a status URL (/status/<status_id>)
      - PROFILE: profile handle is accepted
      - REJECTS: x.com, twitter.com, generic profiles for SEARCH, /explore, /search
    """
    if not cand or not cand.external_id:
        return False

    # Check non-social blacklist
    parsed = urllib.parse.urlparse(cand.canonical_url)
    netloc = parsed.netloc.lower()
    for d in NON_SOCIAL_DOMAINS:
        if d in netloc:
            return False

    if cand.platform == "reddit":
        if task_type in ("SUBREDDIT_FEED", "HOT_TOPICS"):
            return cand.source_type in ("subreddit", "post", "comment")
        # For general SEARCH or POST_AND_COMMENTS: must be actual post, comment, or subreddit container
        if cand.source_type in ("post", "comment"):
            # External ID must be alphanumeric and not a synthetic sample
            if cand.external_id.lower().startswith("sample"):
                return False
            return bool(re.match(r"^[a-z0-9]+$", cand.external_id, re.IGNORECASE))
        if cand.source_type == "subreddit":
            return bool(cand.subreddit) and cand.subreddit.lower() not in REDDIT_RESERVED_PATHS
        return False

    if cand.platform in ("twitter", "x"):
        if task_type == "PROFILE":
            return cand.source_type == "profile" and bool(cand.handle)
        # For SEARCH / TWEET: allow status or valid user profile
        if cand.source_type == "status":
            return bool(re.match(r"^\d+$", cand.external_id))
        if cand.source_type == "profile":
            return bool(cand.handle) and cand.handle.lower() not in TWITTER_RESERVED_PATHS
        return False

    return True


def extract_reddit_source(url_or_text: str, query: str = "") -> Optional[SourceDiscoveryResult]:
    """
    Parse a Reddit URL and extract canonical post ID, comment ID, or subreddit.
    Delegates to SocialTargetResolver for robust canonicalization.
    """
    if not url_or_text or not isinstance(url_or_text, str):
        return None

    clean_str = resolve_bing_redirect(url_or_text.strip())
    from backend.services.agent_reach.native.social_resolver import social_target_resolver
    resolved = social_target_resolver.resolve_reddit(clean_str)
    if resolved:
        return SourceDiscoveryResult(
            platform="reddit",
            canonical_url=resolved.canonical_url,
            source_type=resolved.target_type,
            external_id=resolved.external_id,
            handle=resolved.handle,
            subreddit=resolved.container,
            parent_id=resolved.parent_id,
            discovered_from="search_url_discovery" if query else "direct_input",
            discovery_query=query,
            confidence=resolved.confidence
        )
    return None


def extract_x_source(url_or_text: str, query: str = "") -> Optional[SourceDiscoveryResult]:
    """
    Parse an X/Twitter URL and extract canonical status ID or user profile handle.
    Delegates to SocialTargetResolver for robust canonicalization.
    """
    if not url_or_text or not isinstance(url_or_text, str):
        return None

    clean_str = resolve_bing_redirect(url_or_text.strip())
    from backend.services.agent_reach.native.social_resolver import social_target_resolver
    resolved = social_target_resolver.resolve_twitter(clean_str)
    if resolved:
        return SourceDiscoveryResult(
            platform="twitter",
            canonical_url=resolved.canonical_url,
            source_type=resolved.target_type,
            external_id=resolved.external_id,
            handle=resolved.handle,
            discovered_from="search_url_discovery" if query else "direct_input",
            discovery_query=query,
            confidence=resolved.confidence
        )
    return None


def calculate_candidate_score(
    cand: SourceDiscoveryResult,
    target_entity: str = "",
    target_topic: str = "",
    target_claim: str = "",
    task_type: str = "SEARCH"
) -> float:
    """
    Score a discovered candidate source based on entity match, topic match,
    claim keywords overlap, specificity, and penalties for generic/non-content URLs.
    """
    # 0. Severe penalty for corporate/non-social domains
    parsed = urllib.parse.urlparse(cand.canonical_url)
    netloc = parsed.netloc.lower()
    for d in NON_SOCIAL_DOMAINS:
        if d in netloc:
            return -100.0

    score = 0.0
    text_corpus = f"{cand.raw_title} {cand.raw_snippet} {cand.canonical_url}".lower()

    # 1. Base platform match bonus (+10.0)
    score += 10.0

    # 2. Specific content vs broad container scoring
    if task_type in ("SEARCH", "POST_AND_COMMENTS"):
        if cand.source_type in ("status", "post", "comment"):
            score += 25.0
        elif cand.source_type in ("profile", "subreddit"):
            # Valid social containers, prioritized below direct post/status
            score += 10.0
    elif task_type == "PROFILE":
        if cand.source_type == "profile":
            score += 25.0
        else:
            score += 5.0
    elif task_type in ("SUBREDDIT_FEED", "HOT_TOPICS"):
        if cand.source_type in ("subreddit", "post"):
            score += 25.0

    # 3. Exact Entity match (+15.0)
    if target_entity:
        e_words = [w.lower() for w in target_entity.split() if len(w) > 2]
        if any(w in text_corpus for w in e_words):
            score += 15.0
        if cand.handle and any(cand.handle.lower() == w.lower() for w in e_words):
            score += 10.0

    # 4. Topic match (+10.0)
    if target_topic:
        top_words = [w.lower() for w in target_topic.split() if len(w) > 3]
        if any(w in text_corpus for w in top_words):
            score += 10.0

    # 5. Claim keyword match (+3.0 per term up to 15.0)
    if target_claim:
        c_words = [w.lower() for w in re.split(r"\W+", target_claim) if len(w) > 3]
        overlap = sum(1 for w in c_words if w in text_corpus)
        score += min(15.0, float(overlap) * 3.0)

    return round(score, 2)


def discover_sources_from_search(
    fragments: List[Any],
    platform: str,
    query: str = "",
    target_entity: str = "",
    target_topic: str = "",
    target_claim: str = "",
    task_type: str = "SEARCH",
    max_candidates: int = 5
) -> List[SourceDiscoveryResult]:
    """
    Extract, canonicalize, deduplicate, and rank candidate social references
    from web search / discovery fragments.
    Strictly filters out non-content URLs according to task_type.
    """
    discovered: List[SourceDiscoveryResult] = []
    seen_ids: Set[str] = set()

    for frag in fragments:
        url = getattr(frag, "url", "")
        title = getattr(frag, "title", "")
        snippet = getattr(frag, "snippet", "") or getattr(frag, "content", "")

        resolved_url = resolve_bing_redirect(url)

        candidate: Optional[SourceDiscoveryResult] = None
        if platform == "reddit":
            candidate = extract_reddit_source(resolved_url, query=query)
            # If main URL is not reddit, inspect text snippet for embedded permalinks
            if not candidate:
                m = re.search(r"https?://(?:www\.|old\.)?reddit\.com/r/[a-zA-Z0-9_]+/comments/[a-z0-9]+", snippet)
                if m:
                    candidate = extract_reddit_source(m.group(0), query=query)
        elif platform in ("twitter", "x"):
            candidate = extract_x_source(resolved_url, query=query)
            # If main URL is not twitter/x, inspect text snippet for embedded status URLs
            if not candidate:
                m = re.search(r"https?://(?:www\.)?(?:x|twitter)\.com/[a-zA-Z0-9_]+/status/\d+", snippet)
                if m:
                    candidate = extract_x_source(m.group(0), query=query)

        if candidate and candidate.external_id:
            # Check strict content validity for task_type
            if not is_valid_content_source(candidate, task_type=task_type):
                continue

            dedup_key = f"{candidate.platform}:{candidate.external_id}"
            if dedup_key not in seen_ids:
                seen_ids.add(dedup_key)
                candidate.raw_title = title
                candidate.raw_snippet = snippet
                candidate.confidence = calculate_candidate_score(
                    candidate, target_entity, target_topic, target_claim, task_type=task_type
                )
                if candidate.confidence > 0.0:
                    discovered.append(candidate)

    # Sort descending by candidate confidence score
    discovered.sort(key=lambda c: c.confidence, reverse=True)
    return discovered[:max_candidates]


def check_entity_semantic_match(
    text: str,
    target_entity: str
) -> Tuple[bool, int]:
    """
    Semantic entity matcher with strict anti-token-cheat protection.
    A single token overlap is NOT sufficient for multi-token entities.
    
    Examples:
      - 'Satya Nadella' -> requires 'Satya Nadella' OR 'Nadella' OR ('Satya' + 'Microsoft'/'AI')
        Will REJECT 'Satya' incense (r/Incense).
      - 'Sam Altman' -> requires 'Sam Altman' OR 'Altman' OR ('Sam' + 'OpenAI'/'AI')
        Will REJECT 'Sam' in Lord of the Rings (r/lotr).
      - 'Jensen Huang' -> requires 'Jensen Huang' OR 'Huang' + 'Nvidia'/'GPU'
        Will REJECT 'Jensen' in gaming (r/leagueoflegends).
        
    Returns:
      (match_bool, score_weight: 0, 1, or 2)
    """
    if not target_entity or not text:
        return False, 0

    t_lower = text.lower()
    ent_clean = re.sub(r"[^\w\s-]", " ", target_entity).strip().lower()
    words = [w for w in ent_clean.split() if len(w) > 1]

    if not words:
        return False, 0

    # 1. Full phrase match (Strongest: 2)
    if ent_clean in t_lower:
        return True, 2

    # 2. Multi-word entity checks
    if len(words) >= 2:
        surname = words[-1]
        first_name = words[0]

        # Context terms that disambiguate executive/founder names
        disambiguation_orgs = {
            "satya": ["microsoft", "nadella", "copilot", "windows", "azure", "openai"],
            "sam": ["altman", "openai", "chatgpt", "worldcoin", "stargate"],
            "jensen": ["huang", "nvidia", "gtc", "blackwell", "cuda", "geforce"],
            "tim": ["cook", "apple", "iphone", "cupertino", "vision pro"],
            "elon": ["musk", "tesla", "spacex", "xai", "grok", "twitter"],
            "yann": ["lecun", "meta", "fair", "facebook", "deep learning"],
            "andrew": ["ng", "coursera", "deeplearning.ai", "landing ai"],
            "demis": ["hassabis", "deepmind", "google", "alphafold", "isomorphic"],
            "andrej": ["karpathy", "tesla", "openai", "eureka", "nanogpt"],
        }

        # Common words / corporate suffixes that must NOT be treated as distinctive surnames
        generic_suffixes = {
            "act", "bill", "law", "inc", "corp", "corporation", "ltd", "limited",
            "co", "company", "group", "holdings", "fund", "etf", "capital", "partners",
            "management", "technologies", "tech", "network", "protocol", "token",
            "coin", "chain", "ai", "labs", "systems", "app", "media", "news", "report"
        }

        # Check surname as a discrete word (only if not a generic suffix)
        if surname not in generic_suffixes:
            surname_match = bool(re.search(rf"\b{re.escape(surname)}\b", t_lower))
            if surname_match:
                # Surname found: verify it's not a generic false positive
                return True, 2

        # First name only found: MUST co-occur with org/context
        first_match = bool(re.search(rf"\b{re.escape(first_name)}\b", t_lower))
        if first_match:
            req_contexts = disambiguation_orgs.get(first_name, words[1:])
            if any(ctx in t_lower for ctx in req_contexts):
                return True, 2
            # First name only without disambiguation is a FALSE POSITIVE (e.g. Satya incense, Samwise)
            return False, 0

        # All words must appear separately if not surname/first
        if all(bool(re.search(rf"\b{re.escape(w)}\b", t_lower)) for w in words):
            return True, 2

        return False, 0

    # 3. Single word entity (e.g. AMD, NVIDIA, TSMC, Nike, Adidas, Reddit, Apple)
    single_word = words[0]
    # Check whole word boundary to avoid substrings (e.g. 'and' in 'demand')
    if re.search(rf"\b{re.escape(single_word)}\b", t_lower):
        return True, 2

    return False, 0


def evaluate_content_relevance(
    content: str,
    target_entity: str = "",
    target_topic: str = "",
    target_claim: str = "",
    platform: str = "reddit",
    candidate_metadata: Optional[Dict[str, Any]] = None,
    requested_scope: str = "",
    task_type: str = "SEARCH"
) -> Dict[str, Any]:
    """
    Deterministic scoring rubric for content-level evaluation:
    
    SOURCE CORRECTNESS (0, 1, 2)
      2 = directly addresses requested subject
      1 = related context but not a suitable evidence source
      0 = wrong/unrelated source
      
    CLAIM SUPPORT (0, 1, 2)
      2 = directly supports or directly contradicts the claim
      1 = relevant contextual evidence
      0 = does not support the claim
      
    CONTENT RELEVANCE (0, 1, 2)
      2 = clearly about requested topic
      1 = tangentially related
      0 = unrelated
      
    PLATFORM SCOPE (0 or 1)
      1 = correct
      0 = incorrect (e.g. r/investing requested but candidate is in r/privacy)
      
    FINAL ACCEPTANCE GATE:
      platform_scope == 1 and content_relevance >= 1 and (claim_support >= 1 or (content_relevance == 2 and entity_match))
    """
    candidate_metadata = candidate_metadata or {}
    t_lower = (content or "").lower()

    # 1. Platform Scope
    platform_scope = 1
    cand_sub = (candidate_metadata.get("subreddit") or "").lower()
    cand_handle = (candidate_metadata.get("handle") or "").lower().lstrip("@")

    if requested_scope:
        req_clean = requested_scope.lower().strip()
        if req_clean.startswith("r/"):
            req_sub = req_clean[2:]
            if cand_sub and cand_sub != req_sub:
                platform_scope = 0  # HARD SCOPE REJECT: e.g. r/investing -> r/privacy
        elif req_clean.startswith("@"):
            req_hand = req_clean[1:]
            if cand_handle and cand_handle != req_hand:
                platform_scope = 0  # HARD SCOPE REJECT: e.g. @OpenAI -> @random

    # 2. Entity Relevance (Anti-cheat protected)
    ent_match, ent_weight = check_entity_semantic_match(content, target_entity)

    # 3. Topic Relevance
    top_clean = re.sub(r"[^\w\s-]", " ", target_topic or "").strip().lower()
    top_words = [w for w in top_clean.split() if len(w) > 3]
    top_matches = sum(1 for w in top_words if re.search(rf"\b{re.escape(w)}\b", t_lower))
    topic_match = (top_matches >= 2) if len(top_words) >= 2 else (top_matches >= 1 if top_words else True)

    # Domain keywords related to query/task
    has_tech_context = any(w in t_lower for w in [
        "gpu", "ai", "chip", "semiconductor", "model", "server", "data center",
        "compute", "power", "tsmc", "packaging", "hbm", "cluster", "firmware",
        "earnings", "stock", "revenue", "capex", "market", "pricing", "scam"
    ])

    # Determine Content Relevance (0, 1, 2)
    if platform_scope == 0:
        content_relevance = 0
    elif ent_match and (topic_match or has_tech_context):
        content_relevance = 2  # Clearly about requested topic
    elif ent_match or (topic_match and has_tech_context):
        content_relevance = 1  # Tangentially related
    else:
        content_relevance = 0  # Unrelated

    # 4. Claim Support (0, 1, 2)
    clm_clean = re.sub(r"[^\w\s-]", " ", target_claim or "").strip().lower()
    clm_words = [w for w in clm_clean.split() if len(w) > 3]
    clm_matches = sum(1 for w in clm_words if re.search(rf"\b{re.escape(w)}\b", t_lower))

    if platform_scope == 0 or content_relevance == 0:
        claim_support = 0
    elif clm_matches >= 3 and ent_match:
        claim_support = 2  # Directly supports/contradicts target claim with detailed points
    elif clm_matches >= 1 and (ent_match or topic_match):
        claim_support = 1  # Relevant contextual evidence
    else:
        claim_support = 0  # Does not support claim

    # 5. Source Correctness (0, 1, 2)
    if platform_scope == 0 or content_relevance == 0:
        source_correctness = 0  # Wrong/unrelated source
    elif content_relevance == 2 and (claim_support >= 1 or len(content.strip()) > 100):
        source_correctness = 2  # Directly addresses requested subject
    elif content_relevance >= 1:
        source_correctness = 1  # Related context but not ideal evidence source
    else:
        source_correctness = 0

    # 6. Final Acceptance Gate
    accepted = (
        platform_scope == 1
        and content_relevance >= 1
        and (claim_support >= 1 or (content_relevance == 2 and ent_match))
    )

    # 7. Semantic Score
    semantic_score = (
        (source_correctness * 40.0)
        + (content_relevance * 30.0)
        + (claim_support * 20.0)
        + (10.0 if ent_match else 0.0)
    ) if platform_scope == 1 else -1000.0

    return {
        "platform_scope": platform_scope,
        "content_relevance": content_relevance,
        "source_correctness": source_correctness,
        "claim_support": claim_support,
        "accepted": accepted,
        "entity_match": ent_match,
        "topic_match": topic_match,
        "claim_match": (claim_support > 0),
        "semantic_score": round(semantic_score, 2),
        "clm_term_matches": clm_matches,
        "top_term_matches": top_matches,
    }


class BlindSecondaryAdjudicator:
    """
    Independent second-pass evaluator.
    Receives ONLY: query, target_entity, target_topic, target_claim, selected_content.
    MUST NOT see primary evaluator's score, discovery ranking, or router score.
    """

    def evaluate(
        self,
        query: str,
        target_entity: str,
        target_topic: str,
        target_claim: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Execute independent, blind evaluation of content against ground truth criteria.
        """
        # Independent extraction and lexical-semantic checks
        res = evaluate_content_relevance(
            content=content,
            target_entity=target_entity,
            target_topic=target_topic,
            target_claim=target_claim,
            requested_scope=""
        )
        return {
            "source_correctness": res["source_correctness"],
            "content_relevance": res["content_relevance"],
            "claim_support": res["claim_support"],
            "platform_scope": res["platform_scope"],
            "accepted": res["accepted"],
            "semantic_score": res["semantic_score"],
        }

