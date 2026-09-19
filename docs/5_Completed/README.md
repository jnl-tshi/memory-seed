# 5_Completed — shipped / applied

Work that has been implemented and merged. A clean record of real accomplishments — rejected, superseded,
and parked material live in their own lanes (`6_Rejected`, `7_Replaced`, `8_Deferred`) so they don't
clutter this one.

**Required YAML:** `implemented_by:` (session entry id or commit) and the ship date.

**Contents** (12 documents as of 2026-07-16; `docs index` will render this as a table in P2):

- `freshness-aware-memory-ranking-proposal.md` — supersession dampener + `evolved_head`, on by default.
- `real-corpus-ranking-validation-gate-proposal.md` — reusable full-corpus ranking A/B gate and binding
  "expose before you rank" contract.
- `supersession-successor-surfacing-proposal.md` — `superseding_head` plus the lineage-bounded,
  full-corpus-gated successor boost.
- `memory-trace-topic-neighbourhoods-plan.md` — controlled topics across parser, retrieval, CLI, MCP,
  Trace chronological chains, and deterministic topic suggestions.
- `evolution-edges-plan.md` — typed `evolves`, artifact continuity, retrieval surfacing, and the Trail
  continuity axis.
- `configurable-integration-mode-plan.md` — `local-merge`/`pr` project mode, agent contract, integration
  commands, and human-confirmed bootstrap suggestion.
- `proactive-history-retrieval-discipline-proposal.md` — retrieve-the-*why* control-plane discipline.
- `grounding-provenance-write-time-links-proposal.md` — consulted-memory provenance in write-time link
  suggestions.
- `memory-seed-architectural-discovery-proposal.md` — shipped architectural discovery work.
- `fontjoy-typography-pairing.md` — self-hosted Inter + Space Grotesk pairing.
- `goal-run-core-parity-codex.md`, `goal-run-trace-surface-claude.md` — spent 2026-07-13 goal-run briefs,
  fully executed and merged.

The larger archive in `docs/5_Completed/` (43 docs) migrates here in the P2 bulk move.

<!-- docs-index:begin -->
| Document | Priority | Blocked by | Next action / pointer |
|---|---|---|---|
| [3.0-plan.md](3.0-plan.md) | — | — | — |
| [adr-refines-review-trigger-plan.md](adr-refines-review-trigger-plan.md) | — | — | — |
| [adr-reviewed-recorder-proposal.md](adr-reviewed-recorder-proposal.md) | P2 | — | None - CLI and MCP parity shipped with shared validation. |
| [agent-fanout-workflow-plan.md](agent-fanout-workflow-plan.md) | — | — | — |
| [agent-rules-lazy-loading-recommendations.md](agent-rules-lazy-loading-recommendations.md) | — | — | — |
| [agent-worktree-and-branch-hygiene-plan.md](agent-worktree-and-branch-hygiene-plan.md) | P3 | — | complete |
| [agent-worktree-namespace-guard-plan.md](agent-worktree-namespace-guard-plan.md) | — | — | — |
| [baseline-seed-promotions.md](baseline-seed-promotions.md) | — | — | — |
| [branch-field-provenance.md](branch-field-provenance.md) | P3 | [] | None. Decided (JNL, 2026-07-26): A now, D as the standing convention; both are documented. The … |
| [chain-position-aware-link-candidates-proposal.md](chain-position-aware-link-candidates-proposal.md) | — | — | — |
| [chains-as-artifacts-proposal.md](chains-as-artifacts-proposal.md) | — | — | — |
| [cheap-tooling-hardening-proposals.md](cheap-tooling-hardening-proposals.md) | — | — | — |
| [compact-mermaid-diagram-skill-proposal.md](compact-mermaid-diagram-skill-proposal.md) | — | — | — |
| [confidence-signaling-protocol-proposal.md](confidence-signaling-protocol-proposal.md) | — | — | — |
| [configurable-integration-mode-plan.md](configurable-integration-mode-plan.md) | — | — | — |
| [constitution-1.1-partitioned-markdown-authority-amendment.md](constitution-1.1-partitioned-markdown-authority-amendment.md) | — | — | completed |
| [dev-tools-reel-10of10-websites.md](dev-tools-reel-10of10-websites.md) | — | — | — |
| [document-lifecycle-system-plan.md](document-lifecycle-system-plan.md) | P2 | — | Phases 2-3 COMPLETE 2026-07-17: migration, `docs check` (also in esr + CI), and `docs index` (m… |
| [docx-render-windows-seed-lessons.md](docx-render-windows-seed-lessons.md) | — | — | — |
| [evolution-edges-plan.md](evolution-edges-plan.md) | — | — | — |
| [evolution-type-refines-builds-on-proposal.md](evolution-type-refines-builds-on-proposal.md) | — | — | None. The four-step delivery order shipped on 2026-08-09. |
| [excerpt-fallback-defect.md](excerpt-fallback-defect.md) | P1 | — | None. Fixed at the cause: the reader now recognises the legacy singular decision form, so the f… |
| [exclude-superseded-filter-plan.md](exclude-superseded-filter-plan.md) | — | — | — |
| [failed-approaches-logging-plan.md](failed-approaches-logging-plan.md) | — | — | — |
| [fontjoy-typography-pairing.md](fontjoy-typography-pairing.md) | — | — | — |
| [freshness-aware-memory-ranking-proposal.md](freshness-aware-memory-ranking-proposal.md) | — | — | — |
| [git-commit-entry-linking-plan.md](git-commit-entry-linking-plan.md) | — | — | — |
| [goal-roadmap-refinement-and-staged-implementation.md](goal-roadmap-refinement-and-staged-implementation.md) | — | — | — |
| [goal-run-core-parity-codex.md](goal-run-core-parity-codex.md) | — | — | — |
| [goal-run-trace-surface-claude.md](goal-run-trace-surface-claude.md) | — | — | — |
| [graph recommendations.md](graph%20recommendations.md) | — | — | — |
| [grounding-provenance-write-time-links-proposal.md](grounding-provenance-write-time-links-proposal.md) | — | — | — |
| [hierarchical-topic-vocabulary-proposal.md](hierarchical-topic-vocabulary-proposal.md) | P3 | — | ACCEPTED 2026-07-26/27 (JNL, settled inline below) - not a JNL gate any more. Build order steps… |
| [hosted-edition-authority-amendment.md](hosted-edition-authority-amendment.md) | — | — | — |
| [interaction-frequency-ranking-plan.md](interaction-frequency-ranking-plan.md) | — | — | — |
| [lifecycle-link-authoring-assist-proposal.md](lifecycle-link-authoring-assist-proposal.md) | — | — | — |
| [link-sidecar-placement-review.md](link-sidecar-placement-review.md) | — | — | — |
| [memory-entry-trailer-plan.md](memory-entry-trailer-plan.md) | — | — | — |
| [memory-explorer-entry-level-ui-results-plan.md](memory-explorer-entry-level-ui-results-plan.md) | — | — | — |
| [memory-index-dry-run-plan.md](memory-index-dry-run-plan.md) | P1 | — | JNL decides whether to submit to Verging Labs v0.2 (early September) on Run 9's 87.1/CLEAR, zer… |
| [Memory-Seed Logic Capture Improvement.md](Memory-Seed%20Logic%20Capture%20Improvement.md) | — | — | — |
| [memory-seed-architectural-discovery-proposal.md](memory-seed-architectural-discovery-proposal.md) | — | — | — |
| [memory-seed-trace-upgrade-shutdown-plan.md](memory-seed-trace-upgrade-shutdown-plan.md) | — | — | — |
| [memory-seed-utf8-encoding-policy-phase-1.md](memory-seed-utf8-encoding-policy-phase-1.md) | — | — | — |
| [memory-trace-children-proposal.md](memory-trace-children-proposal.md) | P2 | — | DONE 2026-07-27 - 17 slugs live in .memory-seed/topics.yaml and 166 entries attributed via topi… |
| [memory-trace-distribution-plan.md](memory-trace-distribution-plan.md) | — | — | — |
| [memory-trace-plan-integration-and-retirement-guide.md](memory-trace-plan-integration-and-retirement-guide.md) | — | — | execution-guide |
| [memory-trace-product-and-trail-view-plan.md](memory-trace-product-and-trail-view-plan.md) | — | — | — |
| [memory-trace-topic-neighbourhoods-plan.md](memory-trace-topic-neighbourhoods-plan.md) | — | — | — |
| [memory-trace-ui-audit.md](memory-trace-ui-audit.md) | — | — | — |
| [memory-trail-graph-and-topic-neighbourhoods.md](memory-trail-graph-and-topic-neighbourhoods.md) | — | — | — |
| [memory-trail-renaming-plan.md](memory-trail-renaming-plan.md) | — | — | — |
| [mermaid-usage-guidance-plan.md](mermaid-usage-guidance-plan.md) | — | — | — |
| [multi-user-deep-research-report.md](multi-user-deep-research-report.md) | — | — | — |
| [multi-user-session-memory-proposal.md](multi-user-session-memory-proposal.md) | — | — | — |
| [openssf-credibility-proposals.md](openssf-credibility-proposals.md) | — | — | — |
| [operating-mode-variables-proposal.md](operating-mode-variables-proposal.md) | P2 | — | completed |
| [outcome-level-composition-constitutional-amendment.md](outcome-level-composition-constitutional-amendment.md) | — | — | — |
| [persona-usage-deactivation-esr-proposal.md](persona-usage-deactivation-esr-proposal.md) | — | — | — |
| [ponytail-implementation.md](ponytail-implementation.md) | — | — | — |
| [proactive-history-retrieval-discipline-proposal.md](proactive-history-retrieval-discipline-proposal.md) | — | — | — |
| [README Improvements.md](README%20Improvements.md) | — | — | — |
| [readme-front-door-refresh-plan.md](readme-front-door-refresh-plan.md) | — | — | — |
| [real-corpus-ranking-validation-gate-proposal.md](real-corpus-ranking-validation-gate-proposal.md) | — | — | — |
| [related-entries-generation-plan.md](related-entries-generation-plan.md) | — | — | — |
| [related-entries-p2-mutation-plan.md](related-entries-p2-mutation-plan.md) | — | — | None. link add shipped; historical backfill remains a deliberately manual, per-edge procedure r… |
| [residual-fuse-non-utf8-silent-skip.md](residual-fuse-non-utf8-silent-skip.md) | — | — | — |
| [residual-processes-cp1252-decode.md](residual-processes-cp1252-decode.md) | — | — | — |
| [resolve-stale-worktrees-and-decision-origins-plan.md](resolve-stale-worktrees-and-decision-origins-plan.md) | P1 | — | todo |
| [retrieval-specification-m0-m1-implementation-plan.md](retrieval-specification-m0-m1-implementation-plan.md) | P1 | — | None. M0-M1 landed on main; M2-M5 remain owned by the active declarative retrieval specificatio… |
| [risk-signaling-and-stop-triggers-plan.md](risk-signaling-and-stop-triggers-plan.md) | — | — | — |
| [session-decision-diagrams-plan.md](session-decision-diagrams-plan.md) | — | — | — |
| [stop-trigger-taxonomy-proposal.md](stop-trigger-taxonomy-proposal.md) | — | — | — |
| [storyline-gap-tranche-implementation-plan.md](storyline-gap-tranche-implementation-plan.md) | P1 | — | None — R5, R8, and R13 are reconciled from reviewed implementation evidence. |
| [structured-mermaid-d2-diagrams-skill-evaluation.md](structured-mermaid-d2-diagrams-skill-evaluation.md) | — | — | — |
| [superpowers-delivery-quality-uplift-plan.md](superpowers-delivery-quality-uplift-plan.md) | P1 | — | Use the behavioral evaluation corpus and real-work trials to measure future uplift without trea… |
| [supersession-edges-plan.md](supersession-edges-plan.md) | — | — | — |
| [supersession-successor-surfacing-proposal.md](supersession-successor-surfacing-proposal.md) | — | — | — |
| [test-suite-protection-value-audit.md](test-suite-protection-value-audit.md) | P3 | [] | Audit fully closed 2026-07-20 (content cull + the deferred structural split, both resolved). No… |
| [transitive-session-fusion-refinement-plan.md](transitive-session-fusion-refinement-plan.md) | P0 | [] | None. The reviewed transitive fuse evidence contract shipped on 2026-09-06. |
| [user-interface-deep-research-report.md](user-interface-deep-research-report.md) | — | — | — |
| [utf8-encoding-doctor-and-static-check-plan.md](utf8-encoding-doctor-and-static-check-plan.md) | — | — | — |
| [vocabulary-proposal-mode-proposal.md](vocabulary-proposal-mode-proposal.md) | P3 | — | SHIPPED 2026-07-27 (day after JNL raised it) - not a JNL gate any more. scripts/propose_topic_c… |
| [worker-context-minimisation-proposal.md](worker-context-minimisation-proposal.md) | — | — | — |
| [worktree-dependency-control-plane-source.md](worktree-dependency-control-plane-source.md) | — | — | refined-into-active-plan |
| [worktree-dependency-strategy-plan.md](worktree-dependency-strategy-plan.md) | — | — | — |
| [write-time-topic-envelope-closure-proposal.md](write-time-topic-envelope-closure-proposal.md) | P1 | — | none - accepted and implemented 2026-08-07; the topic swarm it unblocks is the next step |
<!-- docs-index:end -->
