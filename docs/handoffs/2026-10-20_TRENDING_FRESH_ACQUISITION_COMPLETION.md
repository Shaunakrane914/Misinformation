# Trending fresh acquisition and source handoff — 2026-10-20

Read [the report](../testing/TRENDING_FRESH_ACQUISITION_COMPLETION_2026-10-20.md),
[selected proof](../testing/evidence/2026-10-20_trending_completion/README.md), AGENTS
and current status/diff before editing. Earlier zero-current-source reports are
historical. User asked to complete Trending, not deploy or rewrite architecture.

Worktree `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus extensive preserved dirty work.
No staging, commit, push, merge, deployment, credentials/access change or protected
data repair. Do not clean or overwrite inherited implementation.

## Code map and rationale

- `backend/services/research/harvesting.py`: Trending title fit/observed publisher
  diversity, exact observed alternate hubs within existing slots, truthful unread
  reasons; unacquired wrappers are not primary/official documents. Actual-host,
  wrapper/read/operation/native HTTP/time caps and SSRF/access policy stay intact.
- `backend/services/research/relevance_gate.py`: a short specialist preview cannot
  hide subject terms in an already-qualified acquired article. Body reuse requires
  native read success + acquisition ID + structural article + nonmetadata depth +
  layer2 eligibility. Exact topic and captured-publication/48-hour gates remain.
- `backend/services/research/passage_extractor.py`: source-reported testing/launch
  lead outranks explicit historical background, retaining exact text/qualifications
  and raw history. No event-date inference or technical-performance verification.
- `backend/agents/trending/agent.py`: observed publisher-host fallback; no invented
  author from channel/publisher.
- `scripts/audits/replay_specialist_completion.py`: restore only genuinely recorded
  acquisition IDs on exact ID/URL/body-hash match. Pool-only captures lack these IDs;
  never invent them or bypass acquisition guards to make replay pass.
  Both pipeline and specialist gate aliases use the saved observation clock;
  a synthetic historical replay prevents wall-clock drift.
- New tests: `test_trending_read_opportunity.py` (11),
  `test_trending_body_handoff.py` (14), under `tests/unit/`.

## What is established

Exactly two authorized normal AI-disabled local queries, no article URLs supplied:

- Grid-scale energy storage: 27.32s, 27 candidates/18 reads/83 native HTTP admissions;
  five structural article bodies/4,396 words. Qnetic's October 20 article has 1,177
  words. Live qualification succeeded but specialist preview lost the source. Current
  offline correction returns one source/66-word new pilot passage with citation.
- Semiconductor manufacturing: 24.95s, 36 candidates/16 reads/81 admissions;
  two bodies/1,567 words. TweakTown's October 19 article has 1,024 words and a 44-word
  attributed passage. Current API/browser preserves it.

No model/capability/key request, third investigation, retry, access bypass or new
provider. 240s/24-read/120-native-admission ceilings respected. Source IDs/URLs/titles/
dates/body hashes unchanged; final replay manifests record zero publication changes.
Final downstream changes have genuine-source offline API/SSE and six Chromium-state
proof, not a fresh final-code network run. Broad accuracy/independence/virality are
not established; no release authorization.

Final full **1,767 /69.25s**, fast **1,559 /51.15s**, exit0. Fatal lint, all nine Node
scripts, frozen verifier, smoke, isolated persistence, final two replays and browser
exit0. Browser resource-console limitations are explicit in the report. Historical
archive, deployed rollback, production and hosted CI remain unverified. Protected
dossier/research/artifact/frozen-data diffs empty. No frontend source changes.

## Reproduce without network

Use new output paths, never tracked proof or historical dossiers:

```text
python scripts/audits/replay_specialist_completion.py --input <saved-grid-native.json> --output-dir <new-temp-dir> --agent trending --subject "grid-scale energy storage"
python scripts/audits/replay_specialist_completion.py --input <saved-semiconductor-native.json> --output-dir <another-new-temp-dir> --agent trending --subject "semiconductor manufacturing"
python -m pytest tests/unit/test_trending_read_opportunity.py tests/unit/test_trending_body_handoff.py tests/unit/test_trending_current_evidence.py -q
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validation/verify_frozen_benchmarks.py
python scripts/validate_release_candidate_smoke.py --output <new-temp-smoke.json>
python scripts/validate_rollback_compatibility.py --output <new-temp-rollback.json>
```

The two live permissions are consumed, not standing permission to repeat. Chromium
replay needs pinned Chart.js 4.4.1 and the existing audit harness; arrange unchanged
SSE as `01-trending-events.json`/`02-trending-events.json`. Do not click source
follow-up read buttons in offline acceptance.

Temp basename `aegis-trending-completion-feca018701e649a18ab0cccacc749765` contains
`live/`, `live-measurements.json`, `replay-grid-verified/`,
`replay-semiconductor-verified/`, `browser-closeout/`, `full-verified.log`,
`fast-verified.log`, final lint logs,
smoke/persistence reports and earlier failed replay versions. Temp can expire;
selected sanitized metadata/images are durable in docs. Next work is bounded
held-out accuracy and release verification with explicit scope, not another
architecture phase, relaxed gates or claimed popularity from one snapshot.
