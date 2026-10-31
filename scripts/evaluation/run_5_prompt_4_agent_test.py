"""
Aegis Protocol — 5 Prompt 4 Agent Live Evaluation & Word Extraction Benchmark
=============================================================================
Runs 5 diverse, realistic prompts across each of the 4 production agents:
1. ScoutAgent (Financial / Corporate / Equities)
2. BrandShieldAgent (Brand defense / Counterfeiting / Impersonation / Scams)
3. TrendingAgent (Emerging memetic virality / Narrative velocity / Pop culture)
4. PersonalWatchAgent (VIP / Executive defense / Doxxing / Deepfake / Identity)

Measures:
- Total raw body words fetched
- Unique retained body words (case-insensitive distinct tokens)
- Number of evidence/source records
- Number of deep reads (FULL_ARTICLE / PRIMARY_DOCUMENT / PARTIAL_CONTENT)
- Execution latency per prompt
- Specific channel issues, network warnings, or extraction bottlenecks
"""

import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

# Ensure deterministic source planning without Gemini 429 quota exhaustion
os.environ["AEGIS_SOURCE_PLANNER_LLM_ENABLED"] = "false"
os.environ["AEGIS_MOCK_LLM"] = "true"

from backend.agents.scout.agent import scout_agent
from backend.agents.brandshield.agent import brandshield_agent
from backend.agents.trending.agent import trending_agent
from backend.agents.personal_watch.agent import personal_watch_agent

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("FivePromptBenchmark")

PROMPTS = {
    "Scout": [
        "NVDA",
        "AAPL",
        "TSLA",
        "MSFT",
        "AMZN",
    ],
    "BrandShield": [
        "Nike",
        "Rolex",
        "Pfizer",
        "Gucci",
        "Sony",
    ],
    "Trending": [
        "Russell Brand",
        "Taylor Swift",
        "OpenAI",
        "Artificial Intelligence",
        "DeepSeek",
    ],
    "PersonalWatch": [
        "Satya Nadella",
        "Tim Cook",
        "Sam Altman",
        "Sundar Pichai",
        "Jensen Huang",
    ],
}


def compute_word_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute total words, unique words, deep reads count, and unique body count."""
    seen_hashes: Set[str] = set()
    all_tokens: Set[str] = set()
    total_words = 0
    deep_reads = 0
    body_records = 0
    sample_sources = []

    for item in records:
        if not isinstance(item, dict):
            if hasattr(item, "to_dict"):
                item = item.to_dict()
            else:
                continue

        content = item.get("content") or item.get("snippet") or ""
        depth = item.get("content_depth") or (item.get("metadata", {}).get("content_depth") if isinstance(item.get("metadata"), dict) else "")
        source_name = item.get("source") or item.get("platform") or "Web"
        url = item.get("url") or item.get("canonical_url") or ""

        if depth in ("FULL_ARTICLE", "PRIMARY_DOCUMENT", "PARTIAL_CONTENT", "FEED_ENTRY_CONTENT"):
            deep_reads += 1

        if content:
            h = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                words = content.split()
                total_words += len(words)
                body_records += 1
                tokens = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", content.lower())
                all_tokens.update(tokens)

        if len(sample_sources) < 4 and (source_name or url):
            sample_sources.append({
                "source": source_name,
                "title": (item.get("title") or "")[:70],
                "depth": depth or "SNIPPET",
                "words": len((content or "").split()),
            })

    return {
        "total_records": len(records),
        "body_records": body_records,
        "deep_reads": deep_reads,
        "total_words": total_words,
        "unique_words": len(all_tokens),
        "sample_sources": sample_sources,
    }


def run_single_test(agent_name: str, prompt: str) -> Dict[str, Any]:
    """Run an individual agent test and record timing, words, and issues."""
    t0 = time.time()
    error_msg = None
    records = []
    findings_count = 0

    try:
        if agent_name == "Scout":
            res = scout_agent.analyze_stock(prompt)
            records = res.get("sources", [])
            findings_count = len(res.get("findings", []))
        elif agent_name == "BrandShield":
            res = brandshield_agent.scan(brand_name=prompt)
            records = res.get("evidence", []) or res.get("sources", [])
            findings_count = len(res.get("findings", []))
        elif agent_name == "Trending":
            res = trending_agent.scan(asset_name=prompt)
            records = res.get("evidence", [])
            findings_count = len(res.get("trends", [])) or len(res.get("findings", []))
        elif agent_name == "PersonalWatch":
            res = personal_watch_agent.scan(vip_profile={"name": prompt})
            records = res.get("evidence", []) or res.get("mentions", [])
            findings_count = len(res.get("threats", [])) or len(res.get("findings", []))
        else:
            raise ValueError(f"Unknown agent: {agent_name}")

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"[{agent_name}] Error executing prompt '{prompt}': {exc}", exc_info=True)

    elapsed = round(time.time() - t0, 2)
    metrics = compute_word_metrics(records)

    return {
        "agent": agent_name,
        "prompt": prompt,
        "elapsed_seconds": elapsed,
        "total_records": metrics["total_records"],
        "body_records": metrics["body_records"],
        "deep_reads": metrics["deep_reads"],
        "total_words": metrics["total_words"],
        "unique_words": metrics["unique_words"],
        "findings_count": findings_count,
        "sample_sources": metrics["sample_sources"],
        "error": error_msg,
        "status": "FAILED" if error_msg else ("EXCELLENT" if metrics["total_words"] >= 1500 else ("GOOD" if metrics["total_words"] >= 300 else "DEGRADED")),
    }


def main():
    print("=" * 80)
    print("AEGIS PROTOCOL — 4-AGENT 5-PROMPT LIVE BENCHMARK")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    results: List[Dict[str, Any]] = []
    agent_summaries: Dict[str, Dict[str, Any]] = {}

    for agent_name, prompt_list in PROMPTS.items():
        print(f"\n>>> RUNNING AGENT: {agent_name.upper()} ({len(prompt_list)} prompts)")
        agent_words = 0
        agent_unique_tokens: Set[str] = set()
        agent_time = 0.0
        agent_records = 0
        agent_deep = 0

        for idx, prompt in enumerate(prompt_list, start=1):
            print(f"  [{idx}/5] Testing '{prompt}' ... ", end="", flush=True)
            res = run_single_test(agent_name, prompt)
            results.append(res)

            agent_words += res["total_words"]
            agent_time += res["elapsed_seconds"]
            agent_records += res["total_records"]
            agent_deep += res["deep_reads"]

            print(f"Done ({res['elapsed_seconds']}s) -> {res['total_records']} sources | {res['deep_reads']} deep reads | {res['total_words']} words ({res['unique_words']} unique) [{res['status']}]")

        agent_summaries[agent_name] = {
            "total_prompts": len(prompt_list),
            "total_time_seconds": round(agent_time, 2),
            "avg_time_per_prompt": round(agent_time / len(prompt_list), 2),
            "total_records": agent_records,
            "total_deep_reads": agent_deep,
            "total_words": agent_words,
            "avg_words_per_prompt": round(agent_words / len(prompt_list), 1),
        }

    # Print Summary Table
    print("\n" + "=" * 80)
    print("FINAL 4-AGENT BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Agent':<15} | {'Total Words':<12} | {'Avg Words/P':<12} | {'Deep Reads':<11} | {'Sources':<8} | {'Avg Time (s)':<12}")
    print("-" * 80)
    for agent_name, summ in agent_summaries.items():
        print(f"{agent_name:<15} | {summ['total_words']:<12} | {summ['avg_words_per_prompt']:<12} | {summ['total_deep_reads']:<11} | {summ['total_records']:<8} | {summ['avg_time_per_prompt']:<12}")
    print("-" * 80)

    # Save artifact
    output_path = Path("artifacts/live_evaluation/five_prompt_four_agent_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_summaries": agent_summaries,
            "test_cases": results,
        }, f, indent=2)

    print(f"\nDetailed evaluation results saved to: {output_path}")


if __name__ == "__main__":
    main()

