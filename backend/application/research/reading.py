"""Primary-source escalation and bounded deep reading."""

from datetime import datetime
import time
from typing import Any, List

from backend.application.research.contracts import EscalatedEvidence, RankedEvidence, ReadEvidence
from backend.services.agent_reach.channels import QueryExecutionRecord
from backend.services.research.deep_reader import deep_reader
from backend.services.research.primary_source_escalator import primary_source_escalator
from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import ResearchRequest
from backend.services.research.source_quality import source_quality_engine


class PrimaryEscalationStage:
    def run(self, request: ResearchRequest, budget: ResearchBudget, ranked: RankedEvidence,
            start_ts: float, effective_timeout: float) -> EscalatedEvidence:
        # Stage 7: Adaptive Primary Source Escalation (Requirement 16)
        escalation_query_records: List[QueryExecutionRecord] = []
        # Escalation shares discovery's slice; it cannot consume the protected
        # deep-read and synthesis reservation after initial/adaptive discovery.
        escalation_time = min(budget.discovery_timeout_seconds, effective_timeout * 0.45) - (time.monotonic() - start_ts)
        if escalation_time > 0:
            escalated_primaries, esc_telemetry = primary_source_escalator.escalate(
                ranked.ranked,
                target_name=request.target,
                domain=request.domain,
                max_escalations=budget.max_primary_escalations,
                timeout_seconds=escalation_time,
            )
            if escalated_primaries:
                for p in escalated_primaries:
                    source_quality_engine.classify_and_score(p, target_name=request.target)
                esc_acc, esc_rej = relevance_gate.filter_candidates(
                    escalated_primaries,
                    target_entity=request.target,
                    domain=request.domain
                )
                ranked.rejected.extend(esc_rej)
                ranked.ranked = esc_acc + ranked.ranked

            escalation_query_records = esc_telemetry.get("execution_records") or []
            if not escalation_query_records and esc_telemetry.get("queries"):
                for idx, eq_text in enumerate(esc_telemetry.get("queries", [])):
                    q_id = f"q_esc_{idx + 1:03d}"
                    prim_count = sum(1 for p in (escalated_primaries or []) if p.metadata.get("primary_query_id") == q_id or p.metadata.get("escalation_query") == eq_text)
                    escalation_query_records.append(QueryExecutionRecord(
                        query_id=q_id,
                        channel="web",
                        query_text=eq_text,
                        query_class="primary_escalation",
                        phase="escalation",
                        status="SUCCESS" if prim_count > 0 else "NO_RESULTS",
                        started_at=None,
                        completed_at=None,
                        latency_ms=None,
                        result_count_raw=prim_count,
                        result_count_normalized=prim_count,
                        error=None,
                        retrieval_mode="direct",
                        backend_id="web",
                    ))
        else:
            escalated_primaries, esc_telemetry = [], {"queries": [], "escalations": 0}

        return EscalatedEvidence(ranked, escalated_primaries, esc_telemetry, escalation_query_records)


class DeepReadingStage:
    def run(self, request: ResearchRequest, budget: ResearchBudget, ranked: RankedEvidence,
            start_ts: float, effective_timeout: float) -> ReadEvidence:
        # Stage 8: Diversity-Aware Deep Reading (Requirement 13 & 14)
        deep_read_budget = max(0, min(request.deep_read_budget, budget.max_deep_reads))
        # The bounded discovery transport already fetched explicit source URLs.
        # Preserve those bodies without requesting the same URL twice.
        carried = [item for item in ranked.ranked if item.metadata.get("acquired_during_discovery")
                   and item.acquired_id and item.acquisition_attempt_id]
        pending = [item for item in ranked.ranked if item not in carried
                   and item.canonical_url not in {source.canonical_url for source in carried}]
        if request.domain == "financial":
            from backend.services.research.content_roles import matches_objective
            pending.sort(key=lambda item: not matches_objective(item.title, "financial"))
        if request.domain in {"brand", "personal"}:
            from backend.services.research.content_roles import matches_objective, background_read_reason
            # Spend scarce reads on the agent's task, not just a famous name.
            # All candidates remain in the corpus, with their normal ranking.
            pending.sort(key=lambda item: not matches_objective(
                f"{item.title} {item.snippet}", request.domain))
            for item in pending:
                item.metadata["objective_read_match"] = matches_objective(f"{item.title} {item.snippet}", request.domain)
                item.metadata["read_exclusion_reason"] = background_read_reason(item, request.domain)
            has_objective = any(item.metadata["objective_read_match"] for item in pending)
            for item in pending:
                item.metadata["defer_non_objective_read"] = has_objective and not item.metadata["objective_read_match"]
        # An issuer index -> quarterly index -> HTML statement is a bounded
        # at most three-hop document chain. Reserve existing read slots, not
        # extra fan-out or wall time. PDFs use the bounded text-layer parser.
        issuer_chain = request.domain == "financial" and any(
            item.query_class == "issuer_documents" for item in carried)
        first_limit = max(1, deep_read_budget - 2) if issuer_chain and deep_read_budget > 1 else deep_read_budget
        if request.domain in {"brand", "personal"}:
            # Leave an existing attempt allowance for alternatives; do not
            # increase total fan-out when the first selected batch fails.
            first_limit = min(first_limit, 3)
        if deep_read_budget > 2 and any(item.metadata.get("publisher_source_url") for item in pending):
            first_limit = min(first_limit, max(1, deep_read_budget - 4))
        from backend.services.research.publisher_links import is_publisher_hub
        if (request.domain == "financial" and not issuer_chain and deep_read_budget > 2
                and any(is_publisher_hub(item.canonical_url) for item in pending)):
            first_limit = min(first_limit, deep_read_budget - 2)
        time_left = max(0.0, effective_timeout * 0.85 - (time.monotonic() - start_ts))
        first_timeout = max(0.0, time_left - 3.0) if issuer_chain and deep_read_budget > 1 else time_left
        if deep_read_budget > 0 and pending and time_left > 0:
            investigated_items, read_telemetry = deep_reader.deep_read(
                pending,
                max_reads=first_limit,
                timeout_per_read=min(budget.channel_timeout_seconds, first_timeout)
            )
        else:
            investigated_items, read_telemetry = [], {
                "attempted": 0,
                "successful": 0,
                "failed": 0,
                "cached": 0,
                "total_chars_read": 0,
                "read_urls": [],
                "candidate_selection_audit": [],
            }

        read_telemetry["replacement_read_rounds"] = 0
        if pending and deep_read_budget > 0 and time_left <= 0:
            read_telemetry["read_failure_reason"] = "READING_DEADLINE_EXHAUSTED"
        # Only failed batches trigger replacement. Each new URL consumes the
        # original total attempt limit and the actual remaining reading window.
        attempted_ids = {row.get("candidate_id") for row in read_telemetry.get("acquisition_attempts", [])}
        attempted_urls = {row.get("url") for row in read_telemetry.get("acquisition_attempts", [])}
        while not issuer_chain and request.domain in {"brand", "personal"} and read_telemetry.get("failed", 0):
            remaining = max(0, deep_read_budget - read_telemetry.get("attempted", 0))
            time_left = max(0.0, effective_timeout * 0.85 - (time.monotonic() - start_ts))
            from backend.services.research.publisher_links import failed_feed_publisher_hubs
            if remaining >= 2 and failed_feed_publisher_hubs(pending,
                    read_telemetry.get("acquisition_attempts", []), attempted_urls):
                break  # Preserve two existing slots for an observed hub/article.
            # Deferral is priority, not permanent ineligibility. Once the
            # objective batch fails, let the reader reassess unattempted leads.
            # Keep real background/auth/quality exclusions enforced there.
            alternatives = [item for item in pending if item.id not in attempted_ids
                            and item.canonical_url not in attempted_urls]
            for item in alternatives:
                item.metadata["defer_non_objective_read"] = False
            if not remaining or not alternatives or time_left <= 0:
                break
            extra, observed = deep_reader.deep_read(alternatives, max_reads=remaining,
                timeout_per_read=min(budget.channel_timeout_seconds, time_left))
            if not observed.get("attempted"):
                break
            investigated_items.extend(extra)
            for row in observed.get("acquisition_attempts", []):
                attempted_ids.add(row.get("candidate_id"))
                attempted_urls.add(row.get("url"))
            for key in ("attempted", "successful", "failed", "cached", "total_chars_read"):
                read_telemetry[key] = read_telemetry.get(key, 0) + observed.get(key, 0)
            for key in ("read_urls", "acquisition_attempts"):
                read_telemetry.setdefault(key, []).extend(observed.get(key, []))
            audits = {row["candidate_id"]: row for row in read_telemetry.get("candidate_selection_audit", [])}
            audits.update({row["candidate_id"]: row for row in observed.get("candidate_selection_audit", [])})
            read_telemetry["candidate_selection_audit"] = list(audits.values())
            read_telemetry["replacement_read_rounds"] += 1
            if not observed.get("acquisition_attempts") or not observed.get("failed"):
                break

        linked_candidates = []
        remaining_reads = max(0, deep_read_budget - read_telemetry.get("attempted", 0))
        time_left = max(0.0, effective_timeout * 0.85 - (time.monotonic() - start_ts))
        for _followup in range(2):
            if not issuer_chain or not remaining_reads or time_left <= 0:
                break
            from urllib.parse import urlsplit
            from backend.application.research.acquisition import _observed_issuer_documents
            from backend.infrastructure.acquisition.adapters.web.page_extraction import document_link_priority
            seen = {item.canonical_url for item in ranked.ranked}
            round_candidates = []
            parents = sorted(investigated_items, key=lambda item: (-item.metadata.get("document_hop", 0), document_link_priority({"text": item.title, "url": item.canonical_url})))
            for parent in parents:
                if parent.query_class != "observed_issuer_document":
                    continue
                children = _observed_issuer_documents(parent)
                children.sort(key=lambda child: (not urlsplit(child.canonical_url).path.lower().endswith(".pdf"), document_link_priority({"text": child.title, "url": child.canonical_url})))
                for child in children:
                    if (child.canonical_url in seen
                            or not urlsplit(child.canonical_url).path.lower().endswith((".html", ".htm", ".pdf"))):
                        continue
                    seen.add(child.canonical_url)
                    source_quality_engine.classify_and_score(child, target_name=request.target)
                    round_candidates.append(child)
                    if len(round_candidates) >= min(1, remaining_reads):
                        break
                if round_candidates:
                    break
            accepted, rejected = relevance_gate.filter_candidates(
                round_candidates, target_entity=request.target, domain=request.domain, intent=request.intent)
            linked_candidates.extend(round_candidates)
            ranked.rejected.extend(rejected)
            ranked.accepted.extend(accepted)
            ranked.ranked.extend(item for item in accepted if item not in ranked.ranked)
            if accepted:
                from backend.services.research.source_independence import source_independence_engine
                ranked.ranked, ranked.clusters = source_independence_engine.cluster_independence(ranked.ranked)
                time_left = max(0.0, effective_timeout * 0.85 - (time.monotonic() - start_ts))
                extra, observed = deep_reader.deep_read(accepted, max_reads=min(1, remaining_reads),
                    timeout_per_read=min(budget.channel_timeout_seconds, time_left))
                investigated_items.extend(extra)
                for key in ("attempted", "successful", "failed", "cached", "total_chars_read"):
                    read_telemetry[key] = read_telemetry.get(key, 0) + observed.get(key, 0)
                for key in ("read_urls", "candidate_selection_audit", "acquisition_attempts"):
                    read_telemetry.setdefault(key, []).extend(observed.get(key, []))
                read_telemetry["issuer_link_follow_up_count"] = read_telemetry.get("issuer_link_follow_up_count", 0) + len(extra)
            if not round_candidates:
                break
            remaining_reads = max(0, deep_read_budget - read_telemetry.get("attempted", 0))
            time_left = max(0.0, effective_timeout * 0.85 - (time.monotonic() - start_ts))
        # Non-catalog publishers can expose useful articles through a captured
        # hub. Use only observed links, the original attempt cap and remaining
        # stage deadline. This is discovery, not a manufactured article body.
        if not issuer_chain:
            from backend.services.research.publisher_links import observed_publisher_articles, failed_feed_publisher_hubs
            read_telemetry["publisher_link_audit"] = []
            seen_urls = {item.canonical_url for item in ranked.ranked}
            # Search can return only opaque wrappers. A feed's observed
            # publisher hub offers a second discovery path without guessing a
            # slug, adding providers, or increasing attempts. Leave a slot for
            # an article; captured hubs remain background, not findings.
            remaining_reads = max(0, deep_read_budget - read_telemetry.get("attempted", 0))
            time_left = max(0.0, effective_timeout * 0.85 - (time.monotonic() - start_ts))
            hubs = failed_feed_publisher_hubs(pending, read_telemetry.get("acquisition_attempts", []), seen_urls)
            if hubs and remaining_reads >= 2 and time_left > 0:
                hubs = hubs[:min(2, remaining_reads - 2)] if remaining_reads > 2 else hubs[:1]
                linked_candidates.extend(hubs)
                seen_urls.update(item.canonical_url for item in hubs)
                extra, observed = deep_reader.deep_read(hubs, max_reads=len(hubs),
                    timeout_per_read=min(budget.channel_timeout_seconds, time_left))
                investigated_items.extend(extra)
                for key in ("attempted", "successful", "failed", "cached", "total_chars_read"):
                    read_telemetry[key] = read_telemetry.get(key, 0) + observed.get(key, 0)
                for key in ("read_urls", "candidate_selection_audit", "acquisition_attempts"):
                    read_telemetry.setdefault(key, []).extend(observed.get(key, []))
                read_telemetry["feed_publisher_hub_attempts"] = observed.get("attempted", 0)
            for _ in range(2):
                remaining_reads = max(0, deep_read_budget - read_telemetry.get("attempted", 0))
                time_left = max(0.0, effective_timeout * 0.85 - (time.monotonic() - start_ts))
                if not remaining_reads or time_left <= 0:
                    break
                observed = []
                for parent in carried + investigated_items:
                    for child in observed_publisher_articles(parent, request.domain, read_telemetry["publisher_link_audit"], request.target):
                        if child.canonical_url not in seen_urls:
                            seen_urls.add(child.canonical_url)
                            source_quality_engine.classify_and_score(child, target_name=request.target)
                            observed.append(child)
                if not observed:
                    break
                accepted, rejected = relevance_gate.filter_candidates(observed, target_entity=request.target,
                    domain=request.domain, intent=request.intent, provisional_read=request.domain == "trending")
                # Feed URLs are an observed publisher discovery step, not
                # subject evidence. Do not fake an entity match on the feed.
                accepted += [item for item in observed if item.metadata.get("discovery_kind") == "FEED_INDEX"
                             and item not in accepted]
                linked_candidates.extend(observed)
                ranked.rejected.extend(rejected)
                ranked.accepted.extend(accepted)
                ranked.ranked.extend(accepted)
                if not accepted:
                    break
                round_limit = min(2, remaining_reads)
                if accepted and accepted[0].metadata.get("discovery_kind") == "FEED_INDEX":
                    round_limit = 1  # Reserve an existing slot for its article.
                extra, extra_trace = deep_reader.deep_read(accepted, max_reads=round_limit,
                    timeout_per_read=min(budget.channel_timeout_seconds, time_left))
                investigated_items.extend(extra)
                for key in ("attempted", "successful", "failed", "cached", "total_chars_read"):
                    read_telemetry[key] = read_telemetry.get(key, 0) + extra_trace.get(key, 0)
                for key in ("read_urls", "acquisition_attempts", "candidate_selection_audit"):
                    read_telemetry.setdefault(key, []).extend(extra_trace.get(key, []))
        read_telemetry["reused_acquired_count"] = len(carried)
        return ReadEvidence(carried + investigated_items, read_telemetry, linked_candidates)
