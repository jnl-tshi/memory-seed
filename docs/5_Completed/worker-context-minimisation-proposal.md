---
memory-system-version: 2.18
tags:
  - memory-seed
  - proposal
  - agent-collaboration
  - personas
  - subagents
---

# Worker Context Contract — subagent workers load a slim packet, not full operating-mode startup

Status: **SHIPPED 2026-07-17** under live user consent (the `agent-rules.md` edit is a locked-file
change; the 2026-07-14 approval authorised the work, the user authorised the edit on the day). The
Worker Context Contract lives in `.memory-seed/skills/agent_collaboration.md` with Task Packet fields
`persona:` + `context_load:`; `agent-rules.md` step 10 carries a single worker-exemption clause (its
260-line startup budget is now exactly full). Seed twins synced. Session: `mse_5ekvf2d0h5e2gw3y`.
Priority: P2 — recurring efficiency + coordination friction on every fan-out; guidance-only change (no code strictly required).
Next action: draft the "Worker Context Contract" section in `.memory-seed/skills/agent_collaboration.md` and the two Task Packet fields (`persona:`, `context_load:`), add the worker-exemption note to `agent-rules.md` "Operating Mode Start", then mirror both into the `memory_seed/seed/` twins.
Dependencies: none hard. The companion `persona-usage-deactivation-esr-proposal.md` compounds the win (fewer active personas) but is not a blocker; either can land first.
Scope: control-plane guidance only — `agent_collaboration.md`, `agent-rules.md`, seed twins. Optional lint is out of scope for the first cut.
Source: The two-axis persona/orchestration evaluation (`mse_y7nhd5hcpwa0qb51`), which surfaced the on-record friction `mse_jh2n9x7p5bq4r6cd` — *"heavy startup/persona load for every worker"* — and `mse_jg33a730vpr4085a`, where a fan-out re-derived safeguards a worker never needed.

## Problem — workers inherit the primary agent's full startup

Operating-mode startup (`.memory-seed/agent-rules.md` "Operating Mode Start", steps 1–10) is written for the **primary** agent: read the full read-order, establish current state from the newest session log, read the whole skill registry, and — step 10 — **load *all* active personas** and apply their rules. Today there are four active personas (solo-founder, developer, content-creator, copywriter).

A spawned **worker** has a bounded objective (edit these files, run these checks, return evidence). It does not need four persona operating systems, the full index, or the newest-session recency read — the orchestrator already holds current state and distilled the scope into the Task Packet. Loading all of that per worker is:

- **wasteful** — most of the context is irrelevant to a one-file task (the recorded `mse_jh2n9x7p5bq4r6cd` friction);
- **a coordination risk** — a worker steeped in whole-project context is likelier to stray outside its `allowed_files` or re-derive safeguards the packet already fixes (`mse_jg33a730vpr4085a`).

## Current behavior (grounded)

- `agent-rules.md` "Operating Mode Start" step 10: *"load all persona files with `status: active` … Apply persona rules."* No worker exemption.
- `agent_collaboration.md` Task Packet says *"Keep packets narrow. Do not hand a worker the whole repository history."* — the right instinct, but it never addresses **startup/persona load** specifically, and the packet has no field for which persona (if any) a worker should adopt.
- `agent_collaboration.md` already establishes the orchestrator owns memory/session writes and workers return handoff evidence — so workers are *already* exempt from the end-of-turn persona/skill-evolution steps in practice; that exemption is just not stated as a context contract.

## Proposal — a "Worker Context Contract" in `agent_collaboration.md` (+ agent-rules pointer + seed twins)

A worker spawned with a Task Packet **does not run full operating-mode startup**. It loads only:

1. the **Task Packet** (objective, base_sha, allowed/forbidden files, validation, handoff shape);
2. **at most one domain persona** — the slug named in the packet's new `persona:` field, or none for mechanical work;
3. **only the skills its objective triggers** (registry-matched to the packet objective), not the whole registry as an operating surface;
4. the **named context files** the packet points at.

It **skips**: loading all active personas, the full `index.md` read (the packet carries the orchestrator-distilled scope), the newest-session recency read (orchestrator holds current state), and the end-of-turn persona/skill-evolution + consolidation steps (orchestrator owns durable memory).

It **still runs** the packet `preflight` — `pwd`, `git rev-parse HEAD` vs `base_sha`, and the worktree guard. Skipping the *current-state* read never means skipping *tree verification*: this repo's stale-worktree hazard (`project_stale_worktree_subagents` — a subagent can inherit a frozen worktree) makes the base-commit check non-negotiable regardless of how light the context load is.

Task Packet gains two fields:

```yaml
persona: "<one active-persona slug, or 'none'>"   # domain voice the worker adopts; default none
context_load: "minimal"                            # minimal (worker default) | full (orchestrator)
```

The **orchestrator** still runs full startup — it owns scope, sequencing, integration, final validation, and durable logging, all of which need whole-project context.

## Non-goals

- Does not change **primary-agent** startup — the full read order stays for any agent that isn't a packeted worker.
- Does not remove, rename, or deactivate any persona (that is the companion proposal, `persona-usage-deactivation-esr-proposal.md`).
- Does not let workers write session logs or evolve personas/skills — that stays orchestrator-owned, unchanged.
- Not proposing enforcement code as a hard requirement; this is a guidance/contract change. An optional lint could confirm packets set `persona`/`context_load`, but the value is in the documented contract.

## Acceptance criteria

- `agent_collaboration.md` has a **"Worker Context Contract"** section stating the load/skip list above.
- The Task Packet template gains `persona:` and `context_load:` with the defaults above.
- `agent-rules.md` "Operating Mode Start" notes that a packeted worker follows the Worker Context Contract instead of steps 5, 7, and 10 (current-state read, full registry-as-surface, load-all-personas).
- Seed twins under `memory_seed/seed/.memory-seed/` updated to match (live/seed parity test stays green).
- Fewer active personas (companion proposal) compounds the win but is not a dependency.

## Relationship to existing coverage (checked)

- The orchestration topology (orchestrator/worker/validator, 9-gate Fan-Out Recipe, worktree isolation, namespace guard) is **already shipped** — this proposal does **not** re-touch it (see the retraction of `subagent-orchestration-contract-proposal.md`, `mse_8wr3drtm6rts42ty`). It adds only the **context-load** dimension of a worker, which no shipped doc addresses.
- Companion: `persona-usage-deactivation-esr-proposal.md` (fewer active personas → lighter load on both this contract and primary startup).
- Provenance: `mse_y7nhd5hcpwa0qb51` (two-axis evaluation), `mse_jh2n9x7p5bq4r6cd` (the recorded friction), `mse_jg33a730vpr4085a` (fan-out re-derivation lesson).
