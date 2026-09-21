"""
FastAPI Backend for Aegis Protocol — Multi-Agent Threat Intelligence & Verification
=====================================================================================

v3.5.1 — Modular APIRouter Architecture
- Deconstructed domain routing across backend/api/ (claims, agent_reach, threat_lab, agents, system)
- Synchronous 5-section Truth Dossier verification endpoint (/api/claims/verify)
- Domain-specialized Omni-Channel scraper endpoint (/api/agent-reach/omni-scan)
- Enhanced Scout market catalyst & short attack correlation (/api/scout/analyze)
- Full 7-agent telemetry and capability matrix (/api/system/agents)
- Interactive OpenAPI Swagger UI with pre-populated examples
"""

import os
import time
import uuid
import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='ts=%(asctime)s level=%(levelname)s logger=%(name)s msg="%(message)s"',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# ── OpenAPI Tags & Metadata ───────────────────────────────────────────────────
tags_metadata = [
    {
        "name": "Claims & Verification",
        "description": "Multi-agent epistemic truth verification, evidence extraction, and synchronous Truth Dossier generation.",
    },
    {
        "name": "Scout Agent (Financial Intelligence)",
        "description": "Stock price drop detection, market volatility z-scores, social media catalyst extraction, and coordinated short-attack correlation.",
    },
    {
        "name": "BrandShield Agent (Brand Defense)",
        "description": "Cross-platform fake review detection, counterfeit product identification, and brand smear campaign forensics.",
    },
    {
        "name": "Personal Watch Agent (VIP Protection)",
        "description": "High-profile individual protection, audio/video deepfake marker detection, impersonation scanning, and doxxing alerts.",
    },
    {
        "name": "Trending & Contagion Agent",
        "description": "Viral narrative tracking, Hawkes process contagion modeling, and instant crisis response statement generation.",
    },
    {
        "name": "Agent Reach (Omni-Channel Scrapers)",
        "description": "Zero-cost, zero-API-key scraper fabric across Reddit, Twitter/X, YouTube, News Wires, and Jina Reader.",
    },
    {
        "name": "Threat Intelligence Lab",
        "description": "Mathematical physics instruments: Mandelbrot token rank-frequency regression, Hawkes blast radius, and Byzantine fault-tolerant consensus.",
    },
    {
        "name": "War Room & Incident Response",
        "description": "Real-time threat feed and automated crisis mitigation deployment.",
    },
    {
        "name": "System & Telemetry",
        "description": "Agent health checks, system status, and capability inventories.",
    },
]

# ── App Initialization ───────────────────────────────────────────────────────
app = FastAPI(
    title="Aegis Protocol — Multi-Agent Intelligence API",
    description="""
### Real-Time Misinformation Detection, Market Threat Defense & Forensic Truth Dossier

Aegis Protocol orchestrates a coordinated swarm of 7 specialized AI agents and zero-cost scraping fabric:
- **ClaimIngestionAgent**: Cryptographic hash normalization and deduplication.
- **ResearchAgent**: Multi-source evidence gathering with dynamic Gemini rotation and AgentReach.
- **InvestigatorAgent**: Stance classification, Bayesian evidence matrix, and contradiction detection.
- **TrendingAgent**: Viral narrative velocity, Hawkes self-exciting point processes, and crisis PR generation.
- **ScoutAgent**: Stock drop anomaly detection, Yahoo Finance telemetry, and short-seller attack correlation.
- **BrandShieldAgent**: E-commerce counterfeit detection and fake review ring forensics.
- **PersonalWatchAgent**: High-profile VIP protection, audio/video deepfake analysis, and impersonation detection.
- **AgentReach Scraper**: Zero-cost scraper fabric spanning Reddit, Twitter/X, YouTube, Google News, and Jina Reader.
""",
    version="3.5.1",
    openapi_tags=tags_metadata
)

# ── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.middleware("http")
async def request_logger(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000.0
    logger.info(
        f"[HTTP] rid={rid} method={request.method} path={request.url.path} "
        f"status={response.status_code} duration_ms={duration:.1f}"
    )
    response.headers["X-Request-ID"] = rid
    return response


# ── Register Modular API Routers ─────────────────────────────────────────────
try:
    from backend.api import all_routers
    for domain_router in all_routers:
        app.include_router(domain_router)
    logger.info(f"[FastAPI] Registered {len(all_routers)} domain routers successfully")
except (ImportError, ModuleNotFoundError):
    from api import all_routers
    for domain_router in all_routers:
        app.include_router(domain_router)


# ── Startup & Shutdown Lifecycle ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 80)
    logger.info("[FastAPI] Aegis Protocol API v3.5.1 — STARTING (Modular Architecture)")
    logger.info(f"[FastAPI] Supabase URL: {os.getenv('SUPABASE_URL', 'NOT SET (Using Local SQLite)')}")
    logger.info("[FastAPI] Agents: ClaimIngestion | Research | Investigator | Trending | Scout | BrandShield | PersonalWatch")
    logger.info("=" * 80)

    # Warm dashboard cache
    try:
        from backend.services.dashboard_loader import get_dashboard_claims_rotating
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: get_dashboard_claims_rotating(
                n=15, ttl_seconds=int(os.getenv("DASHBOARD_TTL", "300"))
            )
        )
        logger.info("[Startup] Dashboard cache warmed")
    except Exception as e:
        logger.warning(f"[Startup] Failed to warm dashboard cache: {e}")

    # Start RSS ingestion background loop
    if os.getenv("RSS_INGESTION_ENABLED", "true").lower() != "false":
        from backend.services.rss_ingestion import rss_ingestion_loop
        asyncio.create_task(rss_ingestion_loop())
        logger.info("[FastAPI] RSS ingestion loop scheduled (15 min interval)")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("=" * 80)
    logger.info("[FastAPI] Aegis Protocol API — SHUTTING DOWN")
    logger.info("=" * 80)


# ── Frontend HTML Page Routes ────────────────────────────────────────────────
@app.get("/")
@app.get("/index.html")
async def root():
    return FileResponse("frontend/index.html")


@app.get("/launch-video", tags=["Media & Teaser"])
@app.get("/teaser", tags=["Media & Teaser"])
async def serve_launch_video():
    video_page = "brag-output/composition/index.html"
    if os.path.exists(video_page):
        return FileResponse(video_page)
    return FileResponse("frontend/index.html")


@app.get("/dashboard")
@app.get("/dashboard.html")
async def dashboard_page():
    return FileResponse("frontend/dashboard.html")


@app.get("/agents")
@app.get("/agents.html")
async def agents_page():
    return FileResponse("frontend/agents.html")


@app.get("/about")
@app.get("/about.html")
async def about_page():
    return FileResponse("frontend/about.html")


@app.get("/submit")
@app.get("/submit.html")
async def submit_page():
    return FileResponse("frontend/submit.html")


@app.get("/status")
@app.get("/status.html")
async def status_page():
    return FileResponse("frontend/status.html")


@app.get("/changelog")
@app.get("/changelog.html")
async def changelog_page():
    return FileResponse("frontend/changelog.html")


@app.get("/trending-agent")
@app.get("/trending-agent.html")
async def trending_agent_page():
    return FileResponse("frontend/trending-agent.html")


@app.get("/scout-agent")
@app.get("/scout-agent.html")
async def scout_agent_page():
    return FileResponse("frontend/scout-agent.html")


@app.get("/personal-watch-agent")
@app.get("/personal-watch-agent.html")
async def personal_watch_agent_page():
    return FileResponse("frontend/personal-watch-agent.html")


@app.get("/brandshield-agent")
@app.get("/brandshield-agent.html")
async def brandshield_agent_page():
    return FileResponse("frontend/brandshield-agent.html")


@app.get("/lab")
@app.get("/lab.html")
async def lab_page():
    return FileResponse("frontend/lab.html")


@app.get("/favicon.ico")
async def favicon():
    if os.path.exists("frontend/favicon.ico"):
        return FileResponse("frontend/favicon.ico")
    return JSONResponse({"status": "no favicon"}, status_code=404)


@app.get("/dashboard.css")
async def dashboard_css():
    return FileResponse("frontend/dashboard.css")


@app.get("/dashboard.js")
async def dashboard_js():
    return FileResponse("frontend/dashboard.js")


@app.get("/{filename:path}")
async def serve_static_root(filename: str):
    """Serve any static asset located in frontend directory at root URL."""
    if ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    file_path = os.path.join("frontend", filename)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail=f"File not found: {filename}")


if __name__ == "__main__":
    import uvicorn
    logger.info("[FastAPI] Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
