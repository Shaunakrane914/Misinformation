# Adobe post-fix live check — 2026-10-20

## Decision

**Autonomous article acquisition demonstrated for this one Adobe case. Research
quality remains PARTIAL / not accepted.** The native reader acquired a genuine
publisher-page body through a link observed on a query-discovered newsroom.
The resulting finding is only an earnings-call heading, not the substantive
corporate announcement. This is now a measured downstream qualification/selection
defect, not evidence that scraping failed or that useful text was unavailable.

User separately authorized exactly one local Scout/Adobe POST, 120-second ceiling,
six deep-reader attempts, AI disabled, no audit-level retries or deployment.
That request ran once and is complete. No further live case was run.

[Measurements and screenshot](evidence/2026-10-20_adobe_postfix/README.md) ·
[Handoff](../handoffs/2026-10-20_ADOBE_POSTFIX_CHECK.md) ·
[Earlier repair report](AUTONOMOUS_DISCOVERY_REPAIR_2026-10-20.md).

## Code and runtime identity

Branch `fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, plus preserved dirty implementation.
Application fingerprint before and after:
`93fa5595adbebce17f21b3ecbce9797cc843f0361b748ae3d5402ea83dd26fc8`.
This matches the final code from the preceding repair. No application, test,
script, secret, provider-policy or deployment configuration changed this turn.
Only fresh proof and documentation were added/updated. No commit or push.

## Actual fresh funnel

| Observation | Result |
| --- | ---: |
| End-to-end local elapsed | 44.39 seconds |
| Initial generated queries / main lifecycle records | 13 / 17 |
| Instrumented provider invocations / observed responses | 53 / 51 |
| Sampled URL decisions / discarded decisions | 387 / 296 |
| Normalized / accepted candidates, including later leads | 23 / 23 |
| Selected acquisition attempts | 5 of maximum 6 |
| Successful captures | 3 |
| Real article bodies | 1 |
| Article retained text | **842 whitespace words / 5,957 UTF-8 bytes / 5.957 decimal KB** |
| All three captures together | 1,961 words / 14.492 decimal KB |
| Pipeline-qualified items / findings | 1 / 1, but heading-only finding is not research acceptance |
| Research budget remaining after processing | About 75.8 seconds |

Provider decisions can repeat URLs across searches; these are not 387 unique
sources or complete HTTP accounting. Legacy fallback transport is uninstrumented.
Two captures are landing/newsroom context, not articles. The 842-word article
capture itself includes publisher boilerplate and CMS labels; not all words are
useful evidence. Word count is not accuracy, relevance or independent corroboration.

### Provenance chain, with no manually supplied URL

```text
Scout input: Adobe
  → native search observation of news.adobe.com/
  → native HTTP read of that newsroom (HTTP 200)
  → observed "Read more" link to a dated corporate announcement
  → bounded publisher-link selection
  → native_http_reader HTTP 200, 112.25ms
  → acquired record ev_page_cc47517fb870, 842 retained words
  → shared report citation availability SOURCE_RECORD
```

The acquired URL was
`https://news.adobe.com/news/2026/09/adobe-announces-anil-chakravarthy-to-become-president-and-ceo`.
It came from the fetched newsroom, not an externally researched URL or a test
fixture. Parent ID `ev_f4b9204e3102`; acquisition attempt `acq_att_ea49157412`;
acquired ID `cand_acq_ev_page_cc47517fb870`. The captured source contains a
substantive leadership-announcement paragraph and its stated effective date.
This verifies acquisition/provenance, not independent truth of the announcement.

Asset links were rejected as `NON_DOCUMENT_ASSET`; no icon was read. The other
failed attempts were Reuters HTTP 401 and an unresolved Google News wrapper.
Its nested search returned a matching wrapper, correctly rejected as WRAPPER_URL,
not misrepresented as a directly read publisher article. Yahoo still returned
HTTP 500s; unrelated results were retained only as rejection diagnostics.

Compared with the earlier Adobe run: four home/news/index/icon captures and zero
real articles became three captures including one real article; five attempts in
both runs. These are separate live observations, not an identical-response
controlled experiment or proof of a recall/accuracy percentage.

## Remaining interpretation and presentation defects

1. [PassageExtractor.extract_passages](../../backend/services/research/passage_extractor.py)
   calls [matches_objective](../../backend/services/research/content_roles.py)
   before scoring. The financial terms exclude the actual leadership-announcement
   paragraph. The short earnings heading passes because it contains `earnings`.
   [has_usable_passage](../../backend/services/research/passage_extractor.py) accepts
   signal words without requiring a full proposition. The selected span is
   **4254–4297**, just the 43-character heading. The deeper passage inspection
   already retains the substantive announcement at **194–701** in the same body.
2. [DeepReader.deep_read](../../backend/services/research/deep_reader.py) stores
   the captured page title in metadata, but keeps the discovery anchor as the
   record title. [synthesize_grounded_findings](../../backend/application/research/synthesis.py)
   consequently emits `Observed Publisher Article: Read more` as its title.
3. Publication metadata remains empty although the captured body has a date.
   Temporal status is UNKNOWN, and the selected earnings-call date is historical
   relative to this investigation. Source declaration, announcement effective
   date and publication date must remain distinct; do not guess them into fields.
4. Readable text still includes CMS/style/card labels. Raw capture preservation
   is correct, but those labels should not compete with substantive propositions.

The shared report preserves the acquired evidence ID and displays the same weak
finding returned by the backend. It is labeled UNVERIFIED with entailment not
verified; no broken citation join or missing frontend finding was observed here.
The misinformation assessment remains INSUFFICIENT_EVIDENCE / UNASSESSED, no
financial facts or primary filing reported. Do not describe this as completed
financial reasoning or independent corroboration.

No implementation correction was made in this verification-only continuation.
The next focused change can use these saved bytes for offline passage/title/date
regressions; another live source sweep is unnecessary to reproduce this defect.

## Verification actually run

| Check | Result |
| --- | --- |
| Authorized terminal investigation | Exit 0; one result event, no SSE error, 44.39s; mocks off, zero live AI |
| Saved-result read-only summarizer | Exit 0; native response/source hashes stored |
| `python -m pytest tests/ -q` | Exit 0; **1,532 passed / 51.46s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **1,324 passed / 34.43s** |
| Fatal flake8 command / frozen verifier | Exit 0; zero fatal findings / hashes match |
| All nine Node frontend scripts | Exit 0 each |
| Release smoke, new output | Exit 0; OFFLINE_SMOKE_PASS |
| Rollback validator, new output | Exit 0; OFFLINE_PERSISTENCE_PASS; historical archive/deployed rollback NOT_VERIFIED |
| Protected Git diff / diff whitespace | Exit 0; no protected-file mutation |
| Exact fresh-response browser replay | Exit 0; three states at 320/390/1440px; matching 1 finding, 3 source cards, 19 discovery cards; no horizontal overflow or uncaught page exception |

Browser mode used the E2E-testing skill's isolated saved-data approach: real Scout
button and renderers, exact captured SSE, readiness stubbed, all other API calls
blocked. **No second provider investigation.** The desktop report screenshot was
visually inspected and shows the same earnings heading. Source inspection opened
by keyboard at each width. Blocked fonts/harness resource errors are disclosed in
the browser summary; this is not a complete accessibility or console-clean claim.

Full logs/captures reside in new system-temp tree
`aegis-adobe-postfix-d2231ffc-f101-4356-82d6-2a7a965e0eeb` under `live`, `browser`
and gate logs. Durable selected proof is linked above. Secrets and full bodies
were not copied into the report. Prior datasets, dossiers and proof preserved.

**Not verified:** consistent success across subjects/providers, Dyson after the
scheduling change, other agents, independent accuracy, hosted CI, production
parity, historical recovery or launch readiness. No push, merge or deployment.
