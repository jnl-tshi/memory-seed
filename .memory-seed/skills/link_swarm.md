---
memory-system-version: 2.19
governing_adr: adr_edge_confidence
tags:
  - memory-seed
  - skill
  - link-swarm
---

# Lifecycle-Link Judgment Swarm Skill

Use this skill to enrich lifecycle edges (`replaces`/`evolves`/`related_entries`) across the corpus at
scale, when the mechanical `link audit` sweep has surfaced more candidate gaps than a human wants to
classify by hand. It is the automated **judgment** layer above the manual Lifecycle Link Sweep in
`end_of_turn.md`: `link audit` finds the pairs mechanically, a swarm of small models judges each at
decision granularity, an orchestrator validates the verdicts mechanically, and a human approves the
batch before any edge is written. Do not reach for this for one or two obvious edges — classify those
by hand per `end_of_turn.md`. This is for a backfill campaign over many gaps.

**Opt-in and cost.** The swarm calls a fan-out of models (a Workflow), so it is network-using and must
be run deliberately — never as an automatic step. Confirm with the user before launching the fan-out,
and confirm again before writing any edge. The core stays network-free (Constitution Invariant #1); the
model calls live entirely in this optional layer, and every stored edge is human-gated and authored as
an ordinary `:dN` edge with no dependency on the model that suggested it (Invariant #5).

## The pipeline

```
memory-seed link audit --json --date <today>     (core, mechanical, network-free)
    -> judgment-ready tasks: each gap carries both ends' decision bodies + criteria
Workflow fan-out                                 (optional layer, network)
    -> one haiku agent per candidate gap; each returns a verdict per the criteria below
orchestrator validation                          (mechanical-first, no new model calls)
    -> drop verdicts that fail a quote-match, a dangling ordinal, or the consistency check
batch approval                                   (the human gate)
    -> surface the surviving verdicts as one batch; the user approves, edits, or rejects
write + check
    -> approved edges written to the day's link sidecar; memory-seed links check validates
```

### 1. Mechanical recall

Run `memory-seed link audit --json --date <today>` (or `--for <entry_id>` to scope to one entry). The
JSON emits each gap as a judgment-ready task: both ends' `decisions` (ordinal + name + body), the
overlap evidence (files/topics/title), and a `criteria` block.

**Candidates arrive from TWO sources, and the payload must keep them apart.** Most come through the
lexical gate — a shared file, a distinctive title term, or an unsuppressed topic — and carry that
overlap as evidence a worker can check. Up to two more per gap carry `"ungated": true`: the gate
could not have surfaced them at all, and they are there on semantic rank alone. That second source
exists because the gate's blind spot is structural, not unlikely — an entry sharing none of those
three signals can never appear however related it is, so without it the gate, not the swarm's
judgement, sets the ceiling on every campaign.

Tell the worker which kind it is holding. An ungated candidate is a RECALL widening, never a
stronger signal: it offers nothing to verify, so it must be judged on the decision bodies alone and
should draw a `none` verdict more readily than a gated one. Say so in the brief rather than hoping
the flag speaks for itself. Pre-filter before fan-out: skip a gap
whose pair already carries a recorded edge, and skip a milestone/no-decision pair the criteria exclude
(see rules 5-6). One surviving gap = one agent.

### 2. The judging criteria (what the swarm decides)

Each agent reads the two decision bodies and returns, per gap:
`{verdict: replaces|evolves|related|none, source_dN, target_dN, why, quote, confidence}`.

The verdict rules, measured against 68 validated corrections:

1. **The three-way litmus is the spine.** The newer decision *retires* the older -> `replaces`; *refines
   it while it stays valid* -> `evolves`; genuinely just connected -> `related`; no real relationship ->
   `none`. When in doubt between `related` and `evolves`, ask whether the newer entry changes or
   completes the older *decision itself*, not merely follows it in time.
2. **Implementation evolves its proposal.** An entry that *implements what an earlier entry proposed,
   scoped, or drafted* **evolves** it — the proposal stays valid as rationale. This is the single most
   under-declared shape.
3. **Deferral completion evolves the deferring entry.** An entry that *completes a design call an
   earlier entry explicitly deferred* (an evaluation, a selection, a scoping) **evolves** it.
4. **An explicit rewrite replaces.** A decision that plainly reverses or rewrites an earlier decision
   **replaces** it. Retiring a feature with no successor still `replaces` the retired feature's entries.
5. **Landing work is not a lifecycle edge.** An entry whose decision is to merge / land / integrate /
   publish existing work does **not** evolve the work it lands — that is `none` (or `related` at most).
6. **Parallel campaign steps are `related` at most.** Audits of different files, batches of one sweep,
   cycles of one programme are `related`, never `evolves`/`replaces` of each other.

Granularity: name an ordinal on an end **only when that entry has 2+ decisions** — a single- or
no-decision end takes the bare id (its `:d1` and bare id denote the same edge). This matches the
write-time mandate; the swarm's output is canonical by construction. **All three verdict kinds carry
decision granularity** — since 2026-07-25 `related` may also be decision-level (`related_entries:
mse_x:d2`), so a `related` verdict SHOULD name the specific decisions it connects when either end is
multi-decision, exactly as the reasoning already identifies them. This is why one swarm run suffices:
it emits the finest granularity the grammar allows, and the corpus never needs a second pass to add it.

The `quote` field must be a verbatim phrase from the entry that grounds the verdict — if the agent
cannot quote something specific, the verdict is `none`.

### 3. Orchestrator validation (mechanical-first — no new model calls)

Before surfacing anything, the orchestrator drops verdicts mechanically:

- **Quote grounding:** the `quote` must appear in the cited entry's body (whitespace-normalized
  substring match). A verdict whose quote is not found is discarded — this is the primary hallucination
  guard.
- **Ordinal / id existence:** `source_dN` and `target_dN` must exist on their entries; the ids must
  resolve; forward-only must hold (target older than source). Reuse `links check`'s own rules.
- **Consistency:** group verdicts by pair; a pair with contradictory verdicts across runs is held back
  for human eyes, not auto-resolved.
- **Litmus regressions:** spot-check that no `evolves`/`replaces` verdict is actually a landing/parallel
  case (rules 5-6) — the two the swarm most often over-calls.

Surviving verdicts are candidates; everything dropped is logged so the human sees what was filtered.

### 4. Batch approval (the human gate)

Surface the surviving verdicts as ONE batch — pair, verdict, ordinals, the grounding quote, and the
`why`. The user approves the batch, edits individual verdicts, or rejects. **Never write without this
approval** (same gate as persona evolution and stub-to-edge conversion in `end_of_turn.md`). A
confidence floor may auto-*hide* low-confidence verdicts from the batch, but never auto-*writes* them.

### 5. Write + check

Write approved edges into the link sidecar for the **source entry's own session date** —
`.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md`, where the date is when that entry was logged,
**not today**. A campaign spanning many dates therefore writes to many files; filing a block under any
other date fails `links check` with `link-sidecar-date-mismatch`.

One block per SOURCE (newer) entry, keyed `## <authoring wall clock> - <short label>` + a fenced yaml
with `entry_id:` and the `replaces:`/`evolves:`/`related_entries:` lists (arrow grammar for the source
ordinal when the source is multi-decision). Use the wall clock, **not** the entry's own timestamp:
block identity is `(entry_id, heading timestamp)`, so a later pass needs a distinct stamp to append a
second block for the same entry. Never reopen a written entry — append-only. Then run
`memory-seed links check` and confirm integrity OK before merging.

## Guardrails

- Run on the trunk / integration checkout, not a task branch — link sidecars belong on main (see
  `agent_collaboration.md`).
- Block identity for a link sidecar is `(entry_id, timestamp)`; two blocks for one entry need distinct
  timestamps.
- The swarm only *suggests*. The mechanical recall, the validation, the approval, and the write are all
  outside the model's authority — a stronger `link suggest`, not a new source of truth.

See `docs/2_Todo/link-audit-decision-judgment-swarm-proposal.md` for the design rationale and the
open orchestration questions this skill resolves.
