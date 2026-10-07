# SCOUT FAILURE MODEL SPECIFICATION
**Aegis Protocol — Agent 1: Scout Proprietary Source Acquisition Engine**
*Phase 3 Deliverable — Structured Failure Taxonomy & Fallback Handling*

---

## 1. Core Principle: Never Fail Silently

In a trading and verification architecture, returning an empty list `[]` or a silent failure corrupts downstream reasoning.
Downstream agents (`ResearchAgent`, `InvestigatorAgent`, `CoordinatorAgent`) must understand **why** an acquisition failed:
- Was the source deleted?
- Did the search engine return zero results?
- Was it rate-limited?
- Was it blocked due to SSRF defenses?
- Did it fail semantic entity matching?

Every failed acquisition returns an explicit `ScoutFailureCode` accompanied by a diagnostic message and execution telemetry.

---

## 2. Taxonomy of Failure Codes (`ScoutFailureCode`)

```python
from enum import Enum


class ScoutFailureCode(str, Enum):
    # Discovery Failures
    DISCOVERY_EMPTY = "DISCOVERY_EMPTY"                    # Zero search/index results returned
    DISCOVERY_RATE_LIMITED = "DISCOVERY_RATE_LIMITED"      # Search engine 429 or CAPTCHA challenge
    DISCOVERY_TIMEOUT = "DISCOVERY_TIMEOUT"                # Search query exceeded latency budget

    # Validation & Gate Failures
    INVALID_URL = "INVALID_URL"                            # Malformed URL syntax
    BLOCKED_SSRF = "BLOCKED_SSRF"                          # Private IP, loopback, or cloud metadata blocked
    SOURCE_SCOPE_MISMATCH = "SOURCE_SCOPE_MISMATCH"        # Mismatch with requested subreddit/account
    INVALID_URL_STRUCTURE = "INVALID_URL_STRUCTURE"        # Generic homepages or non-content URLs
    TOKEN_CHEAT_REJECTED = "TOKEN_CHEAT_REJECTED"          # Ambiguous single-token match without context
    DOMAIN_REJECTED = "DOMAIN_REJECTED"                    # Irrelevant corporate or aggregator domain

    # Acquisition Failures
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"            # HTTP 404, 410, or page removed
    MIRROR_UNAVAILABLE = "MIRROR_UNAVAILABLE"              # Arctic Shift or FxTwitter mirror down
    AUTH_REQUIRED = "AUTH_REQUIRED"                        # Target requires login/session (zero-auth reject)
    RATE_LIMITED = "RATE_LIMITED"                          # Upstream endpoint 429
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"                    # Acquisition exceeded timeout budget
    CONNECTION_FAILED = "CONNECTION_FAILED"                # TCP/DNS resolution error

    # Extraction & Parsing Failures
    PARSE_FAILED = "PARSE_FAILED"                          # Unable to parse HTML/JSON DOM
    INSUFFICIENT_CONTENT = "INSUFFICIENT_CONTENT"          # Content length < 50 characters / stub page
    METADATA_MISSING = "METADATA_MISSING"                  # Critical publication timestamps absent

    # Semantic & Quality Failures
    SEMANTICALLY_IRRELEVANT = "SEMANTICALLY_IRRELEVANT"    # Failed entity/topic relevance scoring
    CONTRADICTION_UNRESOLVED = "CONTRADICTION_UNRESOLVED"  # Irreconcilable conflicting claims
    STALE_CONTENT = "STALE_CONTENT"                        # Content exceeds requested freshness window
```

---

## 3. Failure Escalation & Recovery Matrix

| Failure Code | Primary Action | Fallback Strategy | Telemetry Attribution |
|---|---|---|---|
| `DISCOVERY_EMPTY` | Broaden query | Query expansion with ticker/executive synonyms | `discovery_retries += 1` |
| `DISCOVERY_RATE_LIMITED` | Back off | Switch from Bing to Yahoo / RSS Discovery | `retrieval_mode = "rss_feed"` |
| `MIRROR_UNAVAILABLE` | Retry mirror | Fall back to direct HTTP / Jina Reader | `fallback_reason = "MIRROR_DOWN"` |
| `CONTENT_UNAVAILABLE` | Check archive | Fall back to syndicated search snippets | `content_depth = "SNIPPET"` |
| `AUTH_REQUIRED` | Do NOT bypass | Fall back to public search snippets or fail | `is_authenticated = False` |
| `BLOCKED_SSRF` | Terminate | Never bypass security boundary | `security_violation = True` |
| `TOKEN_CHEAT_REJECTED` | Terminate | Candidate discarded; evaluate next rank | `rejection_reason = "TOKEN_CHEAT"` |
| `SOURCE_SCOPE_MISMATCH`| Terminate | Candidate discarded; evaluate next rank | `rejection_reason = "SCOPE_MISMATCH"` |

---

## 4. Provenance Transparency

Whenever Scout falls back to secondary mechanisms, the evidence fragment's provenance records:
- `requested_channel`: What the user or agent originally wanted (e.g., `reddit`).
- `actual_channel`: Where it was fetched (e.g., `reddit` via Arctic Shift, or `news_rss`).
- `retrieval_mode`: Exact mechanism (`zero_auth_public_mirror`, `direct_api`, `syndicated_fallback`).
- `fallback_reason`: The exact `ScoutFailureCode` that triggered the cascade.
- `is_authenticated`: Strict boolean `False` for zero-auth public extractions.
