# Desktop frontend content sufficiency — October 28, 2026

## What was measured

Real Chromium rendered the actual Scout, BrandShield, Trending and Personal Watch
HTML pages and shared renderer at **1366×768, 1440×900, 1920×1080 and 390×844**.
The page buttons consumed exact saved SSE; no browser action reacquired a source
or called a model. API readiness was an explicit replay stub. External resources
were blocked except previously saved pinned Chart 4.4.1 bytes; these measurements
use available local/system fonts, not a fresh production/font-network test.

Sixteen input sets × four sizes = **64 final browser states**. Eleven cases use
their original native response, four use current reprocessing of their original
saved captures (S1/B1/P1/P2), and T2 uses an explicitly labeled recovered-pool
replay because its original response was not saved. T1 renders its real explicit
failure. These categories must not be called sixteen new live frontend results.

The [section ledger](evidence/2026-10-28_16prompt_yield/frontend_sections.csv) and
[complete browser observations](evidence/2026-10-28_16prompt_yield/browser-summary.json)
record every measured dynamic block: summary, findings, workbench, source cards,
discovery, disagreements, changes, specialized intelligence, timeline, trust,
coverage and next steps, plus native result containers. Static heroes, forms,
instructions and pre-scan guide content are outside the result-workspace sample.

Each section records width, height, scroll height, nonduplicate visible-line
words, exact source-quote words, visible recognized card types, fully visible
viewport word counts, empty markers, disclosure/pagination controls and overflow
observations. Card counts explicitly describe their selectors; generic native
container blocks are separately measured rather than asserted to be individual
source cards. Hidden details are excluded from visible text. Native heuristic
summary/analysis is not mislabeled as AI-generated prose: synthesis was disabled,
and query-advice tokens are not report words. Exact quoted-word counts are a
lineage-backed subset of the dynamic text, not an entailment/accuracy score.

## First pagination page is not the viewport

The workbench displays at most eight passage cards per pagination page. Those
cards may span several vertical screens. “First page” below means the displayed
pagination page; **it does not mean all these words are immediately above the
fold**. All-accessible counts include pagination; viewport geometry is separate.
Repeated labels, native source previews and four viewport copies do not create
additional unique evidence.

| Case / 1440px projection | First-page evidence words | All accessible evidence words | Older words | Workbench height px |
| --- | ---: | ---: | ---: | ---: |
| S1 NVIDIA, replay | 495 | 5,685 | 0 | 2,924 |
| S2 Tata Motors | 282 | 282 | 0 | 2,184 |
| S3 Apple | 288 | 2,388 | 0 | 2,775 |
| S4 Infosys | 294 | 294 | 0 | 2,455 |
| B1 Nike, corrected replay | 79 | 79 | 0 | 714 |
| B2 Dyson | 0 | 0 | 0 | 350 |
| B3 Pfizer | 240 | 240 | 0 | 1,870 |
| B4 Apple | 0 | 0 | 0 | 350 |
| T1 battery recycling, failed | 0 | 0 | 0 | 350 |
| T2 Shah Rukh Khan, recovered-pool replay | 239 | 239 | 0 | 2,477 |
| T3 Indian semiconductors | 0 | 0 | 1,074 | 350* |
| T4 Virat Kohli | 132 | 132 | 432 | 965 |
| P1 Tim Cook, replay | 334 | 334 | 0 | 2,299 |
| P2 Sam Altman, replay | 486 | 1,111 | 0 | 2,799 |
| P3 Mary Barra | 0 | 0 | 0 | 350 |
| P4 Shah Rukh Khan | 0 | 0 | 0 | 350 |

*The 350px empty current workbench excludes the separate populated older section.
The current rendered sets contain 207 passage instances and 10,784 case-summed
task/current words, plus 1,506 older words. Cross-case text deduplication is still
required; these case sums are not global unique totals or a live-before/after gain.

## Readability observations and changes

Before changes, S1's 495-word first pagination page occupied 3,351px and P1's
334 words occupied 2,673px at 1440px. A large part of the card height was repeated
capture IDs, offsets and language notices. The shared report was also below a
long legacy workspace, so a short initial dashboard did not reveal its full
evidence collection.

The final local UI keeps publisher, date, assertion status, source link and
required licence credit visible. IDs/offsets/language move into an accessible
native disclosure. A result-top navigation link reports first-page and all-page
quoted words and jumps to the workbench below the fixed header. Older-only
results link to separately labeled background. No source words were added.
Scout badges use actual epistemic state rather than treating schema `FACT` as a
green verified finding.

S1's workbench decreases **3,351 → 2,924px** (12.7%) for the same 495 first-page
words and 5,685 total words. Tim Cook decreases **2,673 → 2,299px** (14.0%) while
retaining 334 words. Initial heading overlap was caught by the browser control
check and corrected; final navigation and detail expansion/collapse pass at all
tested widths. There is more opportunity to group consecutive passages by
source; eight short T2 paragraphs still need 2,477px despite only 239 words.

Screenshots were visually sampled for all four agents, a recovered current
Trending example, a meaningful empty state and mobile. Automated geometry/text
checks cover all 64 states; this is not a claim that every screenshot received
an independent human readability review. See the [screenshot index](evidence/2026-10-28_16prompt_yield/screenshots/README.md).

## Content requirements derived from these layouts

Controlled layout trials showed **subsets of genuine first-page passages**,
never generated filler or new investigations. At 1440px, two Tim Cook cards
contain 107 words in 916px, two Pfizer cards 104 words in 990px, and two Virat
cards 132 words in 965px. Four cards yield 216 Tim words in 1,494px and 188 Pfizer
words in 1,568px. One 79-word Nike incident card occupies 714px and is already a
readable bounded brief. These measurements reject a universal 450–750-word
minimum. Cards/source diversity and the required facts matter more than word total.

The following are **soft editorial recommendations based on measured layouts
and agent review**, not validated psychometric thresholds or backend success
gates. Actual minimums vary by question, source structure and numeric tables.

| Agent | Recommended minimum evidence brief | Comfortable scrollable evidence brief | What must be present |
| --- | ---: | ---: | --- |
| Scout | About 150–200 words | About 300–450 words | Period, entity, units/currency, actual versus forecast, primary disclosure or an explicit missing-primary limit |
| BrandShield | About 80–150 words | About 200–300 words | Specific event/warning, actor/brand relationship, date, case status, evidence scope |
| Trending | About 100–150 words | About 200–300 words | Dated on-topic developments; separate current event/report date and older context; no invented popularity |
| Personal Watch | About 100–150 words | About 200–350 words | Speaker, source, event/publication context, quotation attribution or exact identity-deception evidence |

Zero evidence words are appropriate for an honest failed/insufficient result.
It needs a concise failure explanation and next step, not another 250 words of
padding. A 239-word T2 report is visually informative already; eleven extra words
are not a research problem. Conversely S4's 294 words and P2's 1,111 words do not
answer their exact tasks. Layout targets cannot rescue stale or off-task evidence.

## Conditional evidence gap

[Per-case gap accounting](evidence/2026-10-28_16prompt_yield/evidence-gap.json)
uses reference targets of Scout 350 and the other agents 250 words, inside the
recommended ranges. It records actual source words, selected/published words,
displayed analysis, first-page output, background and a conditional numerical
gap. Empty/error results mark the target inapplicable; missing output is unknown.
Task sufficiency is separately reviewed. A zero numerical gap is never a PASS.

The remaining layout improvement is source-grouped cards and a compact concise
brief with explicit paths to deeper evidence. It should conserve exact text,
dates, permissions, passage offsets and all accessible pagination, rather than
use AI to occupy space. No deployment or production UI claim is made here.
