# Aegis Protocol — Backend

FastAPI application with four production intelligence agents.

## Structure
```
backend/
├── agents/          # Scout, Trending, BrandShield, PersonalWatch
├── api/             # FastAPI route handlers
├── application/     # Research pipeline orchestration
├── core/            # Settings, config, DI
├── data/            # Local SQLite DB and dossiers
├── db/              # Database layer (Supabase + SQLite fallback)
├── infrastructure/  # Acquisition fabric (NativeRouter)
├── main.py          # FastAPI app factory
└── services/        # GeminiService, ResearchEngine, AgentReach
```

## Key Invariants
- Never block the event loop with synchronous I/O in async routes
- All outbound requests use `is_safe_url()` SSRF guard
- `AEGIS_MOCK_LLM=true` forbidden in `ENVIRONMENT=production`
