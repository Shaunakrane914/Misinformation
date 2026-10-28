# Public-source access activation — 2026-10-26

## Scope and current decision

User accepted implementing legitimate public-access routes, with no publisher
agreements configured and existing gates retained. Three individual source checks
and four DNS-only operations were explicitly approved; one CPSC post-fix check
was separately approved. Both source allowances are consumed. No AI calls,
paid readers, audit retries, system-network changes, commit, push or deployment.

Worktree `.scratch/phase9-remediation-20261016`, branch
`release/specialist-task-20261024`, base
`7ad13a59f86a78802e45685ecfd1fd4999a2e5ce`, plus preserved dirty implementation.
The original IDE checkout is a different worktree. Credentials, protected frozen
data, historical dossiers, research/artifacts and working scrapers were preserved.

**Scoped permission and diagnostic fixes are implemented. Live research acceptance
is not met:** FTC yielded a discovery feed, no article; DOJ no body; CPSC's
corrected native API attempt timed out. No production-readiness claim.

Full [report and rationale](../testing/PUBLIC_SOURCE_ACCESS_ACTIVATION_2026-10-26.md),
[new evidence index](../testing/evidence/2026-10-26_public_source_access/README.md),
[operations guide](../operations/TOPIC_SOURCE_ROUTING.md).

## Changes to resume from

- `source_registry.py`, `source_registry_data.json`, `source_public_licence_reviews.json`:
  separate unknown review from explicit restriction; scoped DOJ/FTC agency press
  text and CPSC recall API reviews; exact host/path limits; double-encoded escape
  rejection; separate external model-processing review. Seven reviewed families,
  eight existing-route families, nine explicit agreement requirements and 36
  unreviewed. 60 families / 61 declared hosts is not a successful scraper count.
- `evidence_advisor.py`, `passage_extractor.py`, `page_extraction.py`: check model
  permission before prompt/gateway use, recheck excerpt permission for imported
  controlled URLs, and preserve contrary-rights notices through footer cleanup.
  Local AI enablement and shared ledger were not reset or edited.
- `consumer/cpsc_recalls.py`, `expanded_catalog.py`: bounded documented JSON
  adapter, actual observed native IDs/field provenance, discovery-only export
  without inferred article bodies. Explicit adapter use only; automatic
  API-to-agent-report wiring remains incomplete. Generic webpage reading is not
  intercepted and the API review does not approve CPSC website-wide material.
- `SourceRegistry.robots_decision` / `enforce_scoped_body_access`: corrected scoped
  API/press access rejecting its own robots document. Exact temporary document
  lease, no redirects, one bounded attempt, unchanged SSRF/DNS controls.
- `jina._execute_web_read`, `DeepReader`, `expansion_safety.safe_fetch`: retain
  typed native/fallback causes, bounded sanitized history, HTTP/observed-network
  flags and DNS-validation failures; permission/robots denials stay terminal.
- `probe_source_families.py`: explicit approved family selection required;
  at most 90s/six native admissions/two reads per selected family. Structured
  records, discovery words, article words and published words counted separately.

Regression pointers: [public permissions](../../tests/unit/test_public_source_permissions.py),
[CPSC](../../tests/unit/test_cpsc_recalls.py),
[failure preservation](../../tests/unit/test_public_source_transport_failures.py),
[site diagnostics](../../tests/unit/test_source_site_probe.py),
[advisor controls](../../tests/unit/test_evidence_role_advisor.py),
[routing controls](../../tests/unit/test_topic_source_registry.py),
[saved event controls](../../tests/unit/test_oct21_event_selection.py) and
[footer extraction](../../tests/unit/test_web_page_extraction.py).

## Observations and first losses

| Check | Seconds | Native HTTP admissions | Result |
| --- | ---: | ---: | --- |
| FTC initial | 11.96 | 3 | RSS200, 937 retained discovery words / 12.039KB; observed article failed, original typed cause lost |
| DOJ initial | 4.40 | 2 | Directory failed, original typed cause lost |
| CPSC initial | 0.02 | 0 | Locally rejected robots request inside API-only body scope |
| CPSC post-fix | 5.40 | 2 | Progressed to native HTTP attempt; typed TIMEOUT, no response/records observed |

Total seven admissions; zero acquired articles, zero recall records, zero published
evidence words, zero generated findings. Feed counts are not article evidence.
Four DNS-only operations for DOJ/FTC resolved public answers in 0.001–0.064s.
They do not establish the cause of earlier timeouts or HTTP availability.

The original DOJ/FTC cause cannot be reconstructed from their generic failures.
The typed-cause repair is verified by offline controls, not an additional live
DOJ/FTC request. No guard was loosened to pass an access failure.

## Commands actually run

Run from the release worktree; use fresh temporary output paths for validators.

| Command / scope | Actual closeout outcome |
| --- | --- |
| `python -m pytest tests/ -q --tb=short` | Exit0, **2,746 passed / 64.02s** |
| `python -m pytest tests/unit tests/chaos tests/security -q --tb=short` | Exit0, **2,538 passed / 55.35s** |
| Focused permissions/CPSC/site/typed-transport controls before the CPSC recheck | Exit0, 97 passed / 1.04s; five more transport cases included in final full/fast runs |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit0, zero fatal findings |
| Each of ten `tests/frontend/test_*.js` Node scripts | Exit0 each; simulated DOM, not a new rendered-browser investigation |
| `python scripts/validate_release_candidate_smoke.py --output <new-temp-json>` | Exit0, OFFLINE_SMOKE_PASS |
| `python scripts/validate_rollback_compatibility.py --output <new-temp-json>` | Exit0, isolated OFFLINE_PERSISTENCE_PASS; this checkout's historical archive NOT_VERIFIED |
| Same rollback validator, `--archive ../../backend/data/dossiers --output <new-temp-json>` | **Exit1, HISTORICAL_ARCHIVE_FAIL**: original archive 11 VERIFIED / 2,445 LEGACY_UNSEALED / **55 FAILED**; no records repaired |
| Frozen verifier / protected Git diff / whitespace and relative-document links | Exit0; frozen hashes match and protected tracked trees unchanged |
| Three-source probe, explicit `--family doj --family ftc --family cpsc --seconds-per-family 90` | Exit0 diagnostic transport; zero articles/records, not research success |
| Separate CPSC probe, explicit `--family cpsc --seconds-per-family 90` | Exit0 diagnostic transport; TIMEOUT, zero records |
| Four DNS-only observations | Exit0, no HTTP/model calls or settings changes |

Intermediate failures are not hidden as passes. An old unknown-review assertion
was updated to the new `UNVERIFIED` semantics. Three genuine saved-prefix event
controls gained explicitly synthetic test-only excerpt permissions to isolate
classification; source fixtures and expected classifications remain unchanged.
CPSC's API-only review no longer advertises an automatic webpage route. A routing
fixture also generated distinct URLs for identical generic synthetic articles;
thread scheduling could consume its three read attempts before refinement. It
now uses one stable duplicate URL, without changing assertions/caps, sleeping or
retrying. This does not promise refinement after real read budgets are exhausted.
An intermediate full run passed 2,741 before the final five transport controls;
the final full/fast results above include every current case.

## Limits / next work

1. Preserve publisher gates. Real intended-use agreements are still needed for
   restricted entertainment/sports content; source publicity or an API key does
   not automatically cover retention, display or external model processing.
2. Real article access remains unverified for these new routes. Future checks need
   an explicit bounded allowance; use the repaired typed diagnostics rather than
   extrapolating from zero outputs or increasing all timeouts.
3. CPSC structured normalization has offline proof only, and is not yet an
   automatic agent/report route. A recall is a safety notice, not proof of fraud.
4. The 55 malformed historical dossiers remain a release gate. Readable legacy
   records are unsealed, not cryptographically verified. Deployed rollback,
   independent research accuracy, fresh browser/provider behavior and hosted CI
   were not verified.

Full temporary logs are under system-temp basename
`aegis-public-access-activation-mvdketxe`; sanitized selections are durable in the
new evidence directory. These are execution summaries, not a reconstructed raw
transcript. No commit, push, merge or deployment was performed.
