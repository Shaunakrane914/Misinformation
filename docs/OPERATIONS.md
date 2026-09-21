# Aegis Protocol — Operations & Deployment Guide
**Document Version**: 3.5.1  
**Target Environment**: Production Docker / Cloud / Local Developer Workstation

---

## 1. Environment Variable Reference

| Variable Name | Required? | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | Optional* | None | Primary Google Gemini API key for live inference. |
| `GEMINI_API_KEY_2`, `_3` | Optional | None | Secondary rotating keys for load distribution. |
| `AEGIS_MOCK_LLM` | Optional | `false` | When set to `true`, forces offline deterministic mock LLM provider. |
| `SUPABASE_URL` | Optional* | None | Supabase project URL for PostgreSQL persistence. |
| `SUPABASE_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Optional* | None | Supabase authentication token. |
| `APIFY_TOKEN` | Optional | None | Token for Twitter/X scraper integration. |
| `YF_API_KEY` | Optional | None | Yahoo Finance API key for market quotes. |
| `LOG_LEVEL` | Optional | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `PORT` | Optional | `8000` | HTTP listening port for Uvicorn server. |

*\*Note: If Gemini API keys or Supabase credentials are not provided or remote servers are unreachable, Aegis Protocol automatically activates its zero-crash local in-memory fallback stores and resilient mock providers, enabling full local testing without requiring external credentials.*

---

## 2. Local Setup & Startup

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/Shaunakrane914/Misinformation.git
cd Misinformation
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials if live services are desired
```

### 3. Initialize Database Schema (Supabase / Postgres)
If using Supabase or PostgreSQL:
1. Open the SQL Editor in your Supabase dashboard.
2. Run the script: `backend/setup_aegis_db.sql`.
3. This creates the `claims` and `evidence` tables, indexes, and constraints.

### 4. Run Development Server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to:
- Interactive API Documentation: `http://localhost:8000/docs`
- Main Dashboard: `http://localhost:8000/index.html`
- Threat Intelligence Lab: `http://localhost:8000/threat-lab.html`

---

## 3. Health & Telemetry Endpoints

- **`GET /healthz`**: Basic liveness probe returning system status, version, timestamp, and active agent count.
- **`GET /api/`**: OpenAPI metadata, system topology, and agent registry.
- **`GET /api/dashboard/stats`**: Aggregated claim and threat statistics.
