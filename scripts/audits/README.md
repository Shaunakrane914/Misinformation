# scripts/audits/

Live-network audit scripts that produce empirical evidence artifacts.

> **Warning:** These scripts make real network requests and require valid API keys.
> Run in a properly configured environment, not during CI.

| Script | Description |
|--------|-------------|
| `run_final_retrieval_audit.py` | Phase 6.9 final provider audit |
| `run_complete_retrieval_fix_audit.py` | Post-fix full acquisition audit |
| `run_phase6_7_live_acquisition_audit.py` | Phase 6.7 live acquisition |
| `run_phase6_8_resolution_benchmark.py` | Social resolution benchmark |
| `live_agent_json_audit.py` | JSON structure validation on live agent outputs |
| `local_agent_json_audit.py` | JSON structure validation on local cached outputs |

Audit outputs are preserved in `artifacts/` per AGENTS.md invariants.
