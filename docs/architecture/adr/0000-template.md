# ADR 0000: Architectural Decision Record Template

## Status
**PROPOSED** | **ACCEPTED** | **DEPRECATED** | **SUPERSEDED by [ADR-XXXX](XXXX-title.md)**

## Date
YYYY-MM-DD

## Deciders
- Architecture & Technical Lead:
- Core Maintainers:

---

## 1. Context and Problem Statement
What is the specific architectural, design, or engineering problem we are attempting to resolve?
Describe the technical context, current codebase constraints, observed defects, or performance bottlenecks.

## 2. Decision Drivers
- Driver 1 (e.g. Modularity, maintainability, upgrade safety)
- Driver 2 (e.g. Execution latency, deterministic testing, zero-cost acquisition)
- Driver 3 (e.g. Evidence provenance, cryptographic auditability, lineage preservation)
- Driver 4 (e.g. Operational simplicity, single deployable artifact)

## 3. Considered Alternatives
- **Alternative 1**: Description and rationale.
- **Alternative 2**: Description and rationale.
- **Alternative 3**: Description and rationale.

## 4. Decision Outcome
Chosen option: **[Option Name]**, because [justification].

### Detailed Architectural Contract
Specify the exact contracts, protocols, schemas, directory structures, or API interfaces governed by this decision.

### Invariants Enforced
1. Invariant 1
2. Invariant 2
3. Invariant 3

---

## 5. Consequences

### Positive Consequences
- Positive impact 1
- Positive impact 2

### Negative Consequences / Trade-offs
- Trade-off or complexity introduced
- Mitigation strategy

---

## 6. Pros and Cons of the Alternatives

### [Alternative 1]
- Good, because ...
- Bad, because ...

### [Alternative 2]
- Good, because ...
- Bad, because ...

---

## 7. Validation & Verification Plan
How will compliance with this ADR be automatically verified in tests, CI, or linters?
- Test suite:
- Linting / architecture rule:
- Rollback criteria:
