# Aegis Protocol — Security & Privacy Audit Findings
**Audit Date**: September 21, 2026

---

## Security Risk Matrix

| Finding ID | Vulnerability | Severity | Affected Components | User / System Impact | Recommended Remediation |
|---|---|---|---|---|---|
| **SEC-01** | **Server-Side Request Forgery (SSRF)** | **High** | `backend/services/agent_reach_scraper.py`, `backend/main.py` | Attackers can specify internal URLs (`http://127.0.0.1:8000`, `http://169.254.169.254/latest/meta-data`) in `source_url` parameter to probe internal services and cloud metadata | Implement strict URL validation: enforce `http`/`https`, resolve DNS, and block loopback, link-local, private IP ranges (RFC 1918), and cloud metadata IP ranges |
| **SEC-02** | **Stored / Reflected Cross-Site Scripting (XSS)** | **High** | `frontend/trending-agent.html`, `frontend/scout-agent.html`, `frontend/submit.html`, `frontend/personal-watch-agent.html` | Scraped article titles, tweets, or malicious user claims containing `<script>` or `<img src=x onerror=...>` are injected into DOM via `.innerHTML` | Implement HTML entity escaping utility (`escapeHtml`) across all frontend renderers, and use `textContent` where HTML formatting is not required |
| **SEC-03** | **Prompt Injection & Instruction Hijacking** | **Medium** | `backend/agents/research_agent.py`, `backend/agents/investigator_agent.py` | Untrusted scraped webpage contents concatenated directly into LLM prompts without clear structural boundary tags, allowing adversarial texts to manipulate verdict | Wrap untrusted evidence inside strictly delimited XML-like containers (e.g., `<evidence_untrusted>...<\evidence_untrusted>`) and explicitly instruct the model to treat content within tags as data, never instructions |
| **SEC-04** | **Unbounded Input Payload & ReDoS** | **Medium** | `backend/schemas/claim_schemas.py`, `backend/main.py` | `claim_text` accepts arbitrary payload sizes; regex tokenizers run on unbounded input strings | Enforce Pydantic validation: `min_length=5`, `max_length=5000` on input texts; add timeout guards to regex operations |
| **SEC-05** | **Configuration Credential Drift** | **Low** | `backend/config.py`, `backend/db/database.py` | Inconsistent variable names (`SUPABASE_KEY` vs `SUPABASE_SERVICE_ROLE_KEY`) cause silent fallback to in-memory store in production | Unify configuration resolution in `backend/config.py` to check `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_KEY`, and `SUPABASE_ANON_KEY` |
