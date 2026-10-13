# Phase 8B bounded GitHub issue-discussion follow-up — 2026-10-13

## Scope and implementation decisions

The user asked to continue the Phase 8 work, with durable code/test/evidence
handoffs. This change remained in the isolated `feat/phase8b-extraction`
worktree because another coding agent used the original Phase 8 branch. It
started from `f4640f2e03174e00dd4c813db05faace4e505c9a`, which passed
[all five jobs in hosted CI run 38375744471](https://github.com/Shaunakrane914/Misinformation/actions/runs/38375744471).
The implementation and initial live observations were committed and pushed as
`2530ae88b78423c4272abab249ee493b57e7a43d`. The final clean-commit
observations and this handoff are append-only follow-up documentation; check
their exact final commit and push with `git status --short --branch` and
`git log -1`. No merge, deployment, credential change, frozen benchmark edit,
historical dossier edit or original-worktree Git operation was performed.
The implementation commit passed [hosted CI run 38412902499](https://github.com/Shaunakrane914/Misinformation/actions/runs/38412902499): all five jobs completed successfully, including fatal Python lint/frontend contracts, the entire offline suite with release and persistence validators, and Python 3.11/3.12/3.13 unit/chaos/security jobs. This is CI evidence for that exact commit, not for the later append-only evidence commit.

The [GitHub REST executor](../../backend/services/agent_reach/native/executor.py)
now supports **opt-in** `include_comments=True` for `github.issues` only.
It makes at most two actual issue-comment follow-up requests, at most five
comments per issue, with five-second and 1 MB bounds per request. Each saved
comment body is capped at 1,000 characters and retains its provider URL,
author/date when present, truncation flag, and transport observation. No
authorization bypass or synthetic comment is used. By default, the operation
remains its prior one-request issue-list behavior. The
[routing layer](../../backend/infrastructure/acquisition/routing/standard_handlers.py)
keeps issue-body evidence if comment lookup fails and labels results as a
*bounded sample*, never a complete discussion. Missing author, date or URL
stays absent. Telemetry records the actual follow-up request count.

The first [live diagnostic](../../artifacts/phase8_issue_comment_probes/2026-10-13_09-27-47Z/summary.json)
exposed a positional-budget bug: zero-comment issues consumed the first two
slots. The budget now counts only actual follow-up requests; the
[negative and positive records](../../artifacts/phase8_issue_comment_probes/README.md)
are both retained and labeled. A
[clean-commit probe](../../artifacts/phase8_issue_comment_probes/2026-10-13_14-23-15Z/summary.json)
on `2530ae8` observed one actual public comment from one follow-up request,
with source URL, author, date and transport observation; it retained no
issue/comment text. A separate [five-GitHub-operation re-probe](../../artifacts/phase8_extraction_spotchecks/2026-10-13_14-23-30Z/)
sampled 15 scenarios on the same clean commit after the base REST timeout was
clamped to five seconds. All five operations returned live classified output
on at least one target. Its `PHASE8A_GATE=PARTIAL` means the other 11
operations were intentionally excluded, **not** that those routes regressed.
The [v13 richness summary](../../artifacts/phase8_extraction_spotchecks/2026-10-13_14-23-30Z/richness_summary_v13.json)
overlays these GitHub records on the prior full 16-operation run.

GitHub's [official issue-comment API documentation](https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28)
supports public issue-comment listing and pagination; the bounded Aegis
follow-up uses only the first page. Provider API support is not proof that
every issue has available comments or that deleted/restricted content can be
recovered.

## Verification actually run

| Check | Observed result |
|---|---|
| Focused executor, route and probe-redaction tests | Exit 0; 66 passed after the budget fix. |
| `pytest tests/ -q -o addopts='--tb=short -ra'` | Exit 0; 1046 passed. |
| `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | Exit 0; 850 passed. |
| `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; zero selected fatal errors. |
| All five Node `tests/frontend/test_*.js` scripts | Exit 0; simulated-DOM contracts passed, not a visual audit. |
| `python scripts/validation/verify_frozen_benchmarks.py` | Exit 0; frozen content hashes verified. |
| `python scripts/validate_release_candidate_smoke.py` | Exit 0; `OFFLINE_SMOKE_PASS`, with test mocks and disabled acquisition. |
| `python scripts/validate_rollback_compatibility.py` | Exit 0; isolated `OFFLINE_PERSISTENCE_PASS`; historical archive and deployed rollback remained `NOT_VERIFIED` here. |
| `python -m scripts.audits.run_phase8_github_issue_comment_probe` | Exit 0 in three append-only runs: one negative pre-fix, one dirty positive and one clean-commit positive. The latter observed one comment; no full-discussion claim. |
| `python -m scripts.audits.run_phase8_live_acquisition_audit --output-root artifacts/phase8_extraction_spotchecks --operations github.read,github.issues,github.prs,github.commits,github.releases --max-scenarios 3` | Exit 0; five filtered operations live-verified on sampled targets, 15 probes. |
| `python -m scripts.audits.summarize_phase8_extraction` over the full and filtered JSONL files | Exit 0; 16-operation v13 summary created exclusively, without network. |
| Protected frozen/dossier/research diff, selected credential-pattern scan and `git diff --cached --check` | Exit 0/no scan matches; new bounded proof artifacts are intentionally append-only. |

## Limits and next work

Stage 8B remains **PARTIAL**. This change only adds an optional bounded first
page of issue comments. It does not fetch issue events, PR review comments,
all discussion pages or full bodies beyond the 1,000-character sample; it
does not quantify marginal request cost across providers. The 16-operation
Stage 8A clean run remains the earlier separately documented pass. Stages
8C/8D/8F remain unaccepted. The frontend Stage 8E is **not complete**: Node
contracts pass, but a browser visual/responsive/accessibility audit was not
possible in this session because the computer-use browser inventory was empty
and in-app browser creation failed. Historical dossier recovery and deployed
rollback are unverified; deployment remains unauthorized.

Next agent: verify the exact hosted CI result for the follow-up
documentation commit, inspect the [schema matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md),
then prioritize other bounded missing-field and pagination gaps. Preserve
the negative live record and do not treat a sampled comment, GitHub-provided
timestamp or absent `Link` header as complete discussion proof.
