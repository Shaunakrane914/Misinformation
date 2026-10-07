"""
Aegis Protocol — GitHub Native Adapter
=======================================
Acquires GitHub repositories, READMEs, code, and releases via native GitHub API
or gh CLI.
"""

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.agent_reach.native.adapters.base import PlatformAdapter
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)


class GitHubAdapter(PlatformAdapter):
    """
    Acquires GitHub repositories and documentation.
    """

    @property
    def platform(self) -> str:
        return "github"

    @property
    def backend_id(self) -> str:
        return "github_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        return candidate.platform.lower() == "github" or "github.com" in url

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url

        # 1. SSRF Gate
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                failure_reason=f"SSRF validation failed: {reason}",
            )

        t0 = time.perf_counter()
        raw_json_str = ""
        status = "FAILED"
        err_msg = None

        # Check if URL points to a specific repo (github.com/owner/repo)
        import re
        m = re.search(r"github\.com/([^/]+)/([^/]+)", target_url)
        if m:
            owner, repo = m.group(1), m.group(2).rstrip(".git")
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "AegisAgentReach/3.0",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=7.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_json_str = json.dumps(data)
                    status = "SUCCESS"
            except Exception as e:
                err_msg = str(e)
        else:
            # Search repositories
            q = request.query or candidate.title or "repository"
            api_url = f"https://api.github.com/search/repositories?q={urllib.parse.quote_plus(q)}&per_page=5"
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "AegisAgentReach/3.0",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=7.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    items = data.get("items", [])
                    raw_json_str = json.dumps(items)
                    status = "SUCCESS"
            except Exception as e:
                err_msg = str(e)

        lat = int((time.perf_counter() - t0) * 1000)
        return FetchedDocument(
            url=target_url,
            status=status,
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            raw_content=raw_json_str,
            latency_ms=lat,
            failure_reason=err_msg,
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        try:
            parsed = json.loads(document.raw_content)
        except Exception:
            return []

        items = [parsed] if isinstance(parsed, dict) else parsed
        frags: List[EvidenceFragment] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("full_name") or item.get("name") or "GitHub Repo"
            desc = item.get("description") or "No description provided."
            url = item.get("html_url") or document.url
            stars = item.get("stargazers_count", 0)
            lang = item.get("language") or "Code"
            owner = (item.get("owner") or {}).get("login") or "github"

            content = f"Repository: {name}\nLanguage: {lang}\nStars: {stars}\n\nDescription:\n{desc}"
            snippet = f"{name} ({stars} stars): {desc[:200]}"

            frag = EvidenceFragment(
                platform=self.platform,
                title=f"GitHub: {name}",
                content=content,
                url=url,
                author=owner,
                published=item.get("pushed_at") or datetime.now(timezone.utc).isoformat(),
                snippet=snippet,
                score=candidate.semantic_score or 1.0,
                retrieval_method="agent_reach",
                channel_name="github",
                content_depth="PARTIAL_CONTENT",
                query_id=request.request_id,
                query_class=request.task_type,
                query_text=request.query,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id=self.backend_id,
                is_authenticated=False,
                raw_metadata={"stars": stars, "language": lang},
            )
            frags.append(frag)

        return frags
