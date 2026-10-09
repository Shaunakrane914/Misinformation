# Aegis Protocol — Developer Guide & Runtime Standards

Welcome to the development guide for **Aegis Protocol**. This guide covers local environment setup, runtime execution, coding standards, and developer workflow.

---

## 1. Prerequisites & Environment Setup

### System Requirements
- **Python**: 3.11 or higher (tested on 3.11, 3.12, 3.13)
- **Git**: 2.30+
- **OS**: Windows, macOS, or Linux

### Virtual Environment Setup
```bash
# Clone the repository
git clone https://github.com/Shaunakrane914/Misinformation.git
cd Misinformation

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (cmd):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Configuration & Secrets

Copy the environment template and configure keys if live services are desired:
```bash
cp .env.example .env
```

Key environment variables:
| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | `None` | Google Gemini API key for live inference. Key rotation is supported via `GEMINI_API_KEY_1`, `_2`, etc. |
| `AEGIS_MOCK_LLM` | `false` | When `true`, activates deterministic offline mock LLM provider. |
| `SUPABASE_URL` | `None` | Supabase / PostgreSQL persistence URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | `None` | Supabase service key. |
| `LOG_LEVEL` | `INFO` | Application log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `PORT` | `8000` | HTTP listening port for Uvicorn server. |

> [!NOTE]
> **Zero-Credential Developer Mode:** Aegis Protocol automatically degrades gracefully to an in-memory SQLite database and deterministic offline mock services if external API keys or cloud database connections are absent. All 530 tests run fully offline without external keys.

---

## 3. Running the Development Server

Start the application using the root entrypoint:
```bash
python main.py
```
Or directly via Uvicorn:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Accessing Interfaces
- **Web UI**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Reference**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **System Health Liveness**: [http://localhost:8000/healthz](http://localhost:8000/healthz)

---

## 4. Testing & Verification Standards

Aegis Protocol enforces a zero-regression invariant:
```bash
# Execute the complete 530-test regression suite
pytest

# Run fast unit tests only
pytest tests/unit/

# Run security & SSRF tests
pytest tests/security/

# Run retrieval benchmark assertions
pytest tests/test_retrieval_benchmark.py tests/test_retrieval_metrics.py
```

### Writing Tests
- All unit tests live under `tests/unit/` using standard `pytest` conventions.
- Never write tests that require live external network access unless marked with `@pytest.mark.live_network`.
- Never mutate frozen benchmark fixtures in `tests/retrieval_benchmark/`.
- Ensure new API routes have corresponding test coverage in `tests/test_api_endpoints.py` or `tests/contract/`.

---

## 5. Architectural Standards & Boundary Rules

1. **Modular Monolith Layering**:
   - `backend/core/`: Foundation utilities, settings, normalization.
   - `backend/schemas/`: Immutable Pydantic models and request/response contracts.
   - `backend/db/`: Database persistence and repositories.
   - `backend/services/`: Core domain engines (Research, Intelligence, Reranker).
   - `backend/agents/`: Autonomous domain sentinels (Scout, Trending, BrandShield, Personal Watch, Investigator).
   - `backend/api/`: Modular FastAPI routers mounted to `backend/main.py`.
2. **Input Sanitization**:
   - All inbound URLs must be validated via `backend.services.url_validator.validate_url_safe()`.
   - All inbound claim strings must be normalized via `ClaimIngestionAgent` (Unicode NFC, whitespace collapsing, length bounds).
3. **Frontend Hygiene**:
   - Frontend is built with Vanilla HTML5, CSS3, and JavaScript without node-based build steps.
   - All user or untrusted LLM strings injected into DOM must use `escapeHtml()` from `frontend/aegis-nav.js` or `textContent`.

---

## 6. Git & Branching Workflow

- Main branch: `main`
- Active refactoring branch: `feat/retrieval-quality-benchmark`
- Commit message convention: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Always ensure `pytest` reports 0 failures and 0 warnings prior to committing.
