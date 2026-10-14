"""
Aegis Protocol — GitHub Native Adapter
=======================================
Acquires GitHub repositories, READMEs, code, and releases via native GitHub API
or gh CLI.
"""

import json
import logging
import time
import re
import urllib.parse
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
from backend.infrastructure.acquisition.network.http import decode_bounded_http_body, fetch_public_http

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
        host = (urllib.parse.urlsplit(candidate.canonical_url or candidate.url).hostname or "").lower().rstrip(".")
        return host in {"github.com", "www.github.com"}

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
        transport = None

        # Check if URL points to a specific repo (github.com/owner/repo)
        parsed = urllib.parse.urlsplit(target_url)
        parts = parsed.path.strip("/").split("/")
        if (parsed.hostname or "").lower().rstrip(".") not in {"github.com", "www.github.com"} or len(parts) < 2:
            return FetchedDocument(url=target_url, status="BLOCKED", backend_id=self.backend_id,
                                   failure_reason="Candidate is not a GitHub repository URL")
        owner, repo = parts[0], parts[1].removesuffix(".git")
        if any(part in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in (owner, repo)):
            return FetchedDocument(url=target_url, status="BLOCKED", backend_id=self.backend_id,
                                   failure_reason="Invalid GitHub owner or repository")
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            response = fetch_public_http(api_url, headers={"User-Agent": "AegisAgentReach/3.0",
                                                          "Accept": "application/vnd.github.v3+json"},
                                         timeout=5.0, max_bytes=1_000_000)
            raw_json_str = json.dumps(json.loads(decode_bounded_http_body(response).decode("utf-8")))
            status = "SUCCESS"
            transport = {"endpoint": response.endpoint, "network_observed_this_attempt": True,
                         "http_status": response.status_code, "content_type": response.content_type,
                         "raw_body_bytes": len(response.body), "network_latency_ms": response.latency_ms,
                         "cache_status": "UNKNOWN"}
        except Exception as e:
            err_msg = str(e)

        lat = int((time.perf_counter() - t0) * 1000)
        return FetchedDocument(
            url=target_url,
            status=status,
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            raw_content=raw_json_str,
            raw_metadata={"transport": transport},
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
            name = item.get("full_name") or item.get("name") or ""
            desc = item.get("description") or ""
            if not name and not desc:
                continue
            url = item.get("html_url") or document.url
            stars = item.get("stargazers_count")
            lang = item.get("language")
            owner = (item.get("owner") or {}).get("login")

            content_lines = []
            if name:
                content_lines.append(f"Repository: {name}")
            if lang:
                content_lines.append(f"Language: {lang}")
            if stars is not None:
                content_lines.append(f"Stars: {stars}")
            if desc:
                content_lines.append(f"Description: {desc}")
            content = "\n".join(content_lines)
            snippet = (desc or name)[:200]

            frag = EvidenceFragment(
                platform=self.platform,
                title=f"GitHub: {name}" if name else "GitHub repository metadata",
                content=content,
                url=url,
                author="",  # repository owner is not the author of this record
                published="",  # created/pushed timestamps are not article publication dates
                snippet=snippet,
                score=candidate.semantic_score or 0.0,
                retrieval_method="agent_reach",
                channel_name="github",
                content_depth="STRUCTURED_METADATA",
                query_id=request.request_id,
                query_class=request.task_type,
                query_text=request.query,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id=self.backend_id,
                is_authenticated=False,
                raw_metadata={"stars": stars, "language": lang, "owner_login": owner,
                              "created_at": item.get("created_at"), "updated_at": item.get("updated_at"),
                              "pushed_at": item.get("pushed_at"),
                              "transport": document.raw_metadata.get("transport")},
            )
            frags.append(frag)

        return frags
