# 2_Todo

This lane contains accepted or still-owned roadmap work; it is not a priority ranking by itself.
Start with [`0_NEXT_STEPS.md`](0_NEXT_STEPS.md), which groups the live plans into ready slices,
dependency-blocked programmes, unresolved user decisions, and the separate Superpowers plan. The
generated table below is a complete metadata index for lookup; it is intentionally not the route
through the work. Mixed plans keep their full history and shipped-phase detail in their source files.

<!-- docs-index:begin -->
| Document | Priority | Blocked by | Next action / pointer |
|---|---|---|---|
| [seed-pod-p0-reconciliation-plan.md](seed-pod-p0-reconciliation-plan.md) | P0 | G0 independent re-review approval and stabilized Reflection… | Focused G0 re-review of legacy root Task Packet compatibility and distinct-path root provenance… |
| [task-packet-hardening-progressive-provenance-plan.md](task-packet-hardening-progressive-provenance-plan.md) | P0 | — | Harden and independently review Task Packet compilation, then dogfood the improved packets whil… |
| [declarative-retrieval-specification-proposal.md](declarative-retrieval-specification-proposal.md) | P1 | [] | Keep the delivered M0-M3 retrieval and Task Packet contracts stable; design M4 Trace/Evidence E… |
| [derived-projection-implementation-plan.md](derived-projection-implementation-plan.md) | P1 | — | Phase 1 SHIPPED 2026-07-15 (warm start + atomic swap + perf). Remaining fast-follow (deferred, … |
| [independent-validation-brief.md](independent-validation-brief.md) | P1 | — | Hand this file to an agent that has not worked on Memory Seed's experiments; it derives its own… |
| [memory-index-dry-run-plan.md](memory-index-dry-run-plan.md) | P1 | — | JNL decides whether to submit to Verging Labs v0.2 (early September) on Run 9's 87.1/CLEAR, zer… |
| [memory-provenance-and-authority-taxonomy-proposal.md](memory-provenance-and-authority-taxonomy-proposal.md) | P1 | — | Steps 5–6 (GATED on the participant/role model + a user go): implement actionability as a polic… |
| [memory-quality-metrics-v0-proposal.md](memory-quality-metrics-v0-proposal.md) | P1 | user review — is the baseline useful and repeatable? (propo… | JNL reviews docs/4_Reference/memory-quality-v0-baseline.md. Only then propose targets, ESR surf… |
| [memory-seed-semantic-record-and-signal-foundation-plan.md](memory-seed-semantic-record-and-signal-foundation-plan.md) | P1 | — | Evaluate the remaining record_kind and retrieval-signal work after the provenance and quality g… |
| [memory-trace-graph-and-workspace-proposal-set-index.md](memory-trace-graph-and-workspace-proposal-set-index.md) | P1 | — | promoted-to-todo |
| [memory-trace-graph-visualisation-and-temporal-topology-proposal.md](memory-trace-graph-visualisation-and-temporal-topology-proposal.md) | P1 | — | promoted-to-todo |
| [memory-trace-structural-graph-enrichment-provider-proposal.md](memory-trace-structural-graph-enrichment-provider-proposal.md) | P1 | — | promoted-to-todo |
| [memory-trace-three-region-workspace-and-dockable-inspector-proposal.md](memory-trace-three-region-workspace-and-dockable-inspector-proposal.md) | P1 | — | promoted-to-todo |
| [memory-trace-ux-m0-interaction-matrix.md](memory-trace-ux-m0-interaction-matrix.md) | P1 | [] | Implement M3 bounded graph perspectives and controlled expansion against the named fixtures. |
| [memory-trace-ux-reference-model-implementation-plan.md](memory-trace-ux-reference-model-implementation-plan.md) | P1 | — | Implement M3 bounded graph perspectives and controlled expansion against memory-trace-ux-m0-int… |
| [reflection-ledger-workstream-evolution-plan.md](reflection-ledger-workstream-evolution-plan.md) | P1 | — | Complete integrated launch verification and first-board evaluation; track public retention-exte… |
| [reflection-prototype-retirement-plan.md](reflection-prototype-retirement-plan.md) | P1 | — | Verify the retired prototype stays absent in the integrated launch matrix and first-board evalu… |
| [retrieval-recall-fixes-proposal.md](retrieval-recall-fixes-proposal.md) | P1 | — | Re-derive lifecycle labels from evolves edges (F0) - F2 cannot detect its own regression withou… |
| [task-packet-calibration-harness-plan.md](task-packet-calibration-harness-plan.md) | P1 | — | Freeze the representative development population and sealed holdout design now that the Qwen3.5… |
| [adjudication-queue.md](adjudication-queue.md) | P2 | — | JNL to rule each row; the rulings become the project's only validity ground truth. |
| [adr-attached-decisions-earn-a-diagram-proposal.md](adr-attached-decisions-earn-a-diagram-proposal.md) | P2 | — | ACCEPTED 2026-08-07 (JNL) - not a JNL gate any more. Blocked on the ADR backlog draining (open … |
| [attention-retrieval-signal-proposal.md](attention-retrieval-signal-proposal.md) | P2 | — | Accumulate real MCP usage, then run `memory-seed ranking-ab --signal attention --query ...` bef… |
| [document-lifecycle-system-plan.md](document-lifecycle-system-plan.md) | P2 | — | Phases 2-3 COMPLETE 2026-07-17: migration, `docs check` (also in esr + CI), and `docs index` (m… |
| [file-touch-decision-surfacing-proposal.md](file-touch-decision-surfacing-proposal.md) | P2 | — | Observe the hook in real sessions; extend to Codex/Gemini/Cursor events when their PostToolUse … |
| [link-audit-decision-judgment-swarm-proposal.md](link-audit-decision-judgment-swarm-proposal.md) | P2 | — | Batching and retention are shipped. Design the broader vendor-neutral queue orchestration aroun… |
| [memory-seed-workflow-evidence-and-review-workbench-plan.md](memory-seed-workflow-evidence-and-review-workbench-plan.md) | P2 | — | Reconstruct three completed project journeys from existing entries, documents, and Git referenc… |
| [memory-trace-children-proposal.md](memory-trace-children-proposal.md) | P2 | — | DONE 2026-07-27 - 17 slugs live in .memory-seed/topics.yaml and 166 entries attributed via topi… |
| [memory-trace-living-archive-and-editorial-focus-proposal.md](memory-trace-living-archive-and-editorial-focus-proposal.md) | P2 | >- | >- |
| [ranking-ab-unit-change-gate-proposal.md](ranking-ab-unit-change-gate-proposal.md) | P2 | — | Decide whether unit changes need a gate at all, or whether the real-corpus measurement harness … |
| [superpowers-collaboration-integration-proposal.md](superpowers-collaboration-integration-proposal.md) | P2 | — | Complete Phase 0 routing checks, then use the adapter on the first suitable approved multi-task… |
| [write-time-sidecar-consolidation-proposal.md](write-time-sidecar-consolidation-proposal.md) | P2 | — | M1 topics-and-links transaction is in progress on `codex/feature/decision-sidecar-transaction`;… |
| [decision-level-topics-proposal.md](decision-level-topics-proposal.md) | P3 | — | PROPOSAL — decision-level topic *inference* stays gated behind a DECISION-LEVEL GRAPH (JNL's vi… |
| [hierarchical-topic-vocabulary-proposal.md](hierarchical-topic-vocabulary-proposal.md) | P3 | — | ACCEPTED 2026-07-26/27 (JNL, settled inline below) - not a JNL gate any more. Build order steps… |
| [memory-trace-semantic-projections-plan.md](memory-trace-semantic-projections-plan.md) | P3 | — | After B0b and the semantic foundation, validate one Decision projection against the real ADR co… |
| [sidecar-editable-lens-refinement-proposal.md](sidecar-editable-lens-refinement-proposal.md) | P3 | — | SCOPE NARROWED 2026-07-23 — the "add a later edge to an already-blocked entry" case (the withhe… |
| [0_NEXT_STEPS.md](0_NEXT_STEPS.md) | — | — | — |
| [lifecycle-link-authoring-assist-proposal.md](lifecycle-link-authoring-assist-proposal.md) | — | — | — |
| [memory-trace-ai-timeline-summarisation-plan.md](memory-trace-ai-timeline-summarisation-plan.md) | — | — | Phase 2: implement a disabled-by-default provider interface and local-model adapter over determ… |
| [memory-trace-evidence-annotations-and-projection-architecture.md](memory-trace-evidence-annotations-and-projection-architecture.md) | — | — | proposed |
| [memory-trace-frontend-architecture-and-design-system-proposal.md](memory-trace-frontend-architecture-and-design-system-proposal.md) | — | — | proposed |
| [memory-trace-next-generation-coverage-matrix.md](memory-trace-next-generation-coverage-matrix.md) | — | — | active-integration-matrix |
| [memory-trace-next-generation-implementation-roadmap.md](memory-trace-next-generation-implementation-roadmap.md) | — | — | proposed |
| [memory-trace-product-and-system-architecture-blueprint.md](memory-trace-product-and-system-architecture-blueprint.md) | — | — | proposed-canonical-plan |
| [openssf-credibility-proposals.md](openssf-credibility-proposals.md) | — | — | — |
| [session-decision-diagrams-plan.md](session-decision-diagrams-plan.md) | — | — | — |
| [skillopt-fit-analysis.md](skillopt-fit-analysis.md) | — | — | proposal |
<!-- docs-index:end -->
