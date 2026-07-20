---
title: Inbox current-capability crosswalk — ontology, evidence, and relevance proposal sets
status: inbox-crosswalk
date: 2026-07-20
promotion: not applicable
sources:
  - INBOX-ASSESSMENT.md
  - ../7_Superseded/memory-seed-ontology-evidence-set-index-exploration.md
  - ../7_Superseded/memory-seed-ontology-exploration.md
  - ../7_Superseded/evidence-model-and-packets-exploration.md
  - ../7_Superseded/decision-supersession-and-evolution-exploration.md
  - ../7_Superseded/deterministic-context-assembly-exploration.md
  - ../7_Superseded/benchmarking-decision-quality-exploration.md
  - ../7_Superseded/constitutional-principles-decision-efficiency-exploration.md
  - ../7_Superseded/memory-seed-relevance-set-index-exploration.md
  - ../7_Superseded/constitutional-principles-deterministic-agents-exploration.md
  - ../7_Superseded/sidecar-lens-architecture-exploration.md
  - ../7_Superseded/deterministic-sidecar-generation-exploration.md
  - ../7_Superseded/entry-intent-metadata-exploration.md
  - ../7_Superseded/high-signal-knowledge-lenses-exploration.md
  - ../7_Superseded/integrated-implementation-sequence-exploration.md
  - ../CONSTITUTION.md
  - ../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md
  - ../2_Todo/memory-provenance-and-authority-taxonomy-proposal.md
  - ../2_Todo/memory-quality-metrics-v0-proposal.md
  - ../3_Spec/graph-edge-contract.md
  - ../3_Spec/lifecycle-edge-linking-sidecars.md
  - ../3_Spec/draft/adr-lifecycle-sidecar-contract.md
  - ../3_Spec/memory-trace-derived-artifact-provenance-contract.md
  - ../4_Reference/memory-quality-v0-baseline.md
---

# Inbox capability crosswalk

## Purpose

This is step 1 of the corrected pre-triage sequence in
[INBOX-ASSESSMENT.md](INBOX-ASSESSMENT.md): a current-capability crosswalk of both inbox proposal sets
against the active semantic-record plan, the graph-edge contract, the provenance and authority taxonomy,
the Evidence Pack, the topic vocabulary, and the existing sidecar contracts. Each claimed capability is
scored against what the owner documents and the shipped code actually do, not against the proposals'
own characterisation of the status quo.

**Disposition, 2026-07-20.** Both sets have now been retired to `7_Superseded/` — de-numbered, renamed
`-exploration`, each pointing back here. This document is the surviving record of what they claimed and
what already covered it; it is more accurate than the sources were, since they systematically understate
shipped capability. Nothing was promoted, and nothing was deleted. The ten deltas below were adversarially
re-verified before the retirement (see the verification note at the end of Findings); their surviving
residues are recorded in the owner plans named in each row.

## Reading the tables

Proposal codes:

| Code | Document |
|---|---|
| A0 | [memory-seed-ontology-evidence-set-index-exploration.md](../7_Superseded/memory-seed-ontology-evidence-set-index-exploration.md) |
| A1 | [memory-seed-ontology-exploration.md](../7_Superseded/memory-seed-ontology-exploration.md) |
| A2 | [evidence-model-and-packets-exploration.md](../7_Superseded/evidence-model-and-packets-exploration.md) |
| A3 | [decision-supersession-and-evolution-exploration.md](../7_Superseded/decision-supersession-and-evolution-exploration.md) |
| A4 | [deterministic-context-assembly-exploration.md](../7_Superseded/deterministic-context-assembly-exploration.md) |
| A5 | [benchmarking-decision-quality-exploration.md](../7_Superseded/benchmarking-decision-quality-exploration.md) |
| A6 | [constitutional-principles-decision-efficiency-exploration.md](../7_Superseded/constitutional-principles-decision-efficiency-exploration.md) |
| B0 | [memory-seed-relevance-set-index-exploration.md](../7_Superseded/memory-seed-relevance-set-index-exploration.md) |
| B1 | [constitutional-principles-deterministic-agents-exploration.md](../7_Superseded/constitutional-principles-deterministic-agents-exploration.md) |
| B2 | [sidecar-lens-architecture-exploration.md](../7_Superseded/sidecar-lens-architecture-exploration.md) |
| B3 | [deterministic-sidecar-generation-exploration.md](../7_Superseded/deterministic-sidecar-generation-exploration.md) |
| B4 | [entry-intent-metadata-exploration.md](../7_Superseded/entry-intent-metadata-exploration.md) |
| B5 | [high-signal-knowledge-lenses-exploration.md](../7_Superseded/high-signal-knowledge-lenses-exploration.md) |
| B6 | [integrated-implementation-sequence-exploration.md](../7_Superseded/integrated-implementation-sequence-exploration.md) |

`Delta` values:

- **none** — fully covered by shipped code or a live normative contract.
- **narrow** — mostly covered; one specific named gap. Includes capabilities an owner document already
  claims but has not yet implemented (the gap is implementation, not ownership), and capabilities an
  owner document explicitly declines by non-goal (the gap is a stated conflict, not an opening).
- **genuine** — materially uncovered by shipped code, unclaimed by any owner document, and not declined
  by an owner non-goal.

Owner shorthand used in the tables:

- **Semantic-record plan** — [memory-seed-semantic-record-and-signal-foundation-plan.md](../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md)
- **Edge contract** — [graph-edge-contract.md](../3_Spec/graph-edge-contract.md)
- **Link sidecars** — [lifecycle-edge-linking-sidecars.md](../3_Spec/lifecycle-edge-linking-sidecars.md)
- **ADR contract (draft)** — [adr-lifecycle-sidecar-contract.md](../3_Spec/draft/adr-lifecycle-sidecar-contract.md)
- **Provenance taxonomy** — [memory-provenance-and-authority-taxonomy-proposal.md](../2_Todo/memory-provenance-and-authority-taxonomy-proposal.md)
- **Quality metrics v0** — [memory-quality-metrics-v0-proposal.md](../2_Todo/memory-quality-metrics-v0-proposal.md)
- **Derived-artifact provenance contract** — [memory-trace-derived-artifact-provenance-contract.md](../3_Spec/memory-trace-derived-artifact-provenance-contract.md)
- **Constitution** — [CONSTITUTION.md](../CONSTITUTION.md), v1.3, ratified 2026-07-19

Code references are given as inline paths (`memory_seed/core.py`, `memory-trace/memory_trace/evidence.py`)
rather than links, since they sit outside the `docs/` tree.

## Crosswalk — ontology and evidence set

| Proposal | Claimed capability | Already exists as | Owner document | Delta |
|---|---|---|---|---|
| A0 | Crosswalk of every proposed entity/edge/writer against an existing owner | This document | INBOX-ASSESSMENT.md step 1 | none |
| A1 | `Claim` entity — proposition requiring evidence | "Material claims with evidence references and freshness metadata" defined for derived artefacts; `generated_claim_citation_coverage` metric already specified | Derived-artifact provenance contract; Quality metrics v0 metric 3 | narrow — the contract scopes claims to derived artefacts; no claim identity inside an authored entry |
| A1 | `BenchmarkTask` entity — repeatable evaluation task with an ID | Named query cases in a `ranking-ab` run, consumed as a metric population | Quality metrics v0 metric 5 | narrow — `ranking-ab` cases test retrieval ordering, not decision quality; no task-type vocabulary |
| A1 | `Actor` entity — human/agent/team/system participant | `user_initials`, `user`, `agent_type`, `agent_name` on every entry; participant/role policy named as the gate on actionability | Edge contract; Provenance taxonomy axis 4 | narrow — identity is recorded, role is not; the role model is the taxonomy's own named blocker |
| A1 | New edge types `updates`, `depends_on`, `derived_from`, `authored_by`, `affected_by`, `evaluated_by` | Four never-merged edge kinds (`related_entries`, `supersedes`, `evolves`, `commits`) plus `branch`/`continuity` labels | Edge contract; Semantic-record plan | narrow — declined: the plan's non-goals state "No new graph edge kinds" |
| A1 | Decision-level identity (`dec-0042-01`) distinct from entry ID | `source_decision: d1` frontmatter and a legacy stable decision key with heading path and text fingerprint | ADR contract (draft); Semantic-record plan phase 1 | narrow — the contract is DRAFT and unimplemented; no code path resolves a sub-entry anchor |
| A1 | Formal action verbs `promote`, `supersede`, `update`, `attach_evidence` | Shared core operations `promote_decision`, `transition_adr`, `supersede_adr` specified in phase 2 | Semantic-record plan phase 2 | narrow — specified, not built; `validate_topics` ships as `memory-seed topics check` |
| A1 | `decisions:` block with embedded `relationships:` inside entry YAML | Decision identity and lifecycle assigned to an append-only sidecar so historical entries are never edited | ADR contract (draft); Constitution invariant #2 | narrow — declined: authority for decision identity is the sidecar, not entry YAML |
| A2 | Evidence as a first-class structured record | Entry- and section-granular `entries[]`/`chunks[]` with per-item fingerprints in the Evidence Pack builder (`memory-trace/memory_trace/evidence.py`) | Derived-artifact provenance contract | narrow — evidence is addressed at entry/chunk granularity; no typed evidence record with target, validity, or method |
| A2 | Evidence roles `supports`, `contradicts`, `qualifies`, `context` | Derived `contradictions[]` (mixed and reciprocal lifecycle-edge detection) in the Evidence Pack | Derived-artifact provenance contract | narrow — contradiction is derived, never authored; no `supports`/`qualifies` vocabulary exists |
| A2 | Deterministic evidence packet with provenance and fingerprint | `build_timeline_evidence_pack` — `schema_version`, `selection_fingerprint`, `pack_fingerprint`, corpus SHA-256 per tracked document, git revision and dirty state, byte-exact snapshot test | Shipped Phase 1 (`memory-trace/memory_trace/evidence.py`) | none |
| A2 | Missing-evidence and contradiction reporting inside the packet | `missing_evidence[]` and `contradictions[]`, plus a `constraints` block instructing consumers not to infer unseen state | Shipped Phase 1 | none |
| A2 | Command returning an evidence packet for a decision ID | The builder exists but is reachable only by importing the Python function | Semantic-record plan (identity); Phase 2 of the AI timeline summarisation plan (surface) | narrow — the packet is not wired to CLI, MCP, or HTTP, and its addressing is entry-level |
| A2 | Embedded `## Evidence` section (EV-01 blocks) in an ADR | DRAFT `F:` files and `T:` tests lines per decision; transition blocks reference rationale and evidence entries | Constitution §4 DRAFT policy; ADR contract (draft) | narrow — evidence is referenced in prose lines, not addressable blocks |
| A2 | Six-tier deterministic evidence selection policy | Neighbourhood selection by `graph_entry_id`, `graph_depth`, `edge_types` | Shipped Phase 1 | narrow — selection is uniform neighbourhood expansion; there is no tiered priority order |
| A2 | Validation of evidence IDs, targets, roles, and locators | `links check` validates ref existence, forward-only order, acyclicity, duplicate IDs, authored inverse fields | Edge contract validation authority | narrow — validation covers entry refs; no evidence-record schema exists to validate |
| A3 | Typed supersession and evolution edges | `supersedes` and `evolves` as independent typed kinds, forward-only and acyclic per kind, authored in YAML or append-only link sidecars, union-merged at read time | Edge contract; Link sidecars | none |
| A3 | Six-type evolution vocabulary (`updates`, `extends`, `reaffirms`, `reverts`, `clarifies`) | Two typed lifecycle kinds with a stated semantic line: supersession retires, evolution refreshes | Edge contract; Semantic-record plan | narrow — declined: "No new graph edge kinds" is an explicit plan non-goal |
| A3 | Decision-level supersession identity | ADR sidecar identity with `source_decision`; the entry-level collateral is on the record in `mse_mkxdvaxvw99dz4s0`, which names the still-live siblings it dampens | ADR contract (draft); Semantic-record plan phase 1 | narrow — the owner claims this and phase 1 promotes a multi-decision entry, but the contract is unimplemented |
| A3 | Partial supersession with a `scope` field and residual validity | Per-decision ADR identity addresses the same collateral by promoting each decision separately | Semantic-record plan phase 1 | narrow — the owner solves the problem by identity, not by scoped edges; field-level scope is uncovered and unmotivated by the plan |
| A3 | Generated `resolved_status` / active-decision index | Computed `superseded_by`, `evolved_by`, `superseding_head`, `evolved_head`; the plan requires `current_status` to be computed, never authored | Edge contract; Semantic-record plan acceptance criteria | none |
| A3 | Ten supersession invariants (existence, direction, acyclicity, no history rewrite) | `dangling-supersedes`, `dangling-evolves`, `self-supersedes`, `supersedes-postdates`, `supersedes-cycle`, `authored-inverse-field` and the `evolves` equivalents | Edge contract validation authority | narrow — the structural invariants ship; "reason and evidence required on supersession" is unenforced |
| A3 | Decision trail artifact and `trace_decision` rendering | `memory-seed link show`, MCP `memory_link_show`, and the Trace Trail rendering persistent replaces/evolves lines | Edge contract read surfaces; Link sidecars | narrow — the trail is entry-level; no decision-level trail exists |
| A3 | Impact propagation — a reviewable report of what a decision change affects | `link audit` flags structurally adjacent entries with no edge; `docs check` flags lifecycle-pointer and lane contradictions | — | genuine |
| A4 | Deterministic, repeatable context selection | `selection_fingerprint` and `pack_fingerprint` over sorted, stable-ordered selection, with a determinism test and a byte-exact fixture | Shipped Phase 1 | none |
| A4 | Packet manifest recording inclusions, omissions, and reasons | `selection` (filters, matched and returned counts), `provenance` (builder, corpus fingerprints, source revision, freshness), `missing_evidence[]` with reasons | Shipped Phase 1 | none |
| A4 | Versioned task-typed assembly policy (`policy.id`, limits, ordering) | Caller-supplied filters and depth on the pack builder | — | narrow — no task-typed policy layer sits over the builder; the deterministic foundation it would sit on already ships |
| A4 | Relevance labels `required`, `supporting`, `background`, `candidate` | Ranked ordering with lexical, semantic, recency, supersession-damping, and successor-boost signals | Edge contract ranking rules | narrow — items are ordered and scored, never labelled by necessity |
| A4 | Vendor-independent context units instead of token counts | `matched_entry_count`, `returned_entry_count`, section chunk counts | Shipped Phase 1 | narrow — the pack reports counts, not a declared context-unit measure |
| A4 | Determinism metrics (selection and ordering repeatability, evidence recall) | Determinism asserted by test, not reported; `ranking-ab` reports directional improvement plus unaffected controls | Quality metrics v0; Edge contract "Expose before you rank" | narrow — determinism is a test property, not a measured metric; recall needs the A5 gold set |
| A4 | Three initial task policies (`explain-decision`, `explain-supersession`, `identify-active-constraint`) | — | — | narrow — same gap as the policy layer above; these are its first instances, not a separate capability |
| A5 | Gold-set benchmark of decision quality under constrained context | Corpus-health metrics (unlinked rate, DRAFT reason coverage, citation and provenance coverage, ranking regression rate) | Quality metrics v0; [baseline](../4_Reference/memory-quality-v0-baseline.md) | genuine |
| A5 | Comparative retrieval baselines (whole-document, top-k, structural, hybrid, oracle) | `ranking-ab` compares signal-off against signal-on for one named signal over the real corpus | Quality metrics v0 metric 5; Edge contract | narrow — the harness compares signal states, not retrieval strategies |
| A5 | Ablation of individual features to isolate value | `memory-seed ranking-ab --signal <name>` ablates one ranking signal at a time with required controls | Edge contract "Expose before you rank" | narrow — ablation exists for ranking signals only |
| A5 | Composite "Decision Information Efficiency" metric | Component metrics reported separately with population, numerator, denominator, exclusions, and status | Quality metrics v0 | narrow — declined: "No composite quality score" is an explicit non-goal |
| A5 | Abstention quality and insufficient-evidence detection | `missing_evidence[]` in the Evidence Pack; `unavailable` and `not_applicable` metric statuses | Shipped Phase 1; Quality metrics v0 | narrow — insufficiency is reported, never scored as a benchmark dimension |

## Crosswalk — relevance and deterministic-agent set

| Proposal | Claimed capability | Already exists as | Owner document | Delta |
|---|---|---|---|---|
| B0 | Metadata-vs-sidecar-vs-computed-view placement rule | Invariant #6: authority may be partitioned, but every authoritative field or lifecycle has exactly one declared owner; everything else is a rebuildable derived projection | Constitution invariant #6 | narrow — the rule is constitutional; no per-field placement table is written down |
| B2 | "Lens" and "sidecar" as distinct architectural terms | Canonical vs derived projection (invariant #6); `authored`, `computed_canonical`, `git_derived`, `provider_extracted`/`_resolved`/`_inferred`, `generated` authority classes | Constitution invariant #6; Provenance taxonomy axis 2 | none |
| B2 | Four existing lenses (timeline, ADR, diagram, relationship) | Timeline entries, diagram sidecars under `sessions/diagrams/`, link sidecars under `sessions/links/`, the canonical `build_related_entry_graph` reader; the ADR lens is DRAFT only | Edge contract; Link sidecars; ADR contract (draft) | narrow — three of the four ship; the ADR lens is an unimplemented draft |
| B2 | Common sidecar contract with `generator`, `policy_version`, `confidence`, `review.state` | Link and diagram sidecars carry `entry_id` and content only; `classify_pending` is the sole lifecycle flag; authority classes exist on Trace graph nodes | Link sidecars; Provenance taxonomy | narrow — declined in part: a general manifest authority layer conflicts with invariant #6's one-owner-per-field rule; the concrete gap is that no sidecar carries generator or review provenance |
| B2 | Lens admission criteria gating any new lens | The five-question test (§9), "Expose before you rank", "Integrate, don't duplicate", "Prove risky automation on a small case" | Constitution §9 and §3; Edge contract standing rules | none |
| B2 | Decision-oriented retrieval combining signals with successor expansion | `search_memory` combines lexical, semantic (Model2Vec), recency decay, and topic filtering, with default-on `supersession_damping` and `superseding_successor_boost`, annotating every result with `superseded_by`, `superseding_head`, `evolved_by`, `evolved_head` | Edge contract | none |
| B2 | Trace presentation distinguishing canonical, generated, and reviewed | The Trace inspector shows `Authority` and `Provenance` as distinct rows, never a merged score, plus provider, revision, and a `stale` flag | Provenance taxonomy step 4 (done 2026-07-17) | none |
| B3 | Explicit eligibility result vocabulary (`eligible`, `not_applicable`, `uncertain`, `deferred`, `failed`) distinguishing "not applicable" from "not evaluated" | `MetricStatus` = `measured`, `not_applicable`, `unavailable` in `memory_seed/quality.py`, with the rule that an empty population reports `not_applicable` and never a fake 100 percent | Quality metrics v0 | genuine |
| B3 | Deterministic pre-filters triggering sidecar evaluation | `link audit` generates candidates from shared `F:` files and shared topics, with `--for` and `--date` scoping | Link sidecars layer 2 | narrow — detection exists for link edges only; there are no per-sidecar-kind eligibility triggers |
| B3 | Structured rejection recorded instead of silent omission | `classify_pending: true` inert stubs plus the `sidecar-unclassified-stub` warning and ESR open-stub count | Link sidecars | narrow — a stub records "undecided"; there is no vocabulary for "decided not applicable" |
| B3 | Split deterministic and semantic validation | `links check` (schema, refs, forward-only, cycles, duplicates, orphan and malformed sidecars, commit hashes), `topics check` (controlled vocabulary), `docs check` (link resolution, lane bindings) | Edge contract validation authority | narrow — every deterministic check listed ships except Mermaid parsing; no semantic validation exists |
| B3 | Reconciliation commands (`sidecars check`, `reconcile`, `coverage`) | `links check`, `link audit`, `link audit --apply` (idempotent scaffolds), `memory-seed quality report` | Edge contract; Link sidecars; Quality metrics v0 | narrow — reconciliation covers link edges; no per-sidecar-kind coverage command exists |
| B3 | Per-entry sidecar manifest ledger of evaluations | Coverage reported as a derived, read-only projection with declared populations and exclusions | Quality metrics v0; Constitution invariant #6 | narrow — declined: a manifest owning evaluation state conflicts with one-owner-per-field; coverage must be a derived report |
| B3 | Coverage metrics for sidecar generation and reconciliation debt | Five v0 metrics with population, numerator, denominator, exclusions, and status; baseline recorded at revision `bc9b174` | Quality metrics v0 | narrow — the metric framework ships; none of its metrics measure sidecar coverage |
| B3 | Cross-provider output conformance suite with fixtures and thresholds | Invariant #5 states model independence as a property of meaning; no conformance harness exists | Constitution invariant #5 | genuine |
| B3 | Lifecycle-state vocabulary `generated`, `validated`, `reviewed`, `promoted`, `stale`, `superseded` | Authority classes distinguish `authored` from `generated`; `stale` flag in the Trace inspector; ADR transitions proposed→accepted/rejected→superseded | Provenance taxonomy; ADR contract (draft) | narrow — source and authority ship; no review or promotion state exists on any sidecar |
| B4 | Declared `intent` entry field (`research_planning`, `implementation`, `validation`, `decision_update`) | Nothing records declared intent; `topics`, `branch`, DRAFT sections, and `F:` file evidence must be read to infer stage | Edge contract (entry metadata) | genuine |
| B4 | Branch lifecycle as a computed view over entry intents | `branch` is a stored historical label; Trace chains entries sharing it as a time-ordered axis alongside `topic`, `agent`, `day` | Edge contract | narrow — the axis exists; no lifecycle state is derived from it, and derivation depends on `intent` |
| B4 | `entries check-intent`, `branch lifecycle`, `branch gaps` commands | — | — | narrow — the commands are downstream of the `intent` field above, not a separable capability |
| B4 | Historical backfill of intent with inferred-source provenance | Append-only history with a single narrow, per-edge, user-approved exception for untyped `related_entries` metadata | Constitution invariant #2 (v1.2 exception); Semantic-record plan non-goals | narrow — declined: "No historical entry migration or inferred reclassification" is a plan non-goal, and invariant #2 permits no inferred batch pass |
| B5 | Open-questions and unresolved-tensions lens | Constitution §10 is a single hand-maintained section; `blocked_by` and `next_action` are per-document lane fields | Constitution §10 | genuine |
| B5 | Assumptions and validity-conditions lens | DRAFT `A:` records alternatives, not assumptions; nothing records a validity condition or its validation result | Constitution §4 DRAFT policy | genuine |
| B5 | Validation and evidence-record lens | DRAFT `T:` tests and `F:` files record validation evidence per entry; `ranking-ab` records signal validation results | Constitution §4 DRAFT policy; Edge contract | narrow — validation evidence is recorded per entry, never addressed to a subject decision |
| B5 | Durable findings / learned-facts lens with `invalidated_by` | Session entries are the durable finding record; supersession and evolution already express invalidation, and files are authority for what is true now | Constitution invariants #2, #4; Edge contract | narrow — findings live in prose; there is no compressed claim-level record |
| B5 | Question-oriented retrieval index with canonical questions and variants | Lexical plus semantic search over the corpus, alias-expanded topic filtering through `.memory-seed/topics.yaml` (23 canonical slugs), Trace facets | Edge contract; Constitution §4 topic policy | narrow — question-shaped retrieval works; no canonical-question deduplication layer exists |
| B5 | Pilot method — hand-label a sample, extract with two providers, measure | Step 2 of the corrected sequence already prescribes hand-modelling before automation | INBOX-ASSESSMENT.md corrected sequence | narrow — the method is agreed; the provider-first half is explicitly resequenced by the assessment |
| B6 | Phase A — baseline and overlap map against existing owners | This document | INBOX-ASSESSMENT.md step 1 | none |
| B6 | Phase 0 — architectural vocabulary (`canonical`, `declared`, `derived`, `promotion`) | Invariant #6's authoritative-vs-derived distinction; the seven authority classes; ADR promotion semantics | Constitution invariant #6; Provenance taxonomy | none |
| B6 | Phases 1–6 delivery sequence | Restates the capabilities scored above; the plan gates in the semantic-record plan, quality metrics v0, and the provenance taxonomy already sequence the same work | Semantic-record plan; Quality metrics v0; Provenance taxonomy | narrow — sequencing is owned; the proposed order inverts the assessment's evidence-first correction |

## Crosswalk — proposed constitutional principles

A6 and B1 are near-duplicate constitutional drafts. Both were written against Constitution v1.2 or
earlier; the ratified text is now v1.3 (2026-07-19). This table maps each proposed principle to the
seven invariants, the principles in §3, the five-question test in §9, and the `[candidate]` sections
§7 and §8.

| Proposal | Proposed principle | Already constitutional law? | Where | Delta |
|---|---|---|---|---|
| A6-1 / B1-3 | Every component should reduce decision effort | Yes, as a gate | §9 five-question test — every proposal must improve Capture, Validation, Retrieval, Trust, or Application, and say which | none |
| A6-2 | Important decisions must remain explainable | Yes | Invariant #3 — every decision traceable to who, what, when, and the reasoning | none |
| A6-3 | Supersession must preserve causality; never rewrite history | Yes | Invariant #2 append-only; forward-only and acyclic guards in the edge contract; §4 DRAFT `D:`/`R:` policy | none |
| A6-4 | Evidence should be proportional to consequence | No | Nearest is §7 trust model, still `[candidate]`, and the `risk_signaling` skill | genuine |
| A6-5 | Context should be minimal but sufficient | No | Not present at any layer | genuine |
| A6-6 / B1-1 | Deterministic structure should reduce stochastic choice | Partly | Invariant #2 write-surface parity (v1.3) requires identical validation on every write surface; §4 controlled topic vocabulary; invariant #5 model independence | narrow — determinism is law for writes and identity; it is not law for classification or generation |
| A6-7 / B1-5 | Generated views must not become hidden sources of truth | Yes | Invariant #6 — every cache, index, database, embedding, snapshot, or hosted backend is a rebuildable derived projection, never authoritative | none |
| A6-8 | Historical truth and current truth must coexist | Yes | Invariants #2, #4, and #7 — append-only history, files authoritative for now and memory for why, superseded entries down-ranked but never removed | none |
| A6-9 | Structure must earn its maintenance cost | Yes, as a gate | §9 five-question test; §3 "Immediate value before future value" | none |
| A6-10 | Benchmark the behaviour the system is intended to create | Partly | §8 memory quality, still `[candidate]`; §3 "Expose before you rank"; the shipped `ranking-ab` gate | narrow — benchmarking is a principle and a shipped gate for ranking only; §8 has not graduated |
| A6 rule | Prefer designs that increase decision quality under constrained context | No | Not present | genuine |
| A6 rule | Consequential claims must be traceable to evidence, assumptions, or declared uncertainty | Yes | §3 "Evidence before opinion"; invariant #3 | none |
| B1-2 | Constrain what is known; derive what is discovered | Yes | Invariant #6 partitioned authority with one declared owner per field; Link sidecars principle 3 — write-time YAML is canonical for what the author knew, the sidecar is the enrichment layer for what is discovered later | none |
| B1-4 | Optimise for reasoning, not storage | Partly | §1 vision — preserve reasoning so work is not repeated; §9 | narrow — stated as purpose, not as a testable design principle |
| B1-6 | Absence should be queryable when meaningful | No | `MetricStatus` in `memory_seed/quality.py` covers metric populations only | genuine |
| B1-7 | Model capability differences affect quality, not contract compliance | Partly | Invariant #5 — no entry's meaning depends on the agent or model that wrote it | narrow — the invariant governs entry meaning; a minimum provider output contract is not law |
| B1 test | Ten-question gate before adding any field, sidecar, or index | Yes, in a different shape | §9 five-question test; §11 governance | none |

## Findings

**Already shipped law.** Six of A6's ten principles and four of B1's seven are already constitutional
text, in most cases more precisely than the proposals state them. Invariant #6 covers A6-7 and B1-5
verbatim in substance. Invariant #2, #4, and #7 together cover A6-8, and invariant #2's v1.3 write-surface
parity amendment covers most of B1-1's "enforce through validation rather than agent discretion" — the
proposals predate it. Invariant #3 covers A6-2. The §9 five-question test covers A6-1, A6-9, B1-3, and
B1's ten-question gate. B1-2 is close to a restatement of the link-sidecar contract's own principle 3.
None of these needs an amendment; several would be weakened by re-ratification in looser wording.

**Already shipped capability the proposals understate.** The Evidence Pack builder already produces a
deterministic, fingerprinted packet with corpus and revision provenance, contradiction detection, and
missing-evidence reporting, verified by a byte-exact snapshot test — A2 and A4 both describe this as
absent. Its real gap is surface exposure, not existence: it is reachable only by importing
`build_timeline_evidence_pack` from `memory-trace/memory_trace/evidence.py`. Likewise, `supersedes` and
`evolves` ship as independent typed kinds with forward-only and acyclic guards, sidecar augmentation, and
computed inverses including `superseding_head`; A3 treats supersession as generic and document-level.
Retrieval already blends lexical, semantic, recency, topic, and supersession signals with default-on
damping and a validated successor boost; B2 proposes this as new integration work.

**Duplication across the two sets.** A6 and B1 are the same document written twice: eight of A6's
thirteen statements have a direct B1 counterpart, and both propose ratifying material that is already
law. A2 and B2 propose overlapping layers under different names — B2's "lens with provenance" is the
general form and A2's "evidence packet" the specific instance — and both are largely realised already by
the Evidence Pack, the live link and diagram sidecars, and the provenance taxonomy's `provenance_class`
and `authority_class`. The A4/B5 pairing asserted in triage does not hold on inspection: A4 is a
context-assembly pipeline and B5 a knowledge-lens roadmap, with no shared mechanism. **A4 and B3** share a
mechanism without being duplicate documents: both propose a versioned policy plus a generated manifest
recording what was included, omitted, and why, applied to different subjects — retrieval-time context
assembly in A4, generation-time sidecar coverage in B3. One manifest and policy layer could plausibly
serve both. A1 and A3 also overlap internally — A1's decision IDs and A3's
decision-level supersession are one capability, already owned by the semantic-record plan.

**Conflicts with owner non-goals.** Five claims are uncovered but explicitly declined, and are not
promotion candidates as written: A1's and A3's new edge kinds ("No new graph edge kinds"), A1's embedded
`decisions:` block in entry YAML (decision identity is the sidecar's), A5's composite efficiency metric
("No composite quality score"), B3's per-entry manifest owning evaluation state (invariant #6's
one-owner-per-field rule), and B4's inferred historical backfill ("No historical entry migration or
inferred reclassification"; invariant #2 permits no inferred batch pass).

**Genuine deltas.** Eleven rows, grouped below into ten items; four are constitutional principles rather
than capabilities:

1. **A3 — decision-change impact report.** No owner document proposes propagating a decision change to
   the plans, specs, and tasks it affects; `link audit` detects uncaptured structural neighbours only.
   Large and unowned; the assessment's scope-multiplication warning applies directly.
2. **A5 — gold-set benchmark of decision quality under constrained context.** Quality metrics v0
   measures corpus health and `ranking-ab` measures retrieval ordering; neither scores whether a
   grounded decision was reached. Gated behind the v0 usefulness review, whose next action is JNL's.
3. **B3 — eligibility result vocabulary distinguishing not-applicable from not-evaluated.** The
   `MetricStatus` precedent covers metric populations only; nothing records that a record was evaluated
   and found not to need a sidecar.
4. **B3 — cross-provider output conformance suite.** Invariant #5 makes model independence law as a
   property of meaning; no fixture corpus or conformance threshold tests it. Downstream of an extraction
   pipeline that does not exist.
5. **B4 — declared `intent` entry field.** No field records intent; stage must be inferred from prose.
   The capability is uncovered; its *value* is contested — the assessment requires proof that it beats
   existing topics, DRAFT sections, branch, and `F:` file evidence before it becomes mandatory.
6. **B5 — open-questions lens, addressed to an entry.** *(narrowed 2026-07-20)* Constitution §10 is one
   hand-maintained section and nothing addresses an open question to an **entry**. The original wording
   here also claimed nothing "resolves it over time", which is false: §10 carries dated resolutions
   (`CONSTITUTION.md:192,199`, both "RESOLVED (2026-07-14)"), and `blocked_by`/`next_action` are enforced
   per document by `docs_check.py`. The table row above was accurate; this prose was not.
7. **B5 — assumptions and validity-conditions lens.** *(narrowed 2026-07-20)* The residue is a validity
   condition **bound to a stated assumption**. The original "no validation result is recorded anywhere"
   is false — DRAFT `T:` records validation results per entry, as the table row itself concedes. Stating
   an assumption is also live practice in the `risk_signaling` Proceed-and-flag tier, but it is spoken,
   not durably recorded.
8. **A6-4 — graded evidence requirements across decisions.** *(corrected 2026-07-20)* The original claim
   — "not present at any constitutional layer" — was **false**. `CONSTITUTION.md:105-106` carries a
   *cited* §3 principle, "Prove risky automation on a small case; don't remove guards you don't
   understand", which is consequence-proportional evidence at the Principles layer; the crosswalk weighed
   only §7 and the `risk_signaling` skill. The real residue is narrower: §3 covers the risky-automation
   *instance*, while A6-4 grades evidence across five axes (consequence, irreversibility, reach,
   uncertainty, dispute) as a general rule — and §4's DRAFT policy requires D/R/A/F/T *uniformly*
   regardless of consequence, which is the opposite of graded.
9. **A6-5 — minimal-but-sufficient context as constitutional text.** *(narrowed 2026-07-20)* Literally
   true that neither appears in the Constitution, but "as a design objective" is falsified by shipped
   work: `docs/5_Completed/worker-context-minimisation-proposal.md` (SHIPPED 2026-07-17) defines a Worker
   Context Contract with `context_load: minimal` and an explicit sufficiency guard. The residue is
   constitutional codification, plus decision-quality-under-constrained-context as a stated objective —
   which is what delta 2's benchmark would supply evidence for.
10. **B1-6 — authored, record-level queryable absence.** *(narrowed 2026-07-20)* Two shipped forms of
    meaningful absence already exist: `missing_evidence[]` with reasons in the Evidence Pack, and the
    `unavailable` vs `not_applicable` split in `memory_seed/quality.py:35` — which *is* the
    not-evaluated/not-applicable distinction B1-6 asks for. The residue is applying it at record level to
    authored entries. Extension of a proven pattern, not a new design.

**Verification note (2026-07-20).** An adversarial pass tried to falsify all ten before these documents
were retired on their basis. Deltas 1–5 survived clean. Deltas 6–10 were true only under a narrow reading
of their own wording and are reworded above; delta 8 was outright false and is corrected. In two cases
(6, 7) the crosswalk's own table rows were more accurate than this Findings prose, so the tables above
stand as written. Deltas 2, 3, 6, 7 and 10 additionally gained a named active owner on 2026-07-20 when
[the Living Archive proposal](../2_Todo/memory-trace-living-archive-and-editorial-focus-proposal.md) was
promoted — it proposes an Open Questions Brief, open-question metadata, assumption lenses, queryable
absence, and a task-completion test for decision quality.

## What step 2 would need

Steps 2 through 5 of the corrected sequence in [INBOX-ASSESSMENT.md](INBOX-ASSESSMENT.md) are undone.
Step 2 hand-models three multi-decision entries with decision-level IDs and evidence anchors, measuring
ambiguity reduction against authoring cost; the natural subject is the collateral recorded in
`mse_mkxdvaxvw99dz4s0`, and the natural target shape is the `source_decision` anchor in the draft ADR
contract, so step 2 is an experiment inside the semantic-record plan rather than new work. Step 3's
constrained-context gold set is the prerequisite for genuine delta 2 and for A4's evidence-recall
metrics, and it can reuse the Evidence Pack as its structural-expansion arm without building anything.
Step 4 pilots the open-questions lens manually and rejects it if it merely duplicates Todo and
`blocked_by` state. Only step 5 decides which of the ten genuine deltas above deserve folding into an
existing owner plan.

---

This document defers disposition. No proposal has been promoted, rejected, or moved.
