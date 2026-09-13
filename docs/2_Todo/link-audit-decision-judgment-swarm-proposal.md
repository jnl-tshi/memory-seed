---
priority: P2
next_action: "Batching and retention are shipped. Design the broader vendor-neutral queue orchestration around probe/claim/complete plus the agreed merge hook/controller boundary; do not reopen the settled decision-level edge or approval contracts."
---

# link audit → decision-judgment swarm

Status: **PROPOSAL — foundation shipped, orchestration to design.** Raised 2026-07-23 by JNL, resolving
the decision-level-refs spec's open question #1: *"I think auto inference once you have mechanically
pulled semantically similar candidates can be passed to a swarm of the small agents (haiku) with clear
instructions for what is a link and what isn't."*

> The nervous system of decision history: being specific about **which decisions** have been superseded
> or evolved, and **why** — at decision granularity, especially for decisions promoted to ADRs in a
> diagram sidecar. `link audit` finds the pairs mechanically; an agent swarm judges them at decision
> granularity; a human approves. This doc covers the swarm half — the in-core half is done.

## The insight, and why it needs a swarm not an embedding

`link audit`'s ranking evidence — shared files, topics, title terms, entry embeddings — is all keyed on
`entry_id`. Two decisions of one entry share every bit of it, so the mechanical scorer *cannot* tell
which decision an edge belongs to (confirmed in code and in the spec). Extending it with decision-body
*embeddings* would fight its own discipline ("the lexical gate decides membership, semantic only
reorders") for a short, noisy signal the spec doubts is meaningful.

An LLM sidesteps this: it **reads** the two decision bodies and judges "D2 of B evolves D1 of A, because
…" — the semantic judgment embeddings can't do. So the split is: **mechanical recall** (cheap,
deterministic, in-core) → **LLM precision** (reads decisions, narrows to `:dN`, external) → **human
approval** (the edge is authored, gated, model-independent).

## What is already built (in-core foundation, shipped 2026-07-23)

- `entry_body_decisions(body)` → per-decision `(ordinal, name, text)` at `:dN` granularity.
- `LinkGap` / `LinkGapCandidate` carry both ends' `decisions`; `audit_link_gaps` populates them (surfaced,
  never scored — scoring is byte-for-byte unchanged).
- `link audit` (human text) shows decisions for multi-decision entries with a "target one as `<id>:dN`"
  hint; `link audit --json` emits each candidate as a **judgment-ready task**: both ends' decision bodies
  plus a `criteria` block (supersedes / evolves / related / none, the `:dN` narrowing rule, forward-only).

That JSON is the contract the swarm consumes. It is the whole in-core surface this feature needs.

## The constitutional shape (why the swarm is never in core)

- **Invariant #1 — the core runs with no server, database, or network.** LLM calls are network, so the
  swarm cannot live inside any `memory-seed` core command. The core emits the task; the model calls
  happen in an **optional layer** outside it (same boundary as the `[trace]` extra).
- **Invariant #5 — model-independence.** The swarm only *suggests*. A human (or the normal write-time
  guards) approves, and the edge is written as an ordinary `:dN` lifecycle edge — identical to a
  hand-authored one, carrying no dependency on the model that suggested it. Haiku is a stronger
  `link suggest`, not a new authority.
- **§11.** No amendment is needed: the invariants are *satisfied* by keeping the swarm external and the
  stored edge human-gated. A design that called an LLM from inside `link audit` *would* need one — so it
  is out of bounds by construction.

## Architecture

```
memory-seed link audit --json --date <today>   (core, mechanical, network-free)
        │  judgment-ready tasks: {criteria, gaps:[{decisions, candidates:[{decisions}]}]}
        ▼
orchestrator (external optional layer)
        │  one Haiku agent per (source-decision × candidate) pair, given the two decision
        │  bodies + criteria; returns {verdict: supersedes|evolves|related|none, source_dN,
        │  target_dN, why, confidence}
        ▼
collect + rank verdicts  →  present to human for approval  →  author :dN edges via the
gated write path (link sidecar), then links check validates them
```

The swarm is **read-then-suggest**: it never writes. Writing is the existing gated path
(`memory_session_integrate` / a link-sidecar append), unchanged.

## Granularity posture — which class of edge the swarm should aim for (JNL, 2026-07-24)

The swarm's instructions rank the *granularity* of the edge it proposes, not just its type. Three
classes, by precision, mirroring what the Trail now draws and weights:

1. **Decision → decision (first class).** Both ends name a specific decision (`A:d2 evolves B:d1`).
   This is the target the swarm should reach for whenever it can quote the two decisions the edge
   actually connects. It is the most precise statement and the whole reason the swarm reads decision
   bodies rather than entry summaries.
2. **Entry → decision (second class).** One end names a decision, the other is the whole entry. Allowed
   **when the whole entry is centered on a single decision that relates to a subset of specific items in
   the other entry** — a broad entry that retires one earlier call, or one call that reframes a whole
   earlier entry. Do not manufacture this shape to look precise; use it only when the entry genuinely
   has one throughline.
3. **Entry → entry (third class).** Neither end names a decision. This covers history links and — the
   load-bearing rule — **any entry with one decision or no decisions**: for those the `:dN` detail is
   redundant (a single-decision entry's `d1` and its entry id denote the same thing), so the swarm links
   at entry level and stops. Referenced entries that are single- or zero-decision are **always** linked
   entry-level, on both ends.

The instruction to the workers is therefore: *prefer the highest class the evidence honestly supports,
fall to the next when it does not, and never split a single-decision entry into `:dN`.* This keeps the
precise edges precise without inflating the common case, and it is why the Trail can weight class 3 as
quiet background — most of the corpus legitimately lives there.

> **Reconciled 2026-07-24 (JNL).** The earlier grammar-v2 mandate required an explicit `:d1` for *any*
> decision-bearing target, single-decision included — the opposite of rule 3. That was relaxed to match:
> **an ordinal is named only when the entry it belongs to has 2+ decisions.** A single-decision target
> takes the bare id (`:d1` there is redundant and now *rejected* at `session append`, warned as
> `redundant-decision-ref` at `links check`), exactly as a single-decision *source* already omits its
> arrow. So rule 3 is now the write-time rule everywhere, not just the swarm's posture — no split
> between hand-authoring and the sidecar path. The swarm therefore emits `:dN` only for multi-decision
> targets and bare ids otherwise, and its output is canonical by construction.

## Open design questions (for JNL)

1. **Where does the orchestration live?** A repo **skill** (an agent runs it by hand at session end), a
   **Workflow** script (deterministic fan-out), or both. It is *not* a `memory-seed` subcommand — that
   would put the network in the core.
2. **The approval gate.** Batch-review all verdicts at once, or per-edge? What confidence threshold, if
   any, auto-drops a verdict before a human sees it? (Never auto-*writes* — only auto-*hides* low
   confidence, like the ESR persona-usage window.)
3. **Fan-out unit.** One agent per candidate pair (judging all decision combinations at once), or one per
   `(source_dN, candidate)` — finer, more agents, cleaner prompts. Cost scales with the choice.
4. **Scope gate.** Run the swarm over every audited pair, or only where an end is **ADR-promoted**
   (`has_diagram`) — the case JNL named as most valuable? Note ADR-promotion is entry-level today; a
   per-decision ADR marker (see below) would sharpen this.
5. **Prompt/criteria authorship.** The `criteria` block in `--json` is a first draft; the swarm's
   instructions ("what is a link and what isn't") deserve their own careful pass, tested against the
   corpus's author-declared decision edges the way the lexical scorer was.

## Adjacent, separable

- **A per-decision ADR marker.** Today "promoted to an ADR" is entry-level (`has_diagram`). A first-class
  "this decision is an ADR" signal would let the swarm (and coverage metrics) target ADR decisions
  precisely. Its own small schema addition — scope separately.
- **ESR decision-edge coverage** (spec open question #2) — whether to count decision edges in coverage
  without making history look worse. Related, deferred.

## Recommendation

Build the orchestration as a **skill** first (lowest ceremony, an agent runs it at session end over
`link audit --json --date <today>`), with a **batch human-approval** step and a confidence floor that
only hides, never writes. Prove it on one real multi-decision pair before scaling the fan-out. Keep every
model call outside the core; keep every write on the gated path.

## References

- `docs/3_Spec/draft/decision-level-link-sidecar-refs.md` — the `:dN` grammar and open question #1 (now
  resolved to this split).
- `docs/CONSTITUTION.md` — Invariant #1 (network-free core), #5 (model-independence), §11.
- `memory_seed/retrieval.py` `audit_link_gaps`, `memory_seed/core.py` `entry_body_decisions`,
  `memory_seed/cli.py` `link audit --json` — the shipped foundation.
