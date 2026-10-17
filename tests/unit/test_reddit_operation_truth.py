"""Keep comment operations and removed markers from inflating text acquisition."""
from types import SimpleNamespace

from backend.infrastructure.acquisition.routing.social_handlers import SocialChannelHandlers
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.native.normalizer import NativeNormalizer


def test_comments_operation_never_returns_post_body_or_resolves_unrelated_subreddits():
    calls = []
    comment = EvidenceFragment(platform="reddit", content="Observed comment", content_depth="COMMENT")
    router = SimpleNamespace(use_arctic_shift=True,
        _fetch_arctic_shift_comments=lambda post_id, *args: calls.append(post_id) or [comment])
    handler = SocialChannelHandlers(router)
    handler._mark_mirror_success = lambda fragments, *args: None
    result = handler._execute_reddit(
        "https://www.reddit.com/r/IAmA/comments/z1c9z/example/", 2, "q", "direct", "source", {}, {"operation": "comments"})
    assert result == [comment] and calls == ["z1c9z"]


def test_comments_operation_requires_a_thread_and_does_not_fallback_to_search():
    handler = SocialChannelHandlers(SimpleNamespace(use_arctic_shift=True))
    telemetry = {}
    result = handler._execute_reddit("unrelated topic", 2, "q", "direct", "source", telemetry, {"operation": "comments"})
    assert not result and telemetry["status"] == "FAILED"


def test_removed_comment_is_a_metadata_observation_not_raw_prose():
    fragment = NativeNormalizer.normalize_arctic_shift_comments([
        {"id": "a1", "link_id": "t3_z1c9z", "body": "[removed]"}
    ])[0]
    assert fragment.content == "" and fragment.snippet == ""
    assert fragment.content_depth == "METADATA"
    assert fragment.raw_metadata["observed_body_marker"] == "[removed]"


def test_actual_comment_is_not_labeled_a_full_article_based_on_length():
    body = "Observed discussion context. " * 30
    fragment = NativeNormalizer.normalize_arctic_shift_comments([
        {"id": "a1", "link_id": "t3_z1c9z", "body": body}
    ])[0]
    assert fragment.content == body and fragment.content_depth == "COMMENT"


def test_comment_fetch_uses_bounded_transport_and_rejects_wrong_parent(monkeypatch):
    import json
    from backend.infrastructure.acquisition.adapters.social import reddit
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    calls = []
    def fetch(url, **kwargs):
        calls.append(kwargs)
        payload = {"data": [{"id": "a", "link_id": "t3_z1c9z", "body": "Observed reply"},
                            {"id": "b", "link_id": "t3_other", "body": "Wrong parent"}]}
        return BoundedHTTPResponse(json.dumps(payload).encode(), url, 200, "application/json", {}, 1, 1)
    monkeypatch.setattr(reddit, "fetch_public_http", fetch)
    fragments = reddit.fetch_arctic_shift_comments("z1c9z", 2, cache_get=lambda key: None, cache_set=lambda *a: None)
    assert len(fragments) == 1 and fragments[0].content == "Observed reply"
    assert calls[0]["timeout"] <= 5 and calls[0]["max_bytes"] == 1_000_000


def test_invalid_comment_target_makes_no_network_request(monkeypatch):
    from backend.infrastructure.acquisition.adapters.social import reddit
    def forbidden(*args, **kwargs):
        raise AssertionError("No transport for invalid target")
    monkeypatch.setattr(reddit, "fetch_public_http", forbidden)
    assert reddit.fetch_arctic_shift_comments("bad&link_id=other") == []
