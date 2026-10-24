# Handoff: three prompts per agent, word yield and relevance — 2026-10-21

## Request, execution and decision

User requested three prompts per agent, word-count growth and whether information
was sufficiently relevant. Ran the exact twelve October 16 inputs once each through
real local API/SSE acquisition, AI disabled, DEEP profile bounded to 240s/24 reads/
120 native HTTP admissions per case. No audit retries or extra provider probes.

**Result: not complete/release-ready.** Retained words rose 1,948 → 15,461, but six
cases still returned no retained evidence. Scout/Trending bodies are richer;
financial periods, peripheral matches and event-passage selection remain weak.
BrandShield and Personal Watch failed this batch amid recorded reading/DNS and
subsequent discovery transport failures. Do not describe them as universally
incapable, recovered, safe or independently accepted based on these observations.

[Full report, twelve-case/funnel tables](../testing/TWELVE_PROMPT_WORD_YIELD_AND_RELEVANCE_2026-10-21.md)
· [durable sanitized evidence](../testing/evidence/2026-10-21_twelve_prompt_yield/README.md).

## Repository and edits

Actual worktree `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus preserved dirty work.
Stable backend/frontend fingerprint throughout the entire live batch:
`53ea40a1ab4ae48eb55fb6f72d98b0b4ff58e9e3d0935a9cec4cc3d408d15eb1`.
Only new docs/sanitized observations and navigation links were written. No
application/source-test/config changes, secrets, approval flags, historical data
edits, commits, pushes, merge or deployment. Original archive remains protected.

## Findings to reproduce offline before any fresh calls

1. `05-trending` genuine TechCrunch bodies begin with current TorchTPU/TorchNeuron
   announcements. Their selected development passages are historical PyTorch/CUDA
   context; a third source is an ex-NVIDIA employee/VC interview with an incidental
   talent mention. Inspect `PassageExtractor.extract_passages()` and Trending's
   `recent_developments` projection. Preserve source bytes, dates and attribution;
   no generated summaries/URLs or weaker evidence gates are needed.
2. `02-scout` retains 2026 results, 2010 earnings guidance and a 2025 buyback item.
   Keep periods separate; do not make a current assessment by combining them.
3. `01-scout` selects a 689-word brand-strategy block. It is not a concise financial
   investigation. `03-scout` has useful official release text but comparison status
   remains `NOT_PERFORMED`.
4. `08-brandshield` has 66 candidates, 24 failed reads, 20 ACCESS_REJECTED/SSRF-layer
   observations with actual log reasons DNS `getaddrinfo`/11001 failures. This is
   not evidence of private-IP destinations or permission to disable SSRF. The last
   four cases fail in discovery. Shared cooldown, host networking and exact later
   transport causes were not proven; do not infer them only from empty reports.

## Evidence, verification and next boundary

Fresh temp basename `aegis-twelve-depth-8620b716970f4392b41737621a9290eb` contains
`live/` native/SSE/pipeline responses, backend log, temporary pools/dossiers,
`terminal-run.log`, `raw-harvest.json` and regression/validator logs. Temp may expire.
Durable metadata excludes complete bodies and credentials; historical baseline
hash and saved source hashes are in the linked comparison/evidence files.

Actual checks: full 1,826 passed/38.29s; fast 1,618 passed/25.21s; fatal flake8,
all nine Node scripts, frozen verifier and protected diffs exited 0. Smoke passed
offline; rollback passed isolated persistence, with historical archive/deployed
rollback NOT_VERIFIED. The live runner/summarizer exited 0, but six research
outcomes are failed/insufficient. No browser or remote CI/deployment was run.

Command already executed (authorization consumed, not permission to rerun):

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --research-profile DEEP --env-file <server-env> --output-dir <new-temp-run> --timeout-seconds 240 --max-deep-reads 24 --max-http-admissions 120
```

Safe saved-file summary command:

```text
python scripts/audits/summarize_raw_harvest.py --run-dir <saved-temp-run> --output <new-summary.json>
```

Next implementation should use the saved genuine NVIDIA/financial responses for
deterministic passage/period regressions and separately diagnose transport failure
taxonomy. The user asked for this audit, not application repairs; none were made.
Any fresh validation beyond the completed twelve requests needs another bounded
authorization. Preserve all security/access/data controls and the independent
review boundary. Word growth is not accuracy, independence or production acceptance.
