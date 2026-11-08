# Codex To Claude Handoffs

## 2026-11-08 - MSI-022/MSI-024 ICM design

- Branch: `codex/docs/msi-022-024-icm-design`
- Outcome: added `docs/1_Inbox/icm-workflow-and-stage-contract-integration-proposal.md` as a proposal only; no MSI-022/MSI-024 behavior was implemented.
- Recommended boundary: ICM files are opt-in, create-once, project-owned workflow contracts; Memory Seed retains Task Dispatch/Packet, worktree, integration, policy, and durable-memory authority.
- Proposed adapter: Dispatch v2-only stage-contract rendering, and single-task `from-plan` ingestion that can supply explicit read scope but cannot broaden plan-derived write authority.
- Approval gate: JNL must decide the five-stage default pack, project-owned lifecycle, v2/single-task initial limits, and precedence rules before implementation.
- Validation: `docs check`, `links check`, `encoding check`, and `git diff --check` passed. Link checking retained only the repository's pre-existing warnings.
- Coordination note: `to-codex.md` was absent at the start and recheck of this item; this file was also absent, so this handoff creates the requested Claude channel.

## 2026-11-08 - MSI-034 legacy managed-file digests

- Branch: `codex/fix/msi-034-legacy-digests` (stacked on the MSI-022/MSI-024 design commit).
- Outcome: added the seven exact Gagiste v2.24 managed-file preimages to `KNOWN_LEGACY_MANAGED_SEED_DIGESTS`: three skills and four hooks. Unknown bytes remain preserved and warned as before.
- Tests-first evidence: the new pinned-preimage regression failed with seven subtest failures before the constant changed, then passed with all seven paths covered.
- Focused validation: the three digest/update regressions passed (`3 passed, 7 subtests`); the full serial project-lifecycle module passed (`83 passed, 13 subtests`).
- Field-shaped validation: a shallow isolated clone of Gagiste `main` updated with zero warnings, backed up and archived exactly seven files, refreshed all seven to current seed bytes, and recorded all seven in `managed-seed.json`. The temporary clone was removed afterward.
- Coordination note: `to-codex.md` remained absent at the item start and completion recheck.

## 2026-11-08 - MSI-033 version-bump verification

- Branch: `codex/test/msi-033-version-bump` (stacked on MSI-036).
- Outcome: added a regression that removes the MSI-021 project markers from version 2.23-shaped managed `AGENTS.md` and `CLAUDE.md`, then exercises the current update path.
- Result: the regression passed without a production change. A version bump restores both files at the current control-plane version, adds exactly one project-owned marker block to each, backs up and archives both old files, and is idempotent on the next update.
- Decision: no MSI-033 same-version logic fix is included. The release bump to control-plane 2.25 supplies the required transition; changing same-version semantics would expand overwrite risk beyond the requested verification.
- Validation: the full serial lifecycle module passed (`85 passed, 15 subtests`); docs, encoding, and `git diff --check` passed.
- Coordination note: `to-codex.md` remained absent at the item start and completion recheck.

## 2026-11-08 - MSI-036 once-visible hook import warning

- Branch: `codex/fix/msi-036-hook-import-warning` (stacked on MSI-034).
- Outcome: `session-log-check.py` no longer disappears silently when a refreshed hook outruns the installed package and cannot import `memory_seed.session_checkpoint`.
- Once-visible behavior: the hook atomically creates `.memory-seed/.session-log-import-warning-stamp`, emits one host-shaped upgrade/reinstall warning, then stays silent and fail-open on later invocations. Codex receives `systemMessage` with `continue: true`; Claude/VS Code receives the one blocking shape required to make a Stop-hook reason model-visible. Cursor, Gemini, and Copilot retain their native output shapes.
- Hygiene: init/update add the stamp to `.gitignore`, and the live and seeded hook copies are byte-identical.
- Tests-first evidence: two missing-package regressions failed before implementation; the gitignore regression also failed before the operational ignore was added.
- Validation: the combined serial hook/lifecycle/text/git-hook suite passed (`132 passed, 14 subtests`); docs, encoding, parity, and `git diff --check` passed.
- Coordination note: `to-codex.md` remained absent at the item start and completion recheck.

## 2026-11-08 - Memory Seed 2.25.0 local release preparation

- Branch: `codex/release/2.25.0-prep` (stacked on MSI-033).
- Outcome: prepared package version `2.25.0` and control-plane version `2.25`, archived the exact 2.24 `agent-rules.md` and `project-bootstrap.md` preimages, refreshed live and seeded version frontmatter, dated the changelog, refreshed the functionality audit and generated docs indexes, and built both distribution artifacts. Nothing was published, tagged, pushed, or merged.
- Artifact inspection: the wheel and sdist both report version `2.25.0`; the wheel contains the packaged agent entry point and control-plane skills. SHA-256: wheel `C0247B561C2108A21E5459184AB1C03276272ADB117806D20B26C490062FF3EB`; sdist `6F675C00C6A63D79B95AAD042EDB4B9FFDF40664950DFC10375A97C3CFB55E12`.
- Package smoke: an isolated no-dependency wheel install reported CLI/control-plane versions `2.25.0`/`2.25`, imported `memory_seed.core`, and initialized a 2.25 seed successfully. Its doctor correctly reported the fresh project as seeded-but-not-bootstrapped because generated `index.md` and `policy.md` do not exist until bootstrap.
- Passing gates: focused version tests; doctor; links integrity (pre-existing warnings only); docs lifecycle and generated-index checks; encoding; archive byte comparisons; build; artifact content/version inspection; installed-wheel smoke; and `git diff --check`.
- Full serial suite: `2365 passed, 2 skipped, 307 subtests passed`; the only two failures are MSI-031's scheduled inventory work in `tests/hosted/test_import_inventory.py`, where `project.docs`, `project.docs.allowlist`, and `project.docs.lanes` are absent from the crosswalk/snapshot. They were deliberately not folded into this release-boundary commit because the approved order keeps MSI-031 post-release-track.
- Promotion state: local release candidate prepared, but final full-suite promotion remains pending MSI-031's separate repair and final rerun.
- Coordination note: `to-codex.md` remained absent throughout release preparation.

## 2026-11-08 - MSI-035 documentation allowlist coverage

- Branch: `codex/feat/msi-035-docs-allowlist` (stacked on the 2.25.0 release-preparation commit).
- Outcome: documentation allowlist entries now cover directory subtrees. Literal entries act as path prefixes; POSIX glob entries (`*`, `?`, character classes, and `**`) cover a matched directory and its descendants.
- Non-lane behavior: an allowlisted tree outside `docs.lanes` is now an explicit exemption, while unrelated non-lane folders continue to raise `off-lane-folder`.
- Tests-first evidence: four new regressions failed before implementation—literal descendant coverage, lane glob coverage, literal non-lane exemption, and globbed non-lane exemption—then all passed.
- Validation: the serial docs check/index/lifecycle suite passed (`119 passed, 15 subtests`); live docs lifecycle checked 275 files; generated indexes were current; encoding and `git diff --check` passed.
- Documentation: README, the project configuration comment, repository docs front door, and Unreleased changelog now describe prefix/glob/non-lane semantics. The stale `SIDE_FOLDER_ALLOWLIST` reference was corrected to `.memory-seed/project.yaml`.
- Coordination note: `to-codex.md` remained absent at item start and completion.

## 2026-11-08 - MSI-031 hosted import inventory refresh

- Branch: `codex/fix/msi-031-inventory` (stacked on MSI-035).
- Outcome: classified `project.docs` as a structural container and `project.docs.allowlist` / `project.docs.lanes` as preserved, non-authoritative `control_plane_config` metadata targeting `project_artifacts.metadata_json`.
- Snapshot: regenerated `hosted/importing/inventory.json` from the canonical live scanner and updated the checkpoint census documentation to the 2.25.0 local release state.
- Tests-first evidence: the release/full-suite reproduction failed only the two inventory tests before implementation, naming the three `project.docs*` fields; the focused module then passed all 5 tests.
- Validation: crosswalk uniqueness, explicit classification/target rules, live totality, actor coverage, frozen fixture hashes, unknown-field negative control, and snapshot vocabulary parity all pass.
- Coordination note: `to-codex.md` remained absent at item start and completion.

## 2026-11-08 - MSI-032 Windows xdist subtest serialization

- Branch: `codex/fix/msi-032-xdist` (stacked on MSI-031).
- Outcome: converted the three remaining `pathlib.WindowsPath` unittest subtest labels in handoff-wiring and subagent-orientation tests to POSIX strings. Assertions still operate on the original `Path` objects; only cross-worker diagnostic metadata changes.
- Reproduction: the exact two-module xdist run failed before implementation with 3 `execnet.gateway_base.DumpError` failures (`can't serialize <class 'pathlib.WindowsPath'>`) and passed serially.
- Focused validation: the same modules pass under xdist and serial execution (`9 passed, 37 subtests` in each mode).
- Full parallel validation: default pytest/xdist completed cleanly with `2371 passed, 2 skipped, 307 subtests passed` in 406.40 seconds. A transient Git-for-Windows signal-pipe permission message did not produce a pytest failure.
- Decision: fixed serializability at the subtest-label boundary; no module exclusions, serial-only markers, or suite-wide xdist workaround were added.
- Coordination note: `to-codex.md` remained absent at item start and completion.

