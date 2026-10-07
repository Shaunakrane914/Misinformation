# SPECIALIST AGENT: TRENDING AGENT SPECIFICATION

**Agent:** Specialist Agent — TRENDING  
**Implementation:** [`backend/agents/trending_agent.py`](file:///backend/agents/trending_agent.py)  
**System:** Aegis Protocol

---

## 1. Architectural Mission & Identity

`TrendingAgent` provides real-time viral anomaly detection and misinformation wave tracking across social and syndication networks.

### Core Responsibilities
1. **Anomaly Detection**: Scan high-velocity topics, hashtags, and social chatter for sudden narrative spikes.
2. **Velocity & Acceleration Metrics**: Compute narrative spread speed and multi-platform diffusion rate.
3. **Misinformation Early Warning**: Flag suspicious claims before they achieve mainstream saturation.
4. **Temporal Ordering**: Maintain chronological threat timelines tracking how a narrative evolves over time.

---

## 2. Interface Contract

### Inputs
- Platform streams (Reddit, X, News feeds) and entity watchlists.

### Outputs
- `TrendingReport`:
  - List of active viral anomalies.
  - Threat velocity and potential market/societal impact score.
  - Origin timestamps and initial propagator accounts.
