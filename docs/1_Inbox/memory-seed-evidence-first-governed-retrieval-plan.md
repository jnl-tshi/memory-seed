---
title: Evidence-first governed retrieval and execution assurance plan
status: inbox
priority: P1
next_action: JNL reviews this evidence-reconciled synthesis and decides whether to promote it to docs/2_Todo.
blocked_by: []
sources:
  - active-truth-execution-control-proposal.md
  - memory-seed-first-principles-proposal.md
  - memory-seed-governed-interactive-retrieval-proposal.md
  - semantic-compression-benchmark-proposal.md
  - ../4_Reference/INBOX-ASSESSMENT-2026-08-20-DROP.md
  - ../4_Reference/inbox-2026-08-20-drop-review-claude.md
  - ../4_Reference/inbox-2026-08-20-drop-review-codex.md
  - ../7_Replaced/declarative-retrieval-specification-proposal.md
  - ../4_Reference/information-theoretic-evolution-disposition.md
  - ../../experiments/semantic-compression/recommendation.md
spec_binding: null
---

# Evidence-First Governed Retrieval and Execution Assurance Plan

Status: **INBOX — PROMOTION-READY SYNTHESIS, NOT YET APPROVED WORK.** JNL requested that this document
remain in `docs/1_Inbox/` for the time being. Its metadata, scope, dependencies, sequence, and acceptance
criteria are complete enough for a later move to `docs/2_Todo/` without redesign.

Priority if promoted: **P1**, sequenced behind the delivered Retrieval Specification M0/M1 contract and
inside the existing context-derivation and quality-measurement programme.

## Decision requested

Approve one bounded evidence programme, not a new top-level architecture:

> Measure whether inspectable task-time retrieval, disciplined natural authoring, and three
> execution-assurance controls prevent real errors. Extend an existing owner only when a preregistered
> negative control demonstrates a gap.

The programme absorbs the useful residues of the four 2026-08-20 proposals while rejecting their shared
failure mode: restating shipped mechanisms under new names and promoting the restatement as foundational
work.

## Why this is the synthesis

The four source documents are one thesis with four roles:

| Source | Retained contribution | Disposition inside this plan |
|---|---|---|
| First-principles product definition | Decision memory is the core; enrichment must prove incremental value. | Governing product lens only; no new canonical-object model. |
| Governed interactive retrieval | Reproducible bootstrap context and inspectable effective context are different things. | Workstream 1, built as experiment instrumentation over existing Retrieval Specification output. |
| Semantic compression benchmark | Derived representations must beat raw canonical prose without changing meaning. | Workstream 2 incorporates the completed extractive/selector/normalization evidence and leaves only a separately approved natural-authoring study open. |
| Active truth and execution control | Correct retrieval does not prove correct action; postflight, conflict, and source-trust failures need tests. | Workstream 3, three independent negative controls rather than one P0 control plane. |

The two agent reviews agree on this direction. Claude's review supplies the sharpest prohibitions
(`confidence` does not determine authority; a designated agent does not approve project decisions).
Codex supplies the dependency order and the requirement that claimed gaps survive source-level and
measurement checks before becoming work.

## Existing authority and owners

This plan does not replace or weaken any existing owner:

- Canonical project memory remains human-editable, append-only Markdown. Session decisions retain detailed
  evidence authority; living ADRs curate concern-specific heads and synopsis.
- [`declarative-retrieval-specification-proposal.md`](../7_Replaced/declarative-retrieval-specification-proposal.md)
  owns reproducible context requests and Evidence Pack resolution. M0/M1 are delivered; this plan does not
  reimplement them or pull M2 profiles/composition forward.
- `experiments/context-derivation/` owns retrieval-packet experiments. Its current measured result is the
  baseline: complete-query Recall@5 is 47/60 (78.3%), so enrichment cannot recover decisions that ranking
  never supplied.
- `experiments/semantic-compression/` owns the completed compression evidence package. Its Stage 1,
  lean-DRAFT, front-door, and identifier-normalization diagnostics reject the tested automatic compact
  representations and retrieval repair as production improvements; its current disposition is
  **INVESTIGATE FURTHER**, bounded to a separately designed natural-authoring comprehension and delayed-
  recall study.
- [`memory-quality-metrics-v0-proposal.md`](../2_Todo/memory-quality-metrics-v0-proposal.md) owns quality
  graduation and target-setting. This plan reports component metrics and does not create a second quality
  framework.
- [`information-theoretic-evolution-disposition.md`](../4_Reference/information-theoretic-evolution-disposition.md)
  remains the boundary against relitigating semantic similarity, topic-as-compression, or a broad
  information-theoretic architecture.

## Scope

### In scope

- A fixture-only retrieval trace that distinguishes deterministic bootstrap evidence from consequential
  evidence discovered later in a task.
- A minimal checkpoint experiment comparing static, interactive, and governed-interactive retrieval.
- Reconciliation of the completed semantic-compression evidence and, only with separate approval, a
  natural-authoring study that preserves decision, reason, adopted boundary, rejected alternative, and
  exact identifiers.
- One falsifying test for each claimed execution-assurance gap: postflight compliance, incompatible
  decision writes, and untrusted-source authority leakage.
- Evidence-backed BUILD / EXTEND EXISTING OWNER / DO NOT BUILD decisions for each surviving candidate.

### Non-goals

- No new `active truth` store, lifecycle schema, canonical record, ontology, graph, or authority layer.
- No change to session/ADR authority, Markdown authority, sidecar precedence, or human approval boundaries.
- No Retrieval Specification M2 profiles, composition, named-spec registry, Trace UI, or Evidence Pack
  cache/get API.
- No production checkpoint policy, postflight gate, decision-conflict engine, source quarantine, or meaning
  sidecar before its negative control passes.
- No confidence threshold as authority and no designated-agent approval for project decisions.
- No hidden-reasoning capture. “Evidence used” means an explicit canonical citation or a mechanically
  copied fact in the output, never an agent's self-report about its internal reasoning.
- No rerun of the completed extractive, lean-selector, front-door, or identifier-normalization diagnostics
  unless a new question and sealed evaluation justify it.

## Workstream 0 — Freeze the owner and baseline matrix

Before building an experiment, make every candidate answer four questions:

1. Which current file, contract, test, or command already owns the behaviour?
2. What exact failure remains after that owner is used correctly?
3. What negative control makes the failure observable?
4. What is the smallest reversible intervention that could catch it?

Deliverable: one matrix covering every retained claim from the four proposals, labelled `covered`,
`narrow gap`, or `candidate gap`. A candidate cannot enter Workstream 1–3 without an owner and negative
control.

Acceptance:

- Every claim cites current code/spec/experiment evidence, not only proposal prose.
- No candidate duplicates an active `docs/2_Todo/` owner.
- A clean negative control is tested against the instrument before the instrument is trusted.

## Workstream 1 — Governed interactive retrieval pilot

Extend the existing context-derivation fixtures with a minimal, experiment-only trace:

```yaml
task_run:
  corpus_revision:
  bootstrap_pack_fingerprint:
  retrieval_contract_version:
  consequential_queries:
    - trigger:
      method:
      query:
      result_refs:
      cited_refs:
  final_checks:
    contradictions_checked:
    active_authority_checked:
```

Compare three arms over the same tasks and revision:

1. delivered static Retrieval Specification pack;
2. static pack plus unrestricted task-time retrieval;
3. static pack plus a small preregistered checkpoint set.

Start with component modification, architecture change, and before-completion contradiction checks. Do
not create a general policy vocabulary until an individual checkpoint demonstrates value.

Measures:

- complete-query decision recall and critical-evidence coverage;
- task correctness and detected contradictions;
- unsupported assumptions and human corrections;
- retrieval calls, input tokens, latency, and cited-result utilization;
- false assurance: a completed checkpoint whose output still violates the relevant authority.

Acceptance:

- Bootstrap fingerprints and canonical refs reproduce at one corpus revision.
- The trace separates retrieved refs from explicitly cited/material refs without recording hidden reasoning.
- At least one checkpoint shows a replicated correctness, evidence-coverage, or error-prevention gain over
  unrestricted interactive retrieval; otherwise checkpoint implementation stops.
- No arm weakens current authority, permission, or fail-closed behaviour.
- Findings extend `experiments/context-derivation/`; no parallel benchmark or production contract is added.

## Workstream 2 — Reconcile completed compression evidence; gate natural authoring

Status: **INVESTIGATE FURTHER — the automatic-compression candidates are closed.** The complete
reproducible evidence package now lives in `experiments/semantic-compression/`; do not repeat it as the
previous version of this synthesis proposed.

| Measured stage | Result | Disposition |
|---|---|---|
| Stage 1 extractive representations | Raw retrieval MRR was `0.582`; the best compact arm reached `0.502`. The relationship task was underpowered. | No production meaning sidecar; relationship evidence remains inconclusive. |
| Lean-DRAFT selector | Lean semantic MRR was `0.403` versus raw `0.520`; adjudicated critical errors affected 50% of lean cards versus 0% raw. | Reject canonical shortening and the measured selector. |
| Verbatim D/R/A front door | It retained 97.8% of answer spans, but median first-view context was 86.2% of raw against the frozen 80% maximum. | Reject the query-evidence front door; it did not earn enough context reduction. |
| Held-out identifier normalization | The treatment changed 12–18 full rankings and 31 target scores, but changed zero target ranks; identifier MRR was already `1.000`. | Do not ship the normalization repair as a retrieval improvement on this evidence. |

The current actionable boundary is therefore:

- Keep complete DRAFT prose canonical, rankable, and immediately available.
- Do not ship the tested compact selector, query-evidence front door, semantic sidecar, or lexical
  normalization repair as a performance improvement.
- Treat shorter *natural authoring* as a different hypothesis from automatic compression. It may proceed
  only through a separately approved study using independently authored paired records, human readers,
  comprehension tasks, and delayed recall.
- Require every concise authored arm to retain the decision, reason, adopted boundary, rejected
  alternative, and exact identifiers. Unsupported additions, changed modality/scope/causality, or omitted
  critical constraints are fidelity failures.
- Report task performance and context cost separately. A null result is successful: if the concise arm
  does not pass fidelity or does not materially improve performance per context, close it as **DO NOT
  BUILD**.

This workstream creates no canonical entry change, automatic rewrite, production preview, sidecar,
ontology, or migration. Promotion of this plan does not by itself authorize the remaining study.

## Workstream 3 — Execution-assurance gap probes

Treat the three surviving claims independently:

### 3A — Postflight compliance

Give a worker a versioned pack containing one required and one prohibited behaviour, then inject output
that violates each while remaining structurally valid. Determine whether existing tests/validators catch
the violation. If not, specify the smallest output-to-constraint comparison that does.

### 3B — Decision-level write conflict

Create two isolated branches whose session writes are individually valid but assert incompatible decisions
over one declared scope. Determine whether current structural integration detects only file/ledger conflict
or the semantic incompatibility. Do not infer conflict from similarity; the fixture declares the exclusive
scope and expected incompatibility.

### 3C — Untrusted-source authority leakage

Import a fixture document containing authority-like instructions and an explicit provenance/trust label.
Verify that retrieval and write paths keep it ordinary evidence unless a human-governed promotion path
acts. This is a trust-boundary experiment: no real email, web, client, or private source data is used.

Shared acceptance:

- Each probe includes a positive case, negative control, and instrument-corruption check.
- “Gap” means the current system demonstrably permits the bad outcome; absence of a named feature is not
  enough.
- A passing current control closes the candidate as DO NOT BUILD.
- A reproduced failure produces a focused proposal in the existing owner's document, with its own risk and
  acceptance criteria. It does not automatically authorize implementation.

## Workstream 4 — Decision and routing gate

For each result, choose exactly one disposition:

| Result | Action |
|---|---|
| Existing control passes | **DO NOT BUILD**; record the negative result. |
| Gap reproduced and an owner exists | **EXTEND EXISTING OWNER** with the minimum intervention. |
| Gap reproduced and genuinely ownerless | **BUILD CANDIDATE** as one focused proposal, requiring JNL review. |
| Instrument inconclusive | **INVESTIGATE FURTHER** with the missing evidence named. |

The programme is complete when every retained claim has a disposition and no result remains as a vague
“future platform” recommendation.

## Dependencies

- Delivered Retrieval Specification M0/M1 and its deterministic resolution trace/fingerprint.
- Existing context-derivation fixtures and mechanical scoring.
- Completed `experiments/semantic-compression/` evidence, recommendation, frozen artifacts, and focused
  tests.
- Current quality-v0 usefulness gate and ranking A/B discipline.
- Accepted Markdown, session-decision/ADR, derived-precedence, and control-file authority decisions.
- Explicit approval before provider calls, model downloads, or scored runs that incur cost.

## Risks and controls

| Risk | Control |
|---|---|
| The four proposals and two reviews are correlated evidence. | Treat them as one thesis; require repository evidence and negative controls. |
| Trace volume becomes a proxy for correctness. | Score prevented errors and evidence coverage; trace presence alone earns nothing. |
| “Materially used” becomes unverifiable self-report. | Count explicit canonical citations/copied facts only. |
| Compression becomes a knowledge-representation project. | The automatic arms are closed; any follow-up is a separately approved natural-authoring study with a hard fidelity gate and null-result stop. |
| Governance adds ceremony to low-risk work. | Measure each checkpoint separately; unhelpful checkpoints do not graduate. |
| Source-trust testing crosses a security boundary. | Use synthetic fixtures only and require a separate security review before production design. |

## Programme acceptance criteria

This plan is complete when:

- all retained claims are mapped to current owners and measured failure modes;
- the retrieval pilot reports replicated benefit/cost or a clear stop decision;
- the completed compression evidence remains the baseline and any separately approved natural-authoring
  study resolves to BUILD CANDIDATE, DO NOT BUILD, or INVESTIGATE FURTHER;
- all three execution-assurance probes resolve to DO NOT BUILD, EXTEND EXISTING OWNER, BUILD CANDIDATE,
  or INVESTIGATE FURTHER;
- no experiment writes canonical state or silently changes a production retrieval/authority contract;
- every surviving implementation candidate names one owner, one smallest intervention, and one validation
  gate; and
- results are recorded in existing owner documents rather than creating a second quality, retrieval, or
  governance roadmap.

## Promotion checklist

When JNL approves promotion:

1. Move this file to `docs/2_Todo/` and change frontmatter `status` from `inbox` to `active`.
2. Keep priority P1 and set `next_action` to Workstream 0's owner/baseline matrix.
3. Repair inbound links and regenerate `docs/1_Inbox/README.md`, `docs/2_Todo/README.md`, and
   `docs/README.md` indexes.
4. Do not move the four source proposals automatically; disposition them only after JNL chooses whether
   this synthesis replaces, extracts, or merely relates to them.

## Immediate next action if promoted

Write the Workstream 0 owner/baseline matrix and a one-page Workstream 1 preregistration using the existing
context-derivation fixtures. Do not write production code, launch a scored provider run, or design a new
schema during that first step. Do not rerun Workstream 2's completed automatic-compression diagnostics;
the remaining natural-authoring study requires its own explicit approval and sealed protocol.
