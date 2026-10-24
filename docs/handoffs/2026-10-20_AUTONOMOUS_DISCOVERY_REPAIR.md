# Autonomous discovery repair handoff — 2026-10-20

> Follow-up: [one separately authorized Adobe live check](2026-10-20_ADOBE_POSTFIX_CHECK.md)
> now demonstrates article acquisition, but finds a downstream passage-selection
> defect. The earlier two-case results below are preserved historical observations.

## Start here

Read [AGENTS](../../AGENTS.md), inspect `git status --short` and the complete diff.
Work continues in `.scratch/phase9-remediation-20261016` on
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, with extensive **preserved uncommitted**
October 19 work. No other writer/delegated agent was used this turn.
No commit, push, merge, deployment, secret or access-gate edit.

[Full report and code/function map](../testing/AUTONOMOUS_DISCOVERY_REPAIR_2026-10-20.md)
and [selected measurements](../testing/evidence/2026-10-20_autonomous_discovery/README.md)
are authoritative for this checkpoint. These are engineering conclusions and
command records, not a raw transcript or private reasoning trace.

## Scope, decisions and acceptance

User requested actual autonomous discovery repair, full funnel diagnostics,
deterministic saved replay, bounded live verification and preserved research
integrity. User authorized exactly Scout/Adobe and BrandShield/Dyson once each,
120 seconds and six deep-reader attempts, no AI. **Both ran; authority consumed.**
No more live source cases without a new small proposed request budget.

Implemented request-local provider/candidate observations, same-gate legacy/feed
fallback, bounded observed-hub link continuation, honest transport failures,
HTTP-status propagation, index/asset roles and parent-bounded resolver scheduling.
Keep the existing query planner, title join, topic logic, SSRF, HTTP caps and
operation contracts. See the full report for every changed implementation/test.

**Autonomous live discovery remains NOT ACCEPTED.** Adobe retained 3,012 words
of home/news/index/icon text, not a qualifying publisher article. Its false index
finding is removed on current saved-byte processing. Dyson found relevant wrapper
leads but acquired no bodies: unrelated Bing, Yahoo 500 and one queued resolver.
No global deadline starvation; 68/79 seconds remained respectively. Post-capture
resolver/asset corrections are offline verified, not freshly live proven.

Tradeoffs: keep weak hubs as leads without elevating them to facts; follow only
observed same-host/subdomain URLs; reserve existing attempt slots, not new fan-out;
use remaining read time for a multi-provider resolver chain while keeping body
time and five-second HTTP bounds. Do not restore a rejected search hit via legacy
fallback or accept a headline list simply because it uses `<article>` markup.

## Reproduction and actual gates

Final: **1,532 full / 1,324 fast**, Python 3.13.5; nine Node scripts pass on
v22.17.1. Fatal flake8, frozen verifier and protected diff exit 0. Smoke and
offline persistence/readers pass; historical archive/deployed rollback NOT_VERIFIED.
Six Chromium exact-SSE states pass bounded counts/overflow/page-exception checks.
Zero live AI/model/quota calls. Hosted CI and production parity NOT VERIFIED.
The report records failed iterations, their causes and final timings separately.

Actual commands (run from the implementation worktree):

```text
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m pytest tests/unit/test_autonomous_discovery_funnel.py tests/unit/test_research_pipeline_golden.py -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
node tests/frontend/test_<each-of-nine-files>.js
python scripts/validation/verify_frozen_benchmarks.py
python scripts/validate_release_candidate_smoke.py --output <new-smoke.json>
python scripts/validate_rollback_compatibility.py --output <new-rollback.json>
git diff --exit-code HEAD -- tests/retrieval_benchmark/candidates.jsonl tests/retrieval_benchmark/labels.jsonl tests/retrieval_benchmark/scenarios.jsonl backend/data/dossiers research artifacts scrapers backend/services/agent_reach_scraper.py
git diff --check
```

Native acquisitions used `scripts/audits/run_terminal_agent_quality.py` with
`--allow-live --env-file <server-env> --output-dir <new-temp-live> --case scout:Adobe
--case brandshield:Dyson --timeout-seconds 120 --max-deep-reads 6`.
Do not rerun that live command under consumed authorization.

Offline processing adds `--capture-from <saved-live-directory>` and a new output
directory. Despite the legacy `--allow-live` parser flag, saved mode blocks live
network before app imports; no AI opt-in. Saved read counters are historical
observations, not fresh attempts. Corpus metadata wins over redacted display
metadata; failed attempts export once with `observation_origin: SAVED_CAPTURE`.

`scripts/audits/summarize_discovery_funnel.py --capture-dir <saved-directory>
--output <new-file.json>` imports no app, performs no network and fails if output
exists. It stores the captured version's counters, not current inferred metrics.

Browser replay used `scripts/audits/run_phase9_four_agent_browser_audit.py` with
the same two `--case` flags, `--replay-dir <current-saved-processing>`, an existing
pinned Chart.js asset and new output directory. Real buttons/shared renderers;
readiness stub and all other API calls blocked. Do not claim live UI acquisition.

Temporary basename: `aegis-autonomous-discovery-f0ae999e-a4bc-44b4-a996-aa710f88093f`.
Contains `live`, intermediate reprocessing, final `reprocess-current`, intermediate
browser runs, final `browser-current`, gate logs and isolated storage. No user
credential copied. Temporary data may expire; durable selected proof is linked.

## Next agent

1. Preserve all dirty changes and historical proof; do not stage everything blindly.
2. Read live measurements, nested resolver lifecycle, selected/rejected links and
   captured source roles before changing another timeout or planner.
3. Start with the 27 discovery controls plus existing acquisition/P0/search/golden
   tests. Historical manifests/frozen benchmark labels were not rebaselined.
4. If further live validation is needed, request a tiny explicit case/request
   budget. Prove actual query-discovered article bodies and useful passages;
   counts, headlines, replay and HTTP 200 do not satisfy that requirement.
5. No merge/deployment until separately authorized and verification is sufficient.
   Archive recovery, independent accuracy and production parity remain open.
