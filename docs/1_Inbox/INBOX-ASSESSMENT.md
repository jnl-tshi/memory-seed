---
title: Inbox pre-triage assessment — ontology, relevance, and Trace design
status: inbox-assessed
date: 2026-07-18
promotion: explicitly deferred
---

# Inbox pre-triage assessment

This assessment strengthens the incoming material without promoting it. The two proposal sets remain in
`docs/1_Inbox/`; no item is accepted as active work by this document.

## Executive assessment

Both sets contain useful experiments, but neither is safe to promote as written. They were composed as if
Memory Seed lacked capabilities that now exist: entry-level `supersedes`/`evolves`, append-only link and
decision-diagram sidecars, the canonical graph reader, deterministic Evidence Pack Phase 1, the
Constitution v1.2 authority boundary, and the active ADR sidecar foundation plan. The central pre-triage
task is therefore subtraction and integration, not wholesale adoption.

## What is genuinely additive

1. **Decision-level identity** beyond entry-level identity, if proven on multi-decision entries.
2. **Evidence-to-decision addressing** and compact evidence packets, building on—not replacing—the shipped
   timeline Evidence Pack.
3. **Constrained-context benchmarks** that measure grounded decision quality, sufficiency, stability, and
   irrelevant-context ratio.
4. **Queryable absence** for required evaluations, where `not_applicable` is distinct from missing work.
5. **Open-question and assumption lenses** as non-authoritative pilots, provided they prove retrieval or
   decision value and do not become a parallel task system.

## Weaknesses that must block promotion

| Weakness | Why it matters | Required correction |
|---|---|---|
| Duplicate ontology | Several proposed entities and edges already exist under different names. | Begin from a current-capability crosswalk and propose only the missing delta. |
| Wrong supersession baseline | The ontology set treats supersession as absent and proposes a parallel decision graph. | Keep the shipped entry graph authoritative; test decision-level addressing as a layer over it. |
| Competing sidecar authority | The relevance set implies a general mutable manifest and reconciliation layer. | Conform to Constitution Invariant #6: narrowly scoped append-only Markdown owns declared facts; manifests and UI remain derived. |
| Premature constitutionalization | Both sets suggest adopting principles before the experiments that would justify them. | Run prototypes first; constitutional amendments are a final, separately ratified outcome. |
| Historical backfill pressure | Intent and ontology proposals imply broad inferred mutation or classification of history. | Preserve append-only history; derived classifications must remain provenance-labelled and non-authoritative. |
| Scope multiplication | Ontology, evidence, context assembly, provider conformance, intent, lenses, and retrieval are bundled as one programme. | Split into independent hypotheses with kill criteria and one owner plan per workstream. |
| Undefined user value | Several schemas are justified by theoretical neatness rather than a repeated user task. | Every pilot must name the user question, existing failure, and observable improvement. |
| Provider-first sequencing | Cross-provider generation is planned before proving that a lens is useful. | Hand-build a gold set first; automate only after the human baseline demonstrates value. |
| False precision | Confidence scores and composite benchmark formulas risk appearing objective without calibration. | Prefer categorical evidence quality and report component metrics separately before any composite. |

## Set-specific disposition recommendation for later triage

### Ontology and evidence set

- Preserve the constrained-context benchmark and evidence-addressing experiments.
- Merge decision identity into the active semantic-record/ADR sidecar programme rather than creating a
  second decision lifecycle.
- Treat deterministic context assembly as a retrieval experiment downstream of the current graph and
  Evidence Pack, not a new source-of-truth architecture.
- Do not promote the constitutional proposal until experiments produce evidence for a specific amendment.

### Relevance and deterministic-agent set

- Preserve queryable absence, sidecar conformance tests, and the open-question/assumption pilots.
- Replace the proposed general sidecar manifest with derived coverage reporting over the existing narrow
  sidecar contracts.
- Do not make `intent` mandatory until a real-corpus study shows it predicts a useful query or workflow gap
  better than existing topics, DRAFT sections, branches, and file evidence.
- Rewrite the delivery sequence around tests and deltas, not architectural-language adoption.

## Corrected pre-triage sequence

1. Build a current-capability crosswalk against the active semantic-record plan, graph-edge contract,
   provenance taxonomy, Evidence Pack, topics, and existing sidecars.
2. Hand-model three multi-decision entries with decision-level IDs and evidence anchors; measure ambiguity
   reduction and authoring cost.
3. Build a small constrained-context gold set and compare current retrieval against one deterministic
   structural-expansion policy.
4. Pilot one open-question lens manually; reject it if it merely duplicates Todo/blocked-by state.
5. Only then decide which narrow proposal deltas deserve promotion into existing owner plans.

## Trace design assessment

The current Trace is credible and information-rich, but its dense beige chrome, uniform border treatment,
small controls, and visually competing side panels make it feel like an internal diagnostic console. The
humanised direction should retain density while improving reading rhythm:

- editorial hierarchy: serif display titles, humanist sans controls and metadata;
- warm paper neutrals with mineral green, dusty blue, terracotta, and ochre accents;
- fewer boxes, more whitespace and typographic grouping;
- a readable document inspector with evidence in the margin rather than stacked chips everywhere;
- restrained organic cues in timeline paths, without compromising exact graph semantics;
- progressive disclosure for project counts, topics, and low-priority metadata;
- explicit focus and review states expressed in language, not colour alone.

The mockups are design hypotheses. They do not authorize implementation or replace B0b acceptance work.
