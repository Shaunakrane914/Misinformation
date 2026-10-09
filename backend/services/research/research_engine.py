"""Compatibility entry point for the application research pipeline.

Callers may continue to import ResearchEngine and research_engine from this
module. Investigation behavior is implemented in backend.application.research.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.services.research.research_budget import ResearchBudget, default_budget
from backend.services.research.research_models import EvidenceItem, Finding, ResearchRequest, ResearchResult

logger = logging.getLogger(__name__)


class ResearchEngine:
    def __init__(self, budget: Optional[ResearchBudget] = None):
        self.budget = budget or default_budget
        logger.info("[ResearchEngine] Initialized with full research pipeline and bounded budgets")

    def _synthesize_grounded_findings(
        self, target_name: str, domain: str, investigated_items: List[EvidenceItem],
        contradictions: List[Dict[str, Any]], intent: str = ""
    ) -> List[Finding]:
        """Preserve the historical helper for existing integrations."""
        from backend.application.research.synthesis import synthesize_grounded_findings

        return synthesize_grounded_findings(
            target_name, domain, investigated_items, contradictions, intent
        )

    def investigate(self, request: ResearchRequest) -> ResearchResult:
        from backend.application.research.pipeline import ResearchPipeline

        return ResearchPipeline(self.budget).run(request)


research_engine = ResearchEngine()
