# Phase 8A real acquisition capability matrix

- Commit: `dc249fe369506c8677916b57f8022d292be62216`
- Gate: **PARTIAL**
- Protected operations live-verified: 15 / 16
- A live verification requires adapter-level network observation and usable, honestly classified output.
- Response bodies are not retained; bounded hashes/byte counts and normalized excerpts provide reproducible proof without storing whole copyrighted documents.

| Operation | Status | Verified depth | Probes | Live probes |
|---|---|---|---:|---:|
| `github.read` | LIVE_VERIFIED | DIRECT_METADATA | 3 | 2 |
| `github.issues` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 3 | 2 |
| `github.prs` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 3 | 2 |
| `github.commits` | LIVE_VERIFIED | DIRECT_METADATA | 3 | 1 |
| `github.releases` | NOT_LIVE_VERIFIED | none | 3 | 0 |
| `youtube.read` | LIVE_VERIFIED | DIRECT_METADATA | 3 | 2 |
| `youtube.transcript` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 3 | 2 |
| `youtube.comments` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 3 | 2 |
| `v2ex.latest` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 3 | 3 |
| `v2ex.search` | LIVE_VERIFIED | DIRECT_FULL_CONTENT, DIRECT_PARTIAL_CONTENT | 3 | 2 |
| `v2ex.topic` | LIVE_VERIFIED | DIRECT_FULL_CONTENT, DIRECT_PARTIAL_CONTENT | 3 | 2 |
| `v2ex.replies` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 3 | 2 |
| `web.read` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 3 | 2 |
| `rss.read` | LIVE_VERIFIED | SYNDICATED_SUMMARY | 3 | 2 |
| `xiaoyuzhou.podcast` | LIVE_VERIFIED | SYNDICATED_SUMMARY | 3 | 1 |
| `xiaoyuzhou.episodes` | LIVE_VERIFIED | SYNDICATED_SUMMARY | 3 | 1 |

## Gate limitations

- `github.releases` was not independently live-verified.
