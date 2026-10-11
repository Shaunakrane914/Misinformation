# Pre-Phase 7 verified capability matrix

- Commit: `f7aa96ff7a3b3ae6c276e9c4b86d8872bc231da8`
- Generated: `2026-10-11T00:56:00.975094+00:00`
- HTTP fields are populated only from adapter-level transport observations.
- `network_io_observed=false` means transport facts remain unknown, even when normalized fragments exist.

| Channel | Operation | Outcome | Health | Items | Network observed | HTTP |
|---|---|---|---|---:|---|---|
| web | search | SEARCH_INDEX_DISCOVERY | DEGRADED | 3 | true | 200 |
| web_search | search | SEARCH_INDEX_DISCOVERY | DEGRADED | 3 | true | 200 |
| web | read | DIRECT_CONTENT | HEALTHY | 1 | true | 200 |
| news | search | SYNDICATED_SUMMARY | LIMITED | 3 | true | 200 |
| rss | search | SYNDICATED_SUMMARY | LIMITED | 3 | true | 200 |
| jina_reader | read | DIRECT_CONTENT | HEALTHY | 1 | true | 200 |
| github | search | PARTIAL_OR_UNCLASSIFIED | DEGRADED | 3 | true | 200 |
| github | read | DIRECT_CONTENT | HEALTHY | 1 | true | 200 |
| github | issues | DIRECT_CONTENT | HEALTHY | 1 | true | 200 |
| github | releases | DIRECT_CONTENT | HEALTHY | 3 | true | 200 |
| youtube | search | DIRECT_METADATA | LIMITED | 3 | true | unknown |
| youtube | read | DIRECT_METADATA | LIMITED | 1 | true | unknown |
| youtube | transcript | DIRECT_CONTENT | HEALTHY | 1 | true | unknown |
| youtube | comments | DIRECT_CONTENT | HEALTHY | 3 | true | unknown |
| v2ex | hot | PARTIAL_OR_UNCLASSIFIED | DEGRADED | 3 | true | 200 |
| v2ex | latest | DIRECT_CONTENT | HEALTHY | 3 | true | 200 |
| v2ex | topic | DIRECT_CONTENT | HEALTHY | 1 | true | 200 |
| v2ex | replies | DIRECT_CONTENT | HEALTHY | 3 | true | 200 |
| bilibili | search | DIRECT_METADATA | LIMITED | 3 | true | 200 |
| twitter | profile | DIRECT_METADATA | LIMITED | 1 | true | 200 |
| twitter | status | DIRECT_CONTENT | HEALTHY | 1 | true | 200 |
| reddit | search | BLOCKED | BLOCKED | 0 | false | unknown |
| reddit | comments | BLOCKED | BLOCKED | 0 | false | unknown |
| linkedin | jobs | PARTIAL_OR_UNCLASSIFIED | DEGRADED | 3 | true | 200 |
| xueqiu | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| xiaohongshu | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| instagram | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| facebook | search | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| boss | search_jobs | AUTH_REQUIRED | BLOCKED | 0 | false | unknown |
| xiaoyuzhou | podcast | PARTIAL_OR_UNCLASSIFIED | DEGRADED | 3 | true | 200 |
