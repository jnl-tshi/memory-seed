---
status: research
kind: report
created: 2026-09-24
scope: Atomic-unit extraction research and a FACT/DECISION item proposal for Memory Seed
non_goals:
  - changing any code, schema, validator, or existing record
  - adding edge kinds or identity grammar without a separate ADR/Constitution decision
---

# Atomic facts and decisions: research survey and item proposal

## Verdict

- **Keep the decision record as the atomic decision.** The research doesn't support splitting a decision
  from its reasons. Fact-checking work converged on *molecular* units: minimal, but carrying enough
  context to stand alone. Memory Seed's `(entry_id, dN)` DRAFTS record already has that shape. What it
  lacks is a clear atomicity rule (one issue, one chosen option, one scope) and a decontextualized
  one-sentence claim.
- **Add FACT as a new, separate item kind.** A fact is non-authoritative and truth-apt: an observation,
  measurement, constraint, assumption, or definition. It carries a `volatility` flag and can be
  replaced. The existing Documentation kind can't hold facts because it has no lifecycle, and
  invalidation is the entire reason to atomize facts.
- **The main new value is the decision→fact dependency (`rests_on`).** When a measurement or
  constraint changes, every decision that rested on it becomes reviewable. IBIS, QOC, Toulmin and
  agent-memory systems like Zep and Mem0 all model this link, and Memory Seed currently doesn't.
- **Store `rests_on` as a field, not an edge.** The ADR ledger's `supporting_decisions` already works
  this way. Storing it as a field keeps the Constitution-governed edge-kind set untouched.
- **Retrieval needs no new decay.** Existing supersession damping (0.10) and the successor boost
  already carry temporal truth for decisions. Facts reuse them. Fact hits roll up to the decisions
  they support, following the pattern of the current section→entry rollup. Invariant 7 (never hide)
  applies unchanged.
- **Curator extraction must be grounded and closed-world.** It works from logged records plus the
  orchestrator's harvest packet. It gets verbatim quotes of 40–120 characters and a closed list of link
  candidates. Any label that changes structure is run twice and only the intersection is kept.
  Supersede and support candidates are written as inert `classify_pending` stubs, never as live edges.

---

## 0. What exists today (the baseline this builds on)

Read from the repository on 2026-09-24; see the cited files for the full contracts.

| Concern | Current mechanism | Where |
|---|---|---|
| Atomic decision identity | `(entry_id, dN)`, with refs written `mse_x:dN` | `.memory-seed/decisions/adr_decision_identity.md` |
| Record shape | DRAFTS typed records: `#### Dn - Decision:` / `Documentation:`. Scope is universal. Decision records require Disposition and R. A/F/T are optional. S is required when a repository source materially informed the record. | `.memory-seed/decisions/adr_draft_format.md`, `.memory-seed/index.md` |
| Who decided | `decision_origins: {dN: user \| agent}` in the entry YAML | session entries |
| Lifecycle | `related` / `supersedes` (replaces) / `evolves` edges. They are forward-only and acyclic. Late-discovered edges go in link sidecars, with inert `classify_pending` stubs. | `adr_edge_kinds.md`, `docs/3_Spec/lifecycle-edge-linking-sidecars.md` |
| Topics | Controlled two-axis vocabulary. Decision-level topic sidecars are amended append-only. | `.memory-seed/topics.yaml` |
| ADRs | Event ledger with a derived current view. Events carry `supporting_decisions` as a **field**. | `.memory-seed/decisions/*.md` |
| Retrieval | BM25F lexical, plus model2vec cosine (additive blend, weight 15), plus a recency multiplier floored at `RECENCY_FLOOR = 0.98`, plus `REPLACED_RANK_DAMPING = 0.10` (on by default), plus a bounded successor boost (on by default). Default `granularity="decision"`, with rollup to entries. There is no cross-encoder reranker in the code. "Reranking" here means these multiplicative passes. | `memory_seed/retrieval.py`, `memory_seed/semantic_cache.py` |
| Curator | Proposed single Decision Curator, gate-triggered. It returns a receipt and a diff, and the orchestrator decides. | `docs/1_Inbox/decision-curator-orchestration-proposal.md` |
| Prior "meaning" idea | A Meaning Sidecar ablation: `core` / `because` / `constraint`, with SRO propositions as the upper bound | `docs/1_Inbox/semantic-compression-benchmark-proposal.md` |

Two measurements from the repo frame the problem:

- **Recovering evidence after the fact is weak.** The 2026-09-24 alignment study recovered only 0/50 High
  and 3/50 Medium decision→chat alignments (`experiments/decision-chat-alignment/REPORT.md`). Facts
  therefore have to be captured at the gate, first-hand, and not mined from history later.
- **Brute-force vectors are cheap at this scale.** Embedding 637 entries took 0.17 s once the model was
  loaded (`lifecycle-edge-linking-sidecars.md`). The corpus now holds about 1,640 canonical decisions.

---

## Part 1 — Research survey

### 1.1 Atomic fact / proposition decomposition

**Atomic unit.** A short, self-contained natural-language statement carrying one piece of information.
FActScore defines an atomic fact as "a short statement containing one piece of information." Dense X
defines a *proposition* as an atomic expression that encapsulates a distinct factoid in a concise,
self-contained form.

**Main methods.**
- **FActScore** (Min et al., 2023). An LLM splits generated text into atomic facts. Each fact is
  verified against a knowledge source, and the score is the supported fraction. This turned "partially
  correct" into countable units. OpenFActScore (2025) re-implements it with open models.
- **SAFE / LongFact** (Wei et al., 2024). Decompose → revise each fact to be self-contained →
  relevance check → search-augmented verification. Its *revise to self-contained* step is
  decontextualization in practice.
- **Dense X Retrieval** (Chen et al., 2023). A trained "Propositionizer" rewrites passages into
  propositions (the FactoidWiki corpus). Indexing propositions outperformed passage and sentence
  indexing under a fixed word budget.
- **Proposition segmentation.** PropSegmEnt (Chen et al., 2023) provides a 45k-proposition human
  corpus. Abstractive proposition segmentation (2024) provides scalable, open
  segmenters. The Sub-Sentence Encoder (Chen et al., 2023/NAACL 2024) embeds each proposition
  *in context*, as a separate vector.
- **Decontextualization** (Choi et al., 2021). Rewrite a sentence so it is interpretable on its own
  while preserving its meaning.
- **Claim decomposition quality.**
  - *A Closer Look at Claim Decomposition* (Wanner et al., 2024) introduces DecompScore and a
    Russell/neo-Davidsonian decomposition prompt.
  - *Molecular Facts* (Gunjal & Durrett, 2024) names the two desiderata: **decontextuality** (can
    stand alone) and **minimality** (adds as little as possible to get there).
  - *Decomposition Dilemmas* (Hu et al., 2024) finds that decomposition helps weak verifiers and can
    hurt strong ones, and catalogues the error types decomposition introduces.
  - DnDScore (2024) scores decomposition and decontextualization jointly.

**Failure modes.**
- **Over-atomization.** Fully atomic facts lose the context needed to interpret them. Gunjal & Durrett
  show "atomic" facts becoming ambiguous or unverifiable.
- **Decomposition noise.** It can drop qualifiers, invent sub-claims, or duplicate content (Hu et al.).
  Wanner et al. show that decomposition method materially changes scores.
- **Aggregation errors.** Individually true facts can combine into a false whole (*Merging Facts,
  Crafting Fallacies*, 2024).
- **Granularity drift.** The same text yields different atom counts from different models or prompts.

**Directly reusable for Memory Seed.**
- Use the **molecular** target, not the atomic one: each item must pass decontextuality and minimality.
- Use the decompose → *revise to stand alone* → verify-against-source loop, with the session record as
  the "knowledge source." The mechanical check is a verbatim grounding quote.
- The Sub-Sentence Encoder idea supports embedding a decision's claim separately from its rationale,
  while keeping both attached to one record.

### 1.2 Open information extraction (OpenIE)

**Atomic unit.** A relational tuple `(arg1, relation, arg2[, …])` extracted without a predefined
schema. TextRunner is the canonical example.

**Main methods.**
- **TextRunner** (Banko et al., 2007) founded the paradigm.
- **Stanford OpenIE** (Angeli et al., 2015) splits sentences into entailed clauses, then shortens each
  with natural logic.
- **MinIE** (Gashteovski et al., 2017) minimizes extractions and moves polarity, modality, attribution
  and quantities into **annotations** instead of the triple text.
- OpenIE6 and neural taggers followed. Since 2023, generative LLM-based IE has dominated (see the OpenIE
  survey from rule-based models to LLMs, 2024, and the generative-IE survey, 2023).

**Failure modes.**
- **Conditions and context are lost.** "We'll adopt FAISS *if* the corpus passes 50k items" becomes
  `(we, adopt, FAISS)`.
- **Attribution and modality flattening.** Without MinIE-style annotations, "JNL suspects X" becomes
  a bare `X`.
- **Relation-phrase proliferation.** Unnormalized relations yield near-duplicate predicates.
- **Reasons don't fit the triple frame.** Rationale is inter-propositional, and triples are
  intra-propositional.

**Directly reusable.**
- MinIE's move: keep the statement minimal and put **polarity, modality, attribution, and conditions
  in typed fields** (`qualifiers`), not in the text.
- A normalized `subject` field (the thing the fact is *about*: a file, component, tool, or metric)
  enables deduplication and "all facts about X."
- Triples themselves aren't worth storing. The existing Meaning Sidecar proposal already treats SRO
  propositions as an experimental upper bound only. This survey agrees.

### 1.3 Argumentation and claim mining

**Atomic unit.** An *argumentative discourse unit* (ADU) with a role (major claim, claim, premise),
plus typed relations (support/attack) between ADUs. Toulmin refines this into claim, data (grounds),
warrant, backing, qualifier and rebuttal. The Argument Interchange Format (AIF; Chesñevar et al., 2006)
represents arguments as typed graphs of information nodes and scheme nodes.

**Main methods.**
- Pipeline or joint models do segmentation → role classification → relation prediction. The survey is
  Lawrence & Reed (2019); the persuasive-essays corpus is Stab & Gurevych (2017).
- LLM-based argument mining since 2024 includes relation-based AM with LLMs (2024) and the LLMs in AM
  survey (2025). LLM detection/extraction/relation classification was studied on online comments
  (2025).

**Failure modes.**
- **Poor transfer across domains.** *Limited Generalizability in Argument Mining* (2025) finds that
  models "learn datasets, not arguments."
- **Implicit warrants.** The unstated reason linking data to claim is rarely extractable.
- **Weak performance on long, nuanced, or emotionally charged text.**
- **Relation-direction and attack/support confusion.**

**Directly reusable.**
- **Support is the missing relation.** Memory Seed has lifecycle edges (replace/extend/relate) but no
  "this decision rests on that premise." Toulmin grounds map to *fact items*. The warrant maps to the
  decision's R text, which stays inline because it's rarely separable. Qualifiers map to
  `qualifiers.condition`. Rebuttals map to rejected alternatives and "accepting that…" costs.
- **Attack** maps to fact→fact conflict (§2.6), which the curator surfaces as a candidate `replaces`
  stub.
- TRACE (Chang & Chang, 2026) independently argues for typed, versioned, append-only reasoning records
  for agent commitments, building on AIF. It's a schema proposal without released code. Cited as
  convergent evidence only.

### 1.4 Decision detection in dialogue

**Atomic unit.** A **decision region** made of decision dialogue acts (DDAs):
- *Issue* — what needs deciding.
- *Resolution*, split into *Proposal* (RP) and *Restatement* (RR).
- *Agreement*.

For action items the unit is task description, owner, agreement, and timeframe.

**Main methods.**
- On the AMI corpus: Hsueh & Moore (2007) used lexical, prosodic, DA and topical features.
  Fernández et al. (2008) showed that **modelling the DDA sub-structure hierarchically beats flat
  "decision / not decision" classification**. Frampton et al. (2009) extended this to real-time
  detection.
- Wang & Cardie (2016) summarized decisions from these regions.
- Purver et al. (2007) found the same thing for action items: detecting their sub-classes (owner,
  timeframe, agreement) beats flat detection.
- Recent work: LLM meeting recap with action items (Asthana et al., 2023), action-item detection with
  context modelling (2023), and the AutoMin 2025 minuting shared task.

**Failure modes.**
- **Proposals mistaken for decisions.** A proposal without agreement isn't a decision. This is the
  most common LLM error, and it's the "auto-capture every sentence" risk the curator proposal already
  rejects.
- **Decisions scattered over many turns.** A decision region spans many turns, and the resolution is
  often restated later with different wording.
- **Implicit agreement.** Silence or "ok, go" is agreement, and it's hard to attribute.
- **Hallucinated decisions** in LLM recaps when long transcripts are processed in one pass.

**Directly reusable.**
- **Issue / Proposal / Agreement is exactly what `decision_origins` needs.** The *agreement* utterance
  identifies who decided (user vs agent) and is the natural grounding quote. The curator should check
  that a decision has an agreement span. A proposal with no agreement becomes a `proposed` status, not
  a decision.
- The *Issue* gives the decision an IBIS question (`issue` field), which makes "what did we decide
  about X?" retrievable.
- Action items map to decisions with `status: accepted`, an owner, and a trigger. They don't need a
  third kind.

### 1.5 Design rationale and ADRs

**Atomic unit.**
- **IBIS** (Kunz & Rittel, 1970): *Issue* → *Positions* → *Arguments* (pro/con).
- **QOC** (MacLean et al., 1991): *Question* → *Options* → *Criteria* (assessments). The authors call
  QOC a condensation of an IBIS history.
- **ADR** (Nygard, 2011): Context / Decision / Status / Consequences, one record per decision, with
  supersession by later ADRs.
- **MADR** adds Decision Drivers, Considered Options, Confirmation, and deciders metadata.
- **Y-statements** (Zimmermann) fit a decision into one sentence: *in the context of … facing … we
  decided for … and neglected … to achieve … accepting that …*.
- **Kruchten (2004)** gives decisions a state machine (idea, tentative, decided, approved, rejected,
  among others) and classifies them as existence, property, or executive decisions.

**Main methods.** Mostly manual capture. LLM-generated design rationale was evaluated in 2025. So was
mining design information from issue logs, and an exploratory 2026 study asks whether LLMs can extract
architectural decisions from commits.

**Failure modes.**
- **Capture cost.** This is the classic reason design rationale gets abandoned.
- **Rationale decay.** Criteria are recorded, but the facts behind them go stale unnoticed.
- **LLM-generated rationale is plausible but unverifiable** unless it's grounded in a source.
- **Tension between one-decision-per-record and bundled records.**

**Directly reusable.**
- **The Y-statement as the canonical `claim` sentence template.** It is a decontextualized molecular
  unit that already includes the rejected alternative ("neglected") and the accepted cost ("accepting
  that").
- **The QOC Criteria are facts or drivers.** They become `rests_on` fact items, which is what makes
  staleness detectable.
- **Kruchten's status vocabulary** is a starting point for a controlled `Disposition`.
- Memory Seed's ADR ledger already *is* the IBIS "history" and its current view the QOC
  "condensation." This proposal only adds the premise layer underneath.

### 1.6 Adjacent: agent-memory systems (context for the design, not a requested area)

- **Mem0** (2025) extracts salient facts. It then chooses **ADD / UPDATE / DELETE / NOOP** against
  similar existing memories. Memory Seed can't DELETE or UPDATE in place (Invariant 2). It maps these to
  *append new*, *append + `replaces` candidate*, and *NOOP*.
- **Zep / Graphiti** (2025) uses a bi-temporal knowledge graph: each fact edge carries validity time,
  and contradicted facts are **invalidated, not deleted**. This is the closest precedent for fact
  `replaces` plus `observed_at`.
- **A-MEM** (2025) keeps Zettelkasten-style notes with keywords, tags and links, and "memory evolution"
  updates old notes. The evolution step conflicts with append-only; its linking step matches link audit.
- **ROAM** (2026) organizes atomic memories by pairwise relation: independent, equivalent, subsuming,
  or conflicting. That is a useful dedup taxonomy for the curator (§2.6). Cited at abstract level.

---

## Part 2 — Design proposal

### 2.1 Two kinds, one item envelope

Every atomic item is either a **DECISION** or a **FACT**. Both share one envelope. Documentation
records remain as they are: searchable work records with no lifecycle. They aren't items in this
model.

| Kind | What it is | Authority | Can be replaced? |
|---|---|---|---|
| DECISION | A commitment by the project, of the form "we will / won't / will defer X" | Authoritative "why" (Invariant 4) | Yes, through `supersedes`/`evolves` |
| FACT | A truth-apt statement the project relies on | Evidence, not authority | Yes, through `replaces` when a newer observation contradicts it |

**Fact types (`fact_type`):**
- `observation` — something seen in code, output, or behaviour.
- `measurement` — a number with units and a method.
- `constraint` — an external or user-imposed limit ("PyPI publish requires manual approval"; "JNL
  wants no server dependency").
- `assumption` — believed and relied on, but unverified.
- `definition` — what a term means in this project.

**Deciding fact vs decision.** Ask: *could this be wrong about the world, or is it a choice?* A user
*preference* is a `constraint` fact attributed to the user. What the project *does* about it is a
decision.

### 2.2 Minimal fields

**Every item carries:**

| Field | Meaning | Existing home | New? |
|---|---|---|---|
| `id` | Decisions: `mse_x:dN` (unchanged). Facts: proposed `mse_x:fN` | `adr_decision_identity` | Fact ref grammar is **new**, a schema change (see Q2) |
| `kind` | `decision` \| `fact` | DRAFTS heading type | Adding `fact` is **new** |
| `claim` | One decontextualized, minimal sentence (Y-statement for decisions) | The D text is close but often not stand-alone | **New**, derived |
| `scope` | Where it applies: repo, subproject, component, or path glob | `Scope:` subfield | Existing |
| `topics` | Controlled slugs | Decision-level topic sidecars | Existing |
| `provenance` | `first-hand` \| `reconstructed` (Constitution 1.6) | Declared on some records | **New** as a required item field |
| `evidence` | `{source: entry/file/command, quote: 40–120 chars}` | S/F/T labels, without the quote | Quote is **new** |
| `created_at`, `user_initials`, `agent_type` | Stamp | Entry YAML | Existing (inherited) |

**Decisions additionally carry:**

| Field | Meaning | Existing home | New? |
|---|---|---|---|
| `issue` | The IBIS question this decision answers | Heading title (implicit) | **New**, optional |
| `rationale` | The warrant, kept inline | `R` | Existing |
| `rejected` | `[{option, reason}]` | `A` (free text) | Structure is **new** |
| `status` | Controlled: `proposed \| accepted \| implemented \| deferred \| rejected` | `Disposition:` (free text) | Controlled vocabulary is **new** |
| `decided_by` | `user \| agent`, plus the agreement quote | `decision_origins` | Quote is **new** |
| `rests_on` | Refs to fact items (and optionally decisions) this depends on | ADR events' `supporting_decisions` field (precedent) | **New** |
| `accepting` | Accepted costs and consequences (Y-statement "accepting that") | ADR "Impact"; often in R | **New**, optional |
| `revisit_when` | A trigger condition, required for `deferred` | Usually buried in Follow-up | **New** |
| `supersedes` / `evolves` | Lifecycle | Entry YAML + link sidecars; inverses computed | Existing, unchanged |

**Facts additionally carry:**

| Field | Meaning |
|---|---|
| `fact_type` | One of the five types above |
| `subject` | Normalized thing it's about (path, component, tool, metric). Used for dedup and "facts about X". |
| `qualifiers` | `{condition, polarity, modality, attribution}` (MinIE-style; keeps `claim` minimal) |
| `observed_at` | When it was true or measured. Separate from the write time, bi-temporal in the Zep sense. |
| `volatility` | `stable` (definitions, most constraints) \| `drifts` (measurements, versions) \| `point-in-time` |
| `method` | For measurements: the command or procedure, so the fact can be re-run |

**Supersession is not stored on the item.** `superseded_by` and `replaced_by` stay computed at read
time from forward edges, as they are today. That keeps the append-only guarantee.

### 2.3 Atomicity for decisions

A bare atom ("use numpy brute force") is useless without its reason. The research consensus
(*Molecular Facts*; FActScore's own ambiguity problems) points to this definition:

> **A decision item is one chosen option, for one issue, in one scope, together with the reasons that
> are specific to that choice.**

Three tests the curator applies:

1. **Independent-revisability test (split rule).** If one part of the D text could be reversed while
   another part stands, they're two decisions. Example: "defer FAISS *and* embed claim text only"
   splits into two decisions.
2. **Premise-extraction test (factor-out rule).** A reason clause that is itself truth-apt and could
   become false independently becomes a fact item. The decision cites it in `rests_on`, and the R text
   keeps its wording. Example: "brute force is ~ms at 1.6k items" is a measurement fact. "Simpler to
   operate" stays in R, because it's a judgment about the choice.
3. **Agreement test (existence rule).** Following the DDA work, a candidate without an agreement
   span, or one written only as a proposal, gets `status: proposed`. It isn't counted as a decision.

**Rejected alternatives stay inline** on the chosen decision (`rejected`). They aren't separate
decision items, because a rejection is part of *this* choice's rationale (QOC Options). There's one
exception: a rejection whose reason is a reusable fact ("FAISS wheels are unavailable for platform Y")
factors that reason out as a fact.

This keeps the accepted `adr_retrieval_entry_granularity` concern ("separating a decision from its
rationale loses too much context") intact. Rationale never leaves the decision. Only its independently
falsifiable premises gain their own identity.

### 2.4 Where items live (Markdown stays the authority)

Proposal. The option in Q1 needs a decision.

- **Decisions:** the DRAFTS record in the session entry stays the single authority. The item
  envelope for a decision (`claim`, `issue`, structured `rejected`, `rests_on`, `revisit_when`) is
  written into an **items sidecar**. The sidecar enriches the record; it doesn't hold a second copy.
- **Facts:** authoritative in the items sidecar. That is a narrowly scoped Markdown sidecar, which
  Invariant 6 permits.
- **Path:** `.memory-seed/sessions/items/YYYY-MM/YYYY-MM-DD.md`, one block per source entry.
- **Keying:** `(entry_id, heading timestamp)`, the same as link and diagram sidecars. A correction is
  an appended block that supersedes the earlier one. Nothing is edited in place.
- **Validation:** `links check` and a *proposed* `items check` would enforce chronology, ref existence, topic vocabulary,
  quote grounding, and id collision on every write surface (Invariant 2's write-surface parity rule, added in v1.3).

Sketch:

````markdown
## 2026-09-24 15:10 - Defer FAISS; embed decision claims

```yaml
entry_id: mse_example0000001
provenance: first-hand          # written at the curator gate, before merge
items:
  - id: mse_example0000001:d1
    kind: decision
    claim: "Memory Seed defers adopting FAISS and keeps brute-force model2vec cosine until the item index exceeds 50,000 vectors."
    ...
  - id: mse_example0000001:f1
    kind: fact
    ...
```
````

### 2.5 Links

| From → To | Mechanism | Status |
|---|---|---|
| decision → decision | `supersedes` / `evolves` / `related` (unchanged) | Existing |
| fact → fact | `replaces` when newer contradicts older; `related` otherwise | Same edge kinds, **applied to a new node type** (Q3) |
| decision → fact | `rests_on` **field** on the decision's item block | **New field**, not a new edge kind |
| item → topic | Decision-level topic sidecar. Facts inherit the source decision's topics, and those are amendable. | Existing mechanism |
| item → ADR | ADR events already cite `supporting_decisions`. An ADR's head decision inherits its `rests_on` facts. | Derived |

**Why a field and not an edge.** The Constitution governs edge kinds (`constitution:v1#edge-kinds`).
The ADR ledger already records "rests on" as the `supporting_decisions` **field**. A field
- is authored at write time by the same writer as the decision,
- is validated for ref existence, and
- is readable by the graph as a derived, advisory relation.

It never participates in lifecycle-head computation. That respects the lesson that machine edges
never move heads. Promoting it to a first-class edge kind is an open question (Q4).

**Staleness propagation (the payoff).** When fact `f` is replaced, every decision whose `rests_on`
includes `f` gets derived metadata `premise_changed: [f → f′]`. So does every ADR whose head rests on
such a decision.
- ESR lists these as *advisory* reviews.
- Nothing is rewritten, and no status changes automatically.
- A human (or the orchestrator) decides whether to `evolve`, `supersede`, or record "reviewed, still
  holds."

### 2.6 Curator extraction at the gate

**Inputs (stated assumption).** The brief says the curator "works only from logged decisions." The
orchestration proposal's packet also includes "source conversation evidence." This report assumes the
curator receives
- the logged DRAFTS records for the gate, **plus**
- the orchestrator's **harvest packet**: bounded, quoted transcript excerpts selected by the
  orchestrator, which has the full conversation.

It never gets the raw conversation. Retrospective recovery measured at ≤6% Medium-or-better, so facts
that aren't in the record or the packet should be treated as lost. They shouldn't be reconstructed.
If only logged records are allowed, fact yield will be limited to what R/A/T/S happen to state (Q6).

**Pipeline.**

1. **Segment.** Split each record's D/R/A/T/S text into candidate units.
2. **Decisions.** Run the three atomicity tests (§2.3).
   - Propose *splits* as a receipt item for the orchestrator. The curator never rewrites a record.
   - Write the Y-statement `claim`, the `issue`, and structured `rejected`.
   - Check the agreement quote against `decision_origins`.
3. **Facts.** From R/A/T/S and the packet, extract truth-apt premises.
   - Decontextualize with minimality: resolve "it", "this", and "the index", but add nothing else.
   - Classify `fact_type`, `volatility`, `subject`, and `qualifiers`.
4. **Ground.** Every item needs a verbatim quote of 40–120 characters from a named source.
   - Quotes are checked **mechanically** (substring match).
   - An item whose quote fails is dropped. It is never "fixed" by the model.
5. **Deduplicate and relate** against existing facts about the same `subject`.
   - The candidates come from a **closed list** supplied by retrieval. The curator never recalls ids
     on its own, because workers invent identifiers.
   - Relations use the ROAM taxonomy, mapped to append-only operations as Mem0-style ops:
     - *equivalent* → NOOP (cite the existing fact).
     - *subsumes* → new fact + `related`.
     - *conflicting* → new fact + **`classify_pending` stub** proposing `replaces`.
     - *independent* → ADD.
6. **Link.** Add `rests_on` refs, chosen only from items in this gate or the closed candidate list.
   Supersede/evolve candidates between decisions become `classify_pending` stubs for human
   classification, as today.
7. **Stabilize structure-changing labels.** Run steps 2 (split), 5 (conflict), and 6 twice,
   independently, and keep only the intersection. In a 2026-08-09 two-run classification of 405
   lifecycle edges (project working notes, not in the repo corpus), the runs agreed 81% overall, but
   nearly half of one run's `refines` calls were the other run's `builds-on`. Single-run structural
   labels aren't trustworthy.
8. **Receipt.** Return items, dropped candidates with reasons, proposed splits, stubs, and
   `premise_changed` impacts. Use the orchestration proposal's receipt format. The orchestrator
   accepts, pushes back, or escalates to JNL.

**Example extraction prompt** (vendor-neutral; the curator runs it for each gate):

```text
ROLE: Memory Seed Decision Curator — item extraction pass.

You receive:
  RECORDS: the DRAFTS records logged at this gate (entry_id, dN, D, R, A, F, T, S, Scope,
           Disposition, decision_origins).
  PACKET:  quoted excerpts selected by the orchestrator, each with a source label.
  CANDIDATES: a closed list of existing items (id, kind, subject, claim) you may link to.
              You MUST NOT reference any id that is not in RECORDS or CANDIDATES.

Produce items of two kinds.

DECISION = a commitment by the project (we will / will not / will defer X).
  - One chosen option, one issue, one scope. If part of a D text could be reversed while another
    part stands, do NOT split it yourself: emit a SPLIT_PROPOSAL naming the parts.
  - claim: one self-contained sentence, Y-statement form where natural:
    "In the context of <scope>, facing <issue>, we decided <option> [and rejected <alt>]
     to achieve <goal>, accepting <cost>."
  - status: proposed | accepted | implemented | deferred | rejected. Use "proposed" if you cannot
    quote an agreement. "deferred" requires revisit_when.
  - decided_by: user | agent, with the agreement quote. Never upgrade agent to user.
  - rationale stays with the decision. Factor out a reason ONLY if it is a truth-apt statement
    that could become false on its own; make it a FACT and list it in rests_on.

FACT = a truth-apt statement the project relies on.
  - fact_type: observation | measurement | constraint | assumption | definition.
  - claim: minimal and stand-alone. Resolve pronouns and "this/the index"; add nothing else.
    Put conditions, negation, hedging and attribution in qualifiers, not in claim.
  - measurement facts need value, unit, method and observed_at. Unknown -> omit the fact.
  - volatility: stable | drifts | point-in-time.

For EVERY item: evidence.quote = a verbatim substring (40-120 chars) of RECORDS or PACKET, and
evidence.source = its label. If you cannot quote it, do not emit it.

Against CANDIDATES, label each new fact: equivalent | subsumes | conflicting | independent
(with the candidate id). "conflicting" produces a replaces STUB, never a live edge.

Do not invent decisions from discussion that lacks agreement. Do not restate the same fact twice.
Output YAML: items[], split_proposals[], stubs[], dropped[] (with reason). No prose.
```

### 2.7 Retrieval implications

Built on the current pipeline, with no new decay (the `RECENCY_FLOOR` comment already assigns
"prefer the current form" to the lifecycle graph).

**What gets embedded (model2vec):**

| Item | Vector text | Lexical (BM25F) fields |
|---|---|---|
| Decision | `claim` + `scope` | claim (high), issue (high), rationale (mid), rejected options (low), accepting (low) |
| Fact | `claim` + `subject` | claim (high), subject (high), qualifiers (low) |

- Rejected options stay **out of the decision vector**. Otherwise "should we use FAISS?" pulls a
  decision *against* FAISS as a paraphrase match. They stay in a low-weight lexical field so "why not
  FAISS?" still hits.
- Model2Vec averages token vectors, so shorter, single-proposition text should dilute less. Dense X
  gains were measured with trained dense retrievers, not static embeddings, so this is a hypothesis to
  measure (Q8). It isn't a promise.

**Granularity and rollup.** Items form an *additional derived index*, not a replacement for anything.
- A **fact hit rolls up** to the decisions whose `rests_on` cite it. The decision is the result, and
  the fact is its highlight. This is the same pattern as section→entry rollup.
- Fact-seeking queries can request `granularity="fact"` directly.

This extends the accepted `adr_retrieval_entry_granularity` (which is already served at decision
granularity by default). If adopted, it's a revision candidate for that ADR, to go through the normal
ADR review. This report doesn't decide it.

**Temporal scoring and superseded items:**
- Replaced facts get the same `REPLACED_RANK_DAMPING` (0.10) and successor boost as replaced
  decisions. They are down-ranked, never hidden (Invariant 7). `exclude_replaced` stays opt-in.
- **No age decay on facts.** A `drifts`/`point-in-time` fact shows `observed_at` and a "re-verify"
  label, exposing the information before using it to rank (`constitution:v1#expose-before-rank`).
  Changing rank by fact age waits for a paired measurement, like every other ranking constant here.
- A decision with `premise_changed` is **flagged, not demoted**, until measured. The replaced premise
  is shown next to the decision.
- `deferred` decisions with a `revisit_when` are surfaced whenever a fact about the trigger's
  `subject` is written. This is a derived check, not a ranking change.

**Volume and FAISS.** Items multiply index rows by an estimated 3–5×: about 1,640 decisions becomes
roughly 5–8k vectors. That's still well inside the brute-force regime the repo measured (whole-corpus
cosine is "instant" at this scale). So this proposal alone doesn't justify FAISS. It does make vector
count, rather than entry count, the thing to watch.

### 2.8 Worked example (illustrative; numbers taken from repo measurements)

**Transcript (brainstorm, abridged):**

> **JNL:** If we split decisions into atomic items, the index grows. Do we need FAISS now?
> **Claude:** Current scale: about 1,640 canonical decisions. Link audit embedded 637 entries in
> 0.17 s once model2vec was loaded, and the similarity matrix was instant. Even at 5× rows, brute-force
> numpy cosine stays in milliseconds. The cost we actually pay is the cold model load, measured at
> 6.7 s.
> **JNL:** And FAISS on Windows?
> **Claude:** It adds a native wheel dependency. model2vec is currently the package's only dependency,
> which is deliberate.
> **JNL:** Then no FAISS. Revisit if the item index gets past, say, 50k vectors.
> **Claude:** Agreed. Separately, for the vectors: should we embed the whole record or just the claim?
> **JNL:** What do you think?
> **Claude:** Just the claim plus scope. If rejected alternatives are in the vector, a query about
> FAISS matches the decision that *rejected* FAISS as if it endorsed it.
> **JNL:** Makes sense, do that. Keep the rationale searchable, though.
> **Claude:** Also, I think Dense X gains may not transfer to static embeddings. Unmeasured.

**Logged DRAFTS record (what the orchestrator writes):**

```markdown
#### D1 - Decision: Defer FAISS for the item index
- D: Keep brute-force model2vec cosine; do not adopt FAISS. Revisit above ~50k vectors.
  - Scope: Memory Seed local retrieval.
  - Disposition: Deferred.
- R: At ~1,640 decisions (≈5–8k items) brute-force cosine is milliseconds; FAISS adds a native
  dependency while model2vec is the only one.
- A: FAISS now — rejected: no measured need, adds platform-specific wheels.

#### D2 - Decision: Embed decision claims, not whole records
- D: Vectors embed claim + scope; rationale is lexical-only; rejected options are excluded from vectors.
  - Scope: Item index embedding text.
  - Disposition: Accepted.
- R: Rejected alternatives in the vector make "use FAISS?" match the decision rejecting FAISS.
```

**What dropped out at logging:**
- The 0.17 s/637-entry and 6.7 s cold-load measurements. D1's R compresses them to "milliseconds."
- Who proposed D2. The agent proposed it and JNL agreed, so `decision_origins.d2` should be `user`
  (JNL's instruction), with the agent's proposal as context.
- The unverified Dense X hypothesis. It's an *assumption* and not a decision, so it should become a
  fact item, not vanish.
- The implicit agreement "Makes sense, do that."

**Curator items (receipt excerpt):**

```yaml
items:
  - id: mse_example0000001:d1
    kind: decision
    issue: "Should Memory Seed adopt FAISS for the atomic item index?"
    claim: "In the context of Memory Seed local retrieval, facing index growth from atomic items, we decided to keep brute-force model2vec cosine and rejected FAISS, to avoid a native dependency, accepting a revisit above ~50,000 vectors."
    status: deferred
    decided_by: {origin: user, quote: "Then no FAISS. Revisit if the item index gets past, say, 50k vectors."}
    rejected: [{option: "Adopt FAISS now", reason: "no measured need; adds a native wheel dependency"}]
    rests_on: [mse_example0000001:f1, mse_example0000001:f2, mse_example0000001:f3]
    revisit_when: {subject: "item-index vector count", condition: "> 50000"}
    topics: [retrieval]
    provenance: first-hand
    evidence: {source: "packet#3", quote: "Then no FAISS. Revisit if the item index gets past, say, 50k vectors."}

  - id: mse_example0000001:d2
    kind: decision
    issue: "What text should item vectors embed?"
    claim: "Memory Seed item vectors embed only the item claim and scope; decision rationale is indexed lexically and rejected alternatives are excluded from vectors."
    status: accepted
    decided_by: {origin: user, quote: "Makes sense, do that. Keep the rationale searchable, though."}
    rests_on: [mse_example0000001:f5]
    provenance: first-hand
    evidence: {source: "entry:D2.D", quote: "Vectors embed claim + scope; rationale is lexical-only; rejected options are excluded"}

  - id: mse_example0000001:f1
    kind: fact
    fact_type: measurement
    subject: "link-audit embedding"
    claim: "Embedding 637 Memory Seed entries with a loaded model2vec model took 0.17 seconds."
    observed_at: 2026-07-22
    volatility: drifts
    method: "link audit semantic ranking over full corpus"
    evidence: {source: "docs/3_Spec/lifecycle-edge-linking-sidecars.md", quote: "embedding all 637 entries takes 0.17 s once the model is loaded"}

  - id: mse_example0000001:f2
    kind: fact
    fact_type: measurement
    subject: "model2vec cold load"
    claim: "Loading the model2vec model cold took 6.7 seconds on a Windows development machine."
    observed_at: 2026-07-26
    volatility: drifts
    method: "first link audit with semantic ranking enabled, cold process"
    evidence: {source: "docs/3_Spec/lifecycle-edge-linking-sidecars.md", quote: "measured 6.7 s cold on a Windows dev box"}

  - id: mse_example0000001:f3
    kind: fact
    fact_type: constraint
    subject: "memory_seed package dependencies"
    claim: "model2vec is the memory_seed package's only runtime dependency."
    volatility: stable
    evidence: {source: "memory_seed/adr.py:449", quote: "`model2vec` is the package's only dependency"}

  - id: mse_example0000001:f4
    kind: fact
    fact_type: assumption
    subject: "proposition retrieval gains"
    claim: "Proposition-level retrieval gains reported by Dense X may not transfer to static model2vec embeddings."
    qualifiers: {modality: hypothesis, attribution: agent}
    volatility: point-in-time
    evidence: {source: "packet#5", quote: "I think Dense X gains may not transfer to static embeddings. Unmeasured."}

  - id: mse_example0000001:f5
    kind: fact
    fact_type: assumption
    subject: "embedding rejected alternatives"
    claim: "Including a decision's rejected alternatives in its vector makes queries about an alternative match the decision that rejected it."
    qualifiers: {modality: predicted, attribution: agent}
    volatility: stable
    evidence: {source: "entry:D2.R", quote: "Rejected alternatives in the vector make \"use FAISS?\" match the decision rejecting FAISS"}

split_proposals: []          # D1 and D2 were already logged separately
stubs: []                    # no existing FAISS decision in CANDIDATES
dropped:
  - text: "Even at 5x rows, brute-force numpy cosine stays in milliseconds"
    reason: "projection, not a measurement; no method or observed_at — kept only inside d1 rationale"
```

**Later payoff.** Suppose a future session measures cold load at 1.2 s, and the fact is written as
`f2′` with a `replaces` stub against `f2`. Once that stub is classified, D1 shows
`premise_changed: [f2 → f2′]` in retrieval and ESR. Nothing about D1 is rewritten. Someone decides
whether D1 still holds.

---

## Constitution fit

- **Five-question test.**
  - *Capture:* premises and the agreement quote are captured at the gate instead of being lost.
  - *Retrieval:* short claims are indexed, and fact→decision rollup is added.
  - *Trust:* every item is grounded, and staleness is visible.
  - *Validation:* the grounding quote and the ref checks are mechanical.
- **Invariant 2 (append-only).** Items are appended to sidecar blocks. Corrections supersede. Records
  are never rewritten. Splits are *proposals* to the orchestrator.
- **Invariant 3 (explainable).** Every item has a source and a quote. `decided_by` has an agreement
  quote.
- **Invariant 4 (files = now, memory = why).** Facts about code describe the code at `observed_at`.
  They record why a decision was made, not what the code is now. `volatility` makes that visible.
- **Invariant 4, provenance clarification (added in v1.6).** `provenance` is required and declared, never inferred.
- **Invariant 6 (Markdown authority).** Items live in a scoped Markdown sidecar. Vectors are derived.
- **Invariant 7 (never hide).** Damping only; `exclude_replaced` stays opt-in.
- **Principles.**
  - *Expose-before-rank:* `premise_changed` and fact age are metadata first.
  - *Integrate-don't-duplicate:* decisions keep one authority.
  - *Prove automation small:* the proposal should be piloted on one gate before becoming the default.

---

## Open questions for JNL

1. **Where do facts live?** (a) A new items sidecar (recommended above, reconstructed or gate-time).
   (b) A new `#### Fn - Fact:` DRAFTS record kind in the entry itself, written first-hand by the
   orchestrator. (c) Both: first-hand facts in the entry, curator-derived facts in the sidecar.
2. **Fact identity grammar.** Accept `mse_x:fN` as a second ref form? It's a schema change touching
   `adr_decision_identity`, `temporal_lineage.py` (which hard-codes `:dN`), and every ref validator.
   The alternative is to number facts inside the `dN` space with a `kind` field.
3. **Edge kinds on facts.** May `replaces`/`related` apply to fact nodes under the current edge-kinds
   ADR, or does that need a revision?
4. **`rests_on`: field or edge?** A field (recommended) keeps the Constitution's edge set closed. A
   first-class edge would render in Trail and participate in chains, but needs an ADR and possibly a
   Constitution amendment.
5. **Controlled `Disposition` vocabulary.** Adopt `proposed | accepted | implemented | deferred |
   rejected` (Kruchten-derived), and make `revisit_when` mandatory for `deferred`?
6. **Curator input boundary.** Logged records only, or logged records plus the orchestrator's quoted
   harvest packet? The first is safer. The second is the only way to capture premises that the record
   compressed away (see §2.8, "what dropped out").
7. **Scope of the first pilot.** New gates only, or also a reconstructed backfill of facts from
   existing R/T text? Backfilled facts would be `provenance: reconstructed`, and earlier topic
   reconstruction scored only about 0.6 macro-recall.
8. **Measurement before adoption.** Run a paired retrieval eval (claim-only vs record vectors, with
   and without fact rollup) on the existing paraphrase set before any default changes? This could fold
   into the Meaning Sidecar ablation in `semantic-compression-benchmark-proposal.md` as its variant F.
9. **ADR revision.** If adopted, raise a revision candidate for `adr_retrieval_entry_granularity`
   (item index as an additional rollup level), and decide whether the Y-statement `claim` also feeds
   ADR current views.

---

## References

**Atomic facts / propositions / decomposition**
- Min et al., 2023. *FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation.* EMNLP. https://arxiv.org/abs/2305.14251 · https://aclanthology.org/2023.emnlp-main.741/
- *OpenFActScore: Open-Source Atomic Evaluation of Factuality in Text Generation*, 2025. https://arxiv.org/pdf/2507.05965
- Wei et al., 2024. *Long-form factuality in large language models* (SAFE, LongFact). https://arxiv.org/abs/2403.18802v4
- Chen et al., 2023. *Dense X Retrieval: What Retrieval Granularity Should We Use?* https://arxiv.org/abs/2312.06648
- Chen et al., 2023. *PropSegmEnt: A Large-Scale Corpus for Proposition-Level Segmentation and Entailment Recognition.* Findings of ACL. https://aclanthology.org/2023.findings-acl.565/ · dataset https://huggingface.co/datasets/sihaochen/propsegment
- 2024. *Scalable and Domain-General Abstractive Proposition Segmentation.* https://arxiv.org/pdf/2406.19803
- Chen et al., 2023/2024. *Sub-Sentence Encoder: Contrastive Learning of Propositional Semantic Representations.* NAACL. https://arxiv.org/abs/2311.04335 · https://aclanthology.org/2024.naacl-long.89/
- Choi et al., 2021. *Decontextualization: Making Sentences Stand-Alone.* TACL. https://aclanthology.org/2021.tacl-1.27/ · https://arxiv.org/abs/2102.05169
- Wanner et al., 2024. *A Closer Look at Claim Decomposition.* https://arxiv.org/abs/2403.11903
- Gunjal & Durrett, 2024. *Molecular Facts: Desiderata for Decontextualization in LLM Fact Verification.* Findings of EMNLP. https://arxiv.org/abs/2406.20079 · https://aclanthology.org/2024.findings-emnlp.215/
- Hu, Long & Wang, 2024. *Decomposition Dilemmas: Does Claim Decomposition Boost or Burden Fact-Checking Performance?* https://arxiv.org/abs/2411.02400
- *DnDScore: Decontextualization and Decomposition for Factuality Verification in Long-Form Text Generation*, 2024. https://arxiv.org/html/2412.13175v1
- *Merging Facts, Crafting Fallacies: Evaluating the Contradictory Nature of Aggregated Factual Claims in Long-Form Generations*, 2024. https://arxiv.org/pdf/2402.05629
- *Optimizing Decomposition for Optimal Claim Verification*, ACL 2025. https://arxiv.org/pdf/2503.15354

**Open information extraction**
- Banko et al., 2007. *Open Information Extraction from the Web.* IJCAI. https://my.eng.utah.edu/~cs6961/papers/banko-ijca07.pdf · TextRunner demo https://aclanthology.org/N07-4013/
- Angeli, Premkumar & Manning, 2015. *Leveraging Linguistic Structure For Open Domain Information Extraction.* ACL. https://nlp.stanford.edu/pubs/2015angeli-openie.pdf
- Gashteovski, Gemulla & del Corro, 2017. *MinIE: Minimizing Facts in Open Information Extraction.* EMNLP. https://aclanthology.org/D17-1278/
- *A Survey on Open Information Extraction from Rule-based Model to Large Language Model.* Findings of EMNLP 2024. https://arxiv.org/abs/2208.08690
- *Large Language Models for Generative Information Extraction: A Survey.* https://arxiv.org/abs/2312.17617

**Argumentation / claim mining**
- Lawrence & Reed, 2019. *Argument Mining: A Survey.* Computational Linguistics 45(4). https://aclanthology.org/J19-4006/
- Stab & Gurevych, 2017. *Parsing Argumentation Structures in Persuasive Essays.* Computational Linguistics 43(3). https://aclanthology.org/J17-3005/ · https://arxiv.org/abs/1604.07370
- *Can Large Language Models perform Relation-based Argument Mining?*, 2024. https://arxiv.org/pdf/2402.11243
- *Large Language Models in Argument Mining: A Survey*, 2025. https://arxiv.org/html/2506.16383v1
- *LLMs for Argument Mining: Detection, Extraction, and Relationship Classification of pre-defined Arguments in Online Comments*, 2025. https://arxiv.org/abs/2505.22956
- *Limited Generalizability in Argument Mining: State-Of-The-Art Models Learn Datasets, Not Arguments*, 2025. https://arxiv.org/pdf/2505.22137
- Toulmin model overview (claim, data, warrant, backing, qualifier, rebuttal). https://www.sjsu.edu/writingcenter/docs/handouts/Toulmin%20Model%20of%20Argumentative%20Writing.pdf
- Chesñevar et al., 2006. *Towards an Argument Interchange Format.* Knowledge Engineering Review 21(4). https://dl.acm.org/doi/10.1017/S0269888906001044
- Chang & Chang, 2026. *TRACE: An Operational Reasoning Schema for Auditable Agentic Commitments* (discusses AIF, Chesñevar et al. 2006). https://arxiv.org/abs/2607.12480

**Decision detection in dialogue**
- Hsueh & Moore, 2007. *Automatic Decision Detection in Meeting Speech.* MLMI. https://link.springer.com/chapter/10.1007/978-3-540-78155-4_15
- Fernández, Frampton, Ehlen, Purver & Peters, 2008. *Modelling and Detecting Decisions in Multi-party Dialogue.* SIGdial. https://aclanthology.org/W08-0125.pdf
- Frampton et al., 2009. *Real-time decision detection in multi-party dialogue.* https://www.researchgate.net/publication/221013172_Real-time_decision_detection_in_multi-party_dialogue · *Extracting Decisions from Multi-Party Dialogue…* https://aclanthology.org/W09-3934.pdf
- Wang & Cardie. *Summarizing Decisions in Spoken Meetings.* https://arxiv.org/pdf/1606.07965
- Purver et al., 2007. *Detecting and Summarizing Action Items in Multi-Party Dialogue.* SIGdial. https://www.pure.ed.ac.uk/ws/files/14860467/Detecting_Action_Items_in_Meetings.pdf
- Carletta et al. *The AMI Meeting Corpus.* https://www.semanticscholar.org/paper/The-AMI-Meeting-Corpus:-A-Pre-announcement-Carletta-Ashby/e4e0fd56309e28b28bb47c9a72ad6111c76bb8b9
- Asthana et al., 2023. *Summaries, Highlights, and Action items: Design, implementation and evaluation of an LLM-powered meeting recap system.* https://arxiv.org/abs/2307.15793
- *Meeting Action Item Detection with Regularized Context Modeling*, 2023. https://arxiv.org/abs/2303.16763
- *Findings of the Third Automatic Minuting (AutoMin) Challenge*, 2025. https://arxiv.org/pdf/2509.13814

**Design rationale / ADRs**
- Kunz & Rittel, 1970. *Issues as Elements of Information Systems* (IBIS). http://magrawal.myweb.usf.edu/phd/articles/ibis_wp_70.pdf
- MacLean, Young, Bellotti & Moran, 1991. *Questions, Options, and Criteria: Elements of Design Space Analysis.* HCI 6(3–4). https://www.tandfonline.com/doi/abs/10.1080/07370024.1991.9667168
- Nygard, 2011. *Documenting Architecture Decisions.* https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- MADR. https://adr.github.io/madr/ · primer https://www.ozimmer.ch/practices/2022/11/22/MADRTemplatePrimer.html
- Zimmermann. *Y-Statements.* https://medium.com/olzzio/y-statements-10eb07b5a177
- Kruchten, 2004. *An Ontology of Architectural Design Decisions in Software-Intensive Systems.* https://philippe.kruchten.com/wp-content/uploads/2009/07/kruchten-2004-design-decisions.pdf
- *Using LLMs in Generating Design Rationale for Software Architecture Decisions*, 2025 (TOSEM). https://arxiv.org/abs/2504.20781
- *A Novel Approach for Automated Design Information Mining from Issue Logs*, 2024. https://arxiv.org/pdf/2405.19623
- *Can LLMs Extract Architectural Design Decisions from Source Code Commits? — A Preliminary Exploratory Study*, 2026. https://arxiv.org/pdf/2609.03721

**Agent memory (adjacent)**
- 2025. *Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory.* https://arxiv.org/abs/2504.19413 · code https://github.com/mem0ai/mem0
- 2025. *Zep: A Temporal Knowledge Graph Architecture for Agent Memory* (Graphiti). https://arxiv.org/abs/2501.13956
- 2025. *A-MEM: Agentic Memory for LLM Agents.* https://arxiv.org/abs/2502.12110 · code https://github.com/agiresearch/a-mem
- Zheng et al., 2026. *ROAM: Robust Organization of Atomic Memories for Agents through Semantic Relations.* https://arxiv.org/abs/2609.09778

**Repository sources**
- `docs/CONSTITUTION.md` (Invariants 2, 3, 4, 6, 7; §3 principles; §9 five-question test)
- `.memory-seed/decisions/adr_decision_identity.md`, `adr_draft_format.md`, `adr_edge_kinds.md`, `adr_retrieval_entry_granularity.md`
- `docs/3_Spec/lifecycle-edge-linking-sidecars.md`
- `docs/1_Inbox/decision-curator-orchestration-proposal.md`, `docs/1_Inbox/semantic-compression-benchmark-proposal.md`
- `memory_seed/retrieval.py` (`search_memory` defaults), `memory_seed/semantic_cache.py` (`RECENCY_FLOOR`, `REPLACED_RANK_DAMPING`)
- `experiments/decision-chat-alignment/REPORT.md`
