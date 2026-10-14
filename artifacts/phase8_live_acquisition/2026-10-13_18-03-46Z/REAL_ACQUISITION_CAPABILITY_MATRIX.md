# Phase 8A real acquisition capability matrix

- Commit: `6e99b3c195f719372e94edfbf5b1a0acf6cab7cf`
- Gate: **PASS**
- Protected operations live-verified: 16 / 16
- A live verification requires adapter-level network observation and usable, honestly classified output.
- Response bodies are not retained; bounded hashes/byte counts and normalized excerpts provide reproducible proof without storing whole copyrighted documents.

| Operation | Status | Verified depth | Probes | Live probes |
|---|---|---|---:|---:|
| `github.read` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `github.issues` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `github.prs` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `github.commits` | LIVE_VERIFIED | DIRECT_METADATA | 1 | 1 |
| `github.releases` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `youtube.read` | LIVE_VERIFIED | DIRECT_METADATA | 1 | 1 |
| `youtube.transcript` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 1 | 1 |
| `youtube.comments` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 1 | 1 |
| `v2ex.latest` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `v2ex.search` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `v2ex.topic` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `v2ex.replies` | LIVE_VERIFIED | DIRECT_FULL_CONTENT | 1 | 1 |
| `web.read` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
| `rss.read` | LIVE_VERIFIED | SYNDICATED_SUMMARY | 1 | 1 |
| `xiaoyuzhou.podcast` | LIVE_VERIFIED | DIRECT_METADATA | 1 | 1 |
| `xiaoyuzhou.episodes` | LIVE_VERIFIED | DIRECT_PARTIAL_CONTENT | 1 | 1 |
