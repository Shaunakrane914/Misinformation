# Phase 8A real acquisition verification

**Decision:** `PASS` for the Real Acquisition Proof gate on 2026-10-12.

This pass means each of the 16 protected operations independently produced
usable output from observed live provider traffic in at least one bounded probe.
It does **not** mean every target succeeds, every result is full content, or a
provider is continuously available.

The authoritative machine evidence is the consolidated run at
[`artifacts/phase8_live_acquisition/2026-10-12_11-06-45Z`](../../artifacts/phase8_live_acquisition/2026-10-12_11-06-45Z/).
It selects the latest complete probe set per operation from the post-fix runs
listed in `run_metadata.json`.

## Verified capability matrix

| Operation | Live depth proved | Important boundary |
|---|---|---|
| `github.read` | `DIRECT_METADATA` | Repository and owner metadata observed; README content was not consistently obtained. |
| `github.issues` | `DIRECT_FULL_CONTENT` | Bounded first-page issue bodies; pull requests excluded. |
| `github.prs` | `DIRECT_FULL_CONTENT` | Bounded first-page pull-request bodies. |
| `github.commits` | `DIRECT_METADATA` | Commit messages/author/time are records, not repository source-code understanding. |
| `github.releases` | `DIRECT_FULL_CONTENT` | Release notes when present; repositories may legitimately have no releases. |
| `youtube.read` | `DIRECT_METADATA` | Title/channel/description only; unavailable videos no longer fall through to HTML. |
| `youtube.transcript` | `DIRECT_FULL_CONTENT` | Caption text where available; absence is `NOT_FOUND`, not invented transcript. |
| `youtube.comments` | `DIRECT_FULL_CONTENT` | Bounded top-comment sample, not the complete discussion. |
| `v2ex.latest` | `DIRECT_PARTIAL_CONTENT` | Latest-topic records; body population varies. |
| `v2ex.search` | `DIRECT_FULL_CONTENT` / `DIRECT_PARTIAL_CONTENT` | Public node lookup, not arbitrary full-text search. |
| `v2ex.topic` | `DIRECT_FULL_CONTENT` / `DIRECT_PARTIAL_CONTENT` | Explicit topic IDs; body availability varies. |
| `v2ex.replies` | `DIRECT_FULL_CONTENT` | Bounded reply records for explicit topic IDs. |
| `web.read` | `DIRECT_PARTIAL_CONTENT` | Text is deliberately capped at 4,000 normalized characters in this route. |
| `rss.read` | `SYNDICATED_SUMMARY` | Feed entries are not promoted to linked full articles. |
| `xiaoyuzhou.podcast` | `DIRECT_METADATA` | Official public Xiaoyuzhou page/ID only. |
| `xiaoyuzhou.episodes` | `DIRECT_PARTIAL_CONTENT` | Official public episode metadata and show notes; no claim of audio understanding. |

Auxiliary discovery operations were sampled separately: `web.search` returned
`SEARCH_DISCOVERY_ONLY`, `rss.search` returned `SYNDICATED_SUMMARY`, and GitHub
and YouTube search returned metadata. They are not counted among the 16.

## Defects found and corrected

1. An unavailable YouTube video fell through to the generic web reader and its
   error page could be labeled video metadata. Recognized YouTube URLs now fail
   closed at the specialist adapter.
2. Empty provider results lost transport proof because telemetry was derived
   only from normalized fragments. Provider observations now survive empty and
   failed normalization paths.
3. Truncated web reads were labeled full articles. The handler now compares the
   source character count with the returned bounded content.
4. GitHub commits were classified as full articles. They are now direct
   metadata records.
5. A generic Apple Podcast search was mislabeled as Xiaoyuzhou acquisition and
   returned Ximalaya content. Direct Xiaoyuzhou operations now require an
   official public URL/ID and parse the page's public structured data. Generic
   search is a disclosed web-index discovery fallback.
6. HTTP redirect chains and bounded raw-body SHA-256 proofs were missing.
   Successful bounded HTTP records now preserve both without storing bodies.
7. GitHub unauthenticated quota exhaustion returned HTTP 403 and looked like a
   policy denial. Rate-limit headers now propagate and a zero remaining quota
   is classified `RATE_LIMITED`.

## Negative evidence and limitations

- Intermediate runs are intentionally retained. They show the false-positive
  classifications that caused the fixes and a real unauthenticated GitHub rate
  limit. The artifact README identifies their chronology.
- No provider credentials were used (`GITHUB_TOKEN`, `YOUTUBE_API_KEY` and
  `GROQ_API_KEY` were absent). No CAPTCHA, authentication or policy restriction
  was bypassed.
- The audit retains bounded normalized excerpts plus raw byte counts/hashes,
  not complete copyrighted response bodies.
- Redirects are observable only for the shared HTTP transport. External tools
  such as `yt-dlp` do not expose an HTTP redirect chain through the current
  contract.
- Live verification is time-bound. Runtime health must age and revalidate; this
  report is not a permanent always-green provider badge.

## Gate interpretation

Stage 8B may begin because every protected operation has a truthful live status
and at least one successful live acquisition proof. Stage 8B must still measure
field completeness, pagination and extraction loss; Stage 8A does not establish
maximum extraction.
