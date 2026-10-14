# Security Policy

## Supported Versions
Only the latest release branch is actively maintained.

## Reporting a Vulnerability
Please **do not** open a public GitHub issue for security vulnerabilities.
Email the maintainer directly. We aim to respond within 72 hours.

## Known Security Controls
- SSRF validation via `is_safe_url()` on all outbound requests
- XSS sanitization on all user-supplied inputs before rendering
- No API keys logged or included in research dossiers
- `AEGIS_MOCK_LLM=true` forbidden in `ENVIRONMENT=production`
