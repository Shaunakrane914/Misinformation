# Continuous source intelligence review — 2026-10-17

**Overall: PARTIAL. Research-quality acceptance: FAIL. No main merge or deployment.**

This is a dated engineering checkpoint, not completion of Phase 9. Development
branch: `feat/continuous-source-intelligence-20261017`; base
`1669b336ce509e5a789f7f83f2ff647702f9c82f`. Acquisition checkpoints
`e1bf5c4` and `b89daae`; frontend isolation fix `bc67b83`.
[Engineering handoff](../handoffs/2026-10-17_CONTINUOUS_SOURCE_INTELLIGENCE.md),
[durable evidence](evidence/2026-10-17_continuous_source_intelligence/README.md),
[machine-readable measurements](evidence/2026-10-17_continuous_source_intelligence/measurements.json).

## A. Source-by-source improvements

### Method and acceptance boundary

All **52 executable operations** were retained and probed using the existing
configured access context. All **16 protected operations** returned sampled
observations. The final source pass produced 78 observations and 68 bounded
captured samples (maximum two captured samples per operation). Eleven operations
returned none. No access gates were changed. The pre-existing local Reddit flag
was true; that observation is **not independent provider authorization**.

Before measurements are the preceding configured source-text pass; after
measurements are the final stable source pass in this iteration. Target hashes
match for all 52 operations. These are time-separated observations of changing
services, **not controlled causal attribution** to code changes. No improvement
is claimed merely because a comment count or word count increased.

Words are whitespace-delimited; KB is UTF-8 bytes / 1,000 in bounded captured
text, excluding JSON metadata. Chinese whitespace word counts are not linguistic
token counts. Native observation counts, selected sample counts, raw response
bytes and unique relevant bodies are different quantities. Raw and readable
metrics are separate in the JSON; missing dates remain unknown, not “Recent.”

Field inventory below: T title, U URL, A author, D publication date, B captured
body; number is sampled records missing that field. “none” means no missing
fields in that inventory, **not validated field accuracy**. Zero-item rows have
no meaningful completeness assessment.

Every nonempty operation is **PARTIAL**, not whole-source acceptance.
**BLOCKED** identifies explicit access/configuration requirements.
**FAIL** means no observations in this probe without a demonstrated fix.
Every captured inspection was included in a labeled all-four-page display
scaffold, 320/390/1440px: 12 states, zero measured failures. This scaffold is
not proof each operation is selected by each agent in normal research.

| Operation | Readable words before → after | Readable KB before → after | Observed runtime | Acceptance | Missing fields | Actual useful scope and remaining limit |
| --- | ---: | ---: | --- | --- | --- | --- |
| `github.read` | 4749 → 4749 | 42.167 → 42.167 | SUCCESS | PARTIAL | A1, D1 | README body; author/date absent, not repository-wide audit |
| `github.issues` | 710 → 710 | 5.843 → 5.843 | SUCCESS | PARTIAL | none | bounded issue bodies/comments; not all discussions |
| `github.prs` | 97 → 97 | 1.146 → 1.146 | SUCCESS | PARTIAL | none | bounded PR text; not full diff/review |
| `github.commits` | 302 → 302 | 2.897 → 2.897 | SUCCESS | PARTIAL | none | commit messages/metadata; not changed-code analysis |
| `github.releases` | 124 → 124 | 2.651 → 2.651 | SUCCESS | PARTIAL | none | release notes; not independently checked release claims |
| `youtube.read` | 379 → 379 | 2.546 → 2.546 | SUCCESS | PARTIAL | none | video description/metadata, not spoken content |
| `youtube.transcript` | 675 → 675 | 4.263 → 4.263 | SUCCESS | PARTIAL | T1, A1, D1 | captions retained; title/author/date missing; no audiovisual verification |
| `youtube.comments` | 10 → 49 | 0.038 → 0.281 | SUCCESS | PARTIAL | none | two sampled comments, not sentiment population |
| `v2ex.latest` | 79 → 24 | 1.978 → 0.542 | SUCCESS | PARTIAL | none | bounded latest topics; Chinese whitespace undercounts tokens |
| `v2ex.search` | 95 → 95 | 2.065 → 2.065 | SUCCESS | PARTIAL | none | bounded topic results; not exhaustive search |
| `v2ex.topic` | 165 → 165 | 3.622 → 3.622 | SUCCESS | PARTIAL | none | topic text; no independent verification |
| `v2ex.replies` | 19 → 19 | 0.314 → 0.314 | SUCCESS | PARTIAL | none | two replies, not whole conversation |
| `web.read` | 333 → 333 | 2.258 → 2.258 | SUCCESS | PARTIAL | A1, D1 | main/article extraction: 680 raw to 333 readable words; author/date absent |
| `rss.read` | 374 → 376 | 2.523 → 2.523 | SUCCESS | PARTIAL | A2 | feed summaries plus bounded linked-read context; missing authors |
| `xiaoyuzhou.podcast` | 17 → 17 | 0.443 → 0.443 | SUCCESS | PARTIAL | none | podcast metadata, not audio transcript |
| `xiaoyuzhou.episodes` | 116 → 116 | 4.052 → 4.052 | SUCCESS | PARTIAL | none | episode show notes, not audio transcript |
| `reddit.read` | 211 → 210 | 1.273 → 1.264 | SUCCESS | PARTIAL | B1 | old AMA sample plus removed/empty item; not current broad coverage |
| `reddit.comments` | 211 → 4 | 1.273 → 0.021 | SUCCESS | PARTIAL | B1 | four words plus deleted/empty marker; not full thread |
| `twitter.status` | 5 → 5 | 0.024 → 0.024 | SUCCESS | PARTIAL | none | five-word historical public post; no current coverage proof |
| `twitter.profile` | 16 → 16 | 0.133 → 0.133 | SUCCESS | PARTIAL | D1 | 16-word bio; no observed publication date or identity authentication |
| `hackernews.read` | 184 → 184 | 1.053 → 1.053 | SUCCESS | PARTIAL | B1 | parent plus sampled comments; one empty parent body |
| `hackernews.search` | 484 → 484 | 2.888 → 2.888 | SUCCESS | PARTIAL | B2 | bounded parents/comments; two records lack bodies |
| `stackexchange.read` | 2319 → 2319 | 13.740 → 13.740 | SUCCESS | PARTIAL | none | question and bounded answers; not all answers |
| `stackexchange.search` | 3548 → 3548 | 21.277 → 21.277 | SUCCESS | PARTIAL | none | two bounded Q&A bundles; not all discussions |
| `sec_edgar.read` | 0 → 0 | 0.000 → 0.000 | CONFIG_REQUIRED | BLOCKED | none | SEC_USER_AGENT configuration required; retained blocked state |
| `nist_cve.read` | 103 → 103 | 0.713 → 0.713 | SUCCESS | PARTIAL | none | vulnerability description/metadata, not exploit verification |
| `arxiv.read` | 166 → 166 | 1.136 → 1.136 | SUCCESS | PARTIAL | none | abstract and metadata, not full paper |
| `fact_check.search` | 0 → 0 | 0.000 → 0.000 | AUTH_REQUIRED | BLOCKED | none | Google Fact Check credential unavailable; no fabricated ClaimReview |
| `arxiv.search` | 514 → 514 | 3.730 → 3.730 | SUCCESS | PARTIAL | none | two abstracts, not full papers |
| `bilibili.search` | 35 → 34 | 1.431 → 1.076 | SUCCESS | PARTIAL | none | video metadata; real returned publication date, no transcript |
| `boss.search_jobs` | 0 → 0 | 0.000 → 0.000 | AUTH_REQUIRED | BLOCKED | none | configured authenticated browser/CDP access unavailable |
| `facebook.oembed` | 10 → 10 | 0.270 → 0.270 | SUCCESS | PARTIAL | D1 | ten-word embed/bootstrap HTML; not substantive post body |
| `facebook.search` | 0 → 0 | 0.000 → 0.000 | AUTH_REQUIRED | BLOCKED | none | required server-side access unavailable |
| `github.search` | 23 → 23 | 0.284 → 0.284 | SUCCESS | PARTIAL | A2, D2 | repository search metadata only |
| `instagram.oembed` | 0 → 0 | 0.000 → 0.000 | DEGRADED | FAIL | none | empty degraded embed; no substantive post body |
| `instagram.search` | 0 → 0 | 0.000 → 0.000 | AUTH_REQUIRED | BLOCKED | none | required server-side access unavailable |
| `jina_reader.read` | 333 → 333 | 2.258 → 2.258 | SUCCESS | PARTIAL | A1, D1 | same public page as web.read; not independent corroboration |
| `linkedin.jobs` | 30 → 30 | 0.559 → 0.563 | SUCCESS | PARTIAL | D2 | 30 words of job metadata; missing dates stay unknown |
| `news.search` | 62 → 58 | 0.360 → 0.372 | SUCCESS | PARTIAL | A2 | syndicated discovery; not original article bodies |
| `nist_cve.search` | 104 → 104 | 0.675 → 0.675 | SUCCESS | PARTIAL | none | bounded vulnerability metadata |
| `reddit.search` | 215 → 0 | 1.098 → 0.000 | DEGRADED | FAIL | none | empty final probe; earlier 84-word observation was not reproduced |
| `rss.search` | 32 → 30 | 0.214 → 0.188 | SUCCESS | PARTIAL | A2 | summary/discovery only; missing authors |
| `sec_edgar.search` | 0 → 0 | 0.000 → 0.000 | CONFIG_REQUIRED | BLOCKED | none | SEC_USER_AGENT configuration required; retained blocked state |
| `twitter.read` | 5 → 5 | 0.024 → 0.024 | SUCCESS | PARTIAL | none | same status alias, not another independent source |
| `twitter.search` | 16 → 16 | 0.133 → 0.133 | SUCCESS | PARTIAL | D1 | profile fallback, not matching post search |
| `v2ex.hot` | 14 → 14 | 1.076 → 1.076 | SUCCESS | PARTIAL | none | bounded hot topics; Chinese whitespace undercounts tokens |
| `web.search` | 60 → 59 | 0.419 → 0.410 | SUCCESS | PARTIAL | D2 | search-index snippets; missing publication dates |
| `web_search.search` | 59 → 59 | 0.410 → 0.410 | SUCCESS | PARTIAL | D2 | same search-index alias; do not double-count independence |
| `xiaohongshu.search` | 0 → 0 | 0.000 → 0.000 | AUTH_REQUIRED | BLOCKED | none | required server-side access unavailable |
| `xiaoyuzhou.search` | 0 → 0 | 0.000 → 0.000 | DEGRADED | FAIL | none | empty search; no useful text acquired |
| `xueqiu.search` | 0 → 0 | 0.000 → 0.000 | AUTH_REQUIRED | BLOCKED | none | required server-side access unavailable |
| `youtube.search` | 72 → 72 | 0.455 → 0.455 | SUCCESS | PARTIAL | D2 | search metadata; publication dates absent |

### What changed, and what was deliberately not rewritten

- **Web/article sources:** readable text and observed document links now use the
  same semantic root. The Infosys page previously exposed navigation links
  despite selecting main text. Link priorities now expose bounded statement
  leads. Boilerplate remains preserved in bounded raw capture, not silently
  rewritten into purported facts.
- **Publisher feeds and issuer pages:** original OpenAI/NVIDIA/Apple/Microsoft
  feed discovery, specialist EV reporting, and verified issuer indexes avoid
  depending entirely on opaque news wrappers. Discovery summaries remain
  distinct from linked bodies. Two-hop same-origin HTML followups spend an
  existing read slot; PDFs remain inspectable leads, not parsed statements.
- **Reddit/X:** missing dates are honest; query-empty status does not globally
  disable unrelated targets. Native body preservation avoids unnecessary
  generic rereads. Direct Reddit samples and a normal OpenAI subreddit read
  succeeded, but final Reddit search was empty. X profile fallback is still
  profile metadata, not evidence of matching posts or identity authenticity.
  No authorization/rate-limit bypass was implemented.
- **Bilibili/LinkedIn/Meta/Xueqiu:** supplied dates are retained where observed;
  absent dates are not invented. Meta bootstrap content is not accepted as
  substantive post content. Auth-only operations remain blocked.
- **GitHub/YouTube/V2EX/HN/Stack Exchange/NIST/arXiv/podcast operations:**
  existing bounded acquisition was preserved and remeasured. No fictitious
  source-specific upgrade is claimed. Metadata, captions, abstracts, show
  notes, sampled comments and full bodies keep different evidentiary meanings.
- **Shared processing:** literal negation/qualifiers survive longer bounded
  passage retention; keyword-heavy legal boilerplate is penalized for selection,
  not deleted from raw text. Distinct propositions no longer inherit all
  citations from one shared discovery query. These are conservative UNVERIFIED
  observations, not entailment or independent corroboration.
- **Shared frontend:** all four pages retain extraction inspections, missing-field
  notices, discovery-only context and citation states. A classic-script helper
  collision was reproduced and fixed by isolating renderer internals while
  preserving public exports. Agent-page helpers can no longer replace shared
  escaping, erase zero counts or replace shared timeline rendering.

No frozen benchmark JSONL, historical dossier, research or artifact bytes were
changed. Existing scrapers, compatibility shims and protected registrations
remain. Legacy Reddit RSS/posts/X-mirror transport hardening remains follow-up
work; this checkpoint does not certify every historical transport.

## B. Actual four-agent improvements

### Normal operation, not a display-only demonstration

The fixed baseline had eight zero-acquisition inputs, five native records and
355 retained-text words. Subsequent real cycles inspected content, fixed
reproduced failures and reran normal local page buttons → backend SSE →
acquisition → processing → shared report. Cycle inventories are observations,
not a deduplicated corpus or accuracy scores.

| Normal pass | Zero-acquisition inputs | Native records | Retained-text words |
| --- | ---: | ---: | ---: |
| Baseline | 8 | 5 | 355 |
| Cycle 2 | 6 | 13 | 1,764 |
| Cycle 3 | 5 | 15 | 1,833 |
| Cycle 4 | 4 | 30 | 10,840 |
| Cycle 5 | 3 | 32 | 12,843 |
| Cycle 6 | 3 | 31 | 11,145 |
| Intermediate final | 3 | 26 | 10,298 |
| Final backend verification | 2 | 33 | 11,336 |

The latest native pass and four unseen inputs have application fingerprint
`716f31a1391535485ec397da708f6eb600be9856b79d4c2e7da3608e14c8a135`.
Their capture HEAD may precede the commit because implementation was then dirty;
the fingerprint stayed unchanged throughout each pass. Backend changes were
subsequently committed at `b89daae`. After the frontend-only fix, exact saved
SSE responses were replayed through all 12 actual page buttons without further
provider requests. That replay's application fingerprint is
`296180b9e376257c482ee4e0d710b9353ebb481beb937094b4f37c8b2f158c70`;
those bytes were committed at `bc67b83`. The JSON records these distinct
capture histories; saved replay is not another live acquisition pass.

Each normal input used one fresh request and two viewport captures
(390/1440px) of that same result. Native final: HTTP 200, 29 progress events and
a completed result per input, no SSE errors, no uncaught page exceptions, matching
finding/evidence/discovery DOM counts, no document overflow. Current-frontend
replay: same invariants across 24 states, with keyboard inspection controls
opening for available acquired records. Empty cases keep their report and
discovery context. These are rendering/transport checks, not research PASS.

| Agent / input | Native records before → after | Words before → after | Final KB | Browser seconds | Findings / discovery cards |
| --- | ---: | ---: | ---: | ---: | ---: |
| scout / TATAMOTORS.NS | 0 → 2 | 0 → 680 | 4.718 | 21.22 | 3 / 26 |
| scout / INFY.NS | 0 → 6 | 0 → 947 | 5.593 | 37.60 | 3 / 29 |
| scout / AAPL | 0 → 8 | 0 → 676 | 6.753 | 36.13 | 4 / 20 |
| trending / OpenAI | 0 → 1 | 0 → 119 | 0.891 | 15.20 | 0 / 9 |
| trending / NVIDIA | 0 → 5 | 0 → 7787 | 53.265 | 15.41 | 5 / 3 |
| trending / electric vehicles | 0 → 1 | 0 → 624 | 3.954 | 16.83 | 2 / 1 |
| brandshield / Nike | 0 → 0 | 0 → 0 | 0.000 | 16.57 | 0 / 14 |
| brandshield / Apple | 2 → 7 | 319 → 467 | 2.753 | 19.84 | 5 / 15 |
| brandshield / Tata Motors | 0 → 0 | 0 → 0 | 0.000 | 16.23 | 0 / 8 |
| personal_watch / Sam Altman | 1 → 1 | 18 → 18 | 0.101 | 18.58 | 0 / 12 |
| personal_watch / Tim Cook | 1 → 1 | 8 → 8 | 0.059 | 17.33 | 0 / 11 |
| personal_watch / Satya Nadella | 1 → 1 | 10 → 10 | 0.073 | 17.04 | 0 / 5 |

### Content-level acceptance: what those numbers actually contain

| Case | Acceptance | Actual result and strategic limitation |
| --- | --- | --- |
| Scout / Tata | PARTIAL acquisition; FAIL financial research | 444-word mixed corporate homepage plus 236-word issuer index. Not verified quarterly performance or an anomaly explanation. Historical-availability observation is not a financial finding. Entity/period distinctions across Tata businesses remain necessary. |
| Scout / Infosys | PARTIAL acquisition; FAIL financial research | Six records: issuer/quarter/annual/P&L indexes and historical table context, 947 words. Second-hop Ind-AS page is a 72-word PDF index, not parsed statements. Three unresolved labels, no grounded financial finding. Some nested result indexes still carry PRIMARY depth/badges; issuer ownership does not establish statement-level support. |
| Scout / Apple | PARTIAL acquisition; FAIL financial research | Product feed summaries, home/support/profile material, not period-bound financial evidence. Eight records are not eight independent relevant financial sources. |
| Trending / OpenAI | PARTIAL; original article reads BLOCKED by observed 403 | First-party bodies failed HTTP 403. One 119-word Reddit link submission/sample comments returned via normal subreddit acquisition. No original article body or findings. A stale feed-summary completeness label after deeper read remains a contract weakness. |
| Trending / NVIDIA | PARTIAL; meaningful article-depth improvement | Five bounded dated original publisher articles, 7,787 words, five separately cited UNVERIFIED observations. Raw/readable inspection and late qualifiers survive native adaptation. Same publisher is not five independent sources; virality and independent claim verification remain unproved. |
| Trending / EV | PARTIAL; passage-selection FAIL remains | A relevant 624-word Montréal airport charging article is retained. The second finding is an irrelevant author biography and cites discovery-only context. This is a confirmed remaining P1 defect, not strategic intelligence. |
| BrandShield / Nike | FAIL research | Zero bodies, 14 discovery cards, failed wrapper reads. Does not establish absence of threats. |
| BrandShield / Apple | FAIL specialized research | Seven records, largely product announcements/homepages. No independently confirmed attacker, impersonation or abuse event. More generic content is not better brand-threat research. |
| BrandShield / Tata | FAIL research | Zero bodies, eight discovery leads. No supported conclusion about brand safety. |
| Personal / Sam Altman | FAIL specialized research | 18-word X bio; no impersonation investigation or media forensics. Zero fabricated findings is safer, but not task completion. |
| Personal / Tim Cook | FAIL specialized research | Eight-word X bio; current identity/ownership and abuse claims not independently verified. |
| Personal / Satya Nadella | FAIL specialized research | Ten-word X bio; no substantive identity-abuse evidence. |

Final structured citation observations: **11 SOURCE_RECORD, one DISCOVERY_ONLY,
zero UNAVAILABLE**. These are reference joins, not unique sources, measured
entailment accuracy or proof that a citation supports its proposition. Legacy
unresolved labels and unspecified-state specialist details remain distinct from
structured grounded findings. No calibrated confidence or recall claim is made.

### Unseen controls

Four additional real normal inputs, not used to tune these changes: Scout/MSFT,
Trending/Microsoft, BrandShield/Adidas, Personal Watch/Sundar Pichai. Stable source,
HTTP 200 and eight viewport states met the same recorded DOM/overflow checks.

| Input | Native records | Words | Result |
| --- | ---: | ---: | --- |
| Scout / MSFT | 8 | 7,809 | Substantial publisher material, but general corporate/AI announcements are not financial adjudication. |
| Trending / Microsoft | 0 | 0 | One discovery lead; FAIL research. Generalization is not established. |
| BrandShield / Adidas | 1 | 2,012 | Encyclopedic/company material, plus a generic complaint label; no authenticated abuse investigation. FAIL specialized relevance. |
| Personal / Sundar Pichai | 1 | 9 | Profile only; FAIL specialized depth. |

These controls are not a calibrated held-out benchmark. The Adidas generic
complaint label needs passage/role review before being treated as an actual
complaint. The fact that MSFT yields material does not accept other agents.

### Verification and reproducibility

| Check actually run | Result and boundary |
| --- | --- |
| `pytest tests/ -q` on final frontend code | exit 0; **1,329 passed, 163.39s** |
| `pytest tests/unit tests/chaos tests/security -q` | exit 0; **1,121 passed, 102.64s** |
| `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | exit 0; zero fatal findings |
| All eight `tests/frontend/test_*.js` with Node | exit 0; all suites passed, including page-global collision control |
| `python scripts/validate_release_candidate_smoke.py` | exit 0; OFFLINE_SMOKE_PASS, explicit isolated mocks, not live research |
| `python scripts/validate_rollback_compatibility.py` | exit 0; OFFLINE_PERSISTENCE_PASS; historical archive NOT_VERIFIED in this worktree, not recovery of the 55 previously damaged dossiers |
| `python scripts/validation/verify_frozen_benchmarks.py` and protected-tree Git diff against base | exit 0; protected bytes unchanged |
| Final 52-operation source probe | exit 0; stable source, 16 protected sampled; all-source PARTIAL |
| Four-page source-inspection scaffold | exit 0; 68 captured native samples, 12 viewport/page states, zero measured failures |
| Current-frontend exact saved SSE replay | exit 0; 12 cases, 24 viewport states; no provider reacquisition |
| Hosted CI for backend `b89daae` | all five jobs SUCCESS; [run](https://github.com/Shaunakrane914/Misinformation/actions/runs/39026974679) |
| Hosted CI for application/frontend `bc67b83` | all five jobs SUCCESS; [run](https://github.com/Shaunakrane914/Misinformation/actions/runs/39048174614) |

Hosted jobs are fatal Python lint/frontend contracts, entire offline suite with
persistence/release validators, and fast unit/chaos/security on Python
3.11/3.12/3.13. Hosted CI does not probe live providers or grant deployment
acceptance. The normal browser passes used a real pinned Chart.js 4.4.1 asset;
external fonts were deliberately blocked. Each final native/replay matrix
logged 18 console resource errors, including blocked font loads and static
404s. No uncaught page exceptions were observed, but this is **not a
console-clean certificate**. No full per-resource attribution is claimed.

The LLM configuration was present with mocks disabled in real runs. Live
attempts logged HTTP 429 and a fallback model HTTP 404; **successful live Gemini
synthesis remains UNVERIFIED**. Do not infer exact account quota or key validity
from those statuses. Existing server secrets were neither printed nor edited.
Audits used temporary SQLite/dossier paths, disabled remote persistence,
notifications and background ingestion. Audit LLM calls were bounded at five
seconds/one retry; these are audit-run settings, not changed production defaults.

Intermediate failed runs were retained in the handoff: nondeterministic timing
hashes, reviewed empty-stop/citation goldens, an invalidated source fingerprint,
and a Windows Git-diff decoding failure. No failure was relabeled PASS.

**UNVERIFIED:** independent claim entailment/precision/recall, successful live
LLM synthesis, authenticated depth of gated providers, full accessibility/axe,
manual screen readers/contrast, Safari/Firefox, real mobile hardware, production
parity, deployed rollback and production-launch readiness.

### Next implementation queue and acceptance gates

1. **P1 — passage roles and epistemic depth:** remove author bios/navigation from
   selected event findings without deleting raw capture; prevent nested issuer
   indexes gaining statement-level PRIMARY semantics. Regressions must retain
   real article claims, negation, quotes and exact offset/citation joins.
2. **P1 — financial statements:** bounded SSRF-safe PDF acquisition/parsing with
   byte/page/time limits and exact source/period/table-cell provenance. Keep
   unavailable PDF leads inspectable; no invented financial metric bindings.
3. **P1 — specialized agent relevance:** investigate actual external brand/identity
   abuse candidates and original supporting reports, not product feeds/bios.
   Context-sensitive “complaint” classification must cite a relevant passage.
4. **P2 — read opportunity and wrapper resolution:** diagnose qualified original
   publisher URLs, per-source failures and deadline allocation. Do not loosen
   relevance thresholds or bypass 403/429 to inflate source counts.
5. **P2 — normalization:** refresh completeness after deeper native reads;
   distinguish metadata, index pages, summaries and parsed bodies consistently
   through source → API → all four renderers.
6. **Owner action — live synthesis/access:** verify provider-supported model and
   quota securely; configure approved source access only when available. Leave
   explicit blocked states until then.
7. Repeat the fixed 12-input matrix plus genuinely new controls, inspect actual
   source passages and frontend, run full regressions and exact-code hosted CI.
   A controlled claim-support evaluation is still required before accepting
   research quality. Do not update frozen labels or historical dossiers.

Portable command templates and code ownership are in the handoff. This work
is committed/pushed on the development branch only; **no main merge,
deployment, historical recovery or unattended future monitoring is claimed**.
