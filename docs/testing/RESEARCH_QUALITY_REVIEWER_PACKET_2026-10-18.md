# Research-quality reviewer packet — 2026-10-18

Status: **PREPARED — independent labels and acceptance pending.**
This packet contains a procedure and unfilled case slots, not a ground-truth
dataset, completed review, or evidence that the release is ready. Existing
coding-agent tests and source examples are calibration only.

## Roles and separation

- Reviewer: someone other than the implementer selects new claims, independently
  reads the relevant sources, assigns expected answers, and freezes labels.
- Operator: runs the frozen requests once through the terminal harness with AI
  disabled, records the actual commit plus dirty patch hash and environment,
  and exports observations without altering the report's meaning.
- Adjudicator: reviews source entailment, contradictions and practical usefulness.
  Prefer a second person for disputed labels. Record disagreements rather than
  silently choosing the model/agent answer.

Do not put credentials, private individuals' personal data, or doxxing material
in cases. Public-figure cases should concern public statements or publicly
documented impersonation, not private contact details. Do not contact alleged
attackers or perform purchases/takedowns. Preserve access gates.

## Select held-out cases before running or tuning

Choose **24 new cases, six per agent**, not cases already used in the
[four-agent audit](FOUR_AGENT_OUTPUT_AUDIT_2026-10-16.md) or the implementer's
regression tests. If a case is exposed during tuning, retire it from acceptance
and retain it as calibration; replace it with a newly reviewed case. Small
samples have uncertainty: publish counts, not a sweeping reliability claim.

Fill every slot with a precise proposition, target, query, evaluation cutoff
and expected behavior. The scenario below is a selection constraint, **not an
answer**. One entity-name-only exploration per agent may be scored by the
manual rubric rather than forcibly assigning a proposition verdict.

| Case IDs | Reviewer-selected scenario |
| --- | --- |
| BS-01 | Direct unauthorized-offer evidence; distinguish seller from publisher |
| BS-02 | Enforcement reporting; distinguish allegation, charge and disposition |
| BS-03 | Protective anti-scam notice, not an attacker listing |
| BS-04 | Specific legitimate customer complaint, not proof of counterfeit |
| BS-05 | Debunked or disputed accusation with qualification preserved |
| BS-06 | New brand exploration, sparse evidence or ambiguous entity |
| PW-01 | Attributed public quotation with original context |
| PW-02 | False-quotation allegation requiring original-source comparison |
| PW-03 | Reported impersonation, without asserting identity authentication |
| PW-04 | Joint statement with multiple speakers and negation |
| PW-05 | Previously unseen public figure with ambiguous names |
| PW-06 | Profile-only/blocked discovery; appropriate abstention |
| SC-01 | Reported financial figure with exact period/currency/basis |
| SC-02 | Same quantity expressed in different monetary scales |
| SC-03 | Conflicting values requiring comparable reporting context |
| SC-04 | Guidance/range versus actual results |
| SC-05 | Table with units, date and consolidated/segment distinction |
| SC-06 | Missing or incomparable filing; appropriate abstention |
| TR-01 | Multiple articles about one underlying announcement |
| TR-02 | Reprinted/syndicated stories, not independent corroboration |
| TR-03 | Chronologically distinct observations with actual timestamps |
| TR-04 | Single snapshot; no unsupported velocity/virality claim |
| TR-05 | Contradictory or corrected narrative with attribution |
| TR-06 | New topic with insufficient relevant observations |

For proposition scoring, balance the three expected verdicts where practical
without inventing claims or forcing a false balance. Record when a case cannot
be adjudicated. A world-truth label and what the captured evidence permits are
different: use the latter for the evidence-grounded verdict and retain the
former as a separate reviewer note with references.

## What the reviewer records per case

1. Stable case ID, agent, exact user input/query, proposition (if any), as-of
   timestamp, locale, reporting period, currency/unit and other necessary context.
2. Expected verdict: `SUPPORTED`, `REFUTED`, or `INSUFFICIENT_EVIDENCE` for a
   proposition. Do not map `NOMINAL`, `LOW`, `KNOWN_FACT`, a risk score or a
   successful HTTP response into one of these verdicts automatically.
3. Independently checked relevant source URLs, publisher, publication date,
   retrieval time, and concise rationale linking passages to the proposition.
   Separate primary/secondary/discovery sources and publisher/actor roles.
4. Exact supporting/contradicting source passages, offsets in the retained text,
   content SHA-256, qualifications, corrections and ownership uncertainties.
5. Expected abstention reason, missing evidence and useful next action where
   applicable. An unavailable source is not a negative finding.
6. Source independence and temporal observation requirements; more URLs, words,
   or repeated fetches do not establish corroboration or trend acceleration.

Archive captures legally in a new reviewer-controlled directory, never in the
frozen retrieval benchmarks or historical dossiers. Keep full captures out of
Git unless reviewed for licensing, secrets and personal data.

## Freeze and execute

Each filled label case has this shape (placeholders, **not reviewed answers**):

```json
{"case_id":"REVIEWER_CASE_ID","agent":"brandshield","input":"REVIEWER_TARGET","query":"REVIEWER_QUERY","as_of":"REVIEWER_ISO_TIMESTAMP","claim":"REVIEWER_PROPOSITION","verdict":"REVIEWER_CHOSEN_VERDICT","relevant_urls":["REVIEWER_CHECKED_URL"],"rationale":"REVIEWER_PASSAGE_AND_CONTEXT_NOTES"}
```

Each observation has this shape. Offsets are zero-based Python Unicode character
positions, end-exclusive, in the exact UTF-8-decoded retained source content;
hashes are SHA-256 of that content encoded as UTF-8, not of its JSON envelope.
Do not replace the agent's prediction with the reviewer's label.

```json
{"case_id":"REVIEWER_CASE_ID","verdict":"ACTUAL_EXPLICIT_VERDICT","sources":[{"evidence_id":"CANONICAL_CAPTURE_ID","url":"ACTUAL_SOURCE_URL","content":"EXACT_RETAINED_CONTENT","content_sha256":"ACTUAL_SHA256"}],"citations":[{"evidence_id":"CANONICAL_CAPTURE_ID","start":0,"end":5,"text":"EXACT"}]}
```

These examples are intentionally not valid scoring inputs until replaced. For
exploratory cases without a proposition/explicit verdict, use a separate manual
rubric sheet and denominator; do not include invented verdicts to satisfy the
automated scorer's schema. Record automated verdict-contract coverage too.

1. Copy the [label template](reviewer_packets/2026-10-18/labels.template.json)
   to a new private review directory. Fill the labels independently; keep
   `label_origin` pending until review is actually complete. Freeze the exact
   UTF-8 bytes and record their SHA-256 in a separately held manifest **before**
   running acceptance or changing code for those cases.
2. Record reviewer/adjudicator names or stable identifiers, ISO timestamp,
   selection method, case exclusions, review disagreements and predeclared
   acceptance thresholds. The scorer cannot verify a person's independence.
3. Run the normal AI-disabled terminal harness, one request per case. Never use
   `--allow-live-ai`. Use a new temporary output directory and no notification
   recipients. Example from the repository root (PowerShell):

   ```powershell
   $runDir = Join-Path $env:TEMP ('aegis-heldout-' + [guid]::NewGuid())
   python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file .env --output-dir $runDir --case 'brandshield:REVIEWER_TARGET' --query 'REVIEWER_EXACT_QUERY'
   ```

   These are placeholders, not a test already run. Use `scout`, `trending`,
   `brandshield`, or `personal_watch` case prefixes. When supplying `--query`,
   supply exactly one per case. Record blocked/deadline/failure outcomes;
   don't rerun until success and discard failures. Guided source-URL requests
   must be scored separately from one-line discovery.
4. Retain full raw JSON, SSE events, pipeline projections, version fingerprint
   and logs locally. Record which process loaded which configuration, without
   copying secrets. Reprocess captures offline for diagnosis **after** the
   acceptance observation is locked; a polished replay is not fresh retrieval.
5. Export the actual observations using the
   [observation template](reviewer_packets/2026-10-18/observations.template.json).
   This export currently requires explicit operator mapping; there is no
   automatic safe conversion from every native agent risk taxonomy. Missing
   proposition verdicts remain a contract/acceptance gap, not a guessed label.
6. Score, pointing to the separately recorded frozen digest:

   ```powershell
   python scripts/evaluation/evaluate_research_quality.py --observations review/observations.json --labels review/labels.json --labels-sha256 REVIEWER_FROZEN_SHA256 --output review/score-new.json
   ```

   The evaluator performs no network/model calls, verifies label and captured
   source hashes, requires exact case coverage, and refuses an existing output
   file. Empty/pending labels cannot establish acceptance. Do not generate the
   frozen digest from mutable labels at scoring time and call that a freeze.

## Automated measurements versus human acceptance

| Measurement | Definition and limitation |
| --- | --- |
| Correct verdict rate | Exact verdict matches / proposition cases; report per agent and overall |
| Incorrect decisive verdicts | Wrong `SUPPORTED`/`REFUTED`, including when abstention was required |
| Abstention precision | Correct abstentions / all abstentions; `null` if none |
| Relevant-source recall | Expected relevant exact URLs acquired / reviewed relevant URLs; not whole-web recall |
| Citation span validity | Canonical ID plus exact nonempty text/offsets in hashed source; **not entailment** |
| Acquisition quality | Reviewer checks acquired body, target relevance, source type, failures, and attribution |
| Citation entailment | Reviewer checks the passage actually supports the stated proposition, period and qualifications |
| Usefulness | Reviewer checks the answer addresses the actual job, explains uncertainty and proposes case-specific next steps |

For human checks, assign `PASS`, `PARTIAL`, `FAIL`, or `NOT_VERIFIED`, with a
short source-backed explanation and severity for errors. Block acceptance for
fabricated evidence, unsupported decisive findings, reporter-as-attacker errors,
misattributed speakers, or hidden missing evidence. Predeclare quantitative
thresholds and acceptable abstention coverage with the project owner **before**
scoring; this packet does not invent a passing threshold after seeing results.

## Frontend follow-through and release boundary

Replay the locked outputs through actual agent-page controls and shared/native
renderers at mobile and desktop widths. Verify summaries, citations, source
inspection, contradictions, uncertainty and progress/failure states against the
saved JSON. Label stubbed transport as replay, not deployed integration.
Record keyboard, accessibility and browser coverage actually performed.

Cloudflare/Render deployed routing, SSE, source inspection and generation-disabled
configuration need separate read-only/safely configured production verification.
Offline tests and reviewer scoring do not authorize deployment or prove hosted
CI, provider access, production parity or launch readiness. Do not unblock those
gates merely because this packet exists.
