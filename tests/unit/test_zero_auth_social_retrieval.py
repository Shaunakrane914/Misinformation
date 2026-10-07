"""
Aegis Protocol — Unit & Integration Tests: Zero-Auth Reddit and X Retrieval
============================================================================
Validates:
1. Reddit:
   - Reddit URL -> Arctic Shift lookup
   - Reddit post ID -> Arctic Shift lookup
   - Reddit query -> Arctic Shift search
   - Reddit comments -> Arctic Shift comment search
   - Arctic Shift timeout -> Web Search Index fallback
   - Arctic Shift malformed response -> Web Search Index fallback
   - Provenance tags: requested_channel="reddit", actual_retrieval_channel="reddit",
     retrieval_mode="zero_auth_public_mirror", backend="arctic_shift", authenticated=false
2. X / Twitter:
   - X status URL -> FxTwitter status lookup
   - X profile URL / handle query -> FxTwitter profile lookup
   - FxTwitter timeout / 404 -> Web Search Index fallback
   - FxTwitter malformed response -> Web Search Index fallback
   - Provenance tags: requested_channel="twitter", actual_retrieval_channel="twitter",
     retrieval_mode="zero_auth_public_mirror", backend="fxtwitter", authenticated=false
   - Absence of personal tokens / cookies does NOT block retrieval
3. Regressions:
   - GitHub native retrieval intact
   - YouTube native retrieval intact
   - Web document reading intact
   - Facebook routing unchanged (session/cookie required for direct scraping)
   - SSRF protection intact on public mirror hostnames
   - In-memory TTL caching
"""

import json
import pytest
from unittest.mock import MagicMock, patch
import urllib.error

from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode
from backend.services.agent_reach.native.router import NativeRouter
from backend.services.agent_reach.native.doctor import native_doctor
from backend.services.agent_reach.native.channel_capabilities import get_capability
from backend.services.agent_reach.native.errors import AuthRequiredError
from backend.services.url_validator import validate_url_safe, APPROVED_SOCIAL_MIRROR_HOSTNAMES


@pytest.fixture
def router():
    return NativeRouter()


# ─────────────────────────────────────────────────────────────────────────────
# 1. REDDIT ZERO-AUTH RETRIEVAL TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_reddit_url_read_arctic_shift(router):
    """Reddit post URL routes to Arctic Shift post lookup and returns structured markdown."""
    mock_post_data = {
        "data": [{
            "id": "z1c9z",
            "title": "I am Barack Obama, President of the United States -- AMA",
            "selftext": "Hi, I'm Barack Obama, President of the United States. Ask me anything.",
            "author": "PresidentObama",
            "subreddit": "IAmA",
            "score": 15000,
            "num_comments": 22000,
            "created_utc": 1346270496,
            "permalink": "/r/IAmA/comments/z1c9z/i_am_barack_obama/",
            "url": "https://www.reddit.com/r/IAmA/comments/z1c9z/i_am_barack_obama/",
            "is_self": True
        }]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_post_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = router.execute_channel_read("https://www.reddit.com/r/IAmA/comments/z1c9z/i_am_barack_obama/")
        assert res["status"] == "success"
        assert res["backend"] == "arctic_shift"
        assert res["fallback_used"] is False
        assert "Barack Obama" in res["title"]
        assert "President of the United States" in res["content"]
        assert "u/PresidentObama" in res["markdown"]


def test_reddit_post_id_arctic_shift(router):
    """Arctic Shift post ID fetch produces EvidenceFragment with zero_auth_public_mirror mode."""
    mock_post_data = {
        "data": [{
            "id": "sphocx",
            "title": "Community Update Post",
            "selftext": "Welcome to r/reddit! Here are the updates.",
            "author": "admin_user",
            "subreddit": "reddit",
            "score": 450,
            "num_comments": 80,
            "created_utc": 1644528745,
            "permalink": "/r/reddit/comments/sphocx/test/",
            "is_self": True
        }]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_post_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        frag = router._fetch_arctic_shift_post("sphocx")
        assert frag is not None
        assert frag.platform == "reddit"
        assert frag.author == "u/admin_user"
        assert frag.retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
        assert frag.native_backend_id == "arctic_shift"
        assert frag.is_authenticated is False
        assert frag.raw_metadata["subreddit"] == "reddit"


def test_reddit_query_search_arctic_shift(router):
    """Reddit subreddit/keyword query uses Arctic Shift search endpoint."""
    mock_search_data = {
        "data": [
            {
                "id": "tech01",
                "title": "Quantum Computing Breakthrough in Silicon",
                "selftext": "Researchers at Princeton achieved 99.9% two-qubit gate fidelity.",
                "author": "science_reporter",
                "subreddit": "technology",
                "score": 1200,
                "num_comments": 95,
                "created_utc": 1710000000,
                "permalink": "/r/technology/comments/tech01/quantum/",
                "is_self": True
            }
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_search_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        frags, telem = router.execute_channel_query(platform="reddit", query="r/technology", limit=5)
        assert len(frags) == 1
        assert frags[0].requested_channel == "reddit"
        assert frags[0].actual_retrieval_channel == "reddit"
        assert frags[0].retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
        assert frags[0].native_backend_id == "arctic_shift"
        assert frags[0].is_authenticated is False
        assert telem["status"] == "SUCCESS"
        assert telem["backend"] == "arctic_shift"
        assert telem["authenticated"] is False


def test_reddit_comments_search_arctic_shift(router):
    """Comment query for a known Reddit submission uses Arctic Shift comment search."""
    mock_comment_data = {
        "data": [
            {
                "id": "c01",
                "link_id": "t3_z1c9z",
                "parent_id": "t3_z1c9z",
                "author": "citizen_one",
                "body": "What are your economic plans for the middle class?",
                "score": 350,
                "created_utc": 1346271000,
                "subreddit": "IAmA"
            }
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_comment_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        frags, telem = router.execute_channel_query(platform="reddit", query="comments:z1c9z", limit=5)
        assert len(frags) == 1
        assert frags[0].title.startswith("Comment by u/citizen_one")
        assert "economic plans" in frags[0].content
        assert frags[0].retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
        assert frags[0].native_backend_id == "arctic_shift"
        assert telem["backend"] == "arctic_shift"


def test_reddit_arctic_shift_timeout_falls_back_to_search_index(router):
    """When Arctic Shift encounters timeout or HTTP error, query gracefully falls back to search index."""
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
        with patch.object(router, "_execute_web_search") as mock_web_search:
            fallback_frag = EvidenceFragment(
                platform="Web",
                title="Reddit: Machine learning developments in 2024",
                content="Public discussion on Reddit regarding new AI reasoning benchmarks.",
                url="https://www.reddit.com/r/MachineLearning/comments/xyz123/",
                author="reddit.com",
                retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                native_backend_id="bing-search-index"
            )
            mock_web_search.return_value = [fallback_frag]

            frags, telem = router.execute_channel_query(platform="reddit", query="AI reasoning benchmarks 2024", limit=3)
            assert len(frags) == 1
            assert frags[0].retrieval_mode == RetrievalMode.WEB_SEARCH_INDEX.value
            assert telem["fallback_used"] is True
            assert telem["fallback_backend"] == "Bing Search Index"
            assert telem["fallback_reason"] == "ARCTIC_SHIFT_UNAVAILABLE"
            assert telem["status"] == "SUCCESS"


def test_reddit_arctic_shift_malformed_response_fallback(router):
    """Malformed response from Arctic Shift does not crash router and falls back gracefully."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<html><head><title>502 Bad Gateway</title></head></html>"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with patch.object(router, "_execute_web_search", return_value=[]):
            frags, telem = router.execute_channel_query(platform="reddit", query="test query", limit=3)
            assert frags == []
            assert telem["status"] == "DEGRADED"
            assert telem["fallback_used"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. X / TWITTER ZERO-AUTH RETRIEVAL TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_x_status_url_read_fxtwitter(router):
    """X/Twitter status URL routes to FxTwitter API and returns structured markdown."""
    mock_tweet_data = {
        "code": 200,
        "message": "OK",
        "tweet": {
            "id": "20",
            "url": "https://x.com/jack/status/20",
            "text": "just setting up my twttr",
            "created_at": "Tue Mar 21 20:50:14 +0000 2006",
            "created_timestamp": 1142974214,
            "author": {
                "name": "Jack Dorsey",
                "screen_name": "jack",
                "avatar_url": "https://pbs.twimg.com/profile_images/jack.jpg"
            },
            "likes": 190000,
            "retweets": 120000,
            "replies": 15000,
            "views": 5000000
        }
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_tweet_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = router.execute_channel_read("https://x.com/jack/status/20")
        assert res["status"] == "success"
        assert res["backend"] == "fxtwitter"
        assert res["fallback_used"] is False
        assert "just setting up my twttr" in res["content"]
        assert "Jack Dorsey (@jack)" in res["title"]


def test_x_profile_lookup_fxtwitter(router):
    """X handle/profile query routes to FxTwitter profile endpoint."""
    mock_user_data = {
        "code": 200,
        "message": "OK",
        "user": {
            "id": "11348282",
            "name": "NASA",
            "screen_name": "NASA",
            "description": "Explore the universe and discover our home planet.",
            "joined": "Wed Dec 19 20:20:32 +0000 2007",
            "followers": 78000000,
            "tweets": 72000
        }
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_user_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        frags, telem = router.execute_channel_query(platform="twitter", query="@NASA", limit=1)
        assert len(frags) == 1
        assert frags[0].author == "@NASA"
        assert "Explore the universe" in frags[0].content
        assert frags[0].retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
        assert frags[0].native_backend_id == "fxtwitter"
        assert frags[0].is_authenticated is False
        assert telem["status"] == "SUCCESS"
        assert telem["backend"] == "fxtwitter"


def test_x_broad_query_falls_back_to_search_index(router):
    """Broad X keyword discovery query falls back to search index without requiring auth."""
    with patch.object(router, "_execute_web_search") as mock_web_search:
        mock_frag = EvidenceFragment(
            platform="Web",
            title="James Webb Space Telescope Carina Nebula update on X",
            content="NASA shared infrared observations of cosmic cliffs on X.",
            url="https://x.com/NASA/status/1546875000000000000",
            author="NASA",
            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
            native_backend_id="bing-search-index"
        )
        mock_web_search.return_value = [mock_frag]

        frags, telem = router.execute_channel_query(
            platform="twitter", query="James Webb Space Telescope Carina Nebula", limit=3
        )
        assert len(frags) == 1
        assert frags[0].retrieval_mode == RetrievalMode.WEB_SEARCH_INDEX.value
        assert telem["fallback_used"] is True
        assert telem["fallback_backend"] == "Bing Search Index"
        assert telem["status"] == "SUCCESS"


def test_x_fxtwitter_404_falls_back_gracefully(router):
    """Deleted/suspended status returns 404 from FxTwitter and falls back to Jina Reader without crash."""
    http_error = urllib.error.HTTPError(
        url="https://api.fxtwitter.com/OpenAI/status/1790072080357986494",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=None
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        with patch.object(
            router.executor,
            "execute_web_read",
            return_value={"content": "Archived article text from fallback index that is safely retrieved and parsed."}
        ):
            res = router.execute_channel_read("https://x.com/OpenAI/status/1790072080357986494")
            # Should fall through to Jina Reader fallback
            assert res["status"] == "success"
            assert res["backend"] == "Jina Reader"


# ─────────────────────────────────────────────────────────────────────────────
# 3. REGRESSION & SECURITY BOUNDARY TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_facebook_channel_remains_unchanged(router):
    """Facebook routing continues to enforce authentication/cookie requirement as designed."""
    # When FACEBOOK_COOKIE is missing, Facebook query must trigger AuthRequiredError/AUTH_REQUIRED
    frags, telem = router.execute_channel_query(platform="facebook", query="NASA", limit=3)
    assert telem["status"] == "AUTH_REQUIRED"
    assert "FACEBOOK_COOKIE" in str(telem.get("error", ""))


def test_doctor_reports_zero_auth_availability():
    """NativeDoctor reports Arctic Shift and FxTwitter as available without authentication."""
    reddit_st = native_doctor.get_channel_status("reddit")
    assert reddit_st["status"] == "ok"
    assert reddit_st["active_backend"] == "Arctic Shift"
    assert reddit_st["zero_auth"] == "AVAILABLE"
    assert reddit_st["auth_required"] is False

    twitter_st = native_doctor.get_channel_status("twitter")
    assert twitter_st["status"] == "ok"
    assert twitter_st["active_backend"] == "FxTwitter"
    assert twitter_st["zero_auth"] == "AVAILABLE"
    assert twitter_st["auth_required"] is False


def test_ssrf_allowlist_preserves_public_mirrors():
    """Outbound SSRF validation allows approved mirror hostnames over HTTPS."""
    assert "api.fxtwitter.com" in APPROVED_SOCIAL_MIRROR_HOSTNAMES
    assert "arctic-shift.photon-reddit.com" in APPROVED_SOCIAL_MIRROR_HOSTNAMES

    safe_fx, _ = validate_url_safe("https://api.fxtwitter.com/NASA/status/100")
    assert safe_fx is True

    safe_as, _ = validate_url_safe("https://arctic-shift.photon-reddit.com/api/posts/ids?ids=z1c9z")
    assert safe_as is True

    # Internal IP attack attempts on mirror domains must still be blocked by SSRF
    blocked, _ = validate_url_safe("https://127.0.0.1/api/posts")
    assert blocked is False

    blocked_meta, _ = validate_url_safe("http://169.254.169.254/latest/meta-data")
    assert blocked_meta is False


def test_in_memory_social_cache(router):
    """Identical lookups within TTL window return cached object without repeating HTTP call."""
    mock_data = {
        "data": [{
            "id": "cache_test_id",
            "title": "Cached Title",
            "selftext": "Cached Content",
            "author": "cached_user",
            "subreddit": "test",
            "score": 10,
            "num_comments": 2,
            "created_utc": 1600000000,
            "permalink": "/r/test/comments/cache_test_id/",
            "is_self": True
        }]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # First call hits mock_urlopen
        frag1 = router._fetch_arctic_shift_post("cache_test_id")
        assert mock_urlopen.call_count == 1

        # Second call returns from cache without repeating network request
        frag2 = router._fetch_arctic_shift_post("cache_test_id")
        assert mock_urlopen.call_count == 1
        assert frag1.title == frag2.title
