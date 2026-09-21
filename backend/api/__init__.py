"""
Aegis Protocol — API Router Registry
====================================
Exposes modular domain routers for FastAPI application assembly.
"""

from fastapi import APIRouter
from backend.api.system import router as system_router
from backend.api.claims import router as claims_router
from backend.api.agent_reach import router as agent_reach_router
from backend.api.threat_lab import router as threat_lab_router
from backend.api.agents import router as agents_router

all_routers = [
    system_router,
    claims_router,
    agent_reach_router,
    threat_lab_router,
    agents_router,
]
