---
completed_on: "2026-09-19"
completion_note: "The provenance worktree was retired, retained refs were documented, decision-origin support landed, and the histories were reconciled on 2026-09-13."
title: Resolve stale provenance worktree and modernize decision origins
status: todo
priority: P1
---

# Resolve stale provenance worktree and modernize decision origins

## Global constraints

- Work only from isolated clean worktrees; do not modify the detached dirty primary checkout.
- Keep all historical branch refs. Remove only the exact obsolete physical worktrees/files named below.
- Never hand-merge `.memory-seed/sessions/**`; use the guarded session fuse.
- Preserve current provenance CLI/MCP behavior and all newer `main` functionality.
- Integrate locally through `session merge-branch`; do not push or open a PR.

## Task 1: Reconcile and preserve provenance history

Current `main` contains the final provenance implementation, but the older
`codex/feature/provenance-surfaces-boundaries-v2` branch retains one unique ESR integration test and
the original detailed session entries. Integrate that branch through the guarded session-fuse path.
Resolve non-session conflicts by preserving current-main implementations and documentation, adding
only the missing ESR test where it remains valid. Fuse the original session entries exactly and keep
their trailers. After review, remove `.codex/worktrees/provenance-surfaces-corrected`; keep every
provenance branch ref.

## Task 2: Retire the inherited-Reflection proposal and correct stale guidance

Delete only the untracked `docs/1_Inbox/reflection-inherited-ledger-integration-admission-proposal.md`
in the locked `a455` worktree after confirming its descendant rule was implemented by `89e0d2b2` and
later superseded by the identical-sibling admission. Keep the locked worktree and every branch ref.
Correct the live and seeded collaboration guidance, operator guide, and active Reflection plan where
they still claim matching-byte sibling branches are refused. Append and commit a durable session
receipt recording the authoritative commits/entries, exact deleted path, retained refs, and the
documentation correction.

## Task 3: Modernize and integrate decision origins

Merge `codex/feature/decision-origins` into this coordination branch through the guarded no-FF/session
fuse workflow. Resolve non-session conflicts semantically against current `main`; do not hand-resolve
session/topic files. Preserve `mse_nqs08dgtyrqjwe9q`.

Required behavior:

- MCP `decisions[]` requires `origin: "user" | "agent"`.
- `user` means a direct user instruction, answer, or correction; `agent` means an implementation,
  investigation, test, or review finding.
- Generated entry YAML stores a complete `decision_origins` mapping.
- Lower-level/CLI callers remain backward compatible: origins are optional, but supplying any origin
  requires complete coverage for the entry.
- Historical entries without the field remain valid.
- Declared mappings reject invalid values, duplicates, missing decisions, and nonexistent ordinals.
- Preserve current provenance tools and other newer MCP/schema behavior.
- Keep live and seeded session-logging guidance in parity.

Run focused MCP/session/core/ADR tests, then full tests and repository integrity checks. No new errors
relative to the captured baseline are allowed.

## Task 4: Final review and guarded integration

Independently review the complete coordination-branch diff and the progress ledger. Resolve all
load-bearing findings through the bounded review loop. Merge the coordination branch into local
`main` with `session merge-branch`, verify entries/trailers/ancestry/worktree cleanup, retain branch
refs, and remove only the plan-specific SDD scratch workspace.
