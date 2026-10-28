# Topic-aware source routing and access reviews

Latest public-access implementation and bounded checks are recorded in the [public-source access report](../testing/PUBLIC_SOURCE_ACCESS_ACTIVATION_2026-10-26.md). The [individual-site repair report](../testing/USABLE_SOURCE_REPAIR_AND_SITE_CHECKS_2026-10-26.md) remains the preceding checkpoint. The [earlier October 26 results](../testing/TOPIC_SOURCE_INTELLIGENCE_IMPLEMENTATION_2026-10-26.md) remain historical evidence. The [58-family research catalog](../architecture/source_candidates_2026-10-26.json) remains a research artifact, not runtime configuration.

## Operational components

- [Operational definitions](../../backend/services/research/source_registry_data.json) describe 60 families: the researched 58 plus Global Voices and the Sports Ministry. Seven families have scoped public-text/API reviews; eight retain existing native-route policy, nine explicitly require an intended-use agreement and 36 remain unreviewed. The seven include an API-only CPSC review, not a website-wide content grant. Definitions contain topics, agents/tasks, language/geography hints, discovery/body routes, declared API/feed support, permission/auth state, unknown costs/rate limits and freshness/archive limitations. These are declarations, not successful acquisition counts.
- [Registry](../../backend/services/research/source_registry.py) evaluates separate discovery, body, excerpt and model-processing scopes against dated reviews. Channel health is a separate cached assessment; it never grants permission. Source-specific runtime observations are bounded, process-local and expire after 15 minutes. Planner assessment performs no network/doctor calls.
- [Context classifier](../../backend/services/research/topic_context.py) records subject, aliases, task, tentative topics/type, language/jurisdiction/time window and ambiguities. Confidence is a heuristic routing score, not a calibrated identity or truth probability. Devanagari script alone is `und-Deva`, not an invented Hindi/Marathi identification.
- [Existing shared planner](../../backend/services/agent_reach/source_planner.py) selects at most two reviewed/native topic-family actions within its original caps. Existing-route admission retains authentication and cached capability gates. India-specific sources require a jurisdiction hint; issuer newsrooms require a matching entity anchor. A registry definition cannot grant new publisher rights by itself.
- [Harvesting](../../backend/services/research/harvesting.py) carries validated actions into all four agents. Matching observed lead titles may refine an unknown subject once by replacing an unsubmitted same-channel action. The existing replan allowance, query count and read/request caps are not enlarged. Refinement is routing context, not independent identity confirmation.
- Configuration-only body permission checks run before reader-slot allocation in both controllers. Denied leads remain inspectable with an explicit unread/rejection reason; they cannot consume the read allowance or count as useful supply. DeepReader and redirect transport still recheck access immediately before fetching.
- Body reads retain SSRF, redirect and provider checks. For newly reviewed families, robots checks run lazily on read workers, with 5-second/128KB/one-attempt limits and cached results. Unknown/denied access is not bypassed through another reader. Crawl-delay waits now use one shared origin lease across threads, bounded by the parent research deadline. Each paced transfer has one attempt and no automatic redirects; multi-process pacing is not established.
- Selected reviewed publisher directories can enter the same read budget, with at most two configured entry points. They are discovery-only; only captured links can lead to articles. `site:` search results must satisfy the observed URL host/path constraint, so off-site results activate existing fallback instead of pretending scoped discovery succeeded.
- Passage selection and the shared renderer preserve exact text/offsets, observed source language, author/source credit and licence links. New controlled sources need separate excerpt permission; Global Voices additionally needs captured author/licence observations and no contrary rights notice. Third-party images/audio/video are not granted by this text review.

## Current review boundary

The user confirmed **no publisher agreements are configured; retain explicit gates**. Private entertainment/sports publishers have not been approved. The versioned [public-licence reviews](../../backend/services/research/source_public_licence_reviews.json) cover eligible Global Voices, GOV.UK, PIB and Sports Ministry text, plus scoped DOJ/FTC agency press text and CPSC recall API records, with an explicit expiry. The three agency reviews include a separate model-processing scope; the earlier four do not. Optional target-only AI search advice retains the strict shared budget. A stored body or excerpt grant never silently permits sending its text to an external model. They authorize bounded attempts under those conditions, not a claim that every article is accessible or reusable. Contrary notices and third-party material remain excluded. Government sources are attributed issuing-body statements, not independent agreement.

References: [Global Voices reuse policy](https://globalvoices.org/about/global-voices-attribution-policy/), [Global Voices AI contributor policy](https://globalvoices.org/about/global-voices-policy-on-ai/), [GOV.UK reuse guidance](https://www.gov.uk/help/reuse-govuk-content). No API key, account, paid plan or model generation is needed to evaluate registry definitions. Existing SEC, social, fact-check and other routes keep their own configuration/approval contracts; `EXISTING_ROUTE_POLICY` is not a new verified licence or health assertion.

## Server-side configuration

`AEGIS_SOURCE_REVIEWS_FILE` optionally points to a bounded JSON file on the server. It is never taken from investigation input or browser data. An external file replaces the versioned review set. Missing/invalid/expired scopes fail closed; malformed external configuration does not restore default permissions silently. No tokens belong in this file.

```json
{
  "schema_version": 1,
  "reviews": {
    "source_family_id": {
      "decision": "REVIEW_REQUIRED",
      "scopes": [],
      "reviewed_at": "YYYY-MM-DD",
      "expires_at": "YYYY-MM-DDT00:00:00Z",
      "basis_url": "https://publisher.example/actual-approved-terms"
    }
  }
}
```

Only an actual documented review may change `decision` to `APPROVED` and supply appropriate scopes (`discovery`, `body`, `excerpt`, `model_processing`). Discovery approval alone permits neither reading a body nor displaying its passages. Unknown families/hosts cannot be added by a review file; the versioned registry defines supported hosts/routes. Required provider credentials and existing native access policies still apply after review approval.

`AEGIS_SOURCE_ALLOWED_FAMILIES` optionally restricts article reads to comma-separated registry IDs, for example `global_voices,govuk`. It restricts eligibility without granting any missing permission. Unregistered publishers are blocked in this mode; recognized Google News wrappers can be inspected as discovery only and never count as article evidence. The approved October 26 pilot used this restriction in its child process. No persistent source permissions or production configuration were changed.

## Optional AI suggestions

The user subsequently requested AI enablement. The existing local server `.env` now enables `AEGIS_LIVE_ADVISORY_ENABLED`, `AEGIS_SEARCH_ADVISOR_ENABLED`, `AEGIS_SOURCE_PLANNER_LLM_ENABLED` and `AEGIS_EVIDENCE_ADVISOR_ENABLED`, using the already configured `gemini-3.5-flash-lite` model. Restart an existing backend process to load changed flags. No credentials were copied into this worktree, and the example configuration remains opt-in.

All suggestion paths share the existing persistent policy: one reservation per investigation, three per UTC day, at most 160 output tokens, one attempt, no key/model fallback, and cooldown on quota failure. Suggestions do not grant publisher permission, invent article text or establish verdicts. Passage advice keeps its privacy and deterministic requalification checks. A completed single live suggestion check used 40 provider-reported tokens; it is separate from the two AI-disabled acquisition pilots and does not demonstrate article acquisition. Ordinary automated tests remain AI-disabled. Production settings were not updated or deployed.

## Verification

Normal tests keep live AI/source traffic disabled:

```text
python -m pytest tests/unit/test_topic_source_registry.py tests/unit/test_source_planning_engine.py tests/unit/test_specialist_harvest_wiring.py -q
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
node tests/frontend/test_evidence_workbench.js
python scripts/validation/verify_frozen_benchmarks.py
```

Run all frontend Node scripts and isolated release/persistence validators as specified by AGENTS. Fresh outputs must use new temporary paths. A passing isolated persistence validator does not verify the historical dossier collection or deployed rollback.

For a planner-only comparison, keep a copy of the previous planner and run:

```text
python scripts/audits/compare_topic_source_plans.py --baseline-planner <saved-previous-planner.py> --output <new-temp-json>
```

The default eight-topic fixture and three ambiguity controls are synthetic calibration, not genuine source bodies or an independent accuracy evaluation. Optional `--saved-batch <native-run-directory>` reuses genuine saved search/read observations through the existing simulator. `--recorded-claims <case-id-to-original-claim.json>` preserves exact original requests when an old runner summary omitted them; clearly identify any reconstruction from recorded command lines. Both planner versions share current controller/permission rules. Missing observations remain unknown; replay costs/latency are modeled. Do not call those results live acquisition or grant additional collection permissions.

Only run fresh investigations under a separately authorized, explicit request budget. Source relevance, rights, access, actual body acquisition, exact attribution, fresh evidence and research accuracy are separate acceptance gates.

The direct per-site inventory/probe command is:

```text
python scripts/audits/probe_source_families.py --allow-live --family doj --family ftc --family cpsc --seconds-per-family 90 --output-dir <new-temp-directory>
```

It inventories all 60 families and requires explicit selection of one to four reviewed families, under at most 90s/six native admissions/two reads per family. It exports JSON/CSV without raw source text. CPSC uses one bounded recall API lookup and counts structured records separately from article bodies. Its API adapter is registered for explicit use; automatic webpage discovery is withheld until the native structured-record path is integrated. It does not claim a recall is a counterfeit finding. No query-based research, AI generation, relevance verdict or automated publication is performed. Gated families remain NOT_PROBED, not network failures. Use it only for an authorized individual-source check; the recorded October 26 runs are already consumed.
