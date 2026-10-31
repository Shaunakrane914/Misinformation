# Aegis Protocol — Security Policy & Defense Architecture

**Document Version:** 2.0.0 (Final v2 Deployment)  
**Classification:** Public Engineering & Security Specification  
**Last Audited:** 2026-10-31  

---

## 1. Supported Versions & Deployment Security Tiers

| Version | Branch | Status | Maintenance Commitment |
| :--- | :--- | :--- | :--- |
| **Aegis 2.0 (v4.1.0 Engine)** | `feat/phase8-real-acquisition-proof` | **Active / Current Production** | Full security patches and vulnerability triage |
| Legacy v1.x | `main` (Historical baseline) | Deprecated | Critical security fixes only |

---

## 2. Reporting a Vulnerability

We prioritize responsible disclosure and take all potential vulnerabilities seriously.
- **Do not** report security vulnerabilities via public GitHub issues, discussions, or pull requests.
- Submit vulnerability reports directly to the maintainer via email with the subject line `[SECURITY REPORT] Aegis Protocol - <Short Description>`.
- **Response SLA**: Acknowledgment within 24 hours; initial triage and severity assessment within 72 hours.
- **Bounty / Attribution**: Coordinated public disclosure with CVE assignment and credit in release notes once the patch is validated.

---

## 3. Seven Core Security Controls & Defense-in-Depth

Aegis Protocol operates as an evidence acquisition engine interacting with untrusted external web endpoints, feeds, and APIs. To prevent weaponization or exploitation, the platform enforces 7 layers of defense:

### 3.1. Outbound SSRF & Network Boundary Defense (`is_safe_url()`)
Every URL passed to the acquisition fabric (via user prompt, RSS redirect, web search, or channel routing) is strictly validated before any HTTP connection is initiated:
- **Protocol Whitelist**: Only `http://` and `https://` schemes are permitted. All others (`file://`, `ftp://`, `gopher://`, `data:`, `expect://`) are immediately rejected.
- **Hostname Resolution & IP Inspection**: Hostnames are resolved to physical IP addresses before connecting. Outbound requests are blocked against:
  - Loopback: `127.0.0.0/8`, `::1`
  - Private RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
  - Link-Local & Carrier-Grade NAT: `169.254.0.0/16`, `100.64.0.0/10`, `fe80::/10`
  - Unique Local IPv6: `fc00::/7`
  - Cloud Instance Metadata Services: `169.254.169.254`, `metadata.google.internal`
- **Encoding Obfuscation Protection**: Rejects octal, decimal (`http://2130706433`), hexadecimal IP representations, and embedded userinfo (`http://user:pass@host`).

### 3.2. Bounded Network I/O & Resource Caps
To prevent denial-of-service, slowloris attacks, and memory exhaustion from malicious web servers:
- **Strict Timeouts**: Every HTTP request enforces a deterministic timeout of `5.0s` (connect timeout `3.0s`).
- **Maximum Buffer Capping**: Response payload sizes are strictly capped at `max_bytes = 1_000_000` (1 MB). Streaming parsers abort downloads if the header or content exceeds 1 MB, mitigating decompression bombs and gigabyte file streams.
- **Bounded Concurrency**: Native workers limit simultaneous in-flight connections per domain to 3, with jittered retry backoffs to prevent outbound traffic spikes.

### 3.3. Zero Secret Leaking & Credential Redaction
- **No Credentials in Storage**: API tokens (`GEMINI_API_KEY`, `SUPABASE_KEY`, `APIFY_TOKEN`, `YF_API_KEY`) are stored exclusively in process memory and environment variables.
- **Log Redaction Filter**: Telemetry loggers enforce automatic string masks for all authorization tokens, cookies, Bearer headers, and user-agent credentials.
- **Sanitized Dossiers**: Investigation dossiers (`backend/data/dossiers/`) are cryptographically sealed with all authorization material stripped.

### 3.4. Production Mock Prohibition Guard
- To prevent accidental deployment of mocked, synthetic, or fake intelligence in production, the application enforces a strict boot-level invariant:
  ```python
  if os.getenv("ENVIRONMENT") == "production" and os.getenv("AEGIS_MOCK_LLM", "").lower() == "true":
      raise RuntimeError("FATAL: AEGIS_MOCK_LLM=true is strictly forbidden when ENVIRONMENT=production")
  ```

### 3.5. Client-Side XSS Sanitization & Content Security
- **DOM Construction over InnerHTML**: `frontend/unified-report-renderer.js` and `frontend/intelligence-transformer.js` avoid unescaped `innerHTML` injection of raw web snippets. All untrusted publisher summaries and post titles are rendered via `element.textContent` or escaped SVG text nodes.
- **CSS Isolation**: High-craft data visualizations use isolated SVG viewBoxes and Canvas 2D contexts, eliminating DOM script injection vectors.

### 3.6. Cryptographic Provenance & Replay Ledger
- Every evidence item acquired during an investigation is hashed via SHA-256 (`content_hash`) upon arrival.
- The `ReplayLedger` records immutable chronological hashes for each stage of pipeline execution. Any post-investigation modification of evidence files or dossiers is immediately detected via hash verification (`/api/replay/verify`).

### 3.7. Truthful Telemetry & Anti-Fabrication Guarantees
- If evidence cannot be retrieved due to provider downtime, paywalls, or rate limits, the system explicitly returns `INSUFFICIENT_EVIDENCE` or status `FAILED`.
- The engine strictly prohibits hallucinating or fabricating positive findings, fake quotes, or synthetic social posts.

---

## 4. Security Verification & Test Suite

All security invariants are tested continuously in the automated test suite:
```bash
# Execute security regression suite
pytest tests/security -q

# Includes:
# - tests/security/test_security_ssrf_xss.py
# - tests/security/test_safe_http_transport.py
# - tests/security/test_review_security_regressions.py
```
Total Security Tests: **42 / 42 passing** with zero warnings or bypassed assertions.
