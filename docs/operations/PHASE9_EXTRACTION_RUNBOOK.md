# Phase 9 acquisition depth and evidence inspection

Maintained checkpoint: 2026-10-15. Implementation is locally validated; overall Phase 9 acceptance remains PARTIAL. See the [handoff](../handoffs/2026-10-15_PHASE9_ACQUISITION_DEPTH.md) for exact results, source snapshots and remaining work. This is not production-launch authorization.

## Scope

The protected set contains 16 operations, not 16 different websites. All remain registered and tested. Reddit/X and the four authoritative channels remain in scope; Hacker News and Stack Overflow are additive community sources, not truth authorities.

| Source | Operations | Useful depth and explicit boundary |
|---|---|---|
| GitHub | `github.read`, `github.issues`, `github.prs`, `github.commits`, `github.releases` | README, issue/release bodies and optional bounded comments/file samples. Not complete repository/history or binary verification. |
| YouTube | `youtube.read`, `youtube.transcript`, `youtube.comments` | Observed metadata, available timed captions and sampled comments. Not video/audio forensics or full discussion coverage. |
| V2EX | `v2ex.latest`, `v2ex.search`, `v2ex.topic`, `v2ex.replies` | Sampled topics/replies. Search is node lookup, not unrestricted full-text search. |
| Web / RSS | `web.read`, `rss.read` | Bounded page content and feed entries; optional one linked-article follow-up. Feed content and acquired article content remain different observations. |
| Xiaoyuzhou | `xiaoyuzhou.podcast`, `xiaoyuzhou.episodes` | Observed identity/episode metadata and show notes. No inferred audio semantics or guaranteed transcripts. |
| Reddit | `reddit.read`, `reddit.comments`, existing search | Existing approved-access policy applies. User confirmed no approved access is configured; retain blocked state and make no requests. |
| X | `twitter.status`, `twitter.profile`, existing search/read | Public-mirror observations are labeled as such. No authenticated identity, complete reply history or global-coverage claim. |
| Hacker News | `hackernews.search`, `hackernews.read` | Disclosed Algolia discovery followed by original Firebase item reads. Deep mode follows at most two direct replies per story; deleted/dead replies are skipped and parent IDs checked. External linked articles are not automatically acquired. |
| Stack Overflow | `stackexchange.search`, `stackexchange.read` | Body-inclusive questions on the explicit `stackoverflow` site. No claim of all Stack Exchange sites, answers or complete discussion. Provider backoff and quota are respected; identical public requests are cached for 60 seconds in-process. |
| SEC / NVD / arXiv / FactCheck | Existing registered operations | SEC contact and FactCheck credentials remain absent. NVD had timeout/503 failures before a later normalized success; NVD/arXiv samples with false network flags do not establish fresh transport proof. arXiv abstracts are not full papers or peer-review certification. |

Provider references: [HN official item API](https://github.com/HackerNews/API), [Algolia HN discovery](https://hn.algolia.com/api), [Stack Exchange search](https://api.stackexchange.com/docs/advanced-search), [body filter](https://api.stackexchange.com/docs/filters), [backoff and caching requirements](https://api.stackexchange.com/docs/throttle). These are contracts to consult, not proof of current uptime. Do not bypass authentication, CAPTCHA, paywalls or access policy.

## Public extraction contract

`POST /api/agent-reach/extract` uses the production native dispatcher. Its synchronous FastAPI handler runs in the worker pool. Platform/operation are checked against executable capabilities; policy, credentials and cooldown decisions are preserved.

Illustrative request, not a recorded response:

```json
{"platform":"hackernews","operation":"read","query":"8863","mode":"deep","limit":2,"max_chars":12000}
```

- `mode`: `quick` or `deep`. Deep enables existing bounded comment/file/article follow-ups where supported; it is not an exhaustive crawl.
- `limit`: 1–5 top-level results. HN deep replies can add at most two records per selected story. The frontend requests two top-level results and limits its follow-up display to 15 records.
- `max_chars`: 1–20,000 where the reader supports it. A generic web read is never labeled complete because it is long.
- Response: status/outcome, observed-network flag, evidence with extraction inspections, aggregate inspection counts, runtime exclusion reason and explicit `claim_support: NOT_ASSESSED` / unknown source completeness.
- HTTP 200 with `SKIPPED`, `AUTH_REQUIRED` or `CONFIG_REQUIRED` is not successful acquisition. Unsupported operations return 422. No raw credentials, provider exception messages or entire metadata dictionaries are exposed by this endpoint.

The additive `extraction` field on unified evidence items is computed by [pure contract inspection](../../backend/schemas/evidence_inspection.py). It contains the hash of the inspected captured text, document/passages IDs, exact captured-text offsets, missing fields, depth, bounded numeric mentions and whitelisted page observations. At most 100,000 captured characters are inspected, eight 600-character chunks shown and twelve numeric mentions sampled. These are observations, not adjudicated financial facts, claim support or calibrated probabilities. An inspection cap is distinct from remote-source truncation and completeness.

## Frontend use

All four agent pages use the shared unified-report renderer. Evidence cards provide expandable passages, acquisition traces, numeric mention context, bounded observed tables/quotes/corrections and sample coverage counts. Missing fields remain visible. Personal Watch's canonical evidence is now retained by its report adapter; generic BrandShield evidence is no longer automatically primary. Missing X engagement stays null rather than invented zero.

“Request bounded source read” chooses an existing operation from an exact hostname and makes an explicit API request. It uses the configured API URL resolver. Returned records are separate follow-up observations; they do not revise the original verdict. Unsafe links are not actionable. Text is escaped, repeated clicks are disabled during the request, nested read buttons are suppressed, and the browser wait ends after 30 seconds. A browser abort does not prove server-side cancellation.

## Repeatable acquisition/evaluation cycle

Run from the intended checkout, not an editable-installed sibling worktree. Use a new output root; scripts refuse to overwrite run directories.

```text
python scripts/audits/run_phase9_extraction_cycle.py --allow-live --rounds 2 --interval-seconds 60 --deep --limit 2 --output-root <new-root>
python scripts/audits/run_phase9_source_api_smoke.py --allow-live --output-root <new-directory>
```

For longer bounded observation use up to ten rounds and an interval of 60–3,600 seconds. This is a repeatable sampling tool, not an installed daemon or automatic self-modifying optimizer. It preserves failed/blocked operations in the denominator, cache/network distinctions, dirty-HEAD disclosure and a fingerprint including untracked implementation files. It stores metrics instead of raw discussion bodies. Do not tune on held-out labels or silently overwrite old results.

Inspect item/character counts, observed fields, discovery-only depth, missing dates/authors, timeouts and policy failures. More captured characters do not demonstrate greater precision, recall or misinformation accuracy. Recall is not measurable without an annotated relevant-document denominator. The protected-operation sample gate is separate from the all-requested-source gate and release acceptance.

## Validation and continuation

Run the [required regression commands](../../AGENTS.md), all Node frontend scripts, frozen-data validation, source API checks and optional browser replay. Browser runner:

```text
python -m http.server 8779 --bind 127.0.0.1 --directory frontend
python scripts/audits/audit_phase9_evidence_inspector.py --base-url http://127.0.0.1:8779 --api-results <recorded-agents-summary.json> --output-root <new-directory>
```

Actual Chromium replay is not a fresh browser-to-provider investigation. Synthetic hostile-response controls are labeled test-only. Manual screen-reader, gradient-contrast acceptance, representative human-adjudicated research accuracy, distributed concurrency and staging rollback remain unverified. Keep protected historical dossiers and frozen benchmark files unchanged; missing source configuration is not permission to fabricate evidence or contact details.
