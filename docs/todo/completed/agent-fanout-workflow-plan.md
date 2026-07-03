---
memory-system-version: 2.13
tags:
  - memory-seed
  - plan
  - agent-collaboration
  - workflow
---

# Fan-Out Agent Workflow - Scope

> **Status: IMPLEMENTED 2026-07-03 (unreleased).** The named "Fan-Out Recipe: Explore / Plan /
> Implement / Validate" (9 gates), the task-packet field additions, and the capability-tier guidance
> below now live in `.memory-seed/skills/agent_collaboration.md` (live + seed twin, byte-identical).
> The CLI scaffolding sketch remains a future evaluation only. Source: an internal multi-agent
> fan-out evaluation of a user-uploaded workflow diagram
> (`docs/inbox/multi-agent-fanout-review-workflow.jpeg`), not the external
> `Memory-Seed Logic Capture Improvement.md` review that the other plan docs derive from.

Four documents evaluated the same source image independently (two initial evaluations, then two parallel syntheses of those two — one by this agent, one by a concurrent Codex session). All four converged on the same verdict. This is the single, consolidated version: nothing here contradicts any source: it's the union, deduplicated.

## Executive summary

1. Add a named recipe to `.memory-seed/skills/agent_collaboration.md` — an optional Level 2/3 pattern, not default behavior. The Scope Gate must state why Level 0/1 is insufficient.
2. Strengthen the existing task-packet contract with identity/base-verification and ownership fields.
3. Add a bounded review→rework loop with a hard iteration cap — the original diagram's most distinctive feature, and the one thing both syntheses had to reconstruct because a purely linear write-up loses it.
4. Keep parallel implementers optional and rare — nothing done in this project so far has needed them.
5. Keep Memory Seed out of hosted agent orchestration. Local-first Markdown/Git scaffolding only, and only if this proves useful in practice.

## What each source contributed

- **Original report** (`multi-agent-fanout-review-workflow-report.md`): the vendor-neutral translation table, an 8-gate pipeline, a branch/worktree naming protocol, and the flag that **shared files — session logs, lockfiles, seed templates, control-plane files — are high-risk** under concurrent writers.
- **Original recommendations** (`multi-agent-workflow-evaluation-recommendations.md`): a **live, reproduced bug** (a research subagent silently running 3 commits behind real `main`, no verification catching it) and the **bounded review→rework loop**, which the original report's linear pipeline dropped entirely.
- **This agent's synthesis**: connected the shared-file risk to a mitigation Memory Seed already has — the participant-count gate on `session_target()` — generalized to "route shared/control-plane writes through the orchestrator only," without treating worker agents as project participants by default.
- **Concurrent Codex synthesis** (`multi-agent-workflow-memory-seed-proposal.md`): a dedicated Worker Identity Gate with concrete preflight commands, a capability-tier table covering every stage (not just planning vs. review), a task-packet YAML schema diff, an explicit "what not to build yet" list, and a concrete later-productization sketch (a `memory-seed workflow fanout` CLI scaffold).

## The gates

1. **Scope Gate** — objective, non-goals, acceptance criteria, base branch/SHA, expected integration artifact, high-risk/shared files, and an explicit call on whether parallel implementation is even justified (default: no, unless file ownership is clearly separable and the risk/wall-clock reduction justifies the integration overhead). The gate must also state why Level 0/1 direct work is insufficient.
2. **Exploration Gate** — read-only agents, each given one narrow question, returning evidence (relevant files, constraints, risks, open questions) — recommendations labeled as such, not stated as fact. Explorers may safely share the current tree since they never write — that exemption covers write-collision safety only, not staleness. Explorers must still satisfy `.memory-seed/policy.md`'s Safety rule (verify `pwd`/`git rev-parse HEAD` against the intended base before trusting their own reads or citations): the bug that originally motivated this whole workflow (a research agent silently three commits behind real `main`) was a read-only Exploration-role failure, not a Worker Identity Gate failure, so the Worker Identity Gate alone would not have caught it.
3. **Plan Gate** — a single orchestrator reconciles explorer conflicts, chooses the architecture, assigns file ownership and interfaces, defines validation commands, and names the conflict-resolution owner. **Use the strongest available capability tier here — same as review, not lighter.** A weak plan poisons every downstream worker; review only catches what's already built.
4. **Worker Identity Gate** — before a worker touches any file, it reports:
   ```text
   pwd
   git rev-parse --show-toplevel
   git rev-parse HEAD
   git status --short
   ```
   The orchestrator verifies this matches the task packet's intended worktree and base commit before the worker proceeds. Not precautionary — this exact failure mode (silent stale-tree inheritance) was reproduced live during this evaluation.
5. **Worktree Gate** — parallel code-writing workers get separate Git worktrees, each with a bounded task packet (owner, base branch/SHA, working branch, worktree path, objective, allowed/forbidden files, validation commands, handoff output, conflict-escalation trigger, shared-file policy). Workers must not touch shared memory/session/control-plane files unless explicitly assigned — those stay orchestrator-owned.
6. **Pre-Review Validation Gate** — each worker commits its own work and reports changed files, checks run, failures, skipped checks (and why), and known risks, *before* review — not only after. No uncommitted worker state gets integrated.
7. **Integration Gate** — the orchestrator merges worker branches one at a time into an integration branch; inspects the diff after each merge; resolves conflicts only via the named owner; reruns targeted validation for the affected surface. No octopus merges for code — they hide integration reasoning.
8. **Bounded Review-to-Rework Loop** — an independent validator (same strong tier as planning) reviews the integrated diff against the original plan. If it finds problems, findings route back to the Worktree Gate for revision — **capped at a fixed number of iterations (default: 2), then automation stops and produces a human decision summary.** The loop tracks `review_loop.current_iteration`; it must not restart exploration or planning automatically. This restores the original diagram's loop-back arrow without letting it become an unbounded automated loop, matching this project's existing bias toward bounded automation (the evolution-nudge hook was deliberately never shipped; the identity-offer hook is deliberately one-shot).
9. **Final Handoff Gate** — output is an integration artifact (PR, merge request, patch, final branch, or local handoff summary), including base SHA, worker branches/worktrees used, validation evidence, review result, unresolved risks, and any memory/session notes — written by the orchestrator, not the workers. Once `git-commit-entry-linking-plan.md` ships, the orchestrator also backfills the handoff session entry's `commits:` field from workers' reported commit hashes — the orchestrator already owns writing that entry (see Memory And Session Policy in `agent_collaboration.md`), and this stays within that plan's append-only scoping (current/newest entry, same turn) since the handoff entry is written in the same turn the commits become known.

## Task packet schema additions

The existing task packet in `agent_collaboration.md` is close. Add or emphasize:

```yaml
base_sha: "<commit hash workers must verify>"
expected_pwd: "<worktree path or repository root>"
integration_artifact: "pr|merge-request|patch|branch|handoff"
capability_tier: "economy|standard|frontier"
conflict_owner: "<orchestrator|worker|human>"
shared_file_policy: "orchestrator_only"
review_loop:
  current_iteration: 0
  max_iterations: 2
  escalation: "<human-or-orchestrator>"
preflight:
  - "pwd"
  - "git rev-parse --show-toplevel"
  - "git rev-parse HEAD"
  - "git status --short"
```

Keep these as portable Markdown/YAML conventions, not platform-specific API requirements.

## Capability tier guidance

Vendor-neutral tiers only — never provider or model names (providers change; roles and capability requirements are durable).

| Stage | Recommended tier | Reason |
|---|---|---|
| Exploration | economy or standard | Narrow, evidence-gathering tasks can be cheap if scoped tightly. |
| Planning | **frontier** | Plan quality determines every downstream worker's output. |
| Implementation | standard | Most work is bounded by the task packet and tests. |
| Integration | frontier or senior orchestrator | Merge reasoning is architecture work, not just conflict resolution. |
| Review | **frontier** | Needs adversarial reasoning across the whole integrated diff. |

Planning and review both warrant the top tier — not review alone, as the original diagram implied. A weak plan is more expensive to catch later than a weak review.

## Shared-file / control-plane risk

Session logs, lockfiles, seed templates, and control-plane files are exactly what this pattern is most exposed to — concurrent writers can interleave or violate append-only ordering. Memory Seed already has a partial, real mitigation in the session-log case: the participant-count gate on `session_target()` (per-user files only activate once 2+ human participants are registered). That lesson generalizes here without registering worker agents as participants: workers are handoff-only by default, and `shared_file_policy: orchestrator_only` routes all durable-memory writes (session log, `index.md`/`policy.md` updates), lockfile changes, seed-template edits, routing files, control-plane docs, and generated binary artifacts through the orchestrator unless a task packet explicitly delegates ownership.

## Document-rendering workflow synergy

The Windows DOCX render lessons strengthen this recipe's bounded-automation and verification-split rules. For DOCX/render workflows, fanout is useful for read-only visual QA agents that inspect rendered page images or contact sheets. Actual DOCX mutation, LibreOffice/Word automation, stale-process cleanup, and final render ownership should stay single-writer/orchestrator-owned because those operations are stateful, hard to merge, and sensitive to local Windows process behavior.

## When to use / avoid

**Use for:** medium-to-large separable work — migrations, feature slices, broad test expansion, refactors with clear module boundaries, or time-sensitive work where parallelism meaningfully cuts wall-clock time.

**Avoid for:** small bug fixes or doc edits, tightly-coupled refactors where one coherent design matters more than speed, or work dominated by shared/control-plane files.

## What not to build yet

- A hosted agent orchestrator.
- Memory Seed spawning agents directly.
- Parallel implementers as the default.
- Registering worker agents as project `participants:` by default.
- The full workflow added to always-read `agent-rules.md` (belongs in the lazy-loaded skill; `agent-rules.md` already states the correct abstraction — use the lowest orchestration level that safely completes the work).
- Unbounded reviewer/reworker loops.

## Possible later productization

If this recipe proves useful across repeated sessions, consider a local-first scaffolding command that emits files but never coordinates agents, spawns agents, mutates branches, or opens worktrees itself:

```text
memory-seed workflow fanout --topic <slug> --workers 2 --dry-run
```

Possible outputs: task-packet Markdown files, suggested branch/worktree names, a validation checklist, a reviewer checklist, and a final handoff template. The first version should be `--dry-run` / preview-first. Keeps Memory Seed focused on durable local memory and workflow artifacts, not runtime orchestration.

## Where this fits, and next action

Both independent syntheses converged on the same placement — a strong signal it's correct:

- A named recipe inside `.memory-seed/skills/agent_collaboration.md` (e.g. "Fan-Out Explore / Plan / Implement / Validate"), loaded lazily, not added to always-read `agent-rules.md`.
- Role labels and capability tiers only, never vendor/model names.

If and when this moves from proposal to implementation:

1. Update `.memory-seed/skills/agent_collaboration.md` with the named recipe and the 9 gates above.
2. Mirror the change into the seed twin (`memory_seed/seed/.memory-seed/skills/agent_collaboration.md`) for parity.
3. Add or update a parity/schema test if one covers seeded skill content, matching how other skill changes in this project are verified.
4. Leave the CLI scaffolding idea as a future `docs/todo/` proposal only after the runbook has actually proved useful in practice.

## Status

Still a proposal only. No implementation started. This file supersedes the four intermediate evaluation/synthesis drafts, which were deleted once this consolidated version was written; the source image (`docs/inbox/multi-agent-fanout-review-workflow.jpeg`) remains in `docs/inbox/` for provenance.
