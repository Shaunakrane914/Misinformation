# Testing

Tests cover routing, extraction, qualification, attribution, report propagation,
API contracts, persistence and network/security boundaries. Normal pytest runs use
fixtures and network guards; passing them does not establish live acquisition quality.

## Local checks

Install `requirements.txt` and the development tools `pytest`, `pytest-rerunfailures`
and `flake8`. Run from the repository root:

```bash
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validation/verify_frozen_benchmarks.py
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
```

Run every `tests/frontend/test_*.js` script with Node. For example in PowerShell:

```powershell
Get-ChildItem tests/frontend/test_*.js | ForEach-Object { node $_.FullName; if ($LASTEXITCODE) { throw "Frontend check failed" } }
```

CI runs fatal lint, frontend contracts, frozen-content checks, unit/chaos/security
on Python 3.11–3.13, and the full offline suite. Counts depend on the revision;
consult the actual run instead of a permanent test-total badge.

## Reproducible evaluations

```bash
python scripts/evaluate_dataset.py --mode all_offline --seed 42 --output-dir <new-output-directory>
python scripts/run_retrieval_quality_benchmark.py --help
```

The three JSONL files in `tests/retrieval_benchmark/` are immutable ground truth.
Do not change them to match implementation output. Historical baseline records and
limitations are explained in [evaluation](EVALUATION.md).

Live investigation tooling is opt-in: see
`scripts/audits/run_terminal_agent_quality.py --help`. Use a defined case manifest,
request/read/time ceilings, temporary storage and explicit provider policy. Never
run a live batch as a side effect of an ordinary unit test. Save source identity,
body depth, dates and passage accounting; keep raw words separate from qualified
and displayed words.
