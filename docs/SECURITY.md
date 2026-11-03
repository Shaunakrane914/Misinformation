# Security boundaries

External URLs and retrieved content are untrusted inputs. The application must
preserve these boundaries across primary readers, redirects and fallbacks:

- Validate destination scheme, port and DNS answers; reject private, loopback,
  link-local and metadata destinations. DNS capacity failure is a failed validation.
- Revalidate redirect destinations and pin validated network addresses. Do not
  forward credentials to another origin or platform.
- Enforce source permissions, robots/rate limits, deadlines, HTTP admissions and
  bounded response/decompression sizes.
- Treat explicit denial, authentication challenges and 401/403/429 as terminal for
  that access path. An alternate reader must not evade the source's restriction.
- Escape untrusted text in browser reports and validate external link schemes.
- Keep credentials and personal investigation records out of responses, logs and Git.
- Treat source prose as data, not instructions to a model or permission to use tools.

See `tests/security/` for regression coverage. These controls are not a certification
that every legacy route is vulnerability-free. Use [SECURITY.md](../SECURITY.md) for
responsible reporting and [operations](OPERATIONS.md) for deployment configuration.
