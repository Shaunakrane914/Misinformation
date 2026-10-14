# Phase 7 protected integration matrix

All routes retain `NativeRouter → ChannelQueryDispatcher → StandardChannelHandlers → NativeExecutor/adapter → normalizer`. Phase 7 changed transport safety and request validation, not the public route contract.

| # | Operation | Pre/Post execution target | Contract evidence | Bounded live status (2026-10-11) | Compatibility |
|---:|---|---|---|---|---|
| 1 | `github.read` | `execute_github_rest_operation` | recovered-route + request-construction tests | Direct content, HTTP 200 | Preserved |
| 2 | `github.issues` | same | same | Direct content, HTTP 200 | Preserved |
| 3 | `github.prs` | same | recovered-route + endpoint mapping tests | Not live-probed; contract verified | Preserved |
| 4 | `github.commits` | same | recovered-route + endpoint mapping tests | Not live-probed; contract verified | Preserved |
| 5 | `github.releases` | same | recovered-route + request-construction tests | Direct content, HTTP 200 | Preserved |
| 6 | `youtube.read` | `execute_youtube_read` | recovered-route tests | Direct metadata; external-tool HTTP unknown | Preserved |
| 7 | `youtube.transcript` | `execute_youtube_transcript` | recovered-route tests | Direct content; external-tool HTTP unknown | Preserved |
| 8 | `youtube.comments` | `execute_youtube_comments` | recovered-route tests | Direct content; external-tool HTTP unknown | Preserved |
| 9 | `v2ex.latest` | `execute_v2ex_operation` | recovered-route + exact URL tests | Direct content, HTTP 200 | Preserved |
| 10 | `v2ex.search` | `execute_v2ex_search` | recovered-route + URL-encoding test | Not live-probed; contract verified | Preserved |
| 11 | `v2ex.topic` | `execute_v2ex_operation` | recovered-route + exact ID test | Direct content, HTTP 200 | Preserved; parser fixed |
| 12 | `v2ex.replies` | `execute_v2ex_operation` | recovered-route + exact ID test | Direct content, HTTP 200 | Preserved |
| 13 | `web.read` | bounded native reader, browser rescue, Jina fallback | provenance + transport/security tests | Direct content, HTTP 200 | Preserved; provenance fixed |
| 14 | `rss.read` | `execute_rss_read` | recovered-route + RSS transport tests | Exact operation not live-probed; same executor observed HTTP 200 through `rss.search` | Preserved |
| 15 | `xiaoyuzhou.podcast` | iTunes discovery + bounded RSS fetch | recovered-route + feed tests | Evidence returned, HTTP 200; partial/unclassified | Preserved |
| 16 | `xiaoyuzhou.episodes` | same public syndication executor | recovered-route tests | Not separately live-probed; contract verified | Preserved |

The bounded run is stored under `artifacts/phase7_live_audit/2026-10-11_07-42-10Z/`. It performed 30 representative probes, recorded adapter facts for 23, and intentionally skipped direct Reddit collection without approved access. “Not live-probed” is not represented as healthy.

