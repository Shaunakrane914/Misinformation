# Independent Phase 8 evidence — 2026-10-14

Append-only bounded observations. Never overwrite these to make a failing result appear to pass. See [review](../../docs/architecture/PHASE8_INDEPENDENT_REVIEW_2026-10-14.md) and [handoff](../../docs/handoffs/2026-10-14_PHASE8_INDEPENDENT_REVIEW.md).

| Directory/file | Meaning |
|---|---|
| `operations/2026-10-14_04-18-12Z/` | First 16-operation public sample; PASS, dirty implementation source explicitly recorded. |
| `final_operations/2026-10-14_04-36-56Z/` | Clean `220f16f`, 16/16 bounded public sample, `--require-pass` exit 0. Not uptime/full history. |
| `2026-10-14_sources/` | Earlier live source probe; exposed invented SEC contact, arXiv timed out. Preserved, not final compliant configuration proof. |
| `2026-10-14_sources_config_safe/` | Corrected source probe: SEC CONFIG_REQUIRED; NVD/arXiv SUCCESS; FactCheck AUTH_REQUIRED. |
| `2026-10-14_api/` | Initial Microsoft API run; JSON retained, report writer failed on sources mapping. Do not infer successful report completion from JSON existence. |
| `2026-10-14_apple_api/` | First Apple actual API run; support/store pages falsely became complaints, Scout report failed. Preserved negative evidence. |
| `final_apple_api/` | Clean `220f16f`, actual four-agent API path, mocks false, no live LLM key, temporary persistence; 3/0/0/0 records. Research PARTIAL, not accuracy proof. |
| `final_brand_date_check/` | Additional live BrandShield-only check after normalization/security follow-up; inspect its exact commit/dirty metadata and record dates. Not a four-agent run. |
| `holdout_before/`, `holdout_after/`, `final_holdout/` | Same separately source-adjudicated small component set; 10 safe outcomes, 0/4 truth resolutions before/after. No human labels, live retrieval or population metrics. |
| `2026-10-14_browser/`, `stress_before/` | Real captures/metrics exposing Scout overflow and invalid ARIA semantics. |
| `stress_after/` | Corrected Microsoft 320px replay plus labeled synthetic stress; eight states pass. |
| `final_result_browser/` | Richer Apple payload exposed additional BrandShield overflow; exit 1. |
| `final_result_browser_corrected/`, `final_progressive_browser/` | Corrected 320px actual recorded-payload replay and separately synthetic 200-record/long-title/hostile-link controls; exit 0. Not fresh browser API requests or screen-reader acceptance. |
| `offline_smoke.json`, `offline_rollback.json` | Isolated offline validators, not live deployment or recovered protected archive proof. |

Screenshots are original browser captures. Synthetic input is explicitly labeled; no screenshot is fabricated. Input record count does not imply all records were rendered. Axe contrast remains incomplete on gradients. Provider latency is variable; HTTP timeouts are per attempt, not a global API SLA. Local commands and secret-pattern scans do not constitute a universal privacy/security assurance.
