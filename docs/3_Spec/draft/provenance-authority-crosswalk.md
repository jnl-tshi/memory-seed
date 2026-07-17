---
title: "Provenance and authority crosswalk (draft)"
date: "2026-07-17"
project: "memory-seed"
spec_binding: draft
status: "candidate — not binding"
next_action: "JNL decides the authority_class contract question in §5, then steps 3–6 of the BG1 proposal can proceed."
related:
  - "docs/2_Todo/memory-provenance-and-authority-taxonomy-proposal.md"
  - "docs/CONSTITUTION.md"
  - "docs/2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md"
  - "docs/2_Todo/memory-trace-structural-graph-enrichment-provider-proposal.md"
---

# Provenance and authority crosswalk (draft)

**Candidate — not binding.** Steps 1–2 of the
[BG1 taxonomy proposal](../../2_Todo/memory-provenance-and-authority-taxonomy-proposal.md): inventory every
existing provenance/authority/confidence/lifecycle field, then publish canonical ownership and aliases.
Per that proposal's own instruction — *"do not change ranking or actionability defaults in the
taxonomy-definition step"* — this document **changes no code and no default**. It is a map of what exists
and where the vocabularies disagree.

It exists because BG1 is a constitutional gate: nothing generated or provider-derived may influence an
agent until provenance and authority are separable and inspectable. You cannot gate on a taxonomy whose
own field values contradict each other, so the disagreements below have to be resolved first.

## 1. Inventory — what exists today (grounded)

| Field | Where | Type today | Values actually emitted |
|---|---|---|---|
| `provenance_class` | `memory-trace/memory_trace/models.py:29` (`ProvenanceClass`) | 7-value `str` Enum | **only** `authored_memory` |
| `provenance_class` | `memory-trace/memory_trace/models.py:252` (`TimelineEntry`) | `ProvenanceClass`, defaults `authored_memory` | `authored_memory` |
| `provenance_class` | `memory-trace/memory_trace/models.py:284` (`RendererGraphNode`) | `ProvenanceClass` | `authored_memory` |
| `authority_class` | `memory-trace/memory_trace/models.py:285` (`RendererGraphNode`) | **bare `str`** | **only** `canonical_memory` |
| `confidence` | `memory_seed/processes.py:18` | `Literal["high","medium","low"]` | `high` / `low` |
| lifecycle edges | entry YAML | `supersedes` / `evolves` / `related_entries` / `continuity` | authored |
| computed inverses | `semantic_cache.build_related_entry_graph` | `inbound` / `superseded_by` / `evolved_by` | computed |

Validation today (`memory-trace/memory_trace/graph_projection.py`):

- `provenance_class` is checked against the `PROVENANCE_CLASSES` frozenset (L216) — **enum-enforced**.
- `authority_class` is checked only as *"a non-empty string"* (L218) — **no vocabulary at all**.

## 2. Canonical ownership

One owner per axis. These are the four questions BG1 separates; nothing may collapse them.

| Axis | Question | Canonical owner | Status |
|---|---|---|---|
| Provenance | Where did it come from? | `ProvenanceClass` (the shipped 7-value API enum) | **settled** — do not fork |
| Authority | What authority does its meaning carry? | `authority_class` | **unsettled** — see §5 |
| Lifecycle | What state is it in? | the record type itself (entry edges, annotation status, proposal lane, provider freshness) | settled — stays distributed on purpose |
| Actionability | May an agent act on it now? | computed by policy; fails closed | not built (BG1 step 5) |

Confidence is **separate metadata on all four**. It can never upgrade authority or actionability.

## 3. Alias map — shorthand that must map, not fork

The evidence-annotations architecture uses a four-class shorthand
(`Authored` / `Computed` / `External` / `Derived`). BG1 requires it map onto the API vocabulary rather
than become a parallel enum. It is not a fifth axis — it is a *coarsening* that straddles two axes:

| Architecture shorthand | → `provenance_class` | → `authority_class` (proposed) |
|---|---|---|
| Authored — entry, `related_entries`, `supersedes`, `evolves`, continuity | `authored_memory` | `authored` |
| Computed — inbound links, `superseded_by`, `evolved_by`, importance, connectivity | `authored_memory` (derived *from* authored memory) | `computed_canonical` |
| External — commit, PR, review comment, CI result | `source_control` / `pr_review` / `automation_ci` | `git_derived` or `provider_*` |
| Derived — AI summary, report, presentation, recommendation | `generated_artefact` | `generated` |

Note the shorthand is lossy in both directions: `External` spans three provenance values, and `Authored`
vs `Computed` share one. **This is why the shorthand cannot be the stored field.** Use it for prose and UI
grouping; store the two axes.

## 4. Name collision — `confidence` in `processes.py` is a different concept

`memory_seed/processes.py:18` defines `Confidence = Literal["high","medium","low"]`. This is **process
detection confidence** (how sure the runtime is that it spotted a running process). It is unrelated to
provenance confidence and must not be reused, imported, or widened for the taxonomy. If provenance
confidence is added later it needs its own type; sharing this one would silently couple a UI trust
signal to process detection.

## 5. The open contract question — `authority_class` already disagrees with BG1

**The shipped code emits `authority_class: "canonical_memory"`
(`graph_projection.py:120`). That value is not in BG1's proposed vocabulary:**

```text
authored · computed_canonical · git_derived
provider_extracted · provider_resolved · provider_inferred · generated
```

So the field BG1 designates as the authority owner is currently a free-text string carrying an
undocumented value from a parallel vocabulary — precisely the "parallel values" failure BG1 exists to
prevent. On the semantics, `canonical_memory` on a `memory_entry` node means BG1's **`authored`**.

Constraining the field is **not additive**, which BG1 step 3 requires ("add additive API models and
fixtures"). `authority_class` is published as `"type": "string"` in the frozen
`/api/v1` contract (`memory-trace/tests/contract/openapi.v1.json:1045`) and in `types.ts:459`. Narrowing a
free string to an enum, or changing the emitted value, is a **v1 contract break** — not a decision an
agent should make unilaterally.

**Open user decision — pick one:**

| Option | Effect | Cost |
|---|---|---|
| **(a)** Rename the emitted value `canonical_memory` → `authored` and enum-constrain in v1 | one vocabulary immediately | breaks any v1 consumer reading the current value |
| **(b)** Add `canonical_memory` to the authority vocabulary as a synonym for `authored` | no break | keeps two names for one concept — the thing BG1 forbids |
| **(c)** Leave v1's `authority_class` a free string; introduce the enum in `/api/v2`, with this crosswalk as the migration map | no break, one vocabulary eventually | the gate waits on v2 |
| **(d)** Keep v1's wire value, but validate against the enum *internally* and map at the boundary | no break, internal correctness now | a mapping layer to maintain |

There is a real argument for **(c)** or **(d)**: only one consumer exists (the bundled React client), the
value has never varied, and BG1's own non-goals forbid breaking changes made for tidiness. But the API is
versioned precisely so this kind of correction has a home — which is why this is yours, not mine.

## 6. What is unblocked once §5 is answered

BG1 steps 3–6 in order: additive models + fixtures → distinct provenance/authority display in Trace →
actionability as a policy result with reason codes → fail-closed fixtures proving generated and
provider-inferred content cannot become actionable on their own. Only then does §7 graduation get
proposed.

Two `memory-seed quality report` metrics (`provenance_coverage`,
`generated_claim_citation_coverage`) currently report `unavailable` **because this taxonomy does not
exist**. They move to `measured` when step 3 lands — that is the first evidence that BG1 works.
