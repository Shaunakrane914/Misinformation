# ADR 0004: Centralized LLM Provider Gateway and Validated Settings

## Status
**ACCEPTED (Implemented in Phase 6)**

## Date
2026-10-09

## Deciders
- Principal Software Architect & Migration Lead
- Aegis Protocol Core Engineering Team

---

## 1. Context and Problem Statement
LLM inference in Aegis Protocol is currently dispersed across multiple components:
- `backend/services/gemini_service.py` provides a `GeminiService` with key rotation and offline mock fallback.
- `backend/services/intelligence.py` provides separate prompt synthesis functions.
- Several agent modules (`coordinator_agent.py`, `brandshield_agent.py`, `trending_agent.py`) read `os.getenv("GEMINI_API_KEY")` directly or call `requests.post` ad-hoc.
- Cross-cutting settings (timeouts, model names, mock flags, feature toggles) are read directly from `os.environ` throughout the codebase rather than being validated at startup.

This leads to uncoordinated rate-limiting, unhandled API key exhaustions, and unpredictable behavior when testing offline.

---

## 2. Decision Drivers
1. **Unified Provider Abstraction**: Agents must depend on a high-level `LLMGateway` protocol, not Google Gemini SDK internals or raw HTTP endpoints.
2. **Deterministic Offline Testing**: Running tests with `AEGIS_MOCK_LLM=true` must completely guarantee zero outbound network requests and deterministic responses without requiring API keys.
3. **Structured Validation**: Environment variables must be loaded into a validated Pydantic `Settings` model at application startup, failing fast on invalid configurations.
4. **Resilient Key Rotation & Backoff**: Rate limits (HTTP 429) must trigger exponential backoff with jitter and automated multi-key rotation transparently to the caller.

---

## 3. Considered Alternatives
- **Alternative 1: Let Each Agent Call LLM APIs Directly**.
  - *Rejected*: Leads to duplicate prompt templates, fragmented error handling, and inability to enforce unified inference budgets.
- **Alternative 2: Adopt Heavy Multi-Agent Frameworks (LangChain, AutoGen, CrewAI)**.
  - *Rejected*: Incurs massive dependency graphs, breaking changes across minor versions, and opaque execution loops that impair deterministic auditability.
- **Alternative 3: Centralized In-House `LLMGateway` with Pydantic Settings (Chosen)**.
  - Establish `infrastructure/llm/gateway.py` with unified retry, key rotation, and response parsing.
  - Consolidate all configuration in `core/settings.py` using `pydantic-settings`.

---

## 4. Decision Outcome
Chosen option: **Alternative 3 — Centralized In-House `LLMGateway`**.

### 4.1 Architectural Invariants
1. **No Ad-Hoc `os.environ` Reads in Domain/Agent Code**:
   - All configuration values are accessed via `from backend.core.settings import settings`.
   - Settings are validated at application factory startup (`backend/main.py:create_app`).
2. **Provider Isolation**:
   - `LLMGateway` defines an abstract interface:
     ```python
     class LLMGateway(Protocol):
         def generate_structured(self, prompt: str, schema: Type[T], **kwargs) -> T: ...
         def generate_text(self, prompt: str, **kwargs) -> str: ...
     ```
   - Implementations: `GeminiProvider` (production) and `MockLLMProvider` (offline/test).
3. **Strict Offline Test Invariant**:
   - When `settings.AEGIS_MOCK_LLM is True` or `ENVIRONMENT == "test"`, the `MockLLMProvider` is injected automatically. Network calls to generative AI endpoints are prohibited.
4. **Scientific Fail-Closed Invariant**:
   - A call with mock fallback disabled bypasses any ambient mock preference and selects the live provider directly.
   - Missing credentials, request exhaustion, or malformed live responses produce an explicit failure and can never become a synthetic success.
5. **Model Identity and Fallback Invariant**:
   - Omitting a model uses the validated preferred-model-first fallback list.
   - Supplying a model is a strict identity request and does not silently switch to another model.
6. **Synthetic Provenance Invariant**:
   - Mock output is marked synthetic and ineligible as evidence in response metadata and serialized controlled-test output.
   - An empty retrieval corpus must abstain without asking any LLM to generate evidence.

---

## 5. Consequences

### Positive Consequences
- **Test Suite Speed**: Running the entire test suite remains fast and deterministic without burning API rate limits or failing due to network downtime.
- **Multi-Model Portability**: Swapping between Gemini 2.5 Flash, Claude 3.5, or local Ollama models requires changing only the gateway adapter, with zero agent refactoring.
- **Observability**: Token counts, prompt latency, and inference costs are measured in one central telemetry record.

### Negative Consequences / Trade-offs
- Requires migrating direct `requests.post` or `genai.*` calls in existing agents into gateway calls during Phase 6.
