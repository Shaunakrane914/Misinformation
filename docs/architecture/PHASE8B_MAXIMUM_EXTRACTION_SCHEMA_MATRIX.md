# Phase 8B maximum extraction schema matrix — working assessment

**Gate: PARTIAL (2026-10-12).** This is a measured checkpoint, not a claim
that every possible public field or page has been extracted. The
[Phase 8A live records](../../artifacts/phase8_live_acquisition/2026-10-12_11-06-45Z/)
prove connection and content depth. The
[Stage 8B spot-checks](../../artifacts/phase8_extraction_spotchecks/2026-10-12_17-09-44Z/)
prove the changed GitHub/RSS paths with live traffic. The
[`richness_summary.json`](../../artifacts/phase8_extraction_spotchecks/2026-10-12_17-14-36Z/richness_summary.json)
measures normalized samples across all 16 operations; it cannot infer which
unretained raw fields the provider offered. Candidate fields below are an
extraction contract backlog, **not** a verified promise from providers.

Field states: **captured** = implementation maps the field and a fixture or live
sample exercises it; **conditional** = code maps it but no live population is
proved for every target; **missing** = known adapter/normalizer omission;
**restricted/unverified** = access or provider behavior not established.
An empty value must remain empty; no fabricated dates, counts, authors or text.

| Operation | Captured or conditional normalized fields | Missing / additional request / restriction |
|---|---|---|
| `github.read` | Repository name, URL, owner, description, updated time, stars/forks/watchers, language, topics; README text/path/SHA/source URL when Contents API includes inline base64. | Branch/tree/source files, contributors and full repository history require separate requests. README alone is `PARTIAL_CONTENT`, never a whole-repo reading. Contents API absence/oversize leaves metadata only. |
| `github.issues` | First-page title, body, author, created time, issue URL. | Labels, state, assignees, comments, update/close chronology and further pages are not normalized; comments require follow-up. |
| `github.prs` | First-page title, body, author, created time, PR URL. | Merge status, review/commit/file diffs, discussion, update chronology and further pages need separate mapping/requests. |
| `github.commits` | First-page message, author, author date, commit URL. | Commit file patches, parent topology, verification/signature and more pages need follow-up; message is metadata, not code evidence. |
| `github.releases` | First-page tag/name, release body, author, publication time, URL. | Asset checksums, binaries, prerelease/draft status and further pages are not normalized. |
| `youtube.read` | Video title, channel, description; ID, channel ID, observed upload date, duration, available view/like/comment counts, tags, categories, availability/live status in metadata. | Captions, audio and semantic video content are separate operations; some counters or dates may be missing; metadata field population after this change needs a new live spot-check. |
| `youtube.transcript` | Caption file text where yt-dlp can retrieve it. | Segment timing, language, auto/manual caption identity and multiple tracks are not structured; transcript availability varies. No audio inference. |
| `youtube.comments` | Bounded top-comment text, author, ID, likes and observed timestamp where present. | Replies, continuation/pagination, moderation context and total-discussion coverage are missing. Relative time is not converted into a fabricated date. |
| `v2ex.latest` | Latest first-page topic title, body when present, author, ID, node, created epoch, replies, URL. | Edited time, last reply, related links and complete chronology not normalized; endpoint list is bounded. |
| `v2ex.search` | Public node lookup topic fields as above. | This is **node lookup**, not arbitrary full-text search; no general text-search claim or pagination. |
| `v2ex.topic` | Explicit topic ID, title, body when present, author, node, created epoch, replies, URL. | Replies require `v2ex.replies`; edits and related links not normalized. |
| `v2ex.replies` | Explicit topic reply text, author, ID, created epoch and URL/parent context where provider supplies it. | Complete discussion pagination and edited/deleted history unverified; chronological sorting contract needs tests. |
| `web.read` | Final URL/transport chain, page title and bounded text (4,000 normalized characters in route). | Canonical URL, author, actual publication/modification dates, headings/tables/citations, corrections, schema.org data and full article extent are missing or unverified. No inferred publication date. |
| `rss.read` | Feed/entry title, link, GUID, observed published/updated dates, author/publisher, categories, summary, content block if provided, enclosure references. | Linked article body is **not** fetched. Feed continuation and completeness vary. Full feed content is `FEED_ENTRY_CONTENT`, still syndicated rather than a direct linked article. |
| `xiaoyuzhou.podcast` | Official public podcast identity, description, author, episode/subscription counts, latest episode date and URL when embedded page data supplies them. | Private analytics, restricted metadata and full episode archive unverified; text search is disclosed external discovery, not direct platform data. |
| `xiaoyuzhou.episodes` | Official public episode title, show notes, date, duration, play/comment counts, audio URL, transcript-availability flag when exposed. | Audio semantics, transcript text, complete pagination, referenced-source extraction and comment discussion not implemented. |

## Measured baseline from retained live records

The summarizer selects the latest record for each operation/scenario pair from
the Phase 8A consolidated probe and the Stage 8B spot-check. There are three
scenarios per operation; edge-case failures are intentionally in the
denominator. Character counts are **normalized relevant text per successful
item**, not raw body size or a completeness percentage.

| Operation | Live success / probes | Mean chars / successful item | Median probe latency, ms | Observed depth |
|---|---:|---:|---:|---|
| `github.read` | 2/3 | 25,476 | 885 | Partial README content |
| `github.issues` | 2/3 | 1,972 | 1,343 | Issue body |
| `github.prs` | 2/3 | 1,263 | 1,649 | PR body |
| `github.commits` | 2/3 | 281 | 731 | Metadata |
| `github.releases` | 1/3 | 1,129 | 820 | Release notes |
| `youtube.read` | 2/3 | 1,400 | 2,357 | Video metadata |
| `youtube.transcript` | 2/3 | 2,228 | 4,520 | Caption file |
| `youtube.comments` | 2/3 | 80 | 5,313 | Bounded comment sample |
| `v2ex.latest` | 3/3 | 362 | 806 | Mixed topic body/snippet |
| `v2ex.search` | 2/3 | 494 | 607 | Node topic body/snippet |
| `v2ex.topic` | 2/3 | 896 | 307 | Mixed topic body/snippet |
| `v2ex.replies` | 2/3 | 81 | 675 | Reply body |
| `web.read` | 2/3 | 4,000 | 449 | Capped page text |
| `rss.read` | 2/3 | 669 | 245 | Summary or full **feed entry** |
| `xiaoyuzhou.podcast` | 2/3 | 150 | 2,149 | Podcast metadata |
| `xiaoyuzhou.episodes` | 1/3 | 953 | 2,057 | Bounded episode notes |

The [later video spot-check](../../artifacts/phase8_extraction_spotchecks/2026-10-12_17-14-36Z/)
observed video ID, channel ID, publication date, duration, view/like/comment
counts, tags/categories and availability fields on one public video. This is
one target, not a platform-wide field guarantee. The machine summary is
authoritative for numeric values. Sample source timestamps and attribution
population in the old Phase 8A probe reflect pre-8B normalization; new
post-change metrics are required before claiming date-completeness gains.

## Current gate blockers

1. Probe artifacts retain normalized excerpts and transport hashes, not raw
   JSON field-presence maps. Therefore provider-field theoretical/observed/
   missing classification is incomplete for most operations. A bounded,
   redacted field-presence audit is required before `PASS`.
2. Collection routes mostly stop at a first page; continuation and marginal
   request cost have not been measured.
3. Web article structure, transcript timing, reply chronology, and source
   references remain unextracted. These affect misinformation analysis.
4. Field-population fixtures and live verification must be extended across
   all 16 operations. The current normalized-sample metric is not a substitute
   for important-field success per source type.

Do not start Phase 8C on the assumption that these contracts are complete.
