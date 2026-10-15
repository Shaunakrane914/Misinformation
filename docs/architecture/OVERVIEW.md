# Executed architecture overview

Maintained against `abe547f` on 2026-10-14. [Target architecture](TARGET_ARCHITECTURE.md) is a design contract; this overview describes concrete current owners. Neither is acceptance evidence by itself. See [system guide](../SYSTEM_GUIDE.md) and [independent review](PHASE8_INDEPENDENT_REVIEW_2026-10-14.md).

## Runtime relationships

```text
User → FastAPI routes → claim orchestration OR specialist agent
                      → shared source planning / operation eligibility
                      → shared acquisition / bounded public transport
                      → normalization, relevance, qualification, reading, lineage
                      → findings / claim assessment / specialist triage
                      → dossier + persistence → report adapter → frontend
```

This is a component map, not a claim that every request invokes every stage. The four specialist scan endpoints are independent entrypoints, not mandatory sequential Scout→Research→Investigator→Coordinator stages. LLM participation depends on configuration; missing credentials do not imply synthetic live results.

| Responsibility | Current owner | Important boundary |
|---|---|---|
| HTTP/static entry | [backend/main.py](../../backend/main.py), [API modules](../../backend/api/) | Routes, request models, worker offloading/admission, static presentation. |
| Claim orchestration | [claims API](../../backend/api/claims.py), [claim worker](../../backend/workers/claim_worker.py) | Current claim normalization, research and verdict/report lifecycle; not yet a separate application/claims package. |
| Specialist agents | [agents](../../backend/agents/) | Scout, Trending, BrandShield, Personal Watch compose shared research with specialized triage; facades remain compatible. |
| Research stages | [application/research](../../backend/application/research/) | Bounded staged orchestration, reading, analysis and assembly; services retain domain engines. |
| Acquisition service/router | [infrastructure/acquisition](../../backend/infrastructure/acquisition/) | Canonical shared runtime, adapters, safe HTTP and operation dispatch; old Agent Reach imports remain shims/contracts. |
| Planning/operation policy | [source planner](../../backend/services/agent_reach/source_planner.py), [operation capabilities](../../backend/services/agent_reach/native/operation_capabilities.py) | Claim-aware source plan; credential/cooldown/implementation eligibility, not provider health proof. |
| Evidence/claim policy | [research services](../../backend/services/research/) | Source qualification, temporal/relevance checks, heuristic grouping, conservative lexical support and model uncertainty. |
| LLM gateway | [infrastructure/llm](../../backend/infrastructure/llm/) | Provider/mode/failover boundaries; no calibrated truth guarantee. |
| Persistence/ledger | [database](../../backend/db/database.py), [replay ledger](../../backend/services/research/replay_ledger.py) | Persistent SQLite or configured cloud storage; hash integrity is not factual truth. |
| Report/UI contracts | [report builder](../../backend/services/report_builder.py), [frontend](../../frontend/) | Grouped agent normalization, escaped source display, uncertainty, bounded health observations. |

## Counts and capability depth

The review checkpoint registers 22 service channels including four authoritative additions. The protected invariant is **16 operations**, not 16 healthy websites or 22 verified providers. Discovery, metadata, abstract, captions, comment samples, feed summaries and article/filing bodies are distinct depths. See [acquisition/extraction matrix](PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md).

SEC submission metadata is not XBRL/full financial filings; arXiv abstracts are not full/peer-reviewed papers; NVD data is vulnerability-specific; FactCheck ratings belong to their publisher. Official-origin and primary-source flags are not claim-support verdicts.

## Debt, evidence and reading paths

The modular-monolith structure, compatibility contracts, safe transport and per-agent admission are retained. Singletons, inconsistent legacy contracts, multiple finding/verdict policy owners, pairwise heuristic analysis and work finishing beyond stage deadlines remain limitations; this is not a distributed scaling or zero-downtime guarantee.

- Start: [portal](../index.md) → [system guide](../SYSTEM_GUIDE.md) → [current code map](../development/CURRENT_CODE_MAP.md).
- Decisions: [ADRs](adr/README.md) → [path trace](PHASE8_INVESTIGATION_PATH_TRACE.md) → [independent findings](PHASE8_INDEPENDENT_REVIEW_2026-10-14.md).
- Run/test: [developer guide](../development/README.md) → [testing](../testing/README.md) → [CI evidence](../testing/CI_COVERAGE_MATRIX.md).
- Operate: [environment](../development/ENV_SETUP.md) → [operations](../operations/README.md) → [security](../security/README.md).

[Phase 0 inventory](CODEBASE_INVENTORY.md) is a historical snapshot with old module sizes/test names, not the current inventory. Preserve its findings and use the current code map for executable locations.
