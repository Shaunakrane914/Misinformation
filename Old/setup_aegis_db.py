"""
Aegis Enterprise Database Setup
================================
Upgrades Supabase schema for War Room architecture.

This script creates tables for:
1. Active Signals - Timeline tracking (crashes + rumors)
2. Deployed Measures - Defense deployment tracking
3. Updates verified_claims - Post-impact analysis

Run this script once to set up the Aegis Enterprise database schema.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "Not configured")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "Not configured")

print("="*80)
print("🏛️ AEGIS ENTERPRISE DATABASE SETUP")
print("="*80)
print()

if SUPABASE_URL != "Not configured":
    print(f"✓ Supabase URL: {SUPABASE_URL}")
    print(f"✓ Service Role Key: {'*' * 40}")
else:
    print("ℹ️  Supabase URL: Not configured")

print()

# We'll generate SQL file instead of executing directly

print("="*80)
print("📊 CREATING AEGIS ENTERPRISE TABLES")
print("="*80)
print()

# ============================================================================
# SQL SCHEMA DEFINITIONS
# ============================================================================

# Table 1: Active Signals (For Correlation Timeline)
active_signals_sql = """
-- Active Signals Table
-- Tracks both stock crashes (CRASH) and misinformation (RUMOR) on a unified timeline
CREATE TABLE IF NOT EXISTS active_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('CRASH', 'RUMOR')),
    severity INTEGER NOT NULL CHECK (severity >= 0 AND severity <= 100),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient timeline queries
CREATE INDEX IF NOT EXISTS idx_active_signals_ticker ON active_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_active_signals_timestamp ON active_signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_active_signals_type ON active_signals(signal_type);

-- Comments
COMMENT ON TABLE active_signals IS 'Timeline tracking for War Room correlation graph';
COMMENT ON COLUMN active_signals.signal_type IS 'CRASH = stock drop, RUMOR = misinformation detected';
COMMENT ON COLUMN active_signals.severity IS 'Panic score (0-100) or Z-score magnitude';
COMMENT ON COLUMN active_signals.metadata IS 'Additional context: price, headline, source, etc.';
"""

# Table 2: Deployed Measures (For Feedback Loop)
deployed_measures_sql = """
-- Deployed Measures Table
-- Tracks when defense responses are deployed and their stock price context
CREATE TABLE IF NOT EXISTS deployed_measures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT NOT NULL,
    measure_type TEXT NOT NULL CHECK (measure_type IN ('LEGAL_NOTICE', 'PR_TWEET', 'INTERNAL_MEMO', 'CEASE_DESIST', 'OFFICIAL_DENIAL', 'CEO_ALERT')),
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stock_price_at_deployment DECIMAL(10, 2),
    ticker TEXT NOT NULL,
    response_text TEXT,
    deployed_by TEXT DEFAULT 'system',
    effectiveness_score INTEGER CHECK (effectiveness_score >= 0 AND effectiveness_score <= 100),
    recovery_time_minutes INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_deployed_measures_event ON deployed_measures(event_id);
CREATE INDEX IF NOT EXISTS idx_deployed_measures_ticker ON deployed_measures(ticker);
CREATE INDEX IF NOT EXISTS idx_deployed_measures_time ON deployed_measures(deployed_at DESC);

-- Comments
COMMENT ON TABLE deployed_measures IS 'Tracks defense deployments for learning/effectiveness analysis';
COMMENT ON COLUMN deployed_measures.stock_price_at_deployment IS 'Stock price when defense was deployed (for recovery calculation)';
COMMENT ON COLUMN deployed_measures.effectiveness_score IS 'How well did this defense work? (calculated post-deployment)';
COMMENT ON COLUMN deployed_measures.recovery_time_minutes IS 'Time until stock recovered after deployment';
"""

# Table 3: Verified Threats (Enhanced version of verified_claims)
verified_threats_sql = """
-- Verified Threats Table
-- Complete attack packages with correlation data and response strategies
CREATE TABLE IF NOT EXISTS verified_threats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT UNIQUE NOT NULL,
    ticker TEXT NOT NULL,
    crash_timestamp TIMESTAMPTZ NOT NULL,
    article_timestamp TIMESTAMPTZ,
    latency_minutes DECIMAL(10, 2),
    smoking_gun_headline TEXT,
    smoking_gun_link TEXT,
    current_price DECIMAL(10, 2),
    z_score DECIMAL(5, 2),
    projected_loss DECIMAL(5, 2),
    panic_score INTEGER CHECK (panic_score >= 0 AND panic_score <= 100),
    correlation_confidence INTEGER CHECK (correlation_confidence >= 0 AND correlation_confidence <= 100),
    verdict TEXT,
    responses JSONB,
    response_deployed BOOLEAN DEFAULT FALSE,
    deployed_at TIMESTAMPTZ,
    post_impact_analysis JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_verified_threats_ticker ON verified_threats(ticker);
CREATE INDEX IF NOT EXISTS idx_verified_threats_crash_time ON verified_threats(crash_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_verified_threats_event_id ON verified_threats(event_id);

-- Comments
COMMENT ON TABLE verified_threats IS 'Complete attack packages from War Room correlation engine';
COMMENT ON COLUMN verified_threats.latency_minutes IS 'Time between article and crash (proves causation)';
COMMENT ON COLUMN verified_threats.correlation_confidence IS 'How confident are we this news caused the crash? (0-100)';
COMMENT ON COLUMN verified_threats.responses IS 'AI-generated crisis responses (legal, PR, CEO alert)';
COMMENT ON COLUMN verified_threats.post_impact_analysis IS 'Recovery metrics after deployment';
"""

# ============================================================================
# EXECUTE SQL OR PROVIDE INSTRUCTIONS
# ============================================================================

print("📝 The following SQL will be executed:\n")
print("1️⃣ CREATE TABLE active_signals")
print("   → For correlation timeline graph")
print()
print("2️⃣ CREATE TABLE deployed_measures")
print("   → For tracking defense deployments and effectiveness")
print()
print("3️⃣ CREATE TABLE verified_threats")
print("   → For complete attack packages with AI responses")
print()

# Note: Supabase Python client doesn't support raw SQL execution directly
# We need to use the REST API or provide SQL for manual execution

print("="*80)
print("⚠️  MANUAL SETUP REQUIRED")
print("="*80)
print()
print("The Supabase Python client doesn't support raw SQL execution.")
print("Please run the following SQL in your Supabase SQL Editor:")
print()
print("📍 Go to: https://app.supabase.com/project/YOUR_PROJECT/sql")
print()
print("="*80)

# Save SQL to file for easy copying
sql_file_path = "backend/setup_aegis_db.sql"

with open(sql_file_path, 'w') as f:
    f.write("-- Aegis Enterprise Database Setup\n")
    f.write("-- Run this SQL in Supabase SQL Editor\n")
    f.write("-- https://app.supabase.com/project/YOUR_PROJECT/sql\n\n")
    f.write("="*80 + "\n")
    f.write("-- TABLE 1: ACTIVE SIGNALS (Timeline Tracking)\n")
    f.write("="*80 + "\n\n")
    f.write(active_signals_sql)
    f.write("\n\n")
    f.write("="*80 + "\n")
    f.write("-- TABLE 2: DEPLOYED MEASURES (Defense Tracking)\n")
    f.write("="*80 + "\n\n")
    f.write(deployed_measures_sql)
    f.write("\n\n")
    f.write("="*80 + "\n")
    f.write("-- TABLE 3: VERIFIED THREATS (Attack Packages)\n")
    f.write("="*80 + "\n\n")
    f.write(verified_threats_sql)

print(f"✅ SQL saved to: {sql_file_path}")
print()
print("="*80)
print("📋 SETUP INSTRUCTIONS")
print("="*80)
print()
print("STEP 1: Open the SQL file")
print(f"   → {os.path.abspath(sql_file_path)}")
print()
print("STEP 2: Copy all the SQL")
print()
print("STEP 3: Paste into Supabase SQL Editor")
print("   → https://app.supabase.com/project/YOUR_PROJECT/sql")
print()
print("STEP 4: Click 'Run' to create all tables")
print()
print("="*80)
print("📊 SCHEMA SUMMARY")
print("="*80)
print()
print("After setup, you'll have:")
print()
print("✓ active_signals")
print("  - Tracks crashes and rumors on unified timeline")
print("  - Enables correlation graph in dashboard")
print()
print("✓ deployed_measures")
print("  - Records when defenses are deployed")
print("  - Tracks stock price at deployment")
print("  - Calculates effectiveness for learning")
print()
print("✓ verified_threats")
print("  - Complete attack packages")
print("  - Smoking gun evidence")
print("  - AI-generated responses")
print("  - Post-deployment analysis")
print()
print("="*80)
print("🚀 NEXT STEPS")
print("="*80)
print()
print("1. Run the SQL in Supabase SQL Editor")
print("2. Verify tables exist in Supabase Dashboard")
print("3. Test with: python test_war_room.py")
print("4. Trigger demo: http://localhost:8000/api/war-room/demo-attack")
print()
print("="*80)
print("✅ SETUP COMPLETE")
print("="*80)
