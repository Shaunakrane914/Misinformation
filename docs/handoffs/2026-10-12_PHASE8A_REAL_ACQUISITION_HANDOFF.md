# Phase 8A real acquisition handoff

Captured on 2026-10-12 (Asia/Calcutta). Read [AGENTS.md](../../AGENTS.md), then
inspect the live branch and worktree; this is a dated engineering record, not
authorization to merge or deploy.

## Requested scope and baseline

- User mandate: begin Phase 8 by tracing the production investigation path,
  proving all 16 protected acquisition operations with real traffic, fixing
  misleading paths, retaining machine evidence and proceeding sequentially.
- Branch: `feat/phase8-real-acquisition-proof`.
- Base commit: `dc249fe369506c8677916b57f8022d292be62216` on
  `feat/phase7-2c-root-cleanup`.
- The base worktree was clean and synchronized. No Phase 7.4 remediation was
  discarded, stashed or overwritten.

## Implementation and decisions

- Added the bounded Phase 8 audit runner and offline contracts.
- Added redirect-chain, response-hash, rate-limit and empty-result transport
  evidence at the shared HTTP/dispatcher boundary.
- Prevented invalid YouTube pages from becoming fake video metadata.
- Corrected depth truth for bounded web reads and GitHub commits.
- Replaced the mislabeled generic Apple Podcast path with a direct official
  Xiaoyuzhou public-page parser. Text search remains disclosed discovery.
- Kept the modular monolith and compatibility paths; no folder rewrite or
  frontend redesign was attempted before data contracts stabilize.

See:

- [production path trace](../architecture/PHASE8_INVESTIGATION_PATH_TRACE.md)
- [Phase 8A verification report](../architecture/PHASE8A_REAL_ACQUISITION_VERIFICATION.md)
- [authoritative machine evidence](../../artifacts/phase8_live_acquisition/2026-10-12_11-06-45Z/)
- [artifact chronology](../../artifacts/phase8_live_acquisition/README.md)

## Observed validation

| Command | Result |
|---|---|
| Phase 8A consolidated audit | `PASS`, 16 / 16 independently live-verified at an honest depth |
| `pytest tests/ -q -o addopts='--tb=short -ra'` | 986 passed in 64.42s |
| `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | 790 passed in 23.85s |
| fatal flake8 command from `AGENTS.md` | exit 0, zero findings |
| release-candidate smoke | `OFFLINE_SMOKE_PASS` |
| frozen benchmark verifier | pass; protected tracked diff empty |
| rollback compatibility | exit 1 only for the known 2,445 legacy-unsealed / 55 malformed protected historical dossiers; all new-state subchecks passed |

Live evidence was captured without `GITHUB_TOKEN`, `YOUTUBE_API_KEY` or
`GROQ_API_KEY`. An unauthenticated GitHub quota event was observed and retained;
no authentication or rate limit was bypassed.

## Gate and remaining risks

- Phase 8A: `PASS`. This is a time-bound capability proof, not continuous
  provider health and not maximum extraction.
- Implementation checkpoint: `b2715406af219ca336b546ed7d42f54fe795cac4`.
- Phase 8B: not yet complete. It must inventory theoretically available,
  observed, populated, optional, restricted and paginated fields for every
  operation and measure important-field completeness.
- The synchronous claims verification work still sits inside an async route;
  address that worker-boundary risk in the API/intelligence phase.
- Push and hosted CI evidence must be appended after remote verification.
  Nothing in this handoff authorizes merge to `main` or deployment.
- The 55 historical malformed dossier files remain byte-for-byte untouched.
