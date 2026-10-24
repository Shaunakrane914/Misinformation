# Scout and Personal Watch source-to-report completion — 2026-10-20

This scoped continuation belongs to the final four-agent completion task. See the
[expanded harvesting baseline](2026-10-20_EXPANDED_HARVESTING.md). It is not a new
live source check, independent truth evaluation or deployment approval.

Checkout: `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, base
`39a514b68388450bbc5e6061aba97bda2077fc7f`, with inherited dirty work preserved.
No commit, push, merge, deployment, credential change or protected-data write.

## Demonstrated defects and corrections

- `personal_watch/monitoring.py`: normalizing typed research evidence used the
  public-inspection metadata projection, which omitted `read_success`, observed
  article structure and acquisition objective. The incidental quotation rule
  therefore passed raw-pool requalification but disappeared in the full agent.
  The adapter now retains a small allowlist of those capture markers without
  forwarding arbitrary provider metadata or authenticating identity.
- `research/passage_records.py`: explicit speaker linkage no longer accepts an
  arbitrary 80-character gap containing a different speaker. Actual quotation
  text has its own exact retained-body offsets. An explicitly labeled terminal
  `(Also read: ...)` link is excluded from the selected personal passage, not
  from raw article text/hash. Contextual qualifications and negations survive.
- `personal_watch/assessment.py` and `agent.py`: public statements explicitly
  remain reported and UNVERIFIED, not authenticated identities. Missing identity
  and impersonation assessments are UNASSESSED. Secondary text overlap is not
  evidence of viral circulation. Contextual entity descriptions no longer say
  the subject is confirmed.
- `personal_watch/dossier.py`: baseline descriptions explain that no prior window
  exists. A prior allegation absent from the next sample is NOT_REOBSERVED,
  not a resolved threat. A newly sampled platform does not prove propagation.
- `research/passage_extractor.py`: the financial selection branch prefers an
  actual target financial proposition over incidental comparison figures. The
  Samsung Korea Times source now selects the Samsung estimate instead of
  Aramco's 2022 comparator, while raw captures remain unchanged.
- `scout/assessment.py`: directional heuristics respect whole metric words,
  plurals and end boundaries. Forecasts/analyst opinions remain unresolved;
  headlines cannot override the acquired passage. A name such as `Dong-won`
  is not a KRW currency marker. Per-source observations retain exact passage
  references, observed currencies/period labels and extended entity names,
  without reconciling affiliates, converting currency or inventing fiscal dates.
- `scout/agent.py`: publishes those financial observations and an explicit
  `filing_comparison.status = NOT_PERFORMED`; article counts never establish
  completed filing reconciliation or independent corroboration.

## Reusable genuine-source replay

[Replay CLI](../../scripts/audits/replay_specialist_completion.py) replaces only
`HarvestingEngine.run` with hash-validated saved source records. Current body
qualification, passage selection, synthesis, specialist agent, API and SSE code
run normally in an isolated ASGI agent-router app. No background lifespan runs.
All network transports are blocked before application imports. Real and synthetic
gateway generation is hard-blocked; any attempted generation fails acceptance.
Existing quote observations or honest quote absence are replayed, never fetched.

```text
python scripts/audits/replay_specialist_completion.py --input <saved-native-response.json> --output-dir <new-directory> --agent personal_watch --subject "Sundar Pichai"
python scripts/audits/replay_specialist_completion.py --input <saved-native-response.json> --output-dir <new-directory> --agent scout --subject Samsung
```

These commands do not prove new discovery/provider health. The SSE progress events
describe newly executed offline processing, not original live search progress.
Replay read counters describe reconstructed successful captures, not all original
provider attempts; consult the untouched source responses for live failures and
latency. The manifest records this boundary and original input hash explicitly.

## Actual observations

Inputs are the original two post-fix native responses under system-temp basename
`aegis-expanded-harvest-976b78ac9bad4aa1a362ab1cd9d3339c/postfix`.
Final current API results/events/manifests are under system-temp basename
`aegis-final-four-agent-f01d3247011f4e2c826da0357a420e4f`, in `replay-scout` and
`replay-personal`. Temp storage can expire. No full articles are republished here.

| Replay | Preserved article bodies / words | Qualified sources / passage words | Current output |
| --- | ---: | ---: | --- |
| Samsung | 7 / 6,544 | 7 / 805 | Six UNVERIFIED source observations; seven financial-context records; zero inferred positive/negative catalysts; filing comparison NOT_PERFORMED |
| Sundar Pichai | 5 / 4,161 | 1 / 53 | One reported quotation and source-context passage; identity and impersonation UNASSESSED |

Every original raw record's ID, URL, title, publication value and retained body/hash
was checked unchanged (29 Samsung / 39 Pichai raw records). Each API SSE pass
returned one result, no SSE error and 20 actual offline-processing progress events.
No new network or model calls occurred. Different publisher hosts are not proven
independent origins; Samsung affiliates and forecasts are not reconciled facts.

Pichai's exact source-context offsets are 926–1258 and quotation-only offsets
991–1076 in source `ev_hv_840b35593560935f15ca`. It is the publisher's reported
attribution, not authentication of a recording, an identity or the quotation's
truth. The other four articles remain raw/inspectable, not four identity findings.

## Tests actually run

- Initial focused set: 40 passed, exit 0.
- Personal Watch/Phase 8C expanded focused set: 72 passed, exit 0.
- Final specialist, attribution, substantive, expanded-projection and native
  preservation set: **82 passed / 3.69s**, exit 0.
- Fourteen new focused controls are in
  [test_specialist_completion.py](../../tests/unit/test_specialist_completion.py).
- Both final genuine-source API/SSE replay CLI commands exited 0.

Full/fast/fatal-lint/frontend/smoke/browser acceptance is owned by the coordinating
four-agent closeout. Do not infer those results from this scoped record.

## Remaining limits

This proves current saved-source interpretation reaches the actual local API/SSE
contract; it does not repeat Samsung/Pichai live acquisition or establish broad
financial/identity accuracy. There is no primary filing reconciliation, numerical
claim entailment certification, authenticated identity or media forensics. Browser
validation and the two separately authorized unresolved acquisition checks belong
to the parent task. No extra live scan, paid model call or deployment is authorized
by this handoff.
