# SCOUT DATA CONTRACT SPECIFICATION
**Aegis Protocol — Agent 1: Scout Proprietary Source Acquisition Engine**
*Formal Interfaces & Data Exchange Contracts*

---

## 1. Input Contract: `ScoutSourceRequest`

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FreshnessRequirement(str, Enum):
    BREAKING_5M = "BREAKING_5M"        # < 5 minutes
    RECENT_30M = "RECENT_30M"          # 5 to 30 minutes
    INTRADAY_2H = "INTRADAY_2H"        # 30m to 2 hours
    DAILY_24H = "DAILY_24H"            # 2 to 24 hours
    WEEKLY_7D = "WEEKLY_7D"            # 1 to 7 days
    ALL_TIME = "ALL_TIME"              # Regulatory filings / historical context


@dataclass
class ScoutSourceRequest:
    query: str
    target_entity: str = ""
    tickers: List[str] = field(default_factory=list)
    sectors: List[str] = field(default_factory=list)
    event_types: List[str] = field(default_factory=list)
    target_sources: List[str] = field(default_factory=list)
    requested_scope: str = ""
    requested_author: str = ""
    requested_domain: str = ""
    platform_hint: Optional[str] = None
    freshness_requirement: FreshnessRequirement = FreshnessRequirement.DAILY_24H
    max_candidates: int = 5            # Default to TOP 5 candidate pool based on benchmark ablation
    max_depth: int = 2
    required_source_tier: str = "TIER_4_COMMUNITY"
    allow_social: bool = True
    allow_fallback: bool = True
    force_refresh: bool = False
    context: Dict[str, Any] = field(default_factory=dict)
```

---

## 2. Evidence Contract: `ScoutEvidence`

Extends and maps 100% losslessly into Aegis `EvidenceFragment`:

```python
@dataclass
class ScoutEvidence:
    evidence_id: str
    url: str
    canonical_url: str
    platform: str
    source_type: str
    source_tier: str
    external_id: str
    title: str
    author: str
    body: str
    snippet: str
    published_at: str
    event_at: Optional[str]
    retrieved_at: str
    financial_facts: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    entities: List[str]
    tickers: List[str]
    score: float
    relevance_score: float
    quality_score: float
    freshness_score: float
    retrieval_mode: str
    adapter: str
    search_engine: str
    is_authenticated: bool = False
    is_primary: bool = False
    syndicated_from: Optional[str] = None
    cluster_id: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
```

---

## 3. Top-Level Result Contract: `ScoutResult`

```python
@dataclass
class ScoutResult:
    query: str
    entity: str
    evidence_items: List[ScoutEvidence]
    clusters: List[Any]
    financial_facts: List[Any]
    events: List[Any]
    contradictions: List[Any]
    primary_source_present: bool
    independent_source_count: int
    epistemic_status: str
    telemetry: Dict[str, Any]
```
