"""
Test suite for Aegis FastAPI OpenAPI Documentation and Agent Route Integrity.
Validates that all core agent routes, omni-scan, truth-dossier, and docs are correctly mapped.
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root_ping():
    response = client.get("/api/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "agents" in data
    print(" [PASS] /api/ root ping ok")

def test_openapi_json_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    paths = schema["paths"]
    
    # Required verified endpoints in Aegis FastAPI API
    expected_endpoints = [
        "/api/healthz",
        "/api/",
        "/api/system/agents",
        "/api/claims/verify",
        "/api/agent-reach/omni-scan",
        "/api/agent-reach/doctor",
        "/api/scout/analyze",
        "/api/brandshield/scan",
        "/api/personal/scan",
        "/api/trending/scan"
    ]
    
    for ep in expected_endpoints:
        assert ep in paths, f"Missing expected endpoint in OpenAPI schema: {ep}"
        print(f" [PASS] Endpoint registered in schema: {ep}")

def test_docs_accessible():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text
    print(" [PASS] /docs Swagger UI accessible")

if __name__ == "__main__":
    print("Starting OpenAPI Schema & Docs Validation...")
    test_root_ping()
    test_openapi_json_schema()
    test_docs_accessible()
    print("All 3 OpenAPI & Docs test suites passed successfully!")
