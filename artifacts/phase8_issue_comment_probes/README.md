# Phase 8B bounded GitHub issue-comment spot-checks

These are append-only observations of the *opt-in* `github.issues`
`include_comments=True` path. The list request is capped at three returned
issues; at most two actual issue-comment follow-up requests are made, with at
most two comments per issue in these probes. Only issue identifiers/URLs,
status, counts, field-presence and transport-observation flags are retained.
No issue body or comment text is saved. GitHub's
[issue-comment API documentation](https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28)
supports the public endpoint; these runs do not prove a complete discussion,
pagination, deleted history or provider-wide availability.

| Run | Observation | Interpretation |
|---|---|---|
| [2026-10-13 09:27:47Z](2026-10-13_09-27-47Z/summary.json) | Dirty pre-fix run, three issues; two zero-comment issues consumed the positional budget and the third was skipped. | Negative regression evidence. Do not use as successful comment-acquisition proof. |
| [2026-10-13 14:18:15Z](2026-10-13_14-18-15Z/summary.json) | Dirty worktree after budget fix, three issues; one actual comment follow-up observed one source-linked, dated, attributed comment. | Bounded positive sample only. A post-commit clean run and CI are still required before treating the implementation as a verified checkpoint. |
