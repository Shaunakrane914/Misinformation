# Useful evidence expansion handoff — 2026-10-25

User request: continue expansion toward much more relevant evidence on all four
agent frontends. **Increment implemented and tested; 20× is not demonstrated.**
The [full report](../testing/USEFUL_EVIDENCE_EXPANSION_2026-10-25.md) contains
decisions, the failed observation, final measurements, commands and limitations.

## Workspace and preservation

Application edits are in `.scratch/phase9-remediation-20261016`, branch
`release/specialist-task-20261024`, HEAD
`1a90d681361b8e027a12feb88266932a5cb5d1d1`, plus preserved uncommitted work.
Original IDE checkout is a separate older branch; do not overwrite this release
code with its older service/router. No commit, push, merge or deployment.
Frozen data, historical dossiers, research/artifacts, credentials, access flags
and existing user changes are preserved. Do not infer production state from
these local results.

## Implementation map

- [Publisher continuation](../../backend/services/research/publisher_links.py)
  and [harvesting](../../backend/services/research/harvesting.py): bounded actual
  article body links may lead to cited documents; no nav-link citation crawl,
  guessed URLs, inherited primary/ownership labels or bypassed safe reader.
  Removed the fallback that undid off-subject helper rejection.
- [Source-family hints](../../backend/services/research/source_diversity.py):
  existing task angles match appropriate family hints within existing caps.
- [Personal passage attribution](../../backend/services/research/passage_records.py):
  observed speaker/reporting-verb association, conservative surname/full-name
  disambiguation; denial/borrowed quote/competing name guards stay intact.
- [Content roles](../../backend/services/research/content_roles.py),
  [extractor](../../backend/services/research/passage_extractor.py) and
  [BrandShield](../../backend/agents/brandshield/intelligence.py): limited FR/ES
  native-text selection, with denials and guidance kept distinct from threats.
- [Workbench](../../backend/services/research/evidence_workbench.py) and
  [inspection](../../backend/schemas/evidence_inspection.py): bounded adjacent
  context, exact spans, overlap/contained-text deduplication and honest counters.
- `diversified_queries` in harvesting: update a personal query's task only when
  its text is actually replaced. A long internal intent had mislabeled the
  unchanged public-statement news query, making duplicate completion order
  affect qualification. The failed same-body result is preserved separately.

## Actual verification and observations

Final full/fast suites: **2,348 / 2,140 passed**. Focused yield/overlap:48 passed.
Fatal lint, all ten Node scripts, frozen verifier and release smoke pass.
Offline persistence passes; release historical archive and deployed rollback
remain NOT_VERIFIED. The original55 malformed dossiers remain untouched.

The final four live cases published Adobe7,111 / Dyson1,080 / battery
recycling322 / Mary Barra0 selected words. Personal's routing fix then passed
one separate live check:114 words from the same2021 statement. These are
different fingerprints, not one all-pass final batch. All ten local live
investigations in this continuation used bounded native acquisition, zero AI,
isolated persistence and no paid readers. Raw words are not useful evidence;
host counts are not independent sources.

A real article's observed citation led to a Motley Fool transcript:2,935 captured
words, nine published passages/958 selected words. This is sampled live
autonomous proof, not broad recall/accuracy acceptance. Personal remains weak
for current identity threats and Trending has only one fresh qualified source.

Exact shared-report browser replay:12 states from the final batch plus3 from
post-fix Personal, at320/390/1440px. Pagination/filter/span visibility checks
passed, no measured overflow/page exceptions. This mounts the shared renderer
and blocks external traffic; it is not a fresh native-form/production browser
test or accessibility certification. Selected screenshots were visually viewed.

## Reproduce safely / next work

Offline commands: `python -m pytest tests/ -q`,
`python -m pytest tests/unit tests/chaos tests/security -q`, fatal flake8,
all Node `tests/frontend/test_*.js`, frozen verifier, and smoke/rollback validators
with fresh `--output` paths. Focused files:
[yield controls](../../tests/unit/test_useful_yield_repair.py),
[overlap controls](../../tests/unit/test_workbench_overlap_safety.py).

Saved-report rendering:

```text
python scripts/audits/audit_evidence_workbench.py --report <saved-native-response> --output-dir <new-temp-directory>
```

Do not silently rerun the live batches. Preserve original captures and fingerprints;
new acquisition is a separate observation under the user's current scope.
Selected measurements and browser checks are under
[dated evidence](../testing/evidence/2026-10-25_useful_yield/final_live_measurements.json).
Full temp basename:`aegis-useful-yield-648b5eb59537470ea08558920b838c3a`.

Next concentrate on Personal current statements/identity-threat reports and
Trending fresh source recall using the saved rejection reasons. Do not relax
attribution/date/access gates or repeat text to force20×. Financial historical
and forecast paragraphs remain contextual; BrandShield allegations/warnings are
not confirmed attacker evidence. Independent held-out accuracy, production
verification, hosted CI and historical recovery are outstanding owner gates.
