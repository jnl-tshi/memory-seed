---
schema_version: 2
session_date: 2026-10-19
hash_id: msm_027258db409317b930030bd23c19e306
user: jean
created_at: 2026-10-19T00:02:59Z
---

## 2026-10-19 01:01 - Prepare and validate the v2.24.0 release

```yaml
entry_id: mse_r396hbfn2w1047hk
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: codex/release/v2-24-0
decision_origins:
  d1: user
  d2: agent
```

### Summary

- Pushed the completed functionality-audit, hook, virtual-environment, and encoding fixes to `origin/main`, then prepared Memory Seed 2.24.0 as the next minor release.
- Refreshed the functionality audit to the 2.24.0 released surface and repaired stale release baselines exposed by the complete test suite.

### Records

#### D1 - Decision: Release the accumulated feature set as v2.24.0
- D: Set the package version to 2.24.0 and the control-plane version to 2.24, archive the 2.23 control plane, fold Unreleased into the dated 2.24.0 changelog section, refresh every live and packaged version surface, and publish only through the GitHub Release workflow.
  - Scope: public package release.
  - Disposition: implemented
- R: Unreleased contains multiple added capabilities—Design Discovery v2, durable workflow telemetry, and the evidence-first capture experiment—so semantic versioning calls for a minor bump rather than a patch.
- F: pyproject.toml, memory_seed/core.py, CHANGELOG.md, .memory-seed/index.md, .memory-seed/archive/2.23/, docs/3_Spec/functionality-audit.md
- T: Targeted release tests passed (118 tests plus 8 subtests); links, docs lifecycle, docs index, Memory Trace (205 tests), React type-check, React tests (239), production asset reproduction, and wheel/sdist inspection all passed.

#### D2 - Decision: Refresh frozen release-validation baselines
- D: Re-hash every declared source in the real-current context fixture, add the newly referenced ADR update entry, and refresh the hosted live-corpus inventory after the release record is written.
  - Scope: test fixtures and generated validation inventory.
  - Disposition: implemented
- R: The first complete suite exposed 32 failures/errors from two drifted ADR hashes and one missing update entry, plus one stale inventory-count assertion. These were pre-existing corpus drift, not release-version regressions, but the release gate requires the full suite to pass.
- F: experiments/context-derivation/fixture_source/real-current.json, hosted/importing/inventory.json
- T: The context-derivation group passed after refreshing the frozen source contract; the inventory and complete suite are rerun after this entry updates the live corpus.

## 2026-10-19 01:35 - Repair v2.24.0 Linux release blockers

```yaml
entry_id: mse_mapgt5zrk2tnejjz
user_initials: JNL
agent_type: codex
project_path: .
subproject_path: null
branch: codex/fix/release-ci
decision_origins:
  d1: agent
  d2: agent
```

### Summary

- Repaired the two Linux-only blockers exposed by the 2.24.0 release verification run without changing the session-checkpoint production contract.
- Updated the changelog and functionality audit with the verified cross-platform behavior.

### Records

#### D1 - Decision: Keep clean-advisory fixtures on the hook's active day

- D: Write synthetic stale entry timestamps into the current-day session target while preserving their old heading timestamps.
  - Scope: session-checkpoint and hook ordering contract tests.
  - Disposition: implemented.
- R: The hook intentionally resolves the current day's session target. Subtracting 16 or 30 minutes from wall-clock time near UTC midnight moved the fixture into yesterday's file, so CI tested target selection instead of advisory age.
- F: tests/test_session_checkpoint.py, tests/test_session_log_ordering_hook.py
- T: The four affected advisory tests and all supported host-shape subtests passed after the fixture correction.

#### D2 - Decision: Use stable capture file identity across POSIX appends

- D: Key capture source identity by device and inode, fall back to ctime only when those identifiers are unavailable, and accept the legacy device:inode:ctime shape during cursor migration.
  - Scope: hosted/capture/adapter.py pause/resume and rotation detection.
  - Disposition: implemented.
- R: POSIX ctime changes on append. Including it in identity made the first post-resume append look like rotation, incremented generation, and replayed previously drained events.
- A:
  - Retaining ctime in the primary identity was rejected because it is not stable on Linux.
  - Treating every identity mismatch as rotation was retained for genuinely different device/inode pairs; prefix compatibility is limited to the previous three-part format.
- F: hosted/capture/adapter.py, tests/test_hosted_decision_capture.py, CHANGELOG.md, docs/3_Spec/functionality-audit.md
- T: The migration regression failed before implementation and passed after it. The three affected modules passed 54 tests and 6 subtests; the complete local suite then passed 2,319 tests with 1 skip.
