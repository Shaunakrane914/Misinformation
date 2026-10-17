# Source-by-source text pipeline handoff — 2026-10-17

## Scope and current decision

User requested repeated assessment and improvement of every website's scraper,
raw text, useful structured extraction and frontend display. Work continues the
isolated `feat/phase9-intelligence-remediation-20261016` branch from
`77f8ec4612317c6eec6bbbb49ccd17eb522138ef`. Fetched main remains
`ff6d246bfe1e9cfd0f21d8e32135582e631636f1`. The worktree was clean before this
task. Original/other worktrees were not reset, modified or merged.

Read the [review and complete operation measurements](../testing/SOURCE_TEXT_PIPELINE_REVIEW_2026-10-17.md)
and [evidence index](../testing/evidence/2026-10-17_source_text_pipeline/README.md).
**Overall Phase 9 remains PARTIAL / research acceptance FAIL.** No production
deployment or main merge. All-source measurement is implemented, not all-source
unrestricted access or “perfect” semantic extraction. No unattended service or
self-modifying optimizer was installed.

## Implementation map and decisions

| Owner | Change / regression pointer |
|---|---|
| `adapters/web/page_extraction.py`, legacy native `executor.py`, web `jina.py` | Select article/main before character truncation; preserve raw text separately and keep table/negation/correction context. `test_source_text_pipeline.py` |
| `schemas/evidence_inspection.py` | Add exact byte/word counts, raw hash, structural selection scope and bounded allowlisted source observations. Metadata/feed summaries stay discovery-only. No model evidence rewriting. |
| `application/research/acquisition.py`, `services/research/deep_reader.py`, acquisition `service.py` | Preserve raw/page/transport/cap context into research; 12k deep body window, explicit source reads honor the existing budget. Transport limits are not increased. |
| `adapters/community.py`, standard handlers and extraction API | Deep Stack Overflow reads add up to two attributed answers to each of two questions. Parent checks, separate answer IDs, original question retention and backoff/quota controls. `test_phase9_community_sources.py` |
| `routing/social_handlers.py`, native `normalizer.py`, social `reddit.py` | Comments operation never substitutes post/search. Removed markers are metadata with no body; actual comments are COMMENT. Comment fetch uses bounded transport and validates parents. `test_reddit_operation_truth.py` |
| Authoritative NVD/arXiv adapters | Fix missing actual transport observations/status/hash; injected fixture fetchers are not called live. `test_source_text_pipeline.py` |
| Shared renderer/theme | Raw/readable metrics and source observations on all agents; min-content evidence-grid clipping fixed. Node renderer tests and real Chromium boundary checks. |
| `run_phase9_extraction_cycle.py` | Complete 52-operation inventory, repeatable rounds, opt-in bounded public captures, explicit allowlisted server config, before/after source fingerprint. |
| `audit_source_text_frontend.py` | Exact native sample inspections replayed in a labeled display scaffold on all four pages at three widths. Not fake native agent reports. |

The skills used for debugging, data quality and end-to-end testing led to
reproducing failures before fixes, explicit contracts and separate source,
API, native-agent and display-harness evidence. They do not establish an external
accuracy certification. Older compatibility imports, working scrapers and frozen
datasets remain intact; no architectural rewrite or new scraping service.

## Executed validation (dated observations)

| Command / observation | Exit / result |
|---|---|
| `python -m pytest tests/ -q` final delivery | 0; **1,309 passed**, 57.92s |
| `python -m pytest tests/unit tests/chaos tests/security -q` final delivery | 0; **1,101 passed**, 32.86s |
| Fatal Flake8 (`E9,F63,F7,F82`) | 0; zero findings |
| All eight Node `tests/frontend/test_*.js` | 0; passed |
| Release candidate smoke | 0; OFFLINE_SMOKE_PASS, explicit isolated mocks, not live-provider acceptance |
| Rollback compatibility | 0; OFFLINE_PERSISTENCE_PASS; historical archive/deployed rollback NOT_VERIFIED |
| Frozen benchmark validator / protected-tree diff / `git diff --check` | 0; protected files untouched |
| Detailed 52-operation baseline | 0; 16 protected sampled, overall PARTIAL |
| Two 54-probe rounds (52 plus two web reads), 60s interval | 0; stable source fingerprints; overall PARTIAL |
| Configured 52-operation pass | 0; 80 records; ten operations without records; overall PARTIAL |
| Final filtered eight-operation recheck | 0; all eight returned observations; not an all-operation acceptance run |
| Real FastAPI extraction smoke HN/Stack Overflow/X/Reddit | 0; four HTTP 200 observations; metrics retained, no full responses committed |
| Twelve real native button/backend/SSE inputs, three per agent | 0; 24 viewport states, five records / 355 words, eight empty inputs — research FAIL |
| Source display replay, 66 native samples, all pages/three widths | Initial weak check missed clipping; stronger check 8/12 failing before CSS, 0/12 after |

Intermediate test failures were retained/interpreted, not called successful:
three missing structural-extractor controls failed before implementation; four
Reddit semantic controls failed before the correction. Migrating comment reads
to the shared transport initially broke an old `urlopen` mock; its test now
injects a bounded HTTP response at the actual new transport seam. The guarantees
and assertions were retained, not loosened.

Fresh raw responses, logs and public samples are in a system-temp tree prefixed
`aegis-source-quality-`. Durable selected measurements/captures are appended
under the evidence index. They contain no environment-file contents or tokens.
The browser initially captured the top of the page after a smooth-scroll race;
the final capture helper uses instant positioning. A screenshot is not assumed
valid merely because DOM counters pass. See the evidence index for capture roles.

The twelve-agent run predates the final focused Reddit and evidence-grid fixes.
Those have dedicated live/source and display rechecks, **not** a falsely claimed
second twelve-agent live matrix. Presence of a Gemini key is not inference proof.

## Access/configuration interpretation

Default standalone probes retained Reddit's blocked state. Normal settings
startup loads the existing local server `.env` and found its previously
operator-enabled flag. A separate configured cycle explicitly read source-only
settings from that existing file and disclosed the flag as a boolean. No file,
secret or approval flag was changed. The flag is **not** independently verified
provider approval or a statement about production access. SEC/FactCheck and
other absent source configuration remain explicit. Never obtain a green result
by silently flipping flags, guessing contact details or copying cookies.

## Reproduce safely

Run from this checkout; use new output paths. Do not put real paths/credentials
in committed instructions. `--capture-samples` retains public research text;
keep it outside tracked proof unless separately reviewed. Counts are whitespace
words and UTF-8 bytes / 1,000, not linguistic CJK tokens or relevance scores.

```text
python scripts/audits/run_phase9_extraction_cycle.py --allow-live --all-operations --deep --limit 2 --rounds 2 --interval-seconds 60 --capture-samples --output-root <fresh-output>
python scripts/audits/run_phase9_extraction_cycle.py --allow-live --all-operations --deep --limit 2 --env-file <existing-server-env> --output-root <different-fresh-output>
python scripts/audits/run_phase9_source_api_smoke.py --allow-live --output-root <fresh-api-output>
python scripts/audits/audit_source_text_frontend.py --cycle-dir <saved-cycle-directory> --round 2 --chart-js <actual-pinned-chart-asset> --output-dir <fresh-browser-output>
python scripts/audits/run_phase9_four_agent_browser_audit.py --env-file <existing-server-env> --chart-js <actual-pinned-chart-asset> --output-dir <fresh-native-browser-output>
```

Standard regression commands remain in [AGENTS.md](../../AGENTS.md). The script's
maximum ten rounds is a bounded observation mechanism, not an installed daemon.
Do not automatically optimize against held-out labels or inflate source counts
with duplicate projections, removal markers, profiles or feed/navigation prose.

## Remaining priorities for the next agent

1. Entity discovery/selection: eight empty native-agent inputs remain despite
   successful direct source probes. Inspect concrete failed queries/qualification
   reasons before changing fan-out, timeouts or relevance rules.
2. Add bounded issuer-linked financial statement/PDF retrieval and period/metric
   binding. This pass does not acquire those linked PDFs.
3. Migrate remaining legacy Reddit post/search/RSS and X mirror `urlopen` calls
   to the existing shared capped/redirect-safe transport, with compatibility,
   caching, throttling and failure telemetry tests. The newly fixed comment
   path is not proof those older paths are hardened.
4. Complete source-specific depth where authorized: transcripts versus show
   notes, complete discussions versus samples, filing metadata versus XBRL.
   Blocked sources remain blocked pending actual owner/provider configuration.
5. Human-reviewed relevance/entailment, manual accessibility/contrast/axe,
   cross-browser/device and production parity remain unverified. Do not merge
   or deploy on the strength of word counts or offline tests.

Publication state at this document's creation: changes prepared locally;
commit/push/hosted CI must be recorded in a follow-up closeout after they are
actually observed. No merge/deployment is authorized by this handoff.
