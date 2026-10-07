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
        safe, reason = is_safe_url(clean_url)
        if not safe:
            raise SecurityPolicyViolation(f"URL failed SSRF validation: {clean_url} ({reason})")

        t0 = time.perf_counter()
        active_backend = "scrapling_http"
        markdown_text = ""
        status_code = 200

        # Primary: Scrapling HTTP
        try:
            from scrapling import Fetcher
            headers = {
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            resp = Fetcher.get(clean_url, headers=headers, timeout=timeout)
            status_code = getattr(resp, "status", 200)
            raw_text = resp.text if hasattr(resp, "text") else str(resp)

            # Clean HTML to readable text/markdown
            import re
            cleaned = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", raw_text, flags=re.IGNORECASE)
            cleaned = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"<[^>]+>", " ", cleaned)
            markdown_text = re.sub(r"\s+", " ", cleaned).strip()

        except Exception as e_scrapling:
            logger.debug(f"[NativeExecutor] Scrapling read error for {clean_url}: {e_scrapling}")
            status_code = 500

        # Secondary: Playwright Rescue (only if lightweight HTTP returned empty/blocked)
        if len(markdown_text) < 250 or status_code in (403, 503):
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
                    if len(p_text) > len(markdown_text):
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
            "--json", "fullName,description,url,stargazerCount,updatedAt"
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
            }
        except subprocess.TimeoutExpired:
            raise BackendExecutionError("github", "gh CLI", " ".join(cmd), 124, "Timeout expired")

    def execute_github_read(self, repo: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Read repository metadata and README using gh CLI."""
        gh_bin = shutil.which("gh")
        if not gh_bin:
            raise BackendExecutionError("github", "gh CLI", "gh repo view", 127, "gh CLI not found")

        cmd = [
            gh_bin, "repo", "view", repo.strip(),
            "--json", "name,description,readme,url,stargazerCount,latestRelease"
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

            data = json.loads(res.stdout) if res.stdout.strip() else {}
            return {
                "platform": "github",
                "backend": "gh CLI",
                "operation": "github.read",
                "status": "SUCCESS",
                "data": data,
                "latency_ms": latency_ms,
            }
        except Exception as e:
            raise BackendExecutionError("github", "gh CLI", " ".join(cmd), 1, str(e))

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
                data = json.loads(resp.read(MAX_OUTPUT_BYTES).decode("utf-8"))
                latency_ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "platform": "v2ex",
                    "backend": "V2EX API (public)",
                    "operation": "v2ex.hot",
                    "status": "SUCCESS",
                    "items": data,
                    "count": len(data),
                    "latency_ms": latency_ms,
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
                data = json.loads(resp.read(MAX_OUTPUT_BYTES).decode("utf-8"))
                latency_ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "platform": "v2ex",
                    "backend": "V2EX API (public)",
                    "operation": "v2ex.search",
                    "status": "SUCCESS",
                    "items": data,
                    "count": len(data),
                    "latency_ms": latency_ms,
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
                raw = json.loads(resp.read(MAX_OUTPUT_BYTES).decode("utf-8"))
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
                }
        except Exception as e:
            raise BackendExecutionError("bilibili", "B站搜索 API", url, 1, str(e))

    # ── 6. RSS / Wire Feeds ────────────────────────────────────────────────

    def execute_rss_read(self, url: str, limit: int = 10, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Parse RSS/Atom feed using feedparser."""
        import feedparser
        clean_url = url.strip()
        if not is_safe_url(clean_url):
            raise SecurityPolicyViolation(f"RSS feed URL failed SSRF check: {clean_url}")

        t0 = time.perf_counter()
        try:
            feed = feedparser.parse(clean_url)
            latency_ms = int((time.perf_counter() - t0) * 1000)
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
            }
        except Exception as e:
            raise BackendExecutionError("rss", "feedparser", clean_url, 1, str(e))

    # ── 7. Authenticated Social Channels Guard ─────────────────────────────

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
