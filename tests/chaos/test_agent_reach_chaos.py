"""
Aegis Protocol — Automated Chaos & Fault Injection Test Suite
=============================================================
Artificially injects network timeouts, HTTP 429 rate limits, malformed payloads,
and missing backends to verify that Aegis:
  1. Recovers gracefully without unhandled 500 exceptions.
  2. Transitions to fallback backends and records failures in the telemetry trace.
  3. Produces ZERO hallucinated / fabricated evidence when upstream fails.
"""

import unittest
from unittest.mock import MagicMock, patch

from backend.services.agent_reach.adapter import AgentReachService
from backend.services.agent_reach.channels import ChannelStatus, EvidenceFragment
from backend.services.research.research_models import ResearchRequest
from backend.services.research.research_engine import ResearchEngine


class TestAgentReachChaos(unittest.TestCase):
    """Chaos engineering harness testing resilience against failure modes."""

    def setUp(self):
        self.service = AgentReachService()

    def test_twitter_timeout_graceful_recovery(self):
        """Simulate Twitter 15-second upstream timeout; assert clean fallback and zero crash."""
        mock_web_frag = EvidenceFragment(
            platform="web",
            title="Tata Motors Q3 Results",
            content="JLR margin expansion confirmed",
            url="https://tatamotors.com/investors",
            channel_name="web"
        )
        with patch.object(self.service.registry.get_channel("twitter"), "search", side_effect=TimeoutError("Twitter API timeout")):
            with patch.object(self.service.registry.get_channel("web"), "search", return_value=[mock_web_frag]):
                res = self.service.retrieve(
                    query="Tata Motors earnings",
                    domain="financial",
                    channels=["web", "twitter"],
                    limit_per_channel=2,
                    timeout=2.0
                )

                # Assert retrieval completed without throwing
                self.assertIsNotNone(res)
                trace = res.retrieval_trace
                self.assertIn("channels", trace)
                
                # Twitter should be marked unavailable or failed in channel stats
                twitter_stat = trace["channels"].get("twitter", {})
                self.assertTrue(
                    twitter_stat.get("status") in (ChannelStatus.UNAVAILABLE.value, "DEGRADED", "FAILED") or
                    "Timeout" in str(twitter_stat.get("failure_reason")),
                    f"Expected Twitter failure logged, got {twitter_stat}"
                )
                # Ensure no fake Twitter fragments were fabricated
                twitter_frags = [f for f in res.fragments if f.platform.lower() == "twitter"]
                self.assertEqual(len(twitter_frags), 0)

    def test_jina_rate_limit_429_fallback(self):
        """Simulate Jina Reader 429 Too Many Requests; assert fallback to secondary parser."""
        from backend.services.agent_reach.native import native_router
        mock_fallback = {
            "status": "success",
            "title": "Fallback Scraped Article",
            "content": "This is content retrieved via fallback scraper.",
            "markdown": "This is content retrieved via fallback scraper.",
            "url": "https://example.com/breaking-financial-news",
            "fallback_used": True,
            "backend": "Legacy Reach Scraper"
        }
        with patch.object(native_router.executor, "execute_web_read", side_effect=Exception("HTTP 429 Too Many Requests: Rate limit exceeded")):
            with patch("backend.services.agent_reach.native.router._get_legacy_scraper") as mock_get_scraper:
                mock_scraper = MagicMock()
                mock_scraper.read_article_markdown.return_value = mock_fallback
                mock_get_scraper.return_value = mock_scraper

                read_result = self.service.read("https://example.com/breaking-financial-news", max_chars=1000)

                # Assert graceful fallback occurred
                self.assertIsInstance(read_result, dict)
                self.assertEqual(read_result.get("status"), "success")
                self.assertTrue(read_result.get("fallback_used", False))
                self.assertIn("fallback", read_result.get("content", "").lower())

    def test_rss_malformed_xml_recovery(self):
        """Feed corrupted XML/binary payloads to RSS parser; assert zero unhandled exceptions."""
        malformed_bytes = b"<?xml version='1.0'?><rss><channel><title>Broken<item><link>unclosed"
        
        rss_channel = self.service.registry.get_channel("rss")
        if rss_channel:
            with patch("requests.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.content = malformed_bytes
                mock_resp.text = malformed_bytes.decode('utf-8', errors='ignore')
                mock_get.return_value = mock_resp

                # Should not raise exception
                try:
                    fragments = rss_channel.search("test query", limit=5)
                    self.assertIsInstance(fragments, list)
                except Exception as e:
                    self.fail(f"RSS channel raised unhandled exception on malformed XML: {e}")

    def test_complete_network_blackout_zero_hallucinations(self):
        """Simulate total network blackout across all channels; verify zero fabricated evidence."""
        # Force all channels to raise connection errors
        for ch_name in ["web", "news", "reddit", "twitter", "youtube", "github"]:
            ch = self.service.registry.get_channel(ch_name)
            if ch:
                ch.search = MagicMock(side_effect=ConnectionError(f"Simulated network blackout on {ch_name}"))

        res = self.service.retrieve(
            query="Ghost Entity XYZ",
            domain="general",
            channels=["web", "news", "reddit", "twitter"],
            limit_per_channel=2,
            timeout=2.0
        )

        self.assertIsNotNone(res)
        # CRITICAL ASSERTION: No fabricated evidence
        self.assertEqual(len(res.fragments), 0, "System must NEVER fabricate evidence during channel outages")
        self.assertEqual(res.total_signals, 0)


if __name__ == "__main__":
    unittest.main()
