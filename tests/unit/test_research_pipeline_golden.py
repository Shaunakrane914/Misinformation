"""Deterministic Phase 4 characterization of result and replay serialization.

The manifest was captured from commit 1795ee4 before changing ResearchEngine.
Only acquisition and deep-reading I/O are faked; planning, gates, ranking,
adaptive accounting, synthesis, graphs, integrity, and ReplayLedger are real.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.services.agent_reach.channels import EvidenceFragment, QueryExecutionRecord, RetrievalResult
from backend.services.research.replay_ledger import ReplayLedger
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_engine import ResearchEngine
from backend.services.research.research_models import ResearchRequest


MANIFEST = Path(__file__).with_name("fixtures") / "research_phase4_golden.json"
STAMP = "2026-10-10T00:00:00+00:00"


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        fixed = cls(2026, 10, 10, tzinfo=timezone.utc)
        return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    @classmethod
    def utcnow(cls):
        return cls(2026, 10, 10)


def _fragment(code, title, url, snippet, *, channel="web", query_class="general", metadata=None):
    return EvidenceFragment(
        platform=channel.title(), title=title, url=url, content=snippet,
        snippet=snippet, author="Fixture Source", published=STAMP,
        retrieved_at=STAMP, evidence_id=code, channel_name=channel,
        query_id=f"q_{code}", query_class=query_class, query_text="Tesla revenue",
        native_backend_id="fixture-backend", raw_metadata=dict(metadata or {}),
    )


def _fixtures():
    relevant = _fragment(
        "ev_sec", "Tesla revenue rose in official filing",
        "https://www.sec.gov/tesla/revenue", "Tesla reported revenue growth in its official filing.",
        query_class="financial",
    )
    wire = _fragment(
        "ev_reuters", "Tesla revenue rose, Reuters reports",
        "https://www.reuters.com/tesla/revenue", "(Reuters) Tesla revenue rose following vehicle deliveries.",
        query_class="financial",
    )
    echo = _fragment(
        "ev_echo", "Tesla revenue rose, Reuters reports",
        "https://finance.yahoo.com/tesla/reuters", "Reporting by Reuters: Tesla revenue rose following vehicle deliveries.",
        query_class="financial",
    )
    adverse = _fragment(
        "ev_adverse", "Tesla revenue fell, analysts report",
        "https://example.org/tesla-revenue-fell", "Tesla revenue did not rise; a competing report says revenue fell.",
        query_class="financial",
    )
    irrelevant = _fragment(
        "ev_wrong", "Unrelated medical trial",
        "https://example.org/medical", "Peer-reviewed clinical trials of a new diabetes therapy.",
    )
    malformed = _fragment("ev_malformed", "Tesla update", "", "Tesla update with missing source URL.")
    secondary = _fragment(
        "ev_secondary", "Tesla regulatory filing referenced by reporters",
        "https://example.org/tesla-filing", "Tesla revenue according to a regulatory filing and official statement.",
        query_class="financial",
    )
    return {
        "relevant": relevant, "wire": wire, "echo": echo, "adverse": adverse,
        "irrelevant": irrelevant, "malformed": malformed, "secondary": secondary,
    }


SCENARIOS = {
    "relevant": ("relevant", "wire"),
    "empty": (),
    "adversarial": ("irrelevant", "relevant"),
    "syndicated": ("wire", "echo", "relevant"),
    "conflicting": ("relevant", "adverse"),
    "missing_primary": ("wire",),
    "primary_escalation": ("secondary",),
    "adaptive_saturation": ("relevant",),
    "discovery_timeout": ("relevant",),
    "credential_failure": (),
    "malformed_metadata": ("malformed", "relevant"),
    "insufficient": ("irrelevant",),
}


def _hash(value):
    def canonical(node):
        if isinstance(node, dict):
            return {
                key: sorted(canonical(entry) for entry in val) if key in {"independence_groups", "entities"} and isinstance(val, list)
                else canonical(val)
                for key, val in node.items()
            }
        if isinstance(node, list):
            return [canonical(entry) for entry in node]
        return node

    # Corroboration group membership and extracted entity names come from sets.
    # Their order is undefined; all IDs, names, and every other field are exact.
    encoded = json.dumps(canonical(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def capture_scenario(name, include_payload=False):
    from backend.services.agent_reach import agent_reach_service
    from backend.services.research import replay_ledger as ledger_module

    fixtures = _fixtures()
    fragments = [fixtures[key] for key in SCENARIOS[name]]
    initial_record = QueryExecutionRecord(
        query_id="q_initial", channel="web", query_text="Tesla revenue",
        query_class="financial", phase="initial",
        status="AUTH_REQUIRED" if name == "credential_failure" else "SUCCESS",
        started_at=STAMP, completed_at=STAMP, latency_ms=0,
        result_count_raw=len(fragments), result_count_normalized=len(fragments),
        retrieval_mode="direct", backend_id="fixture-backend",
    )
    retrieval = RetrievalResult(
        query="Tesla revenue", domain="financial", fragments=fragments,
        channel_health={"web": "AUTH_REQUIRED" if name == "credential_failure" else "AVAILABLE"},
        retrieval_trace={"scan_id": "phase4_fixture"}, query_records=[initial_record],
        total_signals=len(fragments),
    )
    budget = ResearchBudget(
        follow_up_budget=2 if name == "adaptive_saturation" else (1 if name == "discovery_timeout" else 0),
        primary_escalation_budget=1, deep_read_budget=2,
        timeout_seconds=0 if name == "discovery_timeout" else 20,
    )

    def read_fixture(ranked, max_reads, timeout_per_read):
        selected = ranked[:min(2, max_reads)]
        for item in selected:
            item.acquisition_attempt_id = f"attempt_{item.id}"
            item.acquired_id = f"acquired_{item.id}"
            item.read_status = "SUCCESS"
        return selected, {
            "attempted": len(selected), "successful": len(selected), "failed": 0,
            "cached": 0, "total_chars_read": 0, "read_urls": [item.canonical_url for item in selected],
            "candidate_selection_audit": [], "acquisition_attempts": [],
        }

    def search_fixture(channel, query, limit=2):
        if name == "adaptive_saturation":
            return [fixtures["relevant"]]
        return []

    def escalate_fixture(ranked, target_name, domain, max_escalations):
        if name != "primary_escalation":
            return [], {"queries": [], "escalations": 0}
        from backend.services.research.research_models import EvidenceItem
        item = EvidenceItem.from_evidence_fragment(fixtures["relevant"], "ev_escalated", target_name)
        item.metadata["primary_query_id"] = "q_esc_001"
        return [item], {"queries": ['"Tesla revenue" official filing'], "escalations": 1}

    patches = [
        patch.object(agent_reach_service, "retrieve_many", return_value=retrieval),
        patch.object(agent_reach_service, "search_channel", side_effect=search_fixture),
        patch("backend.services.research.deep_reader.deep_reader.deep_read", side_effect=read_fixture),
        patch("backend.services.research.primary_source_escalator.primary_source_escalator.escalate", side_effect=escalate_fixture),
        patch("time.time", return_value=1000.0),
        patch("time.gmtime", return_value=time.struct_time((2026, 10, 10, 0, 0, 0, 5, 283, 0))),
        patch.object(ReplayLedger, "_generate_dossier_id", return_value=f"R-2026-{name.upper()}"),
    ]
    if name == "adaptive_saturation":
        patches.append(patch(
            "backend.services.agent_reach.planner.RetrievalPlanner.plan_adaptive_follow_ups",
            return_value=[
                {"query_id": "q_adaptive_1", "query_text": "Tesla repeated source one", "query_class": "adaptive_expansion", "suggested_channels": ["web"]},
                {"query_id": "q_adaptive_2", "query_text": "Tesla repeated source two", "query_class": "adaptive_expansion", "suggested_channels": ["web"]},
            ],
        ))
    for module_name in (
        "backend.services.research.research_engine",
        "backend.services.research.research_models",
        "backend.services.research.temporal_guard",
        "backend.application.research.adaptive",
    ):
        module = sys.modules.get(module_name)
        if module is None and module_name.startswith("backend.application.research."):
            import importlib
            module = importlib.import_module(module_name)
        if module is not None and hasattr(module, "datetime"):
            patches.append(patch.object(module, "datetime", FixedDatetime))

    with tempfile.TemporaryDirectory() as directory:
        ledger = ReplayLedger(storage_dir=directory)
        patches.append(patch.object(ledger_module, "replay_ledger", ledger))
        from contextlib import ExitStack
        with ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            request = ResearchRequest(
                target="Tesla revenue", domain="financial", intent="Tesla revenue",
                agent_name="phase4_fixture", deep_read_budget=2, timeout_seconds=budget.timeout_seconds,
            )
            result = ResearchEngine(budget=budget).investigate(request)
            dossier = ledger.get_dossier(result.telemetry["dossier_id"])
            assert dossier is not None
            serialized = result.to_dict()
            if include_payload:
                return {"result": serialized, "corpus": result.research_corpus, "dossier": dossier}
            return {
                "result_sha256": _hash(serialized),
                "corpus_sha256": _hash(result.research_corpus),
                "dossier_sha256": _hash(dossier),
                "candidate_ids": [item.id for item in result.candidates],
                "ranked_ids": [item["id"] for item in result.research_corpus["ranked_candidates"]],
                "rejected_ids": [item.get("evidence_id") for item in result.rejected_evidence],
                "query_statuses": [[item["query_id"], item["status"]] for item in result.research_corpus["queries"]],
                "finding_ids": [finding.finding_id for finding in result.findings],
                "candidate_hashes": dossier["candidate_hashes"],
                "lineage_metrics": dossier["source_lineage"].get("metrics", {}),
            }


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_research_result_and_replay_match_pre_refactor(name):
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))[name]
    assert capture_scenario(name) == expected


if __name__ == "__main__":
    print(json.dumps({name: capture_scenario(name) for name in sorted(SCENARIOS)}, indent=2, sort_keys=True))
