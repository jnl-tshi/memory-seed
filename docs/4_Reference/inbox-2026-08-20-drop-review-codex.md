---
title: "Codex review — the four 2026-08-20 inbox proposals"
status: inbox-assessed
date: 2026-08-21
promotion: none — comparative assessment and recommended investigation order only
---

# Codex review — the four 2026-08-20 inbox proposals

## Bottom line

This is one coherent design position expressed through four documents, not four independent signals that the same roadmap should be accelerated.  Its durable contribution is a useful correction to the project's centre of gravity: reliable, inspectable retrieval matters more than accumulating derived structure.  Its main weakness is that it repeatedly proposes a new top-level control plane before proving which specific control failures remain after the controls already in the repository are used and measured.

I would not promote any document unchanged.  I would retain the product framing in Document 2 as reference material, use Document 3 to define a small measurement surface, run a deliberately small version of Document 4, and use the result to decide whether any of Document 1's larger governance mechanisms deserve a scoped proposal.  This order treats the four documents as a portfolio rather than competing plans.

This review is an independent Codex assessment.  It neither changes an inbox document's lifecycle nor authorizes implementation.  The factual crosswalk remains [`INBOX-ASSESSMENT-2026-08-20-DROP.md`](INBOX-ASSESSMENT-2026-08-20-DROP.md); the parallel Claude opinion is [`inbox-2026-08-20-drop-review-claude.md`](inbox-2026-08-20-drop-review-claude.md).

## Method and scope

I read the four proposals in full and compared their stated mechanisms and sequencing against the current repository's control plane, experiments, and tests.  The spot checks confirmed established supersession handling, guarded session append, context-derivation experiments, and an existing ICM treatment in the stack-benchmark preregistration.  They are not a complete implementation audit, so claims of a wholly absent capability below mean “not demonstrated by this review,” not proof of absence.

| Document | Primary value | Main concern | Assessment |
|---|---|---|---|
| [`active-truth-execution-control-proposal.md`](../1_Inbox/active-truth-execution-control-proposal.md) | Identifies failures after retrieval: compliance, conflicting writes, and untrusted source material. | Declares a P0 replacement control plane before a minimal gap map or a measured failure baseline. | Extract questions and adversarial tests; do not adopt the workstream. |
| [`memory-seed-first-principles-proposal.md`](../1_Inbox/memory-seed-first-principles-proposal.md) | Gives the clearest product definition and an appropriate core-versus-enrichment experiment. | Treats sessions as activity-only, which conflicts with the current authored-decision model. | Keep as strategic reference, not an implementation plan. |
| [`memory-seed-governed-interactive-retrieval-proposal.md`](../1_Inbox/memory-seed-governed-interactive-retrieval-proposal.md) | Separates reproducible starting context from inspectable context discovered during work. | Checkpoints and “evidence used” traces can create ceremony or false certainty unless their value is measured. | Best candidate for a bounded instrumentation experiment. |
| [`semantic-compression-benchmark-proposal.md`](../1_Inbox/semantic-compression-benchmark-proposal.md) | Is falsifiable, preserves canonical prose, and accepts a no-build result. | It combines too many tasks and representations before proving a cheap baseline has value. | Run a reduced pilot only, after a repository-grounded design pass. |

## What the documents agree on — and what that means

All four privilege current applicability, provenance, bounded context, and measurement.  That direction is compatible with the repository's append-only history, derived-sidecar boundary, and “minimal but sufficient context” principle.  The overlap is useful as a design theme, but it is not corroboration: the documents share vocabulary, assumptions, and likely source context.  They should therefore be evaluated as one thesis with four possible interventions.

The practical distinction is important:

- Document 2 asks what product should be proved.
- Document 3 asks how retrieval can be observed during a task.
- Document 4 asks whether a smaller representation improves downstream work.
- Document 1 asks how actions and memory writes should be governed once those facts are known.

Only the middle two naturally produce evidence that narrows the others.  That is why “make active truth P0” is the wrong first move even if Document 1 diagnoses real risks accurately.

## Per-document assessment

### 1. Active Truth and Execution Control

The strongest insight is that successful retrieval is not the same thing as a correct action.  Its postflight-validation, decision-conflict, and source-trust sections describe failure modes that ordinary relevance metrics do not settle.  The inversion-style acceptance cases near the end are particularly valuable because they convert a broad governance narrative into observable failures.

However, the proposed lifecycle, typed states, write controls, preflight, packet manifests, Trace views, concurrency model, and source-trust layer are presented as a connected foundational programme.  That is too much coupling.  Parts of the stated lifecycle and write-control problem are already addressed by append-only decision records, supersession/replacement handling, session-append guards, and worktree integration rules.  The proposal does not map each new field or validation to a demonstrated break in those mechanisms, nor quantify the operator cost of requiring a packet for every consequential task.

**Recommendation:** retain three narrow investigation questions: “Can postflight checks detect rule violations missed by current validation?”, “Can two valid branches assert incompatible decision-level outcomes?”, and “How should untrusted imported material be isolated from authority?”  Reuse the proposal's acceptance cases as a test catalogue.  Do not create an active-truth schema or a P0 workstream until each surviving gap has an owner, source-level evidence, and a smallest viable control.

### 2. First-Principles Product Definition

This is the best positioning document in the set.  “Git-native decision memory for long-running, AI-assisted projects” is precise enough to guide prioritisation, and the core-versus-enriched benchmark makes the right strategic demand: derived intelligence must demonstrate incremental value beyond durable decision memory.

Its error is architectural rather than rhetorical.  The statement that sessions are activity logs rather than canonical memory conflicts with the current repository's decision practice, in which authored session decisions provide the canonical record and ADR heads derive from them.  Recasting sessions as merely raw input would lose the durable identity and provenance that the document elsewhere wants to protect.

**Recommendation:** keep this document as product-strategy reference.  Adopt neither its canonical-object schema nor its phase order verbatim.  Any future product-definition update should retain the current session-to-decision authority chain explicitly.

### 3. Governed Interactive Retrieval

This is the most operationally useful proposal.  Its key distinction — deterministic bootstrap context versus an agent's later effective context — removes a false choice between identical packets and free-form exploration.  Reproducible start state plus an inspectable expansion path is a stronger and more realistic target than forcing identical search behaviour.

The unknown-unknown problem is also real: an agent cannot query for a constraint whose relevance it never notices.  But fixed checkpoints should not be treated as automatically beneficial.  They add token cost and can produce a paper trail without improving decisions.  “Evidence materially used” is similarly an attribution claim that needs a precise, auditable definition; a retrieved result and a relied-on result are not identical.

**Recommendation:** make this the first scoped candidate, but limit it to a versioned bootstrap identity and a minimal retrieval-trace schema.  Evaluate selective checkpoints inside the existing context-derivation work rather than building a second benchmark or a broad orchestration layer.  The success condition is measurable incremental discovery or error prevention, not the presence of more trace data.

### 4. Semantic Compression Benchmark

This is the most disciplined research proposal.  It keeps derived representations non-canonical, defines ablations, requires fidelity analysis, and treats “do not build” as a successful outcome.  Its reminder to inspect the repository first is especially important; ICM is an existing benchmark treatment, not a missing component.

The initial experiment is still oversized.  A corpus of roughly 100 decisions across five representations, four task families, several retrieval metrics, and a literature review risks producing a large, fragile measurement programme before its simplest premise is tested.  Its reference answers may also inherit ambiguity from the same canonical prose they assess; the protocol needs a disagreement rule and repeated measurements before it can make a build verdict.

**Recommendation:** start with a small pilot using existing authored decision/rationale material as the zero-generation comparison arm, then compare it with raw prose on one task family (comprehension or retrieval, not all of them).  Predeclare repetitions, fidelity adjudication, and the negative result that stops the work.  Only add generated `core`/`because`/`constraint` fields if that baseline exposes a measurable gap.

## Recommended evidence order

1. **Use Document 2 as a non-binding product lens.** It sets the question: does the core help before enrichment?
2. **Instrument Document 3's smallest slice.** Record the bootstrap identity and only consequential retrieval expansions in an existing experiment.
3. **Run Document 4's thin pilot.** Compare raw decisions with already-authored rationale/constraint material, with replication and an explicit stop condition.
4. **Revisit Document 1 from measured failures.** Promote only the control whose failure mode survives the two experiments; source-trust may warrant an earlier standalone threat-model exercise because it is orthogonal to retrieval quality.

This ordering is deliberately reversible.  It can yield “no checkpoint,” “no semantic sidecar,” or “no active-truth layer” without leaving a half-built control plane behind.

## Decision posture

No inbox lifecycle disposition is applied by this review.  The appropriate next action is a user choice between: retaining all four as assessed source material, extracting one or more focused `2_Todo/` candidates, or recording a terminal disposition with the comparative rationale above.  Until that choice, the documents remain assessed but untriaged inbox material.
