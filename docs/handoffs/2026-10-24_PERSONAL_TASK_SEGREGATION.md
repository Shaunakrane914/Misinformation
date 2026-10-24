# Personal Watch task segregation — 2026-10-24

## Scope and observed checkpoint

Continue agent-specific interpretation above the existing shared scraper. This
subtask changes only [Personal Watch assessment](../../backend/agents/personal_watch/assessment.py)
and adds [fictional offline controls](../../tests/unit/test_personal_task_segregation.py).
Branch `fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`; substantial inherited dirty work
was preserved. No commit, push, merge, deployment, model or network request.

## Repair and rationale

- A `PUBLIC_STATEMENT` content-role keyword is not speaker attribution. Only
  observed author/speaker/quotation linkage from the existing attribution helper
  can enter `public_statements`; identity and quotation truth remain unverified.
- Disputed/misattributed quotation passages now enter additive `disputed_claims`,
  separately from target speech and identity-threat incidents. Each preserves
  exact passage text, offsets, IDs, source URL and date. `speaker` is null,
  `claim_status`/`epistemic_state` are `UNVERIFIED`, and `assessment_status` is
  `SOURCE_REPORT_ONLY`. A publisher's denial is not independent adjudication.
- Disputes require target linkage in the captured paragraph, not the page title
  alone. Metadata, indexes, snippets and explicitly ineligible records cannot
  become task evidence. Structural capture and existing relevance guards remain.
- Disputes are deduplicated by original passage ID and limited to 16 output
  observations. A denial paragraph cannot also become observed target speech or
  an impersonation incident merely through scam/quotation keywords.
- Input records/nested metadata/existing passage caches are copied before
  annotation. Existing actual attributed quotes and publisher-reported threat
  paths remain covered by the earlier regression suites.

Root integration must export `disputed_claims` from the agent/API/shared report
and render it separately. Do not sum these into authenticated statements,
confirmed threats or independently resolved truth claims.

## Commands actually run

- New controls first: 16 failures reproduced wrong-speaker promotion, missing
  dispute projection and input mutation. Intermediate patch: 56 passed/2 failed
  (past-tense denial and alternate search-snippet label); both fixed explicitly.
- `python -m pytest tests/unit/test_personal_task_segregation.py tests/unit/test_personal_source_reports.py tests/unit/test_harvest_statement_attribution.py tests/unit/test_specialist_completion.py -q --tb=short -p no:cacheprovider`:
  exit 0, **58 passed /2.70s**.
- `python -m pytest tests/unit/test_intelligence_completion.py tests/unit/test_two_layer_pipeline.py tests/unit/test_expanded_agent_projection.py tests/unit/test_research_quality_completion.py -q --tb=short -p no:cacheprovider`:
  exit 0, **63 passed /3.05s**.
- Fatal flake8 for the two code/test files: exit 0, zero findings. Scoped
  `git diff --check`: exit 0.

These synthetic controls prove bounded deterministic behavior, not live recall,
independent research accuracy or successful generalization to every person.
Fresh acquisition and full-suite/CI/browser acceptance are outside this subtask;
the root continuation records the actual combined verification.
