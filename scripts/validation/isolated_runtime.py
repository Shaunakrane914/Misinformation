"""Shared subprocess isolation for offline release validation (not a live audit)."""

import json
import ipaddress
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading

from dotenv import dotenv_values, find_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_PREFIX = "AEGIS_VALIDATION_RESULT="
CREDENTIAL_PREFIXES = (
    "GEMINI_API_KEY", "GEMINI_KEY_", "SUPABASE_", "APIFY_", "TWILIO_",
    "GITHUB_TOKEN", "GH_TOKEN", "REDDIT_", "TWITTER_", "X_AUTH_",
    "YOUTUBE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "YF_API_KEY",
    "ADMIN_API_TOKEN", "BRAVE_API_KEY", "EXA_API_KEY", "JINA_API_KEY",
    "GROQ_API_KEY", "LINKEDIN_COOKIE", "XUEQIU_COOKIE", "INSTAGRAM_COOKIE",
    "FACEBOOK_COOKIE", "XIAOHONGSHU_COOKIE", "FIRECRAWL_API_KEY", "HUGINN_WEBHOOK_SECRET",
)


def isolated_environment(storage: Path) -> dict:
    """Explicit empty secrets prevent a repository .env from restoring them."""
    environment = dict(os.environ)
    # Match load_dotenv's parent search as well as the explicit local file.
    # The installed dotenv version may not honor PYTHON_DOTENV_DISABLED.
    configured = set(environment) | set(dotenv_values(REPO_ROOT / ".env")) | set(dotenv_values(find_dotenv()))
    for name in configured | set(CREDENTIAL_PREFIXES):
        if name.startswith(CREDENTIAL_PREFIXES):
            environment[name] = ""
    environment.update({
        # Defense in depth for dotenv versions that support this switch; the
        # explicit blanking above also protects older installed versions.
        "PYTHON_DOTENV_DISABLED": "1",
        "ENVIRONMENT": "test", "AEGIS_ENV": "test", "AEGIS_MOCK_LLM": "true",
        "RSS_INGESTION_ENABLED": "false", "AGENT_REACH_ENABLED": "false",
        "HUGINN_ENABLED": "false", "HUGINN_DB_PATH": str(storage / "huginn.db"),
        "SQLITE_DB_PATH": str(storage / "aegis.db"),
        "AEGIS_SQLITE_PATH": str(storage / "aegis.db"),
        "AEGIS_DOSSIER_DIR": str(storage / "dossiers"),
        "PYTHONIOENCODING": "utf-8",
    })
    return environment


def block_live_network() -> None:
    """Offline validators are allowed ASGI requests, never real TCP/UDP I/O."""
    internal_pair = threading.local()
    original_connect = socket.socket.connect
    original_socketpair = socket.socketpair
    original_getaddrinfo = socket.getaddrinfo
    original_run = subprocess.run

    def offline_getaddrinfo(host, *args, **kwargs):
        name = host.decode() if isinstance(host, bytes) else str(host)
        if name.lower() == "localhost":
            return original_getaddrinfo("127.0.0.1", *args, **kwargs)
        try:
            ipaddress.ip_address(name)
        except ValueError:
            raise socket.gaierror("Offline validation forbids external DNS")
        return original_getaddrinfo(host, *args, **kwargs)

    def blocked(*args, **kwargs):
        if getattr(internal_pair, "active", False):
            return original_connect(*args, **kwargs)
        raise OSError("Offline validation forbids live network")

    def local_socketpair(*args, **kwargs):
        internal_pair.active = True
        try:
            return original_socketpair(*args, **kwargs)
        finally:
            internal_pair.active = False

    def offline_subprocess_run(command, *args, **kwargs):
        executable = command[0] if isinstance(command, (list, tuple)) else str(command).split()[0]
        if Path(str(executable)).stem.lower() in {
            "agent-reach", "yt-dlp", "bird", "curl", "wget", "gallery-dl",
            "gh", "opencli", "twitter-cli", "twitter",
        }:
            raise OSError("Offline validation forbids provider network subprocesses")
        return original_run(command, *args, **kwargs)

    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.socket.sendto = blocked
    socket.socketpair = local_socketpair
    socket.getaddrinfo = offline_getaddrinfo
    subprocess.run = offline_subprocess_run


def run_worker(script: Path, phase: str, storage: Path, *extra: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(script), "--worker", phase, *extra],
        cwd=REPO_ROOT, env=isolated_environment(storage),
        text=True, encoding="utf-8", capture_output=True, timeout=180,
    )
    if completed.returncode:
        raise RuntimeError(f"Validation worker {phase} failed: {completed.stderr[-4000:]}")
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(RESULT_PREFIX):
            return json.loads(line[len(RESULT_PREFIX):])
    raise RuntimeError(f"Validation worker {phase} returned no structured result")


def write_report_exclusively(path: Path, report: dict) -> None:
    """An explicit output can create a report but cannot overwrite audit history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
