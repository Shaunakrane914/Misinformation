# P0 autonomous overhaul continuation — 2026-10-20

[Detailed report, code map and live failures](../testing/P0_AUTONOMOUS_RESEARCH_OVERHAUL_2026-10-20.md)
· [Five-case measurements](../testing/evidence/2026-10-20_p0_overhaul/live-funnel.json)
· [Actual Gemini usage](../testing/evidence/2026-10-20_p0_overhaul/live-summary.json).

## State and scope

User explicitly authorized implementation, a bounded fresh original-five batch,
and three optional short Gemini suggestion calls. A separate reply authorized
one AI-disabled Samsung post-fix request. All six investigations and all three
Gemini calls are consumed. No further sweeps/retries or generation without new
scope. No push, merge, deployment, access-gate or credential changes.

Branch `fix/p0-lenovo-acquisition-20261018`, base HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, isolated worktree
`.scratch/phase9-remediation-20261016`, plus a large preserved dirty implementation.
Read AGENTS and inspect current status/diff before continuing. Do not restore or
overwrite inherited changes, frozen data, historical dossiers, research/artifacts,
working scrapers or compatibility shims.

## Implemented

Token-aware subreddit routing; root URL/exact-body deduplication with aliases;
reference background exclusion; provisional undated Trending reads followed by
strict acquired-page/date qualification; publisher-title reconciliation retained.
Bounded observed RSS/Atom/sitemap and public same-publisher GET form discovery;
raw indexes never findings. Reader slots reserve publisher/feed/article fallback,
financial event titles prioritized. New parser reuses fetched bytes, rejects
DTD/entities and does not infer publication from sitemap lastmod.

Optional one-query advice uses the existing planner validator, gateway, first
credential, exact `gemini-3.5-flash-lite` identity, SQLite reservation ledger and
cooldown. Model verified with one capability GET before the live batch. Three
actual 200 generation responses: 90/51/48 output tokens, 1,365 total provider
tokens. No AI conclusions, model/key fallback or generation retry. Final audit
telemetry is per investigation plus a separate batch ledger summary.

See [25 offline controls](../../tests/unit/test_p0_source_overhaul.py). Historical
golden fixture files are unchanged; only additive advisory diagnostics are
excluded from the old hash projection, separately tested. The complete mocked
hub/feed/article path and blocked-first-publisher replacement stay within their
existing total attempt caps; neither proves live availability.

## What remains broken

**Live research acceptance NOT MET.** Main batch: Samsung only Yahoo hub; Unilever
observation 504 across a large host-time interruption; Adidas no candidates with
transport/security failures; Trending attempted an undated lead but SSRF-rejected;
Sundar only nine-word profile metadata. Zero newly qualified articles. Real Gemini
inference succeeded, not research. Earlier Adobe success is a historical single
case, not substituted into this matrix.

Unilever's host log gap spans 06:46:34–10:52:00. Kernel-Power events support host
interruption but exact full-gap cause is unverified. Late temp dossier records
deadline-exhausted acquisition failure; do not count it as the missing result.
Later passive DNS/URL checks passed for queried search hosts; do not claim the
observed transient security/transport failures are proven permanent provider
access restrictions. Never bypass validation to force a result.

Additional Samsung request: earnings candidate correctly first, two unresolved
publisher lookups, `news.samsung.com` returns HTTP 403, 32.35s, no AI/body/findings.
After that, two-publisher feed/article slot allocation was corrected **offline**
and unit-tested only. A new live matrix would require new authorization and a
stable awake host. Production verification is not recommended yet.

## Reproduce and verify

Final closeout: **1,580 full tests / 61.93s**, **1,372 fast / 44.77s**, both exit 0.
Focused substantive/funnel/overhaul suite: 75 pass. Fatal lint zero; all nine
Node suites, frozen verifier/protected diff, smoke and offline persistence checks
exit 0. Historical archive/deployed rollback remain NOT_VERIFIED. No final browser
or hosted CI run. Earlier full tests failed on the new feed discovery eligibility
and additive golden diagnostics; fixes and actual commands are in the report.

The detailed report owns the final command/results record. Full source events,
logs and temporary dossiers live under system-temp basename
`aegis-p0-overhaul-7bfe8bdb5d464f3490946f0761ab4d6d`; selected sanitized hashes/
measurements are durable. `saved-replay` was network-blocked and is not live
discovery. `live` and `samsung-postfix` are distinct authorized observations with
different application fingerprints; don't rewrite them to final-code outcomes.

Normal tests must keep AI off/mocked and outputs temporary. Live runner's
`--allow-live-ai` is separate opt-in, requires capability verification and opens
one shared max-three-call scope for at most five cases. It must never be enabled
merely to make standard tests pass. No final browser/production/hosted CI or
historical recovery guarantee. Preserve all failed captures and uncertainty.
