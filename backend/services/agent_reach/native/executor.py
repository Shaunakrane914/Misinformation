"""
Aegis Protocol — Native Agent Reach Secure Allowlisted Executor
===============================================================
Executes upstream platform tools (gh CLI, yt-dlp, Jina Reader, V2EX API,
Bilibili API, feedparser, OpenCLI, twitter-cli) through strict, parameter-checked
command allowlists. Arbitrary shell text execution is strictly prohibited.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

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
MAX_OUTPUT_BYTES = 5 * 1024 * 1024  # 5 MB max buffer
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 AegisAgentReach/3.0"


class NativeExecutor:
    """
    Allowlisted command dispatcher executing tools according to upstream Agent Reach
    skill specifications. Operates in parameter array mode (never shell=True).
    """

    def __init__(self):
        self.profile = get_runtime_profile()

    # ── 1. Web Page Reading (Scrapling HTTP Primary -> Playwright Rescue) ──

    def execute_web_read(self, url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """
        Read any public web page following Policy D:
        Primary: Scrapling HTTP / curl_cffi lightweight extraction
        Secondary: Playwright rescue strictly when JS rendering or challenge encountered
        """
        clean_url = url.strip()
        # Resolve Google News redirect URLs to original publisher URLs if needed
        if "news.google.com" in clean_url and ("/articles/" in clean_url or "/read/" in clean_url):
            try:
                from googlenewsdecoder import gnewsdecoder
                dec_res = gnewsdecoder(clean_url)
                if dec_res.get("success") and dec_res.get("decoded_url"):
                    clean_url = dec_res["decoded_url"]
            except Exception as e_dec:
                logger.debug(f"[NativeExecutor] Google News URL decode notice for {clean_url}: {e_dec}")

        safe, reason = is_safe_url(clean_url)
        if not safe:
            raise SecurityPolicyViolation(f"URL failed SSRF validation: {clean_url} ({reason})")

        t0 = time.perf_counter()
        active_backend = "scrapling_http"
        markdown_text = ""
        status_code = None
        content_type = None
        raw_body_bytes = None
        observed_endpoint = clean_url

        # Primary: Scrapling HTTP
        try:
            from scrapling import Fetcher
            headers = {
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            resp = Fetcher.get(clean_url, headers=headers, timeout=timeout)
            status_code = getattr(resp, "status", None)
            if hasattr(resp, "body") and isinstance(resp.body, bytes):
                raw_body_bytes = len(resp.body)
                raw_text = resp.body.decode("utf-8", errors="replace")
            elif hasattr(resp, "html_content"):
                raw_text = str(resp.html_content)
                raw_body_bytes = len(raw_text.encode("utf-8", errors="replace"))
            else:
                raw_text = resp.text if hasattr(resp, "text") else str(resp)
                raw_body_bytes = len(raw_text.encode("utf-8", errors="replace"))
            response_headers = getattr(resp, "headers", None)
            if response_headers:
                content_type = response_headers.get("content-type") or response_headers.get("Content-Type")

            # Clean HTML to readable text/markdown
            import re
            cleaned = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", raw_text, flags=re.IGNORECASE)
            cleaned = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"<[^>]+>", " ", cleaned)
            markdown_text = re.sub(r"\s+", " ", cleaned).strip()

        except Exception as e_scrapling:
            logger.debug(f"[NativeExecutor] Scrapling read error for {clean_url}: {e_scrapling}")

        # Fast HTTP fallback if scrapling returned insufficient text
        if len(markdown_text) < 100:
            try:
                import urllib.request
                import re
                req = urllib.request.Request(
                    clean_url,
                    headers={
                        "User-Agent": _USER_AGENT,
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                    }
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw_bytes = resp.read(MAX_OUTPUT_BYTES)
                    raw_text = raw_bytes.decode("utf-8", errors="replace")
                    cleaned = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", raw_text, flags=re.IGNORECASE)
                    cleaned = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
                    u_text = re.sub(r"\s+", " ", cleaned).strip()
                    if len(u_text) > len(markdown_text):
                        markdown_text = u_text
                        active_backend = "native_http_reader"
                        status_code = getattr(resp, "status", None)
                        content_type = resp.headers.get("Content-Type")
                        raw_body_bytes = len(raw_bytes)
                        observed_endpoint = getattr(resp, "url", clean_url)
            except Exception as e_http:
                logger.debug(f"[NativeExecutor] Fast HTTP fallback notice for {clean_url}: {e_http}")

        CHALLENGE_INDICATORS = (
            "cloudflare", "turnstile", "human security", "just a moment",
            "verify you are human", "attention required", "security check",
            "access denied", "403 forbidden"
        )
        is_challenge = any(ind in markdown_text.lower() for ind in CHALLENGE_INDICATORS)
        if is_challenge:
            markdown_text = ""

        # Secondary: Playwright Rescue (only if lightweight HTTP returned empty/blocked/challenge)
        if len(markdown_text) < 100 or status_code in (403, 503) or is_challenge:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_default_timeout(int(timeout * 1000))
                    page.goto(clean_url, wait_until="domcontentloaded")
                    html_content = page.content()
                    browser.close()
                    import re
                    c_clean = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html_content, flags=re.IGNORECASE)
                    c_clean = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", c_clean, flags=re.IGNORECASE)
                    c_clean = re.sub(r"<[^>]+>", " ", c_clean)
                    p_text = re.sub(r"\s+", " ", c_clean).strip()
                    if not any(ind in p_text.lower() for ind in CHALLENGE_INDICATORS) and len(p_text) > 100:
                        markdown_text = p_text
                        active_backend = "playwright_rescue"
            except Exception as e_pw:
                logger.debug(f"[NativeExecutor] Playwright rescue notice for {clean_url}: {e_pw}")

        # If both failed, try Jina Reader as emergency fallback
        if len(markdown_text) < 100:
            try:
                jina_url = f"https://r.jina.ai/{clean_url}"
                req = urllib.request.Request(
                    jina_url,
                    headers={"User-Agent": _USER_AGENT, "Accept": "text/plain", "X-No-Cache": "true"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw_bytes = resp.read(MAX_OUTPUT_BYTES)
                    j_text = raw_bytes.decode("utf-8", errors="replace").strip()
                    if len(j_text) > len(markdown_text):
                        markdown_text = j_text
                        active_backend = "jina_reader_fallback"
                        status_code = getattr(resp, "status", None)
                        content_type = resp.headers.get("Content-Type")
                        raw_body_bytes = len(raw_bytes)
                        observed_endpoint = getattr(resp, "url", jina_url)
            except Exception as e_jina:
                logger.debug(f"[NativeExecutor] Emergency Jina fallback error: {e_jina}")

        latency_ms = int((time.perf_counter() - t0) * 1000)
        if not markdown_text:
            raise BackendExecutionError("web", active_backend, clean_url, 1, "Failed to retrieve content via Scrapling/Playwright")

        return {
            "platform": "web",
            "backend": active_backend,
            "operation": "web.read",
            "status": "SUCCESS",
            "url": clean_url,
            "content": markdown_text,
            "char_count": len(markdown_text),
            "latency_ms": latency_ms,
            "transport": {
                "endpoint": observed_endpoint,
                "network_observed_this_attempt": True,
                "http_status": status_code,
                "content_type": content_type,
                "raw_body_bytes": raw_body_bytes,
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
                for fname in os.listdir(tmp_dir):
                    if fname.endswith((".vtt", ".srt")):
                        fpath = os.path.join(tmp_dir, fname)
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            transcript_text = f.read()
                        break

                if not transcript_text:
                    return {
                        "platform": "youtube",
                        "backend": "yt-dlp",
                        "operation": "youtube.transcript",
                        "status": "EMPTY",
                        "content": "",
                        "latency_ms": latency_ms,
                    }

                return {
                    "platform": "youtube",
                    "backend": "yt-dlp",
                    "operation": "youtube.transcript",
                    "status": "SUCCESS",
                    "content": transcript_text,
                    "char_count": len(transcript_text),
                    "latency_ms": latency_ms,
                }
            except Exception as e:
                raise BackendExecutionError("youtube", "yt-dlp", " ".join(cmd), 1, str(e))

    # ── 4. V2EX (Public HTTPS JSON API) ───────────────────────────────────

    def execute_v2ex_hot(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Fetch hot topics from V2EX public JSON API."""
        url = "https://www.v2ex.com/api/topics/hot.json"
        t0 = time.perf_counter()
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_body = resp.read(MAX_OUTPUT_BYTES)
                data = json.loads(raw_body.decode("utf-8"))
                latency_ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "platform": "v2ex",
                    "backend": "V2EX API (public)",
                    "operation": "v2ex.hot",
                    "status": "SUCCESS",
                    "items": data,
                    "count": len(data),
                    "latency_ms": latency_ms,
                    "transport": self._http_transport(resp, url, raw_body, latency_ms),
                }
        except Exception as e:
            raise BackendExecutionError("v2ex", "V2EX API (public)", url, 1, str(e))

    def execute_v2ex_search(self, node: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Fetch topics for a specific node from V2EX public API."""
        url = f"https://www.v2ex.com/api/topics/show.json?node_name={urllib.parse.quote(node)}"
        t0 = time.perf_counter()
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_body = resp.read(MAX_OUTPUT_BYTES)
                data = json.loads(raw_body.decode("utf-8"))
                latency_ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "platform": "v2ex",
                    "backend": "V2EX API (public)",
                    "operation": "v2ex.search",
                    "status": "SUCCESS",
                    "items": data,
                    "count": len(data),
                    "latency_ms": latency_ms,
                    "transport": self._http_transport(resp, url, raw_body, latency_ms),
                }
        except Exception as e:
            raise BackendExecutionError("v2ex", "V2EX API (public)", url, 1, str(e))

    # ── 5. Bilibili (Public Search API) ───────────────────────────────────

    def execute_bilibili_search(self, query: str, limit: int = 5, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Search Bilibili using public search web interface API."""
        encoded_q = urllib.parse.quote(query.strip())
        url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={encoded_q}"
        t0 = time.perf_counter()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Referer": "https://www.bilibili.com/",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_body = resp.read(MAX_OUTPUT_BYTES)
                raw = json.loads(raw_body.decode("utf-8"))
                latency_ms = int((time.perf_counter() - t0) * 1000)
                items = []
                data_obj = raw.get("data", {})
                for result_group in data_obj.get("result", []):
                    if result_group.get("result_type") == "video":
                        items.extend(result_group.get("data", [])[:limit])

                return {
                    "platform": "bilibili",
                    "backend": "B站搜索 API",
                    "operation": "bilibili.search",
                    "status": "SUCCESS",
                    "items": items,
                    "count": len(items),
                    "latency_ms": latency_ms,
                    "transport": self._http_transport(resp, url, raw_body, latency_ms),
                }
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
            req = urllib.request.Request(clean_url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_body = resp.read(MAX_OUTPUT_BYTES)
                transport = self._http_transport(resp, clean_url, raw_body, 0)
            feed = feedparser.parse(raw_body)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport["network_latency_ms"] = latency_ms
            entries = []
            for e in feed.entries[:limit]:
                entries.append({
                    "title": getattr(e, "title", ""),
                    "link": getattr(e, "link", ""),
                    "published": getattr(e, "published", ""),
                    "summary": getattr(e, "summary", "")[:500],
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
        except Exception as e:
            raise BackendExecutionError("rss", "feedparser", clean_url, 1, str(e))

    @staticmethod
    def _http_transport(response: Any, endpoint: str, body: bytes, latency_ms: int) -> Dict[str, Any]:
        """Return only transport facts observed at the HTTP boundary."""
        return {
            "endpoint": getattr(response, "url", endpoint),
            "network_observed_this_attempt": True,
            "http_status": getattr(response, "status", None),
            "content_type": response.headers.get("Content-Type") if getattr(response, "headers", None) else None,
            "raw_body_bytes": len(body),
            "network_latency_ms": latency_ms,
            "cache_status": "UNKNOWN",
            "protocol": "http",
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

    def execute_xiaoyuzhou_podcast(self, query: str, limit: int = 5, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Discover public podcast metadata, episodes, and direct audio enclosure URLs
        via iTunes API and RSS syndication (no login / no credential required).
        """
        import httpx
        import feedparser
        import re
        t0 = time.perf_counter()
        clean_q = query.strip()
        client = httpx.Client(headers={"User-Agent": _USER_AGENT}, follow_redirects=True, timeout=timeout)
        items = []
        itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(clean_q)}&entity=podcast&limit=3"
        try:
            r_itunes = client.get(itunes_url)
            feed_urls = []
            if r_itunes.status_code == 200:
                results = r_itunes.json().get("results", [])
                for res in results:
                    f_url = res.get("feedUrl")
                    p_name = res.get("collectionName")
                    if f_url:
                        feed_urls.append((p_name, f_url))

            for pod_name, f_url in feed_urls:
                try:
                    r_rss = client.get(f_url)
                    if r_rss.status_code == 200:
                        feed = feedparser.parse(r_rss.content)
                        for entry in feed.entries[:limit]:
                            enclosures = entry.get("enclosures", [])
                            audio_url = enclosures[0].get("href") if enclosures else None
                            raw_summary = entry.get("summary", "")
                            clean_summary = re.sub(r"<[^>]+>", " ", raw_summary).strip()
                            items.append({
                                "podcast": pod_name,
                                "title": entry.get("title", ""),
                                "published": entry.get("published", ""),
                                "summary": clean_summary[:500],
                                "link": entry.get("link", f_url),
                                "audio_url": audio_url,
                                "has_audio": bool(audio_url),
                            })
                            if len(items) >= limit:
                                break
                except Exception:
                    pass
                if len(items) >= limit:
                    break

            latency_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "platform": "xiaoyuzhou",
                "backend": "podcast-rss-syndication",
                "operation": "xiaoyuzhou.podcast",
                "status": "SUCCESS" if items else "EMPTY",
                "items": items,
                "count": len(items),
                "latency_ms": latency_ms,
            }
        except Exception as e:
            raise BackendExecutionError("xiaoyuzhou", "podcast-rss-syndication", itunes_url, 1, str(e))

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
