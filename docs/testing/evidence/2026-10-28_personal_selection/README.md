# Personal selection and transcript evidence — 2026-10-28

- [Measurement matrix](measurements.json): three initial live investigations,
  one later Mary Barra live investigation, and two final native offline replays.
  Replay acquisition counts are saved historical observations, not new reads.
- [Initial live runtime/AI accounting](live-runtime-accounting.json) and
  [later Mary runtime/AI accounting](mary-postfix-runtime-accounting.json):
  stable per-run fingerprints, shared reservations, two successful suggestions
  and one timeout with unknown usage. No generated text is research evidence.
- [Final local browser replay measurements](browser-final-summary.json): six states,
  exact text across all workbench pages, current/background distinction,
  no observed horizontal overflow or uncaught page exceptions.
- [Fei mobile screenshot](browser-final-fei-390.png) and
  [Mary desktop screenshot](browser-final-mary-1440.png): visually inspected first-page
  workbench views; not full investigation or accessibility evidence.
- [Final gates](final-gates.json), [initial failed closeout](initial-gates.json)
  and [intermediate rerun](intermediate-regression.json): actual command scopes,
  exits and results. Final 2,831 full / 2,623 fast tests pass; historical archive
  and deployed rollback remain unverified by isolated persistence.

The earlier [pre-surname-correction browser matrix](browser-summary.json) and
its screenshots remain preserved. Final Mary output includes one reported
quotation and separate commentary; earlier output retained only commentary.
The measurement JSON labels that earlier offline stage explicitly as interim.

Full source bodies, SSE, raw logs, intermediary failures and additional screenshots
are in system-temp basename `aegis-personal-selection-20261028-cafk_ckt` and may
expire. Source identity/date/body hashes were preserved during final native replay.
No bodies, snippets or model suggestions were invented to fill missing evidence.

See [the report](../../PERSONAL_SELECTION_AND_TRANSCRIPT_REPAIR_2026-10-28.md)
for research limitations, code and test references. No changes from this
continuation were committed, pushed or deployed.
