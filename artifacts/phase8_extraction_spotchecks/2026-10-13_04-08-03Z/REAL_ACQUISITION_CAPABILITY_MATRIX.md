# Phase 8A real acquisition capability matrix

- Commit: `3b3dc23d082f50d4f3654c5afa4b91064fada3bd`
- Gate: **PARTIAL**
- Protected operations live-verified: 10 / 16
- A live verification requires adapter-level network observation and usable, honestly classified output.
- Response bodies are not retained; bounded hashes/byte counts and normalized excerpts provide reproducible proof without storing whole copyrighted documents.

| Operation | Status | Verified depth | Probes | Live probes |
|---|---|---|---:|---:|
| `github.read` | NOT_PROBED | none | 0 | 0 |
| `github.issues` | NOT_PROBED | none | 0 | 0 |
| `github.prs` | NOT_PROBED | none | 0 | 0 |
| `github.commits` | NOT_PROBED | none | 0 | 0 |
| `github.releases` | NOT_PROBED | none | 0 | 0 |
| `youtube.read` | LIVE_VERIFIED | DIRECT_METADATA | 1 | 1 |
| `youtube.transcript` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 1 | 1 |
| `youtube.comments` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 1 | 1 |
| `v2ex.latest` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `v2ex.search` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `v2ex.topic` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `v2ex.replies` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 1 | 1 |
| `web.read` | NOT_PROBED | none | 0 | 0 |
| `rss.read` | LIVE_VERIFIED | SYNDICATED_SUMMARY | 1 | 1 |
| `xiaoyuzhou.podcast` | LIVE_VERIFIED | DIRECT_METADATA | 1 | 1 |
| `xiaoyuzhou.episodes` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |

## Gate limitations

- `github.commits` was not independently live-verified.
- `github.issues` was not independently live-verified.
- `github.prs` was not independently live-verified.
- `github.read` was not independently live-verified.
- `github.releases` was not independently live-verified.
- `web.read` was not independently live-verified.
