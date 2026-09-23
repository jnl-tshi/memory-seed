---
title: "Task Packet source following and subagent orientation lite"
date: "2026-09-23"
project: "memory-seed"
status: "proposed"
priority: "P1"
next_action: "JNL reviews this plan and confirms the D1-D4 readings; implementation starts only after approval."
source:
  - "docs/2_Todo/task-packet-hardening-progressive-provenance-plan.md"
  - "experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md"
  - ".memory-seed/decisions/adr_orientation_completion_gate.md"
scope: "Make Task Packets follow decision S: sources, replace embedded full rules with a digest-pinned subagent orientation-lite skill plus lazily loaded full rules, back the session-writing rule with mechanical enforcement, and remove residual Reflection artifacts."
non_goals:
  - "Do not change the six immutable v1 Retrieval Profiles or what they compile to."
  - "Do not resume Seed Pod, progressive-provenance expansion, or the calibration M1-M5 programme."
  - "Do not rename experiment files cited by session entries."
---

# Task Packet source following and subagent orientation lite

Status: **PROPOSED — awaiting JNL approval.** Written from the 2026-09-23 design discovery with JNL.

## Why

Task Packets are compiled and hardened, but they are not used. Evidence on 2026-09-23:

- The retrieval log has no task-packet events.
- The last activation receipts are from 2026-09-08, all on Reflection or Seed Pod work.
- The 2026-09-05 clause projection cut packets by 44-46%.
- The 2026-09-06 Ada fix then embedded the full `agent-rules.md` (about 20 KB, roughly 5k tokens) in every packet, and the full `session_logging.md` (about 46 KB, roughly 11.5k tokens) in session-writing packets. By estimate this cancels the saving; the size was never re-measured.
- Packets also ignore decisions' `S:` sources, so orchestrators had to name plans and specs by hand in each dispatch.

## Discovery decisions (JNL, 2026-09-23)

- **D1 — Follow `S:` by default, one hop.** When a decision is selected, its `S:` references are included.
  A ref with an anchor contributes that section; a ref without one contributes the whole file. Sources are
  budget-capped and digest-pinned. Missing or over-budget refs are listed, never silently dropped. A dispatch
  can turn this off.
- **D2 — Full rules become lazily loaded; packets embed orientation lite.** *Reading to confirm:* packets
  stop embedding the full `agent-rules.md` and `session_logging.md`, and embed a new subagent
  orientation-lite skill instead. The full files are referenced by path and digest, not embedded, and lite
  states exactly when each must be loaded. Their digests stay in the packet fingerprint, so a rules change
  still changes the packet.
- **D3 — One file, two delivery paths.** Packets embed the lite skill with its digest. Plain subagents
  without packets get a one-line instruction to read it first. Neither path loads `orientation.md` or the
  full index.
- **D4 — Seed it as a core skill.** Orientation lite ships to every Memory Seed project.

## Constraints the design must honour

1. **Lazy loading must not reopen the Ada gap.** The Ada worker skipped a rule it was supposed to read, so
   "load it if needed" fails the same way unless the tooling enforces it. Today, a future heading timestamp is
   only an advisory (`check_entry_timestamp_advisories` in `core.py`), and nothing stops a hand-authored
   entry. The mechanical backstop in T3 is therefore a prerequisite for T5.
2. **v1 profiles and packets are immutable.** Following `S:` ships as new profile versions (or a v2
   Retrieval Specification field) that default to following. Recompiling an existing v1 dispatch must produce
   the same bytes.
3. **The packet shape is versioned.** `worker_baseline` is part of `task-packet` v1, the activation receipt
   and both managed `prepare-commit-msg` hook copies. The change ships as `task-packet` v2, and the hooks
   accept both v1 and v2 during transition.
4. **Governance precedence stays intact.** `adr_orientation_completion_gate` makes the AGENTS.md → agent-rules
   chain mandatory before any task action. Orientation lite needs that ADR to be evolved to cover workers:
   primary sessions complete the full chain, and workers complete the lite gate. The collaboration skill's
   Worker Context Contract already excludes broad orientation for workers.

## Tasks

Dependencies are listed per task. The orchestrator owns shared contracts, control-plane files and integration.

- **T0 — Baseline measurement.** Depends on: none.
  - Compile the pilot fixture and the four frozen Seed Pod dispatches as they are today.
  - Record serialized, baseline-component and envelope tokens.
  - Done when a committed measurement table exists in the evaluation log.
- **T1 — Reflection residue cleanup.** Depends on: none.
  - Delete the empty, untracked `.memory-seed/reflections/` folders.
  - Correct the stale Reflection docstring at `core.py` `_declared_entry_ids`, keeping its still-valid anchoring logic.
  - Do not rename `REFLECTION_LOG.md`.
  - Done when a search of `memory_seed/`, the seed templates and `.memory-seed/skills/` finds no live Reflection reference.
- **T2 — Following `S:` sources.** Depends on: T0.
  - Add following to the resolver behind a new selector, with new profile versions that default it on.
  - Resolve refs at the pinned corpus revision.
  - Map `CONSTITUTION.md` anchors to clause projection, never to the full-document fallback.
  - Keep excluding `index.md`, `policy.md` and `agent-rules.md`.
  - Remove duplicates against already selected ADRs and clauses.
  - Apply a per-source cap; for example, `functionality-audit.md` alone is 94 KB.
  - Label refs into `7_Replaced/` or archived documents and add their successor pointer; don't silently follow them.
  - List missing and external refs in the packet.
  - Tests:
    - v1 recompiles byte-identical;
    - anchored and unanchored refs;
    - the constitution-anchor mapping;
    - the exclusion list;
    - deduplication;
    - the cap and its reporting;
    - replaced-document labelling;
    - determinism;
    - CLI/MCP parity.
- **T3 — Mechanical session-write backstop.** Depends on: none.
  - `session merge-branch`, fuse and the MCP integrate path refuse a future-dated heading.
  - They also refuse an entry whose metadata or sidecar identity shows it was not written by the canonical append writer.
  - Whether a hand-authored entry can be detected without false positives on legitimate backfills is decided within this task. If it can't, only future dates are enforced, and that limit is stated.
  - Tests cover each refusal path and the backfill exception.
- **T4 — Orientation-lite skill and subagent index.** Depends on: none.
  - Write `.memory-seed/skills/subagent_orientation.md`: a compact rules core, plus a routing index that says which skill to load for which objective.
  - Target at most about 1.5k tokens.
  - The inline rules must include:
    - verifying the measured worktree, branch and base SHA;
    - staying within the file scope;
    - never writing shared control-plane or memory files;
    - writing sessions only through `memory_session_append` or `session append` with the automatic clock, and never hand-editing a session file or passing a timestamp;
    - the STOP categories;
    - the return contract.
  - Explicit triggers: "before any session write, load `session_logging.md`", and "for anything outside your packet's scope, load `agent-rules.md`".
  - Add a drift test tying lite's required invariants to marked sections of `agent-rules.md`.
- **T5 — `task-packet` v2 carrying lite.** Depends on: T3, T4.
  - Embed lite with its digest, and add lazy references (path and digest) for the full rules.
  - Keep the full-rules digests in the fingerprint.
  - Update the activation receipt, both hook copies and their seed twins, and have the hooks accept v1 and v2.
  - Update `test_task_packet*`, `test_hooks` and the pilot fixture, re-recording any pinned fingerprint.
- **T6 — Delivery and governance wiring.** Depends on: T4.
  - Add the one-line "read `subagent_orientation.md` first" instruction to `agent_collaboration.md` for plain subagents, and route packet workers to the embedded copy.
  - Evolve `adr_orientation_completion_gate` for the worker scope, through the ADR review gate.
- **T7 — Seed as a core skill.** Depends on: T4, T6.
  - Add it to `CORE_SKILL_NAMES`, both trigger registries, the seed inventory, and the rule that live and seed copies stay identical.
- **T8 — Usage instrumentation.** Depends on: none.
  - Log task-packet compile, preview and activate calls as their own event type in the retrieval log, excluded from attention scoring.
- **T9 — After measurement and review.** Depends on: T2, T5.
  - Recompile the T0 set and report the change per component.
  - Get an independent review of the whole slice before integration.

## Acceptance

- A v2 packet for a session-writing worker is smaller than its T0 v1 baseline by at least the removed rules
  tokens minus the lite skill, with the change reported per component.
- An existing v1 dispatch recompiles byte-identical.
- The integration path refuses a future-dated session entry. The hand-authored entry check is either enforced
  or documented as a stated limit.
- A decision's anchored `S:` source appears in the packet exactly once, pinned by digest. A `CONSTITUTION.md`
  anchor yields clause projection.
- A plain subagent given only the lite instruction has what it needs to verify its scope and write a session
  entry safely. Its return follows the lite contract.
- Task-packet usage appears in the analytics log.

## Disposition of the older plan

Proposal for JNL: move `task-packet-hardening-progressive-provenance-plan.md` to `7_Replaced/` with a pointer
to this plan.

- Its compiler items are delivered.
- Its Seed Pod steps lapsed when Seed Pod was deferred.
- Its dogfooding goal moves to this plan, and to the P0.2 workers as the first real consumers.

The calibration harness plan stays separate and unchanged.
