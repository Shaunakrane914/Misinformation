# Quick Fix Guide - Verification Issues

## Issues Found:

### 1. ❌ Scout Agent Failed
**Problem:** Market is closed (4 PM IST, market closes at 3:30 PM)
**Solution:** Test during market hours (9:15 AM - 3:30 PM IST) OR use the force crash test mode

### 2. ❌ Database Tables Don't Exist  
**Problem:** Tables not created in Supabase yet
**Solution:** Run the SQL script in Supabase SQL Editor

---

## Quick Fixes:

### Fix 1: Create Database Tables

1. **Open Supabase SQL Editor:**
   - Go to https://supabase.com/dashboard
   - Select your project
   - Click "SQL Editor" in the left sidebar

2. **Copy and Paste the SQL:**
   - Open `backend/setup_aegis_db.sql`
   - Copy ALL the content
   - Paste into Supabase SQL Editor
   - Click "Run" button

3. **Verify Tables Created:**
   ```bash
   python debug_db.py
   ```
   You should see:
   ```
   ✅ Table 'active_signals' accessible
   ✅ Table 'verified_threats' accessible
   ✅ Table 'deployed_measures' accessible
   ```

### Fix 2: Test Scout Agent (Without Market)

Since market is closed, use **Force Crash Test Mode**:

1. **Create test file:**
   ```powershell
   New-Item -Name "FORCE_CRASH_TEST" -ItemType File
   ```

2. **Check if server is running:**
   - Look for terminal running `python main.py`
   - If not running, start it: `python main.py`

3. **Watch the logs:**
   You should see:
   ```
   🧪 FORCE CRASH TEST MODE ACTIVATED!
   🚨 SIGMA EVENT DETECTED!
   ```

4. **Clean up:**
   ```powershell
   Remove-Item "FORCE_CRASH_TEST"
   ```

### Fix 3: Add YF_API_KEY (Optional)

If you want to test Scout with real data during market hours:

1. **Get API Key:**
   - Go to https://financeapi.net/
   - Sign up for free tier
   - Get your API key

2. **Add to .env:**
   ```env
   YF_API_KEY=your_api_key_here
   ```

3. **Test during market hours (9:15 AM - 3:30 PM IST):**
   ```bash
   python verify_agents.py
   ```

---

## Expected Results After Fixes:

### ✅ Database Check:
```bash
python debug_db.py
```
```
✅ Supabase client initialized
✅ Table 'active_signals' accessible
✅ Table 'verified_threats' accessible
✅ Table 'deployed_measures' accessible
✅ ALL CHECKS PASSED
```

### ✅ Force Crash Test:
```bash
# Create file, then check server logs
```
```
🧪 FORCE CRASH TEST MODE ACTIVATED!
🚨 SIGMA EVENT DETECTED!
🔎 STEP 2: CONTENT INTELLIGENCE HUNT
🎯 SMOKING GUN IDENTIFIED!
💾 STEP 5: ARCHIVING VERIFIED THREAT
```

---

## Next Steps:

1. **Run SQL in Supabase** (Fix tables)
2. **Use Force Crash Test** (Test pipeline without market)
3. **Check API endpoints:**
   ```powershell
   curl http://127.0.0.1:8000/api/war-room/signals
   curl http://127.0.0.1:8000/api/feed/live
   ```

All systems are **code complete** - just need the database setup to finish verification!
