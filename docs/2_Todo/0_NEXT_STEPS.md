# Next Steps

Status: **ACTIVE — navigation and sequencing guide**
Updated: 2026-09-09

This is the short route through the live work in `docs/2_Todo/`. Source plans keep their full
requirements, rationale, history, and phase detail. The folder remains the lifecycle authority; this
page answers “what can move next, what is gated, and what needs a decision?”

## Read this first

1. Pick one ready slice below and open its source plan.
2. Check the gate before starting; blocked work is not ready work.
3. Ask JNL when marked **user decision**; an advisory recommendation is not approval.
4. Reconcile completion in the source plan and lifecycle lane; one shipped phase does not close a plan.

The [Inbox/Todo lifecycle audit](../4_Reference/inbox-todo-lifecycle-audit-2026-09-09.md) records the
evidence and exact session filename matches for every work item. The prior terminal moves remain in
[the 2026-09-08 audit](../4_Reference/todo-lifecycle-audit-2026-09-08.md).

## Ready next actions

### Memory Trace UX — M3 bounded graph perspectives

Open [the UX implementation plan](memory-trace-ux-reference-model-implementation-plan.md) and
[its interaction matrix](memory-trace-ux-m0-interaction-matrix.md). M0–M2 are delivered. M3 is the
next bounded slice: one-hop expansion with explicit node/edge counts, a keyboard-operable non-canvas
equivalent, reduced-motion checks, selection continuity, and the named neighbourhood fixture. M4
Quick Open and M5 deterministic resume/attention follow only after M3’s fixture and accessibility
gates.

### Task Packet hardening and calibration

- [Task Packet hardening](task-packet-hardening-progressive-provenance-plan.md): continue independent
  review and dogfooding of the hardened compiler/progressive-provenance path.
- [Calibration harness](task-packet-calibration-harness-plan.md): freeze the representative population
  and sealed holdout design after the smoke-tested harness.

Calibration measures the harness; hardening changes the packet/provenance contract.

### Evidence programme — choose one bounded review

- [Independent validation](independent-validation-brief.md) — hand to an independent agent.
- [Adjudication queue](adjudication-queue.md) — JNL rules each row; rulings are validity ground truth.
- [Memory-index dry run](memory-index-dry-run-plan.md) — JNL decides whether to submit the CLEAR run.
- [Workflow evidence/workbench](memory-seed-workflow-evidence-and-review-workbench-plan.md) —
  reconstruct three completed journeys before fixing the workbench fixture.

The ordering among these four is intentionally unresolved.

## Dependency-blocked work

### Reflection and Seed Pod launch

- [Reflection ledger evolution](reflection-ledger-workstream-evolution-plan.md) owns integrated launch
  verification, first-board evaluation, and public retention-extension follow-up. The first real closed
  board exists; ESR’s receipt/header interpretation still blocks a clean launch evaluation.
- [Prototype retirement](reflection-prototype-retirement-plan.md) verifies the retired prototype stays
  absent in the integrated launch matrix.
- [Seed Pod P0](seed-pod-p0-reconciliation-plan.md) waits on G0 independent re-review and stabilized
  Reflection evidence.

### Retrieval, provenance, and quality gates

- [Provenance and authority](memory-provenance-and-authority-taxonomy-proposal.md): steps 5–7 wait on
  the participant/role model and a user go.
- [Quality metrics v0](memory-quality-metrics-v0-proposal.md): JNL reviews the v0 baseline before
  targets or graduation are proposed.
- [Semantic record and signal foundation](memory-seed-semantic-record-and-signal-foundation-plan.md):
  evaluate remaining record-kind and retrieval-signal work after provenance and quality gates.
- [Semantic projections](memory-trace-semantic-projections-plan.md): validate one Decision projection
  only after B0b and the semantic foundation.

### Sidecar and lifecycle infrastructure

- [Write-time sidecar consolidation](write-time-sidecar-consolidation-proposal.md): accepted writer
  tranche remains in progress; parsed fusion fixtures and remaining lenses are open.
- [Link-audit judgment swarm](link-audit-decision-judgment-swarm-proposal.md): batching/retention shipped;
  vendor-neutral queue/controller orchestration remains.
- [Lifecycle-link authoring assist](lifecycle-link-authoring-assist-proposal.md): steps 1–3 shipped;
  optional authoring extensions remain.
- [Decision-level topics](decision-level-topics-proposal.md): inference stays behind the decision-level
  graph and declared-attribution design.
- [Hierarchical vocabulary](hierarchical-topic-vocabulary-proposal.md): core build shipped; a maintainer
  call is still needed for project-type starter vocabulary.

## Programme backlogs — sequence unresolved

These are coordinated sets, not equal “next steps.” The matrix, roadmap, and blueprint are the canonical
owners; component proposals stay in Todo for traceability.

- [Coverage matrix](memory-trace-next-generation-coverage-matrix.md) — integration authority.
- [Implementation roadmap](memory-trace-next-generation-implementation-roadmap.md) — sequencing source.
- [Architecture blueprint](memory-trace-product-and-system-architecture-blueprint.md) — P0 planning entry.
- Components: [graph/workspace set](memory-trace-graph-and-workspace-proposal-set-index.md), [graph visualisation](memory-trace-graph-visualisation-and-temporal-topology-proposal.md), [structural graph provider](memory-trace-structural-graph-enrichment-provider-proposal.md), [three-region workspace](memory-trace-three-region-workspace-and-dockable-inspector-proposal.md), [evidence annotations](memory-trace-evidence-annotations-and-projection-architecture.md), [frontend architecture](memory-trace-frontend-architecture-and-design-system-proposal.md), and [living archive](memory-trace-living-archive-and-editorial-focus-proposal.md).

Do not invent an order within this set. M3 is the currently recorded ready Trace slice; later choices remain
a roadmap decision.

## User decisions and external actions

- [Ranking A/B unit-change gate](ranking-ab-unit-change-gate-proposal.md): decide whether unit changes need
  a gate at all; this is not an accepted gate.
- [OpenSSF credibility](openssf-credibility-proposals.md): the in-repo slice shipped; external
  security-setting/user actions remain.
- [SkillOpt fit](skillopt-fit-analysis.md): analysis remains unaccepted and identifies external-provider
  and control-plane risks.
- [Editable lens refinement](sidecar-editable-lens-refinement-proposal.md): true in-place editing awaits
  a shape decision.
- [AI timeline summarisation](memory-trace-ai-timeline-summarisation-plan.md): optional provider remains
  disabled by default and follows packaging/release gates.

## Separate plan — do not fold into this route

[Superpowers collaboration integration](superpowers-collaboration-integration-proposal.md) is a separate
user-owned plan. It remains in Todo for its own Phase 0 routing and approved multi-task trial; this page
does not start, retire, or rewrite that plan.

## Terminal history

Ten fully shipped documents are already in `5_Completed/`, and one superseded remedy is in `7_Replaced/`.
Partial implementation does not erase an open remainder. See the audits above for exact filenames and
evidence.
