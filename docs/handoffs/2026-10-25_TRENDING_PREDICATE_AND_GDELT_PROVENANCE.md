# Trending passage-predicate generalization and GDELT provenance — 2026-10-25

User request: two targeted repairs after the interleaved-acquisition evaluation, **uncommitted, saved
captures only**. Base: `release/specialist-task-20261024` at `7ad13a5` (clean at start). Nothing was
committed, pushed, merged or deployed. No HTTP acquisition, Gemini call or provider-key probe was made.

**The Trending regression is NOT claimed resolved live.** Offline replay shows the rejected article
now qualifies; whether a fresh live Trending run improves is unverified and needs separate authorization.

## What was wrong

The October 25 Trending run acquired a genuine fresh article
([bioengineer.org ECS meeting](https://bioengineer.org/battery-safety-sodium-ion-and-recycling-research-head-to-ecs-meeting/),
published 2026-10-24T15:38:21+01:00, 801 words) and rejected it as `NO_RELEVANT_PASSAGE`. The only two
paragraphs naming "battery recycling" failed the last clause of
[`has_usable_passage`](../../backend/services/research/passage_extractor.py): a paragraph needed
`is/are/was/were/has/have/allows/contains/includes/limits/rated` or a signal word. "will present",
"covers", "states" and "evaluates" were not on the list. The same list accepted headlines such as
"Why Toyota Tsusho is leaning into EV-battery recycling" because they contain "is".

## Changes (all uncommitted)

| File | Change |
| --- | --- |
| [clause_predicates.py](../../backend/services/research/clause_predicates.py) (new) | Dependency-free finite-predicate recognizer: `find_finite_predicate`, `has_finite_predicate` |
| [passage_extractor.py](../../backend/services/research/passage_extractor.py) | `has_usable_passage` calls it in place of the inline verb regex (signal markers and FR/ES rule retained) |
| [gdelt.py](../../backend/infrastructure/acquisition/adapters/news/gdelt.py) | `seendate` → `gdelt_seen_at` (+raw value, basis); no `published`/`published_at`; snippet no longer reads as a date |
| [expanded_catalog.py](../../backend/infrastructure/acquisition/adapters/expanded_catalog.py) | Forwards only `gdelt_*` provenance and `publication_time_basis` into fragment metadata |
| [test_clause_predicates.py](../../tests/unit/test_clause_predicates.py) (new, 98 tests) | Mechanism, ECS replay, hashes/offsets/citation IDs, corpus controls |
| [test_gdelt_adapter.py](../../tests/unit/test_gdelt_adapter.py) | Replaced the assertion that enshrined the old mapping; three provenance/strict-gate tests |
| `tests/unit/fixtures/oct25_ecs_battery_recycling_raw_pool.json` (new) | The genuine saved ECS record as a one-source raw pool, unmodified |
| `tests/unit/fixtures/predicate_controls_20261025.json` (new) | 45 paragraph controls from saved reports with source hash and paragraph index |

## Fix 1 design and why it is not "any word ending in s"

A sentence counts only if **all** hold: it ends with a period (not `?`, `!`, `:`, `…`/`...`, or nothing);
a lowercase finite verb has a subject head before it (one comma/dash aside may intervene) and a
complement after it; third-person verbs agree and carry subject evidence (pronoun, proper-noun head, or
determiner-led noun phrase), because most `-s` forms are plural nouns; modals, auxiliaries and a
540-stem lexicon with generated 3rd-person/past forms (plus a few irregulars) supply the verbs. Rejected structurally: Title Case
headlines (capitalized verbs), wh-fragments, imperatives/calls to action, reduced relatives
("funds designed to…", "customers highlighted include…"), clause-initial `-ing` modifiers, relative-clause-only
fragments, labels, markup, cookie/newsletter/promo/caption boilerplate, and copy addressed to "you/your"
(unless inside quotation marks). First-person plural is deliberately **allowed**: an executive statement
("We are announcing a leadership transition…") is exactly the primary evidence Personal Watch needs; a
first draft rejected it and `test_joint_statement_keeps_speakers_separate` caught that.

Unchanged by design: subject relevance, topic gate, objective gate, publication-date eligibility,
source-body integrity, `layer2_eligible`, and exact citation offsets.

## Before / after — the affected Trending article

Replayed from the saved bytes through the repo's offline requalifier (`requalify_payload`, reference time
= pool creation time), legacy predicate patched in for "before".

| | Before (`7ad13a5` predicate) | After |
| --- | --- | --- |
| First live run (13:47Z) | `TEMPORAL_MISSING_TIMESTAMP` (`CONFLICTING_CAPTURED_DECLARATIONS`, timezone false conflict) | resolved before this task by the `7ad13a5` timezone work (the 14:20Z rerun reads the date); not changed here |
| Second run (14:20Z) / replay: decision | `REJECTED` — `NO_RELEVANT_PASSAGE` / `NO_EXACT_USABLE_PASSAGE` | **`QUALIFIED`** |
| Publisher date | `2026-10-24T15:38:21+01:00` (captured declaration) | same |
| Usable paragraphs (of 13) | 3 = 350 words | 6 = 651 words |
| Published evidence passages | 0 | 2 (85 and 100 words) |
| Selected excerpt | none | 100 words, offsets **3315–4088**, starts "The third area covers battery recycling…" |
| Captured words / hash | 801 / `692428c0…ccb` | identical (never modified) |
| Rejected rows | share row + 6 metadata rows | identical: all 7 still rejected |

Verified in tests: `sha256(readable_text) == raw_content_hash`; `content[start:end] == excerpt`; passage IDs
equal `ps_` + sha256(`evidence_id:start:text`)[:16] and are unique; every passage slice matches its text;
claim status stays `UNVERIFIED` / `NOT_ADJUDICATED`.

## Reprocessing the saved corpus (no network)

398 unique full-text bodies from 62 saved reports (149 article bodies, 141 discovery leads, 70 homepages,
36 indexes, 2 official docs) = 14,732 paragraphs; `has_usable_passage` baseline 5,349 usable.

| Paragraph level | Count |
| --- | ---: |
| Newly usable | 709 (358 article body, 249 lead, 96 homepage, 4 official, 2 index) |
| No longer usable | 963 |
| Net usable | 5,349 → 5,095 |

Why paragraphs were lost: 498 no finished sentence (unpunctuated headlines, labels, colon lead-ins); 123
boilerplate/caption/CTA/list-marker; 87 truncated snippets; 78 addressed to "you"; 62 questions; 59
markup; **56 finished sentences with no recognized clause** (the genuine false-negative pool).

**Source level (the real test):** 37 distinct saved Trending pools replayed twice (legacy vs new
predicate, same bytes, same reference time). Qualified sources **30 → 34, 0 lost.** The four additions are
the ECS article and one pymnts/Meta-Muse paragraph that appears in three pools. For 1 source
(`techxplore` EV-cyberattack) the selected passage changed to a different valid exact span because newly
usable paragraphs now compete in the existing scorer; human review is needed before calling that better.
One pool needed the repo's documented `disambiguate_aliases` rescue (identically in both modes).

## False positives found (be honest about these)

During development, blind samples of newly accepted paragraphs surfaced real false positives, each fixed
structurally rather than by example: sentence-case headlines, photo captions, cookie banners, "Learn
more"/"please check out" CTAs, adjective + plural noun ("stable yields with…"), compound noun + base verb
("NC ballot requests plunge…"), participles ("funds designed to…"), "these signs", relative-clause
fragments, and an `re.I` flag my own rewrite dropped.

Final blind sample (50 unique newly accepted paragraphs, one reviewer, so an estimate not a precision
claim): ~42 legitimate prose, 6 clear false positives, 2 borderline. Four of the six were then fixed. **Still
admitted, no structural tell:** a table footnote ("Market cap calculated using publicly traded shares…"),
a customer testimonial, company/product marketing sentences with ordinary verbs, and a promotional crypto
sentence. Promotional prose with a real verb passes this filter; later relevance, role and objective gates
decide. All 45 corpus controls pass: 25 old false positives and 8 never-qualified navigation/metadata rows
stay rejected, and 12 real sentences stay usable.

## Fix 2 — GDELT provenance

Before: `seendate` was written to `published` and `published_at` in candidate metadata (and a unit test
asserted it). I traced it: the catalog built the fragment without `published=` or that metadata, so the
mislabel was **latent** — it never reached `EvidenceItem.published_at`, and the live Trending run's GDELT
query failed anyway. It would have been consumed by the temporal guard (which scans item metadata for
`published`/`published_at`) the moment anyone forwarded candidate metadata.

After: candidates carry `gdelt_seen_at` (ISO UTC, or `None`), `gdelt_seen_at_raw`, `gdelt_seen_at_basis =
GDELT_INDEX_OBSERVATION_NOT_PUBLICATION`, `publication_time_basis = UNKNOWN_UNTIL_PUBLISHER_CONTENT`, and no
`published`/`published_at`. The snippet says "Indexed by GDELT (…first seen by GDELT: …)". The catalog
forwards only `gdelt_*` keys. Tests drive the real catalog, `EvidenceItem`, `reconcile_captured_context`
and `temporal_guard`: an unread lead is `MISSING_TIMESTAMP`; a read page with no declaration stays
`MISSING_TIMESTAMP`; a page declaring 2024 is stale; only a publisher declaration inside 48 hours is
eligible. The 48-hour gate itself is unchanged. **Four of the eight GDELT tests fail on the original
`HEAD` files** (checked by temporarily restoring them; SHA-256 verified on restore).

## The 3,454 vs ~7,020 raw-word discrepancy

A measurement-definition issue; no historical result was edited. For the second Trending run the saved
pool reports `raw_article_words` **7,020** (4 article bodies: 2,627 + 2,692 + 900 + 801) and
`raw_source_words` **21,461** (all 14 captures incl. homepages/indexes). The doc's other rows match
[`test_4_agents_word_extraction.py`](../../scripts/evaluation/test_4_agents_word_extraction.py)
("retained unique body words" over report records; Scout 13,589, BrandShield 7,676, Personal 484
reproduce). For Trending that script returns **0**, because the report's `sources` is a channel dict, not
a record list. The pilot run gives 1,701/5,864. **3,454 is not reproducible from any saved Trending
artifact under any definition tried.** Treat the evaluation doc's Trending "Raw Words" cell as
unverified and always state which definition is meant; "raw words" is never useful evidence.

## Commands actually run

| Command | Result |
| --- | --- |
| New + directly affected focused suites (17 files) | exit 0, **384 passed** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | exit 0, **2,313 passed** (35s) |
| `python -m pytest tests/ -q` | exit 0, **2,521 passed** (42s) |
| Fatal flake8 (`E9,F63,F7,F82`) | exit 0, 0 findings |
| 10 Node `tests/frontend/test_*.js` | all exit 0 |
| Frozen verifier / protected-tree `git diff` / `git diff --check` | exit 0 each |

Before the fix the full suite was 2,420 passed. One intermediate run failed
(`test_joint_statement_keeps_speakers_separate`, first-person plural); it led to the design above. Scratch
logs and the saved reports are under the system temp directory and may expire; durable evidence is the
two fixtures and this record.

## Limitations and next actions

- **Plural subject + bare present verb is not recognized** ("Analysts expect…", "Urban areas … include…")
  unless another finite verb is present. Relative-clause verbs do not count. Expert quotations containing
  an unquoted "you" are rejected. These are false negatives by design.
- The lexicon is finite; a verb outside it ("fund" was missing in the first draft) is missed.
- The scorer now sees more candidate paragraphs per source, so selected passages can change.
- Live Trending recall, fresh-source supply and GDELT live productivity (the live query was throttled/failed)
  are unverified. Google Fact Check is still unexercised live.
- Not claimed: independent accuracy, a better live Trending result, hosted CI for these uncommitted edits.
- Suggested order: review the diff; if accepted, commit separately; then one separately authorized,
  bounded Trending live run and compare against the saved baseline using one stated word definition.
