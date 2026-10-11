"""
Aegis Protocol — Native Agent Reach Doctor Bridge
=================================================
Integrates directly with upstream `agent_reach.doctor` and `agent-reach doctor --json`
to provide live, non-hallucinatory capability state for all internet channels.
"""

import json
import logging
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class DoctorBridge:
    """
    Live runtime capability health monitor backed by upstream Agent Reach.
    Caches doctor checks with a 60-second TTL to avoid redundant subprocess overhead.
    """

    def __init__(self, cache_ttl_seconds: float = 60.0):
        self.cache_ttl = cache_ttl_seconds
        self._cached_results: Optional[Dict[str, Any]] = None
        self._last_check_ts: float = 0.0
        self._observed_results: Dict[str, Dict[str, Any]] = {}

    def check_all(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Execute full doctor diagnostic across all upstream platforms.
        Tries Python in-process call first; falls back to CLI `agent-reach doctor --json`.
        """
        now = time.time()
        if not force_refresh and self._cached_results and (now - self._last_check_ts < self.cache_ttl):
            return self._cached_results

        results = None

        # 1. In-process direct call (fastest, zero subprocess overhead)
        try:
            from agent_reach.config import Config
            from agent_reach.doctor import check_all as upstream_check_all
            config = Config()
            results = upstream_check_all(config)
            logger.debug("[DoctorBridge] Direct in-process doctor check succeeded")
        except Exception as py_err:
            logger.debug(f"[DoctorBridge] In-process doctor probe unavailable: {py_err}")

        # 2. CLI fallback: `agent-reach doctor --json` (only if binary exists in PATH)
        if results is None and shutil.which("agent-reach"):
            try:
                proc = subprocess.run(
                    ["agent-reach", "doctor", "--json"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=2.0
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    results = json.loads(proc.stdout.strip())
                    logger.debug("[DoctorBridge] Subprocess `agent-reach doctor --json` succeeded")
            except Exception as cli_err:
                logger.debug(f"[DoctorBridge] Subprocess doctor check failed: {cli_err}")

        # 3. Resilient baseline if both calls failed (e.g. before initial install)
        if not results:
            results = self._generate_fallback_baseline()

        self._cached_results = results
        self._last_check_ts = now
        return results

    def get_all_status(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """Alias for check_all."""
        return self.check_all(force_refresh=force_refresh)

    def get_channel_status(self, platform: str) -> Dict[str, Any]:
        """Get live health and active backend for a specific platform."""
        plat_lower = platform.lower()
        observation = self._observed_results.get("twitter" if plat_lower == "x" else plat_lower)
        if observation:
            return dict(observation)
        if plat_lower in ("reddit", "twitter", "x"):
            return {
                "status": "not_probed",
                "name": "twitter" if plat_lower in ("twitter", "x") else "reddit",
                "message": "No measured runtime acquisition observation is available",
                "tier": 0,
                "backends": [],
                "active_backend": None,
                "zero_auth": "UNVERIFIED",
                "auth_required": False,
            }

        all_results = self.check_all()
        return all_results.get(platform, {
            "status": "off",
            "name": platform,
            "message": "Platform not registered in upstream Doctor",
            "tier": 1,
            "backends": [],
            "active_backend": None,
        })

    def record_observation(
        self, platform: str, telemetry: Dict[str, Any], fragments: List[Any]
    ) -> None:
        """Record execution-derived health without extrapolating to other operations."""
        canonical = "twitter" if platform.lower() == "x" else platform.lower()
        outcome = str(telemetry.get("outcome", "UNKNOWN"))
        if outcome == "DIRECT_CONTENT":
            status, health = "ok", "HEALTHY"
        elif outcome in {"DIRECT_METADATA", "SYNDICATED_SUMMARY", "PARTIAL_OR_UNCLASSIFIED"}:
            status, health = "warn", "LIMITED"
        elif outcome == "AUTH_REQUIRED":
            status, health = "auth_required", "BLOCKED"
        elif outcome in {"SEARCH_INDEX_DISCOVERY", "EMPTY"}:
            status, health = "degraded", "DEGRADED"
        else:
            status, health = "error", "UNAVAILABLE"
        self._observed_results[canonical] = {
            "status": status,
            "health_class": health,
            "name": canonical,
            "message": f"Last measured operation outcome: {outcome}",
            "active_backend": telemetry.get("backend") if fragments else None,
            "operation": telemetry.get("operation"),
            "outcome": outcome,
            "content_class": telemetry.get("content_class"),
            "network_observed": telemetry.get("network_observed", False),
            "http_statuses": list(telemetry.get("http_statuses", [])),
            "last_verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        from backend.services.agent_reach.native.operation_capabilities import (
            runtime_operation_capabilities,
        )
        runtime_operation_capabilities.record_observation(
            canonical, str(telemetry.get("operation", f"{canonical}.search")), telemetry
        )

    def get_active_backend(self, platform: str) -> Optional[str]:
        """Return the active backend serving this channel, or None if inactive."""
        st = self.get_channel_status(platform)
        return st.get("active_backend")

    def is_channel_ready(self, platform: str) -> bool:
        """True if the channel is marked 'ok' with an active backend."""
        st = self.get_channel_status(platform)
        return st.get("status") == "ok" and bool(st.get("active_backend"))

    def get_canonical_status_code(self, platform: Union[str, Dict[str, Any]]) -> str:
        """
        Map upstream doctor status to Aegis status taxonomy:
        AVAILABLE | DEGRADED | AUTH_REQUIRED | UNAVAILABLE | ERROR | UNKNOWN
        """
        if isinstance(platform, dict):
            st = platform
        else:
            st = self.get_channel_status(platform)
        status = str(st.get("status", "off")).lower()
        msg = str(st.get("message", "")).lower()
        active = st.get("active_backend")

        if status in ("unknown", "not_probed"):
            return "NOT_PROBED"
        if status in ("error", "exception", "failed"):
            return "ERROR"
        if any(auth_kw in msg for auth_kw in ("cookie", "login", "session", "认证", "token", "auth", "credential")) or status == "auth_required":
            return "AUTH_REQUIRED"
        if status == "ok" and active:
            return "AVAILABLE"
        if status in ("warn", "degraded", "limited") or (status == "ok" and not active):
            return "DEGRADED"
        if status in ("off", "unavailable", "disabled"):
            return "UNAVAILABLE"
        return "UNKNOWN"

    def _generate_fallback_baseline(self) -> Dict[str, Dict[str, Any]]:
        """Static baseline for bootstrap scenarios where upstream capability has not been probed yet."""
        return {
            "web": {"status": "not_probed", "active_backend": None, "tier": 0, "message": "Capability not yet probed (bootstrap baseline)"},
            "rss": {"status": "not_probed", "active_backend": None, "tier": 0, "message": "Capability not yet probed (bootstrap baseline)"},
            "v2ex": {"status": "not_probed", "active_backend": None, "tier": 0, "message": "Capability not yet probed (bootstrap baseline)"},
            "bilibili": {"status": "not_probed", "active_backend": None, "tier": 1, "message": "Capability not yet probed (bootstrap baseline)"},
            "youtube": {"status": "not_probed", "active_backend": None, "tier": 0, "message": "Capability not yet probed (bootstrap baseline)"},
            "github": {"status": "not_probed", "active_backend": None, "tier": 0, "message": "Capability not yet probed (bootstrap baseline)"},
        }


# Global singleton instance
DoctorBridgeAlias = DoctorBridge
NativeDoctor = DoctorBridge
native_doctor = DoctorBridge()
