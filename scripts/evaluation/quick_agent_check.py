"""Quick check of each of the 4 agents to verify entry points and inspect data structure."""
import os
os.environ["AEGIS_SOURCE_PLANNER_LLM_ENABLED"] = "false"
os.environ["AEGIS_MOCK_LLM"] = "true"

import sys
import time
import json

from backend.agents.scout.agent import scout_agent
from backend.agents.brandshield.agent import brandshield_agent
from backend.agents.trending.agent import trending_agent
from backend.agents.personal_watch.agent import personal_watch_agent

def test_quick():
    print("Testing Scout...")
    t0 = time.time()
    res_scout = scout_agent.analyze_stock("NVDA")
    dur_scout = time.time() - t0
    sources_scout = res_scout.get("sources", [])
    words_scout = sum(len((s.get("content") or s.get("snippet") or "").split()) for s in sources_scout)
    deep_scout = sum(1 for s in sources_scout if s.get("content_depth") in ("FULL_ARTICLE", "PRIMARY_DOCUMENT", "PARTIAL_CONTENT"))
    print(f"Scout NVDA: {len(sources_scout)} sources, {deep_scout} deep reads, {words_scout} words in {dur_scout:.1f}s")
    
    print("\nTesting BrandShield...")
    t0 = time.time()
    res_brand = brandshield_agent.scan("Nike")
    dur_brand = time.time() - t0
    sources_brand = res_brand.get("evidence", []) or res_brand.get("sources", [])
    words_brand = sum(len((s.get("content") or s.get("snippet") or "").split()) for s in sources_brand)
    deep_brand = sum(1 for s in sources_brand if s.get("content_depth") in ("FULL_ARTICLE", "PRIMARY_DOCUMENT", "PARTIAL_CONTENT"))
    print(f"BrandShield Nike: {len(sources_brand)} sources, {deep_brand} deep reads, {words_brand} words in {dur_brand:.1f}s")

    print("\nTesting Trending...")
    t0 = time.time()
    res_trend = trending_agent.scan("Russell Brand")
    dur_trend = time.time() - t0
    sources_trend = res_trend.get("evidence", [])
    words_trend = sum(len((s.get("content") or s.get("snippet") or "").split()) for s in sources_trend)
    deep_trend = sum(1 for s in sources_trend if s.get("content_depth") in ("FULL_ARTICLE", "PRIMARY_DOCUMENT", "PARTIAL_CONTENT") or (isinstance(s, dict) and s.get("metadata", {}).get("content_depth") in ("FULL_ARTICLE", "PRIMARY_DOCUMENT", "PARTIAL_CONTENT")))
    print(f"Trending Russell Brand: {len(sources_trend)} sources, {deep_trend} deep reads, {words_trend} words in {dur_trend:.1f}s")

    print("\nTesting PersonalWatch...")
    t0 = time.time()
    res_pw = personal_watch_agent.scan({"name": "Satya Nadella"})
    dur_pw = time.time() - t0
    sources_pw = res_pw.get("evidence", []) or res_pw.get("mentions", [])
    words_pw = sum(len((s.get("content") or s.get("snippet") or "").split()) for s in sources_pw)
    deep_pw = sum(1 for s in sources_pw if s.get("content_depth") in ("FULL_ARTICLE", "PRIMARY_DOCUMENT", "PARTIAL_CONTENT"))
    print(f"PersonalWatch Satya Nadella: {len(sources_pw)} sources, {deep_pw} deep reads, {words_pw} words in {dur_pw:.1f}s")

if __name__ == "__main__":
    test_quick()
