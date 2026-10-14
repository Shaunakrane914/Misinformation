# Source planner deterministic-versus-hybrid evaluation

Generated: `2026-10-11T00:55:41.723713+00:00`

Live LLM executed: **FALSE**

No mock model output was used. Acquisition latency, retrieval failures, useful evidence, token usage, and model cost remain unmeasured because this runner evaluates planning only.

| Scenario | Deterministic actions | Hybrid status | Hybrid actions |
|---|---:|---|---:|
| `nvidia_hardware` | 3 | FALLBACK | 3 |
| `nvidia_financial` | 3 | FALLBACK | 3 |
| `tata_financial` | 3 | FALLBACK | 3 |
| `anthropic_impersonation` | 2 | FALLBACK | 2 |
| `emerging_rumor` | 2 | FALLBACK | 2 |
| `ambiguous_entity` | 2 | FALLBACK | 2 |
| `regional_multilingual` | 3 | FALLBACK | 3 |
| `adversarial` | 3 | FALLBACK | 3 |
| `unavailable_provider` | 2 | FALLBACK | 2 |

## Decision

Deterministic planning remains the default. Hybrid planning cannot be recommended until a configured live model is evaluated; fallback behavior alone is not evidence of model value.
