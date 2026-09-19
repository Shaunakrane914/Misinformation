"""
Live Diagnostic Test of All 5 Aegis Agents
==========================================
Executes each agent with a realistic prompt, evaluates:
1. Execution status (Success / Fail)
2. Scraper channels utilized (Reddit, Twitter, YouTube, News, Jina)
3. Output structure & schema
4. Content quality & analytical usefulness
"""

import sys
import os
import json
import time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_path = os.path.join(project_root, "backend")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_path, ".env"))

def print_separator(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_all():
    summary_report = {}

    # 1. SCOUT AGENT
    print_separator("1. TESTING SCOUT AGENT (Financial Threat & Short Attack)")
    try:
        from agents.scout_agent import ScoutAgent
        scout = ScoutAgent()
        t0 = time.time()
        ticker = "TSLA"
        res_scout = scout.check_stock_impact(ticker)
        dur_scout = round(time.time() - t0, 2)
        
        social_intel = res_scout.get("social_intel", {})
        short_attack = res_scout.get("short_attack_correlation", False)
        
        print(f"Status: PASS (Completed in {dur_scout}s)")
        print(f"Ticker: {ticker} | Price: ${res_scout.get('current_price')} | Volatility Z-Score: {res_scout.get('z_score')}")
        print(f"Is Crashing: {res_scout.get('is_crashing')} | Short Attack Correlated: {short_attack}")
        print(f"Short Seller Risk: {social_intel.get('short_seller_risk')}")
        print(f"Reddit Discussions: {len(social_intel.get('reddit_discussions', []))}")
        print(f"Twitter Cashtags: {len(social_intel.get('twitter_cashtags', []))}")
        print(f"YouTube Analyses: {len(social_intel.get('youtube_analyses', []))}")
        print(f"News Catalysts: {len(social_intel.get('news_catalysts', []))}")
        print(f"Total Social Signals: {social_intel.get('social_signals_detected', 0)}")
        print(f"Top Output Keys: {list(res_scout.keys())}")
        
        summary_report["ScoutAgent"] = {
            "status": "PASS",
            "duration_s": dur_scout,
            "keys": list(res_scout.keys()),
            "ticker": ticker,
            "price": res_scout.get("current_price"),
            "z_score": res_scout.get("z_score"),
            "short_seller_risk": social_intel.get("short_seller_risk"),
            "signals_detected": social_intel.get("social_signals_detected", 0),
            "channels_detected": {
                "reddit": len(social_intel.get("reddit_discussions", [])),
                "twitter": len(social_intel.get("twitter_cashtags", [])),
                "youtube": len(social_intel.get("youtube_analyses", [])),
                "news": len(social_intel.get("news_catalysts", []))
            }
        }
    except Exception as e:
        print(f"Status: FAIL - {e}")
        import traceback
        traceback.print_exc()
        summary_report["ScoutAgent"] = {"status": "FAIL", "error": str(e)}

    # 2. RESEARCH AGENT
    print_separator("2. TESTING RESEARCH AGENT (Epistemic Fact-Check & Verification)")
    try:
        from agents.research_agent import ResearchAgent
        research = ResearchAgent()
        t0 = time.time()
        claim = "The Eiffel Tower was permanently dismantled and moved to Tokyo in 2024"
        res_research = research.process(claim)
        dur_research = round(time.time() - t0, 2)
        
        sup = res_research.get("supporting_evidence", [])
        ref = res_research.get("refuting_evidence", [])
        conf = res_research.get("overall_evidence_confidence", 0.0)
        
        print(f"Status: PASS (Completed in {dur_research}s)")
        print(f"Overall Evidence Confidence (True Probability): {conf}")
        print(f"Supporting Points: {len(sup)}")
        for s in sup[:2]:
            print(f"  [+] {s[:100]}...")
        print(f"Refuting Points: {len(ref)}")
        for r in ref[:2]:
            print(f"  [-] {r[:100]}...")
        print(f"Top Output Keys: {list(res_research.keys())}")
        
        summary_report["ResearchAgent"] = {
            "status": "PASS",
            "duration_s": dur_research,
            "keys": list(res_research.keys()),
            "supporting_count": len(sup),
            "refuting_count": len(ref),
            "overall_confidence": conf,
            "sample_refutation": ref[0] if ref else "None"
        }
    except Exception as e:
        print(f"Status: FAIL - {e}")
        import traceback
        traceback.print_exc()
        summary_report["ResearchAgent"] = {"status": "FAIL", "error": str(e)}

    # 3. BRANDSHIELD AGENT
    print_separator("3. TESTING BRANDSHIELD AGENT (Brand Protection & Sybil Review Rings)")
    try:
        from agents.brandshield_agent import BrandShieldAgent
        brandshield = BrandShieldAgent()
        t0 = time.time()
        brand = "Nike"
        res_brand = brandshield.scan(brand)
        dur_brand = round(time.time() - t0, 2)
        
        findings = res_brand.get("findings", [])
        sources = set(m.get("platform") for m in res_brand.get("mentions", [])) if "mentions" in res_brand else set()
        
        print(f"Status: PASS (Completed in {dur_brand}s)")
        print(f"Brand: {res_brand.get('brand_name', brand)} | Findings: {res_brand.get('total_findings')} | Threat Count: {res_brand.get('threat_count')} | Safe: {res_brand.get('safe_count')}")
        print(f"Platforms Covered: {res_brand.get('platforms', [])}")
        if findings:
            for f in findings[:3]:
                print(f"  [{f.get('threat_type', 'General')}] (Sev: {f.get('severity')}) {f.get('title')}: {f.get('description', '')[:90]}...")
        print(f"Top Output Keys: {list(res_brand.keys())}")
        
        summary_report["BrandShieldAgent"] = {
            "status": "PASS",
            "duration_s": dur_brand,
            "keys": list(res_brand.keys()),
            "total_findings": res_brand.get("total_findings"),
            "threat_count": res_brand.get("threat_count"),
            "safe_count": res_brand.get("safe_count"),
            "platforms": res_brand.get("platforms", []),
            "sample_finding": findings[0] if findings else {}
        }
    except Exception as e:
        print(f"Status: FAIL - {e}")
        import traceback
        traceback.print_exc()
        summary_report["BrandShieldAgent"] = {"status": "FAIL", "error": str(e)}

    # 4. PERSONAL AGENT
    print_separator("4. TESTING PERSONAL AGENT (VIP Protection, Deepfake & Defamation)")
    try:
        from agents.personal_agent import PersonalWatchAgent
        personal = PersonalWatchAgent()
        t0 = time.time()
        vip_profile = {
            "name": "Sam Altman",
            "official_handles": {"twitter": "@sama"}
        }
        res_personal = personal.scan(vip_profile)
        dur_personal = round(time.time() - t0, 2)
        
        sources_p = set(m.get("source") for m in res_personal.get("mentions", []))
        alerts = res_personal.get("alerts", [])
        
        print(f"Status: PASS (Completed in {dur_personal}s)")
        print(f"VIP: {vip_profile['name']} | Threat Level: {res_personal.get('threat_level')} | Threat Score: {res_personal.get('threat_score')}/100")
        print(f"Total Mentions Analyzed: {res_personal.get('total_mentions')} | Active Alerts: {len(alerts)}")
        print(f"Platform Sources Gathered: {sources_p}")
        if alerts:
            for a in alerts[:2]:
                print(f"  [ALERT - {a.get('type')}] (Sev: {a.get('severity')}): {a.get('title')}")
        print(f"Top Output Keys: {list(res_personal.keys())}")
        
        summary_report["PersonalAgent"] = {
            "status": "PASS",
            "duration_s": dur_personal,
            "keys": list(res_personal.keys()),
            "threat_level": res_personal.get("threat_level"),
            "threat_score": res_personal.get("threat_score"),
            "total_mentions": res_personal.get("total_mentions"),
            "sources": list(sources_p),
            "alerts_count": len(alerts)
        }
    except Exception as e:
        print(f"Status: FAIL - {e}")
        import traceback
        traceback.print_exc()
        summary_report["PersonalAgent"] = {"status": "FAIL", "error": str(e)}

    # 5. TRENDING AGENT
    print_separator("5. TESTING TRENDING AGENT (Narrative Virality & Contagion Velocity)")
    try:
        from agents.trending_agent import TrendingAgent
        trending = TrendingAgent()
        t0 = time.time()
        topic = "DeepSeek"
        res_trending = trending.scan(topic)
        dur_trending = round(time.time() - t0, 2)
        
        feed = res_trending.get("feed", [])
        sources_t = res_trending.get("sources", [])
        counts = res_trending.get("counts", {})
        
        print(f"Status: PASS (Completed in {dur_trending}s)")
        print(f"Topic: {topic} | Feed Items: {len(feed)} | Threats: {len(res_trending.get('threats', []))}")
        print(f"Sources: {sources_t} | Counts: {counts}")
        if feed:
            for f in feed[:3]:
                print(f"  [{f.get('source')}] (Sent: {f.get('sentiment')}, Threat: {f.get('is_threat')}): {f.get('title')[:80]}")
        print(f"Top Output Keys: {list(res_trending.keys())}")
        
        summary_report["TrendingAgent"] = {
            "status": "PASS",
            "duration_s": dur_trending,
            "keys": list(res_trending.keys()),
            "feed_items_count": len(feed),
            "threats_count": len(res_trending.get("threats", [])),
            "sources": sources_t,
            "counts": counts
        }
    except Exception as e:
        print(f"Status: FAIL - {e}")
        import traceback
        traceback.print_exc()
        summary_report["TrendingAgent"] = {"status": "FAIL", "error": str(e)}

    report_path = os.path.join(os.path.dirname(__file__), "agent_test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)
    print(f"\nSaved complete audit to: {report_path}")

if __name__ == "__main__":
    test_all()
