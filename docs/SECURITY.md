# Aegis Protocol — Security Architecture & Hardening Guide
**Document Version**: 3.5.1  
**Scope**: Full Stack (FastAPI, Scrapers, Agent Reach, Ingestion, Frontend UI)

---

## 1. Threat Model & Mitigation Matrix

| Attack Vector | Impact | Implemented Mitigation | Verification Method |
| :--- | :--- | :--- | :--- |
| **Server-Side Request Forgery (SSRF)** | Attacker submits internal URLs (`127.0.0.1`, `169.254.169.254`, `10.0.0.0/8`) via `source_url` to inspect cloud metadata or internal services. | `backend/services/url_validator.py` resolves DNS hostnames before fetching, blocking private IPv4/IPv6 CIDR ranges, link-local addresses, and non-standard ports. | Tested in `tests/security/test_security_ssrf_xss.py` across 10 dangerous URL vectors. |
| **Cross-Site Scripting (XSS)** | Malicious claims or scraped summaries containing `<script>` or event handler payloads execute in client browsers. | Global `escapeHtml` sanitizer implemented in `frontend/aegis-nav.js`; applied to all dynamic innerHTML injections across agent pages. | Tested in `tests/security/test_security_ssrf_xss.py`. |
| **Prompt Injection / Jailbreaks** | Untrusted scraped web content embeds instructions attempting to override fact-checker verdicts or exfiltrate system prompts. | Structured `<evidence_untrusted>` XML encapsulation in `backend/agents/research_agent.py` and `investigator_agent.py`; models instructed to treat raw text strictly as evidentiary data. | Verified in investigator agent prompt definitions. |
| **Unbounded Concurrency & Resource Exhaustion** | Floods of claims or scrapers exhausting memory, sockets, or LLM quotas. | 1. Ingestion deduplication by SHA-256 hash.<br>2. Bounded worker tasks via FastAPI background queue.<br>3. Jittered exponential backoff on HTTP 429 rate limits. | Verified in `tests/unit/test_normalization_and_dedup.py` and `gemini_service.py`. |
| **Credential Exposure** | API keys committed or leaked in client responses / logs. | Key sanitization in logging; centralized `backend/config.py` loading keys strictly from environment; no raw keys transmitted to frontend. | Codebase audited in Phase 0 audit. |

---

## 2. SSRF Guard Implementation Details

All outbound HTTP fetching via `agent_reach_scraper.py` is guarded by:
```python
from backend.services.url_validator import validate_url_safe

is_safe, reason = validate_url_safe(target_url)
if not is_safe:
    raise ValueError(f"Blocked unsafe URL: {reason}")
```

### Blocked Ranges:
- `127.0.0.0/8` (IPv4 loopback)
- `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC 1918 Private)
- `169.254.0.0/16` (IPv4 Link-Local & AWS/GCP Metadata)
- `::1/128`, `fc00::/7`, `fe80::/10` (IPv6 loopback, ULA, link-local)
- Protocols other than `http` and `https`
- Ports other than `80` and `443`

---

## 3. Security Regression Testing
Run the automated security regression tests:
```bash
python -m pytest tests/security/ -v
```
