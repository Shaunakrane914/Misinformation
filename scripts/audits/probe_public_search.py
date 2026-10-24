"""At most three top-level public fetches to inspect search drift; no app or AI.

Explicit live opt-in, safe transport, one attempt per request, fresh temp output.
Captured HTML is untrusted diagnostic data, never executed or source evidence.
"""
import argparse
import json
import re
from pathlib import Path
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--news-only", action="store_true", help="One existing Bing News RSS request instead of the three web probes")
    parser.add_argument("--observed-url", help="One already observed public wrapper URL, protected by the normal HTTP validator")
    parser.add_argument("--html-alternative", action="store_true", help="One DuckDuckGo non-JavaScript public search request")
    args = parser.parse_args()
    if not 4 <= len(args.query) <= 200:
        parser.error("Query must be 4..200 characters")
    if re.search(r"(?:api_?key|token|secret|password|cookie)\s*[:=]", args.query + " " + (args.observed_url or ""), re.I):
        parser.error("Public diagnostic queries/URLs must not contain credentials")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    from bs4 import BeautifulSoup
    from backend.infrastructure.acquisition.network.http import fetch_public_http, decode_bounded_http_body
    observations = []
    probes = (
        ("bing", args.query, "https://www.bing.com/search", "q", "li.b_algo"),
        ("bing-quoted", '"' + args.query.replace('"', '') + '"', "https://www.bing.com/search", "q", "li.b_algo"),
        ("yahoo", args.query, "https://search.yahoo.com/search", "p", "div.algo"),
    )
    if args.news_only:
        probes = (("bing-news", args.query, "https://www.bing.com/news/search", "q", "item"),)
    if args.observed_url:
        probes = (("observed-wrapper", args.query, args.observed_url, "q", "a[href]"),)
    if args.html_alternative:
        probes = (("duckduckgo-html", args.query, "https://html.duckduckgo.com/html/", "q", ".result"),)
    for name, query, base, parameter, selector in probes:
        url = args.observed_url or base + "?" + urlencode({parameter: query, **({"format": "rss"} if args.news_only else {})})
        row = {"provider": name, "requested_query": query}
        try:
            response = fetch_public_http(url, timeout=5.0, max_bytes=1_000_000, max_attempts=1,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"})
            body = decode_bounded_http_body(response)
            (args.output_dir / (name + ".html.txt")).write_bytes(body)
            soup = BeautifulSoup(body, "xml" if args.news_only else "html.parser")
            field = soup.select_one(f'input[name="{parameter}"]')
            row.update(status=response.status_code, endpoint=response.endpoint,
                query_field=field.get("value") if field else None,
                page_title=soup.title.get_text(" ", strip=True) if soup.title else None,
                results=[item.get_text(" ", strip=True)[:700] for item in soup.select(selector)[:5]])
            if args.observed_url:
                row.update(redirect_chain=response.redirect_chain,
                    canonical=[node.get("href") for node in soup.select('link[rel="canonical"]')],
                    links=[{"text": node.get_text(" ", strip=True)[:100], "url": node.get("href")}
                           for node in soup.select("a[href]")[:10]])
        except Exception as exc:
            row.update(error_type=type(exc).__name__, http_status=getattr(exc, "status_code", None))
        observations.append(row)
        print(json.dumps(row, ensure_ascii=True), flush=True)
    (args.output_dir / "observations.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
