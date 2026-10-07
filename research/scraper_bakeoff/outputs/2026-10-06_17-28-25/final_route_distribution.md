# Aegis Protocol — Cascade Final Route Distribution

Percentage of benchmark cases resolved by each retrieval tier under each policy.


| Tier / Route | Policy A (Current) | Policy B (Proposed) | Policy C (Search-First) | Policy D (Optimized) |
|---|---:|---:|---:|---:|
| **`NATIVE_API`** | 7.4% | 7.4% | 0.0% | 7.4% |
| **`SPECIALIST`** | 0.0% | 13.5% | 0.0% | 13.5% |
| **`SCRAPLING`** | 0.0% | 13.2% | 0.0% | 13.2% |
| **`PLAYWRIGHT`** | 0.0% | 0.0% | 0.0% | 0.0% |
| **`CURRENT_READER`** | 7.1% | 0.0% | 0.0% | 0.0% |
| **`SEARCH_FALLBACK`** | 85.6% | 65.9% | 100.0% | 65.9% |
| **`NO_VALID_RETRIEVAL`** | 0.0% | 0.0% | 0.0% | 0.0% |

## Key Insights on Route Dependencies

- **Native API (`aegis_native_github`)**: Resolves exactly **7.4%** of total system load (25/25 GitHub cases with 100% precision).

- **Specialist Media (`yt-dlp`)**: Resolves **13.5%** of total load (46/50 YouTube videos with full metadata).

- **Scrapling HTTP**: Resolves **13.2%** of total load (45/50 web targets with zero browser overhead).

- **Playwright Headless**: Resolves **0.0%** of load (0/340 selected final routes). Playwright is retained as a secondary rescue capability for JS/client-side rendered pages, but it was not selected as the final route in this frozen 340-case benchmark.

- **Search Fallback**: Resolves **65.9%** of load in zero-config mode, functioning as the primary evidence provider for auth-walled social platforms (Reddit, Twitter, Instagram, TikTok, LinkedIn, Facebook, Bilibili).

- **Unresolved**: Exactly **0.0%** (0/340 cases). All 340 cases resolved via direct route or search fallback.
