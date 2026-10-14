# Phase 8A real acquisition capability matrix

- Commit: `f0a41b7fd1b2548dfe5ef2002ee308cd21d039f0`
- Gate: **PARTIAL**
- Protected operations live-verified: 3 / 16
- A live verification requires adapter-level network observation and usable, honestly classified output.
- Response bodies are not retained; bounded hashes/byte counts and normalized excerpts provide reproducible proof without storing whole copyrighted documents.

| Operation | Status | Verified depth | Probes | Live probes |
|---|---|---|---:|---:|
| `github.read` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `github.issues` | NOT_PROBED | none | 0 | 0 |
| `github.prs` | NOT_PROBED | none | 0 | 0 |
| `github.commits` | NOT_PROBED | none | 0 | 0 |
| `github.releases` | NOT_PROBED | none | 0 | 0 |
| `youtube.read` | LIVE_VERIFIED | DIRECT_METADATA | 1 | 1 |
| `youtube.transcript` | NOT_PROBED | none | 0 | 0 |
| `youtube.comments` | NOT_PROBED | none | 0 | 0 |
| `v2ex.latest` | NOT_PROBED | none | 0 | 0 |
| `v2ex.search` | NOT_PROBED | none | 0 | 0 |
| `v2ex.topic` | NOT_PROBED | none | 0 | 0 |
| `v2ex.replies` | NOT_PROBED | none | 0 | 0 |
| `web.read` | NOT_PROBED | none | 0 | 0 |
| `rss.read` | LIVE_VERIFIED | SYNDICATED_SUMMARY | 1 | 1 |
| `xiaoyuzhou.podcast` | NOT_PROBED | none | 0 | 0 |
| `xiaoyuzhou.episodes` | NOT_PROBED | none | 0 | 0 |

## Gate limitations

- `github.commits` was not independently live-verified.
- `github.issues` was not independently live-verified.
- `github.prs` was not independently live-verified.
- `github.releases` was not independently live-verified.
- `v2ex.latest` was not independently live-verified.
- `v2ex.replies` was not independently live-verified.
- `v2ex.search` was not independently live-verified.
- `v2ex.topic` was not independently live-verified.
- `web.read` was not independently live-verified.
- `xiaoyuzhou.episodes` was not independently live-verified.
- `xiaoyuzhou.podcast` was not independently live-verified.
- `youtube.comments` was not independently live-verified.
- `youtube.transcript` was not independently live-verified.
