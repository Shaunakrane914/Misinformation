# Phase 8A real acquisition capability matrix

- Commit: `ca57e70b75d4365eeda26a65495c284cdc88aac4`
- Gate: **PARTIAL**
- Protected operations live-verified: 1 / 16
- A live verification requires adapter-level network observation and usable, honestly classified output.
- Response bodies are not retained; bounded hashes/byte counts and normalized excerpts provide reproducible proof without storing whole copyrighted documents.

| Operation | Status | Verified depth | Probes | Live probes |
|---|---|---|---:|---:|
| `github.read` | NOT_PROBED | none | 0 | 0 |
| `github.issues` | NOT_PROBED | none | 0 | 0 |
| `github.prs` | NOT_PROBED | none | 0 | 0 |
| `github.commits` | NOT_PROBED | none | 0 | 0 |
| `github.releases` | NOT_PROBED | none | 0 | 0 |
| `youtube.read` | NOT_PROBED | none | 0 | 0 |
| `youtube.transcript` | NOT_PROBED | none | 0 | 0 |
| `youtube.comments` | NOT_PROBED | none | 0 | 0 |
| `v2ex.latest` | NOT_PROBED | none | 0 | 0 |
| `v2ex.search` | NOT_PROBED | none | 0 | 0 |
| `v2ex.topic` | NOT_PROBED | none | 0 | 0 |
| `v2ex.replies` | NOT_PROBED | none | 0 | 0 |
| `web.read` | LIVE_VERIFIED | DIRECT_FULL_CONTENT, DIRECT_PARTIAL_CONTENT | 2 | 2 |
| `rss.read` | NOT_PROBED | none | 0 | 0 |
| `xiaoyuzhou.podcast` | NOT_PROBED | none | 0 | 0 |
| `xiaoyuzhou.episodes` | NOT_PROBED | none | 0 | 0 |

## Gate limitations

- `github.commits` was not independently live-verified.
- `github.issues` was not independently live-verified.
- `github.prs` was not independently live-verified.
- `github.read` was not independently live-verified.
- `github.releases` was not independently live-verified.
- `rss.read` was not independently live-verified.
- `v2ex.latest` was not independently live-verified.
- `v2ex.replies` was not independently live-verified.
- `v2ex.search` was not independently live-verified.
- `v2ex.topic` was not independently live-verified.
- `xiaoyuzhou.episodes` was not independently live-verified.
- `xiaoyuzhou.podcast` was not independently live-verified.
- `youtube.comments` was not independently live-verified.
- `youtube.read` was not independently live-verified.
- `youtube.transcript` was not independently live-verified.
