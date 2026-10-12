# Aegis Protocol — Test Suite

**790 tests across 7 layers** — all offline, deterministic, and fast.

| Layer | Path | Description |
|-------|------|-------------|
| Unit | `tests/unit/` | Fast, isolated component tests |
| Integration | `tests/integration/` | FastAPI TestClient multi-component |
| Security | `tests/security/` | SSRF, XSS, adversarial inputs |
| Chaos | `tests/chaos/` | Fault injection and resilience |
| Contract | `tests/contract/` | Upstream fixture contracts |
| Benchmarks | `tests/benchmarks/` | Performance regression |
| Retrieval | `tests/retrieval_benchmark/` | Cranfield benchmark suite |

## Running
```bash
pytest tests/ -q                  # All 790
pytest tests/unit -q              # Unit only (~2s)
pytest tests/security -q          # Security only
```

## Frozen Datasets
`tests/retrieval_benchmark/*.jsonl` — **never modify**. Protected per AGENTS.md.
