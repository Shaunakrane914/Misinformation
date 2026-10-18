"""Offline-only cost controls. No provider calls, keys or real billing."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.core.settings import Settings
from backend.infrastructure.llm.providers.gemini import GeminiProvider
from backend.infrastructure.llm.providers.rate_limit import GeminiRateLimitError, quota_diagnostics
from backend.services.research.evidence_advisor import advisory_call_options


def response(details):
    return SimpleNamespace(status_code=429, headers={}, json=lambda: {"error": {
        "message": "Never export this message: fixture-secret", "details": details}})


def test_small_suggestion_model_is_strict_and_bounded(monkeypatch):
    monkeypatch.delenv("LLM_ADVISORY_MODEL", raising=False)
    options = advisory_call_options(5)
    assert options["model"] == "gemini-3.5-flash-lite"
    assert options["max_output_tokens"] == 160
    assert options["max_attempts"] == 1
    assert options["total_timeout"] == options["timeout"] == 2
    assert options["allow_mock"] is False


def test_quota_details_are_allowlisted_not_provider_messages():
    result = quota_diagnostics(response([
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
            {"quotaId": "GenerateRequestsPerDayPerProject", "quotaValue": "20"}]},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "23023s"},
    ]))
    assert result == {"http_status": 429, "category": "DAILY_QUOTA_EXHAUSTED", "retry_after_seconds": 23023.0}
    assert "fixture-secret" not in str(result)


@pytest.mark.parametrize("value,expected", [("0", "ZERO_CONFIGURED_QUOTA"), ("10", "PER_MINUTE_LIMIT")])
def test_quota_classification(value, expected):
    result = quota_diagnostics(response([{
        "@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
            {"quotaId": "GenerateRequestsPerMinutePerProject", "quotaValue": value}]}]))
    assert result["category"] == expected


def test_default_provider_cannot_send_even_with_credentials(monkeypatch):
    post = Mock()
    monkeypatch.setattr("requests.post", post)
    provider = GeminiProvider(Settings(gemini_api_keys=["fixture-one"]))
    with pytest.raises(RuntimeError):
        provider.generate("suggest", **advisory_call_options())
    post.assert_not_called()


def test_malformed_rate_limit_body_is_still_conservative():
    assert quota_diagnostics(SimpleNamespace(status_code=429))["category"] == "RATE_OR_QUOTA_LIMIT"


def test_profile_only_personal_watch_does_not_invoke_ai(monkeypatch):
    from backend.agents.personal_watch.assessment import synthesize_personal_threats
    forbidden = Mock(side_effect=AssertionError("No AI for profile-only input"))
    monkeypatch.setattr("backend.services.intelligence.call_gemini_text", forbidden)
    result = synthesize_personal_threats({"canonical_name": "Public Person"}, [{
        "evidence_id": "profile", "title": "Profile", "content": "Executive biography",
        "url": "https://x.com/profile", "content_depth": "PROFILE_METADATA"}])
    assert result["threats"] == result["claims"] == []
    forbidden.assert_not_called()
