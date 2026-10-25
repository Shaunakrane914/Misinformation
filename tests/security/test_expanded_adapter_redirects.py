"""Offline redirect-policy controls; no provider requests or access approval."""
import pytest

from backend.infrastructure.acquisition.adapters import expansion_safety as safety
from backend.infrastructure.acquisition.network import http as transport


@pytest.mark.parametrize("target", [
    "https://www.reddit.com/r/example/comments/observed",
    "https://arctic-shift.photon-reddit.com/api/posts/search",
    "https://www.sec.gov/Archives/observed",
    "https://other-publisher.example/article",
])
@pytest.mark.parametrize("requested_redirects", [None, 4])
def test_expanded_adapter_never_transmits_unapproved_redirect(target, requested_redirects, monkeypatch):
    monkeypatch.delenv("REDDIT_APPROVED_ACCESS", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.setattr(safety, "validate_url_safe", lambda _: (True, ""))
    monkeypatch.setattr(transport, "is_safe_url", lambda _: (True, ""))
    monkeypatch.setattr(safety, "_fetch", transport.fetch_public_http)
    transmitted = []
    handlers_seen = []

    def opener(*handlers):
        redirect = next(handler for handler in handlers if isinstance(handler, transport._ValidatingRedirectHandler))
        handlers_seen.append(redirect)

        class MockOpener:
            def open(self, request, timeout):
                assert timeout > 0
                transmitted.append(request.full_url)
                follow = redirect.redirect_request(request, None, 302, "Found", {}, target)
                if follow is not None:
                    transmitted.append(follow.full_url)
                raise RuntimeError("Mock transport stopped; no real network permitted")

        return MockOpener()

    monkeypatch.setattr(transport.urllib.request, "build_opener", opener)
    kwargs = {} if requested_redirects is None else {"max_redirects": requested_redirects}
    start = "https://www.bbc.com/news/observed"
    with pytest.raises(RuntimeError, match="Bounded adapter transport failed"):
        safety.safe_fetch(start, **kwargs)
    assert transmitted == [start]
    assert len(handlers_seen) == 1
    assert handlers_seen[0].max_redirects == 0
