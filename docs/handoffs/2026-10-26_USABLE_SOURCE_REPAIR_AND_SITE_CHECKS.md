# Usable-source repair and individual website checks — 2026-10-26

## Decision and scope

**Engineering corrections pass offline; live article acquisition remains unmet.** User requested usable-source expansion/repair, then individual new-site scraping checks. Read the [full result](../testing/USABLE_SOURCE_REPAIR_AND_SITE_CHECKS_2026-10-26.md), [60-site inventory](../testing/evidence/2026-10-26_usable_sources/individual-sites.csv) and [operational runbook](../operations/TOPIC_SOURCE_ROUTING.md).

Checkout `.scratch/phase9-remediation-20261016`, branch `release/specialist-task-20261024`, base `7ad13a5`, plus preserved pre-existing dirty work. Original IDE root is another worktree. No staging/commit/push/merge/deployment. Pre-edit copies/status and all original new native captures are in fresh system-temp basename `aegis-usable-source-repair-l_nnpdo1`; selected sanitized evidence is [durable](../testing/evidence/2026-10-26_usable_sources/README.md). Protected dossiers, research/artifacts, working shims and frozen retrieval data/manifests remain unchanged.

## Changes

- `search_observations.result_fit`: URL scope enforcement for positive/negative `site:` constraints; off-site provider responses now trigger existing bounded fallback. Genuine normalized Bumrah failure decisions saved in `tests/unit/fixtures/oct26_topic_scope_drift.json`, not fabricated HTML/bodies.
- `source_registry.py` and operational JSON: existing native-route eligibility under original auth/capability gates; topic-specificity preference; India jurisdiction and issuer-anchor restrictions. Four conditional public-text reviews now include PIB/Sports Ministry, following their published policies; no private publisher approvals invented. 60 families/hosts registered, not 60 working scrapers. Eight existing native families, 48 new unreviewed, four publicly reviewed.
- `topic_context.py`: tentative request/subject-matched observed geography, uncertainty on unrelated/conflicting observations. No celebrity identity mapping or nationality authentication.
- `SourceRegistry.discovery_entrypoints` and `harvesting.py`: at most two selected, configured publisher directories within existing read caps; follow only actual observed links through current continuation. Directories remain discovery, never article evidence. Works in both controllers, initially and after bounded topic refinement.
- `deep_reader.py`: wrapper-resolution search outside body scope; resolved body transport still gated. Source/body/robots/SSRF/redirect rules retained.
- `SourceRegistry.paced_request` / bounded HTTP: observed Global Voices 10-second crawl delay honored under the parent deadline, across threads in one process. One transfer attempt, no automatic redirects for paced calls; stop if the wait cannot fit. No multi-process pacing claim. Native executor/modular reader propagate typed policy denial instead of triggering another extraction route.
- `tests/conftest.py`: normal tests explicitly AI-disabled with isolated advisory ledger. Local server `.env` AI enablement remains unchanged.
- `scripts/audits/probe_source_families.py`: per-family inventory and direct reviewed-source diagnostics, 60s/six admissions/two reads per reviewed family; no AI/paid reader/audit retry/raw-body export. Homepage/policy prose excluded from article-yield counts.
- Tests: 27 usable-source controls plus two probe-report controls. Characterization source-plan SEC query changes are recorded in a new reviewed delta file after comparing actual old/current registries. Full source bytes, candidates, corpus/dossier hashes, citations/findings unchanged; historical manifests untouched and no new broad canonicalization exclusion.

## Actual observations

Two approved normal cases (once each, 180s/16 reads/80 admissions): Bollywood 26.25s, three leads, two selections/no actual body read-service starts, 42 admissions; Bumrah 29.54s, 34 leads, two selections/no starts, 38 admissions. Bodies/published words zero. PIB robots403; Global Voices initially required unsupported 10s spacing; Sports Ministry connection failure. Observed cricket/India routing worked; permission-denied candidates no longer exhausted all 16 selections.

After pacing implementation, separately approved Bollywood check ran once: 60.31s, four leads, two selections/no starts, 39 admissions, zero bodies/words. Both directory robots fetches failed DNS validation first, so no live pacing or extraction success was demonstrated. Both batch fingerprints stable. All three investigation allowances consumed; no audit retry.

User's later direct-site request: all 60 families inventoried, four reviewed sites probed, 48 not fetched for missing review, eight existing routes not rerun. PIB/GOV.UK/Global Voices hit DNS_TIMEOUT (about2.5s, zero HTTP admissions each); Sports Ministry CONNECTION_FAILURE (1.24s, one admission). All zero body words/KB; failure before extraction. No model calls. This does not prove remote sites lack information, or establish why the local OS resolver failed.

AI enabled normally under the existing ledger: one recorded successful new suggestion, 389 provider tokens; paced-case suggestion timed out and consumed a reservation without a saved provider outcome/token observation. Usage for that attempt is unknown. Daily shared count ends at three including the earlier40-token enablement check. No quota reset, retry, key/model fallback or extra model checks were used for direct probes.

## Commands / acceptance limits

Final full: `python -m pytest tests/ -q --tb=short`, exit0, **2,645 passed/117.04s**. Fast unit/chaos/security, exit0, **2,437 passed/98.88s**. Focused repair/registry/discovery/golden/runtime133pass; probe+repair29pass. Fatal flake8 exit0. Each of ten frontend Node scripts exit0. Fresh-output release smoke OFFLINE_SMOKE_PASS and isolated persistence OFFLINE_PERSISTENCE_PASS; historical archive/deployed rollback NOT_VERIFIED. Frozen verifier, protected-tree diff and whitespace checks pass.

Nine empty native report replay states at320/390/1440px: expected counts/filter/pagination, no detected horizontal overflow or uncaught page exceptions. Paced-check mobile workbench screenshot visually inspected. External traffic blocked; no fresh browser-to-provider submission or accessibility certification. No hosted CI, independent accuracy acceptance, historical malformed-dossier recovery, production verification or deployment.

Intermediate failed directory controls and ten source-plan characterization differences were investigated and preserved in logs; see the full report for exact resolution. Next runtime issue is DNS/connection establishment, not demonstrated article parsing failure. Further native/model probes must have a new bounded authorization; preserve explicit source gates and never treat catalogue size, HTTP200 or passing tests as acquired evidence.
