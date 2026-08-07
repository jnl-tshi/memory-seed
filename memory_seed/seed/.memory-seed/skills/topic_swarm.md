---
memory-system-version: 2.19
governing_adr: adr_topic_backfill_rejected
tags:
  - memory-seed
  - skill
  - topic-swarm
---

# Decision-Level Topic Judgment Swarm Skill

Use this skill to backfill controlled-vocabulary topics at **decision** granularity (`<slug>:dN`) across
the corpus, when the whole population is to be attributed rather than a handful of entries tagged by
hand. It is the sibling of `link_swarm.md` and has the same shape and the same guarantees: a mechanical
enumeration produces the judgment units, a swarm of small models judges each one, an orchestrator
validates the verdicts mechanically, a **measured pilot** must clear a stated pass line, and a human
approves the batch before any sidecar is written. Do not reach for this to tag one or two entries — the
author writes those into the entry's own `topics:` at write time. This is for the backfill campaign.

> ## STOP — the pilot was run, and it ABORTED (2026-07-26)
>
> **Do not launch the campaign, and do not re-run the pilot blind.** Both permitted pilot runs are
> spent. Leg A macro-recall was **0.583** (run 1) and **0.613** (run 2, after the single allowed
> re-prompt), against `PROCEED ≥ 0.70`. A second band-or-below result aborts the backfill, so the
> backfill is aborted. Zero topic sidecars were written; `.memory-seed/sessions/topics/` does not exist.
>
> The measured reason is in §4 under "Recorded outcome". It is not "the prompt was bad" — the run-2
> prompt fixed everything the run-1 diagnosis identified and moved precision without moving recall.
> **Reviving this campaign requires a changed premise** (a sharper `area` axis, or a metric other than
> roll-up recall), not another prompt rewrite. The rest of this skill is retained because the pipeline,
> the validator, the block grammar and the harness are all sound and reusable; only the *verdict on
> spending 933 judgments* is settled.

**Opt-in and cost.** The swarm calls a fan-out of models (a Workflow), so it is network-using and must
be run deliberately — never as an automatic step. Confirm with the user before launching the fan-out,
confirm the pilot result before the full run, and confirm again before writing any sidecar. The core
stays network-free (Constitution Invariant #1); the model calls live entirely in this optional layer,
and every stored slug is an ordinary sidecar topic with no dependency on the model that suggested it
(Invariant #5).

## Scope — the whole corpus, not the topicless tail

Measured 2026-07-26 against the live corpus. **Re-measure before launching**; these move as the corpus
grows, and the campaign plan must quote its own numbers, not these.

> **This table is superseded — do not re-derive from it.** The pilot re-measured the same corpus later
> the same day and got 641 entries / **899** addressable ordinals / **933** judgment units / 659
> ordinals inside topiced entries. See §4 "Recorded outcome". The table is kept because the *ratios* it
> explains are still the argument for scoping to the whole corpus.

| Measure | Value |
|---|---|
| Entries carrying an `entry_id` | 635 |
| **Addressable decision ordinals** (`entry_body_decisions`) | **888** |
| Entries with **zero** addressable ordinals | 34 |
| **Total judgment units** (888 decision + 34 bare-entry) | **922** |
| Entries with authored topics | 429 |
| Entries with no topics | 206 |
| Addressable ordinals inside already-topiced entries | 648 |

**Already-topiced entries are in scope.** An entry carrying authored entry-level topics still has no
per-decision attribution — that attribution is the whole product — so 648 of the 888 ordinals sit
inside entries that already look tagged. Scoping to the 206 topicless entries would buy 240 ordinals
and leave the campaign to be run twice.

**The unit is the addressable ordinal, never the decision count.** `dangling-topic-decision` validates
`dN` against `_entry_decision_ordinals` — `#### Dn - name` headings, or a singular `### Decision`
reading as `d1`. That is *not* the same as `entry_body_decision_count`, which falls back to counting
`- D:` / `- Dn:` bullets. The two disagree on 10 entries (906 bullets vs 888 addressable): an old-style
entry with one `### Decision` heading and inline `- D1:` / `- D2:` bullets has exactly **one**
addressable ordinal, and emitting `graph:d2` on it is a hard error. **Enumerate with
`entry_body_decisions()`.** Never count bullets.

The draft spec quotes 881 across 621 entries. That number moved for **two** reasons — corpus growth
(621 → 635 entries) *and* the unit correction above. A reader who sees only "881 → 888" will assume
drift and re-derive the wrong figure.

## The pipeline

```
enumerate judgment units                         (core, mechanical, network-free)
    -> one task per addressable dN, plus one bare-entry task per zero-decision entry
PILOT (the gate)                                 (~20 entries with good authored topics, judged blind)
    -> Leg A machine-scored roll-up recall; Leg B human-adjudicated attribution
    -> pass line below decides proceed / re-prompt / abort. NOTHING is written by the pilot.
Workflow fan-out                                 (optional layer, network)
    -> one haiku agent per judgment unit; each returns <=3 slugs with a grounding quote
orchestrator validation                          (mechanical-first, no new model calls)
    -> drop verdicts that fail vocabulary, ordinal existence, the per-decision cap, or quote grounding
batch approval                                   (the human gate)
    -> surface the surviving attributions as one batch; the user approves, edits, or rejects
write + check
    -> approved slugs written to the ENTRY's date file under sessions/topics/; links check validates
```

### 1. Mechanical enumeration

There is no `topic audit --json`; the sibling's `link audit` has no counterpart here because topics are
a per-entry attribute, not a pair. The orchestrator enumerates directly, network-free:

```python
from memory_seed.core import entry_body_decisions
from memory_seed.semantic_cache import extract_memory_chunks

for chunk in extract_memory_chunks("."):
    if not chunk.entry_id:
        continue
    decisions = entry_body_decisions(chunk.text)   # [DecisionSummary(ordinal, name, text), ...]
    # one task per decision; if `decisions` is empty, ONE bare-entry task instead
```

Each task carries the entry title, the decision's `ordinal`, `name`, and `text`, and the vocabulary
from `.memory-seed/topics.yaml` — canonical slug + label + description + **`axis:` and `parent:`**, so
the worker can see which axis a slug answers and which slugs are narrower than which. Aliases go in for
recognition only.
`memory-seed topics suggest --from <file>` is a network-free lexical prior and may seed a shortlist,
but it is file-level and is not the judgment.

### 2. The judging criteria (what the swarm decides)

Each agent returns, per judgment unit:
`{entry_id, ordinal, area, activities: [...], why, quote, confidence}` — `ordinal` is `null` for a
bare-entry task.

**Hand the worker TWO separately labelled closed lists, `areas` and `activities`, never one merged
vocabulary.** The two axes are the same SHAPE (bare slugs), and the one time two same-shaped
vocabularies shared a payload in this project six ADRs took a constitution slug into their topics
field. Assert before fan-out that no slug appears in both lists; the separation is structural, not an
instruction the worker can misread.

**Always offer the escape hatch.** A worker that finds NO area honestly names what a decision is
about may answer `area: null` plus `proposed_area: {slug, why}` instead of forcing one. Without it a
genuine vocabulary gap is indistinguishable from carelessness: it comes back as a wrong-axis drop,
and two campaigns read that pattern as a missing slug on exactly that evidence. Offered the hatch on
2026-08-07, a worker used it zero times out of 4 and found existing areas instead — which is the
kind of thing you can only learn by making declining possible. A proposal is a REQUEST routed to the
ESR queue for a human to rule on; it never becomes vocabulary by being used.

The conventions below are corpus-measured, not imposed; they are recorded live in
`docs/2_Todo/decision-level-topics-proposal.md` and this prompt teaches them verbatim.

1. **Two axes, one of each, ~2 slugs per decision.** Name **where** the work is (`axis: area` — WHAT
   you are working on) and **what was done** (`axis: activity` — what KIND of work it is). This is no
   longer convention taught in prose: `topics.yaml` declares `axis:` on every root and
   `TopicIndex.axis_of()` answers it for any slug, children included, since a child inherits its
   parent's axis and never crosses it. The axis is deliberately **not** called a "subsystem" — the
   vocabulary ships to projects that are not software, where an area translates and a subsystem does
   not.

   **`topics.yaml` is the authority; read it rather than the list below.** This snapshot of the repo's
   own roots (children in parentheses) is a shape illustration measured 2026-07-26, and is exactly the
   thing that goes stale:

   - **area** — `graph` (`related-entries`, `supersession`, `continuity`, `schema`), `memory-trace`,
     `memory-seed`, `session-logging` (`decision-harvest`, `backfill`), `session-layout` (`migration`,
     `multi-user-sessions`), `session-fuse`, `mcp-tools` (`cli`), `control-plane` (`agent-rules`,
     `skill-architecture`, `governance-profile`, `lazy-loading`), `process-management`
     (`upgrade-workflow`), `retrieval`, `hooks`, `mermaid`, `windows-encoding`
   - **activity** — `documentation` (`readme`, `functionality-audit`, `document-ingestion`), `bugfix`
     (`process-correction`, `memory-repair`, `cleanup`), `git-workflow` (`merge`, `branch-history`,
     `git-publishing`), `release` (`release-packaging`, `release-preflight`, `changelog`),
     `proposal-lifecycle` (`proposal`, `roadmap`, `goal`), `tooling-evaluation` (`licensing`,
     `design-evaluation`), `ui-design`, `agent-collaboration`, `security`, `performance`

   A child is the better answer whenever it fits — see rule 4. Authored entries average 2.26 canonical
   slugs; two is the target, not a floor to pad toward.
2. **Cross-cutting concerns are rare add-ons, not a third axis.** `windows-encoding`, `performance`,
   and `security` are quality attributes spanning any (area, activity) pair; they total ~11 uses in
   the whole corpus. Reach for one **only when the quality concern is genuinely the theme** (a
   `performance` fix in the `graph` layer). A third mandatory axis was assessed and rejected — it has
   no home in the vocabulary beyond these three low-use slugs and would push the corpus past its
   measured norm.
3. **The cap is 3 per decision, and it binds.** `MAX_TOPICS_PER_DECISION = 3`; the rolled-up entry
   union is deliberately uncapped, because a six-decision entry legitimately spans more ground than a
   one-decision one. Three is the ceiling, ~2 is the expected output. A label that fits everything
   distinguishes nothing.
4. **Canonical slugs only — and the most specific canonical slug that fits.** Aliases resolve at read
   time but a sidecar carrying one is a `non-canonical-topic-slug` error. **A child slug is canonical
   in its own right and is the better answer, not a violation:** prefer `related-entries` over `graph`
   and `merge` over `git-workflow` wherever the narrower slug is true. Specificity is free — the parent
   is derived from the child at read time (`TopicIndex.ancestors()`), so a child costs no extra budget
   and a filter on the parent still matches it. What must never be emitted is a **spelling variant**:
   `performance`, never `perf`; `memory-trace`, never `memory-trace-ui`. Only 11 topiced entries still
   author an alias (12 distinct, measured 2026-07-26 — down from 45 because 31 of the old aliases were
   the second kind and became child slugs) — the swarm must not copy even those.

   **A slug must fit EVERY ancestor, not just its immediate parent** (JNL, 2026-07-27). Before
   emitting a grandchild, check the whole chain: `inspector` asserts the work is in the inspector pane,
   AND that it is `panes` work, AND that it is `memory-trace` work. If any link in that chain would be
   wrong, the slug is wrong — emit the deepest ancestor that *is* true instead, or nothing.

   This is what pays for depth. Specificity is free only because every consumer rolls up
   (`expand_topic_filter` matches a parent against all its descendants), and roll-up is a promise:
   filtering on `memory-trace` returns this entry. A leaf that does not honour its chain does not
   merely mislabel one entry — it silently pollutes every ancestor's filter, and it does so invisibly,
   because nobody inspecting `memory-trace` sees which leaf put the entry there. Rule 4's pressure
   toward the narrowest slug is therefore bounded by this: **narrower is better only while every level
   above stays true.** When in doubt, go up a level; a correct parent beats a plausible child.
5. **Bare slugs are permanently legal, not a migration stage.** A zero-decision entry (34 of them —
   a note, an observation, a milestone) can never carry a decision-keyed topic and takes a bare slug.
   Bare slugs keep the per-*entry* ceiling of 4 (`MAX_INFERRED_TOPICS`), not 3.
6. **A decision-keyed slug that refines an authored entry-level slug is enrichment, not redundancy.**
   Attributing `graph:d1` to an entry the author tagged `graph` *adds* the per-decision attribution the
   author never recorded. That is the point of the campaign; do not suppress it. (`links check` agrees:
   only *bare* sidecar slugs can trip `topic-already-authored`.)

The `quote` field must be a verbatim phrase from that decision's own body grounding the choice. If the
agent cannot quote something specific for a slug, that slug is dropped rather than guessed.

### 3. Orchestrator validation (mechanical-first — no new model calls)

Before surfacing anything, the orchestrator drops attributions mechanically. **Anything failing is
dropped, never repaired** — a repaired verdict is the orchestrator's judgment wearing the swarm's
provenance.

- **Vocabulary:** the slug must resolve in `.memory-seed/topics.yaml` **as a canonical slug**, not an
  alias. Unknown → dropped; alias → dropped (not silently canonicalized: the drop is the signal that
  the prompt taught the wrong spelling).
- **Ordinal existence:** `dN` must appear in `entry_body_decisions(entry.text)` for that entry. Reuse
  `links check`'s own `dangling-topic-decision` rule rather than a second implementation.
- **Per-decision cap:** at most 3 slugs per `(entry_id, ordinal)`; at most 4 for a bare-entry
  attribution. Over-cap groups are dropped whole, not truncated to the first three.
- **Quote grounding:** the `quote` must appear in that decision's body (whitespace-normalized substring
  match). This is the primary hallucination guard — a slug whose quote is not found is discarded.
- **Duplicate slug:** the same slug twice in one block is a `malformed-topic-sidecar`; dedupe within a
  block is legal, across decisions of one entry is expected (the roll-up dedupes at read time).
- **Axis sanity:** now mechanical rather than a spot-check — `TopicIndex.axis_of()` resolves every
  emitted slug (children inherit), so the orchestrator can count areas and activities per block
  directly. Flag a block that is two activity slugs with no area, or three cross-cutting slugs — the
  two shapes the swarm most often over-calls, and the first of which the pilot measured on 10 of 45
  units before the axes were an output contract.

Surviving attributions are candidates; everything dropped is logged so the human sees what was filtered
and why.

### 4. The pilot — this is the gate

**Run the pilot before the campaign, and write nothing from it.** A pilot with no pass/fail line is not
a gate.

**Sample.** 20 entries drawn from entries that **already carry good authored topics** (2-4 authored
slugs), stratified **14 with ≥2 addressable ordinals + 6 single-decision** — otherwise Leg B has
nothing to measure, since inheritance and the swarm are indistinguishable on a one-decision entry. Draw
with a **recorded fixed seed** so the sample is reproducible and visibly not cherry-picked. As of
2026-07-26 the pools are 125 multi-decision and 240 single-decision entries.

**Blind means blind.** The authored `topics:` live in the entry's own YAML metadata block. Workers must
receive the **decision body only**, taken after the metadata fence — the same slice `entry_body_decisions`
returns. Leaking the metadata block invalidates the whole pilot.

**Leg A — roll-up recall (machine-scored).** The human never recorded per-decision attribution, so
agreement with what they wrote can only score the **rolled-up union**. Canonicalize *both* sides through
`topics.yaml` before comparing — a residual 11 entries still author an alias, and unresolved, `perf`
scores as a miss against `performance`. **A re-run must also expand ancestors**, which the 2026-07-26
runs did not have to: now that 31 aliases are child slugs, a worker emitting `related-entries` against
an author's `graph` is *more* specific and correct, but scores as a flat miss unless
`TopicIndex.ancestors()` is folded in before comparing. Report macro-averaged recall of the authored
set, and precision as a diagnostic only — an entry's authored list is a floor, not a ceiling, so a
legitimate addition would score as a precision error.

Anchored against baselines computed on the same corpus, same canonicalization, same macro-average:

| Predictor | Macro-recall |
|---|---|
| Random 2 slugs from the vocabulary | 0.10 |
| Always the top-2 authored slugs (`graph`, `memory-trace`) | 0.32 |
| Always the top-3 authored slugs (+ `memory-seed`) | 0.43 |
| Always the top-4 | 0.52 |

- **PROCEED at macro-recall ≥ 0.70.** The swarm must recover a clear majority of what the author wrote
  and beat the strongest free constant-guess baseline (0.43) by a wide margin.
- **ABORT below 0.55.** That is ~0.12 above a predictor that reads nothing; at that level the swarm is
  not earning 922 judgments and the corpus is better served by inheritance.
- **Between 0.55 and 0.70:** re-prompt **once**, redraw a fresh disjoint sample of 20, re-run. A second
  failure aborts. Do not tune the prompt against the same sample — that is fitting to the gate.

#### Recorded outcome — both runs are spent and the gate ABORTED (2026-07-26)

| | run 1 | run 2 (the one re-prompt) |
|---|---|---|
| seed | 20260726 | 20260726002 |
| sample | 14 multi + 6 single, 45 units | 14 multi + 6 single, 45 units, **disjoint by construction** |
| **Leg A macro-recall** | **0.583** | **0.613** |
| precision (diagnostic) | 0.521 | 0.587 |
| slugs proposed / surviving | 88 / 83 | 94 / 92 |
| sole validator drop reason | quote-not-grounded (5) | quote-not-grounded (2) |
| baselines on that sample | random-2 0.087, top-2 0.217, top-3 0.362, **top-4 0.404** | random-2 0.085, top-2 0.208, top-3 0.408, **top-4 0.500** |

Held constant across both runs: haiku, one worker per judgment unit, the stratification, the harness,
the validator, and the pass line. Run 2's brief is versioned at
`scripts/topic_swarm_worker_brief.md` and was committed **before** its fan-out.

**Why it fell short, measured rather than guessed.** Run 1's recall loss was 63% *area*-slug misses,
and only 24 of 45 units emitted the intended one-area + one-activity shape (10 emitted **no area at
all**). Run 2 made the two axes an output contract and that fix landed completely — **45 of 45 units
emitted exactly one area and one activity**, spurious slugs fell 38 → 27, quote drops fell 5 → 2, and
precision rose 0.066. Recall rose 0.030, which at n=20 (SE ≈ ±0.065) is noise.

So the residual misses are **not shape errors, and not fixable by prompting**:

- **The `area` axis is genuinely ambiguous, because `graph` is both an area and a subject.** Three
  run-2 entries (`mse_aa4tha73d513ptnt`, `mse_d9zzc4jeadak3g8r`, `mse_rqkgatgt5eh55yb8`) are authored
  `graph` + `memory-trace` + `ui-design`; workers called every decision `memory-trace` + `ui-design` and
  lost `graph`, capping each at 0.67. Both readings are defensible — the author used `graph` for the
  *subject matter*, the worker used `memory-trace` for the *package*. Decisively, the confusion runs
  **both** ways: on `mse_cdndmm2p0dmbkbq9` the swarm emitted `graph` and the author did not. So this is
  an ambiguous axis, not workers under-calling one slug — and no prompt resolves it. The vocabulary
  would have to.
- **One area per decision structurally caps roll-up recall.** When an entry's decisions all sit in one
  area — the common case — the rolled-up union contains exactly one area slug, while authors routinely
  write two or three. The attribution rule that maximises per-decision *precision* is in direct tension
  with the metric Leg A scores. This is a real limitation of Leg A as a gate, **stated here rather than
  used to excuse the result**: 0.613 is below 0.70 and the campaign is aborted on it.
- **The margin over free is thin.** On run 2's sample the always-top-4 constant guess scores 0.500. The
  swarm bought +0.113 for 45 model calls; the campaign would spend 933. The 0.70 line exists exactly to
  require a wide margin over a predictor that reads nothing, and the swarm did not clear it.

Leg B was never adjudicated — Leg A is the first gate and it did not clear, so the ~150–240 pair
human adjudication was not spent. **If this is ever revived, the premise must change first** (sharpen
the area axis in `topics.yaml`, or score Leg B–style attribution directly instead of roll-up recall),
and the pilot must be re-run from scratch under the new premise with a fresh pass line.

> **Note added 2026-07-26, after these runs: part of that premise has since moved.** The vocabulary
> now declares `axis:` and `parent:` at `schema_version: 2`, 23 roots carry an explicit axis, and 31
> aliases became child slugs — so the "sharpen the area axis" precondition is partly discharged, and
> the worker brief can hand the swarm a structured axis instead of a prose convention. This does
> **not** un-abort the campaign: nothing above was re-measured, `graph`-as-area-versus-subject is
> untouched by the change, and the numbers in this section stand exactly as recorded. Read it as
> "the door is no longer bolted", not "the gate passed".

**Leg B — attribution, benchmarked against inheritance (human-adjudicated).** Leg A alone would pass a
swarm that gets every slug right and every attribution wrong, which is exactly the thing decision-level
topics exist to provide. Inheritance — giving every decision its entry's whole authored topic set — is
free, needs no swarm, and is already the fallback in the proposal's sequencing. Its recall is 100% by
construction, so **precision is the only axis on which the swarm can earn its 922 judgments.**

On the 14 multi-decision pilot entries, pool the swarm's `(decision, slug)` pairs and inheritance's,
deduplicate, present them **interleaved and unlabelled**, and have the human mark each *correctly
attributed to that decision* or not. Then compare precision on the same adjudication pass.

- **PROCEED when swarm precision exceeds inheritance precision by ≥ 15 points** *and* swarm precision
  is ≥ 0.75 in absolute terms.
- **ABORT when the swarm does not beat inheritance,** or when absolute precision is below 0.60. If it
  cannot beat free, the backfill buys nothing.

**Cost of the gate.** ~50 addressable decisions across the 14 multi-decision entries yield roughly
150-240 distinct pair judgments after dedupe — on the order of an hour of human attention. Budget it
honestly: a gate nobody will sit through is not a gate.

**Do not carry the 28% forward as a comparison.** The prior entry-level pilot scored 28% *exact set
match*, a different and much harsher metric than macro-recall. "0.70 recall" is not "improved from 28%".

### 5. Batch approval (the human gate)

Surface the surviving attributions as ONE batch — entry, decision ordinal and name, the slugs, the
grounding quote, and the `why`. The user approves the batch, edits individual attributions, or rejects.
**Never write without this approval** (same gate as persona evolution and stub-to-edge conversion in
`end_of_turn.md`). A confidence floor may auto-*hide* low-confidence attributions from the batch, but
never auto-*writes* them. Keep batches small enough to review — one campaign is many batches.

### 6. Write + check

**A new block SUPERSEDES the entry's previous one wholesale — carry the old attributions
forward.** `entry_topic_sidecars` is most-recent-wins **per ENTRY**, not per decision, so a block
listing only the decisions this campaign judged silently un-attributes every sibling decision an
earlier campaign had already keyed. Their slugs stay on disk and stop being readable, which is worse
than losing them: nothing reports it. On 2026-08-07 this turned 14 already-attributed decisions into
gaps, and was caught only because the resulting gap count did not match the arithmetic. Before
writing, read the entry's current `decision_area`/`decision_activity` pairs and restate every one
this batch is not itself replacing.

**The file is keyed to the ENTRY's date, not to today.** This is the one place where copying
`link_swarm.md` will burn you: link sidecars are filed under the day the edge was authored, but
`topic-sidecar-date-mismatch` is an **error** that compares the entry's own logged date against the
sidecar's filename date. A batch of 40 entries therefore touches ~40 files —
`.memory-seed/sessions/topics/YYYY-MM/YYYY-MM-DD.md` for each distinct **entry** date — scattered
across every month the corpus covers. One block per entry, appended:

````markdown
---
tags:
  - session-log-topics
topic_date: 2026-05-14
---

## 2026-05-14 09:02 - topics (swarm batch 3)

```yaml
entry_id: mse_zwzdjn0m9e34gdth
topics:
  - memory-trace:d1
  - ui-design:d1
  - graph:d2
  - bugfix:d2
```
````

- The **filename** and `topic_date` are the entry's date. The **heading date** matches the file, as in
  the diagram and link families; the heading **time** is the block's precedence key.
- Block identity is `(entry_id, heading timestamp)`. Two blocks for one entry at the same timestamp in
  one file is `duplicate-topic-block` — a transcription defect, not a correction.
- Ordinals are written as `<slug>:dN`; a zero-decision entry takes bare slugs. A file may mix both.

Then run `memory-seed links check` — it owns all three sidecar families and is the only command that
validates a topic sidecar — and confirm integrity OK before merging. (`memory-seed topics check`
validates the vocabulary file and the topics **authored** in entries; it does not read sidecars.)

This block shape was exercised end to end on 2026-07-26 against a real three-decision entry: `links
check` passed, `entry_topic_sidecars` returned `(('d1', 'memory-trace'), ('d1', 'ui-design'), ('d2',
'graph'), ('d3', 'bugfix'))` with the roll-up union on `inferred_topics`, `memory-trace:d1` against an
authored entry-level `memory-trace` correctly did **not** warn, and refiling the same block under
today's date failed the check with `topic-sidecar-date-mismatch`. The probe was then removed; no topic
sidecar is committed.

## Correcting a batch that turns out wrong

Topic sidecars are **append-only with most-recent-wins per entry** — the topic-family instance of
`docs/3_Spec/draft/sidecar-supersession-model.md`. A topic list is a *state* replaced wholesale by a
better one, so unlike link edges there is no `retracts:` mechanism and none is needed.

To re-attribute an entry, **append a new block to the same entry-date file under a strictly later
heading time**. Precedence is `(heading timestamp, block index within the file)` — and because the
date-mismatch rule pins every block for an entry into that one file, a later *file* can never
supersede an earlier one. Read the entry's existing blocks and choose a time greater than all of them.

Never edit or delete the superseded block (Invariant #2): it stays readable as the record of what was
previously believed, and the swarm campaign that produced it stays auditable. Note the batch in the
heading title (`- topics (swarm batch 3, corrected)`), which is free text.

## Guardrails

- Run on the trunk / integration checkout, not a task branch — sidecars belong on main (see
  `agent_collaboration.md`).
- The swarm only *suggests*. The enumeration, the validation, the pilot, the approval, and the write are
  all outside the model's authority — a stronger `topics suggest`, not a new source of truth.
- Roll-up to entry level is a **read-time derivation** (Invariant #6). Never store the union; the
  sidecar holds decision-keyed slugs and `entry_topic_sidecars` exposes both channels.
- A decision-level consumer must exist before the full campaign runs — the gate recorded in
  `docs/2_Todo/decision-level-topics-proposal.md`. Judging 922 units that nothing renders is waste.

See `docs/3_Spec/draft/decision-level-topic-sidecars.md` for the grammar and precedence contract, and
`docs/2_Todo/decision-level-topics-proposal.md` for the two-axis conventions and why the cap is 3.
