"""
Aegis Protocol — Native Agent Reach Secure Allowlisted Executor
===============================================================
Executes upstream platform tools (gh CLI, yt-dlp, Jina Reader, V2EX API,
Bilibili API, feedparser, OpenCLI, twitter-cli) through strict, parameter-checked
command allowlists. Arbitrary shell text execution is strictly prohibited.
"""

import base64
import binascii
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from backend.infrastructure.acquisition.network.http import (
    BoundedHTTPResponse,
    ProviderHTTPError,
    decode_bounded_http_body,
    fetch_public_http,
)
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details, extract_readable_page
from backend.services.agent_reach.native.errors import (
    AuthRequiredError,
    BackendExecutionError,
    NativeReachError,
    SecurityPolicyViolation,
)
from backend.services.agent_reach.native.runtime import RuntimeProfile, get_runtime_profile
from backend.services.url_validator import is_safe_url

logger = logging.getLogger(__name__)

# Execution security boundaries
DEFAULT_TIMEOUT_SECONDS = 12.0
MAX_OUTPUT_BYTES = 1_000_000  # Shared public acquisition response cap
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 AegisAgentReach/3.0"


def _caption_segments(text: str) -> List[Dict[str, str]]:
    """Extract bounded VTT/SRT cues without pretending that captions are audio analysis."""
    timing = re.compile(
        r"(?:(\d{1,2}):)?(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+"
        r"(?:(\d{1,2}):)?(\d{2}):(\d{2})[.,](\d{3})"
    )
    segments: List[Dict[str, str]] = []
    for block in re.split(r"\r?\n\s*\r?\n", text):
        lines = block.splitlines()
        cue = next((index for index, line in enumerate(lines) if timing.search(line)), None)
        if cue is None:
            continue
        match = timing.search(lines[cue])
        if match is None:
            continue
        words = " ".join(line.strip() for line in lines[cue + 1:] if line.strip())
        if not words:
            continue
        def clock(groups: Tuple[Optional[str], ...]) -> str:
            return f"{int(groups[0] or 0):02}:{int(groups[1]):02}:{int(groups[2]):02}.{groups[3]}"
        segments.append({
            "start": clock(match.groups()[:4]),
            "end": clock(match.groups()[4:]),
            "text": words[:1000],
        })
        # One look-ahead cue distinguishes exactly 500 from truncation.
        if len(segments) >= 501:
            break
    return segments


class NativeExecutor:
    """
    Allowlisted command dispatcher executing tools according to upstream Agent Reach
    skill specifications. Operates in parameter array mode (never shell=True).
    """

    def __init__(self):
        self.profile = get_runtime_profile()

    # ── 1. Web Page Reading (Bounded HTTP Primary -> Bounded Jina) ──

    def execute_web_read(self, url: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Read any public web page following Policy D:
        Primary: redirect-safe, bounded lightweight HTTP extraction
        Secondary: bounded Jina extraction for empty or challenged documents.
        Browser and external URL-decoder requests cannot honor the pinned-IP
        boundary and therefore are not automatic production fallbacks.
        """
        clean_url = url.strip()
        safe, reason = is_safe_url(clean_url)
        if not safe:
            raise SecurityPolicyViolation(f"URL failed SSRF validation: {clean_url} ({reason})")

        t0 = time.perf_counter()
        active_backend = "native_http_reader"
        markdown_text = ""
        status_code = None
        content_type = None
        raw_body_bytes = None
        decoded_body_bytes = None
        observed_endpoint = clean_url
        selected_response: Optional[BoundedHTTPResponse] = None
        page_metadata: Dict[str, Any] = {}
        raw_capture: Dict[str, Any] = {}
        primary_http_error: Optional[ProviderHTTPError] = None

        # Primary: shared bounded HTTP.  Redirect targets are validated before
        # they are followed and the body cannot exceed MAX_OUTPUT_BYTES.
        try:
            headers = {
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            response = fetch_public_http(
                clean_url, headers=headers, timeout=timeout, max_bytes=MAX_OUTPUT_BYTES
            )
            status_code = response.status_code
            raw_body_bytes = len(response.body)
            decoded_body = decode_bounded_http_body(response, max_bytes=MAX_OUTPUT_BYTES)
            decoded_body_bytes = len(decoded_body)
            raw_text = decoded_body.decode("utf-8")
            if any(ord(character) < 32 and character not in "\t\r\n" for character in raw_text):
                raise ValueError("HTTP response contains binary control characters")
            content_type = response.content_type
            media_type = (content_type or "").split(";", 1)[0].strip().lower()
            if media_type and not (
                media_type.startswith("text/")
                or media_type in ("application/xhtml+xml", "application/xml", "application/json", "application/ld+json")
            ):
                raise ValueError("HTTP response is not a text document")
            observed_endpoint = response.endpoint

            if (
                "html" in (content_type or "").lower()
                or raw_text.lstrip().lower().startswith(("<!doctype html", "<html"))
            ):
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(raw_text, "html.parser")

                def meta_content(*, name: str = "", prop: str = "") -> str:
                    tag = soup.find("meta", attrs={"name": name}) if name else soup.find(
                        "meta", attrs={"property": prop}
                    )
                    return str(tag.get("content") or "").strip() if tag else ""

                title_tag = soup.find("title")
                title = meta_content(prop="og:title") or (
                    title_tag.get_text(" ", strip=True) if title_tag else ""
                )
                canonical_tag = soup.find("link", rel="canonical")
                page_metadata = {
                    "title": title[:500],
                    "author": meta_content(name="author")[:300],
                    "published": (
                        meta_content(prop="article:published_time")
                        or meta_content(name="citation_publication_date")
                        or meta_content(name="datePublished")
                    )[:100],
                    "modified": meta_content(prop="article:modified_time")[:100],
                    "declared_canonical_url": (
                        str(canonical_tag.get("href") or "")[:1000]
                        if canonical_tag else ""
                    ),
                    "headings": [
                        heading.get_text(" ", strip=True)[:300]
                        for heading in soup.find_all(("h1", "h2", "h3"), limit=20)
                    ],
                }
                if page_metadata["declared_canonical_url"]:
                    page_metadata["declared_canonical_verified"] = False
                page_metadata.update(extract_observed_page_details(soup, response.endpoint))
                extracted = extract_readable_page(soup)
                markdown_text = extracted["text"]
                page_metadata["content_scope"] = extracted["content_scope"]
                raw_text = extracted["raw_text"]
                raw_capture = {
                    "text": raw_text[:100_000], "truncated": len(raw_text) > 100_000,
                    "selection_method": extracted["selection_method"],
                    "source_text_chars": len(raw_text),
                    "source_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                }
            else:
                markdown_text = raw_text.strip()
            selected_response = response

        except ProviderHTTPError as error:
            primary_http_error = error
            logger.debug("[NativeExecutor] Bounded HTTP read failed for %s: %s", clean_url, error)
            raise
        except Exception as error:
            logger.debug("[NativeExecutor] HTTP parsing failed for %s: %s", clean_url, error)

        CHALLENGE_INDICATORS = (
            "cloudflare", "turnstile", "human security", "just a moment",
            "verify you are human", "attention required", "security check",
            "access denied", "403 forbidden"
        )
        is_challenge = any(ind in markdown_text.lower() for ind in CHALLENGE_INDICATORS)
        if is_challenge:
            markdown_text = ""

        # Browser rescue is intentionally disabled: hostname interception alone
        # cannot pin Chromium's destination DNS or bound all subresource I/O.
        # For empty/challenge responses, only the bounded Jina transport remains.
        if len(markdown_text) < 100:
            try:
                jina_url = f"https://r.jina.ai/{clean_url}"
                response = fetch_public_http(
                    jina_url,
                    headers={"User-Agent": _USER_AGENT, "Accept": "text/plain", "X-No-Cache": "true"},
                    timeout=timeout,
                    max_bytes=MAX_OUTPUT_BYTES,
                )
                decoded_body = decode_bounded_http_body(response, max_bytes=MAX_OUTPUT_BYTES)
                j_text = decoded_body.decode("utf-8").strip()
                if any(ord(character) < 32 and character not in "\t\r\n" for character in j_text):
                    raise ValueError("Reader response contains binary control characters")
                if len(j_text) > len(markdown_text):
                    markdown_text = j_text
                    # Metadata from the challenged source page must not be
                    # attached to content returned by a separate reader.
                    page_metadata = {}
                    raw_capture = {}
                    active_backend = "jina_reader_fallback"
                    status_code = response.status_code
                    content_type = response.content_type
                    raw_body_bytes = len(response.body)
                    decoded_body_bytes = len(decoded_body)
                    observed_endpoint = response.endpoint
                    selected_response = response
            except Exception as e_jina:
                logger.debug(f"[NativeExecutor] Emergency Jina fallback error: {e_jina}")

        latency_ms = int((time.perf_counter() - t0) * 1000)
        if not markdown_text:
            if primary_http_error is not None:
                raise primary_http_error
            raise BackendExecutionError("web", active_backend, clean_url, 1, "Failed to retrieve content via bounded HTTP/Jina")

        return {
            "platform": "web",
            "backend": active_backend,
            "operation": "web.read",
            "status": "SUCCESS",
            "url": clean_url,
            "content": markdown_text,
            "char_count": len(markdown_text),
            "page_metadata": page_metadata,
            "raw_capture": raw_capture,
            "latency_ms": latency_ms,
            "transport": {
                "endpoint": observed_endpoint,
                "requested_endpoint": clean_url,
                "redirect_chain": list(selected_response.redirect_chain) if selected_response else [clean_url],
                "network_observed_this_attempt": True,
                "http_status": status_code,
                "content_type": content_type,
                "raw_body_bytes": raw_body_bytes,
                "decoded_body_bytes": decoded_body_bytes,
                "raw_body_sha256": (
                    hashlib.sha256(selected_response.body).hexdigest()
                    if selected_response is not None
                    else None
                ),
                "network_latency_ms": latency_ms,
                "cache_status": "UNKNOWN",
            },
        }

    # ── 2. GitHub CLI (gh) ────────────────────────────────────────────────

    def execute_github_search(self, query: str, limit: int = 5, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Search repositories using gh CLI."""
        gh_bin = shutil.which("gh")
        if not gh_bin:
            raise BackendExecutionError("github", "gh CLI", "gh search repos", 127, "gh CLI executable not found on PATH")

        cmd = [
            gh_bin, "search", "repos", query.strip(),
            "--limit", str(min(limit, 15)),
            "--json", "fullName,description,url,stargazersCount,updatedAt"
        ]
        t0 = time.perf_counter()
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if res.returncode != 0:
                raise BackendExecutionError("github", "gh CLI", " ".join(cmd), res.returncode, res.stderr)

            repos = json.loads(res.stdout) if res.stdout.strip() else []
            return {
                "platform": "github",
                "backend": "gh CLI",
                "operation": "github.search",
                "status": "SUCCESS",
                "items": repos,
                "count": len(repos),
                "latency_ms": latency_ms,
                "transport": {
                    "endpoint": "gh search repos",
                    "network_observed_this_attempt": True,
                    "http_status": None,
                    "content_type": "application/json",
                    "raw_body_bytes": len(res.stdout.encode("utf-8", errors="replace")),
                    "network_latency_ms": latency_ms,
                    "cache_status": "UNKNOWN",
                    "protocol": "external_tool",
                },
            }
        except subprocess.TimeoutExpired:
            raise BackendExecutionError("github", "gh CLI", " ".join(cmd), 124, "Timeout expired")

    def execute_github_read(self, repo: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Read repository metadata and README using gh CLI."""
        gh_bin = shutil.which("gh")
        if not gh_bin:
            raise BackendExecutionError("github", "gh CLI", "gh repo view", 127, "gh CLI not found")

        cmd_meta = [
            gh_bin, "repo", "view", repo.strip(),
            "--json", "name,description,url,stargazerCount,latestRelease"
        ]
        t0 = time.perf_counter()
        try:
            res_meta = subprocess.run(
                cmd_meta,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if res_meta.returncode != 0:
                raise BackendExecutionError("github", "gh CLI", " ".join(cmd_meta), res_meta.returncode, res_meta.stderr)

            data = json.loads(res_meta.stdout) if res_meta.stdout.strip() else {}
            try:
                cmd_body = [gh_bin, "repo", "view", repo.strip()]
                res_body = subprocess.run(
                    cmd_body,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=min(timeout, 5.0)
                )
                if res_body.returncode == 0 and res_body.stdout.strip():
                    data["readme"] = res_body.stdout
            except Exception:
                pass

            return {
                "platform": "github",
                "backend": "gh CLI",
                "operation": "github.read",
                "status": "SUCCESS",
                "data": data,
                "latency_ms": latency_ms,
                "transport": {
                    "endpoint": "gh repo view",
                    "network_observed_this_attempt": True,
                    "http_status": None,
                    "content_type": "application/json",
                    "raw_body_bytes": len(res_meta.stdout.encode("utf-8", errors="replace")),
                    "network_latency_ms": latency_ms,
                    "cache_status": "UNKNOWN",
                    "protocol": "external_tool",
                },
            }
        except Exception as e:
            raise BackendExecutionError("github", "gh CLI", " ".join(cmd_meta), 1, str(e))

    def execute_github_rest_operation(
        self,
        repo: str,
        operation: str,
        limit: int = 5,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        page: int = 1,
        include_comments: bool = False,
        comment_limit: int = 3,
        include_files: bool = False,
        file_limit: int = 5,
    ) -> Dict[str, Any]:
        """Read a public repository or collection through the documented REST API."""
        clean_repo = repo.strip().rstrip("/")
        if "github.com/" in clean_repo:
            parsed = urllib.parse.urlparse(clean_repo if "://" in clean_repo else f"https://{clean_repo}")
            clean_repo = parsed.path.strip("/")
        clean_repo = clean_repo.removesuffix(".git")
        parts = clean_repo.split("/")
        if len(parts) < 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts[:2]):
            raise NativeReachError("GitHub operations require an owner/repository name or URL")
        clean_repo = "/".join(parts[:2])
        op = operation.lower()
        suffix = {
            "read": "",
            "issues": "/issues",
            "prs": "/pulls",
            "releases": "/releases",
            "commits": "/commits",
        }.get(op)
        if suffix is None:
            raise NativeReachError(f"Unsupported GitHub REST operation: {operation}")
        if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= 5:
            raise NativeReachError("GitHub page must be an integer from 1 to 5")
        if not isinstance(include_comments, bool):
            raise NativeReachError("GitHub include_comments must be a boolean")
        if include_comments and op != "issues":
            raise NativeReachError("Comment follow-up is supported only for GitHub issues")
        if not isinstance(comment_limit, int) or isinstance(comment_limit, bool) or not 1 <= comment_limit <= 5:
            raise NativeReachError("GitHub comment limit must be an integer from 1 to 5")
        if not isinstance(include_files, bool):
            raise NativeReachError("GitHub include_files must be a boolean")
        if include_files and op not in {"prs", "commits"}:
            raise NativeReachError("File follow-up is supported only for GitHub prs and commits")
        if not isinstance(file_limit, int) or isinstance(file_limit, bool) or not 1 <= file_limit <= 10:
            raise NativeReachError("GitHub file limit must be an integer from 1 to 10")

        # GitHub's issues collection also includes PRs. Request a modest
        # overfetch so filtering does not routinely return zero real issues.
        per_page = min(max(limit, 10 if op == "issues" else 1), 20)
        url = f"https://api.github.com/repos/{clean_repo}{suffix}"
        if suffix:
            url += f"?per_page={per_page}"
            if page > 1:
                url += f"&page={page}"
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        started = time.perf_counter()
        try:
            response = fetch_public_http(
                url, headers=headers, timeout=min(timeout, 5.0), max_bytes=MAX_OUTPUT_BYTES
            )
            data = json.loads(decode_bounded_http_body(response).decode("utf-8"))
            latency_ms = int((time.perf_counter() - started) * 1000)
            transport = self._bounded_http_transport(response)
            items = data if isinstance(data, list) else [data]
            provider_count = len(items)
            if op == "issues":
                items = [item for item in items if not item.get("pull_request")]
            filtered_pull_requests = provider_count - len(items) if op == "issues" else 0
            if op == "read":
                readme_url = f"https://api.github.com/repos/{clean_repo}/readme"
                try:
                    readme_response = fetch_public_http(
                        readme_url, headers=headers, timeout=min(timeout, 5.0),
                        max_bytes=MAX_OUTPUT_BYTES,
                    )
                    readme_meta = json.loads(decode_bounded_http_body(readme_response).decode("utf-8"))
                    encoded = readme_meta.get("content")
                    if readme_meta.get("encoding") == "base64" and isinstance(encoded, str):
                        decoded = base64.b64decode(encoded, validate=False)
                        if len(decoded) <= MAX_OUTPUT_BYTES:
                            items[0]["readme"] = decoded.decode("utf-8", errors="replace")
                            items[0]["readme_path"] = readme_meta.get("path")
                            items[0]["readme_sha"] = readme_meta.get("sha")
                            items[0]["readme_source_url"] = readme_meta.get("html_url")
                            items[0]["readme_transport"] = self._bounded_http_transport(readme_response)
                except (ProviderHTTPError, ValueError, KeyError, binascii.Error, UnicodeError):
                    # Repository metadata remains valid if README retrieval fails.
                    pass
            follow_up_requests = 0
            if op == "issues" and include_comments:
                # At most two extra requests, each with its own five-second
                # deadline. An unavailable discussion must not erase the issue.
                for item in items[:limit]:
                    count = item.get("comments") if isinstance(item, dict) else None
                    number = item.get("number") if isinstance(item, dict) else None
                    if not isinstance(count, int) or isinstance(count, bool):
                        item["comment_lookup_status"] = "NOT_REQUESTED_UNKNOWN_COUNT"
                    elif count <= 0:
                        item["comment_lookup_status"] = "NOT_APPLICABLE_ZERO_COUNT"
                    elif follow_up_requests >= 2:
                        item["comment_lookup_status"] = "NOT_REQUESTED_BUDGET"
                    elif not isinstance(number, int) or isinstance(number, bool) or number < 1:
                        item["comment_lookup_status"] = "NOT_REQUESTED_INVALID_NUMBER"
                    else:
                        follow_up_requests += 1
                        comments_url = (
                            f"https://api.github.com/repos/{clean_repo}/issues/{number}"
                            f"/comments?per_page={comment_limit}"
                        )
                        try:
                            comments_response = fetch_public_http(
                                comments_url, headers=headers,
                                timeout=min(timeout, 5.0), max_bytes=MAX_OUTPUT_BYTES,
                            )
                            comments_data = json.loads(
                                decode_bounded_http_body(comments_response).decode("utf-8")
                            )
                            if not isinstance(comments_data, list):
                                raise ValueError("GitHub comments response is not a list")
                            samples = []
                            for comment in comments_data[:comment_limit]:
                                if not isinstance(comment, dict):
                                    continue
                                body = comment.get("body")
                                body = body if isinstance(body, str) else ""
                                samples.append({
                                    "id": comment.get("id"),
                                    "url": comment.get("html_url"),
                                    "author": (comment.get("user") or {}).get("login"),
                                    "created_at": comment.get("created_at"),
                                    "updated_at": comment.get("updated_at"),
                                    "body": body[:1000],
                                    "body_truncated": len(body) > 1000,
                                })
                            item["sampled_comments"] = samples
                            item["comment_lookup_status"] = "SUCCESS" if samples else "EMPTY"
                            item["comment_has_next_page"] = (
                                'rel="next"' in comments_response.headers.get("Link", "")
                            )
                            item["comment_transport"] = self._bounded_http_transport(comments_response)
                        except Exception as error:
                            item["comment_lookup_status"] = "FAILED"
                            item["comment_failure_class"] = type(error).__name__
                            if isinstance(error, ProviderHTTPError):
                                item["comment_http_status"] = error.status_code
            if op == "prs" and include_files:
                for item in items[:limit]:
                    number = item.get("number") if isinstance(item, dict) else None
                    if follow_up_requests >= 2:
                        item["file_lookup_status"] = "NOT_REQUESTED_BUDGET"
                    elif not isinstance(number, int) or isinstance(number, bool) or number < 1:
                        item["file_lookup_status"] = "NOT_REQUESTED_INVALID_NUMBER"
                    else:
                        follow_up_requests += 1
                        files_url = (
                            f"https://api.github.com/repos/{clean_repo}/pulls/{number}"
                            f"/files?per_page={file_limit}"
                        )
                        try:
                            files_response = fetch_public_http(
                                files_url, headers=headers,
                                timeout=min(timeout, 5.0), max_bytes=MAX_OUTPUT_BYTES,
                            )
                            files_data = json.loads(
                                decode_bounded_http_body(files_response).decode("utf-8")
                            )
                            if not isinstance(files_data, list):
                                raise ValueError("GitHub PR files response is not a list")
                            samples = []
                            for f in files_data[:file_limit]:
                                if not isinstance(f, dict):
                                    continue
                                patch = f.get("patch")
                                patch = patch[:500] if isinstance(patch, str) else None
                                samples.append({
                                    "filename": f.get("filename"),
                                    "status": f.get("status"),
                                    "additions": f.get("additions"),
                                    "deletions": f.get("deletions"),
                                    "changes": f.get("changes"),
                                    "patch_excerpt": patch,
                                })
                            item["sampled_files"] = samples
                            item["file_lookup_status"] = "SUCCESS" if samples else "EMPTY"
                            item["file_transport"] = self._bounded_http_transport(files_response)
                        except Exception as error:
                            item["file_lookup_status"] = "FAILED"
                            item["file_failure_class"] = type(error).__name__
                            if isinstance(error, ProviderHTTPError):
                                item["file_http_status"] = error.status_code
            if op == "commits" and include_files:
                for item in items[:limit]:
                    sha = item.get("sha") if isinstance(item, dict) else None
                    if follow_up_requests >= 2:
                        item["file_lookup_status"] = "NOT_REQUESTED_BUDGET"
                    elif not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
                        item["file_lookup_status"] = "NOT_REQUESTED_INVALID_SHA"
                    else:
                        follow_up_requests += 1
                        commit_url = f"https://api.github.com/repos/{clean_repo}/commits/{sha}"
                        try:
                            commit_response = fetch_public_http(
                                commit_url, headers=headers,
                                timeout=min(timeout, 5.0), max_bytes=MAX_OUTPUT_BYTES,
                            )
                            commit_data = json.loads(
                                decode_bounded_http_body(commit_response).decode("utf-8")
                            )
                            if not isinstance(commit_data, dict):
                                raise ValueError("GitHub commit detail response is not a dict")
                            stats = commit_data.get("stats") if isinstance(commit_data.get("stats"), dict) else None
                            if stats:
                                item["stats"] = {
                                    "total": stats.get("total"),
                                    "additions": stats.get("additions"),
                                    "deletions": stats.get("deletions"),
                                }
                            raw_files = commit_data.get("files")
                            samples = []
                            if isinstance(raw_files, list):
                                for f in raw_files[:file_limit]:
                                    if not isinstance(f, dict):
                                        continue
                                    patch = f.get("patch")
                                    patch = patch[:500] if isinstance(patch, str) else None
                                    samples.append({
                                        "filename": f.get("filename"),
                                        "status": f.get("status"),
                                        "additions": f.get("additions"),
                                        "deletions": f.get("deletions"),
                                        "patch_excerpt": patch,
                                    })
                            item["sampled_files"] = samples
                            item["file_lookup_status"] = "SUCCESS" if (samples or stats) else "EMPTY"
                            item["file_transport"] = self._bounded_http_transport(commit_response)
                        except Exception as error:
                            item["file_lookup_status"] = "FAILED"
                            item["file_failure_class"] = type(error).__name__
                            if isinstance(error, ProviderHTTPError):
                                item["file_http_status"] = error.status_code
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "platform": "github",
                "backend": "GitHub REST API",
                "operation": f"github.{op}",
                "status": "SUCCESS" if items else "EMPTY",
                "items": items[:limit],
                "count": len(items[:limit]),
                "pagination": {
                    "page": page,
                    "per_page": per_page if suffix else None,
                    "provider_items_on_page": provider_count,
                    "filtered_pull_requests": filtered_pull_requests,
                    "has_next_page": 'rel="next"' in response.headers.get("Link", ""),
                    "next_page_supported": bool(suffix),
                },
                "repo": clean_repo,
                "latency_ms": latency_ms,
                "transport": transport,
                "follow_up_requests": follow_up_requests,
            }
        except ProviderHTTPError:
            raise
        except Exception as error:
            raise BackendExecutionError("github", "GitHub REST API", url, 1, str(error))

    # ── 3. YouTube (In-Process yt-dlp Import Primary) ──────────────────────

    def execute_youtube_search(self, query: str, limit: int = 5, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """
        Search YouTube videos using in-process yt-dlp Python import as primary path.
        Eliminates subprocess spawn latency and PATH dependency.
        """
        t0 = time.perf_counter()
        items = []

        # Primary: in-process yt_dlp import
        try:
            import yt_dlp
            search_expr = f"ytsearch{min(limit, 10)}:{query.strip()}"
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_expr, download=False)
                entries = info.get("entries", []) if info else []
                for entry in entries:
                    if entry:
                        items.append(entry)

            latency_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "platform": "youtube",
                "backend": "yt-dlp",
                "operation": "youtube.search",
                "status": "SUCCESS",
                "items": items,
                "count": len(items),
                "latency_ms": latency_ms,
                "transport": {
                    "endpoint": search_expr,
                    "network_observed_this_attempt": True,
                    "http_status": None,
                    "content_type": None,
                    "raw_body_bytes": None,
                    "network_latency_ms": latency_ms,
                    "cache_status": "UNKNOWN",
                    "protocol": "external_tool",
                },
            }
        except Exception as e_inprocess:
            logger.debug(f"[NativeExecutor] In-process yt_dlp search notice: {e_inprocess}. Trying subprocess fallback.")

        # Secondary fallback: subprocess if in-process failed
        ytdlp_bin = shutil.which("yt-dlp")
        if not ytdlp_bin:
            raise BackendExecutionError("youtube", "yt-dlp", "yt-dlp search", 127, "yt-dlp executable or module failed")

        search_expr = f"ytsearch{min(limit, 10)}:{query.strip()}"
        cmd = [
            ytdlp_bin,
            "--dump-json",
            "--flat-playlist",
            "--no-warnings",
            "--ignore-errors",
            search_expr
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            for line in res.stdout.splitlines():
                line = line.strip()
                if line and line.startswith("{"):
                    try:
                        items.append(json.loads(line))
                    except Exception:
                        pass

            return {
                "platform": "youtube",
                "backend": "yt-dlp",
                "operation": "youtube.search",
                "status": "SUCCESS",
                "items": items,
                "count": len(items),
                "latency_ms": latency_ms,
                "transport": {
                    "endpoint": search_expr,
                    "network_observed_this_attempt": True,
                    "http_status": None,
                    "content_type": "application/x-ndjson",
                    "raw_body_bytes": len(res.stdout.encode("utf-8", errors="replace")),
                    "network_latency_ms": latency_ms,
                    "cache_status": "UNKNOWN",
                    "protocol": "external_tool",
                },
            }
        except Exception as e:
            raise BackendExecutionError("youtube", "yt-dlp", " ".join(cmd), 1, str(e))

    def execute_youtube_transcript(self, url: str, timeout: float = 20.0) -> Dict[str, Any]:
        """Extract subtitles/transcripts using yt-dlp without downloading video."""
        ytdlp_bin = shutil.which("yt-dlp")
        if not ytdlp_bin:
            raise BackendExecutionError("youtube", "yt-dlp", "yt-dlp subtitles", 127, "yt-dlp not found")

        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_tmpl = os.path.join(tmp_dir, "%(id)s")
            cmd = [
                ytdlp_bin,
                "--write-sub",
                "--write-auto-sub",
                "--sub-lang", "en,zh-Hans,zh",
                "--skip-download",
                "--no-warnings",
                "-o", out_tmpl,
                url.strip()
            ]
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)

                # Look for downloaded .vtt or .srt file
                transcript_text = ""
                selected_file = ""
                for fname in sorted(os.listdir(tmp_dir)):
                    if fname.endswith((".vtt", ".srt")):
                        fpath = os.path.join(tmp_dir, fname)
                        if os.path.getsize(fpath) > MAX_OUTPUT_BYTES:
                            continue
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            transcript_text = f.read()
                        selected_file = fname
                        break

                if not transcript_text:
                    return {
                        "platform": "youtube",
                        "backend": "yt-dlp",
                        "operation": "youtube.transcript",
                        "status": "EMPTY",
                        "content": "",
                        "latency_ms": latency_ms,
                        "transport": {
                            "endpoint": url.strip(),
                            "network_observed_this_attempt": True,
                            "http_status": None,
                            "content_type": None,
                            "raw_body_bytes": None,
                            "network_latency_ms": latency_ms,
                            "cache_status": "UNKNOWN",
                            "protocol": "external_tool",
                        },
                    }

                observed_cues = _caption_segments(transcript_text)
                segments = observed_cues[:500]
                language_match = re.search(r"\.([A-Za-z]{2,3}(?:-[A-Za-z0-9]+)?)\.(?:vtt|srt)$", selected_file)
                return {
                    "platform": "youtube",
                    "backend": "yt-dlp",
                    "operation": "youtube.transcript",
                    "status": "SUCCESS",
                    "content": transcript_text,
                    "segments": segments,
                    "segments_truncated": len(observed_cues) > 500,
                    "caption_language": language_match.group(1) if language_match else None,
                    "caption_origin": "UNVERIFIED",
                    "char_count": len(transcript_text),
                    "latency_ms": latency_ms,
                    "transport": {
                        "endpoint": url.strip(),
                        "network_observed_this_attempt": True,
                        "http_status": None,
                        "content_type": "text/vtt",
                        "raw_body_bytes": len(transcript_text.encode("utf-8", errors="replace")),
                        "network_latency_ms": latency_ms,
                        "cache_status": "UNKNOWN",
                        "protocol": "external_tool",
                    },
                }
            except Exception as e:
                raise BackendExecutionError("youtube", "yt-dlp", " ".join(cmd), 1, str(e))

    # ── 4. V2EX (Public HTTPS JSON API) ───────────────────────────────────

    def execute_v2ex_hot(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Fetch hot topics from V2EX public JSON API."""
        url = "https://www.v2ex.com/api/topics/hot.json"
        t0 = time.perf_counter()
        try:
            response = fetch_public_http(
                url, headers={"User-Agent": _USER_AGENT}, timeout=timeout,
                max_bytes=MAX_OUTPUT_BYTES,
            )
            data = json.loads(decode_bounded_http_body(response).decode("utf-8"))
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "platform": "v2ex",
                "backend": "V2EX API (public)",
                "operation": "v2ex.hot",
                "status": "SUCCESS",
                "items": data,
                "count": len(data),
                "latency_ms": latency_ms,
                "transport": self._bounded_http_transport(response),
            }
        except ProviderHTTPError:
            raise
        except Exception as e:
            raise BackendExecutionError("v2ex", "V2EX API (public)", url, 1, str(e))

    def execute_v2ex_search(self, node: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Fetch topics for a specific node from V2EX public API."""
        url = f"https://www.v2ex.com/api/topics/show.json?node_name={urllib.parse.quote(node)}"
        t0 = time.perf_counter()
        try:
            response = fetch_public_http(
                url, headers={"User-Agent": _USER_AGENT}, timeout=timeout,
                max_bytes=MAX_OUTPUT_BYTES,
            )
            data = json.loads(decode_bounded_http_body(response).decode("utf-8"))
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "platform": "v2ex",
                "backend": "V2EX API (public)",
                "operation": "v2ex.search",
                "status": "SUCCESS",
                "items": data,
                "count": len(data),
                "latency_ms": latency_ms,
                "transport": self._bounded_http_transport(response),
            }
        except ProviderHTTPError:
            raise
        except Exception as e:
            raise BackendExecutionError("v2ex", "V2EX API (public)", url, 1, str(e))

    def execute_v2ex_operation(
        self, operation: str, value: str = "", timeout: float = DEFAULT_TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """Execute public latest/topic/replies operations with a bounded response."""
        operation = operation.lower()
        if operation == "latest":
            url = "https://www.v2ex.com/api/topics/latest.json"
        else:
            clean_value = (value or "").strip()
            if re.fullmatch(r"\d+", clean_value):
                topic_id = clean_value
            else:
                parsed_path = urllib.parse.urlparse(clean_value).path
                match = re.search(r"/t/(\d+)(?:/|$)", parsed_path)
                topic_id = match.group(1) if match else ""
            if not topic_id:
                raise NativeReachError(f"v2ex.{operation} requires a numeric topic id or URL")
            endpoint = "topics/show" if operation == "topic" else "replies/show"
            parameter = "id" if operation == "topic" else "topic_id"
            url = f"https://www.v2ex.com/api/{endpoint}.json?{parameter}={topic_id}"
        started = time.perf_counter()
        try:
            response = fetch_public_http(
                url, headers={"User-Agent": _USER_AGENT}, timeout=timeout,
                max_bytes=MAX_OUTPUT_BYTES,
            )
            data = json.loads(decode_bounded_http_body(response).decode("utf-8"))
            latency_ms = int((time.perf_counter() - started) * 1000)
            transport = self._bounded_http_transport(response)
            items = data if isinstance(data, list) else [data]
            return {
                "platform": "v2ex",
                "backend": "V2EX API (public)",
                "operation": f"v2ex.{operation}",
                "status": "SUCCESS" if items else "EMPTY",
                "items": items,
                "count": len(items),
                "latency_ms": latency_ms,
                "transport": transport,
            }
        except ProviderHTTPError:
            raise
        except Exception as error:
            raise BackendExecutionError("v2ex", "V2EX API (public)", url, 1, str(error))

    # ── 5. Bilibili (Public Search API) ───────────────────────────────────

    def execute_bilibili_search(self, query: str, limit: int = 5, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Search Bilibili using public search web interface API."""
        encoded_q = urllib.parse.quote(query.strip())
        url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={encoded_q}"
        t0 = time.perf_counter()
        try:
            response = fetch_public_http(url, headers={"User-Agent": _USER_AGENT, "Referer": "https://www.bilibili.com/"},
                                         timeout=min(timeout, 5.0), max_bytes=1_000_000)
            raw = json.loads(decode_bounded_http_body(response).decode("utf-8"))
            latency_ms = int((time.perf_counter() - t0) * 1000)
            items = []
            data_obj = raw.get("data", {})
            for result_group in data_obj.get("result", []):
                if result_group.get("result_type") == "video":
                    items.extend(result_group.get("data", [])[:limit])
            return {"platform": "bilibili", "backend": "B站搜索 API", "operation": "bilibili.search",
                    "status": "SUCCESS", "items": items, "count": len(items), "latency_ms": latency_ms,
                    "transport": self._bounded_http_transport(response)}
        except ProviderHTTPError:
            raise
        except Exception as e:
            raise BackendExecutionError("bilibili", "B站搜索 API", url, 1, str(e))

    # ── 6. RSS / Wire Feeds ────────────────────────────────────────────────

    def execute_rss_read(self, url: str, limit: int = 10, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Parse RSS/Atom feed using feedparser."""
        import feedparser
        clean_url = url.strip()
        safe, reason = is_safe_url(clean_url)
        if not safe:
            raise SecurityPolicyViolation(f"RSS feed URL failed SSRF check: {clean_url} ({reason})")

        t0 = time.perf_counter()
        try:
            response = fetch_public_http(
                clean_url, headers={"User-Agent": _USER_AGENT}, timeout=timeout,
                max_bytes=MAX_OUTPUT_BYTES,
            )
            raw_body = decode_bounded_http_body(response)
            transport = self._bounded_http_transport(response)
            feed = feedparser.parse(raw_body)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport["network_latency_ms"] = latency_ms
            entries = []
            for e in feed.entries[:limit]:
                feed_content = next(
                    (part.get("value", "") for part in e.get("content", [])
                     if part.get("value")), "",
                )
                entries.append({
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "published": e.get("published", "") or e.get("created", ""),
                    "updated": e.get("updated", ""),
                    "author": e.get("author", ""),
                    "guid": e.get("id", ""),
                    "categories": [tag.get("term", "") for tag in e.get("tags", [])][:20],
                    "enclosures": [
                        {"href": enclosure.get("href", ""), "type": enclosure.get("type", "")}
                        for enclosure in e.get("enclosures", [])[:10]
                    ],
                    "summary": e.get("summary", "")[:4000],
                    "feed_content": feed_content[:8000],
                    "feed_title": feed.feed.get("title", ""),
                    "feed_publisher": feed.feed.get("publisher", "") or feed.feed.get("author", ""),
                })
            return {
                "platform": "rss",
                "backend": "feedparser",
                "operation": "rss.read",
                "status": "SUCCESS",
                "items": entries,
                "count": len(entries),
                "latency_ms": latency_ms,
                "transport": transport,
            }
        except ProviderHTTPError:
            raise
        except Exception as e:
            raise BackendExecutionError("rss", "feedparser", clean_url, 1, str(e))

    @staticmethod
    def _http_transport(response: Any, endpoint: str, body: bytes, latency_ms: int) -> Dict[str, Any]:
        """Return only transport facts observed at the HTTP boundary."""
        return {
            "endpoint": getattr(response, "url", endpoint),
            "requested_endpoint": endpoint,
            "redirect_chain": [endpoint, getattr(response, "url", endpoint)]
            if getattr(response, "url", endpoint) != endpoint else [endpoint],
            "network_observed_this_attempt": True,
            "http_status": getattr(response, "status", None),
            "content_type": response.headers.get("Content-Type") if getattr(response, "headers", None) else None,
            "raw_body_bytes": len(body),
            "raw_body_sha256": hashlib.sha256(body).hexdigest(),
            "network_latency_ms": latency_ms,
            "cache_status": "UNKNOWN",
            "protocol": "http",
        }

    @staticmethod
    def _bounded_http_transport(response: BoundedHTTPResponse) -> Dict[str, Any]:
        """Translate shared HTTP observations into the existing evidence contract."""
        return {
            "endpoint": response.endpoint,
            "requested_endpoint": response.redirect_chain[0] if response.redirect_chain else response.endpoint,
            "redirect_chain": list(response.redirect_chain),
            "network_observed_this_attempt": True,
            "http_status": response.status_code,
            "content_type": response.content_type,
            "raw_body_bytes": len(response.body),
            "raw_body_sha256": hashlib.sha256(response.body).hexdigest(),
            "network_latency_ms": response.latency_ms,
            "cache_status": "UNKNOWN",
            "protocol": "http",
            "attempts": response.attempts,
        }

    # ── 7. YouTube Comments ────────────────────────────────────────────────

    def execute_youtube_comments(self, url: str, limit: int = 5, timeout: float = 15.0) -> Dict[str, Any]:
        """Extract top video comments using yt-dlp."""
        ytdlp_bin = shutil.which("yt-dlp")
        if not ytdlp_bin:
            raise BackendExecutionError("youtube", "yt-dlp", "yt-dlp comments", 127, "yt-dlp not found")

        t0 = time.perf_counter()
        bounded_limit = min(max(limit, 1), 10)
        cmd = [
            ytdlp_bin,
            "--write-comments",
            "--extractor-args", f"youtube:max_comments={bounded_limit},{bounded_limit},0,0",
            "--dump-json",
            "--skip-download",
            "--no-warnings",
            url.strip()
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            comments = []
            if res.returncode == 0 and res.stdout.strip():
                try:
                    data = json.loads(res.stdout)
                    comments = data.get("comments", [])[:bounded_limit]
                except Exception:
                    for line in res.stdout.splitlines():
                        line = line.strip()
                        if line.startswith("{"):
                            try:
                                d = json.loads(line)
                                if "comments" in d:
                                    comments = d.get("comments", [])[:bounded_limit]
                                    break
                            except Exception:
                                pass

            return {
                "platform": "youtube",
                "backend": "yt-dlp",
                "operation": "youtube.comments",
                "status": "SUCCESS" if comments else "EMPTY",
                "items": comments,
                "count": len(comments),
                "latency_ms": latency_ms,
                "transport": {
                    "endpoint": url.strip(),
                    "network_observed_this_attempt": True,
                    "http_status": None,
                    "content_type": "application/json",
                    "raw_body_bytes": len(res.stdout.encode("utf-8", errors="replace")),
                    "network_latency_ms": latency_ms,
                    "cache_status": "UNKNOWN",
                    "protocol": "external_tool",
                },
            }
        except Exception as e:
            raise BackendExecutionError("youtube", "yt-dlp", " ".join(cmd), 1, str(e))

    # ── 8. Xueqiu Visitor API (Panniantong issue #664 anonymous /hq session) ──

    def init_xueqiu_client(self, timeout: float = 10.0):
        """Establish an anonymous visitor session with cookies initialized via /hq."""
        import httpx
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://xueqiu.com/",
        }
        client = httpx.Client(headers=headers, follow_redirects=True, timeout=timeout)
        client.get("https://xueqiu.com/hq")
        return client

    def execute_xueqiu(self, query: str, limit: int = 5, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Acquire stock quotes, search results, or public discussions from Xueqiu
        using anonymous visitor session initialization via /hq (Panniantong issue #664).
        """
        import httpx
        import re
        t0 = time.perf_counter()
        clean_q = query.strip()
        items = []
        try:
            client = self.init_xueqiu_client(timeout=timeout)

            is_symbol = bool(re.match(r"^(?:[A-Za-z]{1,5}|[A-Za-z]{2}\d{6})$", clean_q))
            if is_symbol:
                r_q = client.get(f"https://stock.xueqiu.com/v5/stock/quote.json?symbol={clean_q.upper()}")
                if r_q.status_code == 200:
                    data = r_q.json().get("data", {})
                    quote = data.get("quote")
                    if quote:
                        items.append({
                            "type": "quote",
                            "symbol": quote.get("symbol"),
                            "name": quote.get("name"),
                            "current": quote.get("current"),
                            "percent": quote.get("percent"),
                            "high": quote.get("high"),
                            "low": quote.get("low"),
                            "volume": quote.get("volume"),
                            "url": f"https://xueqiu.com/S/{quote.get('symbol')}",
                        })

            if not items:
                r_s = client.get(f"https://xueqiu.com/stock/search.json?code={urllib.parse.quote(clean_q)}")
                if r_s.status_code == 200:
                    stocks = r_s.json().get("stocks", [])
                    for s in stocks[:limit]:
                        items.append({
                            "type": "stock_search",
                            "symbol": s.get("code"),
                            "name": s.get("name"),
                            "url": f"https://xueqiu.com/S/{s.get('code')}",
                        })

            if not items:
                r_d = client.get("https://xueqiu.com/v4/statuses/public_timeline_by_category.json?since_id=-1&max_id=-1&count=5&category=-1")
                if r_d.status_code == 200:
                    raw_posts = r_d.json().get("list", [])
                    for p in raw_posts[:limit]:
                        try:
                            p_data = json.loads(p.get("data", "{}"))
                            items.append({
                                "type": "discussion",
                                "title": p_data.get("title") or (p_data.get("text", "")[:60]),
                                "text": p_data.get("text", ""),
                                "author": p_data.get("user", {}).get("screen_name", "雪球用户"),
                                "url": f"https://xueqiu.com/{p_data.get('user', {}).get('id')}/{p_data.get('id')}",
                            })
                        except Exception:
                            pass

            latency_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "platform": "xueqiu",
                "backend": "xueqiu-visitor-api",
                "operation": "xueqiu.read",
                "status": "SUCCESS" if items else "EMPTY",
                "items": items,
                "count": len(items),
                "latency_ms": latency_ms,
            }
        except Exception as e:
            raise BackendExecutionError("xueqiu", "xueqiu-visitor-api", "xueqiu /hq handshake", 1, str(e))

    # ── 9. Xiaoyuzhou / Open Podcast RSS Syndication ───────────────────────

    def execute_xiaoyuzhou_podcast(
        self,
        query: str,
        limit: int = 5,
        timeout: float = 10.0,
        operation: str = "podcast",
    ) -> Dict[str, Any]:
        """Read a public Xiaoyuzhou podcast page and its embedded public data.

        Text search is deliberately not implemented here: Apple/iTunes podcast
        results do not prove that content came from Xiaoyuzhou.  Callers may use
        the separately disclosed web-index discovery fallback, then pass an
        explicit ``xiaoyuzhoufm.com/podcast/<pid>`` URL to this direct reader.
        """
        from bs4 import BeautifulSoup

        started = time.perf_counter()
        clean_query = query.strip()
        parsed = urllib.parse.urlparse(clean_query if "://" in clean_query else "")
        match = re.search(r"/podcast/([a-f0-9]{24})(?:/|$)", parsed.path, re.IGNORECASE)
        if not match and re.fullmatch(r"[a-f0-9]{24}", clean_query, re.IGNORECASE):
            podcast_id = clean_query.lower()
        elif match and (parsed.hostname or "").lower().rstrip(".") in {
            "xiaoyuzhoufm.com", "www.xiaoyuzhoufm.com",
        }:
            podcast_id = match.group(1).lower()
        else:
            raise NativeReachError(
                "Xiaoyuzhou direct operations require an official public podcast URL or 24-character podcast id"
            )

        page_url = f"https://www.xiaoyuzhoufm.com/podcast/{podcast_id}"
        try:
            response = fetch_public_http(
                page_url, headers={"User-Agent": _USER_AGENT}, timeout=timeout,
                max_bytes=MAX_OUTPUT_BYTES,
            )
            soup = BeautifulSoup(decode_bounded_http_body(response), "html.parser")
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data is None or not next_data.string:
                raise ValueError("public page did not expose structured podcast data")
            document = json.loads(next_data.string)
            podcast = document.get("props", {}).get("pageProps", {}).get("podcast") or {}
            if str(podcast.get("pid", "")).lower() != podcast_id:
                raise ValueError("public page podcast identity did not match requested id")

            title = str(podcast.get("title") or "Xiaoyuzhou podcast")
            if operation == "podcast":
                items = [{
                    "item_type": "podcast",
                    "podcast": title,
                    "title": title,
                    "summary": str(podcast.get("description") or "")[:4000],
                    "published": str(podcast.get("latestEpisodePubDate") or ""),
                    "link": page_url,
                    "audio_url": None,
                    "author": str(podcast.get("author") or ""),
                    "episode_count": podcast.get("episodeCount"),
                    "subscription_count": podcast.get("subscriptionCount"),
                    "source_contract": "xiaoyuzhou_public_next_data",
                }]
            else:
                items = []
                for episode in (podcast.get("episodes") or [])[: min(max(limit, 1), 20)]:
                    episode_id = str(episode.get("eid") or "")
                    enclosure = episode.get("enclosure") or {}
                    items.append({
                        "item_type": "episode",
                        "podcast": title,
                        "title": str(episode.get("title") or "Xiaoyuzhou episode"),
                        "summary": str(episode.get("description") or "")[:4000],
                        "published": str(episode.get("pubDate") or ""),
                        "link": f"https://www.xiaoyuzhoufm.com/episode/{episode_id}" if episode_id else page_url,
                        "audio_url": enclosure.get("url") if isinstance(enclosure, dict) else None,
                        "duration": episode.get("duration"),
                        "play_count": episode.get("playCount"),
                        "comment_count": episode.get("commentCount"),
                        "transcript_available": bool(episode.get("transcript")),
                        "source_contract": "xiaoyuzhou_public_next_data",
                    })

            latency_ms = int((time.perf_counter() - started) * 1000)
            transport = self._bounded_http_transport(response)
            transport["network_latency_ms"] = latency_ms
            return {
                "platform": "xiaoyuzhou",
                "backend": "xiaoyuzhou-public-web",
                "operation": f"xiaoyuzhou.{operation}",
                "status": "SUCCESS" if items else "EMPTY",
                "items": items,
                "count": len(items),
                "latency_ms": latency_ms,
                "transport": transport,
            }
        except ProviderHTTPError:
            raise
        except Exception as error:
            raise BackendExecutionError(
                "xiaoyuzhou", "xiaoyuzhou-public-web", page_url, 1, str(error)
            )

    # ── 10. LinkedIn Guest Job Listings ────────────────────────────────────

    def execute_linkedin_jobs(self, query: str, limit: int = 5, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Fetch public job postings from LinkedIn's guest job-listing API (no login required).
        """
        import httpx
        import bs4
        t0 = time.perf_counter()
        clean_q = query.strip()
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={urllib.parse.quote(clean_q)}&start=0"
        try:
            client = httpx.Client(headers=headers, follow_redirects=True, timeout=timeout)
            r = client.get(url)
            items = []
            if r.status_code == 200:
                soup = bs4.BeautifulSoup(r.text, "html.parser")
                jobs = soup.find_all("li")
                for j in jobs[:limit]:
                    title_elem = j.find("h3", class_="base-search-card__title")
                    company_elem = j.find("h4", class_="base-search-card__subtitle")
                    location_elem = j.find("span", class_="job-search-card__location")
                    link_elem = j.find("a", class_="base-card__full-link")
                    title = title_elem.text.strip() if title_elem else "Job Posting"
                    company = company_elem.text.strip() if company_elem else "Unknown Company"
                    location = location_elem.text.strip() if location_elem else "Unknown Location"
                    job_url = link_elem.get("href") if link_elem else "https://www.linkedin.com/jobs"
                    items.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": job_url,
                    })

            latency_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "platform": "linkedin",
                "backend": "linkedin-guest-jobs-api",
                "operation": "linkedin.jobs",
                "status": "SUCCESS" if items else "EMPTY",
                "items": items,
                "count": len(items),
                "latency_ms": latency_ms,
                "transport": {
                    "endpoint": url,
                    "network_observed_this_attempt": True,
                    "http_status": r.status_code,
                    "content_type": r.headers.get("content-type"),
                    "raw_body_bytes": len(r.content),
                    "network_latency_ms": latency_ms,
                    "cache_status": "UNKNOWN",
                },
            }
        except Exception as e:
            raise BackendExecutionError("linkedin", "linkedin-guest-jobs-api", url, 1, str(e))

    # ── 11. Authenticated Social Channels Guard ────────────────────────────

    def guard_authenticated_channel(self, platform: str, backend: str, env_var: str = "") -> None:
        """
        Check if an authenticated channel has credentials/session.
        If in CLOUD_HEADLESS or credentials missing, raises AuthRequiredError.
        """
        from backend.services.agent_reach.native.channel_capabilities import CAPABILITY_MATRIX
        cap = CAPABILITY_MATRIX.get(platform)
        if self.profile == RuntimeProfile.CLOUD_HEADLESS:
            raise AuthRequiredError(
                platform=platform,
                backend=backend,
                hint="Platform requires browser session or local desktop profile (CLOUD_HEADLESS active)"
            )
        if env_var:
            if not os.getenv(env_var):
                raise AuthRequiredError(
                    platform=platform,
                    backend=backend,
                    hint=f"Required credential/session '{env_var}' not found in environment"
                )
        elif cap and cap.auth_mode not in ("none", "optional"):
            raise AuthRequiredError(
                platform=platform,
                backend=backend,
                hint=f"Platform requires active session or authentication (auth_mode='{cap.auth_mode}')"
            )


# Global singleton instance
native_executor = NativeExecutor()
