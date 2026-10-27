# Expanded scraper fleet — made to actually scrape & wired into discovery — 2026-10-26

**Branch (IDE checkout):** `feat/phase8-real-acquisition-proof`. **Not committed, not pushed.**
**Scope:** user reported ~60 added source sites "couldn't scrape them". Diagnosed the fleet live,
repaired the genuinely broken adapters, wired working adapters into both the discovery and read
paths, and verified real article bodies are scraped end-to-end. No frozen data, dossier, research
or artifact tree was touched. This is a local live diagnosis, not production or hosted-CI proof.

## What was actually wrong (reproduced live, not assumed)

Probing every adapter with real queries (`scripts/`-style one-off harness, bounded/polite) showed:

| Adapter | Before | Cause found live (2026-10-26) |
| --- | --- | --- |
| wikipedia / yahoo_finance / wikidata_exec / arxiv / hackernews | worked in isolation | **not registered for discovery routing** (hackernews, arxiv) |
| news_wires | 0 candidates | `reutersagency.com` feed **404 (decommissioned)**; `pib.gov.in/RssMain.aspx` serves HTML |
| substack | 0 candidates | posts API works, but discovery matched only the whole phrase across 8 fixed pubs |
| bluesky | 0 candidates (silent) | `public.api.bsky.app` `searchPosts` now returns **HTTP 403 (auth required)** |
| trustpilot | acquire error | Trustpilot blocks automated fetch (provider 403); not resolvable without a stealth/paid fetcher |
| reddit_deep / factcheck / sec_edgar / sec_filings_full | 0 (instant) | **config/policy gated** — need env vars, not code fixes |

Root integration gap: the deterministic `SourcePlanningEngine` never emitted an `expanded_sources`
action, so in this checkout the whole fleet was only reachable on the *read* path (a matching host
surfaced by normal discovery), never as a discovery source. That is the core reason investigations
"couldn't scrape them".

## Changes (all uncommitted)

- [`news/wires_adapter.py`](../../backend/infrastructure/acquisition/adapters/news/wires_adapter.py):
  replaced dead Reuters/PIB feeds with verified direct, zero-auth tier-1 feeds returning **real
  article URLs** (BBC world/business/tech, Guardian world/business/tech, Al Jazeera, Ars Technica,
  The Verge, NPR business); bounded to 6 feeds/call; keyword-filtered. Google News RSS search was
  evaluated and **rejected**: its `/rss/articles/` links are opaque `AU_yq…` tokens that are not
  decodable to a real URL without a fragile internal Google API, so they would be unreadable leads.
- [`news/substack.py`](../../backend/infrastructure/acquisition/adapters/news/substack.py):
  relaxed discovery to match the whole phrase OR any ≥4-char query token; `limit=12`; +4 publications.
- [`expanded_catalog.py`](../../backend/infrastructure/acquisition/adapters/expanded_catalog.py):
  registered `hackernews` and `arxiv` (both verified scraping) so they route on the read path;
  repointed Trending/Personal discovery off the dead Bluesky endpoint. (`DOMAIN_DISCOVERY` is unused
  in this checkout; the live mapping lives in the planner below.)
- [`source_planner.py`](../../backend/services/agent_reach/source_planner.py): every plan now emits
  up to two bounded `expanded_sources` discovery actions — a domain specialist plus tier-1 news:
  financial→`yahoo_finance`+`news_wires`, identity/personal→`wikidata_exec`+`news_wires`,
  technical/trending→`hackernews`+`news_wires`, brand/general→`wikipedia`+`news_wires`. Leads still
  require a separate budgeted, SSRF-safe read and are never treated as evidence here.
- Tests updated to the corrected contract:
  [`test_expansion_safety_and_wiring.py`](../../tests/unit/test_expansion_safety_and_wiring.py),
  [`test_source_planning_engine.py`](../../tests/unit/test_source_planning_engine.py).

## Verified live (local, bounded, no AI, no paid readers)

- Full `plan() → to_channel_queries() → retrieve_many()` dispatch now runs the fleet:
  scout→yahoo_finance (3 leads), brand→wikipedia (3), personal→wikidata_exec+Guardian (4),
  trending→BBC (1). All `expanded_sources` query records return SUCCESS or a truthful FAILED.
- End-to-end reads via the real reader returned real bodies: BBC 12k/8.6k chars, Guardian 7.6k,
  and a BBC battery-recycling article captured at 434k chars; wikipedia 25k, yahoo 11.8k, arxiv 1.8k.
- Targeted tests green: adapter + wiring 36/36; fleet adapters 15/15; planner 9/10.
  The one failure, `test_auth_only_scope_returns_no_false_executable_plan`, **also fails on the
  unmodified planner** (a pre-existing LLM-gateway warning-ordering issue in this checkout) — not
  caused by this work. Fatal flake8 (E9/F63/F7/F82) on changed files: 0.

## Still gated / not fixed (truthful)

- **Config/credentials required** (no code fix): `SEC_USER_AGENT` (SEC EDGAR — contact string of the
  owner's choice, used at ≤10 req/s), `GOOGLE_FACTCHECK_API_KEY` (Fact Check), `REDDIT_APPROVED_ACCESS`
  (deep Reddit). Setting these turns those sources on; the channel already fails honestly when unset.
- **Bluesky** public search needs auth (403) and is no longer used for discovery; it remains a read
  specialist for `bsky.app` URLs.
- **Trustpilot** actively blocks automated fetch; not scrapable here without a different fetch path.
- Telegram remains acquire-only (needs a specific `t.me` channel URL), by design.

Full-suite regression, hosted CI, and a live four-agent investigation were not run in this pass.
