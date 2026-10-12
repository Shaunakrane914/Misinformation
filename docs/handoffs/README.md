# Coding-agent handoffs

Start here when resuming work. These are dated engineering records, not promises that the current checkout has been validated. Read [AGENTS.md](../../AGENTS.md) first, then inspect the live worktree before editing.

## Latest: Phase 7.4 verification — 2026-10-12

- [Phase 7.4 verification report](../architecture/PHASE7_4_REMEDIATION_VERIFICATION.md): local security closeout, Git/CI evidence boundary and release decision.
- [Historical dossier recovery inventory](2026-10-12_HISTORICAL_DOSSIER_RECOVERY_INVENTORY.json): read-only paths, SHA-256 hashes, parser diagnostics and candidate results for all 55 malformed records; no dossier content.

The remediation implementation context remains:

1. [State and safe continuation](2026-10-12_ARCHITECTURE_REMEDIATION_HANDOFF.md): where the previous agent stopped, ownership boundaries, implementation entry points, and prioritized follow-up.
2. [Decision rationale and code map](2026-10-12_ARCHITECTURE_REMEDIATION_DECISIONS.md): why the changes were made, tradeoffs, and regression tests that protect them.
3. [Testing and reproduction runbook](2026-10-12_ARCHITECTURE_REMEDIATION_TESTING.md): exact offline commands, isolated logging, expected failures, and honest acceptance criteria.
4. [Execution work log](2026-10-12_ARCHITECTURE_REMEDIATION_WORK_LOG.md): reconstructed checkpoints and observed command-result excerpts; not a verbatim chat export.
5. [Machine-readable context](2026-10-12_ARCHITECTURE_REMEDIATION_CONTEXT.json): portable paths, base commit, scope, evidence links and continuation constraints.

The [remediation report](../architecture/ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md) summarizes the preceding implementation. [Rollback verification](../operations/ROLLBACK_VERIFICATION.md) explains the 55 protected malformed historical JSON files that remain unresolved.

## Record maintenance

- Preserve older handoffs; add a new dated record when work continues and update this index's latest pointer.
- Record observed results separately from planned checks. Include failures and incomplete verification.
- Link to maintained code and tests rather than copying implementations into documentation and creating another source of truth.
- Do not store API keys, bearer tokens, private datasets, full dossier contents, or private reasoning traces here. Record concise technical rationale and evidence instead.
- A dirty worktree is shared work to preserve, not permission for cleanup, restoration, staging, commits or pushes.
