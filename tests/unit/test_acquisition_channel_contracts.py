"""Offline contracts for every advertised acquisition capability."""

import pytest

from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.native.channel_capabilities import CAPABILITY_MATRIX
from backend.services.agent_reach.native.router import NativeRouter


EXPECTED_CHANNELS = {
    "web", "web_search", "github", "youtube", "bilibili", "v2ex", "rss",
    "twitter", "reddit", "xueqiu", "linkedin", "xiaohongshu", "facebook",
    "instagram", "boss", "xiaoyuzhou",
}

AUTHENTICATED_CHANNELS = {
    "linkedin", "xueqiu", "xiaohongshu", "facebook", "instagram", "boss",
    "xiaoyuzhou",
}

EXPLICIT_STANDARD_CHANNELS = {
    "web", "github", "youtube", "bilibili", "v2ex", "rss",
}


def test_canonical_and_legacy_service_exports_have_object_identity():
    from backend.infrastructure import acquisition
    from backend.infrastructure.acquisition.service import (
        AcquisitionService,
        AgentReachService,
        agent_reach_service,
    )
    from backend.services.agent_reach import (
        AgentReachService as LegacyPackageService,
        agent_reach_service as legacy_singleton,
    )
    from backend.services.agent_reach.adapter import AgentReachService as LegacyModuleService

    assert AcquisitionService is AgentReachService
    assert acquisition.AcquisitionService is AgentReachService
    assert acquisition.AgentReachService is AgentReachService
    assert LegacyPackageService is AgentReachService
    assert LegacyModuleService is AgentReachService
    assert legacy_singleton is agent_reach_service


def test_linkedin_credential_contract_is_consistent_at_registration():
    from backend.infrastructure.acquisition.service import agent_reach_service

    channel = agent_reach_service.registry.get("linkedin")
    assert channel.auth_env_var == "LINKEDIN_COOKIE"


def test_capability_matrix_has_the_complete_advertised_channel_set():
    assert set(CAPABILITY_MATRIX) == EXPECTED_CHANNELS


@pytest.mark.parametrize("channel", sorted(EXPECTED_CHANNELS))
def test_every_advertised_channel_has_a_valid_contract(channel):
    capability = CAPABILITY_MATRIX[channel]
    assert capability.platform == channel
    assert capability.operations
    assert capability.backends
    assert capability.auth_mode in {"none", "cookie_required", "session_required", "api_key", "browser_cdp"}
    assert isinstance(capability.cloud_safe, bool)


@pytest.mark.parametrize("channel", sorted(AUTHENTICATED_CHANNELS))
def test_session_gated_channels_fail_explicitly_without_credentials(monkeypatch, channel):
    router = NativeRouter()
    monkeypatch.delenv("LINKEDIN_COOKIE", raising=False)
    monkeypatch.delenv("XUEQIU_COOKIE", raising=False)
    monkeypatch.delenv("XIAOHONGSHU_COOKIE", raising=False)
    monkeypatch.delenv("FACEBOOK_COOKIE", raising=False)
    monkeypatch.delenv("INSTAGRAM_COOKIE", raising=False)
    monkeypatch.delenv("BOSS_CDP_PORT", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    fragments, telemetry = router.execute_channel_query(channel, "contract fixture", limit=1)
    assert fragments == []
    assert telemetry["status"] == "AUTH_REQUIRED"
    assert telemetry["error"]


@pytest.mark.parametrize("channel", sorted(EXPECTED_CHANNELS))
def test_every_channel_uses_the_declared_dispatch_family(monkeypatch, channel):
    router = NativeRouter()
    social_result = [EvidenceFragment(platform="Fixture", title="social")]
    standard_result = [EvidenceFragment(platform="Fixture", title="standard")]

    def social_execute(*args, **kwargs):
        args[6].update(status="SUCCESS", backend="fixture-social")
        return social_result

    def standard_execute(*args, **kwargs):
        args[6].update(status="SUCCESS", backend="fixture-standard")
        return standard_result

    monkeypatch.setattr(router.channel_dispatcher.social, "execute", social_execute)
    monkeypatch.setattr(router.channel_dispatcher.standard, "execute", standard_execute)

    fragments, telemetry = router.execute_channel_query(channel, "controlled fixture", limit=1)
    expected = social_result if channel in {"reddit", "twitter"} else standard_result
    assert fragments is expected
    assert telemetry["status"] == "SUCCESS"
    assert telemetry["platform"] == channel
    assert telemetry["operation"] == f"{channel}.search"


@pytest.mark.parametrize("channel", sorted(EXPECTED_CHANNELS))
def test_every_channel_selects_its_concrete_handler(monkeypatch, channel):
    """Exercise the second-level route, not only social-versus-standard dispatch."""
    router = NativeRouter()
    marker = EvidenceFragment(platform="Fixture", title=channel, channel_name=channel)
    standard = router.channel_dispatcher.standard

    if channel in {"reddit", "twitter"}:
        monkeypatch.setattr(
            router.channel_dispatcher.social,
            "execute",
            lambda *args, **kwargs: [marker],
        )
    elif channel in AUTHENTICATED_CHANNELS:
        monkeypatch.setattr(
            standard,
            "_execute_authenticated",
            lambda platform, telemetry: [marker],
        )
    elif channel in EXPLICIT_STANDARD_CHANNELS:
        monkeypatch.setattr(
            standard,
            f"_execute_{channel}",
            lambda *args, **kwargs: [marker],
        )
    else:
        # web_search is intentionally the generic discovery route. No fake
        # native integration is advertised for it.
        assert channel == "web_search"
        monkeypatch.setattr(
            standard,
            "_execute_generic",
            lambda *args, **kwargs: [marker],
        )

    fragments, telemetry = router.execute_channel_query(channel, "controlled fixture", limit=1)
    assert fragments == [marker]
    assert fragments[0].requested_channel == channel
    assert fragments[0].actual_retrieval_channel == channel
    assert telemetry["platform"] == channel


@pytest.mark.parametrize("channel", sorted(EXPECTED_CHANNELS))
def test_every_channel_fails_closed_on_unexpected_handler_error(monkeypatch, channel):
    """A backend exception must become explicit telemetry, never fabricated evidence."""
    router = NativeRouter()

    def fail(*args, **kwargs):
        raise RuntimeError(f"{channel} fixture failure")

    handler = (
        router.channel_dispatcher.social
        if channel in {"reddit", "twitter"}
        else router.channel_dispatcher.standard
    )
    monkeypatch.setattr(handler, "execute", fail)

    fragments, telemetry = router.execute_channel_query(channel, "controlled fixture", limit=1)
    assert fragments == []
    assert telemetry["status"] == "FAILED"
    assert telemetry["fallback_used"] is False
    assert telemetry["error"] == f"{channel} fixture failure"


def test_router_forwards_context_and_read_options_to_dispatcher(monkeypatch):
    router = NativeRouter()
    captured = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return [], {"status": "SUCCESS"}

    monkeypatch.setattr(router.channel_dispatcher, "execute", capture)
    router.execute_channel_query(
        "jina_reader",
        "fixture",
        domain="finance",
        entity="Acme",
        url="https://example.com/report",
        max_chars=1234,
    )

    assert captured["domain"] == "finance"
    assert captured["entity"] == "Acme"
    assert captured["url"] == "https://example.com/report"
    assert captured["max_chars"] == 1234


def test_web_search_exception_uses_deterministic_legacy_fallback(monkeypatch):
    router = NativeRouter()
    fallback = EvidenceFragment(platform="Web", title="fallback", channel_name="web")
    monkeypatch.setattr(
        router,
        "_execute_web_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("search unavailable")),
    )
    monkeypatch.setattr(router, "_fallback_web_scraper", lambda *args, **kwargs: [fallback])

    fragments, telemetry = router.execute_channel_query("web", "controlled fixture", limit=1)

    assert fragments == [fallback]
    assert telemetry["status"] == "SUCCESS"
    assert telemetry["fallback_used"] is True
    assert telemetry["fallback_backend"] == "Legacy Web Scraper"
    assert telemetry["fallback_reason"] == "BING_SEARCH_UNAVAILABLE"
    assert fragments[0].requested_channel == "web"
    assert fragments[0].actual_retrieval_channel == "web"
