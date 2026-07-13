---
memory-system-version: 2.13
tags:
  - memory-seed
  - claude
  - proposal-review
  - roadmap
status: draft
---

# Proposal Synergy Evaluation (Claude)

## Summary

This evaluated the six active `docs/2_Todo/` proposals (five Logic Capture items plus
`agent-fanout-workflow-plan.md`) against each other and against `docs/3_Spec/functionality-audit.md`, using
a fan-out of three read-only research subagents (ranking/graph cluster, guidance/convention cluster,
functionality-audit cross-check + ship order), each briefed with specific hypotheses to confirm or
refute rather than sent in blind.

**Mid-evaluation, a concurrent Codex session independently ran a near-identical synergy pass** and
applied edits directly to almost every file this evaluation also targeted (see
[`codex-proposal-synergy-evaluation.md`](codex-proposal-synergy-evaluation.md)). Rather than
duplicate or revert that work, this report reconciles: it identifies what Codex's pass already fixed,
confirms nothing here contradicts it, and applies only the remainder - four items neither Codex's
report nor its edits covered.

## What The Three Subagents Found

**Ranking/graph cluster** (`interaction-frequency-ranking-plan.md`, `supersession-edges-plan.md`,
`related-entries-generation-plan.md`): confirmed the core code citations are accurate (no drift);
confirmed `interaction-frequency-ranking-plan.md`'s P1 "ship now" framing conflicted with its own
Definition of Done, which needs real `supersedes` edges to exist for its required fixture test -
the two P1s are co-dependent, not sequential; found the acyclicity claim for `supersedes` rests on an
unenforced forward-only convention, with no `links check` guard; surfaced a candidate new idea (an
opt-in `exclude_superseded`-style `memory_search` filter) that neither companion plan proposes, but
flagged it must respect the existing "never hide, only deprioritize" contract.

**Guidance/convention cluster** (`mermaid-usage-guidance-plan.md`, `failed-approaches-logging-plan.md`,
`agent-fanout-workflow-plan.md`): confirmed the two guidance-doc bullets are fully independent of each
other and of the existing Working Principles; confirmed a failed-approach entry scoring high under
Option C's raw backlink count is a correct outcome, not a bug needing a doc change (the harmony
contract already distinguishes this from `supersedes` dampening); found two real gaps in
`agent-fanout-workflow-plan.md` - no cross-reference to backfilling `commits:` on orchestrator
handoffs, and no acknowledgment that read-only Explorers (exempt from the Worktree Gate on
write-collision grounds) still need this repo's `policy.md` pwd/HEAD verification rule, which is
actually the mechanism that would have caught the bug that motivated this whole plan.

**Functionality-audit cross-check + ship order**: produced a full dependency graph across all six
proposals (below); confirmed the MCP filter surface and `doctor` warnings-channel descriptions in the
audit are accurate against real code; confirmed the audit's section 14 gap (missing `agent-fanout-workflow-
plan.md`) and one minor prose imprecision in `NEXT_STEPS.md` (the "items 1 and 2 shared a dependency"
line conflates the links-check dependency with the separate supersession/ranking coupling).

## Reconciliation With The Concurrent Codex Pass

Codex's pass, read after the fact, already fixed almost everything the three subagents found:

| Finding | Status |
|---|---|
| `interaction-frequency-ranking-plan.md` P1 falsely claims independence from `supersession-edges-plan.md` | **Already fixed by Codex** - split into P1a (raw `related_degree`, ships now) / P1b (supersession-aware `importance_score`, ships after `supersession-edges-plan.md` P1). Cleaner than this evaluation's own draft fix; no further change made. |
| `related-entries-generation-plan.md` stale P1/DoD wording (`link add` incorrectly listed as shipped) | **Already fixed by Codex.** |
| `3.0-plan.md` / `user-interface-deep-research-report.md` / `Memory-Seed Logic Capture Improvement.md` stale status | **Already fixed by Codex** (status blockquotes added; not in this evaluation's original scope). |
| Audit section 14 missing `agent-fanout-workflow-plan.md`, stale "4 of 5" count, stale Mermaid label | **Already fixed by Codex.** |
| `agent-fanout-workflow-plan.md` should not register worker agents as `participants:` | **Already fixed by Codex** (`shared_file_policy: orchestrator_only` field added, explicit "not registering worker agents as participants" note added to "What not to build yet"). |
| `supersedes` field name open decision | **Already resolved by Codex** (picked `supersedes` over `deprecates`). |
| Forward-only/cycle-detection gap for `supersedes` in `links check` | **Not covered by Codex.** Applied here - see below. |
| `commits:` backfill cross-reference on fanout orchestrator handoffs | **Not covered by Codex.** Applied here. |
| Read-only Explorers still need the `policy.md` pwd/HEAD check | **Not covered by Codex.** Applied here. |
| `exclude_superseded`-style MCP filter idea | **Not covered by Codex.** New proposal doc written (see below). |

No contradiction was found between this evaluation's findings and Codex's applied edits - the two
passes converged independently on the same core issue (the ranking/supersession co-dependency),
which is a strong signal that finding was real, not an artifact of either evaluation's framing.

## What Changed In This Pass

1. **`agent-fanout-workflow-plan.md`** - added two clauses: the Exploration Gate now states that
   read-only Explorers must still satisfy `.memory-seed/policy.md`'s pwd/`git rev-parse HEAD`
   verification rule (the actual mechanism that would have caught the live-reproduced stale-worktree
   bug, since that bug hit a read-only research role, not a write-side worker); the Final Handoff Gate
   now states the orchestrator backfills the handoff entry's `commits:` field once
   `git-commit-entry-linking-plan.md` ships, within that plan's existing append-only scoping.
2. **`supersession-edges-plan.md`** - added a Validation-section note that the "provably acyclic"
   claim currently rests on an unenforced forward-only authoring convention, not a code-enforced
   invariant, with a candidate `links check` forward-only/cycle guard added to the Definition of Done
   as a P1 candidate (not yet committed to). Also fixed a stray mojibake character
   (a double-encoded dash sequence repaired to a plain hyphen) introduced in the open-decision note.
3. **New: `exclude-superseded-filter-plan.md`** - a small, explicitly opt-in `memory_search` filter
   proposal, blocked on `supersession-edges-plan.md` P1, respecting the existing "never hide, only
   deprioritize" contract. Added as item 6 under NEXT_STEPS.md's "Logic Capture Improvements".
4. **`NEXT_STEPS.md`** - linked this report alongside the Codex report; added the new filter plan as
   item 6.

Explicitly **no changes** to `mermaid-usage-guidance-plan.md`, `failed-approaches-logging-plan.md`,
`related-entries-generation-plan.md`, `3.0-plan.md`, `user-interface-deep-research-report.md`,
`docx-render-windows-seed-lessons.md`, or `Memory-Seed Logic Capture Improvement.md` - Codex's pass
already left these in a coherent state and no subagent found a further real gap.

## Unified Ship Order (six active proposals + the new filter idea)

```text
related_entries P1 (shipped 2.13.0)
  -> supersession-edges P1 (supersedes schema, superseded_by, links check, forward-only guard candidate)
       -> interaction-frequency-ranking P1b (supersession-aware importance_score, shared fixture test)
       -> exclude-superseded-filter P1 (new; needs superseded_by to exist)
  (independently, no dependency on the above:)
interaction-frequency-ranking P1a (raw related_degree) -- ships now, no schema change
git-commit-entry-linking P1 -- ships now, independent
  -> agent-fanout-workflow's commits: backfill note (soft, non-blocking; only relevant once shipped)
mermaid-usage-guidance -- ships now, fully independent
failed-approaches-logging -- ships now, fully independent
agent-fanout-workflow -- ships now (recipe/documentation only), independent of the ranking/graph cluster
```

This matches Codex's own dependency graph in its report; the P1a/P1b split Codex already applied is
precisely what makes a simple linear ship-order accurate rather than aspirational.

## Verification

`memory-seed doctor` and `memory-seed links check` both re-run clean before and after this pass's
edits (baseline confirmed clean prior to touching any Codex-modified file, per this repo's own
concurrent-writer discipline that `agent-fanout-workflow-plan.md` itself now documents).

## Status

All items from this evaluation are either already applied (this file), reconciled as already handled
by the concurrent Codex pass (see table above), or captured as their own new proposal doc
(`exclude-superseded-filter-plan.md`). No further research loop is open.
