# Database Integration - SQL Schema

Create these tables in your Supabase SQL Editor:

```sql
-- Claims table
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_hash TEXT UNIQUE NOT NULL,
    claim_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    verdict TEXT,
    confidence DECIMAL(3,2),
    severity TEXT,
    reasoning TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Evidence table
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID REFERENCES claims(id) ON DELETE CASCADE,
    source_url TEXT,
    summary TEXT NOT NULL,
    stance TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_claims_hash ON claims(claim_hash);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_evidence_claim_id ON evidence(claim_id);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_claims_updated_at BEFORE UPDATE ON claims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Table Descriptions

### `claims` table
- `id` - UUID primary key
- `claim_hash` - SHA256 hash of normalized text (unique)
- `claim_text` - Original claim text
- `normalized_text` - Lowercase, trimmed text
- `status` - pending | in_progress | completed | failed
- `verdict` - True | False | Misleading | Unverified
- `confidence` - 0.0 to 1.0
- `severity` - Low | Medium | High
- `reasoning` - Explanation text
- `created_at` - Timestamp
- `updated_at` - Auto-updated timestamp

### `evidence` table
- `id` - UUID primary key
- `claim_id` - Foreign key to claims
- `source_url` - URL of evidence source (nullable)
- `summary` - Evidence description
- `stance` - supporting | refuting | neutral
- `created_at` - Timestamp
