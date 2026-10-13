# Phase 8A real acquisition capability matrix

- Commit: `620beecff25c7561769db926d8f7ac12447d3bfa`
- Gate: **PARTIAL**
- Protected operations live-verified: 4 / 16
- A live verification requires adapter-level network observation and usable, honestly classified output.
- Response bodies are not retained; bounded hashes/byte counts and normalized excerpts provide reproducible proof without storing whole copyrighted documents.

| Operation | Status | Verified depth | Probes | Live probes |
|---|---|---|---:|---:|
| `github.read` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `github.issues` | NOT_LIVE_VERIFIED | none | 1 | 0 |
| `github.prs` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `github.commits` | LIVE_VERIFIED | DIRECT_METADATA | 1 | 1 |
| `github.releases` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `youtube.read` | NOT_PROBED | none | 0 | 0 |
| `youtube.transcript` | NOT_PROBED | none | 0 | 0 |
| `youtube.comments` | NOT_PROBED | none | 0 | 0 |
| `v2ex.latest` | NOT_PROBED | none | 0 | 0 |
| `v2ex.search` | NOT_PROBED | none | 0 | 0 |
| `v2ex.topic` | NOT_PROBED | none | 0 | 0 |
| `v2ex.replies` | NOT_PROBED | none | 0 | 0 |
| `web.read` | NOT_PROBED | none | 0 | 0 |
| `rss.read` | NOT_PROBED | none | 0 | 0 |
| `xiaoyuzhou.podcast` | NOT_PROBED | none | 0 | 0 |
| `xiaoyuzhou.episodes` | NOT_PROBED | none | 0 | 0 |

## Gate limitations

- `github.issues` was not independently live-verified.
- `rss.read` was not independently live-verified.
- `v2ex.latest` was not independently live-verified.
- `v2ex.replies` was not independently live-verified.
- `v2ex.search` was not independently live-verified.
- `v2ex.topic` was not independently live-verified.
- `web.read` was not independently live-verified.
- `xiaoyuzhou.episodes` was not independently live-verified.
- `xiaoyuzhou.podcast` was not independently live-verified.
- `youtube.comments` was not independently live-verified.
- `youtube.read` was not independently live-verified.
- `youtube.transcript` was not independently live-verified.
