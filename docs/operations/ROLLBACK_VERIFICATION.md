# Aegis Protocol — Rollback & Recovery Verification
**Phase 7.1 Release Candidate Deliverable G**  
*Lead Production Reliability Engineer Audit*

---

## 1. Rollback Protocol Verification

The rollback procedure documented in [`docs/operations/V1_OPERATIONS_RUNBOOK.md`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/docs/operations/V1_OPERATIONS_RUNBOOK.md) was empirically tested using [`scripts/validate_rollback_compatibility.py`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/scripts/validate_rollback_compatibility.py).

```bash
# Automated verification execution:
python scripts/validate_rollback_compatibility.py
```

### Verification Findings
1. **SQLite Database Schema Stability**:
   - Database file: `aegis_local.db` (loaded 644 claims)
   - Core tables verified: `claims`, `evidence`, `claim_research`.
   - All Phase 7 and 7.1 changes to data models are strictly additive. No tables, constraints, or columns were dropped or altered destructively.
2. **Replay Dossier Persistence**:
   - Location: `backend/data/dossiers/`
   - Active Dossier Count: **2,312 JSON dossiers**
   - Format: Universal JSON Replay Dossier v3 (cryptographic hash indexed).
   - In a rollback to earlier Phase 7 commits (e.g. `258cb4f` or `c34b154`), all historical dossiers remain completely readable and reproducible.
3. **Health Endpoint Liveness**:
   - Process restarted with in-memory state cleared.
   - `/api/healthz` returned `status="ok"` immediately.
   - `/api/readyz` returned `status="ready"` with `mode="READY_UNVERIFIED"`.

---

## 2. Step-by-Step Rollback Execution Procedure

If an owner chooses to roll back a release candidate deployment to the previous verified Phase 7 baseline (`258cb4f1fc71c379d0e882d8804c2a9770fc7f60`):

### Step 1: Drain Traffic
Direct upstream ingress / reverse proxy (Nginx, Netlify, Cloudflare) to pause routing new research requests to the deploying instance.

### Step 2: Checkout Baseline Commit
```bash
git checkout 258cb4f1fc71c379d0e882d8804c2a9770fc7f60
```

### Step 3: Verify State & Health
```bash
# Re-run smoke validation on the restored codebase
pytest -q tests/unit/test_frontend_operation_health_contract.py tests/unit/test_recovered_operation_routes.py
python scripts/validate_rollback_compatibility.py
```

### Step 4: Resume Traffic
Confirm `/api/healthz` and `/api/readyz` respond with HTTP 200 before routing live user traffic back to the instance.

---

## 3. Forward-Recovery Strategy

In the event of an infrastructure-level failure (e.g. cloud PostgreSQL connectivity loss):
- Aegis automatically degrades to local SQLite storage without crashing.
- Claims submitted during the outage are written to local SQLite and JSON dossiers.
- Once cloud connectivity is restored, dossiers can be replayed to cloud PostgreSQL using the Replay Ledger CLI (`scripts/replay_dossier.py`).
