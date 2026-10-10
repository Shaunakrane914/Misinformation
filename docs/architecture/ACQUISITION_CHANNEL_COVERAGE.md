# Acquisition channel coverage matrix

This file describes the upstream declaration catalogue. It is not an executable
support claim. The authoritative current audit is
`docs/architecture/PRE_PHASE7_READINESS_REPORT.md`, and the machine-readable
per-operation evidence is in the latest timestamped
`artifacts/pre_phase7_audit/` run. Runtime capability responses now expose
`declared_operations` separately from executable `operations`; registration,
credentials, and a provider declaration do not prove meaningful acquisition.

| Channel | Operations | Auth mode | Primary / fallback | Offline expectation | Runtime status |
|---|---|---|---|---|---|
| web | read | none | Jina Reader | safe public read path | capability-gated |
| web_search | search | none | Exa / Bing / DuckDuckGo | discovery, no fabricated result | search-discovery-backed |
| github | search, read, issues, PRs, releases, commits | none | gh CLI / REST | REST fallback is explicit | implemented |
| youtube | search, read, transcript, comments | none | yt-dlp / OpenCLI / Whisper | degraded fallback is explicit | implemented |
| bilibili | search, read, hot, rank | none | public API / bili-cli | empty or degraded is valid | capability-gated |
| v2ex | hot, latest, search, topic, replies | none | public API | empty result is valid | implemented |
| rss | read | none | feedparser | legacy news fallback is explicit | implemented |
| twitter | search, read, status, profile, feed | none | FxTwitter / search index | zero-auth mirror then indexed fallback | implemented |
| reddit | search, read, comments | none | Arctic Shift / search index | zero-auth mirror then indexed fallback | implemented |
| xueqiu | search, quotes, hot posts/stocks | cookie_required | OpenCLI / API | AUTH_REQUIRED without cookie | credential-gated |
| linkedin | profile, company, jobs, read | session_required | LinkedIn MCP / Jina | AUTH_REQUIRED without session | credential-gated |
| xiaohongshu | search, read, comments, feed | session_required | OpenCLI / XHS MCP | AUTH_REQUIRED without session | credential-gated |
| facebook | search, profile, feed, groups | session_required | OpenCLI | AUTH_REQUIRED without session | credential-gated |
| instagram | search, profile, posts, explore | session_required | OpenCLI | AUTH_REQUIRED without session | credential-gated |
| boss | search jobs, read JD | browser_cdp | boss CLI | AUTH_REQUIRED without CDP | credential-gated |
| xiaoyuzhou | transcribe | api_key | Groq Whisper / ffmpeg | explicit unavailable state without key | credential-gated |

The declaration contract test is `tests/unit/test_acquisition_channel_contracts.py`.
It validates catalogue integrity and deterministic routing with controlled
fixtures. It does not prove live availability. The pre-Phase-7 audit found 37
declared operations with no production execution path and five routable operations
not exercised in its bounded live run; these remain unsupported or unverified,
not green.

## Runtime responsibility map

| Component | Responsibility |
|---|---|
| `NativeRouter` | Thin query entry point; safe reads, shared search helpers, and Policy D coordination |
| `ChannelQueryDispatcher` | Social/standard selection, shared telemetry, latency, error conversion, provenance defaults |
| `StandardChannelHandlers` | GitHub, YouTube, feeds, web, reader, generic discovery, auth guards, deterministic fallbacks |
| `SocialChannelHandlers` | Reddit/X direct input, URL discovery, public mirrors, indexed fallback |
| `NativeExecutor` and adapters | Allowlisted platform I/O and backend-specific acquisition |
| `NativeNormalizer` | Conversion of upstream payloads into `EvidenceFragment` records |
| URL validator | Fail-closed SSRF checks before web reads |

`web` advertises the canonical read capability, which is served by
`execute_channel_read()`. Its query route remains as a backward-compatible search
entry point. Credential-gated channels do not fabricate evidence: without the
required environment value they return `AUTH_REQUIRED`; where no deterministic
native acquisition is implemented, passing the guard still yields an empty result.
