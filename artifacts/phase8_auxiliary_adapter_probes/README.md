# Phase 8B auxiliary direct-adapter spot-checks

These append-only observations exercise the separate legacy-compatible
`GitHubAdapter`, `WebAdapter` and `YouTubeAdapter` paths. They do **not** exercise
the 16 protected recovered-operation routes or establish extraction
completeness, difficult-case reliability, security of all nested provider
requests, or deployed health.

Run from the intended checkout with
`python -m scripts.audits.run_phase8_auxiliary_adapter_probe`.
The runner uses three fixed public URLs and writes only status, lengths,
field-presence and key-name metadata to a new timestamped directory. It does
not retain response bodies, evidence text, credentials, or provider secrets.
An artifact's `dirty_worktree` and `git_head` describe execution time, not a
later commit or CI result.

| Observation | Scope | Outcome |
|---|---|---|
| [2026-10-13 08:59:48Z](2026-10-13_08-59-48Z/summary.json) | One fixed public target each for GitHub, web and YouTube; code checkout was dirty at run time. | 3/3 returned `SUCCESS` with one normalized fragment each. GitHub author/publication remained absent; web was a snippet, not a full article. No provider-completeness conclusion. |
