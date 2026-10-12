# Phase 8B maximum extraction schema matrix — working assessment

**Gate: PARTIAL (2026-10-12).** This is a measured checkpoint, not a claim
that every possible public field or page has been extracted. The
[Phase 8A live records](../../artifacts/phase8_live_acquisition/2026-10-12_11-06-45Z/)
prove connection and content depth. The
[guarded Stage 8B spot-checks](../../artifacts/phase8_extraction_spotchecks/README.md)
prove the changed paths with live traffic from the isolated checkout. Earlier
spot-checks loaded the editable-installed outer checkout and are retained but
**not** used as isolated-branch proof. The
[`richness_summary_v3.json`](../../artifacts/phase8_extraction_spotchecks/2026-10-12_17-37-38Z/richness_summary_v3.json)
measures normalized samples and bounded parsed adapter-item key names across
all 16 operations; it cannot infer a complete raw provider schema. The 17:37Z
guarded live pass sampled one common target per operation, with 16/16 returning
classified usable output. It is not proof of difficult-case or pagination
completeness. Candidate fields below are an
extraction contract backlog, **not** a verified promise from providers.

Field states: **captured** = implementation maps the field and a fixture or live
sample exercises it; **conditional** = code maps it but no live population is
proved for every target; **missing** = known adapter/normalizer omission;
**restricted/unverified** = access or provider behavior not established.
An empty value must remain empty; no fabricated dates, counts, authors or text.

| Operation | Captured or conditional normalized fields | Missing / additional request / restriction |
|---|---|---|
| `github.read` | Repository name, URL, owner, description, updated time, stars/forks/watchers, language, topics; README text/path/SHA/source URL when Contents API includes inline base64. | Branch/tree/source files, contributors and full repository history require separate requests. README alone is `PARTIAL_CONTENT`, never a whole-repo reading. Contents API absence/oversize leaves metadata only. |
| `github.issues` | Title/body, author, created time, URL; observed number, state/reason, labels, assignees, comment count, update/close times and author association are retained as provider fields. Explicit page 1–5 is bounded; `Link: rel=next` is observed. | Comment bodies/events require follow-up; a filtered page may contain fewer issues than `per_page` because GitHub's issues endpoint also lists PRs. No automatic complete-history claim. |
| `github.prs` | Title/body, author, created time, URL; number, state, merged time, draft flag, base/head refs, comments and update/close times retained. Explicit page 1–5 is bounded. | Review/commit/file diffs and discussion need separate requests; list response alone cannot prove merge integrity. |
| `github.commits` | Message, author/date, URL; SHA, parent SHAs, committer name/date and API verification status retained. Explicit page 1–5 is bounded. | File patches and complete topology need follow-up; verification field is provider-reported, not an independent signature audit. Message is metadata, not code evidence. |
| `github.releases` | Tag/name, release body, author, publication time, URL; draft/prerelease status and bounded asset name/URL/size/content type retained. Explicit page 1–5 is bounded. | Asset checksums/binary contents are not acquired; release notes do not prove installed software behavior. |
| `youtube.read` | Video title, channel, description; ID, channel ID, observed upload date, duration, available view/like/comment counts, tags, categories, availability/live status in metadata. | Captions, audio and semantic video content are separate operations; some counters or dates may be missing; metadata field population after this change needs a new live spot-check. |
| `youtube.transcript` | Caption file text, up to 500 observed timed cues and filename language where yt-dlp can retrieve them; cue fixtures and a live English-caption sample exercised this path. | Auto/manual caption origin remains `UNVERIFIED`; only one bounded selected file is retained, not multiple tracks. Availability varies. No audio inference. |
| `youtube.comments` | Bounded top-comment text, author, ID, likes and observed timestamp where present. | Replies, continuation/pagination, moderation context and total-discussion coverage are missing. Relative time is not converted into a fabricated date. |
| `v2ex.latest` | Latest first-page topic title, body when present, author, ID, node, created epoch, replies, URL; observed edit/last-touch/last-reply fields retained. | Related links and complete chronology not normalized; endpoint list is bounded. |
| `v2ex.search` | Public node lookup topic fields as above. | This is **node lookup**, not arbitrary full-text search; no general text-search claim or pagination. |
| `v2ex.topic` | Explicit topic ID, title, body when present, author, node, created epoch, replies, URL. | Replies require `v2ex.replies`; edits and related links not normalized. |
| `v2ex.replies` | Explicit topic reply text, author, reply ID, topic ID, created epoch, observed last-modified and thanks fields. Sampled replies are sorted by observed creation epoch; fixture verifies reply IDs are never mistaken for topic URLs. | Complete discussion pagination and deleted history unverified; missing timestamps retain original sample order. |
| `web.read` | Observed final endpoint, page title, explicitly declared author/publication/modification metadata and headings when present; bounded text (4,000 normalized characters in route). A publisher-declared canonical link is retained as **unverified**, not accepted as source identity. | Tables/citations, corrections, schema.org data and full article extent are missing or unverified. The tested pages did not expose an observed author or publication date; both stayed empty. |
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
| `github.read` | 2/3 | 21,038 | 983 | Partial README content |
| `github.issues` | 2/3 | 2,834 | 621 | Issue body |
| `github.prs` | 2/3 | 1,263 | 1,649 | PR body |
| `github.commits` | 2/3 | 281 | 706 | Metadata |
| `github.releases` | 1/3 | 1,129 | 701 | Release notes |
| `youtube.read` | 2/3 | 1,400 | 2,357 | Video metadata |
| `youtube.transcript` | 2/3 | 2,228 | 4,520 | Caption file |
| `youtube.comments` | 2/3 | 86 | 4,184 | Bounded comment sample |
| `v2ex.latest` | 3/3 | 639 | 496 | Mixed topic body/snippet |
| `v2ex.search` | 2/3 | 494 | 492 | Node topic body/snippet |
| `v2ex.topic` | 2/3 | 896 | 348 | Mixed topic body/snippet |
| `v2ex.replies` | 2/3 | 66 | 675 | Reply body |
| `web.read` | 2/3 | 4,000 | 253 | Capped page text |
| `rss.read` | 2/3 | 253 | 304 | Summary or full **feed entry** |
| `xiaoyuzhou.podcast` | 2/3 | 150 | 1,691 | Podcast metadata |
| `xiaoyuzhou.episodes` | 1/3 | 953 | 2,057 | Bounded episode notes |

The [guarded video spot-check](../../artifacts/phase8_extraction_spotchecks/2026-10-12_17-21-49Z/)
observed video ID, channel ID, publication date, duration, view/like/comment
counts, tags/categories and availability fields on one public video. This is
one target, not a platform-wide field guarantee. The machine summary is
authoritative for numeric values. Sample source timestamps and attribution
population in the old Phase 8A probe reflect pre-8B normalization; new
post-change metrics are required before claiming date-completeness gains.

## Current gate blockers

1. The new field-presence names cover parsed adapter result items, not complete
   provider response schemas. YouTube read/transcript and web have no `items`
   list, so item-key counts are zero even where metadata/cues were observed.
   Theoretical/optional/restricted classification still needs source-specific
   evidence and tests before `PASS`.
2. GitHub permits bounded explicit page 1–5, but continuation completeness
   and marginal request cost are not measured. Other collection routes remain
   first-page or bounded-sample only.
3. Web article tables/citations/corrections/structured data, multi-track
   caption context and discussion completeness remain unextracted or unverified.
4. Important-field population rates, not merely generic title/URL presence,
   need fixture and live evaluation across all 16 operations. The current
   normalized-sample metric is not a completeness score.

Do not start Phase 8C on the assumption that these contracts are complete.
