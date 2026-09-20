"""
Automated Test Suite: Aegis Protocol Launch Video Integrity
===========================================================
Validates that:
1. Storyboard plan, composition brief, and social share copy exist.
2. Composition HTML contains valid GSAP timeline and audio elements.
3. FastAPI endpoints /launch-video and /api/media/launch-info respond successfully.
"""

import sys
import os

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_launch_documents_exist():
    required_files = [
        "brag-output/brag-plan.md",
        "brag-output/composition-brief.md",
        "brag-output/share-copy.md",
        "brag-output/brag.png",
        "brag-output/composition/index.html"
    ]
    for rel_path in required_files:
        assert os.path.exists(rel_path), f"Missing required file: {rel_path}"
        assert os.path.getsize(rel_path) > 0, f"File is empty: {rel_path}"
        print(f" [PASS] File verified: {rel_path} ({os.path.getsize(rel_path)} bytes)")

def test_composition_html_structure():
    with open("brag-output/composition/index.html", "r", encoding="utf-8") as f:
        content = f.read()
    assert "data-composition-id=\"main\"" in content
    assert "gsap.timeline" in content
    assert "assets/music/music.mp3" in content
    assert "AEGIS PROTOCOL" in content
    print(" [PASS] Composition HTML markup and timeline verified")

def test_launch_api_endpoints():
    # Test metadata endpoint
    r = client.get("/api/media/launch-info")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ready"
    assert data.get("duration_seconds") == 20
    print(f" [PASS] /api/media/launch-info -> {data['title']}")

    # Test interactive player route
    r2 = client.get("/launch-video")
    assert r2.status_code == 200
    assert "Aegis Protocol — Launch Film" in r2.text
    print(" [PASS] /launch-video served successfully")

if __name__ == "__main__":
    print("Running Launch Video Integrity Test Suite...")
    test_launch_documents_exist()
    test_composition_html_structure()
    test_launch_api_endpoints()
    print("All launch video tests passed successfully!")
