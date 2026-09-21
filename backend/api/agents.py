"""
Aegis Protocol — Specialized Agents & War Room API Router
=========================================================
Endpoints for:
- Scout Agent (Financial Threat Intelligence & Stock Telemetry)
- BrandShield Agent (Counterfeits, Fake Reviews & Brand Defamation)
- Personal Watch Agent (VIP Reputation, Deepfakes & Impersonation)
- Trending Agent (Narrative Velocity, RSS Streams & Crisis PR)
- War Room (Live Threat Signals & Incident Response Countermeasures)
"""

import logging
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.db import database as db
from backend.agents.trending_agent import TrendingAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy-loaded agent getters
_scout_agent = None
_trending_agent = None
_brandshield_agent = None
_personal_agent = None


def get_scout_agent():
    global _scout_agent
    if _scout_agent is None:
        from backend.agents.scout_agent import ScoutAgent
        _scout_agent = ScoutAgent()
    return _scout_agent


def get_trending_agent():
    global _trending_agent
    if _trending_agent is None:
        _trending_agent = TrendingAgent()
    return _trending_agent


def get_brandshield_agent():
    global _brandshield_agent
    if _brandshield_agent is None:
        from backend.agents.brandshield_agent import BrandShieldAgent
        _brandshield_agent = BrandShieldAgent()
    return _brandshield_agent


def get_personal_agent():
    global _personal_agent
    if _personal_agent is None:
        from backend.agents.personal_agent import PersonalWatchAgent
        _personal_agent = PersonalWatchAgent()
    return _personal_agent


# ── Request Models ───────────────────────────────────────────────────────────

class ScoutAnalyzeRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol (e.g. 'NVDA', 'TATAMOTORS.NS')", json_schema_extra={"example": "NVDA"})
    query: Optional[str] = Field(None, description="Optional search query override.", json_schema_extra={"example": "Nvidia Blackwell AI chip delay packaging defect"})


class BrandShieldScanRequest(BaseModel):
    brand_name: str = Field(..., description="Brand, company, or trademark name.", json_schema_extra={"example": "Sony Electronics"})


class PersonalScanRequest(BaseModel):
    name: str = Field(..., description="Full name of VIP, executive, or public figure.", json_schema_extra={"example": "Sam Altman"})
    official_handles: Optional[Dict[str, str]] = Field(None, description="Official social media handles.", json_schema_extra={"example": {"twitter": "@sama"}})
    phone_number: Optional[str] = Field(None, description="Optional phone number for breach alerts.")


class TrendingScanRequest(BaseModel):
    asset_name: Optional[str] = Field(None, description="Company, asset, or entity name.")
    query: Optional[str] = Field(None, description="Alternative field for search query.")
    identifiers: Optional[List[str]] = Field(None, description="Keywords, cashtags, or tickers.")


class DefenseRequest(BaseModel):
    rumor_text: str = Field(..., description="Misinformation or smear claim text.", json_schema_extra={"example": "Secret leaked audit confirms company is declaring bankruptcy next week."})


class DeployResponseRequest(BaseModel):
    event_id: int = Field(..., description="ID of verified threat event.")
    response_type: str = Field(..., description="'cease_desist' | 'official_denial' | 'ceo_alert' | 'sec_filing'", json_schema_extra={"example": "official_denial"})


STOCK_NAME_MAP = {
    'NVIDIA': 'NVDA', 'APPLE': 'AAPL', 'TESLA': 'TSLA', 'MICROSOFT': 'MSFT',
    'GOOGLE': 'GOOGL', 'ALPHABET': 'GOOGL', 'AMAZON': 'AMZN', 'META': 'META',
    'FACEBOOK': 'META', 'NETFLIX': 'NFLX', 'TATA MOTORS': 'TATAMOTORS.NS',
    'TATAMOTORS': 'TATAMOTORS.NS', 'RELIANCE': 'RELIANCE.NS', 'INFOSYS': 'INFY.NS',
    'TCS': 'TCS.NS', 'HDFC': 'HDFCBANK.NS', 'HDFCBANK': 'HDFCBANK.NS',
    'WIPRO': 'WIPRO.NS', 'ICICI': 'ICICIBANK.NS', 'SBI': 'SBIN.NS', 'ADANI': 'ADANIENT.NS',
}


# ── Stock Telemetry & Scout Agent ────────────────────────────────────────────

@router.get("/api/stock", tags=["Scout Agent (Financial Intelligence)"], summary="Real-Time Stock Price & Volatility Z-Score")
@router.get("/.netlify/functions/stock", tags=["Scout Agent (Financial Intelligence)"])
async def get_stock_quote(ticker: str = "NVDA"):
    """Fetch live stock price and volatility metrics server-side."""
    clean_sym = ticker.strip().upper()
    sym = STOCK_NAME_MAP.get(clean_sym, clean_sym)
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            result = data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                quote = result[0].get("indicators", {}).get("quote", [{}])[0]
                closes = [p for p in quote.get("close", []) if p is not None]
                curr = meta.get("regularMarketPrice") or (closes[-1] if closes else 0.0)
                prev = meta.get("chartPreviousClose") or (closes[-2] if len(closes) >= 2 else curr)
                drop = (((curr - prev) / prev) * 100) if prev and prev > 0 else 0.0
                z_score = 0.0
                if len(closes) >= 3:
                    avg = sum(closes) / len(closes)
                    variance = sum((x - avg) ** 2 for x in closes) / len(closes)
                    std_dev = variance ** 0.5
                    if std_dev > 0:
                        z_score = (curr - avg) / std_dev
                is_crashing = (drop <= -3.0) or (z_score <= -2.0)
                return {
                    "ticker": meta.get("symbol", sym),
                    "name": meta.get("longName") or meta.get("shortName") or sym,
                    "current_price": round(float(curr), 2),
                    "prev_close": round(float(prev), 2),
                    "drop_percent": round(float(drop), 2),
                    "z_score": round(float(z_score), 2),
                    "currency": meta.get("currency") or ("INR" if sym.endswith(".NS") or sym.endswith(".BO") else "USD"),
                    "is_crashing": is_crashing
                }
    except Exception as e:
        logger.warning(f"[Stock] Quote fetch failed for {sym}: {e}")

    is_inr = sym.endswith(".NS") or sym.endswith(".BO")
    return {
        "ticker": sym,
        "name": sym,
        "current_price": 0.0,
        "prev_close": 0.0,
        "drop_percent": 0.0,
        "z_score": 0.0,
        "currency": "INR" if is_inr else "USD",
        "is_crashing": False,
        "status": "Telemetry Standby"
    }


@router.post("/api/scout/analyze", tags=["Scout Agent (Financial Intelligence)"], summary="Stock Volatility & Coordinated Short Attack Analysis")
@router.post("/scout/analyze", tags=["Scout Agent (Financial Intelligence)"])
async def analyze_stock_live(request: ScoutAnalyzeRequest):
    """
    Analyze a stock ticker with real-time price metrics, multi-platform social catalysts,
    news sentiment, and automated coordinated short-attack correlation.
    """
    logger.info(f"[API] POST /api/scout/analyze - ticker={request.ticker}")
    try:
        scout = get_scout_agent()
        trending = get_trending_agent()

        stock_data = scout.check_stock_impact(request.ticker)
        if not stock_data or not stock_data.get("current_price"):
            quote_data = await get_stock_quote(request.ticker)
            if quote_data and quote_data.get("current_price", 0) > 0:
                stock_data = quote_data

        if not stock_data or not stock_data.get("current_price"):
            stock_data = {
                "ticker": request.ticker,
                "current_price": 0.0,
                "drop_percent": 0.0,
                "z_score": 0.0,
                "is_crashing": False,
                "status": "Telemetry Active"
            }

        company_name = request.ticker.replace('.NS', '').replace('.BO', '')

        # News Articles
        raw_news = trending.fetch_news(company_name, limit=5)
        company_articles = []
        analysis_queue = []
        for article in (raw_news or []):
            t = article.get('title', 'No title')
            src = article.get('source') or 'Google News'
            analysis_queue.append(t)
            company_articles.append({
                'title': t,
                'source': src,
                'category': 'Market Analysis' if 'stock' in t.lower() else 'Company News',
                'summary': f"Reported via {src}: {t[:110]}",
                'is_threat': False,
                'sentiment': 15,
                'time': article.get('published', 'Recent')
            })

        if analysis_queue:
            try:
                from backend.services.intelligence import analyze_sentiment
                sent_results = analyze_sentiment(analysis_queue)
                for idx, res in enumerate(sent_results):
                    if idx < len(company_articles):
                        s_score = res.get("sentiment_score") if res.get("sentiment_score") is not None else res.get("score", 0)
                        lbl = res.get("label", "neutral")
                        is_t = res.get("is_threat", False) or (s_score < -25) or (lbl.lower() in ["negative", "toxic", "threat"])
                        company_articles[idx]["sentiment"] = int(s_score * 100) if abs(s_score) <= 1 else int(s_score)
                        company_articles[idx]["is_threat"] = is_t
                        if is_t:
                            company_articles[idx]["summary"] = f"Volatility alert: {company_articles[idx]['summary']}"
            except Exception as e_sent:
                logger.debug(f"[ScoutAnalyze] Sentiment analysis notice: {e_sent}")

        # Social Chatter via AgentReach
        try:
            from backend.services.agent_reach import agent_reach_service
            query_q = request.query or request.ticker
            social_intel = agent_reach_service.omni_scan(
                query=query_q,
                domain="financial",
                limit_per_channel=3
            )
        except Exception as e_reach:
            logger.debug(f"[ScoutAnalyze] Social intel notice: {e_reach}")
            social_intel = {"channels": {"reddit": [], "twitter": [], "youtube": [], "news": []}}

        channels = social_intel.get("channels", {})
        reddit_catalysts = len(channels.get("reddit", []))
        twitter_catalysts = len(channels.get("twitter", []))
        youtube_catalysts = len(channels.get("youtube", []))
        total_social_catalysts = reddit_catalysts + twitter_catalysts + youtube_catalysts

        drop_pct = abs(stock_data.get("drop_percent", 0.0))
        z_score = abs(stock_data.get("z_score", 0.0))

        if drop_pct >= 3.0 and total_social_catalysts >= 4:
            short_attack_risk = "CRITICAL COVERT SHORT ATTACK"
            correlation_score = 92
        elif drop_pct >= 1.5 or z_score >= 1.5:
            short_attack_risk = "ELEVATED VOLATILITY DISINFO"
            correlation_score = 68
        else:
            short_attack_risk = "NOMINAL (NO ANOMALY)"
            correlation_score = 15

        short_attack_correlation = {
            "risk_level": short_attack_risk,
            "correlation_score": correlation_score,
            "social_catalyst_volume": total_social_catalysts,
            "drop_percent": stock_data.get("drop_percent", 0.0),
            "z_score": stock_data.get("z_score", 0.0),
            "is_anomalous": short_attack_risk != "NOMINAL (NO ANOMALY)",
            "recommendation": (
                "Immediate War Room escalation: Coordinated negative narrative volume matches algorithmic sell threshold."
                if short_attack_risk.startswith("CRITICAL")
                else "Continue passive monitoring of cashtag sentiment."
            )
        }

        return {
            "stock": stock_data,
            "news": {"company": company_articles, "ceo": [], "analysis": company_articles},
            "social_intel": social_intel.get("channels", {}),
            "short_attack_correlation": short_attack_correlation,
            "ticker": request.ticker,
            "analyzed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"[API] Error in scout analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ── Trending Agent ───────────────────────────────────────────────────────────

@router.post("/api/trending/scan", tags=["Trending & Contagion Agent"], summary="Viral Narrative Velocity & Critical Alerts")
async def trending_scan(request: TrendingScanRequest):
    """Trigger the Trending Agent ingestion pass for an asset/celebrity."""
    target_name = request.asset_name or request.query or "General"
    logger.info(f"[API] POST /api/trending/scan - asset={target_name}")
    try:
        agent = get_trending_agent()
        result = agent.scan(target_name, request.identifiers)
        from backend.services.alerts import check_critical_threats
        result["alerts"] = check_critical_threats(result)
        return result
    except Exception as e:
        logger.error(f"[API] Trending scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trending scan failed: {str(e)}")


@router.post("/api/defense/generate", tags=["Trending & Contagion Agent"], summary="Generate Rapid Crisis PR Defense Statement")
async def generate_defense_endpoint(request: DefenseRequest):
    """Generate a PR defense statement using Gemini."""
    logger.info("[API] POST /api/defense/generate")
    try:
        from backend.services.intelligence import generate_defense
        statement = generate_defense(request.rumor_text)
        return {"defense_statement": statement}
    except Exception as e:
        logger.error(f"[API] Defense generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Defense generation failed: {str(e)}")


@router.get("/api/trending-news", tags=["Trending & Contagion Agent"], summary="Real-Time Market Moving Google News Feeds")
async def get_trending_news():
    """Fetch live trending stock market news from Google News RSS."""
    logger.info("[API] GET /api/trending-news")
    try:
        trending = TrendingAgent()
        search_queries = [
            "Indian stock market", "Reliance Industries", "Tata Motors", "Infosys",
            "US stock market", "Apple", "Tesla", "Microsoft"
        ]
        all_articles = []
        for query in search_queries:
            articles = trending.fetch_targeted_news(query, window_mins=1440)
            all_articles.extend(articles)

        unique_articles = {a['title']: a for a in all_articles}.values()
        sorted_articles = sorted(unique_articles, key=lambda x: x.get('published', ''), reverse=True)[:4]

        news_items = [{
            'title': a.get('title', 'No title'),
            'link': a.get('link', '#'),
            'time': a.get('age_minutes', 0),
            'source': 'Market News'
        } for a in sorted_articles]

        return {"items": news_items, "count": len(news_items)}
    except Exception as e:
        logger.error(f"[API] Error fetching trending news: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch trending news: {str(e)}")


# ── Personal Watch Agent ─────────────────────────────────────────────────────

@router.post("/api/personal/scan", tags=["Personal Watch Agent (VIP Protection)"], summary="VIP Reputation, Deepfake & Impersonation Scan")
@router.post("/api/personal-watch/scan", tags=["Personal Watch Agent (VIP Protection)"])
async def personal_watch_scan(request: PersonalScanRequest):
    """Run a Personal Watch scan for a public figure or individual."""
    logger.info(f"[API] POST /api/personal/scan - VIP: {request.name}")
    try:
        from backend.agents.personal_agent import process_personal_watch
        vip_profile = {
            "name": request.name,
            "official_handles": request.official_handles or {},
            "phone_number": request.phone_number
        }
        results = process_personal_watch(vip_profile)
        return results
    except Exception as e:
        logger.error(f"[API] Personal Watch scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


# ── BrandShield Agent ────────────────────────────────────────────────────────

@router.post("/api/brandshield/scan", tags=["BrandShield Agent (Brand Defense)"], summary="Counterfeit, Fake Review & Brand Defamation Scan")
async def brandshield_scan(request: BrandShieldScanRequest):
    """Run a BrandShield scan for a brand or product across reviews and forums."""
    logger.info(f"[API] POST /api/brandshield/scan - brand={request.brand_name}")
    try:
        agent = get_brandshield_agent()
        results = agent.scan(request.brand_name)
        return results
    except Exception as e:
        logger.error(f"[API] BrandShield scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"BrandShield scan failed: {str(e)}")


# ── War Room & Incident Response ─────────────────────────────────────────────

@router.get("/api/war-room/signals", tags=["War Room & Incident Response"], summary="Get Live Detected Market Threat Signals")
@router.get("/war-room/signals", tags=["War Room & Incident Response"])
async def get_war_room_signals(limit: int = 20):
    """Get recent active signals detected by the Scout Agent."""
    try:
        if db.supabase:
            response = db.supabase.table("active_signals") \
                .select("*").order("timestamp", desc=True).limit(limit).execute()
            signals = response.data if response.data else []
            return {"signals": signals, "count": len(signals)}
        return {"signals": [], "count": 0}
    except Exception as e:
        logger.warning(f"[API] Signal table fetch note: {str(e)}")
        return {"signals": [], "count": 0, "status": "standby"}


@router.get("/api/feed/live", tags=["War Room & Incident Response"], summary="Get Verified Crisis Threats Feed")
@router.get("/feed/live", tags=["War Room & Incident Response"])
async def get_live_feed(limit: int = 10):
    """Get recent verified threats (correlated misinformation + stock crashes)."""
    try:
        if db.supabase:
            response = db.supabase.table("verified_threats") \
                .select("*").order("created_at", desc=True).limit(limit).execute()
            threats = response.data if response.data else []
            return {"threats": threats, "count": len(threats)}
        return {"threats": [], "count": 0}
    except Exception as e:
        logger.warning(f"[API] Verified threats table note: {str(e)}")
        return {"threats": [], "count": 0, "status": "standby"}


@router.post("/api/deploy-response", tags=["War Room & Incident Response"], summary="Deploy Crisis Countermeasure")
@router.post("/deploy-response", tags=["War Room & Incident Response"])
async def deploy_response(request: DeployResponseRequest):
    """Deploy a crisis response measure for a verified threat."""
    logger.info(f"[API] POST /deploy-response - event_id={request.event_id}, type={request.response_type}")
    try:
        if not db.supabase:
            raise HTTPException(status_code=503, detail="Database not configured")

        event_response = db.supabase.table("verified_threats").select("*").eq("id", request.event_id).execute()
        if not event_response.data:
            raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")

        event = event_response.data[0]
        ticker = event.get("ticker")

        scout = get_scout_agent()
        stock_data = scout.check_stock_impact(ticker)
        current_price = stock_data.get("current_price", 0.0)

        measure_payload = {
            "event_id": request.event_id,
            "measure_type": request.response_type,
            "current_stock_price": current_price,
            "stock_price_at_deployment": event.get("current_price"),
            "metadata": {"ticker": ticker, "deployed_via": "api"}
        }
        insert_response = db.supabase.table("deployed_measures").insert(measure_payload).execute()
        db.supabase.table("verified_threats").update({"response_deployed": True}).eq("id", request.event_id).execute()

        return {
            "status": "success",
            "event_id": request.event_id,
            "response_type": request.response_type,
            "current_stock_price": current_price,
            "measure_id": insert_response.data[0]["id"] if insert_response.data else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error deploying response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deploying response: {str(e)}")
