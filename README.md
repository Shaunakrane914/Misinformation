# Aegis Protocol

A source-backed research application for investigating public claims, company news,
brand incidents and statements attributed to public figures.

[Live application](https://aegis-protocol-110.pages.dev/) ·
[Architecture](docs/ARCHITECTURE.md) · [API](docs/api/README.md) ·
[Testing](docs/TESTING.md) · [Evaluation](docs/EVALUATION.md)

## What it does

| Workspace | Purpose |
| --- | --- |
| Scout | Collect company disclosures and financial reporting; retain period, currency and source context. |
| BrandShield | Research reported counterfeit, fraud and impersonation incidents with attribution. |
| Trending | Find dated coverage of a topic and distinguish recent developments from older background. |
| Personal Watch | Inspect public statements, reported quotations and identity-related allegations. |
| Claim verification | Compare a specific assertion with acquired supporting and contradicting material. |

All four specialists share an acquisition pipeline. It plans queries, ranks observed
URLs, reads bounded documents, checks relevance and dates, deduplicates captures and
publishes cited passages. The interface exposes source links, original dates,
extraction limits and downloadable reports.

## Engineering

- **Backend:** Python 3.11+, FastAPI, Pydantic and a modular research pipeline.
- **Frontend:** HTML, CSS and JavaScript with responsive specialist workspaces.
- **Acquisition:** shared platform adapters, publisher feeds, observed-link traversal
  and structured document extraction, including speech and financial-document paths.
- **Evidence:** source identifiers, content hashes, exact passage offsets and separate
  roles for primary records, reporting, community leads and reference background.
- **Reliability:** request deadlines, HTTP admission limits, bounded response sizes,
  URL/DNS validation and explicit unavailable/insufficient-evidence states.
- **Storage:** SQLite-backed local records with optional configured Supabase services.
- **Evaluation:** offline regression/security tests, frozen retrieval fixtures and
  separate classical ML and reranking experiments.

The implementation lives in [backend](backend/), [frontend](frontend/) and
[tests](tests/). See [architecture and tradeoffs](docs/ARCHITECTURE.md) for the
request flow and module map.

## Run locally

```bash
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -r requirements.txt
python -m pip install pytest pytest-rerunfailures flake8
```

Copy [.env.example](.env.example) to a local `.env`, leave unavailable integrations
unset, and configure only the services you intend to use. Never commit credentials.

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` and `http://127.0.0.1:8000/docs` for the interface and
interactive API reference. See [operations](docs/OPERATIONS.md) for deployment,
provider configuration and access restrictions.

## Language-model integration

Configured language-model providers assist with query advice, entity suggestions
and parts of claim analysis. Acquisition controls, source records and passage
validation are explicit application code. Generated text is not a retrieved source.
Offline tests use mocked providers; they do not prove live retrieval quality.
Model-assisted conclusions still require source review.

## Validation and limitations

```bash
python -m pytest tests/ -q
python scripts/validation/verify_frozen_benchmarks.py
```

[Testing](docs/TESTING.md) lists the complete local checks and reproducible benchmark
commands. [Evaluation](docs/EVALUATION.md) separates historical dataset results
from live claim verification.

The application remains a research aid. A source count does not establish
independent confirmation; a quotation does not authenticate identity; a single
coverage snapshot does not measure virality. Live acquisition and report quality
vary by subject and source permissions. Known report-level limitations include
claim framing for bare entity names, source-role consistency and investigation
history recovery. This repository does not claim universal fact-checking accuracy.

## Repository contents

Application code, tests, required fixtures, benchmark records and operational
configuration are versioned here. Development-session transcripts, assistant skills,
large screenshot collections and superseded audit dumps are excluded. Earlier
committed material remains recoverable in Git history.

See [Contributing](CONTRIBUTING.md), [Security reporting](SECURITY.md) and
[MIT License](LICENSE). Acquisition integrates the separately maintained
[Agent Reach](https://github.com/Panniantong/Agent-Reach) package; publisher content
and third-party assets retain their own terms.
