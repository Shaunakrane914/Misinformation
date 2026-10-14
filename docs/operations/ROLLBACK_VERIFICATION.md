# Rollback and recovery verification

Run the non-destructive validator:

```bash
python scripts/validate_rollback_compatibility.py
```

It writes validation claims and dossiers only to a temporary directory. A producer and consumer run as different OS processes, proving that claim verdicts, evidence and a new sealed dossier reload from disk. It checks required SQLite tables, dossier JSON shape, checksum tamper detection, and honest `LEGACY_UNSEALED` reporting.

The actual SQLite and JSON reader implementations from baseline commit `258cb4f1fc71c379d0e882d8804c2a9770fc7f60` then read the new persisted data in a third process. Only the historical ledger's default storage location is redirected to the temporary directory. The script checks that these readers did not change dossier bytes. Supply another locally available commit using `--baseline-ref <sha>`; no checkout, fetch or history rewrite occurs. An unavailable baseline is `NOT_VERIFIED`.

The default historical archive `backend/data/dossiers/` is inspected read-only. Invalid JSON, missing required fields or failed checksums are reported and cause a nonzero exit code. Empty/unavailable archives are `NOT_VERIFIED`. Legacy dossiers are readable but are not claimed to have cryptographically verified integrity; new checksums are not independently signed authenticity proofs.

## Historical archive finding

The corrected read-only validator on 2026-10-12 identified 55 malformed existing JSON files among 2,500 dossiers; 2,445 readable records were `LEGACY_UNSEALED`. For example, `R-2026-02617B.json` fails JSON parsing at line 42, column 24. These protected historical files were not modified, deleted, re-sealed or silently skipped. The validator reports `HISTORICAL_ARCHIVE_FAIL`, while separately retaining evidence for successful temporary-state reload and historical reader compatibility. Owner-directed recovery from trustworthy backups is required; never fabricate the missing dossier contents.

The Phase 7.4 [read-only recovery inventory](../handoffs/2026-10-12_HISTORICAL_DOSSIER_RECOVERY_INVENTORY.json) records portable paths, hashes and parser locations for all 55 files. It found 51 property-name syntax errors and 4 missing-delimiter errors, with no valid candidates in the repository filesystem or available Git history. This does not exclude owner-controlled external backups. Reproduce the assessment with `python scripts/validation/inventory_historical_dossiers.py --candidate-root . --include-git-history`; the tool compares before/after archive hashes and never emits dossier contents.

Historical `quality_tensor: null` entries represent an unknown metric, not malformed JSON or a failed content checksum. Nullable legacy metrics remain readable and unverified; accepting their documented absence does not manufacture measurements or weaken checksum validation. The 55 failed records above are JSON parsing failures, not these nullable legacy records.

This corrects the earlier filename-count-only acceptance claim. A historical count, `/readyz` response or current in-process client did not establish restart, integrity or prior-version compatibility.

## Deployed rollback remains an owner action

The automated reader test does not boot the entire earlier application version or reproduce deployed infrastructure. A staging rollback remains `NOT_VERIFIED` until the owner drains traffic, backs up storage, deploys the chosen earlier release without destructive migrations, verifies contracts and data readability, and then resumes traffic. See the [operations runbook](V1_OPERATIONS_RUNBOOK.md).

Cloud outages can fall back to local SQLite, but automatic SQLite-to-Supabase reconciliation is not implemented. No `scripts/replay_dossier.py` recovery command exists. Reconciliation requires a separately reviewed migration tool with backup, identity mapping and conflict handling; do not claim dossier trace playback performs database replication.
