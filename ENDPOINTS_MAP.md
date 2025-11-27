# Aegis Enterprise - Complete Endpoint Map

## 🌐 Server: http://127.0.0.1:8000

---

## Frontend Routes

### Main Pages
- `GET /` → Home page (index.html)
- `GET /dashboard` → Live dashboard with claims feed
- `GET /about` → About page with agent explanations
- `GET /submit` → Submit claim form
- `GET /agents` → **NEW** Agent overview with 4 cards

### Agent Pages
- `GET /scout-agent` → **NEW** Scout Agent (Financial Watchdog) - LIVE
- `GET /trending-agent` → **NEW** Trending Agent (Content Intelligence) - LIVE
- `GET /brandshield-agent` → **NEW** BrandShield Agent - Coming Soon
- `GET /personal-watch-agent` → **NEW** Personal Watch Agent - Coming Soon

### Static Assets
- `GET /dashboard.css` → Dashboard styles
- `GET /dashboard.js` → Dashboard JavaScript
- `GET /static/*` → All other frontend files

---

## Backend API Routes (Prefix: /api)

### Health & Info
- `GET /api/` → API information and endpoints list
- `GET /api/healthz` → Health check

### Claims Management
- `POST /api/claims/submit` → Submit new claim for fact-checking
- `GET /api/claims/{claim_id}` → Get claim status and results
- `GET /api/claims` → List all claims (with pagination)

### Dashboard
- `GET /api/dashboard/claims` → Get 15 random claims for dashboard
- `GET /api/dashboard/debug` → Debug info for dashboard
- `POST /api/explain-claim` → Generate AI explanation for claim

### War Room (Aegis Enterprise)
- `GET /api/war-room/signals` → Get recent crash signals (active_signals table)
- `GET /api/feed/live` → Get verified threats (verified_threats table)
- `POST /api/deploy-response` → Deploy crisis response measure

---

## Database Tables (Supabase)

### Misinformation Detection
- `claims` - Submitted claims with verdicts
- `evidence` - Supporting evidence for claims

### War Room (Aegis)
- `active_signals` - Scout Agent crash detections
- `verified_threats` - Correlated misinformation + crashes
- `deployed_measures` - Crisis responses deployed

---

## Featured Pages

### 🎯 Scout Agent Page (`/scout-agent`)
**5 Agentic Features:**
1. 📉 Predictive Impact Modeling - Monte Carlo simulation
2. 🔍 Autonomous Investigator Swarm - Multi-agent debate
3. ⚡ Network Neutralization - Bot graph mapping
4. 🛠️ Strategic Response Orchestrator - Multi-modal countermeasures
5. 🚨 Self-Healing Feedback Loop - Outcome learning

### 🤖 Agents Overview (`/agents`)
**4 Agent Cards:**
1. Scout Agent - Financial misinformation detection
2. Trending Agent - Viral content analysis
3. BrandShield Agent - Product protection (coming soon)
4. Personal Watch Agent - Individual monitoring (coming soon)

---

## Testing Endpoints

```bash
# Health check
curl http://127.0.0.1:8000/api/healthz

# Dashboard claims
curl http://127.0.0.1:8000/api/dashboard/claims

# War Room signals
curl http://127.0.0.1:8000/api/war-room/signals

# Live threat feed
curl http://127.0.0.1:8000/api/feed/live

# Submit claim
curl -X POST http://127.0.0.1:8000/api/claims/submit \
  -H "Content-Type: application/json" \
  -d '{"claim_text": "Test claim", "source_url": "https://example.com"}'
```

---

## Environment Variables Required

```env
# Gemini AI
GEMINI_API_KEY_1=your_key
GEMINI_API_KEY_2=your_key
GEMINI_API_KEY=your_key

# Yahoo Finance
YF_API_KEY=your_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_key
```

---

## Quick Start

```bash
# 1. Start server
python main.py

# 2. Open in browser
http://127.0.0.1:8000

# 3. Navigate to:
- Home: http://127.0.0.1:8000/
- Agents: http://127.0.0.1:8000/agents
- Scout Agent: http://127.0.0.1:8000/scout-agent
- Dashboard: http://127.0.0.1:8000/dashboard
```

---

## Status Summary

✅ **Working:**
- All frontend pages
- Scout Agent full demo
- Agents overview page
- Dashboard with claims
- API health endpoints

⚠️ **Needs Database Setup:**
- War Room tables (run setup_aegis_db.sql in Supabase)
- Then: `/api/war-room/signals` and `/api/feed/live` will work

🚀 **Ready for Hackathon Demo:**
- Scout Agent page is fully featured
- 4-agent strategy is clear
- All routes connected
