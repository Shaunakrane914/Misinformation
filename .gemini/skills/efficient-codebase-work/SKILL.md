---
name: efficient-codebase-work
description: Maximize coding efficiency in large repositories by enforcing scope-first, evidence-driven exploration, minimal file working sets, and targeted validation while preventing whole-repo scans and architecture rediscovery loops.
---

# Efficient Large-Codebase Workflow Skill

## Overview

This skill teaches the agent to work with precision and speed on large codebases.
**A large repository does not require large exploration for every change.**

When working on a familiar repository (such as `Shaunakrane914/Misinformation`), architectural patterns and system components are already established in context. The agent must prioritize **evidence-driven, localized engineering** over broad exploratory sweeps.

---

## Core Execution Loop

Default to:

```text
TASK
  ↓
CLASSIFY TASK
  ↓
IDENTIFY LIKELY OWNER
  ↓
READ SMALLEST RELEVANT FILE SET (1–5 files)
  ↓
CHECK DIRECT DEPENDENCIES (if needed)
  ↓
EDIT (minimal correct change)
  ↓
RUN TARGETED TESTS
  ↓
EXPAND SCOPE ONLY WHEN EVIDENCE REQUIRES IT
```

Never default to:

```text
TASK
  ↓
SCAN ENTIRE REPOSITORY (grep/glob/list_dir)
  ↓
READ MANY UNRELATED FILES
  ↓
REDISCOVER KNOWN ARCHITECTURE
  ↓
RUN HUNDREDS OF UNRELATED TESTS
  ↓
MAKE SMALL EDIT
```

---

## 1. Context vs. Verification

Do NOT repeatedly rediscover information already established in the conversation or documented in the repository.

- **Conversation context**: Provides the architecture, conventions, API contracts, and prior decisions. Use it.
- **Filesystem inspection**: Strictly to verify the *current implementation* and line numbers of the targeted files.
- **Do not confuse**: *"verify current code"* with *"rediscover the entire repository."*

---

## 2. Scope-First Exploration & Working Sets

Before executing broad searches or scans:
1. **Identify the requested behavior.**
2. **Identify the most likely owning file(s).**
3. **Identify directly related files or tests.**
4. **Declare the working set.**
5. **Start strictly with those files.** Expand only if runtime evidence, missing definitions, or failing tests require it.

### Target Working Set Size
For ordinary and isolated tasks, the working set should typically be:
- **1–5 source files**
- **1–5 relevant tests**

---

## 3. Lightweight Routing Map (Aegis Domain Starting Points)

Use this known architecture routing table as immediate entry points rather than searching from root:

| Domain / Area | Likely Owning Frontend / Entrypoint | Likely Owning Backend / Logic | Primary Test File(s) |
|---|---|---|---|
| **Claim Analysis** | `frontend/index.html` | `backend/api/claims.py`<br>`backend/agents/investigator_agent.py` | `tests/unit/test_claims_*.py` |
| **Trending Intelligence** | `frontend/trending-agent.html` | `backend/api/trending.py`<br>`backend/agents/trending_agent.py` | `tests/unit/test_trending_*.py` |
| **BrandShield** | `frontend/brandshield-agent.html` | `backend/agents/brandshield_agent.py` | `tests/unit/test_brandshield*.py`<br>`tests/unit/test_product_honesty_and_integrity.py` |
| **Personal Watch** | `frontend/personal-watch-agent.html` | `backend/agents/personal_agent.py` | `tests/unit/test_personal_*.py` |
| **Scout / Deep Research** | `frontend/scout-agent.html` | `backend/agents/scout_agent.py`<br>`backend/services/research/research_engine.py` | `tests/unit/test_scout_*.py`<br>`tests/unit/test_research_engine*.py` |
| **System / Deployment** | `frontend/system-health.html` (or modal) | `backend/api/system.py`<br>`backend/services/system_probe.py` | `tests/unit/test_system_*.py`<br>`tests/unit/test_product_honesty_and_integrity.py` |
| **Global Navigation** | `frontend/aegis-nav.js` | N/A | Browser / smoke tests |
| **Shared Provenance & Lineage** | N/A | `backend/services/research/source_lineage.py`<br>`backend/services/research/evidence_graph.py`<br>`backend/services/research/source_independence.py` | `tests/unit/test_source_lineage.py`<br>`tests/unit/test_evidence_*.py` |

*Note: These paths are concrete starting anchors. Do not assume they are the only files, but always check them first before running generic directory searches.*

---

## 4. Shared Infrastructure Rule

Aegis has shared foundational infrastructure (e.g. `ResearchEngine`, `EvidenceGraph`, `NativeRouter`, `ReplayLedger`).

- Do **NOT** modify or inspect shared systems merely because they are conceptually adjacent.
- If fixing a BrandShield UI or heuristic bug:
  - Start with `backend/agents/brandshield_agent.py` and `frontend/brandshield-agent.html`.
  - Do **NOT** immediately inspect `research_engine.py`, `source_lineage.py`, or `trending_agent.py` unless direct imports or runtime errors specifically implicate them.

---

## 5. File Reading & Search Discipline

### Reading
- Prefer viewing the specific function, class, or section using line ranges or symbol targets.
- Do not repeatedly read 800+ lines of code when only a 30-line function is being modified.
- Stop exploring once the local context needed to implement the fix is clear.

### Searching
- **Never** do repository-wide keyword searches for common generic terms (e.g. `confidence`, `status`, `data`, `result`).
- Use **exact, targeted searches**:
  - Exact symbol name: `def calculate_confidence` or `class BrandShieldAgent`
  - Exact route/endpoint: `@router.get("/status")`
  - Exact DOM ID: `id="threat-indicators-list"`
  - Specific error message or status enum: `UNSUPPORTED_REVIEW` or `HEALTHY_SIMULATED`
- Scope searches to specific directories:
  - Pass `backend/agents/` or `frontend/` instead of scanning repository root.

---

## 6. Prohibited Default Behaviors

Do **NOT** perform any of the following unless explicitly instructed:
1. `list_dir` on root, backend, frontend, agents, and services recursively at the start of a task.
2. Repo-wide `grep_search` across all extensions.
3. Reading git log or commit history for dozens of commits during an ordinary bug fix.
4. Running the full test suite (`pytest`) when validating a 5-line change in a single module.

### When are broad searches permitted?
Only when:
- The user explicitly requests a repository-wide audit or migration.
- The change is genuinely cross-cutting across all agent interfaces.
- A targeted test failure demonstrates an unexpected foreign component broke.
- The target code imports an unknown abstraction whose location is ambiguous.

---

## 7. Targeted Validation & Testing

- **Default**: Run only the test file directly covering the modified component:
  ```powershell
  python -m pytest tests/unit/test_product_honesty_and_integrity.py -k test_brandshield -v
  ```
- **Escalate to broader suites only when**:
  - Modifying core shared infrastructure (`backend/services/research/`).
  - Public API schemas or shared contracts were altered.
  - The targeted test fails due to a dependency contract.
  - The user explicitly requests a full pass.

---

## 8. Change Size & Implementation Discipline

- Implement the **smallest correct change** that satisfies the requirement.
- Do not refactor adjacent code just because it looks unideal.
- Do not invent duplicate utility functions or parallel abstractions when one already exists.
- Preserve existing comments, docstrings, and non-target logic.

---

## 9. Required Output Protocol: Working Set Declaration

Before making edits, briefly declare your intended working set in your response:

```text
Working set:
- backend/agents/brandshield_agent.py
- frontend/brandshield-agent.html
- tests/unit/test_product_honesty_and_integrity.py
```

If the working set must expand during implementation, state the concrete evidence:

```text
Expanded scope:
- Adding backend/services/research/source_lineage.py because BrandShieldAgent imports and invokes LineageTracker directly for review provenance.
```

This ensures complete transparency and prevents scope creep.
