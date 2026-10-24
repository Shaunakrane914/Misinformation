"""
Aegis Protocol — Pytest Configuration and Global Fixtures
==========================================================
Provides isolated test clients, in-memory database resets, and mock LLM fixtures.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def deterministic_semantic_predictor():
    """Offline semantic-score double; tests ranking policy, never model quality."""
    import hashlib
    import math
    import re

    def predict(pairs):
        logits = []
        for query, document in pairs:
            query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
            document_tokens = set(re.findall(r"[a-z0-9]+", document.lower()))
            overlap = len(query_tokens & document_tokens)
            coverage = overlap / max(1, len(query_tokens))
            density = overlap / max(1, math.sqrt(len(document_tokens)))
            digest = hashlib.sha256(f"{query}\0{document}".encode("utf-8")).digest()
            stable_variation = ((int.from_bytes(digest[:4], "big") / (2**32 - 1)) * 2.0) - 1.0
            logits.append((5.0 * coverage) + density + (2.5 * stable_variation) - 2.0)
        return logits

    return predict
from fastapi.testclient import TestClient
from dotenv import dotenv_values, find_dotenv

# Isolate storage and credentials BEFORE importing any application singleton.
# Empty values (rather than deletion) prevent load_dotenv from restoring secrets.
_test_storage = tempfile.TemporaryDirectory(prefix="aegis-pytest-")
_test_root = Path(_test_storage.name)
os.environ["AEGIS_MOCK_LLM"] = "true"
os.environ["AEGIS_ENV"] = "test"
os.environ["ENVIRONMENT"] = "test"
os.environ["RSS_INGESTION_ENABLED"] = "false"
os.environ["SQLITE_DB_PATH"] = str(_test_root / "aegis.db")
os.environ["AEGIS_SQLITE_PATH"] = os.environ["SQLITE_DB_PATH"]
os.environ["AEGIS_DOSSIER_DIR"] = str(_test_root / "dossiers")
os.environ["HUGINN_ENABLED"] = "false"
os.environ["HUGINN_DB_PATH"] = str(_test_root / "huginn.db")
_credential_prefixes = (
    "GEMINI_API_KEY", "GEMINI_KEY_", "SUPABASE_", "APIFY_", "TWILIO_",
    "GITHUB_TOKEN", "GH_TOKEN", "REDDIT_", "TWITTER_", "X_AUTH_",
    "YOUTUBE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "YF_API_KEY",
    "ADMIN_API_TOKEN", "BRAVE_API_KEY", "EXA_API_KEY", "JINA_API_KEY",
    "GROQ_API_KEY", "LINKEDIN_COOKIE", "XUEQIU_COOKIE", "INSTAGRAM_COOKIE",
    "FACEBOOK_COOKIE", "XIAOHONGSHU_COOKIE", "FIRECRAWL_API_KEY", "HUGINN_WEBHOOK_SECRET",
)
# python-dotenv's load_dotenv() searches parent directories. A nested Git
# worktree can therefore inherit the outer checkout's .env unless the same
# discovered file is sanitized before importing application singletons.
_configured_names = set(os.environ) | set(dotenv_values(find_dotenv()))
for _name in _configured_names | set(_credential_prefixes):
    if _name.startswith(_credential_prefixes):
        os.environ[_name] = ""

# Also protect import-time initialization and collection, before autouse fixtures.
from scripts.validation.isolated_runtime import block_live_network
block_live_network()

from backend.main import app
from backend.services.gemini_service import get_gemini_service
from backend.db import database
from backend.services.research.replay_ledger import replay_ledger
from backend.services.agent_reach.native.doctor import native_doctor
from backend.services.agent_reach.native.operation_capabilities import runtime_operation_capabilities
from backend.infrastructure.acquisition.security.url_validator import clear_dns_cache


@pytest.fixture(autouse=True)
def reset_in_memory_db(tmp_path, monkeypatch):
    """Reset ALL caches and isolated persisted rows between independent tests."""
    isolated_path = database.SQLITE_DB_PATH

    def reset():
        for cache in (database._mem_claims, database._mem_evidence,
                      database._mem_hash_index, database._mem_research):
            cache.clear()
        with sqlite3.connect(isolated_path) as connection:
            for table in ("claims", "evidence", "claim_research"):
                connection.execute(f"DELETE FROM {table}")
        replay_ledger._memory_cache.clear()
        runtime_operation_capabilities.reset_observations()
        native_doctor._observed_results.clear()
        native_doctor._cached_results = None
        native_doctor._last_check_ts = 0.0
        clear_dns_cache()

    reset()
    dossier_path = tmp_path / "dossiers"
    dossier_path.mkdir()
    monkeypatch.setenv("AEGIS_DOSSIER_DIR", str(dossier_path))
    monkeypatch.setattr(replay_ledger, "storage_dir", str(dossier_path))
    gemini = get_gemini_service()
    gemini.mock_mode = True
    yield
    reset()


@pytest.fixture
def test_client():
    """Return a FastAPI TestClient instance."""
    with TestClient(app) as client:
        yield client
