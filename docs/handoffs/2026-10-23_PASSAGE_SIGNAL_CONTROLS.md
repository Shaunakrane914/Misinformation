# Exact financial-passage selection and currency controls — 2026-10-23

Subtask of the scraper-reliability continuation, not independent research or
release acceptance. Checkout `fix/p0-lenovo-acquisition-20261018`, base
`39a514b68388450bbc5e6061aba97bda2077fc7f`, with preserved inherited dirty work.
No commit, push, merge, deployment, model call or new provider request.

## Corrections and boundaries

- [Content roles](../../backend/services/research/content_roles.py): standalone
  interrogative questions and explicit answer-selection prompts cannot become
  asserted findings merely because they contain the subject, numbers or
  financial verbs. Reported quotations, warnings, incident accounts and complete
  question-and-answer paragraphs remain eligible under the existing gates.
- [Passage selection](../../backend/services/research/passage_extractor.py):
  retain exact source paragraphs and offsets; reject an exact captured source
  title even when the older capture lacks an H1 block. Give explicit financial
  amounts greater selection priority than webcast logistics or company lists.
  Exact reported/attributed-speech verbs are usable; domain, subject, structural,
  freshness and access gates are unchanged. No raw body is deleted or rewritten.
- [Financial context](../../backend/services/research/financial_context.py):
  prompts cannot unlock financial assessment or produce monetary assertions.
  Nearby consensus/forecast ranges keep `FORECAST_OR_ESTIMATE` roles separately
  from observed reported values. This is conservative lexical classification,
  not amount/issuer/fiscal-period verification.
- [Financial observations](../../backend/services/research/financial_observations.py):
  a bare dollar glyph is `DOLLAR_SYMBOL_UNSPECIFIED`, never invented USD.
  Explicit US$/USD, INR, EUR and GBP labels remain supported with exact spans.
  Comparisons abstain on ambiguous currency, including two equal bare-dollar
  amounts; no currency conversion is performed. Existing fictional comparison
  controls now use explicit USD for valid match/mismatch positive cases.

## Actual offline proof

[23 new adversarial controls](../../tests/unit/test_oct23_passage_signal.py)
use fictional held-out subjects. Before implementation, the initial 15-control
run returned **11 failures / 4 passes**, exposing both false assertions and
false rejection of reported speech/warnings. After implementation:

- Latest financial/passage group: **106 passed / 1.91s**, exit 0.
- Earlier extended selection group: **116 passed / 2.01s**, exit 0.
- Additional brand/personal/trending/requalification impacts: **143 passed /
  3.73s**, exit 0. These overlap, so totals must not be added as unique tests.
- Fatal lint on owned implementation/tests: exit 0, zero findings.
- Owned-file whitespace check: exit 0.

All these Python checks first applied `isolated_environment()` to new system-temp
storage and `block_live_network()` before application imports. AI credentials
and optional integrations were disabled. Full/fast regression and any subsequent
authorized live verification belong to the coordinating continuation, not this
focused subtask.

## Genuine saved-source replay, not live acquisition

The prior authorized native batch remains under system-temp basename
`aegis-native-strength-22672d05ff0849d19830f006ba744ae2`. Read-only reselection of
its nine Adobe article records verifies unchanged body hashes and exact excerpt
offsets. Raw article text remains **9,460 words**; selected words **420 → 411**.
This reduction removes noise; it is not a scraper-volume gain.

- The captured financial quiz question: selected **17 → 0 words**.
- The captured earnings release: webcast logistics **55 words** replaced with
  its actual source-reported revenue/GAAP/non-GAAP paragraph **39 words**.
- CryptoBriefing's **53-word** full paragraph survives rather than its repeated
  title becoming a finding. Historical captures keep their original dates and
  historical labels. No source assertion becomes independently verified.

Remaining limitation: a multi-company earnings preview can still supply sector
results alongside a target mention; exact issuer-level entailment is not solved.
Prioritize a qualified target-performance passage for the executive brief, but
do not claim that source ordering itself proves financial correctness. The
financial helper is not a complete parser for tables, every currency or all
forecast/actual clause combinations. Broader independent accuracy, browser
acceptance and live discovery strength remain separate checks.
