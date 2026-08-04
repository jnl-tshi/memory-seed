---
title: "Architecture Decision Record Standards Report"
date: "2026-08-01"
project: "memory-seed"
kind: "report"
next_action: "source-only"
author_context: "Prepared for Jean Nathan Tshibuyi (JNL). Report 5 of a seven-report research programme."
---

# Architecture Decision Record Standards Report

**Report 5 of 7.** Researches ADR conventions in depth and recommends how Memory Seed should align —
**as extensions to the contracts that already exist, not as a parallel scheme.**

**Headline: Memory Seed already solves two problems the ADR ecosystem has openly failed to solve —
validated relationship integrity, and amending a decision without superseding it. It is behind on three
things the conventions do better: evaluation criteria, a status vocabulary, and a published location.
None of the gaps requires inventing anything new.**

> **Amendment, 2026-08-03 — §8.1 is done. This report's central premise is now stale.**
>
> This report was written while the ADR lifecycle sidecar contract was marked *DRAFT — NOT IMPLEMENTED*,
> and it recommended building it as specified. **It shipped the same day** (`codex/feature/adr-sidecar`,
> merged at `0fed577`). The contract moved from `3_Spec/draft/` into the live spec lane, its predecessor
> went to `3_Spec/deprecated/`, and three ADRs now exist in `.memory-seed/decisions/`.
>
> What shipped, verified against the CLI and a live sidecar: `adr promote | revise | transition | show |
> list | check`; frontmatter carrying `adr_id`, `topics`, `created_at`, `user_initials`, `agent_type` and
> **`source: write-time`**; an authority pointer at decision granularity (`mse_…:d1`); and a **derived**
> current view rendered between markers rather than an authored status field — exactly the
> replay-don't-store rule §8.1 argued for, and the thing the replaced 2026-07-16 proposal got wrong.
>
> `revise` — *"append a proposed revision without changing authority"* — is the amend-without-superseding
> path §4 identified as absent from every canonical convention. It is now built.
>
> **What this does not change:** the three recommended additions in §8.3 (evaluation criteria, accepted
> downside, and — now partly satisfied — status), the arguments against new edge kinds and review cycles in
> §9, and the caution in §10 that alignment with a convention is not evidence the convention works. Report 4
> still applies: ADR adoption has never been correlated with any downstream outcome, and shipping a
> promotion layer does not change that.

---

## Inputs

| Input | Role |
|---|---|
| [Report 1](standards-and-regulatory-landscape-report.md) §5.13 | Nygard / MADR / 42010 field-by-field spine comparison |
| [Report 2](decision-governance-evidence-spine-report.md) | Verified capture surface and the six confirmed absences |
| [Report 3](memory-seed-strategic-fit-report.md) | Competitive finding: no ADR tool validates anything |
| **`3_Spec/adr-lifecycle-sidecar-contract.md`** | **The implemented living ADR contract (promoted 2026-08-03)** |
| [`3_Spec/graph-edge-contract.md`](../../docs/3_Spec/graph-edge-contract.md) | The four edge kinds, forward-only and acyclic |
| **`7_Replaced/memory-seed-typed-entries-adr-sidecar-proposal.md`** | **Why the earlier shape was replaced — the most important input** |
| `2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md` | The active successor |
| New research, 2026-08-01 | JPH catalogue, Y-statements, TOGAF/ArchiMate/42010, naming, folders, status vocabularies, review cycles, relationship ontologies, linting |

### What this report does not establish

- **No implementation plan.** It recommends contract extensions; sequencing is Report 7's job.
- **No claim that ADRs improve outcomes.** Report 4 established that this has never been measured.
- **No new sidecar family.** Three exist; this report proposes no fourth.

---

## 1. Executive summary

**1. There is no ADR standard — there is a catalogue and two dominant templates.** Joel Parker
Henderson's repository (**16,568 stars, actively maintained, migrated to its own GitHub org**) is the de
facto reference *catalogue*, offering **13 template variants** from Nygard's minimal five fields to
NHS Wales' sign-off variant `[primary]`. It is more referenced than any single tool or template, and it
is explicitly not normative. The only genuinely authoritative document is **ISO/IEC/IEEE 42010:2022**,
and it does something narrower than people assume — see finding 4.

**2. Memory Seed already has what the ecosystem admits it lacks.** Two confirmed gaps in *every*
canonical convention:

- **No convention has a mechanism to amend a decision without superseding it.** Practitioners patch it
  with an informal "Amended by" status that appears in no template. **Memory Seed's `evolves` edge is
  exactly this mechanism** — a typed freshness edge meaning "extends and refines while the original stays
  valid" — and it is validated, forward-only, and acyclic.
- **No convention prescribes a review cycle or review date.** This is deliberate silence flowing from
  "immutable once accepted," not an oversight.

**3. Nobody validates relationship integrity, and Memory Seed does.** Report 3 confirmed no ADR tool
checks that a superseding reference resolves or that supersession is acyclic. Memory Seed's `links check`
does both, per edge kind, independently.

**4. But the academic lineage is far ahead of Memory Seed on relationship *semantics*.** Kruchten et al.
(2006) proposed `enables`, `subsumes`, `conflicts with`. Zimmermann et al. (2009) built a UML metamodel of
ADIssue / ADAlternative / ADOutcome. **Szlenk (2018) gave it formal semantics** — `compatibleWith`,
`incompatibleWith`, `forcedBy`, `triggeredBy` — with model consistency defined and verified in Alloy
`[primary, arXiv:1807.02798]`. Memory Seed has four edge kinds and none of them expresses conflict or
dependency. That is a real gap, and §7 argues against closing most of it.

**5. Three things Memory Seed should adopt, all cheap.** MADR's **`Decision Drivers`** (evaluation
criteria — independently required by CMMI DAR and absent per Report 2); a **status vocabulary** via the
draft contract's transition replay; and a decision on **where published ADRs live**, since the ecosystem
has converged on `NNNN-title.md` naming but *not* on a folder.

**6. Enterprise architecture frameworks are a dead end here.** **TOGAF has no ADR artefact** — an
Architecture Board and a governance log of meeting minutes, with decision rationale expected to live
inside other deliverables. **ArchiMate has no Decision element** — its Motivation layer models Stakeholder,
Driver, Assessment, Goal, Outcome, Principle, Requirement, Constraint, which are decision *inputs*, not
the decision. People bolt ADRs onto TOGAF informally. There is nothing to align with.

---

## 2. The convention landscape — who actually publishes what

| Source | Nature | Authority | Maintenance |
|---|---|---|---|
| **Nygard (2011)** | ~800-word blog article | Origin of the practice; no governing body | Static |
| **MADR 4.0.0** | Template + markdownlint config | The dominant *structured* template | Active — pushed 2026-07-13, 2,362★ `[primary]` |
| **Joel Parker Henderson repo** | Catalogue of 13 template variants | Most-referenced collection; explicitly non-normative | Active — pushed 2026-07-12, 16,568★ `[primary]` |
| **Y-statements (Zimmermann)** | One-sentence grammar | Peer-reviewed origin (IEEE Software 2013) | Author-maintained writing |
| **AWS / Azure guidance** | Vendor prescriptive guidance | Authoritative for their platforms only | Active |
| **ISO/IEC/IEEE 42010:2022** | International standard | **The only formal standard** | Current 2nd edition |
| **adr-tools** | Bash CLI | De facto tooling default | 5,585★, last push 2024-04-25 — **stale** `[primary]` |
| **TOGAF / ArchiMate** | EA frameworks | **No decision artefact at all** | Active but irrelevant here |

**The structural point:** the most-used artefacts have no authority, and the only authoritative artefact
has no template. That is why the ecosystem has 13 competing variants and no validator.

### Y-statements — worth knowing, not worth adopting wholesale

The six-clause grammar `[primary, Zimmermann]`:

> *In the context of **[use case]**, facing **[concern]**, we decided for **[option]** and neglected
> **[alternatives]**, to achieve **[qualities]**, accepting **[downside]**, because **[rationale]**.*

Origin: SATURN 2012, published in Zdun, Capilla, Tran & Zimmermann, *"Sustainable Architectural Design
Decisions,"* IEEE Software 30(6), 2013. Zimmermann credits a sponsor demanding decisions fit *on one
slide including rationale* — the length constraint shaped the form.

What it adds over Nygard: it **forces explicit enumeration of rejected alternatives and accepted
trade-offs** in a single scannable unit. Nygard's free-text Context/Decision/Consequences does not.

Its relevance to Memory Seed is diagnostic rather than prescriptive: DRAFT's `D:` + `R:` + `A:` already
carries decision, rationale, and alternatives. What the Y-statement has that DRAFT lacks is the
**"accepting [downside]"** clause — an explicitly recorded accepted cost. That is a genuine and cheap
addition, discussed in §8.

Zimmermann's later work also motivated MADR's rebrand from *Markdown **Architectural** Decision Records*
to *Markdown (for) **Any** Decision Records* at 3.0.0 — the scope widened deliberately beyond
architecture. His stated discipline: **~20–30 architecturally significant decisions per project**, not
exhaustive documentation. That number is a useful sanity check against Memory Seed's 876 addressable
decisions and the project's own conclusion that most are tactical.

---

## 3. Required metadata — field-by-field

Consolidating Report 1's spine comparison with the new research, against Memory Seed's DRAFT labels:

| Concept | Nygard | MADR 4.0.0 | 42010:2022 | Memory Seed |
|---|---|---|---|---|
| The decision | `Decision` | `Decision Outcome` | AD (conceptual) | **`D:` — mandatory, enforced** |
| Rationale | `Context` | `Context and Problem Statement` | **Architecture Rationale — first-class** | **`R:` — mandatory, enforced** |
| Alternatives | — | `Considered Options`, `Pros and Cons` | Alternatives-not-chosen in rationale | **`A:` — optional** |
| **Evaluation criteria** | — | **`Decision Drivers`** | Basis for decision | **absent** |
| Validation | — | **`Confirmation`** (renamed from "Validation" in 4.0) | — | **`T:` — optional** |
| Affected entities | `Consequences` (prose) | `Consequences` | **Traceable to AD Elements** | `F:` — file paths only |
| Accepted downside | in `Consequences` | in `Consequences` | in rationale | **absent as a distinct field** |
| Decision-maker | — | `decision-makers` | — | `user_initials` (session, not decider) |
| Consulted / informed | — | `consulted`, `informed` | — | absent |
| Date | — | `date` | — | **machine-stamped, enforced** |
| Status | `Status` | `status` | — | **absent (draft only)** |
| Supersession link | Status text | `superseded by` | — | **`replaces` — typed, validated** |
| **Amend without supersede** | **absent** | **absent** | **absent** | **`evolves` — typed, validated** |

> **Amendment, 2026-08-03 — a failure mode the literature does not name.** See the
> [field evidence log](field-evidence-log.md). Asked what problems ADRs had actually caused, a practitioner
> answered: *"making the AI not willing to go with your product decision because it doesn't understand the
> ADR."*
>
> **The record becomes over-authoritative and blocks a legitimate new decision.** Every source in §4 treats
> staleness as a record falling *behind* reality. This is the opposite failure: a record that is obeyed when
> it should have been superseded. Neither Nygard, MADR, adr-tools, nor the academic lineage names it.
>
> It sharpens why `evolves` and `replaces` matter — an amendment path is not only for the author's
> convenience, it is what stops a superseded decision from being enforced against its successor. It also
> argues for surfacing supersession state *at retrieval time*, not merely storing it: an agent that reads a
> decision without seeing it has been replaced will apply it.

**Two observations.**

**MADR's `Confirmation` is functionally Memory Seed's `T:`.** MADR 4.0.0 renamed "Validation" to
`Confirmation`; both ask how the decision was verified. This is convergence, not coincidence — and it
means Memory Seed's DRAFT grammar is closer to MADR than to Nygard.

**`Decision Drivers` is the standout absence.** MADR has it. CMMI's DAR practice area independently
requires *recorded evaluation criteria* against which alternatives were judged. Report 2 confirmed
Memory Seed has no such field — `A:` records alternatives with prose reasons, not the criteria. **Two
unrelated traditions asking for the same missing field is the strongest signal in this report.**

---

## 4. Lifecycle — status, supersession, updates

### Status vocabularies

| Source | Values |
|---|---|
| Nygard | proposed · accepted · deprecated · superseded |
| MADR | proposed · **rejected** · accepted · deprecated · superseded by |
| adr-tools | accepted / superseded (adds a `supersede` CLI verb, no new states) |

**"Rejected" is the divergence point.** Nygard's lineage absorbed rejected options into narrative;
MADR made rejection a terminal state. The common core is
**proposed → accepted | rejected → deprecated | superseded**.

Memory Seed's draft contract proposes `proposed → accepted/rejected` and `accepted → superseded`, which
matches the common core exactly. **No change needed — the design already agrees with the ecosystem.**

### Supersession

Universal convention, and the one thing everybody agrees on: a change of decision produces a **new
record**, the old one's status flips, and the two are linked bidirectionally. AWS: *"When the team accepts
an ADR, it becomes immutable."* Azure: *"an append-only log."*

Memory Seed's `replaces` edge implements this **and adds what no convention has**: forward-only and
acyclic validation, computed inverses that are never written to disk, and an append-only `retracts:`
correction path.

### The gap nobody has filled — amendment

**Confirmed across Nygard, MADR, and adr-tools: no canonical convention has a mechanism to amend an
accepted decision without superseding it.** Practitioner guidance invents an "Amended / Amended by"
status that appears in no template `[secondary]`.

The informal consensus is that accepted ADRs are **immutable for substance, editable for typos and
link-rot** — which is exactly the ambiguity a validated system should not rely on.

**Memory Seed's `evolves` edge is this missing mechanism**, and it is more precisely defined than the
patch the ecosystem reaches for: *"this decision extends or refines that one, which remains valid but is
incomplete alone,"* forward-only, acyclic, and — critically — **never dampening the target's importance
score**, because evolution is freshness, not retirement.

This is the report's strongest finding. Memory Seed did not copy this from the ADR world; it does not
exist there.

### Review cycles — deliberate silence

**No canonical convention prescribes a review date or cadence.** Not Nygard, not MADR, not adr-tools.
The one recommendation found (quarterly for external, annual for internal, with an explicit
"revisit if X exceeds Y" trigger) is a practitioner blog explicitly self-labelled as the author's own
synthesis `[secondary]`.

This silence is a *consequence* of immutability: if a decision is superseded rather than revised, there
is nothing to review on a schedule. **Recommendation: do not add a review-date field.** Report 1 found
that only regulated frameworks demand review (HIPAA §164.316(b)(2)(iii), ISO 27001 clause 9.3), and those
review the *management system*, not individual decisions. Adding one would import governance ceremony the
conventions deliberately avoid.

### Decision ownership — near-total silence

Nygard: no ownership field. MADR: `decision-makers`, `consulted`, `informed` — RACI-derived, the only
template-level mechanism in the ecosystem. Beyond that, **who owns an ADR after acceptance is
unaddressed by every canonical source.**

Given Report 3's conclusion — approval should be a *reference* to an existing record, not a workflow —
and Report 4's finding that external approvals correlate negatively with delivery performance,
**recommendation: do not adopt `decision-makers`/`consulted`/`informed` as authored fields.**

---

## 5. Relationships — where the academy is ahead

Beyond supersession, three research lineages define richer decision-to-decision relations:

| Source | Relations |
|---|---|
| **Kruchten, Lago & van Vliet (2006)** | `enables`, `subsumes`, `conflicts with` — informally defined |
| **Zimmermann et al. (2009)**, JSS 82(8) | UML metamodel: ADIssue / ADAlternative / ADOutcome, with dependency relations and integrity constraints |
| **Szlenk (2018)**, arXiv:1807.02798 | **Formal semantics**: `compatibleWith` (symmetric, reflexive, not transitive), `incompatibleWith`, `forcedBy`, `triggeredBy`; defines model **consistency** and verifies it in Alloy `[primary]` |

Memory Seed's four edge kinds — `related_entries`, `replaces`, `evolves`, `continuity` — express
relatedness, retirement, refinement, and artifact lineage. **None expresses conflict, dependency, or
enablement.**

**Recommendation: do not adopt these, with one narrow exception.** The reasoning:

- **Szlenk's formalism solves a design-space problem, not a memory problem.** Its purpose is generating
  and validating *consistent configurations* — 22 valid designs for a robotics platform via a model
  checker. That is architecture-configuration tooling, not decision history.
- **Every edge kind added is a validation surface, a UI surface, and an authoring burden.** The
  graph-edge contract's own standing rule is *"one name, one meaning"*; four kinds already require
  independent per-kind validation.
- **42010 — the only actual standard — does not define decision-to-decision relations at all.** It
  relates a decision to *concerns* and to *AD Elements* it affects. The formal ontologies are research,
  not convention, and no shipped tool implements them.

**The narrow exception worth considering: `conflicts with`.** Report 3's Evidence Pack already computes
a `contradictions[]` array by detecting mixed and reciprocal lifecycle edges. A conflict relation would
make *authored* contradiction expressible rather than only *derived*. This is the one relation with a
governance use — "these two decisions cannot both hold" is exactly what an auditor or an agent needs to
know. Defer it, but note it is the only one with a case.

---

## 6. Naming, folders, templates

**Naming: genuine convergence.** `NNNN-title-in-kebab-case.md` with zero-padded, monotonically
increasing, never-reused numbers is used by adr-tools, MADR, and the JPH catalogue alike. Dates-as-filename
and pure slugs are minority patterns no major template mandates.

**Folders: genuine divergence.**

| Location | Used by |
|---|---|
| `doc/adr/` | adr-tools default (legacy, largest install base) |
| `docs/adr/` | community-common |
| `docs/decisions/` | **MADR 4.0.0's new default** |

The trend is toward `docs/decisions/` as tooling catches up to MADR 4, but `docs/adr/` remains most seen
in the wild. **There is no single standard location** — which matters for §8's recommendation about
whether Memory Seed should publish ADRs at a conventional path at all.

**Templates: 13 variants, differentiated by audience not field list** — Nygard (minimal), Tyree & Akerman
(enterprise, adds assumptions/justification), arc42 (embedded in a documentation framework), Alexandrian
(context/forces/solution), Business Case (cost, SWOT, sponsors), MADR (structured), Planguage (QA-focused),
Y-statements (one sentence), NHS Wales (public-sector sign-off), ITDs (executive-facing).

**The lesson for Memory Seed is not to pick one.** It is that the ecosystem fragmented because different
audiences need different *presentations* of the same underlying facts. Memory Seed stores structured
facts; rendering them into any of these templates is a projection problem, not a schema problem.

---

> **Amendment, 2026-08-04 — the field says the trigger matters more than the format (E7).** A
> 45K-view thread asking practitioners what actually made them stop writing ADRs produced a
> challenge this report did not consider: three responders independently argued that decisions
> belong in **executable checks**, not records. The sharpest version — half of one practitioner's
> ADRs were read once at write time, and the half that got read again were read *because a test
> failed and pointed back at them*. Another: the only thing that kept a team honest was making the
> build go red, explicitly because an agent will not follow a requirement it never loaded.
>
> **This report optimised the wrong variable.** Sections 3–6 refine what a record contains and how
> it is named, versioned and superseded. Nobody in the field reported the format as their reason for
> quitting. They reported that nothing ever surfaced the record again. A validated schema constrains
> what gets *written*; it does nothing about what gets *read*.
>
> **The gap in the counter-position** is that a test encodes what is forbidden, never why, and
> cannot carry a rejected alternative — which is the exact failure the r/ClaudeAI thread describes
> (an agent re-proposing an approach abandoned in June). The synthesis nobody in the field stated:
> **tests are an excellent trigger and a poor record.** The product implication is to surface the
> relevant decision when an execution artefact fails or is touched, using the file references and
> typed edges the schema already carries — not to refine the schema further.
>
> **One new failure mode to design against**, also unreported until now: a practitioner found an ADR
> made the agent refuse a *new* product decision, because it did not understand the existing record.
> A validated, agent-loaded, enforced store makes a stale record harder to override, not easier.
> Retrieval must surface current status prominently, and agents must treat records as evidence
> rather than instruction. Worth an explicit test.

## 7. Automation — the state of validation

| Tool | What it does | Status |
|---|---|---|
| **MADR's own markdownlint config** | Format linting, shipped `.markdownlint` + GitHub Actions workflow | Active, the de facto baseline |
| **mdbook-lint ADR rules** | ADR001–ADR007+, validates Nygard *and* MADR 4.0 formats, incl. status-vocabulary checking | Active `[secondary]` |
| **structured-madr** (zircote) | **YAML frontmatter, risk assessment, audit trails, GitHub Action validator, JSON Schema, three conformance levels** | Created 2026-01-15, pushed 2026-07-27, **10 stars** `[primary]` |
| **adr-tools** | Creation and supersession CLI — **no validation at all** | 5,585★, last push 2024-04-25 |

**`structured-madr` is the closest thing to a competitor Memory Seed has in this space** — it is
attempting schema validation, audit trails, and CI enforcement over ADRs. It is seven months old with ten
stars. That simultaneously confirms the need is real enough for someone else to attempt it and that
nobody has established a position.

**Still true after this research: no tool validates the decision *graph*** — that a superseding reference
resolves, that supersession is acyclic, that an amendment chain is coherent. Linting validates *a file*.
Memory Seed validates *the relationships between files*. That distinction is the defensible one.

---

## 8. Recommendations for Memory Seed

Each is framed as an extension to an existing contract. **None proposes a new sidecar family or a
parallel scheme.**

### 8.1 How to store ADRs

**Implementation outcome (2026-08-03): the ADR contract is now live.** The shipped model keeps the
report's essential recommendation—one append-only Markdown file per architectural concern at
`.memory-seed/decisions/<adr_id>.md`, stable identity frontmatter, and status derived by replay rather
than authored state—while replacing the pointer-only draft with a living revision ledger and a
regenerable current view.

**The reason this shape is right is recorded in the repo's own history.** The predecessor proposed
mutable machine-maintained YAML with an authored `current_status` and a "do not edit manually" banner.
It was replaced on 2026-07-16 precisely because a mutable status field is a second source of truth that
can drift, which Invariant #2 forbids. **Do not reopen that.**

**Do not adopt a mandatory entry `type` field.** The replaced proposal wanted one; it did not survive,
and Report 2 confirms no `type` exists today. `(entry_id, dN)` plus the living ADR sidecar already
distinguishes governing decisions from tactical ones without classifying every entry up front.

### 8.2 How to reference ADRs

**No change.** `(entry_id, dN)` is already the identity, grammar v2 already mandates decision-level refs
when either end has multiple decisions, and the live contract resolves ADR → source decision by
that pair. The ecosystem's `NNNN-title.md` convention is a *filename* scheme, not an identity scheme, and
adopting it would add a second identifier for the same thing.

### 8.3 How to extend ADRs — three additions, ranked

| # | Addition | Justification | Cost |
|---|---|---|---|
| 1 | **Evaluation criteria** — an optional DRAFT sub-label under `A:`, or a `Decision Drivers` field on the ADR sidecar | MADR has it; **CMMI DAR independently requires it**; Report 2 confirmed it absent. Two unrelated traditions demanding the same field | Low — grammar addition |
| 2 | **Status via transition replay** | The live contract implements it; matches the ecosystem's common core exactly | Shipped 2026-08-03 |
| 3 | **Accepted downside** — the Y-statement's *"accepting [downside]"* clause | Records the cost knowingly taken. `A:` records what was rejected; nothing records what was accepted *despite* | Low — grammar addition |

**Do not add:** review dates (no convention has them, and Report 1 shows only management-system standards
require review); `decision-makers`/`consulted`/`informed` (Report 3 demoted approval to a reference);
`conflicts with` and the Szlenk relation family (design-space tooling, not memory).

### 8.4 How to support decision updates

**`evolves` already is the amendment mechanism the ADR ecosystem lacks — say so, and document it as
such.** This is currently framed internally as a freshness edge for session entries. Framed externally,
it answers a named, acknowledged gap in every canonical ADR convention.

Concretely: a correction that does not change the decision is an **appended block that supersedes**
(the Constitution v1.5 route, already established for diagram sidecars); a refinement that extends a
still-valid decision is an **`evolves` edge**; a change of decision is a **`replaces` edge**. Three
distinct cases, three distinct mechanisms, all already built. **No convention distinguishes all three.**

### 8.5 How to support evidence packets

The Evidence Pack is deterministic, fingerprinted, and already computes `contradictions[]` and
`missing_evidence[]`. Two extensions, both from Report 4's priorities:

- **An export path.** `EvidencePack = dict[str, Any]` with no serialiser is the gap; the hard part is done.
- **ADR-scoped packs.** Once promotion exists, a pack scoped to *governing decisions in a topic area*
  rather than a time window is the artefact that answers "show me the architecture decisions and their
  evidence."

### 8.6 How to support AI retrieval

**The promotion layer is the unlock, and it is a retrieval feature before it is a governance feature.**
Zimmermann's ~20–30 significant decisions per project versus Memory Seed's 876 addressable decisions is
the whole problem: an agent retrieving over undifferentiated decisions gets tactical noise.

`memory_search` already accepts a `topics` filter. Adding an ADR-status filter — *governing decisions in
this area* — is the highest-value retrieval improvement available, and it needs the promotion layer, not
new retrieval machinery.

### 8.7 How to support graph relationships

**No new edge kinds.** The four are sufficient, they are independently validated, and the graph-edge
contract's "one name, one meaning" rule is a real constraint. The academic ontologies are richer but
unimplemented anywhere and aimed at a different problem.

The one thing worth surfacing: **the derived `contradictions[]` in the Evidence Pack is already a
conflict signal.** Expose it in Trace before considering an authored conflict edge.

### 8.8 How to support audit trails

Report 2's conclusion stands and is not softened here: **an evidence pack over a corpus with no
governing-decision marking is a work log, not an audit trail.** The ordering is therefore fixed —
promotion first, export second, audit claims third. Any audit-trail work before promotion exists is
building on a foundation that does not hold.

---

## 9. What Memory Seed should not do

1. **Do not invent a proprietary standard.** The brief allowed it if justified; it is not. Every gap
   identified is closable within the existing contracts.
2. **Do not adopt a template.** The ecosystem has 13 because different audiences need different
   presentations. Memory Seed stores facts; templates are a rendering concern.
3. **Do not chase `NNNN-title.md` naming or a `docs/decisions/` folder** unless publishing externally.
   The ecosystem has not converged on a folder, and Memory Seed's identity scheme is stronger than a
   filename.
4. **Do not add review cycles.** Deliberate silence across every convention.
5. **Do not build the Szlenk relation family.** Configuration tooling, not decision memory.
6. **Do not reopen mutable status.** The repo already tried and replaced it.
7. **Do not claim ADR conventions validate the product.** Report 4: ADR adoption has been measured across
   921 repositories and never correlated with any downstream outcome. Alignment with a convention is not
   evidence that the convention works.

---

## 10. Limitations

1. **TOGAF's primary text was inaccessible** — the Open Group moved chapter content behind SSO. The
   "no ADR artefact" finding rests on secondary characterisation, though it is consistent across sources.
2. **ISO/IEC/IEEE 42010:2022 was not read directly** — `iso-architecture.org` refused connection and the
   standard is paywalled. Its rationale and relationship model are search-synthesised.
3. **The ECSA 2024 ADR action-research study's quantitative findings could not be extracted** — the PDF
   failed to parse. Only its scope is confirmed.
4. **Zachman was not verified** this session.
5. **`structured-madr` was assessed from its repository metadata**, not by use. Ten stars at seven months
   old is thin evidence either way.
6. **This report recommends alignment with conventions whose effectiveness is unmeasured.** Report 4's
   finding applies to its own recommendations: aligning with MADR is a compatibility argument, not an
   evidence-based one.

---

*End of Report 5. Report 6 — Ideal Customer Profile — must confront the demand question this programme
has deferred four times.*
