# Intelligence pipeline implementation and verification — 2026-10-18

**Engineering checkpoint implemented; research-quality acceptance remains PARTIAL.**
No production deployment, main merge, quota probe or live generation was performed.
This supersedes the earlier terminal-quality checkpoint's *current* limitations;
that historical report and its measurements remain unchanged.

## Actual acquisition, then offline polish

One final bounded four-input live local ASGI/SSE pass used normal acquisition,
fresh temporary persistence, disabled notifications/background ingestion, no AI
credentials and no LLM mocks. Subsequent corrections reused those exact captured
source bytes with network blocked. Browser checks replayed the polished API
responses through actual page buttons, stream client and shared/native renderers.
They did not call providers again.

| Agent / input | Retained records | Words | UTF-8 KB | Live seconds | Polished finding strings |
|---|---:|---:|---:|---:|---:|
| Scout / INFY.NS | 6 | 2,331 | 17.207 | 26.51 | 1 |
| Trending / NVIDIA | 5 | 5,380 | 36.326 | 14.27 | 3 |
| BrandShield / Nike | 2 | 662 | 3.788 | 14.19 | 0 |
| Personal Watch / Sam Altman | 6 | 2,811 | 15.843 | 13.54 | 5 |

Counts include indexes, profiles and other background records; these are not
19 independently verified sources, measured recall, or proof of agent accuracy.
Words are whitespace tokens in one retained content/snippet per native record;
KB = UTF-8 bytes / 1,000. No extrapolation to every website is justified.

Before: the preceding twelve-case checkpoint returned an 18-word Sam profile.
After: this four-case observation retained five Atom articles plus a profile.
An intermediate Sam capture had already acquired five articles but rejected
them because the relevance gate ignored the observed feed author. The fix
qualifies first-person public statements using author attribution without
authenticating identity or converting policy discussion into abuse incidents.
The feed URL was observed on the actual publisher homepage, not invented.

## Seven implementation cycles

1. **AI controls — PASS for offline enforcement; live capability unverified.**
   Ordinary generation is denied before transport. Native Scout, BrandShield
   and Personal Watch synthesis is deterministic. Optional search/passage
   advice requires an explicit model-verified run and investigation scope.
   Strict model identity is `gemini-2.5-flash-lite`; output <=160 tokens,
   prompt <=6,000 characters, one attempt, one request/investigation and three/run.
   Shared SQLite reservations serialize entry points, count timeouts before
   HTTP and persist cooldown. No model/key waterfall, retries or quota probes.
   An expired caller cannot mutate evidence through late advice. Search advice
   additionally requires a failed deterministic discovery observation.
   Offline doubles tested these conditions; **live generation: 0, model lists: 0**.
   The old key diagnostic is presence-only; model-list diagnostic never generates.

2. **BrandShield — bounded correctness PASS; live threat research PARTIAL.**
   Catalog, advertising, corporate background and anti-scam warning passages
   are not attacker findings. Complaint/counterfeit allegations remain
   investigable with canonical IDs and explicitly unverified heuristic states.
   Lookalikes require ownership/behavior review, not automatic takedown.
   The real Nike result remains insufficient, not a fabricated positive.

3. **Personal Watch — acquisition/rendering improved; overall PARTIAL.**
   Feed authors survive qualification/normalization. Public statements and
   abuse allegations have separate contracts; generic/unlinked deepfake text
   cannot establish a subject incident. No technical forensics or identity
   authentication is claimed. Sam's text painted in inspected 320/390/1440px
   captures; other subjects' substantive depth was not live-revalidated here.

4. **Scout — typed prose PASS; general financial/table understanding PARTIAL.**
   Observations preserve metric, currency/unit, exact span, PDF page, unique
   document-quarter context and source ID. The observed Infosys prose reports
   USD 5,082 million revenue for the quarter ended June 30, 2026.
   Revenue percentage share is not a monetary amount. FY27 20–22% margin
   guidance is separated from reported 21.1% margin, with no quarterly period
   assigned to that guidance. Comparisons abstain on currency/period mismatch,
   negation, conflicting values or ambiguous context. Source agreement is not
   independently verified truth. Rounded FCF amounts remain distinct source
   observations; there is no inferred conversion, table-column certainty or OCR.

5. **Trending — passage integrity improved; velocity/coverage PARTIAL.**
   Footer/trademark prose no longer becomes an event. The polished captured
   NVIDIA source instead yields an actual partnership passage. Source dates,
   IDs and qualifications survive. Community text is labeled sampled discourse,
   not measured virality or independent corroboration. Casual non-event chat
   remains inspectable evidence, not a key trend. No historical velocity,
   internet-wide trend detection or current-source completeness was established.

6. **API/frontend integrity — PASS within the measured cases.**
   Exact-span classified passages and financial observations survive public
   metadata inspection; invalid offsets are not exported. Unresolved Scout
   leads remain inspectable separately from key findings. Long findings use
   an explicitly incomplete preview with expandable full context. No new HTML
   interpretation of untrusted source text was introduced.

7. **Regression/publication — local checks PASS; hosted result recorded in handoff.**
   1,402 full / 1,194 fast tests; eight Node scripts; fatal lint; frozen hashes;
   offline release smoke and isolated rollback compatibility pass. The isolated
   worktree has no historical archive to validate. This does not repair or
   verify the original workspace's previously inventoried 55 malformed dossiers.
   Deployed rollback remains NOT VERIFIED. See the dated handoff for Git/CI status.

## Browser evidence and limits

Twelve states: four agents at 320, 390 and 1440px. Counts, citation/finding text
retention, keyboard evidence-inspection activation, no horizontal overflow and
no uncaught page exceptions passed. Screenshot inspection covered report text
for all four agents and Sam at all three widths. Shared-card backdrop
compositing was removed; prior blank Sam cards did not reproduce in this bounded
check. This is not a claim about every browser, long-running interaction or device.

The first browser counter incorrectly included unresolved-lead list items as
findings. That harness selector was corrected; the initial run remains diagnostic,
not accepted evidence. Earlier reprocessing omitted acquired PDF/profile depth;
the harness now restores only previously successful captured reads and keeps
their depth/IDs. All iterations remained offline after the one final live matrix.

External fonts were deliberately blocked and are separately recorded resource
failures, not silently declared fixed. Screen readers, axe, measured WCAG
contrast, Safari/Firefox, real devices, production parity, all-site live access
and final production-launch readiness remain UNVERIFIED.

## Evidence and continuation

See [measurements and screenshots](evidence/2026-10-18_intelligence_completion/README.md)
and [engineering handoff](../handoffs/2026-10-18_INTELLIGENCE_PIPELINE_COMPLETION.md).
Full captured responses, streams, current-process dossiers and logs remain in
a new system-temp proof tree, not over tracked benchmarks or historical records.
Only bounded measurements and selected screenshots are committed.

Existing access flags and credential files were not changed. A local enabled
Reddit policy flag is not proof of provider authorization or production access.
Do not bypass denied providers, invent findings or keep spending AI quota to
fill the remaining research gaps.
