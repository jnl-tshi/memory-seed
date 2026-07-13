> Status: EXECUTED TO COMPLETION 2026-07-10. All four phases ran the same day: alignment
> audit (3 reviewers, 4 user decisions), consolidation, assumption-review swarm (4 reviewers,
> 4 approved fixes), and stages S2-S6 each as one revertable merge commit - including the
> v2.17.0 release. Stage-to-merge-commit map: `0_NEXT_STEPS.md`.

---
memory-system-version: 2.18
tags:
  - memory-seed
  - goal
  - roadmap
---

# Goal: Roadmap Refinement, Assumption Review, and Staged Implementation

> **Status:** Goal directive - authored 2026-07-10 from the user's stated intent. This document is
> the durable driver for a multi-phase run: it must be executable by a fresh session after
> context compaction without needing the conversation that produced it.
> **Approval authority:** the user (Jean). Nothing is added to any plan, design, or codebase
> without the user's explicit knowledge and approval.
> **Scope:** the Active Roadmap in `docs/2_Todo/0_NEXT_STEPS.md` - every active/proposed plan plus
> the recorded residuals (evolution-edges lineage seeding pass, Trace lineage pass, and any plan
> whose status block names remaining work).

## Standing rules (every phase)

- Follow `AGENTS.md` and the `.memory-seed/` read order before starting; establish current state
  from the newest session file, topical context via `memory_search`.
- Decision gates use AskUserQuestion with a recommendation; risk posture follows
  `risk_signaling.md` (shared-contract and design changes are propose-and-wait).
- Session-log every meaningful unit per `session_logging.md`, running the full Decision Harvest
  including the lifecycle prompts (`supersedes`/`evolves`/`related_entries`) and the continuity
  prompt (record `continuity:` on any rename/relocation/removal).
- All feature work on task branches; integrate one branch at a time with
  `memory-seed session merge-branch --branch <branch>` (clean tree required; `session fuse` is the
  fallback for manually inspected merges).
- Validation gates per change: full `python -m unittest discover -s tests`,
  `python -m memory_seed.cli links check`, `git diff --check`, live/seed skill parity when skills
  are touched.
- Subagent tiers per the user's standing preference: sonnet-or-below for research fan-out,
  frontier tier for synthesis and critique. Never push to origin without explicit direction.

## Phase 1 - Plan refinement and alignment

1. Read every in-scope plan end to end. Build an alignment matrix: each plan's claims vs. the
   recorded design decisions (`docs/3_Spec/graph-edge-contract.md`,
   `docs/3_Spec/functionality-audit.md`, session entries retrieved by topic). List every gap,
   contradiction, stale status line, or undefined behavior.
2. Classify each finding: (a) resolvable from recorded decisions - propose the exact fix;
   (b) genuinely open - queue a user question. Batch the questions (AskUserQuestion, with a
   recommended option) so no area of implementation uncertainty survives this phase.
3. Blindspot hunt: actively surface what the user has *not* asked about - failure modes,
   migration/compatibility, multi-user/team implications, release sequencing, performance
   ceilings, security/trust boundaries, retrieval-quality regressions - and raise each explicitly
   rather than silently absorbing it.
4. Where an open decision would benefit from external grounding, launch small sonnet-tier
   research subagents on industry standards and prior art; feed cited findings into the
   recommendations, labeled as evidence rather than fact.
5. **Exit gate:** the user has answered every queued question and no in-scope plan contains a
   known gap or contradiction.

## Phase 2 - Consolidation and compaction

1. Update every touched plan document with the Phase 1 resolutions - status blocks, scope,
   non-goals, dependencies, acceptance criteria per `proposal_lifecycle.md`.
2. Update the durable-fact control plane: `.memory-seed/index.md` (active state, topology,
   risks), `.memory-seed/policy.md` if behavior rules changed, skills + seed twins
   (byte-identical) where procedures changed, `docs/2_Todo/0_NEXT_STEPS.md`,
   `docs/3_Spec/functionality-audit.md`, and `CHANGELOG.md` where release-facing.
3. Run the memory-consolidation review (`memory_consolidation.md`) so stable conclusions live in
   the control plane rather than only in chat history; log the session entry.
4. **Exit gate:** signal readiness and ask the user to run `/compact`, so implementation starts
   on a clean context anchored to the updated documents. This goal file and the updated plans are
   the post-compaction drivers - assume the conversation history is gone.

## Phase 3 - Assumption review swarm

1. Launch a swarm of parallel, read-only sonnet-tier review agents, each with one bounded
   assumption class across the refined plans: internal consistency, contract alignment
   (graph-edge/validator/read surfaces), test-coverage plausibility, migration and backward
   compatibility, retrieval/ranking impact, and doc/spec drift.
2. Synthesize at frontier tier into a verdict-first report: confirmed sound / needs change /
   needs user decision - terse bullets, evidence cited.
3. Present the synthesis. **Every** proposed change - however small - is shown to the user before
   any plan is touched; apply only what is approved, then log.
4. **Exit gate:** the user signs off the plan set as implementation-ready.

## Phase 4 - Staged implementation

1. Propose a stage sequence (dependency-ordered; each stage independently valuable and
   independently revertable) and get the user's approval of the sequence itself.
2. Per stage: create `claude-feature-<slug>` -> implement -> full suite + `links check` green ->
   session entry on the branch (with `branch:` provenance; `evolves`/`supersedes`/`continuity`
   where genuinely true; diagram sidecar when a positive trigger applies) -> integrate via
   `session merge-branch` -> verify ascending chronology and the 2-parent merge commit.
   One stage = one merge commit = auditable and reversible (`git revert -m 1 <merge>` backs the
   whole feature out; the session entry records why it existed).
3. Between stages, report progress tersely: what shipped, what's next, anything discovered that
   changes the plan (which routes back through user approval, never silent scope growth).
4. **After all stages ship - docs-folder accuracy pass:** move completed plans to
   `docs/2_Todo/completed/` with final dispositions near the top; refresh `0_NEXT_STEPS.md`,
   `functionality-audit.md`, `README.md`, `CHANGELOG.md`, and `.memory-seed/index.md` to the new
   condition; repair any links that pointed at moved files; log the closing entry with the full
   stage-to-merge-commit map.

## Done means

- Every in-scope plan is either implemented (moved to `completed/` with disposition) or
  explicitly re-scoped with the user - none left ambiguous.
- Full test suite green; `links check` clean; docs accurate to the shipped state.
- Every shipped feature traceable to exactly one merge commit and one session entry, reversible
  in one revert.
