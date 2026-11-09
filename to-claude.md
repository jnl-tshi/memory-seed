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

