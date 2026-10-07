"""
Aegis Protocol — Live Production Smoke Test
Zero-Auth Reddit & X Retrieval Validation
"""

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.agent_reach.native.router import NativeRouter

def run_smoke_test():
    router = NativeRouter()
    print("=" * 60)
    print("RUNNING LIVE ZERO-AUTH SOCIAL SMOKE TEST (PRODUCTION)")
    print("=" * 60)

    test_cases = [
        {
            "channel": "reddit",
            "type": "read",
            "target": "https://www.reddit.com/r/IAmA/comments/z1c9z/i_am_barack_obama_president_of_the_united_states/",
            "desc": "Reddit Post Read (Obama AMA)"
        },
        {
            "channel": "reddit",
            "type": "query",
            "target": "r/technology",
            "desc": "Reddit Subreddit Query (r/technology)"
        },
        {
            "channel": "reddit",
            "type": "query",
            "target": "comments:z1c9z",
            "desc": "Reddit Comments Lookup (Obama AMA post z1c9z)"
        },
        {
            "channel": "twitter",
            "type": "read",
            "target": "https://x.com/jack/status/20",
            "desc": "X Status Read (Jack Dorsey first tweet)"
        },
        {
            "channel": "twitter",
            "type": "read",
            "target": "https://x.com/NASA",
            "desc": "X Profile Read (@NASA)"
        },
    ]

    results = []

    for tc in test_cases:
        print(f"\n--- Testing: {tc['desc']} ---")
        t0 = time.perf_counter()
        if tc["type"] == "read":
            res = router.execute_channel_read(tc["target"])
            latency_ms = int((time.perf_counter() - t0) * 1000)
            status = res.get("status")
            backend = res.get("backend", "unknown")
            content = res.get("content", "")
            content_length = len(content)
            fallback_used = res.get("fallback_used", False)
            retrieval_mode = "zero_auth_public_mirror" if not fallback_used else "search_index_or_reader"
            authenticated = False

            item = {
                "desc": tc["desc"],
                "provider": tc["channel"],
                "backend": backend,
                "authenticated": authenticated,
                "retrieval_mode": retrieval_mode,
                "url": tc["target"],
                "content_length": content_length,
                "latency_ms": latency_ms,
                "fallback_used": fallback_used,
                "status": status,
            }
            results.append(item)

        elif tc["type"] == "query":
            frags, telem = router.execute_channel_query(platform=tc["channel"], query=tc["target"], limit=3)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            status = telem.get("status")
            backend = telem.get("backend", "unknown")
            fallback_used = telem.get("fallback_used", False)
            retrieval_mode = telem.get("retrieval_mode", "unknown")
            authenticated = telem.get("authenticated", False)
            content_length = sum(len(f.content or f.snippet) for f in frags) if frags else 0

            item = {
                "desc": tc["desc"],
                "provider": tc["channel"],
                "backend": backend,
                "authenticated": authenticated,
                "retrieval_mode": retrieval_mode,
                "url": tc["target"],
                "content_length": content_length,
                "latency_ms": latency_ms,
                "fallback_used": fallback_used,
                "status": status,
                "fragment_count": len(frags),
            }
            results.append(item)

        print(f"provider:       {item['provider']}")
        print(f"backend:        {item['backend']}")
        print(f"authenticated:  {item['authenticated']}")
        print(f"retrieval_mode: {item['retrieval_mode']}")
        print(f"url:            {item['url']}")
        print(f"content_length: {item['content_length']}")
        print(f"latency_ms:     {item['latency_ms']}")
        print(f"fallback_used:  {item['fallback_used']}")

    print("\n" + "=" * 60)
    print("LIVE SMOKE TEST COMPLETE")
    print("=" * 60)
    return results

if __name__ == "__main__":
    run_smoke_test()
