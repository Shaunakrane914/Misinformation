"""
Aegis Protocol — Unit Tests: Capability Registry & Channel Abstraction
========================================================================
Validates:
- Channel registration and unregistration
- Channel health transitions (AVAILABLE, DEGRADED, UNAVAILABLE, AUTH_REQUIRED)
- Health discovery probe mechanism
- Domain-aware and health-aware channel routing
- Capability inventory map serialization
- Graceful handling of optional authenticated channels
"""

import pytest
from typing import List
from backend.services.agent_reach.channels import (
    Channel,
    ChannelStatus,
    EvidenceFragment,
)
from backend.services.agent_reach.registry import CapabilityRegistry
from backend.services.agent_reach.channels_impl import (
    AuthenticatedOptionalChannel,
)


class DummyHealthyChannel(Channel):
    @property
    def name(self) -> str:
        return "dummy_healthy"

    def search(self, query: str, limit: int = 6) -> List[EvidenceFragment]:
        return [
            EvidenceFragment(
                platform="Dummy",
                title=f"Result for {query}",
                content="Mock body",
                url="https://example.com/item1",
                channel_name=self.name,
            )
        ]

    def health_check(self) -> ChannelStatus:
        return ChannelStatus.AVAILABLE


class DummyFailingChannel(Channel):
    @property
    def name(self) -> str:
        return "dummy_failing"

    def search(self, query: str, limit: int = 6) -> List[EvidenceFragment]:
        raise RuntimeError("Channel network failure")

    def health_check(self) -> ChannelStatus:
        return ChannelStatus.UNAVAILABLE


def test_registry_registration_and_lifecycle():
    registry = CapabilityRegistry()
    assert len(registry) == 0

    ch = DummyHealthyChannel()
    registry.register(ch)
    assert len(registry) == 1
    assert "dummy_healthy" in registry.channel_names
    assert registry.get_status("dummy_healthy") == ChannelStatus.AVAILABLE

    registry.unregister("dummy_healthy")
    assert len(registry) == 0
    assert registry.get_status("dummy_healthy") == ChannelStatus.UNAVAILABLE


def test_registry_status_transitions():
    registry = CapabilityRegistry()
    ch = DummyHealthyChannel()
    registry.register(ch)

    # Initial state
    assert registry.get_status("dummy_healthy") == ChannelStatus.AVAILABLE

    # Degrade
    registry.mark_degraded("dummy_healthy")
    assert registry.get_status("dummy_healthy") == ChannelStatus.DEGRADED

    # Unavailable
    registry.mark_unavailable("dummy_healthy")
    assert registry.get_status("dummy_healthy") == ChannelStatus.UNAVAILABLE

    # Recover
    registry.update_status("dummy_healthy", ChannelStatus.AVAILABLE)
    assert registry.get_status("dummy_healthy") == ChannelStatus.AVAILABLE


def test_registry_discovery_probing():
    registry = CapabilityRegistry()
    registry.register(DummyHealthyChannel())
    registry.register(DummyFailingChannel())

    results = registry.discover()
    assert results["dummy_healthy"] == ChannelStatus.AVAILABLE.value
    assert results["dummy_failing"] == ChannelStatus.UNAVAILABLE.value

    # Verify that get_available only returns healthy channels
    available = registry.get_available()
    assert len(available) == 1
    assert available[0].name == "dummy_healthy"


def test_registry_routing_with_platform_filter():
    registry = CapabilityRegistry()
    registry.register(DummyHealthyChannel())

    # Routing all healthy
    routed = registry.route()
    assert len(routed) == 1
    assert routed[0].name == "dummy_healthy"

    # Routing with exclusion filter
    routed_empty = registry.route(requested_channels=["non_existent"])
    assert len(routed_empty) == 0


def test_capability_map_structure():
    registry = CapabilityRegistry()
    registry.register(DummyHealthyChannel())

    cap_map = registry.capability_map()
    assert "dummy_healthy" in cap_map
    info = cap_map["dummy_healthy"]
    assert "status" in info
    assert "last_checked" in info
    assert info["type"] == "DummyHealthyChannel"


def test_optional_authenticated_channel_status():
    channel = AuthenticatedOptionalChannel("linkedin", "LinkedIn", "LINKEDIN_MOCK_SECRET")
    status = channel.health_check()
    assert status == ChannelStatus.AUTH_REQUIRED

    # Searches without token return empty list gracefully
    results = channel.search("tech recruiter")
    assert results == []
