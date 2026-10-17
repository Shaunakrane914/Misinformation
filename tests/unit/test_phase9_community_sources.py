import json

import pytest

from backend.infrastructure.acquisition.adapters import community
from backend.infrastructure.acquisition.adapters.community import acquire_community
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.native.operation_capabilities import RuntimeOperationCapabilities


def response(url, payload):
    return BoundedHTTPResponse(json.dumps(payload).encode(), url, 200, "application/json", {}, 1, 1)


def test_hn_index_is_discovery_and_original_item_provides_text():
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        assert kwargs["timeout"] == 5.0 and kwargs["max_bytes"] == 1_000_000
        if "algolia" in url:
            return response(url, {"hits": [{"objectID": "8863"}, {"objectID": "8864"}, {"objectID": "https://127.0.0.1"}]})
        item_id = int(url.rsplit("/", 1)[-1].split('.')[0])
        return response(url, {"id": item_id, "title": "Observed discussion", "text": "<p>Body</p><script>bad()</script>", "time": 1175714200})

    fragments, telemetry = acquire_community("hackernews", "discussion", 3, http_fetcher=fetch)
    assert len(calls) == 3 and len(fragments) == 2
    assert fragments[0].content == "Body"
    assert fragments[0].source_id != fragments[1].source_id
    assert fragments[0].evidence_id != fragments[1].evidence_id
    assert telemetry["discovery_backend"] == "Algolia HN search index"
    assert all(item["network_observed_this_attempt"] for item in telemetry["transport_observations"])


@pytest.mark.parametrize("platform,query", [
    ("hackernews", "https://news.ycombinator.com.evil/item?id=1"),
    ("hackernews", "https://127.0.0.1/item?id=1"),
    ("stackexchange", "https://stackoverflow.com.evil/questions/1"),
    ("stackexchange", "https://localhost/questions/1"),
])
def test_invalid_direct_targets_make_no_requests(platform, query):
    def fetch(*args, **kwargs):
        pytest.fail("Invalid direct target must not trigger network")
    fragments, telemetry = acquire_community(platform, query, operation="read", http_fetcher=fetch)
    assert not fragments and telemetry["status"] == "INVALID_TARGET"


def test_stack_bodies_quota_and_future_backoff(monkeypatch):
    monkeypatch.setattr(community, "_backoff_until", 0.0)
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        return response(url, {"backoff": 10, "quota_remaining": 2, "has_more": True, "items": [{
            "question_id": 123, "title": "Observed", "body": "<p>Actual question</p>",
            "owner": {"display_name": "Author"}, "creation_date": 1600000000,
        }]})

    fragments, telemetry = acquire_community("stackexchange", "python", http_fetcher=fetch)
    assert fragments[0].content == "Actual question"
    assert "filter=withbody" in calls[0]
    assert telemetry["has_more"] is True
    assert fragments[0].raw_metadata["answers_acquired"] is False
    assert acquire_community("stackexchange", "python", http_fetcher=fetch)[1]["status"] == "RATE_LIMITED"
    assert len(calls) == 1


def test_zero_budget_and_live_registry_contract():
    assert not acquire_community("hackernews", "python", 0)[0]
    runtime = RuntimeOperationCapabilities()
    for name in ("hackernews", "stackexchange"):
        assert runtime.assess(name, "read")["decision"] not in {"EXCLUDE", "DEFER_TEMPORARY"}
    from backend.infrastructure.acquisition.service import AgentReachService
    service = AgentReachService()
    assert {"hackernews", "stackexchange"} <= set(service.registry.channel_names)
    from backend.services.agent_reach.native.doctor import DoctorBridge
    assert DoctorBridge().get_canonical_status_code("hackernews") == "NOT_PROBED"
    assert DoctorBridge().get_canonical_status_code("stackexchange") == "NOT_PROBED"


def test_hn_replies_are_bounded_parent_checked_and_deleted_skipped():
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        if "/8863.json" in url:
            return response(url, {"id": 8863, "kids": [11, 12, 13]})
        child = int(url.rsplit('/', 1)[-1].split('.')[0])
        return response(url, {"id": child, "parent": 8863, "text": "Observed reply", "deleted": child == 12})

    fragments, _ = acquire_community("hackernews", "8863", operation="read", include_comments=True, http_fetcher=fetch)
    assert len(calls) == 3
    assert len(fragments) == 2
    assert fragments[1].content == "Observed reply"
    assert fragments[1].raw_metadata["parent_id"] == 8863
    assert fragments[1].content_depth == "COMMENT"
    assert fragments[0].raw_metadata["transport"]["endpoint"].endswith('/8863.json')
    assert fragments[1].raw_metadata["transport"]["endpoint"].endswith('/11.json')


def test_failed_reply_does_not_discard_original_hn_item():
    def fetch(url, **kwargs):
        if '/8863.json' in url:
            return response(url, {"id": 8863, "text": "Original observed body", "kids": [11]})
        raise TimeoutError("fixture")
    fragments, telemetry = acquire_community("hackernews", "8863", operation="read", include_comments=True, http_fetcher=fetch)
    assert len(fragments) == 1 and fragments[0].content == "Original observed body"
    assert telemetry["followup_failures"] == ["TimeoutError"]


def test_community_direct_urls_route_for_each_agent(monkeypatch):
    # Offline routing test only: transport/DNS security has separate controls.
    monkeypatch.setattr("backend.services.agent_reach.source_planner.is_safe_url", lambda url: (True, "fixture"))
    from backend.services.agent_reach.source_planner import SourcePlanningEngine
    for agent in ("scout", "trending", "brandshield", "personal_watch"):
        for url, channel in (("https://news.ycombinator.com/item?id=8863", "hackernews"),
                             ("https://stackoverflow.com/questions/231767", "stackexchange")):
            plan = SourcePlanningEngine().plan(url, agent=agent, use_llm=False)
            assert any(action.channel == channel and action.operation == "read" for action in plan.actions)


def test_stack_deep_answers_are_separate_attributed_parent_checked_and_bounded(monkeypatch):
    monkeypatch.setattr(community, "_backoff_until", 0.0)
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        assert kwargs["timeout"] <= 5 and kwargs["max_bytes"] == 1_000_000
        if "/answers?" in url:
            return response(url, {"quota_remaining": 4, "has_more": True, "items": [
                {"answer_id": 8, "question_id": 123, "body": "<p>Answer with context.</p>",
                 "owner": {"display_name": "Author"}, "is_accepted": True, "content_license": "CC BY-SA 4.0"},
                {"answer_id": 9, "question_id": 999, "body": "Wrong parent"},
                {"answer_id": 10, "question_id": 123, "body": "Outside sample"},
            ]})
        return response(url, {"quota_remaining": 5, "items": [{
            "question_id": 123, "title": "Question", "body": "Original question", "answer_count": 3,
        }]})
    fragments, _ = acquire_community("stackexchange", "123", operation="read", include_answers=True, http_fetcher=fetch)
    assert len(calls) == 2 and "pagesize=2" in calls[1] and "sort=votes" in calls[1]
    assert len(fragments) == 2 and fragments[0].content == "Original question"
    assert fragments[1].evidence_id == "ev_so_answer_8"
    assert fragments[1].url == "https://stackoverflow.com/a/8"
    assert fragments[1].author == "Author"
    assert fragments[1].raw_metadata["content_license"] == "CC BY-SA 4.0"
    assert fragments[0].raw_metadata["answer_has_more"] is True


@pytest.mark.parametrize("failure", ["backoff", "quota", "timeout"])
def test_stack_deep_backoff_and_failures_preserve_questions(monkeypatch, failure):
    monkeypatch.setattr(community, "_backoff_until", 0.0)
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        if "/answers?" in url:
            if failure == "timeout":
                raise TimeoutError("test-only")
            return response(url, {"items": [], "quota_remaining": 0})
        data = {"items": [{"question_id": 123, "body": "Question preserved", "answer_count": 1}], "quota_remaining": 4}
        if failure == "backoff":
            data["backoff"] = 60
        return response(url, data)
    fragments, _ = acquire_community("stackexchange", "123", operation="read", include_answers=True, http_fetcher=fetch)
    assert len(fragments) == 1 and fragments[0].content == "Question preserved"
    assert len(calls) == (1 if failure == "backoff" else 2)
    assert not fragments[0].raw_metadata["answers_acquired"]
