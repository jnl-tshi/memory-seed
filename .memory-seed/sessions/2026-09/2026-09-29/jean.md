---
schema_version: 2
session_date: 2026-09-29
hash_id: msm_c7edeea2977a18b941c0c5dbddb60a89
user: jean
created_at: 2026-09-29T12:27:21Z
---

## 2026-09-29 13:26 - Complete offline paired decision extraction evaluation

```yaml
entry_id: mse_4bh1kwp2d9vytjcq
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: codex/test/p0-2-paired-replay
decision_origins:
  d1: agent
```

### Summary

- Completed the offline P0.2 paired replay, reconciled the blind semantic review, and published sanitized aggregate evidence without crossing the OAuth boundary.

### Records

#### D1 - Documentation: Complete offline paired extraction evaluation

- D: Completed the frozen old-versus-revised oracle-anchor replay. The revised arm retrieved more cited evidence and avoided repeated extraction work, but both blind reviewers found zero complete semantic matches for either arm; P0.2 actual decision detection remains unvalidated.
  - Scope: Offline P0.2 oracle-anchor replay and retained-state ablation only; no autonomous detection-recall, population-precision, live integration, sign-in, OAuth, approval mutation, or authoritative-memory claim.
- F: `hosted/evaluation/paired_replay.py`, `hosted/evaluation/paired-results.json`, `hosted/evaluation/semantic-results.json`, `hosted/evaluation/PAIRED-REPLAY-RESULTS.md`, `tests/test_p02_paired_replay.py`, `.memory-seed/index.md`, and `docs/2_Todo/0_NEXT_STEPS.md`.
- T: Two raw runs and all masked packets were byte-identical; all 65 saved gold slices passed the identity/heading guard and public projections matched private results. Targeted tests passed 36. The full parallel suite produced 2170 passed, 3 known xdist WindowsPath serialization failures, and 2 skipped; the exact three failures then passed serially with 26 subtests.
- S: `hosted/evaluation/PAIRED-REPLAY-PLAN.md`
- S: `hosted/evaluation/PAIRED-REPLAY-RESULTS.md`
- S: `hosted/evaluation/semantic-results.json`

### Follow-up

- Actual decision detection and live retained-state integration remain unvalidated. Any OAuth or sign-in step still requires separate live approval.
