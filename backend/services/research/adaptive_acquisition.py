"""Opt-in acquisition routing feedback, never final evidence acceptance.

Only already captured bytes enter the existing deterministic Layer 2 gates.
Copies isolate early feedback from raw captures and the final pipeline pass.
No inference provider, extra HTTP request or fabricated article is involved.
"""
import copy
import hashlib
from collections import Counter
from urllib.parse import urlsplit


def inspect_capture(item, target, domain, intent, reference_time):
    from backend.services.research.body_context import reconcile_captured_context
    from backend.services.research.raw_pool import _source_type
    from backend.services.research.relevance_gate import RelevanceGate
    from backend.services.research.source_quality import source_quality_engine
    from backend.services.research.passage_extractor import PassageExtractor, has_usable_passage

    observed = copy.deepcopy(item)
    observed.metadata["temporal_required"] = domain == "trending"
    reconcile_captured_context(observed)
    kind = _source_type(observed, captured=True)
    observed.snippet = (observed.content or "")[:12_000]
    observed.relevant_excerpt = ""
    source_quality_engine.classify_and_score(observed, target_name=target)
    assessment = RelevanceGate(reference_time=reference_time).evaluate_item(
        observed, target, domain=domain, intent=intent)
    structural = kind in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT", "COMMUNITY_POST", "STRUCTURED_PUBLIC_DATA"}
    observed.metadata.update(layer2_eligible=structural and assessment.is_accepted,
        temporal_eligible=assessment.is_accepted if domain == "trending" else True)
    reason = assessment.rejection_reason or ("NO_STRUCTURAL_BODY" if not structural else None)
    if observed.metadata["layer2_eligible"]:
        PassageExtractor().extract_passages([observed], target, intent=intent, domain=domain)
    usable = bool(observed.metadata["layer2_eligible"] and has_usable_passage(observed))
    return {"source_id": item.id, "host": (urlsplit(item.canonical_url).hostname or "").lower(),
        "body_sha256": hashlib.sha256((item.content or "").encode()).hexdigest(),
        "source_type": kind, "usable_passage": usable,
        "selected_excerpt_words": len(observed.relevant_excerpt.split()) if usable else 0,
        "reason": None if usable else reason or observed.extraction_status or "NO_RELEVANT_PASSAGE",
        "scope": "ROUTING_FEEDBACK_ONLY_FINAL_QUALIFICATION_REQUIRED"}


class InterleavedController:
    """Bounded local decisions; source-host coverage is not independence."""
    def __init__(self, target, domain, intent, reference_time):
        self.target, self.domain, self.intent = target, domain, intent
        self.reference_time = reference_time
        self.feedback = []
        self.events = []
        self.event_count = 0
        self.seen_bodies = set()
        self.zero_yield_articles = Counter()

    def record(self, action, **details):
        self.event_count += 1
        if len(self.events) < 100:
            self.events.append({"sequence": self.event_count, "action": action, **details})

    def observe(self, item):
        try:
            row = inspect_capture(item, self.target, self.domain, self.intent, self.reference_time)
        except Exception as error:
            row = {"source_id": item.id, "usable_passage": False,
                   "reason": "FEEDBACK_ERROR_" + type(error).__name__, "scope": "ROUTING_FEEDBACK_UNKNOWN"}
        duplicate = row.get("body_sha256") in self.seen_bodies
        row["duplicate_body_observation"] = duplicate
        if row.get("body_sha256"):
            self.seen_bodies.add(row["body_sha256"])
        if not duplicate and row.get("source_type") in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT"}:
            if row["usable_passage"]:
                self.zero_yield_articles[row["host"]] = 0
            else:
                self.zero_yield_articles[row["host"]] += 1
        self.feedback.append(row)
        self.record("CAPTURE_FEEDBACK", **row)

    def enough_for_discovery_pause(self):
        usable = [row for row in self.feedback if row["usable_passage"] and not row["duplicate_body_observation"]]
        return len(usable) >= 4 and len({row.get("host") for row in usable} - {None, ""}) >= 3

    def defer_reason(self, item):
        # A feed date is only a routing observation. Final body dates still
        # replace discovery metadata and face the unchanged temporal gate.
        if self.domain == "trending":
            status = item.metadata.get("discovery_temporal_observation")
            if status in {"STALE", "FUTURE_DATED", "SYNDICATED_STALE", "UPDATED_HISTORICAL_REJECTED"}:
                return "DEFERRED_DISCOVERY_DATE_" + status
        host = (urlsplit(item.canonical_url).hostname or "").lower()
        if self.zero_yield_articles[host] >= 2:
            if self.domain == "trending" and item.metadata.get("discovery_temporal_observation") in {"FRESH", "UPDATED_HISTORICAL_ACCEPTED"}:
                return None  # A fresh observed lead may test an earlier stale tree; final gates still apply.
            return "DEFERRED_ZERO_YIELD_PUBLISHER_TREE"
        return None

    def snapshot(self):
        return {"mode": "interleaved_v1", "experimental": True,
            "feedback_scope": "Deterministic captured-body passage checks, not claim truth or final qualification",
            "feedback": self.feedback, "zero_yield_article_observations_by_host": dict(self.zero_yield_articles),
            "events": self.events, "event_count": self.event_count,
            "events_omitted_by_limit": max(0, self.event_count - len(self.events)),
            "discovery_pause_threshold": "Four usable captures across three observed hosts, plus remaining read opportunity and planned-action checks; independence unverified"}
