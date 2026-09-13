"""
Agents Module

Contains all agent implementations for the misinformation detection system.
"""

from .claim_ingestion_agent import ClaimIngestionAgent
from .research_agent import ResearchAgent
from .investigator_agent import InvestigatorAgent
from .scout_agent import ScoutAgent
from .trending_agent import TrendingAgent
from .brandshield_agent import BrandShieldAgent
from .personal_agent import PersonalWatchAgent

__all__ = [
    'ClaimIngestionAgent',
    'ResearchAgent',
    'InvestigatorAgent',
    'ScoutAgent',
    'TrendingAgent',
    'BrandShieldAgent',
    'PersonalWatchAgent',
]
