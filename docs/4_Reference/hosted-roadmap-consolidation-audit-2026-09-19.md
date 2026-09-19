---
title: "Hosted roadmap consolidation audit"
date: "2026-09-19"
source: "JNL constitutional amendment authorization, 2026-09-19"
---

# Hosted Roadmap Consolidation Audit — 2026-09-19

This audit records the exhaustive disposition of the 41 substantive documents that were directly in
`docs/2_Todo/` before the hosted-edition amendment. Navigation files (`0_NEXT_STEPS.md` and `README.md`)
are excluded from the count. Folder location remains lifecycle authority.

## Retained active — 5

| Document | Reason |
|---|---|
| `memory-quality-metrics-v0-proposal.md` | Independent local quality gate remains open. |
| `task-packet-calibration-harness-plan.md` | Calibration population and holdout work remains open. |
| `task-packet-hardening-progressive-provenance-plan.md` | Hardening and dogfooding remain open. |
| `memory-trace-ux-reference-model-implementation-plan.md` | Bounded local UX increments remain open. |
| `memory-trace-ux-m0-interaction-matrix.md` | Acceptance matrix remains active with the UX plan. |

Two newly scoped active documents were added after the audit population was counted:
`hosted-memory-mvp-programme.md` and `reflection-launch-verification-closeout.md`.

## Integrated into the hosted programme and replaced — 19

Every document below moved to `docs/7_Replaced/` with
`superseded_by: ../2_Todo/hosted-memory-mvp-programme.md`:

1. `adjudication-queue.md`
2. `attention-retrieval-signal-proposal.md`
3. `declarative-retrieval-specification-proposal.md`
4. `file-touch-decision-surfacing-proposal.md`
5. `independent-validation-brief.md`
6. `link-audit-decision-judgment-swarm-proposal.md`
7. `memory-provenance-and-authority-taxonomy-proposal.md`
8. `memory-seed-semantic-record-and-signal-foundation-plan.md`
9. `memory-seed-workflow-evidence-and-review-workbench-plan.md`
10. `memory-trace-evidence-annotations-and-projection-architecture.md`
11. `memory-trace-frontend-architecture-and-design-system-proposal.md`
12. `memory-trace-graph-and-workspace-proposal-set-index.md`
13. `memory-trace-graph-visualisation-and-temporal-topology-proposal.md`
14. `memory-trace-next-generation-coverage-matrix.md`
15. `memory-trace-next-generation-implementation-roadmap.md`
16. `memory-trace-product-and-system-architecture-blueprint.md`
17. `memory-trace-three-region-workspace-and-dockable-inspector-proposal.md`
18. `reflection-ledger-workstream-evolution-plan.md`
19. `write-time-sidecar-consolidation-proposal.md`

Their useful requirements survive in the capture, evidence, governance, retrieval, privacy, and phased
acceptance sections of the canonical hosted programme. Their former sequencing is no longer authoritative.

## Deferred with explicit revisit conditions — 8

The following moved to `docs/8_Deferred/`:

1. `adr-attached-decisions-earn-a-diagram-proposal.md`
2. `derived-projection-implementation-plan.md`
3. `memory-trace-ai-timeline-summarisation-plan.md`
4. `memory-trace-living-archive-and-editorial-focus-proposal.md`
5. `memory-trace-semantic-projections-plan.md`
6. `memory-trace-structural-graph-enrichment-provider-proposal.md`
7. `seed-pod-p0-reconciliation-plan.md`
8. `superpowers-collaboration-integration-proposal.md`

## Closed or narrowed — 9

| Original document | Outcome |
|---|---|
| `document-lifecycle-system-plan.md` | Completed; optional extensions moved to `local-memory-optional-followups.md`. |
| `hierarchical-topic-vocabulary-proposal.md` | Completed; optional starter packs moved to the same follow-up. |
| `lifecycle-link-authoring-assist-proposal.md` | Completed; optional writer/nudge work moved to the same follow-up. |
| `memory-index-dry-run-plan.md` | Completed experiment; external submission remains a user choice. |
| `memory-trace-children-proposal.md` | Completed; residual hosted evaluation integrated into the hosted programme. |
| `openssf-credibility-proposals.md` | Completed in-repository slice; provider settings retained in a reference checklist. |
| `reflection-prototype-retirement-plan.md` | Replaced by `reflection-launch-verification-closeout.md`; it was not falsely marked complete. |
| `resolve-stale-worktrees-and-decision-origins-plan.md` | Completed based on the 2026-09-13 reconciliation record. |
| `session-decision-diagrams-plan.md` | Completed; optional packaging moved to local follow-ups. |

## Adjacent conflicting document

`docs/8_Deferred/memory-trace-hosted-product-and-security-architecture.md` was outside the 41-document
Todo population. It moved to `docs/7_Replaced/` because its Markdown-settlement/synchronization model
conflicted with the ratified SQL-authoritative hosted edition. Its security requirements remain inputs to
the canonical hosted programme.

## Count check

`5 retained + 19 integrated/replaced + 8 deferred + 9 closed/narrowed = 41`.
