# SPECIALIST AGENT: PERSONAL AGENT SPECIFICATION

**Agent:** Specialist Agent — PERSONAL  
**Implementation:** [`backend/agents/personal_agent.py`](file:///backend/agents/personal_agent.py)  
**System:** Aegis Protocol

---

## 1. Architectural Mission & Identity

`PersonalAgent` focuses on individual defense, VIP threat protection, doxxing detection, and personalized privacy monitoring.

### Core Responsibilities
1. **Doxxing & PII Leak Detection**: Identify unauthorized exposure of personal contact details, residential addresses, or private financial records.
2. **Targeted Harassment Tracking**: Detect coordinated harassment campaigns and synthetic defamation directed at protected individuals.
3. **Deepfake & Synthetic Media Alerts**: Identify manipulated images, cloned voices, and fabricated video content representing the subject.
4. **Protective Response Guidance**: Provide structured personal security steps and takedown templates.

---

## 2. Interface Contract

### Inputs
- Individual identity identifiers, monitored social handles, and privacy parameters.

### Outputs
- `PersonalSecurityReport`:
  - Identified privacy breaches and doxxing risks.
  - Threat actor profiles and campaign velocity.
  - Recommended defensive countermeasures.
