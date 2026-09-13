---
memory-system-version: 2.21
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

**Model selection.** Use the smallest available model that can reliably apply this fixed rubric, with
high reasoning enabled. This is an economy-tier capability requirement, not a provider or model-family
requirement. Escalate only a specific ambiguous gap, and record why a larger model was needed.

## The pipeline

```
memory-seed link batch-plan --date <today> --context-window <tokens> --output-dir <run>
    -> materialized judgment-ready batches + pending analytics.jsonl
Workflow fan-out                                 (optional layer, network)
    -> each worker reads one self-contained batch file, then writes its assigned findings/*.toon file
orchestrator validation                          (mechanical-first, no new model calls)
    -> memory-seed link batch-collect validates reports and writes survivors.json + validation.json
batch approval                                   (the human gate)
    -> surface the surviving verdicts as one batch; the user approves, edits, or rejects
write + check
    -> approved edges written to the day's link sidecar; memory-seed links check validates
finalize + retain
    -> batch-finalize seals a receipt; batch-gc later compacts only expired, hash-matching raw files
```

### 1. Mechanical recall

Run `memory-seed link audit --json --date <today>` (or `--for <entry_id>` to scope to one entry). The
JSON emits each gap as a judgment-ready task: both ends' `decisions` (ordinal + name + body), the
overlap evidence (files/topics/title), and a `criteria` block.

For a swarm, use `link batch-plan` with `--output-dir`. Its default `--top-k 0` enumerates every
lexically admitted candidate instead of retaining only a fixed number per source. `--minimum-score`
sets the combined-score admission floor. `--semantic-cutoff` changes semantic-only recall from the
legacy top-two widening to every older pair whose raw cosine meets the supplied value. Thresholds are
run parameters, never hidden constants; keep them in `plan.json` so later outcome data can calibrate
them rather than guessing.

Every candidate row records the combined score plus separate file, keyword/title, topic, raw semantic,
weighted semantic, temporal-proximity, and day-distance values. File + keyword + weighted semantic are
the current rank; topic and temporal values are diagnostic only. `analytics.jsonl` retains these
features, the threshold disposition, batch assignment, validation status, final verdict, confidence,
and exclusion reason for every candidate, including `none` and below-threshold rows.

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
(see rules 5-6).

**Batch by measured context, never a fixed pair count.** A worker receives as many complete candidate
pairs as fit within **16% of its declared context window for the complete worker document**. This
includes the exact embedded skill text, fixed assignment fields, both decision bodies, candidate
evidence, chain state, and per-pair rubric fields. Pack whole pairs until the next pair would exceed
that budget. The plan also estimates an explicit output reserve per pair and reports it separately. Do not
truncate, summarize, or split a pair to fill a batch. This preserves enough room for careful per-pair
judgment while letting short pairs share one economy-tier worker efficiently. Every pair still receives its own independent
`{verdict, source_dN, target_dN, why, quote, confidence}` result; batching changes transport and cost,
not the evidence standard or the validator.

**Workers use one self-contained file as their contract.** Each `batches/batch-NNNN.md` embeds the
exact active `link_swarm.md` text at its top, records that source path and its SHA-256 digest, and then
contains the mechanical assignment. The packer counts this fixed instruction block inside the declared
16% budget. A worker reads only that batch document; the orchestrator does not need to repeat the rubric
in its prompt or ask the worker to load a second file. The batch names its only authorized output as
`finding_path`; write the complete TOON document there. Do not return the report only in chat, and do
not edit `plan.json`, `analytics.jsonl`, another batch, or a link sidecar. Raw findings are disposable
run evidence; the orchestrator may reject or delete them after collection without changing memory
authority.

### 2. The judging criteria (what the swarm decides)

Each agent reads the two decision bodies and returns, per gap:
`{verdict: replaces|evolves|related|none, source_dN, target_dN, why, quote, confidence}`.

**Batch return contract.** Return exactly one strict **TOON** (Token-Oriented Object Notation) document
with schema `memory-seed.link-swarm-verdicts.v1`: its `batch` and `measurement` identify the packed
input; its `counts` totals verdict kinds; and its homogeneous tabular `verdicts` array is sorted by
source then candidate. Emit one row for **every input pair**, including `none`, with
`source_entry_id`, `source_decision`, `candidate_entry_id`, `candidate_decision`, `verdict`, `quote`,
`quote_entry_id`, `why`, `confidence`, and `exclusion_reason`. Use TOON's null form for an absent
ordinal or quote. No prose, Markdown tables, compressed ranges, or omitted negative results. This
makes a batch mechanically auditable and keeps reviewer reporting independent of model style while
avoiding repeated JSON field names.

`confidence` is either TOON `null` or a numeric value from `0` through `1` inclusive; never use
word labels. This keeps result rows sortable without model-specific normalization.

The first three lines of every report are mechanically fixed:

```text
schema: memory-seed.link-swarm-verdicts.v1
batch: <integer batch number>
verdicts[N]{source_entry_id,source_decision,candidate_entry_id,candidate_decision,verdict,quote,quote_entry_id,why,confidence,exclusion_reason}:
```

Follow them with exactly `N` CSV-style TOON rows and no prose before or after the table. Quote any cell
containing a comma or quote; double an embedded quote. The collector rejects the entire batch when the
schema, batch id, row count, column order, or row width differs.

**Rectangular-table rule.** Every `verdicts` row must contain **exactly one value for every declared
column, in that order**. Never omit a trailing field: emit TOON `null` for an absent `source_decision`,
`candidate_decision`, `quote`, `quote_entry_id`, `confidence`, or `exclusion_reason`. The orchestrator
rejects a batch whose row count or per-row cell count does not match its declared table schema.

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

**Chain position closes part of the verdict space** (2026-08-09). Candidates arrive annotated from the
decision-keyed `refines` spine (`chain_position` in the payload), and every lifecycle edge into a chain
attaches at its HEAD - `refines` takes the single successor slot, `builds-on` forks a new line from it,
and interior members receive only `related`:

- `head` - the full verdict space applies.
- `interior` - this candidate's `refines` slot is taken (`refines_taken_by` names the holder); the
  chain lives at `current_form`. The only recordable verdicts are `related` or `none`. Never propose
  `replaces` or `evolves` onto an interior member - if the real relationship is to the chain, the edge
  belongs at `current_form`.
- Replaced candidates never appear at all; their terminal replacement is offered instead, carrying
  `substitute_for` so the provenance stays visible. Judge the replacement on its own body.

This is the closed-list rule applied to verdicts: the invalid option is removed from the menu rather
than left for the judge to remember to avoid.

The `quote` field must be a verbatim phrase from the entry that grounds the verdict — if the agent
cannot quote something specific, the verdict is `none`. For a non-`none` verdict it must contain at
least 12 meaningful characters and cannot be only a heading, ordinal, label, or punctuation.

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
Run `memory-seed link batch-collect --run-dir <run>` after workers finish. It reads their files,
checks rectangular TOON, pair coverage, duplicate/unexpected rows, ordinals, chain-position legality,
confidence range, and exact quote grounding. It updates `analytics.jsonl` and produces
`validation.json`, `survivors.json`, and `analytics-summary.json`. The summary groups counts and each
component's mean/min/max by final verdict so patterns such as high semantic + short temporal distance
among `evolves` results are visible without collapsing the raw rows. Review `survivors.json`, not chat callbacks.

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

**`links check` alone is NOT sufficient for a bulk write.** It validates what each file SAYS, not
what the effective graph MEANS — it read OK across two silent corruptions caught only by a graph
assertion: 807 `evolves` edges vanished in the 2026-08-09 backfill, and separately a +3 edge
resurrection. Bracket every bulk sidecar write with `memory-seed links graph-diff`: run
`--snapshot <path>` before the campaign and `--against <path>` after. Exit 0 means the effective
`evolves` edge set is unchanged (a pure retype, e.g. untyped → `refines`/`builds-on`, still passes —
typing deltas are reported but informational); exit 1 names every node whose edges actually moved
and must be explained before merging.

## Guardrails

- Run on the trunk / integration checkout, not a task branch — link sidecars belong on main (see
  `agent_collaboration.md`).
- Block identity for a link sidecar is `(entry_id, timestamp)`; two blocks for one entry need distinct
  timestamps.
- The swarm only *suggests*. The mechanical recall, the validation, the approval, and the write are all
  outside the model's authority — a stronger `link suggest`, not a new source of truth.

## Retention and cleanup

Collection never deletes evidence. After the human disposition is known, create a
`memory-seed.link-swarm-approval.v1` JSON record and run `memory-seed link batch-finalize --run-dir
<run> --approval-file <approval.json>`. The finalizer refuses a pending run; an approved disposition
also requires complete validation, at least one surviving approved pair, `graph_delta_reviewed: true`,
a passing live link-integrity check, and a resolvable write commit carrying the declared
`Memory-Entry` trailer. Rejected runs may finalize after an incomplete collection so malformed work can
age out without being mistaken for approved evidence.

```json
{"schema":"memory-seed.link-swarm-approval.v1","run_id":"<run id>","disposition":"approved","approved_pair_ids":["<pair id>"],"reviewer":"<human or delegated orchestrator>","graph_delta_reviewed":true,"write_commit":"<commit>","memory_entry":"<mse id>"}
```

For a rejected run, use `"disposition":"rejected"`, an empty `approved_pair_ids` list, and omit the
graph and commit fields.

The immutable `receipt.json` records the approval, source and skill digests, validation result, graph
delta, commit linkage, expiry, and hashes of every raw artifact. Preserve `analytics.jsonl`,
`analytics-summary.json`, `survivors.json`, `validation.json`, `graph-before.json`, and the receipt
indefinitely. They retain every candidate's component scores and disposition without duplicating full
decision evidence.

Run `memory-seed link batch-gc` to inspect expired runs. It is dry-run by default. `--apply` removes
only the finalized receipt's exact, hash-matching `plan.json`, `batches/*.md`, and `findings/*.toon`
after the configured retention period (30 days by default), then writes `gc.json`. Active, pending,
unfinalized, modified, path-escaping, or otherwise unverifiable artifacts fail closed. `--purge-now`
may bypass time retention but never receipt or hash verification.

See `docs/2_Todo/link-audit-decision-judgment-swarm-proposal.md` for the design rationale and the
open orchestration questions this skill resolves.
