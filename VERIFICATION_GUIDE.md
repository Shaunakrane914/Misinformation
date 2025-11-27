# Aegis Enterprise - Verification Guide

## Complete 5-Phase Verification Procedure

This guide provides step-by-step verification for all phases of the Aegis Enterprise War Room system.

---

## Phase 1 & 2: Agent Verification

### Test: verify_agents.py

**What it tests:**
- Phase 1: Scout Agent (YH Finance API, crash detection)
- Phase 2: Trending Agent (Google News RSS, Gemini AI)

**Run:**
```bash
python verify_agents.py
```

**Expected Output:**
```
✅ Scout Agent functional
   Current Price: ₹945.50
   Drop Percent: -2.5%
   Is Crashing: True

✅ Trending Agent functional
   Articles Analyzed: 5
   Panic Score: 75/100
   Smoking Gun Found: True
```

---

## Phase 3: Coordinator Verification (Force Crash Test)

### Test: Simulation Mode

**What it tests:**
- Coordinator pipeline (Scout → Trending → Correlate → Respond)
- Database insertion for verified threats

**Setup:**
1. Create an empty file named `FORCE_CRASH_TEST` in project root:
   ```bash
   New-Item -Name "FORCE_CRASH_TEST" -ItemType File
   ```

2. Ensure server is running:
   ```bash
   python main.py
   ```

**Expected Logs:**
```
🧪 FORCE CRASH TEST MODE ACTIVATED!
🚨 SIGMA EVENT DETECTED!
🔎 STEP 2: CONTENT INTELLIGENCE HUNT
🔗 STEP 3: CAUSALITY CORRELATION
🎯 SMOKING GUN IDENTIFIED!
🤖 STEP 4: AUTONOMOUS RESPONSE GENERATION
💾 STEP 5: ARCHIVING VERIFIED THREAT
✅ HIGH CONFIDENCE CORRELATION!
```

**Cleanup:**
```bash
Remove-Item "FORCE_CRASH_TEST"
```

---

## Phase 4: Database & API Verification

### Test 1: Database Connectivity

```bash
python debug_db.py
```

**Expected Output:**
```
✅ Supabase client initialized
✅ Table 'active_signals' accessible
✅ Table 'verified_threats' accessible  
✅ Table 'deployed_measures' accessible
```

### Test 2: War Room Signals API

```powershell
curl http://127.0.0.1:8000/api/war-room/signals
```

**Expected:** JSON with recent crash signals

### Test 3: Live Feed API

```powershell
curl http://127.0.0.1:8000/api/feed/live
```

**Expected:** JSON with verified threats

---

## Phase 5: Response Deployment Verification

### Test: Deploy Crisis Response

**Prerequisites:** Ensure at least one verified threat exists (run Phase 3 test)

```powershell
$body = @{
    event_id = 1
    response_type = "cease_desist"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/deploy-response" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

**Expected Response:**
```json
{
  "status": "success",
  "event_id": 1,
  "response_type": "cease_desist",
  "current_stock_price": 945.50
}
```

**Expected Logs (within 5 minutes):**
```
[Coordinator] Running Impact Analysis...
Battle #1 (cease_desist): Recovery +0.5% -> SUCCESS
```

---

## Verification Checklist

| Phase | Test | Status |
|-------|------|--------|
| 1 | Scout Agent | `python verify_agents.py` |
| 2 | Trending Agent | `python verify_agents.py` |
| 3 | Coordinator Pipeline | Create `FORCE_CRASH_TEST` |
| 4A | Database Tables | `python debug_db.py` |
| 4B | War Room Signals API | `curl /api/war-room/signals` |
| 4C | Live Feed API | `curl /api/feed/live` |
| 5 | Deploy Response | `POST /api/deploy-response` |

---

## Troubleshooting

### Scout Agent Fails
- Check `YF_API_KEY` in .env
- Verify market hours (9:15 AM - 3:30 PM IST for Indian stocks)

### Trending Agent Fails
- Check `GEMINI_API_KEY` in .env
- Verify internet connection for Google News RSS

### Coordinator No Crash Detection
- Use `FORCE_CRASH_TEST` file to simulate
- Check terminal logs for SIGMA_EVENT

### Database Errors
- Run `setup_aegis_db.sql` in Supabase SQL Editor
- Verify `SUPABASE_URL` and `SUPABASE_KEY` in .env

### API 404 Errors
- Ensure server is running on port 8000
- Use `/api/` prefix: `/api/war-room/signals`

---

## Success Criteria

✅ **All Phases Pass When:**
1. verify_agents.py shows ✅ for both agents
2. Force crash test triggers full pipeline with logs
3. debug_db.py shows all 3 tables accessible
4. API endpoints return valid JSON
5. Deploy response returns success + shows in logs

**System Is Ready For Production When All ✅ Pass**
