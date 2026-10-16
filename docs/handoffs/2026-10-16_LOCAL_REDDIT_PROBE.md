# Local Reddit gate-enabled probe — 2026-10-16

## Request and scope

The operator explicitly requested setting `REDDIT_APPROVED_ACCESS=true` locally
and measuring the existing subreddit acquisition pipeline. This supersedes the
earlier instruction to retain the local block for this diagnostic; it is not
evidence of provider authorization or permission to enable production.

The ignored `.env` in the original IDE checkout was updated by adding that flag
and an explanatory comment; existing credentials and other settings were not
edited or displayed. It remains enabled locally. The RSS and Arctic Shift flags
were absent, so existing adapter defaults applied. No server environment,
deployment, scraper implementation, frozen dataset or historical dossier changed.

Observed original branch/base: `feat/phase8-real-acquisition-proof`,
`1e1c44e89ff635974150770d5d4cea1e9c9fb19e`. The diagnostic imported the current
release checkout, `release/phase9-acquisition-20261015`,
`ff6d246bfe1e9cfd0f21d8e32135582e631636f1`. Both worktrees were initially clean.
Do not mistake the original IDE checkout for the deployed source version.

## Actual live observations

A fresh Python process read the local flag and called
`NativeRouter.execute_channel_query(platform="reddit", operation="read",
query="r/<subreddit>", limit=5)` for each community, sequentially.
Before dispatch, the capability assessment was `ELIGIBLE_UNVERIFIED`, not
`EXCLUDE`. The router, rather than a direct helper bypass, performed acquisition.
Observation window: 2026-10-16 05:18:33–05:18:38 UTC (10:48:33–10:48:38 IST).

| Subreddit | Records | Returned UTF-8 bytes | KB | Words | Transport |
|---|---:|---:|---:|---:|---|
| IndianStreetBets | 5 | 2,606 | 2.606 | 343 | Reddit RSS; feed-entry summaries |
| IndianStockMarket | 5 | 1,077 | 1.077 | 199 | RSS 429, then existing Arctic Shift fallback |
| stocks | 5 | 3,190 | 3.190 | 582 | RSS 429, then existing Arctic Shift fallback |
| Total | 15 | 6,873 | 6.873 | 1,124 | Mixed provenance; not all direct Reddit |

Each dispatcher response reported `SUCCESS` and `network_observed=true`.
That does not establish the freshness of the original Reddit records returned
by a third-party archive. No repeated RSS retries or rate-limit bypass was added.

KB means 1,000 bytes. Words are whitespace-delimited tokens in each returned
fragment's `content` (or `snippet` if content is absent), without separately
counting titles. Counts can include feed boilerplate, links and removal markers;
they are not counts of relevant factual assertions. The existing clean-content
helper counted 259 / 199 / 582 words respectively after removing known feed
boilerplate and URLs; even those 1,040 tokens are not validated usable evidence.
No complete-thread, comment-coverage, maximum-capacity or company-specific
relevance claim is established by these three explicit-feed samples.

Metrics and public record URLs were saved to a fresh system temporary
`aegis-reddit-enabled-*` directory. Discussion bodies were measured in memory,
not saved. Temporary outputs are not a durable artifact or hosted CI record;
this handoff retains the aggregate observations. No secrets are included.

## Ownership and checks

- Gate: [operation capabilities](../../backend/services/agent_reach/native/operation_capabilities.py).
- Dispatch early return: [channel dispatcher](../../backend/infrastructure/acquisition/routing/channel_dispatcher.py).
- Existing direct-subreddit and fallback paths: [social handlers](../../backend/infrastructure/acquisition/routing/social_handlers.py).
- Existing RSS/archive adapters: [Reddit adapter](../../backend/infrastructure/acquisition/adapters/social/reddit.py).
- Existing taxonomy and clean-text helper: [social resolver](../../backend/infrastructure/acquisition/resolution/social_resolver.py).

Reconstructed execution record, not a verbatim transcript:

| Command/check actually run | Exit | Result |
|---|---:|---|
| Initial `git status --short` / `git diff --stat` | 0 | Clean original checkout; release checkout also clean before this handoff |
| `git check-ignore .env` | 0 | Local `.env` ignored |
| Exact local true-assignment check | 0 | One `REDDIT_APPROVED_ACCESS=true` assignment |
| Inline Python live dispatcher probe described above | 0 | Three samples; 15 records / 1,124 returned-text words |
| `python -m pytest tests/unit/test_zero_auth_social_retrieval.py tests/unit/test_phase6_8_social_resolution.py -q` in release checkout | 0 | 31 passed in 1.15s |
| `git diff --check` before adding this handoff | 0 | No application-source diff |

No full regression suite was rerun for this local flag-only diagnostic. Existing
unit tests do not independently verify provider access or the measured live words.
No commit, push, deployment or hosted CI run was performed. Production retains
its previous configuration. An already-running local process is not proven to
have reloaded `.env`; the fresh diagnostic process explicitly loaded the flag.

The earlier missing-data diagnosis remains separate: report field mappings,
query telemetry, deep-read availability and subreddit taxonomy gaps are not
fixed by opening this gate. The configured flag is a local override, not an
access credential; future agents must preserve the local/production distinction
and must not treat HTTP 429 or stale archive content as an original-source PASS.
