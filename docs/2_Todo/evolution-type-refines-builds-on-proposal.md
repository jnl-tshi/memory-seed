# Typed evolution: one `refines` spine, unlimited `builds-on`

Status: proposed (JNL direction, 2026-08-09)

## The problem, measured

Following an `evolves` chain to its end does not return a chain. It returns a fan: 13 entries in the
corpus produce 10 or more terminal heads, the worst producing **25**.

The cause is not what it looks like. Measured on the 2026-08-09 corpus (896 entries, 1353
decisions, 534 `evolves` edges after sidecar augmentation):

- **The local step is almost always unambiguous.** 195 of 303 nodes with a successor have exactly
  **one**. Mean branching is 1.76.
- **The explosion is transitive.** Chains run to depth 15; 1.76 branches compounded over 15 hops is
  a fan.
- **It is not a granularity artifact.** The 25-head case (`mse_7n25phrhv9kdnnc0`) has only **four**
  immediate successors and its own entry carries **one** decision, so collapsing multi-decision
  entries to entry level is not what produced it. Its four successors are "Worktree dependency
  strategy Phase 1", "Overnight proposal sweep", "Record Explorer UI proposal" and "Track E dry-run
  classifier" - four unrelated pieces of later work.

`evolves` carries two different relations under one name:

1. **the next version of this decision** - same subject, naturally a line
2. **later work that builds on this decision** - different subject, many-to-many, and its transitive
   closure is unbounded by construction

Any traversal over that returns a fan, because the information needed to separate the two was never
written on the edge. No ranking or pathfinding fixes it; they only make the fan smaller to look at.

## Proposal

### 1. `evolves` gains an evolution type

Two values, `refines` and `builds-on`. Unset means **not yet classified** - never "neither". A
sub-field rather than two new edge kinds, because it is additive: all 534 published `evolves` edges
stay exactly as they are and can be typed later, per edge, without touching what is written.

`edge_confidence` proved the mechanism on 2026-07-25 - `links check`'s parser collects lines only
under known ref-list keys, so an unknown sibling key in a sidecar block costs zero parser change to
start writing.

**The type rides on the item, not in a parallel map.** `- d1 -> mse_x:d2 (refines)`, alongside the
arrow prefix that already names the source ordinal. This follows a recorded precedent:
`mse_kdhw53hzp4nh8wwm:d2` withdrew a drafted block-level `source_decision:` field in favour of the
per-item arrow, rejecting "a parallel `source_decisions:` mapping keyed by target - a second
spelling of the same fact, and unreadable in a diff." The same reasoning applies here, and it is
what distinguishes this field from `edge_confidence`: a machine-generated score belongs in a
parallel map, an authored fact belongs on the line that carries the edge.

**The sidecar is already the write-time home, so sidecar-only carries no provenance cost.** Links
supplied through the decisions envelope (`--decisions-file` / MCP `decisions`) are written
mechanically to the links sidecar and tagged `source: write-time` - verified on
`mse_1qwdqgn3gn1v55w7`, whose entry YAML block carries no lifecycle key at all while
`sessions/links/2026-08/2026-08-09.md` holds `evolves: - d1 -> mse_f9sfx7zmwegr3he4` under
`source: write-time`. That declared `source` is exactly what Constitution 1.6 asks for: provenance
on the record rather than inferred from which file it sits in.

### 1a. Entry YAML stops accepting lifecycle links (JNL, 2026-08-09)

Entry YAML is still a live second surface - 772 lifecycle refs sit there (59 in June, 668 in July,
45 in August 2026), written via the `--related`/`--replaces`/`--evolves` flags and hand-authored
entries, and `session append` validates both paths in one loop. JNL's direction is to close it: a
raw ref in an entry's YAML gives a human reading the Markdown nothing - the id is opaque without a
lookup, and an agent resolves it through MCP either way - so it is noise in the file where narrative
belongs.

Invariant #6 already describes exactly this split: *"Narrow sidecars may own explicit promotion or
lifecycle facts while referenced entries own narrative rationale and evidence."* Moving edges out of
entry YAML brings the code to the invariant rather than away from it, and nothing leaves Markdown -
the sidecar is a Markdown file a person can read with no service.

**This can only mean "stop accepting new ones".** The 772 published refs are append-only and cannot
be deleted, so readers keep parsing entry YAML permanently; what changes is the write path. Concretely:

- `session append` and `memory_session_append` refuse entry-level lifecycle args, leaving the
  decisions envelope as the sole write path (write-surface parity, Constitution 1.3).
- `links check` errors on a lifecycle key in entry YAML for entries stamped after a cutoff, using
  the `DECISION_GRANULARITY_MANDATE_SINCE` pattern so published entries stay quiet.

**Read-side ripple is already covered.** `load_corpus` is the canonical corpus read and applies
every sidecar augmentation, and `tests/test_corpus_read_path.py` holds an allowlist of direct
`extract_memory_chunks` callers so a new unaugmented reader fails the suite. That guard exists
because the partial-read failure already happened three times, once in a shipped gate.

**The one real cost:** an entry stops being self-contained. A person reading a single `.md` no longer
sees what it supersedes without opening the sidecar for the same date. Mild - both files are
Markdown and date-aligned - but it is a genuine loss, and it is the reason to keep the two files
named and dated in lockstep.

### 1b. Write-time link evidence, required for lifecycle edges (JNL, 2026-08-09)

`_DecisionSidecarWrite` takes `related_entries`, `replaces` and `evolves` as bare ref lists with
**no evidence field**. The write-time path asks *which* edge, never *why*, so the reason a link was
drawn is lost at exactly the moment it is cheapest to record - the same argument that put the
granularity mandate at write time. An `evolution_type` with no evidence beside it would repeat the
mistake one field over.

Decision: **evidence is required for `replaces` and `evolves`, optional for `related_entries`.** That
split mirrors the 2026-07-24 granularity mandate, which is lifecycle-only for the same reason -
`related` stays casual for hand-authoring, lifecycle edges carry weight and must justify themselves.
Enforced at `session append`, where the ref is still unwritten.

The accepted risk, stated: a mandatory field can be satisfied with a thin answer. The alternative -
an optional prompt - is the shape that already failed this project once, when the per-entry diagram
trigger was retired for having no teeth.

### 2. At most one `refines` successor per decision

This is the rule that makes the spine a spine. With it, `refines` is a linked list: "what does this
say now" has exactly one answer, reached by walking until there is no next one - no frontier, no
ranking, no fan. `builds-on` stays unlimited, which is honest about what it is.

**Constrain outbound successors only.** 129 nodes in the corpus evolve two or more predecessors - a
decision consolidating several earlier ones. That is a join, and it does not fan a forward walk
(both parents lead to the same place), so it stays unconstrained. The rule is about the successor,
not the edge.

### 3. Enforcement is split, and `links check` is the primary surface

- **`session append`** refuses a second `refines` on a target that already has one. This is the one
  moment the ref is unwritten, and it catches the same-repo-state case.
- **`links check`** raises `multiple-refines-successors` as an **error**, not an advisory. Two
  branches can each legitimately write a `refines` and neither is refused, so write-time cannot be
  the only guard. This rule *can* be an error where the 2026-07-24 granularity mandate could not,
  because it is satisfiable: `retracts:` gives a sanctioned append-only route to downgrade the loser.

**Known limit:** `session merge-branch` gates on the fuse preview, not on `check_session_links`
(which is called only from `doctor`, non-fatally, and the CLI). A cross-branch double-`refines`
therefore surfaces *after* the merge, in `links check` or CI, rather than blocking it. Wiring the
check into the merge gate is a separate question.

### 4. A resolved conflict stays visible

Retraction today applies by **removal**: `retrieval.py` accumulates `retracts:` across blocks and
subtracts the named edges from the completed union, so a downgraded edge vanishes from the derived
graph entirely. The Markdown keeps it, because everything is append-only - but nothing surfaces it.

Since the record already holds both halves, a retracted edge should be kept as a distinct labelled
class rather than deleted, so a future graph or Trail view can render *"this was authored `refines`,
downgraded to `builds-on` on <date>"*. That makes the handling of a conflict inspectable instead of
leaving only its outcome. It also matches Invariant #7 - retrieval down-ranks history, it does not
hide it.

## Cost

Against the current 534 `evolves` edges:

| | count |
|---|---|
| Nodes already compliant (exactly one successor) | 195 of 303 |
| Nodes where a `refines` must be chosen | 108 |
| Edges that must therefore carry `builds-on`, at minimum | 231 |

## The link swarm gains a classification task

Three constraints, each from a measured failure:

- **Closed candidate list.** Workers classify edges that already exist and are handed the exact edge
  tokens. Never let a worker recall or reconstruct a ref - that is the 15/17 → 20/20 lesson from the
  ADR attachment campaign.
- **The unit of work is a target and all its successors, not one edge.** The uniqueness rule means
  classification is not per-edge independent: a worker asked "is this edge `refines`?" in isolation
  cannot know another worker is answering yes for the same target.
- **Keep the two vocabularies apart.** `refines`/`builds-on` sits next to the existing
  `replaces`/`evolves`/`related` verdict. A worker asked both questions in one payload will cross
  them, so classification runs as a separate pass over already-decided `evolves` edges.

## Sequencing

Schema, reader and guards merge as their own commit **before** any data using them -
`session merge-branch` validates with main's parser, so a ledger written against a parser that has
not landed fails on merge.

1. Grammar + reader + `links check` rule + `session append` guard + tests
2. `link_swarm.md` and its seed twin - the classification task
3. The 231-edge classification campaign (a separate act, separately approved)

## Related

- `docs/3_Spec/graph-edge-contract.md` - defines `evolved_head` and every consumer; this amends it.
  Note the contract never states a graph granularity: entry-keying is an unstated property of
  `build_related_entry_graph`, not a recorded decision.
- `mse_kdhw53hzp4nh8wwm:d1` / `mse_h297nf3qghp7ysyk:d1` - the 2026-07-24 granularity mandate and its
  relaxation. Orthogonal to this proposal: for a single-decision entry `mse_x` and `mse_x:d1` denote
  the same node, so the ref-grammar question is separate from the graph-granularity one.

## Backfill attempt, 2026-08-09: classification done, write mechanism blocked

The haiku swarm ran and its verdicts are sound. 24 batches over 461 target-units and **807 untyped
`evolves` edges**; every batch validated mechanically against its closed candidate list (target
membership, edge-id set equality, no duplicates, no invented ids, one-`refines` cap). Result:
**173 `refines` (21%), 634 `builds-on`**, zero unresolved edges, and zero cap violations when the cap
was re-checked across the whole plan rather than per batch. Verdicts are preserved in the session
scratchpad under `results_VALIDATED_KEEP/`.

**The retract-and-re-author write was applied to 52 sidecar files, measured, and REVERTED.** It
silently deleted the edges instead of typing them. Two compounding causes, both in the reader:

1. **`evolution_type` never reaches the graph.** `entry_link_sidecars` parses a sidecar ref into
   entry-level lists of bare target ids and `decision_edges` 4-tuples `(kind, source_ordinal,
   target, target_ordinal)`. Neither has a slot for the type, so a re-authored
   `d1 -> mse_x (refines)` arrives at `build_related_entry_graph` indistinguishable from an untyped
   edge. The write grammar and `links check` shipped without the read path.
2. **A retract's identity ignores the type**, so `retracts: evolves d1 -> mse_x` matches the typed
   replacement authored in the same block and removes it too.

Measured before the revert: effective typed edges **0**, nodes with successors fell **303 → 139**,
max lineage heads **25 → 4**. `links check` reported OK throughout - the corpus looked healthy while
807 edges had been dropped, which is the worst failure shape available and the reason this needed a
graph-level assertion rather than an integrity check.

**What must land before the backfill can be re-applied** (the verdicts do not need re-running):

- Carry `evolution_type` through `entry_link_sidecars` into the graph. `decision_edges` is a fixed
  4-tuple that `edge_confidence` deliberately declined to widen, so this is a real schema decision:
  widen the tuple and fix its consumers, or carry a parallel type map as `edge_confidence` does.
- Make the retract key type-aware, so retracting an untyped edge leaves a typed one standing.
- Add a graph-level regression test: after any backfill, assert the effective `evolves` edge count is
  unchanged and the typed count equals the intended one. `links check` passing is not sufficient.

## Second apply attempt, 2026-08-09: one defect left, and it is in `retracts:`

The campaign is COMPLETE and validated: 47 batches, 461 target-units, **807 edges**,
zero invalid. Under the two-run agreement rule the plan is **110 `refines` / 697
`builds-on`**, with **157 refines claims demoted** because only one run made them
(63 run-1-only, 94 run-2-only) - 59% of all refines claims fail agreement, which
is the whole justification for the rule.

Two write attempts, both caught by the graph assertion and both reverted:

1. **534 -> 236 edges.** A bare ref carrying only a type (`mse_x (refines)`) named
   no ordinal on either end, so neither sidecar parser recorded a decision edge -
   the type had nowhere to live, and the survivor check could not see it. Fixed
   in `f665237`; the same write now lands **537/304 with 104 nodes gaining a
   refines successor**.
2. **534 -> 537 edges (+3).** Still aborts, and the cause is a genuine limitation
   nobody had hit before: **a sidecar `retracts:` prunes only the SIDECAR's own
   lists.** `retract_entry` / `retract_decision` are applied to
   `sidecars.get(eid)`, so an edge authored in an entry's own YAML cannot be
   retracted by a later sidecar block at all. 232 of the 807 edges are entry-YAML
   edges, and for those the retract is a silent no-op - the typed re-author simply
   unions alongside the original.

That the drift is only +3 rather than +232 is incidental: the entry-level union
dedupes by target id, so a re-authored edge to the same target collapses. The
three survivors are where that coincidence does not hold.

### What must be decided before the third attempt

`retracts:` was specified when links lived in sidecars. Entry YAML is now closed
to new lifecycle links (`adr_lifecycle_edges_live_in_sidecars`), but the 772
published entry-YAML refs are permanent, so "a sidecar can retract an entry-YAML
edge" is a capability the mechanism needs and does not have. Either:

- **Extend retraction to entry-YAML edges** - `augment_chunks_with_link_sidecars`
  applies the sidecar's retract set to the CHUNK's lists, not just the sidecar's.
  This is the honest reading of what a retraction means, and it is what the
  backfill needs. It also widens what a sidecar can undo, so it wants its own test.
- **Leave the 232 entry-YAML edges unclassified.** Type only the 575
  sidecar-authored ones, and let the gate's cutoff cover the rest permanently.

The verdicts do not need re-running either way - they are preserved and validated.

## JNL, 2026-08-09: no cutoff, and `refines` becomes an ADR review trigger

Two directions, taken together.

### 1. The cutoff is rejected - extend retraction to entry-YAML edges

All 807 edges get typed, so the mechanism must be fixed rather than worked
around: `augment_chunks_with_link_sidecars` applies a sidecar's retract set to the
CHUNK's lists, not only to the sidecar's own. That is the honest reading of what a
retraction means - a later block retracts an edge, wherever it was authored - and
it is the only way to reach the 232 entry-YAML edges, which are permanent.

It widens what a sidecar can undo, so it needs its own test: a sidecar block must
be able to retract an edge declared in an entry's YAML, and must not be able to
retract one from a DIFFERENT entry (the retract set is keyed by the block's
`entry_id`, and that scoping is what keeps it honest).

### 2. `refines` deterministically flags an ADR as needing revision

An ADR's `authoritative_decision` is a decision ref. If that decision has a
`refines` successor, the concern's current form has moved on and the ADR has not:
that is a mechanical fact, not a judgement, so ESR should report it the way
`needs-diagram-review` already reports a diagram answer invalidated by evolution.

**It FLAGS; it never moves a head.** Only an authored `revision-proposed` +
`revision-accepted` pair changes `authoritative_decision`, and that stays true
even when the refines edge came from a swarm - `feedback_machine_edges_never_move_heads`
was written after a 0.75-confidence edge moved an ADR onto an unrelated concern in
one hop. A deterministic trigger is safe precisely because its output is a
question for a human, not a write.

**Blocking dependency, and it is JNL's original point.** An ADR head is
decision-level (`mse_x:d3`), but `refined_by` is entry-keyed: it records THAT an
entry refines another, not WHICH decision refines which. `decision_edges` carries
both ordinals, so the information exists - the walk simply does not use it. So
this trigger cannot be built until `refined_by` and `refines_lineage_head` are
keyed by `mse_x:dN` rather than by entry. That is the decision-level graph, and it
is now on the critical path rather than being a principle.

### Order

1. Retraction reaches entry-YAML edges (+ test).
2. Apply the backfill - verdicts are validated and waiting; the graph assertion is
   the gate, not `links check`.
3. Re-key the lineage walk to decisions.
4. ESR trigger: ADRs whose authoritative decision has a `refines` successor.

### Investigated: does linking the two systems pay? Yes - on precision, not volume

Measured the 109 agreed-refines edges against all 57 ADRs:

| | count |
|---|---|
| ADRs whose AUTHORITATIVE head has a refines successor | **3** |
| ADRs where a non-head MEMBER has one | 3 |
| untouched | 51 |

Low volume, and that is the point: this is a review queue, not a firehose. Six
items is actionable; six hundred would be ignored.

**The first hit is independently verified as a true positive.**
`adr_decision_identity` is headed by `mse_kdhw53hzp4nh8wwm:d1` - the 2026-07-24
mandate requiring an explicit `:d1` on every target - and the proposed successor
is `mse_h297nf3qghp7ysyk:d1`, the decision that RELAXED exactly that rule to
"name a decision only when there is a choice". Both were read from source earlier
in this session for an unrelated reason, so this is not the swarm marking its own
homework: the ADR really is pointing at a superseded form, and the chain found it.
That single case is worth more than the count, because it is the shape the trigger
exists to catch.

**Caveats that bound the claim:**
- One hop, not a walk to the terminus. A real chain may run further.
- The TARGET side is decision-exact (`mse_x:dN`); the SOURCE ordinal was inferred
  as `d1` where the source entry has a single decision. Re-keying the walk to
  decisions removes that inference.
- 109 agreed edges is the current ceiling; it rises once retraction reaches the
  232 entry-YAML edges and the backfill lands.

**Verdict: build it.** The chains already encode "what is the current form of this
decision", which is the same question an ADR head answers for a concern - deriving
one from the other is reusing a fact, not inventing one. It stays FLAG-ONLY: the
ESR report names the ADR, its head, and the proposed successor, and an ADR swarm
adjudicates each. Nothing writes to a ledger without an authored revision.
