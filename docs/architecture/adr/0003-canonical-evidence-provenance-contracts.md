# ADR 0003: Canonical Evidence Provenance, Lineage, and Replay Ledger Contracts

## Status
**ACCEPTED**

## Date
2026-10-09

## Deciders
- Principal Software Architect & Migration Lead
- Aegis Protocol Core Engineering Team

---

## 1. Context and Problem Statement
In automated misinformation and intelligence workflows, a synthesized finding is only as trustworthy as the underlying evidence trail.
Historically, systems suffered from:
- Fabricated citations or hallucinations when scraping failed.
- Conflating publication timestamps with retrieval timestamps.
- Dropping intermediate metadata (e.g. original URLs lost during redirect resolution).
- Inability to mathematically replay an investigation months later to prove why an alert was triggered.

Aegis introduced cryptographic SHA-256 hash chains, `EvidenceFragment`, `EvidenceItem`, and `ReplayLedger`. We must formalize and preserve these contracts as core domain invariants across all refactoring phases.

---

## 2. Decision Drivers
1. **Cryptographic Auditability**: Every finding must trace back to concrete raw text excerpts with verifiable source URLs.
2. **Temporal Integrity**: For high-velocity channels (e.g. Trending), publication time ($T_{pub}$) must remain strictly decoupled from discovery time ($T_{disc}$) and acquisition time ($T_{acq}$).
3. **No Fabricated Evidence**: When acquisition fails or yields zero candidates, the system must fail closed and record zero findings rather than synthesizing plausible hallucinations.
4. **Independent Source Verification**: Evidence must track parent syndication networks to prevent counting syndicated mirrors as independent corroboration.

---

## 3. Considered Alternatives
- **Alternative 1: Unstructured Dict Passing**. Pass arbitrary JSON dictionaries between agents and scrapers.
  - *Rejected*: Inevitably leads to missing keys, silent typing drift, and broken lineage audits.
- **Alternative 2: Heavy Distributed Event Sourcing (Kafka / EventStore)**.
  - *Rejected*: Massive operational burden for a single-node modular monolith.
- **Alternative 3: Strongly-Typed Immutable Domain Models with Hash-Linked Replay Ledger (Chosen)**.
  - Retain `EvidenceFragment` (raw network signal) and `EvidenceItem` (evaluated candidate item) as strongly typed dataclasses/Pydantic models.
  - Enforce hash-linked `ReplayLedger` and `TruthDossier` serialization for every completed research run.

---

## 4. Decision Outcome
Chosen option: **Alternative 3 — Strongly-Typed Immutable Domain Models**.

### 4.1 Invariants Enforced Across the Lifecycle
1. **Invariant A (Rate Bound)**: Total acquired evidence items cannot exceed total discovered candidates ($N_{acquired} \le N_{discovered}$).
2. **Invariant B (Fallback Accounting)**: Fallback attempts must equal the sum of successful reads plus recorded error reasons ($N_{attempts} = N_{success} + N_{failures}$).
3. **Invariant C (Provenance Preservation)**: Every `EvidenceFragment` must retain:
   - `candidate_id` / `evidence_id`: Stable identifier throughout the funnel.
   - `url`: The target URL read.
   - `canonical_url`: The verified unredirected canonical link.
   - `channel_name`: Platform identifier (`web`, `news`, `reddit`, `twitter`, `youtube`, `github`).
   - `actual_retrieval_channel`: Exact backend executing the read (`arctic_shift`, `fxtwitter`, `bing_rss`, etc.).
   - `retrieval_timestamp`: UTC timestamp of network acquisition.
   - `published_at`: Original publisher timestamp (distinct from retrieval timestamp).
4. **Invariant D (Zero Hallucination Guarantee)**: If an agent receives zero accepted candidates from the gating layer, the research report must return `NO_GROUNDED_EVIDENCE` status. Under no circumstances may an LLM summarize an empty candidate pool.

---

## 5. Consequences

### Positive Consequences
- **Legal and Regulatory Compliance**: Intelligence findings can be audited in courtroom or enterprise compliance contexts with full chain of custody.
- **Deterministic Replay**: Investigations can be re-run against frozen dossiers to verify whether algorithmic updates would change historical verdicts.
- **Protection Against Sybil Syndication**: Prevents viral syndication farms from inflating confidence scores.

### Negative Consequences / Trade-offs
- Slight payload size overhead for storing full provenance metadata in `aegis_local.db` and JSON dossier exports.
