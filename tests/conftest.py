"""
Aegis Protocol — Pytest Configuration and Global Fixtures
==========================================================
Provides isolated test clients, in-memory database resets, and mock LLM fixtures.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure test environment variables
os.environ["AEGIS_MOCK_LLM"] = "true"
os.environ["AEGIS_ENV"] = "test"

from backend.main import app
from backend.services.gemini_service import get_gemini_service
from backend.db.database import _mem_claims, _mem_evidence


@pytest.fixture(autouse=True)
def reset_in_memory_db():
    """Clear in-memory dictionaries before each test run."""
    _mem_claims.clear()
    _mem_evidence.clear()
    gemini = get_gemini_service()
    gemini.mock_mode = True
    yield
    _mem_claims.clear()
    _mem_evidence.clear()


@pytest.fixture
def test_client():
    """Return a FastAPI TestClient instance."""
    with TestClient(app) as client:
        yield client
