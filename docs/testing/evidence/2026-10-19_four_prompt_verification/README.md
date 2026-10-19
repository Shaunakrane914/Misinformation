# Four-prompt source/output verification — 2026-10-19

[Report, method, failures and reproduction](../../../handoffs/2026-10-19_FOUR_PROMPT_VERIFICATION.md).
[Sanitized measurements](measurements.json).

One new local AI-disabled investigation per agent; screenshots replay exact saved
responses, not new requests or production output. Selected 390px report captures
were visually inspected:

- [Scout / Infosys](01-scout-390-report.png): shallow investor indexes plus a careers page, no findings.
- [Trending / NVIDIA](02-trending-390-report.png): one source-linked unverified observation.
- [BrandShield / Nike](03-brandshield-390-report.png): explicit acquisition-failure warning.
- [Personal Watch / Tim Cook](04-personal_watch-390-report.png): explicit acquisition-failure warning with queue diagnostics.

Rendering checks passed their bounded scope; research-quality acceptance failed.
Full responses/bodies remain temporary, not copied over existing artifacts.
