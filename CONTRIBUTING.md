# Contributing

Use a focused branch and describe the concrete behavior changed, its tests and any
remaining limitations. Keep runtime changes separate from generated evaluations.

- Preserve working acquisition adapters and compatibility interfaces.
- Do not change frozen retrieval fixtures to make a regression pass.
- Never commit secrets, local databases, personal investigation records or scraped dumps.
- Keep access-denial, source-permission, SSRF and rate-limit protections intact.
- Add a regression when fixing a substantive bug; keep tests offline by default.
- Keep documentation concise: setup, architecture, contracts, reproducibility and limits.

See [architecture](docs/ARCHITECTURE.md), [testing](docs/TESTING.md) and
[security](docs/SECURITY.md). Generated development logs and local assistant
configuration do not belong in the public source tree.
