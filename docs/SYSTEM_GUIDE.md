# Aegis Protocol system guide

Maintained navigation, 2026-10-15. This guide describes implementation owners and limitations, not production acceptance. Begin with [current state](CURRENT_STATE.md) and the [latest handoff](handoffs/README.md); inspect the actual branch and dirty worktree.

## Runtime and evidence flow

FastAPI serves the vanilla frontend and API. Claim workflows currently remain in the claims API and worker; research stages are application-level. Specialist scans enter their own agent modules and use shared research/acquisition facilities. Scout is not a mandatory stage of every claim investigation. Native acquisition preserves channel/operation provenance and bounded transport; qualification, relevance and passage analysis precede report assembly. Unified reports expose evidence, contradictions, uncertainty and retrieval observations.

The system is a transitional modular monolith. [Target architecture](architecture/TARGET_ARCHITECTURE.md) is a destination, not a claim that every legacy facade has moved. Preserve compatibility shims and singleton admission guards. See [current code owners](development/CURRENT_CODE_MAP.md).

## Maintained entry points

- [Local development](development/README.md) and [environment setup](development/ENV_SETUP.md): Python 3.11+, persistent SQLite, explicit mock modes and loopback startup.
- [Architecture overview](architecture/OVERVIEW.md), [executed investigation path](architecture/PHASE8_INVESTIGATION_PATH_TRACE.md) and [source extraction matrix](architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md).
- [API route map](api/CURRENT_ENDPOINTS.md) and runtime `/openapi.json`; legacy proposed routes are not client contracts.
- [Phase 9 extraction runbook](operations/PHASE9_EXTRACTION_RUNBOOK.md): protected 16 operations, Reddit/X, additive community sources, bounded reads and evidence inspections.
- [Operations](operations/README.md), [configuration matrix](operations/PRODUCTION_CONFIGURATION_MATRIX.md), [security boundaries](security/README.md) and [rollback limits](operations/ROLLBACK_VERIFICATION.md).
- [Agent orientation and required commands](../AGENTS.md), [CI coverage](testing/CI_COVERAGE_MATRIX.md), [evaluation history](EVALUATION.md) and [research proof](../artifacts/README.md).

## Non-negotiable interpretation rules

A registered route is not live health. A successful request is not relevant evidence. An official domain is not claim support. A valid citation ID is not entailment. A hash establishes captured-byte consistency, not factual truth. A mirror/profile/sample is not authenticated identity or platform-wide coverage. Absence of retrieved threats is not absence of threats. Missing dates and counts remain unknown.

Separate implementation, offline regressions, bounded live samples, browser replay, independent adjudication, hosted CI and deployment acceptance. Preserve dated historical reports; append new evidence instead of rewriting old results. Frozen retrieval data and all historical dossiers are protected. The original archive's 55 malformed dossiers were not repaired by an isolated smoke test.
