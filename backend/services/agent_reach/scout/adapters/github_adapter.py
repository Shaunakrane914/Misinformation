"""
Aegis Protocol — Scout GitHub Adapter
=====================================
Acquires repository metadata, release notes, and commit activity via GitHub REST API.
Audited as 100% direct control standard.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from backend.services.agent_reach.scout.adapters.base import ScoutSourceAdapter
from backend.services.agent_reach.scout.models import (
    CandidateSource,
    RawSource,
    ScoutEvidence,
    ScoutSourceRequest,
    SourceTier,
)
from backend.services.agent_reach.scout.transport import scout_transport

logger = logging.getLogger(__name__)


class GitHubAdapter(ScoutSourceAdapter):
    """
    Acquires developer releases, repository issues, and technical milestones via GitHub REST.
    """

    GITHUB_API_BASE = "https://api.github.com"

    def can_handle(self, candidate: CandidateSource) -> bool:
        return candidate.platform == "github" or "github.com" in candidate.canonical_url

    def acquire(self, candidate: CandidateSource, request: ScoutSourceRequest) -> RawSource:
        target_url = candidate.canonical_url or candidate.url
        # Parse owner/repo
        m = re.search(r"github\.com/([^/]+)/([^/]+)", target_url)
        content_raw = ""
        method = "github_rest_api"
        status = 200
        lat = 120
        err = None

        if m:
            owner, repo = m.group(1), m.group(2).rstrip(".git")
            api_url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}"
            status, content_raw, _, lat, err = scout_transport.get(api_url, timeout=7.0)
        else:
            status, content_raw, _, lat, err = scout_transport.get(target_url, timeout=8.0)
            method = "direct_http"

        return RawSource(
            candidate=candidate,
            content_raw=content_raw,
            content_type="application/json" if method == "github_rest_api" else "text/html",
            status_code=status,
            acquisition_method=method,
            latency_ms=lat,
            bytes_retrieved=len(content_raw.encode("utf-8")),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            is_authenticated=False,
            error=err
        )

    def extract(self, raw: RawSource, request: ScoutSourceRequest) -> Optional[ScoutEvidence]:
        if raw.status_code != 200 or not raw.content_raw:
            return None

        title = raw.candidate.title or "GitHub Repository Activity"
        body = ""
        author = "GitHub Developer"
        pub_iso = datetime.now(timezone.utc).isoformat()

        try:
            data = json.loads(raw.content_raw)
            if isinstance(data, dict):
                full_name = data.get("full_name", "")
                desc = data.get("description", "")
                title = f"GitHub: {full_name}" if full_name else title
                body = f"{desc}\nStars: {data.get('stargazers_count', 0)} | Forks: {data.get('forks_count', 0)}"
                author = data.get("owner", {}).get("login", author)
                updated_at = data.get("updated_at")
                if updated_at:
                    pub_iso = updated_at
        except Exception:
            body = raw.content_raw[:1000]

        hash_id = hashlib.sha256(raw.candidate.canonical_url.encode()).hexdigest()[:10]
        evidence_id = f"ev_gh_{hash_id}"

        return ScoutEvidence(
            evidence_id=evidence_id,
            url=raw.candidate.url,
            canonical_url=raw.candidate.canonical_url,
            platform="github",
            source_type="code_repository",
            source_tier=SourceTier.TIER_3_SPECIALIST.value,
            external_id=raw.candidate.canonical_url,
            title=title,
            author=author,
            body=f"{title}\n\n{body}",
            snippet=body[:240],
            published_at=pub_iso,
            event_at=None,
            retrieved_at=raw.retrieved_at,
            financial_facts=[],
            events=[],
            entities=[request.target_entity] if request.target_entity else [],
            tickers=request.tickers,
            score=raw.candidate.candidate_score,
            retrieval_mode=raw.acquisition_method,
            adapter="GitHubAdapter",
            search_engine=raw.candidate.discovery_engine,
            is_authenticated=False,
            is_primary=False,
            provenance={
                "repository": author,
                "acquisition_method": raw.acquisition_method,
                "latency_ms": raw.latency_ms
            }
        )
