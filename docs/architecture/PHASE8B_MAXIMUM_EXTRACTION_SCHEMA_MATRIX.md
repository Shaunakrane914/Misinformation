# Phase 8B maximum extraction schema matrix — working assessment

**Gate: PARTIAL (2026-10-13).** This is a measured checkpoint, not a claim
that every possible public field or page has been extracted. The
[clean-commit 48-scenario re-probe](../../artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/)
on 2026-10-13 yielded an 8A connectivity gate `PASS` for all 16 operations;
its [v12 richness summary](../../artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/richness_summary_v12.json)
remains a bounded sample, not Stage 8B field completeness. The
[Phase 8A live records](../../artifacts/phase8_live_acquisition/2026-10-12_11-06-45Z/)
prove connection and content depth. The
[guarded Stage 8B spot-checks](../../artifacts/phase8_extraction_spotchecks/README.md)
prove the changed paths with live traffic from the isolated checkout. Earlier
spot-checks loaded the editable-installed outer checkout and are retained but
**not** used as isolated-branch proof. The
[`richness_summary_v11.json`](../../artifacts/phase8_extraction_spotchecks/2026-10-13_04-08-03Z/richness_summary_v11.json)
measures normalized samples and bounded parsed adapter-item key names across
all 16 operations; it cannot infer a complete raw provider schema. The 17:37Z
guarded live pass sampled one common target per operation, with 16/16 returning
classified output. Its `web.read` text was later found to be compressed bytes
misread as UTF-8 and is **not valid content proof**. The corrected
[2026-10-13 common-case run](../../artifacts/phase8_extraction_spotchecks/2026-10-13_02-53-55Z/)
sampled all 16 again; separate
[web follow-up](../../artifacts/phase8_extraction_spotchecks/2026-10-13_02-55-36Z/)
confirmed readable common/high-content excerpts with title and headings. Later
[GitHub probes](../../artifacts/phase8_extraction_spotchecks/README.md)
exposed a filtered-page false `NOT_FOUND` label and tested bounded overfetch.
None of these
is proof of difficult-case or pagination completeness. Candidate fields below are an
extraction contract backlog, **not** a verified promise from providers.

Field states: **captured** = implementation maps the field and a fixture or live
sample exercises it; **conditional** = code maps it but no live population is
proved for every target; **missing** = known adapter/normalizer omission;
**restricted/unverified** = access or provider behavior not established.
An empty value must remain empty; no fabricated dates, counts, authors or text.

| Operation | Captured or conditional normalized fields | Missing / additional request / restriction |
|---|---|---|
| `github.read` | Repository name, URL, observed owner identity, description, updated time, stars/forks/watchers, language, topics; README text/path/SHA/source URL when Contents API includes inline base64. Owner and last-update timestamp are **not** presented as README author/publication date. | Branch/tree/source files, contributors and full repository history require separate requests. README alone is `PARTIAL_CONTENT`, never a whole-repo reading. Contents API absence/oversize leaves metadata only. |
| `github.issues` | Title/body, observed author and creation time, URL; number, state/reason, labels, assignees, comment count, update/close times and author association retained. Explicit page 1–5 is bounded; `Link: rel=next` observed. A bounded ten-entry provider page is requested for small limits to compensate for PR filtering; returned issues remain capped at the requested limit. An opt-in `include_comments=True` follows at most two nonempty issue discussions, requests at most five comments each, and retains source-linked author/date/body samples capped at 1,000 characters per comment; one live comment was observed again on [clean commit `2530ae8`](../../artifacts/phase8_issue_comment_probes/2026-10-13_14-23-15Z/summary.json). | Comment follow-up is off by default; events, further pages, full comment bodies, and complete discussion chronology remain missing. A filtered issue page can still be empty with later pages available. The 03:53Z HTTP-200/zero-issue result was incorrectly labeled `NOT_FOUND`; the classifier now uses `EMPTY_RESULT` for such non-missing targets. No complete-history claim. |
| `github.prs` | Title/body, author, created time, URL; number, state, merged time, draft flag, base/head refs, comments and update/close times retained. Explicit page 1–5 is bounded. | Review/commit/file diffs and discussion need separate requests; list response alone cannot prove merge integrity. |
| `github.commits` | Message, author/date, URL; SHA, parent SHAs, committer name/date and API verification status retained. Explicit page 1–5 is bounded. | File patches and complete topology need follow-up; verification field is provider-reported, not an independent signature audit. Message is metadata, not code evidence. |
| `github.releases` | Tag/name, release body, observed author/publication time, URL; draft/prerelease status and bounded asset name/URL/size/content type, provider-supplied digest when present, download count and asset dates retained. Explicit page 1–5 is bounded. | Provider-supplied digest is **not** an independent binary verification; asset bytes are not acquired. Release notes are `PARTIAL_CONTENT` and do not prove installed software behavior. A record creation time is not substituted for missing publication time. |
| `youtube.read` | Video title, channel when present, description; ID, channel ID, observed upload date, duration, available view/like/comment counts, tags, categories, availability/live status in metadata. The 04:08Z common-case re-probe returned observed video metadata. | Captions, audio and semantic video content are separate operations; missing title/channel/counts stay absent. No generic HTML fallback can turn an inaccessible video into an article. One live target does not prove optional-field completeness. |
| `youtube.transcript` | Caption file text, up to 500 observed timed cues and filename language where yt-dlp can retrieve them; cue fixtures and a live English-caption sample exercised this path. | Auto/manual caption origin remains `UNVERIFIED`; only one bounded selected file is retained, not multiple tracks. Availability varies. No audio inference. |
| `youtube.comments` | Bounded top-comment text, author, ID, likes and observed timestamp where present. Missing author/likes remain absent; a comment ID is not misused as a video ID. | Replies, continuation/pagination, moderation context and total-discussion coverage are missing. Relative time is not converted into a fabricated date. |
| `v2ex.latest` | Latest first-page topic title, body when present, author, ID, node, created epoch, replies, URL; observed edit/last-touch/last-reply fields retained. | Related links and complete chronology not normalized; endpoint list is bounded. |
| `v2ex.search` | Public node lookup topic fields as above. | This is **node lookup**, not arbitrary full-text search; no general text-search claim or pagination. |
| `v2ex.topic` | Explicit topic ID, title, body when present, author, node, created epoch, replies, URL. | Replies require `v2ex.replies`; edits and related links not normalized. |
| `v2ex.replies` | Explicit topic reply text, author, reply ID, topic ID, created epoch, observed last-modified and thanks fields. Sampled replies are sorted by observed creation epoch; fixture verifies reply IDs are never mistaken for topic URLs. | Complete discussion pagination and deleted history unverified; missing timestamps retain original sample order. |
| `web.read` | Observed final endpoint, page title, explicitly declared author/publication/modification metadata, headings, bounded article/main links, table cells, quotations, media captions, potential correction notices and selected JSON-LD declaration fields when present. Page text is capped at 4,000 normalized characters in the route. Publisher-declared canonical/JSON-LD fields and linked URLs are **unverified**; links are not followed automatically. | The two new live pages populated observed links (2/2) and selected declared structured data (1/2); tables, quotations, captions and correction notices were absent (0/2), though fixtures exercise extraction. Full article extent, source-link credibility and correction authenticity remain unverified. The tested pages did not expose an observed author/publication date. Pre-fix common-page text was invalid compressed-byte gibberish and is superseded. |
| `rss.read` | Feed/entry title, link, GUID, observed published/updated dates, distinct entry author and feed publisher, categories, summary, content block if provided, enclosure references. | Linked article body is **not** fetched. Feed continuation and completeness vary. Full feed content is `FEED_ENTRY_CONTENT`, still syndicated rather than a direct linked article. A title-only feed entry is `METADATA`, not a syndicated summary. |
| `xiaoyuzhou.podcast` | Official public podcast identity, description, author, episode/subscription counts, latest episode date and URL when embedded page data supplies them. | Private analytics, restricted metadata and full episode archive unverified; text search is disclosed external discovery, not direct platform data. |
| `xiaoyuzhou.episodes` | Official public episode title, show notes, date, duration, play/comment counts, audio URL, transcript-availability flag when exposed. Absent show notes leave the item at metadata depth, with no generic title, podcast name or URL invented. | Audio semantics, transcript text, complete pagination, referenced-source extraction and comment discussion not implemented. |

## Provider-documentation boundaries

- [GitHub's issue-list documentation](https://docs.github.com/en/rest/issues/issues)
  says the list can include PRs; a zero result **after Aegis filters PRs** is
  an empty sampled page, not proof of absence. GitHub's
  [pagination documentation](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
  explains the `Link` continuation header. These sources support explicit
  bounded page access, not a claim that Aegis has fetched all pages.
- [GitHub's issue-comment documentation](https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28)
  documents public issue-comment listing, issue-number targeting and
  pagination. The optional Aegis follow-up observes only a capped first page;
  an absent continuation header is not independent proof that discussion or
  deleted history is complete.
- [GitHub release documentation](https://docs.github.com/en/rest/releases/releases)
  includes asset metadata and an optional provider-supplied digest in example
  responses. Aegis retains that string when observed; it has not downloaded
  the asset or independently checked its bytes. PR files/reviews and commit
  file patches are separate documented API reads, not implied by list bodies.
- [YouTube's video API documentation](https://developers.google.com/youtube/v3/docs/videos/list)
  describes metadata parts accessible via its authenticated/API-key interface;
  it is not evidence that Aegis's current public `yt-dlp` path returns every
  such field. Official
  [caption-list/download guidance](https://developers.google.com/youtube/v3/guides/implementation/captions)
  requires OAuth for those methods. Aegis does not bypass that requirement.
  [YouTube comment-thread documentation](https://developers.google.com/youtube/v3/docs/commentThreads)
  states that embedded replies may be incomplete, so current top-comment
  samples cannot represent a complete discussion.

## Measured baseline from retained live records

The summarizer selects the latest record for each operation/scenario pair from
the Phase 8A consolidated probe, the corrected 16-operation spot-check and the
newest web follow-up. There are three
scenarios per operation; edge-case failures are intentionally in the
denominator. Character counts are **normalized relevant text per successful
item**, not raw body size or a completeness percentage.

| Operation | Live success / probes | Mean chars / successful item | Median probe latency, ms | Observed depth |
|---|---:|---:|---:|---|
| `github.read` | 2/3 | 21,038 | 3,364 | Partial README content |
| `github.issues` | 2/3 | 2,429 | 2,242 | Partial issue body; no comments |
| `github.prs` | 2/3 | 8,862 | 1,649 | Partial PR body; no reviews/files |
| `github.commits` | 2/3 | 304 | 731 | Metadata |
| `github.releases` | 1/3 | 1,129 | 820 | Partial release notes |
| `youtube.read` | 2/3 | 1,400 | 2,357 | Video metadata |
| `youtube.transcript` | 2/3 | 2,228 | 4,520 | Caption file |
| `youtube.comments` | 2/3 | 95 | 5,438 | Bounded comment sample |
| `v2ex.latest` | 3/3 | 298 | 520 | Mixed topic body/snippet |
| `v2ex.search` | 2/3 | 494 | 492 | Node topic body/snippet |
| `v2ex.topic` | 2/3 | 896 | 223 | Mixed topic body/snippet |
| `v2ex.replies` | 2/3 | 66 | 675 | Reply body |
| `web.read` | 2/3 | 4,000 | 929 | Capped page text |
| `rss.read` | 2/3 | 250 | 290 | Summary or full **feed entry** |
| `xiaoyuzhou.podcast` | 2/3 | 150 | 1,597 | Podcast metadata |
| `xiaoyuzhou.episodes` | 1/3 | 953 | 2,057 | Bounded episode notes |

The [guarded video spot-check](../../artifacts/phase8_extraction_spotchecks/2026-10-12_17-21-49Z/)
observed video ID, channel ID, publication date, duration, view/like/comment
counts, tags/categories and availability fields on one public video. This is
one target, not a platform-wide field guarantee. The machine summary is
authoritative for numeric values. Sample source timestamps and attribution
population in the old Phase 8A probe reflect pre-8B normalization; new
post-change population is measured in v12 below, but two successful scenarios
per operation at most cannot establish date-completeness gains across a provider.

## Current gate blockers

### Clean-commit three-scenario measurement, 2026-10-13

The full re-probe on commit `8dce5412ab7c3ab4de2d1d6239e4f658bb27e756`
produced 30 live-verified results across 48 designed scenarios, including
deliberately inaccessible targets. Every operation had at least one live
result, so the **Stage 8A** gate passed; the fraction is not a production
uptime estimate. The summary below counts an important field as “always
populated” only when it was populated in every *measured successful normalized
sample*. It does not measure unrequested raw provider fields or every possible
target. Missing values stay missing.

| Operation | Live probes / scenarios | Always populated important fields / measured important fields | Mean relevant characters / successful item |
|---|---:|---:|---:|
| `github.read` | 2/3 | 4/5 | 25,476 |
| `github.issues` | 2/3 | 6/6 | 2,423 |
| `github.prs` | 2/3 | 6/6 | 5,993 |
| `github.commits` | 2/3 | 5/5 | 652 |
| `github.releases` | 1/3 | 4/4 | 1,129 |
| `youtube.read` | 2/3 | 5/5 | 1,401 |
| `youtube.transcript` | 1/3 | 4/4 | 4,017 |
| `youtube.comments` | 2/3 | 4/4 | 47 |
| `v2ex.latest` | 3/3 | 5/5 | 182 |
| `v2ex.search` | 2/3 | 5/5 | 278 |
| `v2ex.topic` | 2/3 | 5/5 | 866 |
| `v2ex.replies` | 2/3 | 5/5 | 48 |
| `web.read` | 2/3 | 6/11 | 4,000 (route cap) |
| `rss.read` | 2/3 | 5/5 | 1,075 |
| `xiaoyuzhou.podcast` | 2/3 | 4/4 | 143 |
| `xiaoyuzhou.episodes` | 1/3 | 5/5 | 975 |

One public video lacked an accessible transcript, a selected repository had
no release result, and a sparse podcast-episode target had a network failure.
Those observed limitations are retained, not filled with synthetic content.
The `github.read` author gap is appropriate: repository ownership is not
proof of README authorship. The five sparse web fields are optional on the
two sampled pages. Pagination remains bounded or absent as documented above;
the table does not resolve that blocker.

1. The new field-presence names cover parsed adapter result items, not complete
   provider response schemas. YouTube read/transcript and web have no `items`
   list, so item-key counts are zero even where metadata/cues were observed.
   Theoretical/optional/restricted classification still needs source-specific
   evidence and tests before `PASS`.
2. GitHub permits bounded explicit page 1–5, but continuation completeness
   and marginal request cost are not measured. Other collection routes remain
   first-page or bounded-sample only.
3. Web article links/tables/quotations/captions/possible corrections/selected
   JSON-LD are now bounded observations, but two live pages do not prove field
   coverage or the truth of publisher declarations. Multi-track caption
   context and discussion completeness remain unextracted or unverified.
4. The v6 summary now measures a declared minimum important-field set for all
   16 operations, including populated vs empty vs not observed. This is a
   small live sample and **not** a provider completeness score. Expand fixture
   and difficult-case coverage before claiming Phase 8B `PASS`.

Do not start Phase 8C on the assumption that these contracts are complete.

## Auxiliary direct-adapter truth check — 2026-10-13

The matrix above principally measures the recovered 16-operation dispatcher.
An additional AgentReach direct-adapter path exists for GitHub repositories,
YouTube video metadata, public web reading, and search-index discovery. A
separate normalization audit removed invented zero-star/language/owner fields,
generic YouTube channel/title values, index pseudo-authors, default high
semantic scores, and search-discovery dates promoted into page publication.
The adapters now retain observed owner, update/push, engagement and discovery
date fields as distinct metadata. See the
[direct-adapter regression tests](../../tests/unit/test_phase8_normalization_truth.py).
These are offline fixture checks; no new live success or richer-field coverage
is inferred from them. Stage 8B remains `PARTIAL`.

## Stage 8B Maximum Extraction Depth Extensions — Verified (2026-10-13)

The following extraction depth extensions were implemented and unit-tested in
[`tests/unit/test_phase8b_maximum_extraction_depth.py`](../../tests/unit/test_phase8b_maximum_extraction_depth.py):

1. **GitHub PR File Follow-Up**: `github.prs` route handler accepts opt-in `include_files=True` (bounded to at most 5 files, 500 chars patch excerpt each). File names, statuses (`added`, `modified`, etc.), additions/deletions counts, and truncated patches are normalized into `provider_fields["file_samples"]` and appended to the PR body, upgrading depth to `PARTIAL_CONTENT`.
2. **GitHub Commit File Follow-Up**: `github.commits` route handler supports `include_files=True` on single-commit inspection, extracting total `stats` (additions, deletions, total) and bounded `file_samples` with diff patches.
3. **OpenGraph & Twitter Card Extraction**: `web.read` now extracts `<meta property="og:description">`, `og:site_name`, `og:type`, `<meta name="twitter:creator">`, `twitter:site`, and `article:section`, exposed under `declared_metadata` with truthful `UNVERIFIED_PUBLISHER_DECLARED` pedigree.
4. **YouTube External Description Links**: `youtube.read` regex-extracts external URLs from video descriptions, populated into `provider_fields["description_links"]` labeled `UNVERIFIED_REFERENCED_LINK`.
5. **V2EX Topic & Reply Links**: `v2ex.topic` and `v2ex.replies` extract plaintext and markdown/HTML URLs into `provider_fields["observed_links"]`.
6. **Xiaoyuzhou Show Notes Links**: `xiaoyuzhou.episodes` extracts external URLs from show notes into `provider_fields["observed_links"]` labeled `UNVERIFIED_SHOW_NOTES_LINK`.
7. **RSS Linked Article Follow-Up**: `rss.read` handler supports `follow_linked_article=True`, dispatching a bounded `execute_channel_read` call (subject to SSRF validation and 5s timeout) to retrieve the linked article text up to 4,000 chars, elevating content depth to `FEED_ENTRY_WITH_LINKED_ARTICLE`.

