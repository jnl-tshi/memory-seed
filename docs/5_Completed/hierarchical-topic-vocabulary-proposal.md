---
completed_on: "2026-09-19"
completion_note: "The approved hierarchy and 17-slug vocabulary change shipped; optional project-type starter packs are parked separately."
priority: P3
next_action: "ACCEPTED 2026-07-26/27 (JNL, settled inline below) - not a JNL gate any more. Build order steps 1, 2, 4, and one neutral starter under step 6 are shipped. The one still-open piece: a per-project-type starter vocabulary (a `--project-type` at `init`, or named starter sets) needs its own JNL call on the axis - see the step-6 correction below. Superseded serialization-wise (not decision-wise) by the schema_version 3 zone/nesting work."
---

# Hierarchical topic vocabulary: parent subsystems, child subsystems

Status: **PROPOSAL — 2026-07-26.** Raised by JNL after the concentration review: *"reframe the
hierarchy in the topics so that it covers topics which subsystem parents and subsystems children, and
the same might be useful for activities"*, and then — the point that ties it to the graph — *"if the
definitions are framed in this way the communities should also be generated more easily at decision
level granularity."*

## The hierarchy already exists. It has been crushed into the alias field.

`aliases:` is documented as spelling variants — "prefer renaming via `aliases:` over deleting". In
practice it has been carrying two different relations at once:

| relation | example | correct home |
|---|---|---|
| **spelling variant** (same concept) | `memory-trace-ui` → `memory-trace`, `perf` → `performance` | alias |
| **narrower concept** (child) | `continuity`, `supersession`, `schema`, `related-entries` → `graph` | **child, not alias** |
| | `agent-rules`, `skill-architecture`, `lazy-loading` → `control-plane` | **child** |
| | `readme`, `functionality-audit`, `document-ingestion` → `documentation` | **child** |
| | `changelog`, `release-preflight` → `release` | **child** |
| | `merge`, `branch-history` → `git-workflow` | **child** |

Most of the 43 aliases in use are the second kind. That is not sloppiness — it is a flat schema
forcing a hierarchical vocabulary through the only field available.

**What the flattening costs.** Alias resolution maps child → parent and *discards the child*. An entry
authored `continuity` is read as `graph`, forever, with no way to recover that it was about continuity
specifically. Measured: **43 distinct aliases in use across 45 entries** are having their specificity
thrown away at read time.

**Correction (2026-07-26, after building step 2).** This paragraph originally continued: *"It also
inflates the parents — part of why `graph` reads at 23.8% is that it absorbs everything authored as
`supersession`, `continuity`, `schema`, `related-entries` and `topics`."* **That was wrong**, and
promoting the aliases measured it:

| slug | before | after | movement |
|---|---:|---:|---|
| `memory-trace` | 197 | **197** | **none at all** — its only alias in use is one genuine spelling variant |
| `graph` | 106 | 103 | 3 entries, not the "part of why" claimed |
| `proposal-lifecycle` | 89 | **77** | the real mover, and **unforecast** — bigger than graph and memory-trace combined |

So **alias flattening was never the source of the concentration.** The specificity recovery is real —
**42 of the 45** alias-carrying entries gained it, and every parent's rollup is unchanged so filtering
reach cost nothing — but it is a *different benefit* from breadth relief. The concentration is
genuine breadth in `memory-trace`, and only new children (step 2's invented half) and the sweep can
touch it. Kept visible rather than quietly edited: the claim shaped the case for doing this work, and
the work was still worth doing for the reason that survived.

## Design

**A slug declares its `axis:` — `area` or `activity`.** The two-axis model is currently *convention*,
described in a project-local proposal and taught to the swarm in prose. Nothing in the schema knows
which axis a slug belongs to, so nothing can check it. Making it a field turns the model from advice
into structure. `schema_version: 1 → 2` carries this and `parent:` together — one bump, not two.

**A slug may declare a `parent:`.** One parent. A child inherits its parent's axis; mixing axes across
a parent/child edge is a validation error. The hierarchy lives **within** an axis — areas nest under
areas, activities under activities — never across.

**Depth is earned by concentration, not fixed** (JNL, 2026-07-26). An earlier draft of this proposal
capped the tree at two levels. That was wrong in both directions: it would force sparse areas to invent
children they do not need, and cap dense ones short of the specificity the corpus demands. An area of
higher complexity should gain grandchildren that further break down its children; a thin one should
stay a leaf.

The trigger is the measurement that started this thread. **A slug earns children when it is carrying
too much of its scope** — and the existing data anchors where that line sits:

| slug | share | reading |
|---|---:|---|
| `memory-trace` | 44.2% | plainly too broad — earns children, and likely grandchildren under `trail` |
| `graph` | 23.8% | too broad — earns children |
| `session-logging` | 11.7% | healthy — stays a leaf |
| `mcp-tools`, `retrieval`, `mermaid`, … | ≤ 4.3% | healthy — stay leaves |

So the line is somewhere between 12% and 24% of the corpus at top level; below it a slug is doing its
job, above it the label has stopped distinguishing. At deeper levels the same question is asked
against the **parent's** population rather than the whole corpus — a child taking most of its parent's
volume is the next candidate to split.

This makes the vocabulary **self-governing**: the concentration review in
[`topic-vocabulary-concentration-review.md`](../7_Replaced/topic-vocabulary-concentration-review.md) stops being a one-off audit and becomes a periodic health
check that says *where* to deepen and *when to stop*. Depth is then bounded by evidence rather than by
a rule nobody can justify — which is the real protection against a taxonomy nobody maintains, since no
level exists unless the corpus paid for it.

### The two axes, named for any project — not for software

`area` answers **"what are you working on"**. `activity` answers **"what kind of work is it"**. Neither
word may assume software, because Memory Seed is a general memory substrate — it can be initialised in
a Substack folder, a research project, a legal matter.

This is a **shipped defect today**, not just a naming preference. The starter vocabulary in
`memory_seed/seed/.memory-seed/topics.yaml` is `architecture, bugfix, documentation, release,
workflow` — every slug assumes a software project, and four of the five are activities, so a new
project starts with **no area axis at all**. A Substack writer's first experience of the vocabulary is
being offered "bugfix" and "release". Meanwhile "subsystem" appears throughout the control plane
(`agent-rules.md`, `agent_collaboration.md`, `session_logging.md`, `topic_swarm.md`), teaching a
software framing to every project that installs it.

For that Substack folder the axes should read naturally: **areas** like `newsletter`, `essays`,
`research`, `audience`; **activities** like `drafting`, `editing`, `publishing`, `planning`. If the
shipped language cannot express that without translation, it is wrong.

**To be precise about what changes and what does not** (JNL, 2026-07-26): `topics:` stays the field
and stays the category name. It is already neutral and it is what every consumer reads. What is
retired is the word **"subsystem"** as the *label for the first axis* — that is the term that fails to
travel, since a Substack folder has areas but no subsystems. So: `topics:` unchanged, axis named
**area**, and "subsystem" retired from the control plane and its twins.

Equally, this project's own slugs are **fine as they are**. `memory-trace`, `mcp-tools`, `session-fuse`
are software terms in a software project — correct, and deploy-once project-local state that
`memory-seed update` never overwrites. The neutrality requirement binds the **schema and the shipped
control plane**, not a curated local vocabulary.

**Starter vocabularies should vary by project type.** A software project and a writing project want
different opening slugs, and the useful shape is the same in both: a handful of areas plus a handful of
activities. There is already a mechanism for this — `SKILL_PROFILES` in `core.py` keys shipped control-
plane content by profile (`coding`, and others), so a starter vocabulary can hang off the same key
rather than inventing a parallel concept. What must be *universal* is the two-axis structure; what is
*per-profile* is which slugs fill it.

**Correction (2026-07-26, after building step 6): `SKILL_PROFILES` cannot carry this, and step 6
shipped ONE neutral starter instead.** Two properties of the mechanism defeat the idea, and neither
is visible until you try it:

1. **Profiles are additive at any time; `topics.yaml` is deploy-once.** `memory-seed skills add
   <profile>` installs a profile on day 30, but the vocabulary is written once at `init` and `update`
   never overwrites it. A profile added after init could never contribute a slug — so the per-profile
   vocabulary would silently apply to whichever profiles happened to be selected in the first minute
   of the project's life, and never again. That is a worse failure than a generic starter, because it
   is invisible.
2. **Profiles are composable capability bundles, not mutually exclusive project types.** A project can
   hold `coding` + `marketing` + `documents` at once. Union-ing three vocabularies needs a merge rule,
   a collision rule for the same slug arriving at different axes, and a slug-ownership concept that
   does not exist today. The proposal assumed profiles partition projects; they do not.

So the useful per-project-type variation is real but **needs its own key** — a `--project-type` at
`init`, or a set of named starter vocabularies to pick from — not a re-use of `SKILL_PROFILES`.
Recorded as a follow-up rather than built, because it is a new user-facing choice at init and wants
JNL's call on the axis. What shipped is one starter that is `schema_version: 2`, declares `axis:` on
every slug, and carries both axes with domain-neutral names (`deliverable`, `research`, `operations`
/ `planning`, `drafting`, `review`, `correction`, `publishing`), shipped **flat** because a project
with no corpus has earned no depth. `deliverable` is deliberately a placeholder: the header comment
says so and tells you to split it, because the area axis is exactly where a project's specificity
lives and a generic area is the one thing a starter cannot supply.

### Follow-up: a cheap guard against skill-versus-vocabulary staleness

`topic_swarm.md` went factually wrong the moment step 2 landed — it told the swarm to emit `graph` and
never `related-entries`, which by then was a canonical child slug, and its axis lists were missing all
31 promoted children. **Nothing went red**, because `docs check` does not cross-validate a skill
against `topics.yaml`. The staleness would have been carried into a 933-judgment campaign.

Proposed (not built): a `docs check` rule that extracts backticked slugs from the skill's judging-
criteria section and asserts each resolves as a **canonical** slug in the local `topics.yaml`. Two
honest caveats, which is why this wants a decision rather than a quiet implementation:

- The skill legitimately names aliases as **counter-examples** ("`performance`, never `perf`"), so the
  rule needs a scoped region or an opt-out marker rather than scanning the whole file.
- The shipped skill is generic while the check reads the *local* vocabulary, so it can only guard this
  repo, not every install. That is still worth having — this repo is where the campaign would run —
  but it is a lint, not a schema guarantee.

### What the explicit axis buys immediately

**Validation becomes a shape rule instead of a blunt count.** Today the guard is `MAX_TOPICS_PER_DECISION
= 3` — a ceiling that cannot tell three activities and no area from a well-formed one-of-each. With
`axis:` declared, `links check` can enforce the actual intent: *at most one area per decision, at least
one axis represented.*

That matters because it is a **measured** failure mode, not a hypothetical. In pilot run 1, **10 of 45
judgment units emitted no area at all** and only 24 of 45 held the one-area+one-activity shape. Run 2
fixed it to 45/45 — by *prompting harder*. A prompt-enforced invariant regresses the moment someone
rewrites the prompt; a schema-enforced one cannot.

**Store the most specific slug; derive ancestors at read time.** An entry tagged `trail` is *also*
about `memory-trace`, but only `trail` is stored. Consequences:

- **The cap is unaffected** — it counts stored slugs, so a parent never consumes budget.
- **Search and filters expand downward.** Querying `memory-trace` matches `trail` entries. This is the
  same shape as the alias expansion `expand_topic_filter` already performs, so there is a natural home
  for it rather than a new mechanism.
- **No entry is rewritten.** The 197 entries carrying `memory-trace` are tagged at *parent* granularity
  — coarse, not wrong. Invariant #2 is untouched, and the corpus needs no migration.
- **A sweep can add a child later** to an entry carrying only the parent. That is enrichment against a
  gap, permitted under the `(source rank, then recency)` precedence rule without any retraction.

**Aliases keep exactly one job**: spelling variants of the same concept. Everything currently
mis-filed there becomes a child slug, which *recovers* specificity the corpus already recorded.

## Why this beats the flat splits

[`topic-vocabulary-concentration-review.md`](../7_Replaced/topic-vocabulary-concentration-review.md) recommended carving `trail` out of `memory-trace` and
splitting `graph`. A hierarchy achieves the same specificity **without the two costs of a flat split**:

1. A flat split leaves `memory-trace` and its new sibling as unrelated peers, so the 197 historical
   entries become permanently unclassifiable at the finer grain — nothing connects the old label to the
   new one. Under a hierarchy they are simply parent-level.
2. A flat split forces a choice between breadth and specificity in one field. A hierarchy keeps both
   and lets each consumer pick its level.

So this **supersedes** the flat-split recommendation rather than competing with it.

## Communities — the reason this matters for the graph

Node colour today comes from **topics**, not topology (`graphCommunities.ts`). The topology route was
measured and closed: Louvain never merges across connected components, so on this corpus `k` is
floored at **110** and a ~16-slot legend is arithmetically unreachable
(`adr-graph-community-detection.md`, re-measured 2026-07-26).

Topic-derived communities have no such floor — they are *designed*, not discovered. But today they
inherit the concentration problem: three slugs (`memory-trace` 44.2%, `memory-seed` 24.2%, `graph`
23.8%) dominate the palette, so most of the map is three colours.

A hierarchy fixes this by **splitting the two jobs a community has to do**:

- **Parent → colour.** Few, stable, legible. A bounded palette that does not reshuffle as the corpus
  grows, because parents change rarely.
- **Child → grouping and filtering.** As specific as the vocabulary gets, without spending colours.

And it is what makes this work **at decision granularity**, which is JNL's point. A decision is a
smaller unit than an entry and should carry roughly one area and one activity — too small to justify a
colour of its own, but exactly the right size to sit inside a parent's colour. Per-decision child slugs
give the clustering; the parent gives the hue. That is a decision-level graph whose colouring is
legible and whose grouping is meaningful, which neither the flat vocabulary nor Louvain could deliver.

## Activities

JNL asked whether activities want the same treatment. **Partly — and for a different reason.**

The concentration review measured the activity axis as healthy: a graded distribution topping out at
21.3%, no slug swallowing the corpus. So hierarchy is **not** needed there to fix breadth.

But the alias evidence shows activities are losing specificity just as areas are: `documentation`
absorbs `readme` / `functionality-audit` / `document-ingestion`; `release` absorbs `changelog` /
`release-preflight`; `git-workflow` absorbs `merge` / `branch-history`. So apply the hierarchy to
activities for **specificity recovery**, not for concentration relief — and expect the tree to be
shallower and to matter less. Do areas first; treat activities as a follow-on that reuses the
mechanism.

## The surface should show the split it now knows about

If the vocabulary distinguishes two axes, a single undifferentiated **Topics** row hides exactly the
distinction the schema just made explicit. The inspector should carry **two sections — Area and
Activity** — rather than one list, and the same split belongs in the authoring surface, so an agent or
human is answering two questions instead of picking from one flat pool.

**Per decision, not per entry.** This is where it earns the most: an entry can legitimately span
several areas, but a *decision* is a single act of work with one area and usually one activity. Showing
Area/Activity per decision is what makes the pair meaningful rather than a union of everything the
entry touched.

The data path for this already exists. `inferred_decision_topics` carries `(ordinal, slug)` pairs and
the read side already exposes the per-decision channel alongside the rolled-up entry view (shipped
2026-07-26). So once `axis:` is declared, splitting the display is largely **presentation** — group the
pairs by decision, then by axis. No new backend field is required.

Sequenced after the graph work rather than before it, because the same `axis:` field feeds both, and
the graph's parent-colour/child-group split is the harder consumer to get right.

## Build order

1. **`axis:` + `parent:` fields, `schema_version: 2`, read-time ancestor derivation** in
   `load_topic_index` and `expand_topic_filter`. One schema bump carrying both. Behaviour-neutral:
   nothing reads the new fields yet, so the blast radius is visible before anything moves.
2. **Declare the axis for all 23 existing slugs**, and **reclassify** the aliases that are really
   children. This changes what 45 entries *resolve to* — strictly more specific, never contradictory —
   so re-measure facet counts before and after and record the delta.
3. **Shape validation**: at most one area per decision, at least one axis represented. Replaces the
   blunt `MAX_TOPICS_PER_DECISION` count with the rule that count was standing in for. Write-time
   only, per the precedent from the branch-provenance analysis — a check that fires across historical
   entries is one people learn to ignore.
4. **Point community colour at the parent level** and grouping/filtering at the child level.
5. **Split the inspector into Area and Activity sections**, per decision. Mostly presentation, since
   `inferred_decision_topics` already carries the pairs.
6. **Retire "subsystem" from the control plane** and ship a two-axis, domain-neutral starter
   vocabulary keyed by profile.
7. **Only then** any topic sweep, so it judges against a vocabulary that can express the distinctions
   being asked for — and so the constrained-choice question ("this entry is `memory-trace`; which
   child?") replaces the unconstrained 2-of-23 that the pilot measured at 0.613.

## Risks

- **Schema change touches every consumer** of the vocabulary: `topics check`, facets, the search
  filter, community colour, the swarm brief. Step 1 must be behaviour-neutral so the blast radius is
  visible before step 2 moves anything.
- **Two derivations risk.** Deriving the parent at read time is a second derivation of a displayed
  fact; the legend and node colour must both read it from **one** function, per the warning already in
  `graphCommunities.ts` — *"two derivations are how a legend ends up quietly lying."*
- **Depth discipline is a measurement, not a cap.** Depth is earned by concentration (see Design), so
  the guard against a taxonomy nobody maintains is that **no level exists unless the corpus paid for
  it**. Two failure modes to watch: deepening a slug because it *feels* broad rather than because it
  measures broad, and letting a level survive after the concentration that justified it has dispersed.
  Re-run the concentration review after each split — it is the same query, and it says both where to
  deepen and where a level has stopped earning its place. The five-question test still applies to any
  level added without a measurement behind it.

## Three rules settled 2026-07-27 (JNL)

### 1. Levels must be well bounded

A child earns its place by being *distinguishable without judgement*, not merely by being narrower.
The strongest boundaries are physical: `panes` splits into `inspector`, `topbar`, `navigation`,
`settings`, `workspace-bar` and `diagram-view` because each names a region that exists in the DOM — a
change is in one `<aside>` or another, so two siblings cannot overlap. Definitions written by hand carry
no such guarantee, which is why reading the component tree beat inferring groupings from entries.

Where no boundary exists, do not create the level however large the parent. `ui-design` (100) is the
open case: its plausible children — layout, theme, typography, motion, accessibility — are judgement
categories, and until they can be bounded the rule says leave it flat.

### 2. The floor applies only to the SECOND generation

`MIN_CHILD_ENTRIES` governs whether a new BRANCH of the tree is justified. Below that, **there is no
floor at all** — a one-off grandchild is fine.

**The floor is 5** (JNL, 2026-07-27, lowered from 8). The original 8 was set before this generation rule
existed, when a child was the only way to add specificity and that one constant was carrying the whole
weight of the depth question. It is not any more: this rule decides *where* the floor bites at all, rule
1 decides whether a level is coherent, and what is left for the number is the narrow job of asking
whether a new branch has evidence behind it. 8 was too blunt for that — `trace-harness` (7 agreed, with
a Storybook directory and a CI job behind it) is plainly a real category, and a rule that calls it
unearned is measuring the wrong thing rather than measuring strictly.

Depth is cheap once a parent exists to aggregate it, and every consumer already rolls up:
`expand_topic_filter` matches a parent against every descendant transitively (verified to three levels),
community colour keys on the ROOT so the palette never grows, and analysis can run at whatever
generation makes sense. A grandchild is therefore strictly more information than its parent carried
alone, at no cost to any reader who wants the coarser view.

This deliberately creates an incentive to GROUP. Sub-floor candidates that share a natural parent should
be proposed underneath it rather than beside it — which is exactly what `panes` did: six children of
2–6 entries each, all failing the floor individually, all floor-free once `panes` (23) carried them.

Not to be confused with `COMMUNITY_TOPIC_FLOOR` (10), which decides which topics may NAME a graph
community. That one stays: it governs how many colours the palette hands out, not what the vocabulary
may say.

### 3. A slug must fit every ancestor, not just its immediate parent

This is what rule 2 costs, and the cost falls on the **workers**. Assigning `inspector` asserts three
things at once — that the work is in the inspector pane, *and* that it is `panes` work, *and* that it is
`memory-trace` work. If any link in that chain is false then the slug is false, however well the leaf
itself fits; the worker emits the deepest ancestor that *is* true, or nothing.

The reason is that roll-up is a promise, not a convenience. Depth is free (rule 2) **because** every
consumer aggregates upward, so a filter on `memory-trace` is guaranteed to return everything filed
anywhere beneath it. A leaf that breaks its chain does not mislabel one entry — it pollutes every
ancestor's filter above it, and does so **invisibly**, since nobody reading `memory-trace` can see which
leaf put a stray entry there. The deeper the tree grows, the further one bad fit propagates, so this
rule is what keeps rule 2 from compounding.

The two pressures are therefore bounded against each other: the swarm brief's rule 4 says *take the
narrowest slug that fits*, and this says *narrower is better only while every level above stays true*.
When in doubt, go up a level — a correct parent beats a plausible child.

No script can check semantic fit, so the tooling makes the claim visible instead.
`propose_topic_children.py` prints the chain a candidate must satisfy — `git-workflow > merge > <child>`
— in both `gather` and `score`, and `topic_swarm.md` teaches the rule inline in §2 rule 4, where the
pressure toward specificity is applied rather than as a footnote read after the damage is done.
