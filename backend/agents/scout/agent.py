"""
Aegis Protocol — Scout Agent 2.0
=================================
Predictive Financial Engine: detects statistical anomalies in stock prices,
conducts multi-channel evidence acquisition, identifies corporate catalysts,
flags coordinated short attacks and misinformation, and predicts price movement.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from backend.agents.scout.assessment import (
    correlate_social_rumors,
    synthesize_financial_intelligence,
)
from backend.agents.scout.extraction import scout_extractor
from backend.agents.scout.financial import (
    analyze_volatility,
    check_stock_impact,
    extract_prices,
    fetch_stock_data,
    predict_impact,
    resolve_ticker_and_company,
)
from backend.services.agent_reach.adapter import agent_reach_service  # Architecture contract preservation

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ScoutAgent:
    """
    The Scout Agent monitors stock prices for anomalies, performs multi-channel
    evidence discovery, and predicts future market movements.
    
    Key Features:
    - Statistical anomaly detection using Z-score analysis
    - Volatility monitoring with 2-sigma threshold
    - Empirical volatility-envelope price prediction
    - Real-time market data integration via Yahoo Finance / yfapi.net
    - Omni-channel social intelligence and short-attack correlation
    """
    
    def __init__(self):
        """Initialize the Scout Agent with API configuration."""
        self.api_key = os.getenv("YF_API_KEY", "")
        self.base_url = "https://yfapi.net"
        
        if not self.api_key:
            logger.warning("YF_API_KEY not found in environment variables")
        else:
            logger.info("Scout Agent initialized with yfapi.net")
    
    def fetch_stock_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time stock chart data from Yahoo Finance API."""
        return fetch_stock_data(ticker, base_url=self.base_url, api_key=self.api_key)
    
    def extract_prices(self, chart_data: Dict[str, Any]) -> Optional[List[float]]:
        """Extract closing prices from chart data."""
        return extract_prices(chart_data)
    
    def analyze_volatility(self, prices: List[float]) -> Dict[str, Any]:
        """Analyze price volatility using statistical Z-score methods."""
        return analyze_volatility(prices)
    
    def predict_impact(self, prices: List[float]) -> Dict[str, Any]:
        """Honest Market Signal Framework for volatility and drift bounds."""
        return predict_impact(prices)
    
    def resolve_ticker_and_company(self, ticker: str) -> Tuple[str, str]:
        """Resolve ticker to standard symbol and clean corporate entity name."""
        return resolve_ticker_and_company(ticker)

    def correlate_social_rumors(self, ticker: str) -> Dict[str, Any]:
        """Correlate stock price volatility with real-time omni-channel signals."""
        return correlate_social_rumors(ticker)

    def check_stock_impact(self, ticker: str) -> Dict[str, Any]:
        """Check stock impact, crash probability, and correlate with social intelligence."""
        return check_stock_impact(
            ticker=ticker,
            base_url=self.base_url,
            api_key=self.api_key,
            social_correlator=self.correlate_social_rumors
        )

    def _synthesize_financial_intelligence(
        self,
        company_name: str,
        ticker: str,
        stock_data: Dict[str, Any],
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Synthesize financial intelligence over retrieved evidence fragments."""
        return synthesize_financial_intelligence(company_name, ticker, stock_data, sources)

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method for the Scout Agent.
        
        Orchestrates:
        1. Fetch real-time stock data
        2. Extract closing prices
        3. Analyze volatility for crash detection
        4. Predict future price movement
        """
        try:
            ticker = task.get('ticker', 'TATAMOTORS.NS')
            logger.info(f"🔍 Processing Scout task for ticker: {ticker}")
            
            # DEMO MODE: Return mock crash for DEMO.NS ticker
            if ticker == "DEMO.NS":
                logger.critical("🎬 DEMO MODE: Simulating Sigma Event for demonstration")
                return {
                    "ticker": "DEMO.NS",
                    "current_price": 1250.00,
                    "timestamp": datetime.now().isoformat(),
                    "stats": {
                        "z_score": -2.8,
                        "volatility_status": "SIGMA_EVENT",
                        "mean": 1300.00,
                        "std_dev": 17.86
                    },
                    "prediction": {
                        "projected_price_1hr": 1200.00,
                        "projected_loss": -4.0,
                        "trend": "DOWNWARD"
                    },
                    "status": "completed",
                    "data_points_analyzed": 100,
                    "demo_mode": True
                }
            
            # Step 1: Fetch stock data
            chart_data = self.fetch_stock_data(ticker)
            if not chart_data:
                return {
                    "ticker": ticker,
                    "status": "failed",
                    "error": "Failed to fetch stock data"
                }
            
            # Step 2: Extract prices
            prices = self.extract_prices(chart_data)
            if not prices:
                return {
                    "ticker": ticker,
                    "status": "failed",
                    "error": "Failed to extract price data"
                }
            
            # Step 3: Analyze volatility
            volatility_analysis = self.analyze_volatility(prices)
            current_price = volatility_analysis.get('latest_price', prices[-1])
            
            # Step 4: Predict impact
            prediction = self.predict_impact(prices)
            
            # Step 5: Compile results
            result = {
                "ticker": ticker,
                "current_price": current_price,
                "timestamp": datetime.now().isoformat(),
                "stats": {
                    "z_score": volatility_analysis.get('z_score', 0.0),
                    "volatility_status": volatility_analysis.get('volatility_status', 'UNKNOWN'),
                    "mean": volatility_analysis.get('mean', 0.0),
                    "std_dev": volatility_analysis.get('std_dev', 0.0)
                },
                "prediction": {
                    "projected_price_1hr": prediction.get('projected_price_1hr', 0.0),
                    "projected_loss": prediction.get('projected_loss', 0.0),
                    "trend": prediction.get('trend', 'UNKNOWN')
                },
                "status": "completed",
                "data_points_analyzed": len(prices)
            }
            
            # Log critical events
            if volatility_analysis.get('volatility_status') == 'SIGMA_EVENT':
                logger.critical(f"🚨 SIGMA EVENT DETECTED for {ticker}!")
                logger.critical(f"   Current: {current_price} | Z-score: {volatility_analysis.get('z_score')}")
                logger.critical(f"   Projected 1hr: {prediction.get('projected_price_1hr')} ({prediction.get('projected_loss')}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing Scout task: {str(e)}")
            return {
                "ticker": task.get('ticker', 'UNKNOWN'),
                "status": "failed",
                "error": str(e)
            }

    def analyze_stock(self, ticker: str, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute comprehensive Financial Intelligence Research Workspace analysis.
        Orchestrates:
        1. Market telemetry & anomaly detection
        2. Agent Reach multi-channel retrieval (News, Reddit, Twitter, YouTube, RSS)
        3. Forensic source role & primary source classification
        4. Chronological research timeline construction
        5. Grounded catalyst, narrative, and contradiction reasoning
        """
        start_t = datetime.utcnow()
        sym, company_name = self.resolve_ticker_and_company(ticker)

        # 1. Market Telemetry
        stock_data = self.check_stock_impact(sym)
        if not stock_data or not stock_data.get("current_price"):
            stock_data = {
                "ticker": sym,
                "name": company_name,
                "current_price": 0.0,
                "prev_close": 0.0,
                "drop_percent": 0.0,
                "z_score": 0.0,
                "currency": "INR" if sym.endswith(".NS") or sym.endswith(".BO") else "USD",
                "is_crashing": False,
                "data_source": "Historical Daily Close via Yahoo Finance Chart API (Delayed) — Non-realtime"
            }
        else:
            stock_data["name"] = company_name
            stock_data["currency"] = "INR" if sym.endswith(".NS") or sym.endswith(".BO") else "USD"
            stock_data["data_source"] = "Historical Daily Close via Yahoo Finance Chart API (Delayed) — Non-realtime"

        # 2. Shared Deep Research Engine Retrieval & Investigation
        from backend.services.research import research_engine, ResearchRequest
        research_req = ResearchRequest(
            target=f"{company_name} ({sym})",
            domain="financial",
            intent=query or f"investigate financial performance, corporate filings, regulatory risks, and market catalysts for {company_name}",
            query_classes=[
                "latest_primary", "official_statement", "regulatory", "investigative",
                "independent_reporting", "community_signal", "contradiction"
            ],
            required_source_roles=["PRIMARY", "SECONDARY", "COMMUNITY"],
            deep_read_budget=15,
            corroboration_budget=4,
        )
        research_res = None
        try:
            research_res = research_engine.investigate(research_req)
            evidence_items = research_res.evidence
            research_findings = research_res.findings
            research_telemetry = research_res.telemetry
            retrieval_trace = research_telemetry
            retrieval_plan = {
                "query_classes": research_req.query_classes,
                "trace": research_telemetry
            }
            channel_health = research_telemetry.get("channel_health", {})
        except Exception as e_ret:
            logger.warning(f"[ScoutAgent:analyze_stock] ResearchEngine exception: {e_ret}")
            evidence_items = []
            research_findings = []
            research_telemetry = {}
            retrieval_plan = {}
            retrieval_trace = {}
            channel_health = {}

        scout_result = None

        # 3. Classify & Group Fragments
        primary_sources = []
        news_items = []
        reddit_items = []
        twitter_items = []
        youtube_items = []
        all_sources = []

        syndicated_count = 0

        for idx, item in enumerate(evidence_items):
            if hasattr(item, "id"):
                e_id = item.id
                title = item.title or "Untitled Discovered Signal"
                url = item.canonical_url or ""
                source_name = item.source_name or item.channel
                channel = item.channel
                published = item.published_at or "Recent"
                discovered = item.discovered_at
                snippet = item.snippet or item.relevant_excerpt[:240]
                relevant_excerpt = item.relevant_excerpt
                role = item.source_role
                tier = item.source_tier
                group = item.independence_group
                family_id = item.source_family_id
                depth = item.content_depth
                q_id = item.query_id
                q_class = item.query_class
                q_text = item.query_text
                is_primary = item.primary_source or role in ("PRIMARY", "PRIMARY_OFFICIAL", "PRIMARY_REGULATORY")
            else:
                e_id = item.get("evidence_id", f"src_{idx+1:03d}")
                title = item.get("title", "Untitled Discovered Signal")
                url = item.get("url", "")
                source_name = item.get("source", item.get("platform", "Channel"))
                channel = item.get("channel", item.get("platform", "news"))
                published = item.get("published_at", item.get("published", "Recent"))
                discovered = item.get("retrieved_at", "")
                snippet = item.get("snippet", "")
                relevant_excerpt = item.get("relevant_excerpt", "")
                role = item.get("source_role", "DISCOVERY")
                tier = item.get("source_tier", "TIER_3_AGGREGATE")
                group = item.get("independence_group", item.get("source_independence_group", "independent"))
                family_id = item.get("source_family_id", "")
                depth = item.get("content_depth", "SNIPPET")
                q_id = item.get("query_id", "")
                q_class = item.get("query_class", "general")
                q_text = item.get("query_text", "")
                is_primary = role == "PRIMARY"

            if group and group.startswith("syndicated_"):
                syndicated_count += 1

            source_record = {
                "evidence_id": e_id,
                "discovered_candidate_id": getattr(item, "discovered_id", getattr(item, "id", None)) if hasattr(item, "id") else item.get("discovered_id", item.get("id")),
                "ranked_candidate_id": getattr(item, "ranked_id", None) if hasattr(item, "id") else item.get("ranked_id"),
                "accepted_candidate_id": getattr(item, "accepted_id", None) if hasattr(item, "id") else item.get("accepted_id"),
                "acquisition_attempt_id": getattr(item, "acquisition_attempt_id", None) if hasattr(item, "id") else item.get("acquisition_attempt_id"),
                "acquired_candidate_id": getattr(item, "acquired_id", None) if hasattr(item, "id") else item.get("acquired_id"),
                "selection_decision": getattr(item, "selection_decision", "ACCEPTED") if hasattr(item, "id") else item.get("selection_decision", "ACCEPTED"),
                "selection_reason": getattr(item, "selection_reason", "ACQUIRED_EVIDENCE") if hasattr(item, "id") else item.get("selection_reason", "ACQUIRED_EVIDENCE"),
                "title": title,
                "url": url,
                "has_url": bool(url),
                "author": source_name,
                "source": source_name,
                "channel": channel,
                "published_at": published,
                "retrieved_at": discovered,
                "snippet": snippet,
                "relevant_excerpt": relevant_excerpt,
                "source_role": role,
                "source_tier": tier,
                "independence_group": group,
                "source_family_id": family_id,
                "content_depth": depth,
                "query_id": q_id,
                "query_class": q_class,
                "query_text": q_text,
            }
            all_sources.append(source_record)

            if is_primary or "investor" in url.lower() or "filing" in title.lower() or "sec.gov" in url.lower():
                primary_sources.append(source_record)

            ch_low = channel.lower()
            if "reddit" in ch_low:
                reddit_items.append(source_record)
            elif "twitter" in ch_low:
                twitter_items.append(source_record)
            elif "youtube" in ch_low:
                youtube_items.append(source_record)
            else:
                news_items.append(source_record)

        # 4. Chronological Research Timeline
        timeline = []
        dated_sources = [s for s in all_sources if s.get("published_at") and s.get("published_at") != "Recent"]
        for s in dated_sources[:8]:
            timeline.append({
                "time": s["published_at"],
                "source": s["source"],
                "title": s["title"],
                "url": s["url"],
                "role": s["source_role"]
            })
        if not timeline and all_sources:
            for s in all_sources[:5]:
                timeline.append({
                    "time": s.get("published_at") or "Monitored Stream",
                    "source": s["source"],
                    "title": s["title"],
                    "url": s["url"],
                    "role": s["source_role"]
                })

        # 5. Extract Grounded Catalysts, Narratives, Contradictions, & Misinformation Risk
        reasoning = self._synthesize_financial_intelligence(company_name, sym, stock_data, all_sources)

        # 6. Backward compatibility fields
        drop_pct = abs(stock_data.get("drop_percent", 0.0))
        z_score = abs(stock_data.get("z_score", 0.0))
        total_social = len(reddit_items) + len(twitter_items) + len(youtube_items)
        if drop_pct >= 3.0 and total_social >= 4:
            risk_level = "CRITICAL COVERT SHORT ATTACK"
            corr_score = 92
        elif drop_pct >= 1.5 or z_score >= 1.5:
            risk_level = "ELEVATED VOLATILITY DISINFO"
            corr_score = 68
        else:
            risk_level = "NOMINAL (NO ANOMALY)"
            corr_score = 15

        short_attack_correlation = {
            "risk_level": risk_level,
            "correlation_score": corr_score,
            "social_catalyst_volume": total_social,
            "drop_percent": stock_data.get("drop_percent", 0.0),
            "z_score": stock_data.get("z_score", 0.0),
            "is_anomalous": risk_level != "NOMINAL (NO ANOMALY)",
            "recommendation": (
                "Immediate War Room escalation: Coordinated negative narrative volume matches algorithmic sell threshold."
                if risk_level.startswith("CRITICAL")
                else "Continue passive monitoring of cashtag sentiment."
            )
        }

        legacy_company_articles = [
            {
                "title": n["title"],
                "source": n["source"],
                "source_url": n["url"],
                "url": n["url"],
                "category": "Primary Source" if n["source_role"] == "PRIMARY" else "Market Intelligence",
                "summary": n["snippet"][:120],
                "is_threat": "investigation" in n["title"].lower() or "crash" in n["title"].lower() or "fraud" in n["title"].lower(),
                "sentiment": 15,
                "time": n["published_at"],
                "source_role": n["source_role"],
                "source_tier": n["source_tier"]
            }
            for n in news_items
        ]

        total_time_ms = int((datetime.utcnow() - start_t).total_seconds() * 1000)

        session_id = research_telemetry.get("dossier_id") or None
        source_lineage = getattr(research_res, "source_lineage_graph", {}) or {
            "nodes": [],
            "edges": [],
            "metrics": research_telemetry.get("source_lineage", {
                "origin_count": 0,
                "echo_count": 0,
                "syndication_ratio": 0.0,
                "lineage_depth": 0
            })
        }
        replay_url = f"/api/research/replay/dossiers/{session_id}" if session_id else None

        corpus_dict = getattr(research_res, "research_corpus", None) or {}
        funnel = research_telemetry.get("funnel") or corpus_dict.get("funnel") or {
            "queries_planned": len(retrieval_plan.get("query_classes", [])),
            "queries_executed": len(all_sources),
            "candidates_found": len(all_sources),
            "unique_candidates": max(0, len(all_sources) - syndicated_count),
            "deep_reads_count": research_telemetry.get("deep_read_success", 0),
            "primary_sources_count": len(primary_sources),
            "independent_groups_count": research_telemetry.get("independent_source_groups", 0),
            "contradictions_count": len(reasoning.get("contradictions", {}).get("for", [])),
            "findings_count": len(research_findings),
            "saturation_score": research_telemetry.get("saturation", {}).get("cumulative_saturation", 0.0),
            "halt_reason": research_telemetry.get("saturation", {}).get("halt_reason") or "BUDGET_CEILING",
        }

        return {
            "ticker": sym,
            "company_name": company_name,
            "session_id": session_id,
            "replay_url": replay_url,
            "source_lineage": source_lineage,
            "funnel": funnel,
            "candidate_selection_audit": research_telemetry.get("candidate_selection_audit", []) or corpus_dict.get("candidate_selection_audit", []),
            "channel_telemetry": channel_health,
            "research_corpus": corpus_dict,
            "analyzed_at": datetime.utcnow().isoformat(),
            "stock": stock_data,
            "market_state": {
                "observed_price": stock_data.get("current_price", 0.0),
                "volatility_status": stock_data.get("stats", {}).get("volatility_status", "STABLE"),
                "drop_percent": stock_data.get("drop_percent", 0.0),
                "z_score": stock_data.get("z_score", 0.0),
                "data_source": stock_data.get("data_source", "Market Feed")
            },
            "findings": [f.to_dict() if hasattr(f, "to_dict") else f for f in research_findings],
            "evidence_chain": getattr(research_res, "evidence_graph", {}),
            "deep_research_trace": research_telemetry,
            "retrieval": {
                "plan": retrieval_plan,
                "channels": channel_health,
                "latency_ms": total_time_ms,
                "total_sources": len(all_sources),
                "unique_sources": max(0, len(all_sources) - syndicated_count),
                "syndicated_sources": syndicated_count,
                "deep_reads": research_telemetry.get("deep_read_success", 0),
                "trace": retrieval_trace,
            },
            "retrieval_trace": retrieval_trace,
            "sources": all_sources,
            "news": {
                "company": legacy_company_articles,
                "ceo": [],
                "analysis": legacy_company_articles
            },
            "social": {
                "reddit": reddit_items,
                "twitter": twitter_items,
                "youtube": youtube_items,
            },
            "social_intel": {
                "reddit": [r["title"] for r in reddit_items],
                "twitter": [t["title"] for t in twitter_items],
                "youtube": [y["title"] for y in youtube_items],
                "news": [n["title"] for n in news_items]
            },
            "primary_sources": primary_sources,
            "catalysts": reasoning.get("catalysts", {"positive": [], "negative": [], "unresolved": []}),
            "risks": reasoning.get("risks", []),
            "narratives": reasoning.get("narratives", []),
            "contradictions": reasoning.get("contradictions", {"for": [], "against": [], "unresolved": []}),
            "timeline": timeline,
            "misinformation": reasoning.get("misinformation", {
                "status": "NOMINAL",
                "rumors_detected": [],
                "manipulation_risk": "LOW",
                "evidence_quality_score": 0.85
            }),
            "limitations": [
                "Market telemetry reflects delayed daily closing series from Yahoo Finance (free tier), not high-frequency tick streams.",
                "Social channels operate via public feeds without authenticated enterprise firehoses.",
                "All citations reflect retrieved public web records; user verification of primary filings is recommended."
            ],
            "short_attack_correlation": short_attack_correlation,
            "financial_facts": [f.__dict__ for f in scout_result.financial_facts] if scout_result else [],
            "corporate_events": [e.__dict__ for e in scout_result.events] if scout_result else [],
            "story_clusters": [c.__dict__ for c in scout_result.clusters] if scout_result else [],
            "epistemic_status": scout_result.epistemic_status if scout_result else "REPORTED",
            "scout_source_telemetry": scout_result.telemetry if scout_result else {}
        }

    def acquire_market_intelligence(
        self,
        ticker: str,
        query: Optional[str] = None,
        max_candidates: int = 5,
        allow_social: bool = True
    ) -> Dict[str, Any]:
        """
        Direct interface to Scout's proprietary Source Acquisition Engine.
        Returns structured financial facts, corporate events, story clusters,
        contradiction records, and normalized evidence fragments.
        """
        sym, company_name = self.resolve_ticker_and_company(ticker)
        from backend.services.agent_reach.scout import scout_source_engine, ScoutSourceRequest
        req = ScoutSourceRequest(
            query=query or f"{company_name} financial guidance corporate events earnings",
            target_entity=company_name,
            tickers=[sym],
            max_candidates=max_candidates,
            allow_social=allow_social
        )
        res = scout_source_engine.execute(req)

        # Real execution stage: invoke ScoutExtractionEngine
        extracted_intel = scout_extractor.extract_market_intelligence(
            symbol=sym,
            company_name=company_name,
            fragments=[ev.to_evidence_fragment() for ev in res.evidence_items],
            market_telemetry={"ticker": sym}
        )

        return {
            "query": res.query,
            "entity": res.entity,
            "ticker": sym,
            "epistemic_status": res.epistemic_status,
            "primary_source_present": res.primary_source_present,
            "independent_source_count": res.independent_source_count,
            "financial_facts": [f.__dict__ for f in res.financial_facts] or [f.to_dict() for f in extracted_intel.financial_facts],
            "events": [e.__dict__ for e in res.events] or [e.to_dict() for e in extracted_intel.corporate_events],
            "clusters": [c.__dict__ for c in res.clusters],
            "contradictions": [k.__dict__ for k in res.contradictions] or [c.to_dict() for c in extracted_intel.contradictions],
            "evidence_count": len(res.evidence_items),
            "evidence": [ev.to_evidence_fragment().to_dict() for ev in res.evidence_items],
            "telemetry": res.telemetry
        }

    def generate_scout_intelligence(
        self,
        subject: str,
        query: Optional[str] = None,
        max_candidates: int = 5,
        allow_social: bool = True
    ) -> Dict[str, Any]:
        """
        Aegis Protocol Output Contract implementation for Scout Agent.
        Adheres strictly to the specification in backend/Prompts/scout_agent.md (Section 17).
        Partitions reasoning into OBSERVED -> INFERRED -> UNCERTAIN and produces
        structured market intelligence without hallucinating certainty.
        """
        sym, company_name = self.resolve_ticker_and_company(subject)
        acq_intel = self.acquire_market_intelligence(
            ticker=sym,
            query=query,
            max_candidates=max_candidates,
            allow_social=allow_social
        )
        stock_impact = self.check_stock_impact(sym)
        volatility = stock_impact.get("volatility_analysis", {})
        prediction = stock_impact.get("prediction", {})

        # 1. Observed facts
        observed: List[str] = []
        for fact in acq_intel.get("financial_facts", []):
            cur = fact.get("currency", "USD")
            metric = fact.get("metric", "metric")
            raw_val = fact.get("raw_value", "")
            direction = fact.get("direction", "neutral")
            observed.append(f"Reported {metric} of {raw_val} ({cur}, direction: {direction})")
        for ev in acq_intel.get("events", []):
            ev_type = ev.get("event_type", "EVENT")
            summary = ev.get("summary", "")
            observed.append(f"Observed corporate event [{ev_type}]: {summary}")
        if stock_impact.get("current_price"):
            observed.append(
                f"Observed market price for {sym}: ${stock_impact.get('current_price')} "
                f"(volatility status: {volatility.get('volatility_status', 'STABLE')}, z-score: {volatility.get('z_score', 0.0)})"
            )

        # 2. Inferred interpretations
        inferred: List[str] = []
        if acq_intel.get("epistemic_status") == "OFFICIAL":
            inferred.append(f"Official primary documentation confirms company communications for {company_name}.")
        elif acq_intel.get("epistemic_status") == "MULTIPLE_SOURCES":
            inferred.append(f"Multiple independent reporting streams corroborate current narrative for {company_name}.")
        
        vol_stat = volatility.get("volatility_status", "STABLE")
        if vol_stat == "SIGMA_EVENT":
            inferred.append(f"Statistical sigma anomaly detected in price series; high sensitivity to current news catalysts.")
        elif vol_stat == "HIGH_VOLATILITY":
            inferred.append(f"Elevated price variance observed; market is actively pricing in event uncertainty.")
        else:
            inferred.append("Price action is consistent with orderly market trading range.")

        # 3. Uncertain / Unknown
        uncertain: List[str] = []
        if acq_intel.get("epistemic_status") in ("UNCONFIRMED", "REPORTED"):
            uncertain.append("Information remains in REPORTED status without primary regulatory filing confirmation.")
        for contra in acq_intel.get("contradictions", []):
            field_name = contra.get("field", "data point")
            vals = contra.get("values", [])
            uncertain.append(f"Conflicting reporting detected for {field_name}: competing values {vals}.")
        if not acq_intel.get("financial_facts") and not acq_intel.get("events"):
            uncertain.append("Limited public structured filings discovered in current retrieval window.")

        # Market impact calculation
        direction = "neutral"
        if prediction.get("catalyst_direction"):
            direction = prediction.get("catalyst_direction").lower()
        elif volatility.get("z_score", 0.0) > 1.5:
            direction = "bullish"
        elif volatility.get("z_score", 0.0) < -1.5:
            direction = "bearish"
        
        confidence = 0.85 if acq_intel.get("primary_source_present") else (0.70 if acq_intel.get("independent_source_count", 0) > 1 else 0.50)
        if acq_intel.get("contradictions"):
            confidence = max(0.30, confidence - 0.25)

        # Risk flags
        risk_flags: List[str] = []
        if acq_intel.get("contradictions"):
            risk_flags.append("UNRESOLVED_SOURCE_CONTRADICTIONS")
        if vol_stat in ("SIGMA_EVENT", "HIGH_VOLATILITY"):
            risk_flags.append(f"PRICE_VOLATILITY_{vol_stat}")
        if acq_intel.get("epistemic_status") == "UNCONFIRMED":
            risk_flags.append("UNVERIFIED_RUMOR_STATUS")

        # Determine retrieval directness & fallback
        telemetry = acq_intel.get("telemetry", {})
        fallback_used = telemetry.get("fallback_rate", 0.0) > 0.0
        fallback_reason = "SEARCH_INDEX_FALLBACK" if fallback_used else None

        return {
            "agent": "scout",
            "subject": sym,
            "market_context": f"Asset: {company_name} ({sym}) | Primary source present: {acq_intel.get('primary_source_present')} | Epistemic status: {acq_intel.get('epistemic_status')}",
            "observed": observed,
            "inferred": inferred,
            "uncertain": uncertain,
            "events": acq_intel.get("events", []),
            "sources": acq_intel.get("evidence", []),
            "corroboration": acq_intel.get("clusters", []),
            "contradictions": acq_intel.get("contradictions", []),
            "price_context": volatility,
            "market_impact": {
                "direction": direction if direction in ("bullish", "bearish", "mixed", "neutral", "unknown") else "neutral",
                "horizon": "days",
                "confidence": round(confidence, 2)
            },
            "risk_flags": risk_flags,
            "retrieval": {
                "direct": not fallback_used,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason
            }
        }

    # Backward-compatible alias
    generate_intelligence = generate_scout_intelligence


# Canonical singleton instance
scout_agent = ScoutAgent()


def process_scout_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """External interface for processing Scout tasks."""
    return scout_agent.process_task(task)


__all__ = [
    "ScoutAgent",
    "scout_agent",
    "process_scout_task",
]
