# Security model and evidence-integrity boundaries

Maintained against `abe547f` on 2026-10-14. This is a code/regression map, not security certification, complete threat coverage or launch approval. See [independent review](../architecture/PHASE8_INDEPENDENT_REVIEW_2026-10-14.md) and [current state](../CURRENT_STATE.md).

## Trust boundaries

User claims, URLs, scraped content, source metadata and model output are untrusted. Distinguish:

1. Input normalization and admission.
2. Network destination/redirect/credential safety.
3. Source ownership and content authority.
4. Citation existence and proposition support.
5. Stored-byte integrity and factual truth.
6. Safe browser display and operator action authorization.

A control at one boundary cannot substitute for the others.

## Network acquisition

Canonical owners: [URL validator](../../backend/infrastructure/acquisition/security/url_validator.py) and [bounded public HTTP transport](../../backend/infrastructure/acquisition/network/http.py). Old service paths are compatibility surfaces.

The validator restricts HTTP(S)/allowed ports and blocks non-public/private/loopback/link-local/reserved addresses. The transport checks destinations/redirects, bounded response/decompression limits and resolved connection behavior. Cross-origin redirects strip authorization, cookies and API-key headers case-insensitively. A pre-fetch string check alone is not the DNS-rebinding defense; callers must use the guarded transport.

[Safe transport regressions](../../tests/security/test_safe_http_transport.py), [legacy Scout transport boundaries](../../tests/security/test_scout_legacy_transport_boundaries.py) and [security regression suite](../../tests/security/) exercise selected cases. Do not assume every future adapter uses this boundary without inspection.

## Source origin and authority

[source_quality.py](../../backend/services/research/source_quality.py) validates canonical hostnames and exact/subdomain boundaries. `sec.gov.attacker.example`, a URL path containing `sec.gov`, userinfo or a supplied publisher name cannot authenticate a regulator. An observed web redirect endpoint takes precedence where retained.

Domain ownership is not content authority: an official homepage/search index/submission metadata record is not an acquired filing body. BrandShield's scan layer uses shared qualification instead of re-promoting URL substrings. A primary label is not proof of speaker identity, claim truth or recording authenticity.

## Prompt/model boundaries

Evidence demarcation, input filtering and instruction separation are defenses, not proven immunity. [Specialist extraction guard](../../backend/services/research/model_grounding.py) removes uncited records and keeps model statuses unverified. Valid evidence IDs are necessary but do **not** prove citation entailment. [Lexical alignment](../../backend/services/research/proposition_grounding.py) is conservative and uncalibrated, not a general semantic truth engine.

Online model prompt-injection and free-text correctness remain unverified without authorized live model evaluation. Offline mock traps must not be labeled successful real-provider jailbreak tests.

## Dossiers and replay

[Replay ledger and its `verify_dossier_integrity()` function](../../backend/services/research/replay_ledger.py) record/validate structural and hash integrity. Hashes can detect changed stored bytes; they do not authenticate a publisher or verify factual veracity. Legacy unsealed records must be labeled separately, malformed records must not be treated as valid evidence, and unknown dates stay unknown.

Actual routes are `/api/research/replay/dossiers`, `/dossiers/{session_id}` and `/reexecute/{session_id}` under that prefix, with compatibility aliases. Read [API map](../api/CURRENT_ENDPOINTS.md); do not assume an invented `/api/replay/verify` route.

Protect every historical dossier and frozen retrieval dataset. Preserve old artifacts/research. Recovery is an owner-led assessment, never fabrication or silent overwrite.

## Browser and action boundaries

[Safe display URLs](../../frontend/safe-source-url.js), escaping/textContent, exact verdict aliases and explicit unknown states are separate from backend SSRF. They apply to inspected maintained components, not a blanket guarantee for every archived page. [Node regressions](../../tests/frontend/) and Chromium proof cover selected states; gradient contrast/manual assistive technology remain open.

[Operator authorization](../../backend/api/security.py) protects the response-deployment action with a server-side bearer token: 503 when configuration is absent; 401 for missing/invalid authorization. Public research endpoints remain public. Do not claim universal authentication or embed this token in browser settings.

## Verification and response

```text
pytest tests/security -q
pytest tests/unit/test_phase8_independent_regressions.py tests/unit/test_phase8_audit_report_truth.py -q
python scripts/validation/verify_frozen_benchmarks.py
```

Use [testing runbook](../testing/README.md) for complete regression commands and isolation. Never reproduce attacks against an unrelated public system, dump secrets, delete evidence or rewrite Git history. Preserve minimal sanitized findings and seek owner authorization for credential rotation, production changes or external reporting.
