---
title: "Task Packet source following and subagent orientation lite"
date: "2026-09-23"
project: "memory-seed"
status: "completed"
shipped: "2026-09-24"
priority: "P1"
next_action: "Completed 2026-09-24 (T0-T10). Deferred follow-ups are carried in docs/2_Todo/0_NEXT_STEPS.md."
source:
  - "docs/2_Todo/task-packet-hardening-progressive-provenance-plan.md"
  - "experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md"
  - ".memory-seed/decisions/adr_orientation_completion_gate.md"
scope: "Make Task Packets follow decision S: sources, replace embedded full rules with a digest-pinned subagent orientation-lite skill plus digest-verified on-demand full rules, back session writing with mechanical enforcement, and remove residual Reflection artifacts."
non_goals:
  - "Do not change the six immutable v1 Retrieval Profiles, the v1 packet, or any byte they compile to."
  - "Do not resume Seed Pod, progressive-provenance expansion, or the calibration M1-M5 programme."
  - "Do not rename experiment files cited by session entries."
  - "Do not add usage instrumentation or move the older hardening plan here; both are separate follow-ups."
---

# Task Packet source following and subagent orientation lite

Status: **COMPLETED 2026-09-24 (T0-T10)**; evidence in [`experiments/task-packet-sources-lite/RESULTS.md`](../../experiments/task-packet-sources-lite/RESULTS.md). Final independent review: session entry `mse_yz25a19sdq9akxmh`. Previously: revision 2, approved by JNL. Written from the 2026-09-23 design discovery with
JNL. Revised after an independent review returned REVISE with three blocking, four major and three minor
findings. Every finding is addressed below.

## Why

Task Packets are compiled and hardened, but they are not used. Evidence on 2026-09-23:

- The retrieval log has no task-packet events.
- The last activation receipts are from 2026-09-08, all on Reflection or Seed Pod work.
- The 2026-09-05 clause projection cut packets by 44-46%.
- Decision `mse_481b9y78d5t4ct3x:d1` (2026-09-06, the Ada incident) then embedded the full `agent-rules.md`
  (20,372 bytes) in every packet, and the full `session_logging.md` (45,904 bytes) in session-writing
  packets. By estimate this cancels the saving; the size was never re-measured.
- Packets also ignore decisions' `S:` sources, so orchestrators had to name plans and specs by hand in each
  dispatch.

## Discovery decisions (JNL, 2026-09-23)

- **D1 — Follow `S:` by default, one hop, on a new path only.** When a decision is selected, its `S:`
  references are included. A ref with an anchor contributes that section; a ref without one contributes the
  whole file. Sources are budget-capped and digest-pinned. Missing, forbidden or over-budget refs are listed,
  never silently dropped. A dispatch can turn this off. The v1 profiles are unchanged.
- **D2 — Lite is sufficient for ordinary work; the full rules load on demand.** Packets embed a new subagent
  orientation-lite skill instead of the full `agent-rules.md` and `session_logging.md`.
  - Lite alone is enough for ordinary work, including a normal session append. This is safe because the
    append tool itself mechanically enforces clock ownership, future-date refusal and entry structure (T3).
  - The full `session_logging.md` is loaded only for repair or backfill, lifecycle edges, ADR-linked writes,
    or when an append is refused. The full `agent-rules.md` is loaded only for work outside the packet's scope.
  - Each full rules file is listed by path and digest, and loaded through a digest-verified governance load
    (T5) that does not spend the supplemental reserve.
  - Their digests stay in the packet fingerprint, so a rules change still changes the packet.
- **D3 — One file, two delivery paths.** Packets embed the lite skill with its digest. Plain subagents
  without packets, including Claude Code subagents, which do not receive the SessionStart hook, get a
  one-line instruction in their spawn prompt to read it first. Neither path loads `orientation.md` or the full
  index.
- **D4 — Seed it as a core skill.** Orientation lite ships to every Memory Seed project, with the live and
  seed copies kept identical.

## Constraints the design must honour

1. **The v1 output must stay byte-identical.** `normalize_retrieval_spec_v2` always writes every selector key
   (`retrieval_spec.py:309-315`), and `_PROFILE_BASE_SPEC` lists them. A new key with a default would change
   `effective_spec_fingerprint` for all six v1 profiles. The same is true of `RETRIEVAL_V2_RESOLVER_VERSION`
   and `EVIDENCE_PACK_VERSION` (`retrieval.py:374-377`), which are embedded in packets and checked by the hook.
   So source following must either leave its key out when off, or live in a new spec version. Resolver and
   Evidence Pack versions change only on that new path.
2. **Loading the full rules on demand must not be refused or starved.**
   `validate_task_packet_supplemental_fetch` (`task_packet.py:998-1004`) refuses re-reads of `worker_baseline`
   sources and charges every other read to `supplemental_input_reserve_tokens`. A lazy read of
   `session_logging.md` could therefore fail with `supplemental_budget_exceeded`, which would recreate the Ada
   gap through budget rules. Governance loads need their own digest-verified path, outside the reserve.
3. **The mechanical backstop comes before removing the embedded rules.** A future heading timestamp is only
   an advisory today (`check_entry_timestamp_advisories`, `core.py:2538-2545`, reported as a warning).
   `session append --timestamp` (`cli.py:781`) and MCP append accept future timestamps, subject only to
   chronology. T3 must land before T5.
4. **The corpus revision is not a git snapshot.** `_retrieval_corpus_revision` (`retrieval.py:448-525`)
   hashes selected inputs: the Constitution, `topics.yaml`, sessions, filter paths and, conditionally,
   decisions. `S:` resolution (`semantic_cache.py:970-985`) and `materialize_evidence_pack`
   (`task_packet.py:1444-1465`) read the live working tree. So followed `S:` files must join the revision
   inputs when the new selector is on, or a change to them would go undetected.
5. **The packet shape is versioned.** `worker_baseline` belongs to `task-packet` v1. Both managed hook copies
   accept only v1 (`packet_version != 1` fails, line 217). The change ships as `task-packet` v2, and the
   hooks accept both.
6. **Governance must be updated before anything depends on it.**
   - `adr_orientation_completion_gate` makes the AGENTS.md → agent-rules chain mandatory before any task
     action. It must be evolved through the ADR review gate before lite replaces that chain for workers.
   - Decision `mse_481b9y78d5t4ct3x:d1` must be formally replaced, not silently reversed. The 2026-09-23
     planning entry `mse_3pgpkt9f5kga1mxj` records only a `refines` edge.

## Tasks

Dependencies are listed per task. The orchestrator owns shared contracts, control-plane files and integration.

- **T0 — Baseline measurement.** Depends on: none.
  - Compile the pilot fixture and the four frozen Seed Pod dispatches as they are today.
  - Record serialized tokens, baseline component tokens, envelope tokens and fingerprints in the evaluation log.
- **T1 — Reflection residue cleanup.** Depends on: none.
  - Delete the empty, untracked `.memory-seed/reflections/{active,trust}` folders.
  - Correct the stale Reflection docstring in `core.py` `_declared_entry_ids` (line 2690), keeping its
    still-valid anchoring logic.
  - Do not rename `REFLECTION_LOG.md`.
  - Done when a search of `memory_seed/`, the seed templates and `.memory-seed/skills/` finds no live Reflection
    reference.
- **T2 — Governance update.** Depends on: none.
  - Evolve `adr_orientation_completion_gate` through the ADR review gate: primary sessions complete the full
    chain, and workers complete the lite gate.
  - Record a decision that replaces `mse_481b9y78d5t4ct3x:d1`.
  - Accepted governance is a precondition for T6 and T8.
- **T3 — Mechanical session-write backstop.** Depends on: none.
  - Refuse a heading timestamp more than the existing 10-minute grace (`core.py:2535`) in the future. This
    applies at CLI and MCP append, and at `session merge-branch`, fuse and MCP integrate.
  - Keep the explicit-timestamp path for the dry-run echo (the returned timestamp) and for labelled backfill.
  - Detecting hand-authored entries has no reliable marker today, so the default outcome is to document it as
    a stated limit. Add detection only if this task finds a marker without false positives.
  - Tests cover each refusal path, the dry-run echo and the backfill exception.
- **T4 — Orientation-lite skill and subagent index.** Depends on: none.
  - Write `.memory-seed/skills/subagent_orientation.md` and its seed copy: a compact rules core, plus a
    routing index that says which skill to load for which objective. Target at most about 1.5k tokens.
  - The inline rules must include:
    - verifying the measured worktree, branch and base SHA;
    - staying within the file scope;
    - never writing shared control-plane or memory files;
    - writing sessions only through `memory_session_append` or `session append`, with the automatic clock, and
      never hand-editing a session file;
    - passing a timestamp only when echoing one a dry run returned;
    - the STOP categories;
    - the return contract.
  - Explicit triggers for the D2 on-demand loads.
  - Add a drift test tying lite's required invariants to marked sections of both the live and seed
    `agent-rules.md`.
- **T5 — Governance-load path.** Depends on: T4.
  - Add a load for governance sources that is separate from the supplemental reserve. It returns the file only
    when the live bytes match the packet's pinned digest, and otherwise refuses with a stale-governance error.
  - Session-writing v2 packets must declare it.
  - Tests cover a successful load, a digest mismatch, the reserve being untouched, and a v1 packet (where
    `worker_baseline` re-read refusal is unchanged).
- **T6 — Following `S:` sources.** Depends on: T0, T2.
  - Add the selector as a key that is absent when off, or as a new Retrieval Specification version, together
    with new profile versions that default it on.
  - When on, include followed files in the corpus-revision inputs, and bump resolver and Evidence Pack versions
    only on that path.
  - Resolve anchors as the section under the matching heading slug, falling back to the whole file with a
    listed warning when the slug doesn't exist.
  - Map `CONSTITUTION.md` anchors to clause projection, never to the full-document fallback.
  - Exclude `index.md`, `policy.md`, `agent-rules.md`, non-Markdown files and `_FORBIDDEN_RETRIEVAL_PATH_PARTS`,
    and list each exclusion.
  - Remove duplicates against selected ADRs and clauses, and apply a per-source cap (for example,
    `functionality-audit.md` is 93,910 bytes).
  - Label refs into `7_Replaced/` or archived documents and give their successor pointer; don't follow them.
    Refs that `semantic_cache` resolves as moved are listed, not followed.
  - Tests:
    - all six v1 profiles recompile byte-identical, with fingerprints unchanged;
    - anchored, unanchored and missing-slug refs;
    - the constitution-anchor mapping;
    - exclusions;
    - deduplication;
    - the cap and its reporting;
    - replaced and moved labelling;
    - corpus-revision sensitivity to a followed file;
    - determinism;
    - CLI/MCP parity.
- **T7 — Before measurement.** Depends on: T6. Recompile the T0 set with source following on, and record the
  change before T8 changes the packet shape.
- **T8 — `task-packet` v2 carrying lite.** Depends on: T2, T3, T5, T7.
  - Embed lite with its digest, and add references (path and digest) for the full rules.
  - Keep the full-rules digests in the fingerprint, and declare the governance-load path.
  - Update the activation receipt and both hook copies:
    - v1 validation stays unchanged;
    - v2 validates lite's content and digest, and only the shape and digest fields of the lazily loaded
      references, since the hook does not re-read files.
  - Update `test_task_packet*`, `test_hooks`, `tests/test_session_schema.py` (task-packet schema, about line
    749) and the pilot fixture. Test both hook copies with v1 and v2 packets.
- **T9 — Delivery wiring and seed.** Depends on: T2, T4.
  - Add the "read `subagent_orientation.md` first" spawn-prompt line to `agent_collaboration.md` and its seed
    copy.
  - Add lite to `CORE_SKILL_NAMES` (`core.py:10150`), `skills/index.md` and the `SKILL_PROFILES` descriptions,
    the seed inventory, and the parity check that keeps live and seed copies identical.
- **T10 — After measurement and review.** Depends on: T8, T9.
  - Recompile the T0 set as v2.
  - Report the per-component change against both T0 and T7, including the tokens a session-writing worker
    would spend on an on-demand load.
  - Get an independent review of the whole slice before integration.

## Acceptance

- An existing v1 dispatch, under each of the six v1 profiles, recompiles byte-identical with an unchanged
  fingerprint. *Scope note (2026-09-24):*
  - This criterion covers the new switches: source following and packet v2.
  - Two fixes that JNL separately approved change v1 packet bytes on purpose:
    - the Constitution anchor rename (correction 2.3);
    - the ranked-clause cap, which replaces the 2026-09-05 keep-every-ranked-clause rule.
  - v1 packets were already corpus-dependent through their corpus revision.
- For ordinary work, a v2 session-writing packet is smaller than its T0 baseline. Measured totals, including
  any on-demand governance load a worker makes, are reported per component, not assumed.
- Append and integration refuse a heading timestamp beyond the grace window, except for a dry-run echo and a
  labelled backfill. The hand-authored entry check is enforced, or documented as a stated limit.
- A governance load returns the pinned bytes, or refuses on a digest mismatch, without touching the
  supplemental reserve.
- A decision's anchored `S:` source appears exactly once, pinned by digest, and changing it changes the corpus
  revision. A `CONSTITUTION.md` anchor yields clause projection.
- A plain subagent given only the lite instruction can verify its scope and complete a normal session append
  that the tooling accepts. Its return follows the lite contract.
- The hooks accept valid v1 and v2 packets and reject tampered ones, in both the live and seed copies.

## Deferred follow-ups

- Usage instrumentation: log compile, preview and activate calls to the retrieval log as their own event type.
- Disposition of `task-packet-hardening-progressive-provenance-plan.md`. Proposal: move it to `7_Replaced/`
  with a pointer here, since its compiler items are delivered and its Seed Pod steps lapsed.
- P0.2 workers as the first real consumers of v2 packets.

The calibration harness plan stays separate and unchanged.
