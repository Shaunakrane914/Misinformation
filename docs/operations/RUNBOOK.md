# Aegis Protocol — Operational Runbook

## Starting the Server
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## Health Checks
```bash
curl http://localhost:8000/api/healthz
curl http://localhost:8000/api/readyz
curl http://localhost:8000/api/agent-reach/doctor
```

## Running Tests
```bash
pytest tests/ -q                          # full suite
pytest tests/unit tests/chaos tests/security -q  # fast subset
```

## Smoke Validation
```bash
python scripts/validation/validate_release_candidate_smoke.py
```

## Docker
```bash
docker compose up --build
```
