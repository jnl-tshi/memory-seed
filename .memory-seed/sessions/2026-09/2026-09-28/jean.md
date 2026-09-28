---
schema_version: 2
session_date: 2026-09-28
hash_id: msm_b1314f94d6e16cff7b813a66b055fa84
user: jean
created_at: 2026-09-28T19:07:14Z
---

## 2026-09-28 20:06 - Set the Jev and CLM-8B selection default

```yaml
entry_id: mse_7hv6dxneyp91hcvm
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: codex/decisions/jev-clm-default
decision_origins:
  d1: user
```

### Summary

- Recorded JNL's conditional default for choosing between Jev and CLM-8B, grounded in the current benchmark and local-running evidence.

### Records

#### D1 - Decision: Prefer Jev by default unless local constraints favor CLM-8B

- D: Use Jev as the safer default candidate for general decision quality and light usage when suitable local hardware would otherwise need to be purchased. Prefer CLM-8B when suitable local NVIDIA hardware already exists, or when privacy, very low latency, high-volume cached-action routing, or domain-specific verifier fine-tuning justify self-hosting.
  - Scope: Candidate-selection guidance for the decision-layer model tournament and future routing or verifier work; this is not a production adoption, an exclusive vendor commitment, or a claim that one model wins every workload.
  - Disposition: Accepted as user-originated conditional selection guidance.
- R:
  - The official CLM release reports strong speed and task-specific results on a single 24 GB GPU, while the independent JevBench comparison currently favors Jev on broad decision quality and calibration.
  - CLM's Apache-2.0 software and weights are free, and electricity is modest once hardware exists; purchasing a capable GPU system dominates the local cost and is hard to justify for light use.
  - Benchmark and hardware-market evidence is time-sensitive, so any production choice still requires a matched evaluation on the project's own workload.
- A:
  - A blanket rejection of CLM-8B was rejected because its cached-action latency, privacy, and fine-tuning advantages can dominate in an established local deployment.
  - Choosing CLM-8B solely because it is faster was rejected because speed does not compensate for weaker broad decision quality or new hardware capital cost in the default case.
- S: Decision-layer model tournament plan `docs/2_Todo/decision-layer-model-tournament-plan.md`.
