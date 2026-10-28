# Publisher read allocation and statement attribution — 2026-10-26

## Decision

**The sampled battery-recycling failure is repaired with live source-to-report proof. Broader research acceptance remains PARTIAL. No deployment.** This closes the repair cycle approved after the user requested a plan before further coding. The [policy and failed-run ledger](READ_ALLOCATION_POLICY_2026-10-25.md) were written before implementation. Live observations were collected October 25; this closeout was written October 26, Asia/Calcutta.

Checkout: `release/specialist-task-20261024`, base `7ad13a5`, plus preserved dirty work. This report concerns the remediation worktree, not deployed code. No commit, push, merge, production mutation or new source sweep was performed.

## First failure and targeted changes

The earlier battery-recycling investigation used nine reads: an unresolved wrapper, then eight publisher reads (home, comments feed, search and five articles subsequently found stale). A relevant ECS article URL and headline were already observed, but its read was rejected after the publisher cap was exhausted. Exact adjacent topic words received a stronger title score than reordered complete topic coverage. Home/index captures also counted as unsuccessful article-yield observations. The final freshness gate correctly rejected stale bodies; it was not the first source loss.

| File / function | Implemented change and reason |
| --- | --- |
| [PublisherReadPolicy](../../backend/services/research/publisher_read_policy.py) | Separately tracks publisher discovery and article attempts. At the existing eight-read host cap, reserves four article opportunities, two initial discovery opportunities and two adaptive discovery opportunities. Scales down for smaller profiles; defers comment feeds for article tasks. |
| [PipelinedAcquisition](../../backend/services/research/pipelined_acquisition.py), `_selectable`, `_ranked`, `_dispatch_reads`, `_complete_read`, `_good_leads`, `_query_limit` | Applies explicit allocation deferrals; updates article-yield feedback only from actual article/document observations; excludes known stale Trending leads from adequate-supply counts; retains one existing query slot while optional advice awaits feedback. Existing global/host/HTTP/deadline/security limits remain. |
| [candidate_selection.py](../../backend/services/research/candidate_selection.py) | Gives reordered complete topic-token coverage the same title weight as adjacent coverage. Statement/interview/transcript labels are weak routing signals, never proof of attribution. |
| [harvesting.py](../../backend/services/research/harvesting.py) | Allows later observed feed aliases to update routing hints in the pipelined controller. Captured-body dates still decide final freshness. |
| [Terminal runner](../../scripts/audits/run_terminal_agent_quality.py) | Uses the existing persisted daily runtime advisory scope instead of a new audit-specific allowance; records reservation deltas. No ledger reset, model/key fallback or generation retry. |
| [content_roles.py](../../backend/services/research/content_roles.py), [passage_records.py](../../backend/services/research/passage_records.py), [evidence_workbench.py](../../backend/services/research/evidence_workbench.py) | Rejects transcript introductions as statements. Requires observed speaker linkage; stops at the next speaker, including inline transitions. Roster/title text alone cannot authenticate speech or identity. |
| [Saved workbench rebuild](../../scripts/audits/rebuild_saved_workbench.py) | Creates a fresh, explicitly offline, evidence-only projection from saved source bodies. Original reports remain immutable; stale findings are not copied. No acquisition, AI, full agent rerun or new verdict. |

The final generic unusable-article feedback adjustment and transcript correction were made **after** the live batch. They have offline regression/replay proof, not another live investigation. Final telemetry uses `consecutive_unusable_articles`; original live telemetry retains its earlier `consecutive_temporally_unusable_articles` field.

## Replay before live use

The exact failed query world was replayed with network blocked. With original observations alone, the ECS URL now received a read within eight publisher attempts; its body outcome remained unknown because the original run never read it. A separately labeled replay supplied an already saved genuine ECS body only at that observed URL: one source and 100 selected words qualified. Neither replay establishes live recall or latency. See [offline control measurements](evidence/2026-10-25_read_allocation/offline-allocation-control.json).

## Four authorized live investigations

One normal local request per case, DEEP/pipelined mode, 240-second ceiling, 24 reads and 120 native HTTP admissions each. No whole-investigation retries or supplied article URLs. Personal queries explicitly requested public statements, so comparisons with earlier name-only investigations are not controlled experiments. The application fingerprint stayed stable during the four-case batch; final offline follow-ups have a different fingerprint, both recorded in [measurements](evidence/2026-10-25_read_allocation/measurements.json).

| Case | Seconds | Reads | Native HTTP admissions | Live qualified records | Selected frontend words / interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| Trending — battery recycling | 38.77 | 11 | 74 | 1 | **185**, fresh publisher article |
| Trending — semiconductor manufacturing | 52.35 | 12 | 80 | 0 | **0**, no adequately dated relevant article |
| Personal Watch — Mary Barra public statement | 103.30 | 19 | 93 | 1 | **114**, historical 2021 reporting |
| Personal Watch — Tim Cook public statement | 63.95 | 19 | 87 | 4 before correction | **204 editorial introduction words; not accepted as statement proof** |

Total: **334 native HTTP admissions**, not a monetary cost or unique-network-request count. Runner exit 0 establishes completed observation, not research acceptance.

Battery recycling autonomously acquired [the ECS meeting article](https://bioengineer.org/battery-safety-sodium-ion-and-recycling-research-head-to-ecs-meeting/): 801 captured body words, observed publication `2026-10-24T15:38:21+01:00`, and two exact passages totaling 185 displayed words. The publisher allocation was four discovery plus four article attempts, with no comment-feed attempt. This proves one real source survived discovery, reading, qualification and rendering; it does not prove scientific truth, virality or source independence.

Semiconductor manufacturing retained 22 eligible candidates but produced stock/company-oriented pages, indexes and stale context. Three Google wrappers remained unresolved; its article-shaped MarketBeat stock page lacked adequate publication evidence. The first remaining problem is task-appropriate discovery/source selection, not an invitation to weaken the date gate. It remains an explicit zero-evidence result.

Mary Barra's qualified source reports a 2021 Business Roundtable statement. Other captures failed subject/structure checks. This does not demonstrate current coverage or identity-threat detection.

Tim Cook's original four selected passages were transcript introductions. Inspecting the complete saved bodies exposed that error despite positive source counts. The corrected offline projection retains **one historical WWDC 2020 source, 16 actual speaker passages and 547 words**. The other three captures lack sufficient speaker linkage and remain rejected. Source publication time is unverified; the event is historical. This is source-attributed reported speech, not authenticated identity. The corrected Mary projection retains one passage/114 historical words. Neither projection is a fresh native agent result.

## AI actually used

The configured `gemini-3.5-flash-lite` capability check returned HTTP 200. Exactly **three generation attempts/reservations** returned HTTP 200: battery recycling 401 tokens, semiconductor manufacturing 385, Mary Barra 381; **1,167 provider-reported tokens total**, 260 output tokens. Each was below 160 output tokens, one attempt only, and supplied a validated query suggestion rather than evidence or a verdict. Tim Cook's fourth reservation was denied locally by the shared daily budget; no fourth generation request was sent. The ledger was not reset. Monetary cost was not measured. Successful advice did not make all investigations successful.

## Rendering and integrity

Four exact native responses and two explicitly offline rebuilt Personal projections were rendered at 320, 390 and 1440px: **18 states**, no detected horizontal overflow or uncaught page exceptions. Passage pagination and filters remained keyboard-operable. External browser traffic was blocked, so these checks made no further provider/model calls. Four focused captures were visually inspected; see the [evidence index](evidence/2026-10-25_read_allocation/README.md).

Twenty-four passage observations across native/rebuilt views passed canonical-source joins, body hashes, exact offsets and deterministic passage-ID checks, with zero errors. They include repeated observations and are not 24 distinct sources or an accuracy evaluation. No selected passage was omitted by display budgets.

These are saved-response rendering checks, not real production form submission, screen-reader acceptance, measured contrast, Safari/Firefox or deployed end-to-end verification.

## Actual final validation

| Check | Observed result |
| --- | --- |
| Focused final allocation/speaker regressions | 18 passed / 6.30s, exit 0 |
| `python -m pytest tests/ -q` | **2,574 passed / 119.76s**, exit 0 |
| `python -m pytest tests/unit tests/chaos tests/security -q` | **2,366 passed / 103.67s**, exit 0 |
| Fatal flake8 E9/F63/F7/F82 | Zero findings, exit 0 |
| Ten `tests/frontend/test_*.js` Node scripts | Each exit 0 |
| Isolated release smoke / persistence validator | OFFLINE_SMOKE_PASS / OFFLINE_PERSISTENCE_PASS, exit 0 |
| Frozen content verifier | Hashes verified, exit 0 |

Frontend/smoke/persistence checks preceded the last generic feedback regression; frontend code was unchanged. Persistence validation used temporary data and explicitly reports the historical archive and deployed rollback **NOT_VERIFIED**. It does not recover or clear the historical malformed-dossier limitation. The initial focused invocation referenced a nonexistent test filename and collected no tests; corrected focused/full commands passed. Two early synthetic control failures were an incorrect fixture URL condition, corrected without loosening qualification. These attempts are not hidden as passing runs.

## Remaining work

1. Diagnose semiconductor topic planning against its saved candidate ledger before requesting another bounded live case. Prefer article-oriented sources capable of answering the topic, without company/stock-page drift.
2. Improve current, explicitly attributed Personal Watch discovery. Historical speech is useful background but does not satisfy current coverage or impersonation/false-quote evaluation.
3. Verify the final speaker correction and generic feedback behavior in a separately authorized small live batch; the four-case authorization is consumed.
4. Independently review passage support and judgments across all four agents. BrandShield and Scout were not newly sampled in this batch. No 2×/20× improvement, independent accuracy acceptance, hosted CI, production parity or release readiness is claimed.

Detailed native logs, source bodies and screenshots remain in temporary tree `aegis-read-allocation-o6nqsake`; selected sanitized measurements are durable below. Temporary logs may expire. No secrets, private reasoning transcript or fabricated evidence are included.
