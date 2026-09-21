"""
Aegis Protocol — Capability Registry
=====================================
Tracks channel health, routes queries to available channels,
and provides a system-wide capability inventory.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from backend.services.agent_reach.channels import (
    Channel,
    ChannelStatus,
    EvidenceFragment,
)

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """
    Central registry of all internet evidence channels.

    Responsibilities:
    - Register/unregister channels by name
    - Track per-channel health status (AVAILABLE / DEGRADED / UNAVAILABLE / AUTH_REQUIRED)
    - Route queries to healthy channels based on domain affinity and availability
    - Provide a capability inventory for diagnostics endpoints
    """

    def __init__(self):
        self._channels: Dict[str, Channel] = {}
        self._status: Dict[str, ChannelStatus] = {}
        self._last_checked: Dict[str, str] = {}
        logger.info("[CapabilityRegistry] Initialized")

    # ── Registration ──────────────────────────────────────────────────────

    def register(self, channel: Channel) -> None:
        """Register a channel implementation."""
        name = channel.name
        self._channels[name] = channel
        self._status[name] = ChannelStatus.AVAILABLE  # Assume healthy until probed
        logger.info(f"[CapabilityRegistry] Registered channel: {name}")

    def unregister(self, name: str) -> None:
        """Remove a channel from the registry."""
        self._channels.pop(name, None)
        self._status.pop(name, None)
        self._last_checked.pop(name, None)
        logger.info(f"[CapabilityRegistry] Unregistered channel: {name}")

    # ── Status Management ─────────────────────────────────────────────────

    def update_status(self, name: str, status: ChannelStatus) -> None:
        """Update a channel's health status."""
        if name in self._channels:
            old = self._status.get(name)
            self._status[name] = status
            self._last_checked[name] = datetime.utcnow().isoformat()
            if old != status:
                logger.info(f"[CapabilityRegistry] {name}: {old} -> {status}")

    def get_status(self, name: str) -> ChannelStatus:
        """Get current status for a channel."""
        return self._status.get(name, ChannelStatus.UNAVAILABLE)

    def mark_degraded(self, name: str) -> None:
        """Mark a channel as degraded (partial failure)."""
        self.update_status(name, ChannelStatus.DEGRADED)

    def mark_unavailable(self, name: str) -> None:
        """Mark a channel as unavailable (complete failure)."""
        self.update_status(name, ChannelStatus.UNAVAILABLE)

    # ── Discovery & Health Check ──────────────────────────────────────────

    def discover(self) -> Dict[str, str]:
        """
        Probe all registered channels and update their status.

        Returns:
            Dict of channel_name -> ChannelStatus string
        """
        logger.info("[CapabilityRegistry] Running health discovery...")
        results: Dict[str, str] = {}

        for name, channel in self._channels.items():
            try:
                status = channel.health_check()
                self.update_status(name, status)
                results[name] = status.value
            except Exception as e:
                logger.warning(f"[CapabilityRegistry] Health check failed for {name}: {e}")
                self.update_status(name, ChannelStatus.UNAVAILABLE)
                results[name] = ChannelStatus.UNAVAILABLE.value

        healthy = sum(1 for s in results.values() if s == ChannelStatus.AVAILABLE.value)
        logger.info(f"[CapabilityRegistry] Discovery complete: {healthy}/{len(results)} healthy")
        return results

    # ── Routing ───────────────────────────────────────────────────────────

    def get_available(
        self,
        platform_filter: Optional[Set[str]] = None
    ) -> List[Channel]:
        """
        Return channels that are AVAILABLE or DEGRADED.

        Args:
            platform_filter: Optional set of channel names to include.
                             If None, returns all healthy channels.
        """
        healthy_statuses = {ChannelStatus.AVAILABLE, ChannelStatus.DEGRADED}
        channels = []

        for name, channel in self._channels.items():
            if self._status.get(name) not in healthy_statuses:
                continue
            if platform_filter and name not in platform_filter:
                continue
            channels.append(channel)

        return channels

    def route(
        self,
        requested_channels: Optional[List[str]] = None
    ) -> List[Channel]:
        """
        Select channels for a query based on requested channels and health.

        Args:
            requested_channels: Specific channels to use.
                                If None, all healthy channels are returned.
        """
        if requested_channels:
            return self.get_available(set(requested_channels))
        return self.get_available()

    # ── Diagnostics ───────────────────────────────────────────────────────

    def capability_map(self) -> Dict[str, Dict]:
        """
        Return a full capability inventory for API diagnostics.

        Returns:
            Dict of channel_name -> {status, last_checked, type}
        """
        result = {}
        for name in self._channels:
            result[name] = {
                "status": self._status.get(name, ChannelStatus.UNAVAILABLE).value,
                "last_checked": self._last_checked.get(name, "never"),
                "type": type(self._channels[name]).__name__,
            }
        return result

    @property
    def channel_names(self) -> List[str]:
        """List all registered channel names."""
        return list(self._channels.keys())

    def __len__(self) -> int:
        return len(self._channels)

    def __repr__(self) -> str:
        healthy = sum(
            1 for s in self._status.values()
            if s in (ChannelStatus.AVAILABLE, ChannelStatus.DEGRADED)
        )
        return f"<CapabilityRegistry channels={len(self._channels)} healthy={healthy}>"
