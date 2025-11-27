-- Aegis Enterprise Database Setup
-- Run this SQL in Supabase SQL Editor
-- https://app.supabase.com/project/YOUR_PROJECT/sql

================================================================================
-- TABLE 1: ACTIVE SIGNALS (Timeline Tracking)
================================================================================


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


================================================================================
-- TABLE 2: DEPLOYED MEASURES (Defense Tracking)
================================================================================


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


================================================================================
-- TABLE 3: VERIFIED THREATS (Attack Packages)
================================================================================


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
