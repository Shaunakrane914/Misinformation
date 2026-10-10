# Pre-Phase 7 verified capability matrix

- Commit: `4d102b2ea11cedb824b8ffa092047ff59b6675ba`
- Generated: `2026-10-10T14:33:35.525074+00:00`
- HTTP fields are populated only from adapter-level transport observations.
- `network_io_observed=false` means transport facts remain unknown, even when normalized fragments exist.

| Channel | Operation | Outcome | Health | Items | Network observed | HTTP |
|---|---|---|---|---:|---|---|
| web | search | SEARCH_INDEX_DISCOVERY | DEGRADED | 3 | true | 200 |
| news | search | SYNDICATED_SUMMARY | LIMITED | 3 | true | 200 |
| rss | search | SYNDICATED_SUMMARY | LIMITED | 3 | true | 200 |
| jina_reader | read | DIRECT_CONTENT | HEALTHY | 1 | true | 200 |
| github | search | PARTIAL_OR_UNCLASSIFIED | DEGRADED | 3 | true | 200 |
| youtube | search | DIRECT_METADATA | LIMITED | 3 | true | unknown |
| v2ex | hot | PARTIAL_OR_UNCLASSIFIED | DEGRADED | 3 | true | 200 |
| bilibili | search | DIRECT_METADATA | LIMITED | 3 | true | 200 |
| twitter | profile | DIRECT_METADATA | LIMITED | 1 | true | 200 |
| twitter | status | DIRECT_CONTENT | HEALTHY | 1 | true | 200 |
| reddit | search | BLOCKED | BLOCKED | 0 | false | unknown |
| reddit | comments | BLOCKED | BLOCKED | 0 | false | unknown |
| linkedin | jobs | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| xueqiu | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| xiaohongshu | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| instagram | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| facebook | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| boss | search_jobs | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| xiaoyuzhou | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| web_search | search | EMPTY | DEGRADED | 0 | false | unknown |
