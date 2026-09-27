---
title: "Task Packets at agent handoff points"
date: "2026-09-25"
project: "memory-seed"
status: "proposed"
priority: "P1"
next_action: "implemented 2026-09-25 (T1–T6); remaining: dogfood with the first P0.2 workers."
source:
  - "docs/5_Completed/task-packet-sources-and-orientation-lite-plan.md"
  - ".memory-seed/skills/agent_collaboration.md"
  - ".memory-seed/skills/design_discovery.md"
  - "memory_seed/planning.py"
scope: "Make Task Packets the natural seeding mechanism wherever a new agent is spawned: generate dispatches from plan tasks, render packets as spawn prompts, name the mandatory handoff points in the workflow skills, and log and report packet usage."
non_goals:
  - "Do not block writes: enforcement is soft and measured, not a guard refusal."
  - "Do not change packet v1/v2 contents, activation, or the hook contract."
  - "Do not packetize swarm workers; link/topic/ADR swarms keep their closed-list batch contracts."
  - "Do not dispatch workers or create worktrees from the compiler; spawning stays with the client."
---

# Task Packets at agent handoff points

Status: **IMPLEMENTED — T1–T6 landed 2026-09-25 (approved by JNL); P0.2 worker dogfood pending.** Written from the 2026-09-25 design discovery with JNL.

## Why

Task Packets were designed to seed newly spawned agents with the right context. But no step in the everyday
flow produces one.

- `design_discovery.md` says discovery carries "into the existing plan and Task Packet path", but no step
  turns a plan task into a dispatch.
- No spawn path compiles or renders a packet.
- Packet usage is not logged, so skipping one goes unnoticed. The whole 2026-09-23/24 session spawned
  reviewers and planners with hand-written prompts.

The pieces already exist:
- a structured `implementation_plan` (tasks with acceptance observables, edit ownership, dependencies and
  verification, validated by `planning.py`);
- packet v2 with orientation lite and digest-verified governance loads.

## Handoff points (JNL, 2026-09-25)

| # | Handoff | Seeding |
|---|---|---|
| 1 | Session-start summary worker (SessionStart hook, `orientation.md`) | Lite skill only; its input is one file |
| 2 | Discovery research fan-out (read-only investigators) | Lite skill only |
| 3 | Plan task → implementation worker (Plan Gate → fan-out) | **Mandatory:** writing v2 packet |
| 4 | Superpowers SDD workers | **Mandatory:** writing v2 packet |
| 5 | Independent reviewer or validator | **Mandatory:** read-only v2 packet (plan, decisions, diff range) |
| 6 | Spawned or next session continuing a tranche (`spawn_task`, Codex rescue, cloud handoff) | **Mandatory:** v2 packet rendered as the opening prompt |
| 7 | Link, topic and ADR swarms | Exempt: closed-list batch files already bound them |

## Discovery decisions (JNL, 2026-09-25)

- **D1 — Plans carry one structured tasks block.**
  - Tranche plans stay prose, but gain one fenced ```` ```json ```` block with
    `"schema": "memory-seed/plan-dispatch"`. It holds the `implementation_plan` in the existing
    `planning.py` schema, plus shared dispatch `defaults` and one objective per task.
  - *Amended 2026-09-25 (JNL):* the block is JSON, not YAML. PyYAML is not a package dependency, and the
    repo's strict profile YAML reader rejects realistic plan blocks.
  - `task-packet from-plan` validates the block and emits one dispatch per task. Each dispatch carries edit
    ownership as allowed files, acceptance observables, dependencies, verification and the approval
    reference.
- **D2 — Render is prompt text plus the packet file.**
  - `task-packet render` writes the canonical packet JSON and prints a client-neutral prompt containing: the
    read-lite-first line, objective, scope and allowed files, acceptance checks, the materialized evidence,
    the return contract, and the packet path and fingerprint.
  - Governance loads and activation use that file.
- **D3 — Enforcement is soft and measured.**
  - The workflow skills name handoff points 3–6 as packet-mandatory.
  - Usage is logged. ESR reports coverage: agent-namespaced branches or worktrees that committed without an
    activated packet, and reviews or spawned sessions with no render event.
  - Nothing is blocked.
- **D4 — Usage events go to the retrieval log as their own kinds.**
  - `task_packet_compile`, `_preview`, `_render`, `_activate` and `_governance_load` are appended to
    `.memory-seed/.retrieval-log.jsonl`.
  - Each event records the packet fingerprint, packet version, profile, write intent and declared handoff
    point.
  - These events are excluded from attention ranking.

## Constraints

1. **Measure the default path, not just the tool.** Events must be recorded from the CLI, the MCP server and
   the Python API alike. Otherwise ESR under-reports usage for agents that call the library.
2. **Telemetry stays derived and local.** The log is gitignored and rebuildable, never authoritative, and
   ESR reports never write memory. Logging must never make a compile fail.
3. **Attention stays clean.** `attention.py` counts only `memory_get_chunk` as a fetch. The new kinds must
   not change any attention score; add a test that asserts this.
4. **The plan schema is reused, not forked.** The structured block validates with the existing
   `validate_implementation_plan`. Adding fields needed for dispatch generation, such as the objective,
   profile or capability tier per task, is an additive schema change with its own tests.
5. **v1/v2 bytes are unchanged.** Rendering and logging read packets and never modify them.

## Tasks

- **T1 — Usage logging.** Depends on: none.
  - Add the event kinds and a single `record_task_packet_event` helper, called from the compiler, activation,
    the governance load and the render.
  - Surfaces pass a `handoff` label (`implementation`, `sdd`, `review`, `spawned-session`, or `other`).
  - The attention reader ignores the new kinds.
  - Tests: events from the CLI, MCP and Python API; logging failure never breaks a compile; attention scores
    are unchanged.
- **T2 — Structured tasks block and `task-packet from-plan`.** Depends on: none.
  - Parse one fenced `implementation_plan` block from a Markdown plan and validate it with `planning.py`.
  - Emit one dispatch per task. Allowed files come from edit ownership, observables from acceptance, and
    `implements` from task evidence references that are decisions.
  - Refuse cycles, unknown dependencies, missing ownership and absent approval.
  - Add the per-task dispatch fields as an additive, tested schema change.
- **T3 — `task-packet render`.** Depends on: T1.
  - Compile or accept a packet, write the canonical JSON, and print the D2 prompt.
  - Provide a CLI command and a read-only MCP tool (`memory_task_packet_render`), with parity tests. The
    render logs a `task_packet_render` event with its handoff label.
- **T4 — Workflow wiring.** Depends on: T2, T3.
  - `agent_collaboration.md` (live and seed): add the handoff table and the mandatory rule for points 3–6.
  - `design_discovery.md`: add a step that writes the structured tasks block at the Plan Gate.
  - `superpowers_integration.md`: SDD workers receive rendered v2 packets.
  - Point the review and spawned-session guidance at `task-packet render`.
  - Registry and drift tests updated.
- **T5 — ESR coverage report.** Depends on: T1.
  - ESR summarizes packet events since the last session.
  - It lists agent-namespaced branches and worktrees that committed without an activated packet, using the
    existing activation artifacts and `Memory-Implements` trailers.
  - It lists review or spawned-session work without a render event.
  - Advisory only.
- **T6 — Dogfood and review.** Depends on: T4, T5.
  - Use the new path for this tranche's own review (point 5), and for the first P0.2 implementation workers
    when that tranche starts.
  - Record measured packet sizes and the ESR coverage output.
  - Get an independent review of the slice before integration.

## T6 results (2026-09-25)

- **Point 5 dogfood.** This tranche's independent reviewer was seeded only from a rendered read-only v2
  packet (`--handoff review`). It returned APPROVE WITH CHANGES in the lite return format; all seven
  findings were fixed with tests before integration.
- **Measured size.** Packet file 77,102 bytes; rendered prompt 49,155 bytes. It carried 7 evidence items,
  26 anchored Constitution clauses and the 1,040-token lite skill; `agent_rules` (5,093 tokens) stayed a
  digest-pinned on-demand reference, not inline text. Cost ledger `unavailable` (no pricing supplied).
- **ESR coverage output.** "Today: compile 1, render 2. Today by handoff: review 3." Three agent branches
  merged earlier that day showed no packet evidence, as expected: they predate the handoff path.
- **Still to observe.** The first P0.2 implementation workers (point 3) are the next dogfood.

## Acceptance

- A Markdown tranche plan with one structured tasks block yields one valid dispatch per task. Invalid plans
  are refused with a named reason.
- `task-packet render` prints a prompt that a clean agent can act on without other context, and writes a
  packet file whose fingerprint matches the prompt. CLI and MCP output match.
- Every compile, render, activation and governance load, from any surface, appears once in the usage log,
  and no attention score changes.
- ESR reports packet coverage and names uncovered agent work, without failing or writing memory.
- The workflow skills name handoff points 3–6 as packet-mandatory, and live and seed copies are identical.
- The tranche's own independent review is seeded by a rendered read-only packet.
