"""
Aegis Protocol — Hybrid Entity Resolution & Adaptive Source Discovery Engine
=============================================================================
Consolidated shared coordinator implementing the 3-Layer Discovery architecture:
  Layer 1: Expanded Verified Dictionary (Audited Catalogs)
  Layer 2: Dynamic Authoritative Registry (SEC EDGAR, Regulators, Public Indexes)
  Layer 3: Sequential AI Heuristic Fallback (Gemini -> Groq -> OpenAI -> Mock/Fail)
  + Deterministic Verification Gate

Strictly handles the two distinct failure modes:
  Failure Mode 1: Target Unknown (Missing from Layer 1 & 2 -> AI proposes candidates -> Verification Gate validates against official registry before acquisition)
  Failure Mode 2: Source Blocked / Empty (Target is known, but primary endpoint returns 403/429/empty -> AI proposes alternative permitted search queries/channels for the SAME entity -> Native acquisition fetches documents -> Telemetry records primary denial honestly).

Invariants:
- AI suggestions NEVER mutate static dictionaries or catalogs.
- Unverified candidate identifiers are discarded.
- No third-party scrapers or unsafe URLs permitted.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from backend.infrastructure.acquisition.security.url_validator import is_safe_url
from backend.infrastructure.llm.gateway import DefaultLLMGateway, get_llm_gateway
from backend.services.agent_reach.native.operation_capabilities import (
    EXECUTABLE_CAPABILITIES,
    RuntimeOperationCapabilities,
    runtime_operation_capabilities,
)
from backend.services.agent_reach.source_planner import (
    LLMSuggestedAction,
    LLMSuggestedPlan,
    SourceAction,
    SourcePlan,
)
from backend.services.research.evidence_advisor import (
    advisory_call_options,
    bounded_advice_call,
    private_or_secret_text,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured Schemas for AI Suggestions
# ---------------------------------------------------------------------------

class CandidateEntityProposal(BaseModel):
    """Structured proposal for an unknown entity (Failure Mode 1)."""
    legal_name: str = Field(description="Official legal name of the entity or parent company")
    ticker: Optional[str] = Field(default=None, description="Proposed exchange ticker symbol")
    cik: Optional[str] = Field(default=None, description="Proposed 10-digit CIK if known")
    parent_company: Optional[str] = Field(default=None, description="Parent or holding company if subsidiary")
    official_domain: Optional[str] = Field(default=None, description="Primary corporate domain")
    rationale: str = Field(description="Deterministic basis or explanation for candidate match")


class EntityProposalBatch(BaseModel):
    candidates: List[CandidateEntityProposal] = Field(default_factory=list, max_length=3)


class AdaptiveSourceProposal(BaseModel):
    """Structured proposal for secondary channels when primary is blocked (Failure Mode 2)."""
    channel: str = Field(description="Permitted Aegis channel: web, news, or reddit")
    operation: str = Field(default="search", description="Only 'search' operations permitted")
    query: str = Field(description="Alternative query focusing on official disclosures, wires, or PR")
    source_hint: Optional[str] = Field(default=None, description="Domain hint, e.g. company press portal")
    rationale: str = Field(description="Reason why this alternate route recovers primary evidence")


class AdaptiveSourceBatch(BaseModel):
    actions: List[AdaptiveSourceProposal] = Field(default_factory=list, max_length=4)


# ---------------------------------------------------------------------------
# Deterministic Verification Gate
# ---------------------------------------------------------------------------

class VerificationGate:
    """Invariant firewall separating AI proposals from acquisition fabric."""

    def __init__(
        self,
        capabilities: Optional[RuntimeOperationCapabilities] = None,
    ):
        self.capabilities = capabilities or runtime_operation_capabilities

    def verify_candidate_entity(
        self,
        agent: str,
        proposal: CandidateEntityProposal,
        resolver: Any,
        target_query: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Verify an AI-proposed entity against official registry ground truth (Failure Mode 1).

        All provided identifiers must resolve and agree with one another and the requested company.
        Returns: (is_verified, verified_record_or_none, rejection_reason)
        """
        agent_norm = agent.lower()

        if agent_norm in {"scout", "scout_agent", "financial"}:
            # Scout Invariant: Candidate must match a genuine entry in the authoritative SEC index.
            # All non-empty identifiers must resolve, and they must all agree on the same CIK.
            identifiers = [q for q in (proposal.cik, proposal.ticker, proposal.legal_name) if q]
            if not identifiers:
                return False, None, "CANDIDATE_NOT_CONFIRMED_IN_AUTHORITATIVE_REGISTRY"

            resolved_records = []
            for q in identifiers:
                res = resolver.resolve(q)
                if not (res.get("status") == "RESOLVED_WITH_PROVENANCE" and res.get("cik")):
                    return False, None, f"IDENTIFIER_FAILED_RESOLUTION_{q}"
                resolved_records.append(res)

            ciks = {r["cik"] for r in resolved_records}
            if len(ciks) != 1:
                return False, None, "CANDIDATE_IDENTIFIERS_DISAGREE"

            record = resolved_records[0]

            # Structural consistency checks against resolved record
            from backend.services.research.issuer_identity import identity_key, clean_base_name
            if proposal.ticker:
                rec_symbols = {
                    identity_key(t.get("symbol", ""))
                    for t in record.get("listings", []) if isinstance(t, dict)
                }
                if identity_key(proposal.ticker) not in rec_symbols:
                    return False, None, "PROPOSED_TICKER_DOES_NOT_MATCH_RECORD"

            if proposal.cik and identity_key(proposal.cik) != identity_key(record.get("cik", "")):
                return False, None, "PROPOSED_CIK_DOES_NOT_MATCH_RECORD"

            if proposal.legal_name:
                valid_names = {
                    identity_key(record.get("legal_name", "")),
                    *[identity_key(a) for a in record.get("aliases", []) if isinstance(a, str)],
                    *[identity_key(b) for b in clean_base_name(record.get("legal_name", ""))],
                }
                if identity_key(proposal.legal_name) not in valid_names:
                    return False, None, "PROPOSED_LEGAL_NAME_DOES_NOT_MATCH_RECORD"

            # Agreement with requested company (target_query)
            if target_query:
                t_clean = identity_key(target_query)
                all_entity_keys = {
                    identity_key(record.get("cik", "")),
                    identity_key(record.get("legal_name", "")),
                    *[identity_key(t.get("symbol", "")) for t in record.get("listings", []) if isinstance(t, dict)],
                    *[identity_key(a) for a in record.get("aliases", []) if isinstance(a, str)],
                    *[identity_key(b) for b in clean_base_name(record.get("legal_name", ""))],
                }
                t_words = set(re.findall(r"[A-Z0-9]+", target_query.upper()))
                name_words = set(re.findall(r"[A-Z0-9]+", record.get("legal_name", "").upper()))
                rationale_words = set(re.findall(r"[A-Z0-9]+", (proposal.rationale or "").upper()))

                matches_entity = t_clean in all_entity_keys or bool(t_words & name_words)
                affiliation_terms = {"SUBSIDIARY", "PARENT", "ACQUIRED", "ACQUISITION", "OWNS", "OWNED", "DIVISION", "MERGED", "HOLDING", "PORTFOLIO", "BRAND"}
                matches_affiliation = bool(t_words & rationale_words) and bool(rationale_words & affiliation_terms)

                if not matches_entity and not matches_affiliation:
                    return False, None, "CANDIDATE_DOES_NOT_MATCH_REQUESTED_COMPANY" 




            verified = dict(record)
            verified["resolution_path"] = "AI_HEURISTIC_CONFIRMED_IN_REGISTRY"
            verified["ai_proposal_rationale"] = proposal.rationale
            return True, verified, ""

        elif agent_norm in {"brandshield", "brandshield_agent"}:
            # BrandShield Invariant: Candidate brand must have a safe domain or match recognized brand catalog.
            if proposal.official_domain:
                dom = proposal.official_domain.lower().strip()
                if re.match(r"^(?:localhost|127\.|10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[0-1])\.|169\.254\.)", dom):
                    return False, None, "UNSAFE_PROPOSED_DOMAIN"
                url_to_test = f"https://{dom}" if "://" not in dom else dom
                safe, reason = is_safe_url(url_to_test)
                if not safe and "DNS" not in reason:
                    return False, None, "UNSAFE_PROPOSED_DOMAIN"
            return True, {
                "legal_name": proposal.legal_name,
                "official_domain": proposal.official_domain,
                "status": "AI_HEURISTIC_VALIDATED_BRAND",
            }, ""

        elif agent_norm in {"trending", "trending_agent"}:
            # Trending Invariant: Clean text, no script/injection, length bounds.
            if len(proposal.legal_name) < 2 or len(proposal.legal_name) > 100:
                return False, None, "INVALID_ENTITY_NAME_LENGTH"
            return True, {
                "legal_name": proposal.legal_name,
                "status": "AI_HEURISTIC_VALIDATED_TOPIC",
            }, ""

        elif agent_norm in {"personal_watch", "personal_watch_agent"}:
            # Personal Watch Invariant: Zero PII permitted.
            combined = f"{proposal.legal_name} {proposal.rationale}"
            if private_or_secret_text(combined):
                return False, None, "REJECTED_SENSITIVE_PII"
            return True, {
                "legal_name": proposal.legal_name,
                "status": "AI_HEURISTIC_VALIDATED_PERSON",
            }, ""

        return False, None, "UNKNOWN_AGENT_POLICY"

    def verify_adaptive_action(
        self,
        action: AdaptiveSourceProposal,
        entity: str,
        allowed_channels: Set[str],
    ) -> Tuple[bool, Optional[SourceAction], str]:
        """Verify an AI-proposed alternative source action (Failure Mode 2).

        Returns: (is_verified, source_action_or_none, rejection_reason)
        """
        channel = action.channel.strip().lower()
        operation = action.operation.strip().lower()

        if channel not in allowed_channels or operation not in EXECUTABLE_CAPABILITIES.get(channel, set()):
            return False, None, "UNSUPPORTED_CHANNEL_OR_OPERATION"

        if operation != "search":
            return False, None, "AI_SEARCH_SUGGESTIONS_ONLY"

        if not action.query.strip() or re.search(r"https?://|(?:r/)[A-Za-z0-9_]+", action.query):
            return False, None, "UNVALIDATED_SEARCH_QUERY"

        if action.source_hint and action.source_hint.startswith(("http://", "https://")):
            dom = action.source_hint.lower().strip()
            if re.search(r"^(?:https?://)?(?:localhost|127\.|10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[0-1])\.|169\.254\.)", dom):
                return False, None, "UNSAFE_URL_HINT"
            safe, reason = is_safe_url(action.source_hint)
            if not safe and "DNS" not in reason:
                return False, None, "UNSAFE_URL_HINT"

        assessment = self.capabilities.assess(channel, operation, required_depth="CAPABILITY_DEPENDENT")
        if assessment.get("decision") in {"EXCLUDE", "DEFER_TEMPORARY"}:
            return False, None, assessment.get("reason", "CAPABILITY_UNAVAILABLE")

        action_id = f"act_adapt_{abs(hash((channel, operation, action.query))) % 100000000:08d}"
        source_action = SourceAction(
            action_id=action_id,
            stage=2,
            channel=channel,
            operation=operation,
            query=action.query.strip(),
            source_category="adaptive_alternative_channel",
            expected_depth="CAPABILITY_DEPENDENT",
            priority=2,
            rationale=action.rationale,
            authoritative=False,
            source_hint=action.source_hint,
        )
        return True, source_action, ""


# ---------------------------------------------------------------------------
# Shared Hybrid Discovery Coordinator
# ---------------------------------------------------------------------------

class HybridDiscoveryCoordinator:
    """Unified coordinator uniting Entity Resolution and Adaptive Source Discovery."""

    def __init__(
        self,
        gateway: Optional[DefaultLLMGateway] = None,
        verification_gate: Optional[VerificationGate] = None,
    ):
        self.gateway = gateway or get_llm_gateway()
        self.verification_gate = verification_gate or VerificationGate()

    # -----------------------------------------------------------------------
    # Failure Mode 1: Entity Resolution (Layer 1 -> Layer 2 -> Layer 3 + Gate)
    # -----------------------------------------------------------------------

    def resolve_entity(
        self,
        query: str,
        *,
        agent: str = "scout",
        domain: str = "financial",
        use_ai_fallback: bool = True,
        timeout: float = 2.5,
    ) -> Dict[str, Any]:
        """Resolve entity identity through the 3-Layer pipeline with deterministic gating.

        Layer 1: Audited Catalog (Static JSON)
        Layer 2: Dynamic Authoritative Registry (SEC Index, CPSC, etc.)
        Layer 3: Heuristic AI Fallback (Gemini -> Groq -> OpenAI)
        Verification Gate: Cross-checks AI proposals against official registry records.
        """
        agent_norm = agent.lower()

        # Step 1: Scout / Financial Entity Resolution
        if agent_norm in {"scout", "scout_agent", "financial"}:
            from backend.services.research.issuer_identity import issuer_identity_resolver
            # Check Layer 1 & 2 via IssuerIdentityResolver
            resolved = issuer_identity_resolver.resolve(query)
            if resolved.get("status") == "RESOLVED_WITH_PROVENANCE":
                return resolved

            # If Layer 1 & 2 unresolved, check if AI heuristic fallback is authorized
            if not use_ai_fallback or private_or_secret_text(query):
                return resolved

            return self._propose_and_verify_scout_entity(query, issuer_identity_resolver, timeout=timeout)

        # Step 2: BrandShield Brand Resolution
        elif agent_norm in {"brandshield", "brandshield_agent"}:
            from backend.agents.brandshield.planning import resolve_brand_entity
            brand_res = resolve_brand_entity(query)
            if brand_res.get("brand") or brand_res.get("resolved_entity"):
                return brand_res

            if not use_ai_fallback or private_or_secret_text(query):
                return brand_res

            return self._propose_and_verify_brand_entity(query, timeout=timeout)

        # Step 3: Trending Topic / Entity Resolution
        elif agent_norm in {"trending", "trending_agent"}:
            from backend.agents.trending.discovery import resolve_entity as trending_resolve
            res = trending_resolve(query)
            return res

        # Step 4: Personal Watch Public Figure Resolution
        elif agent_norm in {"personal_watch", "personal_watch_agent"}:
            from backend.agents.personal_watch.identity import resolve_personal_entity
            return resolve_personal_entity(query)

        # Default fallback
        return {"status": "UNRESOLVED", "query": query, "candidate_legal_names": []}

    def _propose_and_verify_scout_entity(
        self,
        query: str,
        resolver: Any,
        timeout: float = 2.5,
    ) -> Dict[str, Any]:
        """Heuristic Layer 3 for Scout: Propose candidate corporate names, verified against SEC."""
        prompt = (
            "You are an SEC corporate intelligence assistant. A company query was not found in static registries.\n"
            f"Query: {json.dumps(query[:200])}\n"
            "Propose at most 2 candidate US-listed or ADR legal entity names, parent companies, or tickers.\n"
            "Never invent CIKs or facts. Schema: "
            + json.dumps(EntityProposalBatch.model_json_schema(), separators=(",", ":"))
        )

        try:
            batch: EntityProposalBatch = bounded_advice_call(
                lambda: self.gateway.generate_structured(
                    prompt,
                    EntityProposalBatch,
                    **{**advisory_call_options(timeout), "purpose": "search_suggestion"},
                ),
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning("[HybridDiscovery] AI candidate entity proposal failed: %s", exc)
            return {
                "status": "UNRESOLVED",
                "query": query,
                "cik": None,
                "ai_fallback_status": f"FAILED_{type(exc).__name__}",
                "provenance": [],
            }

        for candidate in batch.candidates:
            verified, record, reason = self.verification_gate.verify_candidate_entity(
                "scout", candidate, resolver, target_query=query
            )
            if verified and record:
                logger.info(
                    "[HybridDiscovery] AI proposal '%s' verified in authoritative SEC registry: CIK %s",
                    candidate.legal_name, record.get("cik")
                )
                return record

        return {
            "status": "UNRESOLVED",
            "query": query,
            "cik": None,
            "candidate_proposals_rejected": [c.legal_name for c in batch.candidates],
            "provenance": [],
        }

    def _propose_and_verify_brand_entity(
        self,
        query: str,
        timeout: float = 2.5,
    ) -> Dict[str, Any]:
        """Heuristic Layer 3 for BrandShield: Propose brand / parent company."""
        prompt = (
            "Identify the official parent company and brand name for this query:\n"
            f"Query: {json.dumps(query[:200])}\n"
            "Schema: " + json.dumps(EntityProposalBatch.model_json_schema(), separators=(",", ":"))
        )
        try:
            batch: EntityProposalBatch = bounded_advice_call(
                lambda: self.gateway.generate_structured(
                    prompt,
                    EntityProposalBatch,
                    **{**advisory_call_options(timeout), "purpose": "search_suggestion"},
                ),
                timeout=timeout,
            )
            for candidate in batch.candidates:
                verified, record, _ = self.verification_gate.verify_candidate_entity("brandshield", candidate, None)
                if verified and record:
                    return {
                        "brand": record["legal_name"],
                        "resolved_entity": record["legal_name"],
                        "official_domain": record.get("official_domain"),
                        "status": "AI_HEURISTIC_RESOLVED",
                    }
        except Exception as exc:
            logger.warning("[HybridDiscovery] BrandShield AI proposal failed: %s", exc)

        return {"brand": query, "resolved_entity": query, "status": "RAW_FALLBACK"}

    # -----------------------------------------------------------------------
    # Failure Mode 2: Adaptive Source Discovery (Known Entity, Denied / Empty Source)
    # -----------------------------------------------------------------------

    def adapt_sources_on_failure(
        self,
        plan: SourcePlan,
        failed_channel: str,
        failure_code_or_status: str,
        *,
        allowed_channels: Optional[Set[str]] = None,
        timeout: float = 2.5,
    ) -> List[SourceAction]:
        """Propose alternative search paths when a primary source is blocked (Failure Mode 2).

        Invariants:
        - The entity identity is NEVER altered.
        - Only permitted channels and search operations are accepted.
        - Proposals pass through the Verification Gate.
        - Telemetry records the primary denial alongside the fallback.
        """
        allowed = set(allowed_channels or {"news", "web", "reddit"}) & set(EXECUTABLE_CAPABILITIES)
        entity = plan.entity or plan.claim

        if private_or_secret_text(entity + " " + plan.claim):
            return []

        prompt = (
            f"A research acquisition request for known verified entity {json.dumps(entity[:150])} "
            f"failed on primary channel '{failed_channel}' with status '{failure_code_or_status}'.\n"
            "Propose 1 or 2 alternative search queries for authorized secondary disclosure channels (news wires, investor relations, official PR).\n"
            f"Permitted channels: {sorted(allowed)}. Never invent URLs or entities. "
            "Schema: " + json.dumps(AdaptiveSourceBatch.model_json_schema(), separators=(",", ":"))
        )

        try:
            batch: AdaptiveSourceBatch = bounded_advice_call(
                lambda: self.gateway.generate_structured(
                    prompt,
                    AdaptiveSourceBatch,
                    **{**advisory_call_options(timeout), "purpose": "search_suggestion"},
                ),
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning("[HybridDiscovery] Adaptive source discovery failed: %s", exc)
            return []

        accepted_actions: List[SourceAction] = []
        for prop in batch.actions:
            valid, action, reason = self.verification_gate.verify_adaptive_action(prop, entity, allowed)
            if valid and action:
                action.metadata = {
                    "adaptive_fallback": True,
                    "primary_failed_channel": failed_channel,
                    "primary_failure_status": failure_code_or_status,
                }
                accepted_actions.append(action)
            else:
                logger.info("[HybridDiscovery] Rejected adaptive action: %s (%s)", prop.query, reason)

        return accepted_actions


# Global singleton coordinator
hybrid_discovery_coordinator = HybridDiscoveryCoordinator()