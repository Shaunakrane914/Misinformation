"""
Unit Tests for Doctor Status Taxonomy and Health Semantics
===========================================================
Verifies:
1. Canonical status code taxonomy:
   AVAILABLE | DEGRADED | AUTH_REQUIRED | UNAVAILABLE | ERROR
2. get_canonical_status_code mapping logic:
   - status == 'warn' without auth keywords maps to 'DEGRADED' (NOT 'AUTH_REQUIRED').
   - Auth keywords (token, cookie, session, auth, login, etc.) map to 'AUTH_REQUIRED'.
   - status == 'ok' with active backend maps to 'AVAILABLE'.
   - status == 'ok' without active backend maps to 'DEGRADED'.
   - status in ('error', 'exception', 'failed') maps to 'ERROR'.
   - status in ('off', 'unavailable', 'disabled') maps to 'UNAVAILABLE'.
3. ChannelStatus enum values in backend.services.agent_reach.channels.
"""

import pytest
from unittest.mock import patch

from backend.services.agent_reach.channels import ChannelStatus
from backend.services.agent_reach.native.doctor import DoctorBridge


class TestDoctorStatusTaxonomy:
    """Verifies that ChannelStatus enum contains all canonical values."""

    def test_channel_status_enum_values(self):
        assert ChannelStatus.AVAILABLE.value == "AVAILABLE"
        assert ChannelStatus.DEGRADED.value == "DEGRADED"
        assert ChannelStatus.AUTH_REQUIRED.value == "AUTH_REQUIRED"
        assert ChannelStatus.UNAVAILABLE.value == "UNAVAILABLE"
        assert ChannelStatus.ERROR.value == "ERROR"


class TestDoctorBridgeStatusMapping:
    """Verifies DoctorBridge.get_canonical_status_code across various platform states."""

    def test_warn_maps_to_degraded_not_auth_required(self):
        bridge = DoctorBridge()
        with patch.object(bridge, "get_channel_status") as mock_st:
            mock_st.return_value = {
                "status": "warn",
                "active_backend": "yt-dlp",
                "message": "yt-dlp rate limit notice: performance may be throttled",
            }
            code = bridge.get_canonical_status_code("youtube")
            assert code == "DEGRADED", "Warn status should map to DEGRADED, not AUTH_REQUIRED"

    def test_auth_keywords_map_to_auth_required(self):
        bridge = DoctorBridge()
        with patch.object(bridge, "get_channel_status") as mock_st:
            mock_st.return_value = {
                "status": "warn",
                "active_backend": "twitter_scraper",
                "message": "Missing authentication cookie or bearer token for full access",
            }
            code = bridge.get_canonical_status_code("twitter")
            assert code == "AUTH_REQUIRED"

    def test_ok_with_backend_maps_to_available(self):
        bridge = DoctorBridge()
        with patch.object(bridge, "get_channel_status") as mock_st:
            mock_st.return_value = {
                "status": "ok",
                "active_backend": "Jina Reader",
                "message": "Jina Reader active and reachable",
            }
            code = bridge.get_canonical_status_code("web")
            assert code == "AVAILABLE"

    def test_ok_without_backend_maps_to_degraded(self):
        bridge = DoctorBridge()
        with patch.object(bridge, "get_channel_status") as mock_st:
            mock_st.return_value = {
                "status": "ok",
                "active_backend": None,
                "message": "Provider enabled but no backend assigned",
            }
            code = bridge.get_canonical_status_code("web")
            assert code == "DEGRADED"

    def test_error_maps_to_error(self):
        bridge = DoctorBridge()
        with patch.object(bridge, "get_channel_status") as mock_st:
            mock_st.return_value = {
                "status": "error",
                "active_backend": None,
                "message": "Connection timeout connecting to upstream endpoint",
            }
            code = bridge.get_canonical_status_code("reddit")
            assert code == "ERROR"

    def test_off_maps_to_unavailable(self):
        bridge = DoctorBridge()
        with patch.object(bridge, "get_channel_status") as mock_st:
            mock_st.return_value = {
                "status": "off",
                "active_backend": None,
                "message": "Platform disabled in configuration",
            }
            code = bridge.get_canonical_status_code("tiktok")
            assert code == "UNAVAILABLE"

    def test_social_channel_is_not_green_before_measured_observation(self):
        bridge = DoctorBridge()
        status = bridge.get_channel_status("reddit")
        assert status["status"] == "not_probed"
        assert status["active_backend"] is None
        assert bridge.get_canonical_status_code("reddit") == "NOT_PROBED"

    def test_metadata_observation_is_limited_not_healthy(self):
        bridge = DoctorBridge()
        bridge.record_observation(
            "twitter",
            {
                "outcome": "DIRECT_METADATA",
                "backend": "fxtwitter",
                "operation": "twitter.profile",
                "content_class": "METADATA",
                "network_observed": True,
                "http_statuses": [200],
            },
            [object()],
        )
        status = bridge.get_channel_status("twitter")
        assert status["health_class"] == "LIMITED"
        assert bridge.get_canonical_status_code("twitter") == "DEGRADED"
