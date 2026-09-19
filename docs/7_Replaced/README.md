# 7_Replaced — replaced, with a forward pointer

Documents that were valid but have been replaced by a newer one. Kept so the reasoning trail stays
intact; each points forward to what replaced it.

**Required YAML:** `superseded_by:` (doc path or session entry id), `superseded_on:`.

**Contents** (reclassified 2026-07-14):

- `claude-proposal-synergy-evaluation.md`, `codex-proposal-synergy-evaluation.md` — the two per-agent
  cross-proposal reviews (2.13-era snapshots). Every proposal they weighed has since shipped and both
  self-declare "no further research loop is open," so they are superseded by the shipped work plus the
  refreshed `2_Todo/0_NEXT_STEPS.md`.
- `harness-engineering-comparison-claude.md`, `harness-engineering-comparison-codex.md` — the two
  parallel OpenAI harness-engineering comparison lines (2026-08-13), retired 2026-08-21 once
  `1_Inbox/memory-seed-harness-gap-opportunity-report.md` was confirmed to already fold both lines'
  unique contributions into one opportunity register.

The P2 migration (2026-07-17) moved the whole `2_Todo/completed/` archive into `5_Completed/` as-is and
retired the folder. Docs there marked "SOURCE RESOLVED / folded into <canonical>" may still deserve
reclassification into this lane — that is a per-doc judgement call, deliberately not folded into the
mechanical migration.

<!-- docs-index:begin -->
| Document | Priority | Blocked by | Next action / pointer |
|---|---|---|---|
| [adjudication-queue.md](adjudication-queue.md) | P2 | — | JNL to rule each row; the rulings become the project's only validity ground truth. |
| [agent-namespaced-branch-worktree-lifecycle-proposal.md](agent-namespaced-branch-worktree-lifecycle-proposal.md) | — | — | ../5_Completed/agent-worktree-and-branch-hygiene-plan.md |
| [agent-workflow-observability-exploration.md](agent-workflow-observability-exploration.md) | — | — | ../7_Replaced/memory-seed-workflow-evidence-and-review-workbench-plan.md |
| [attention-retrieval-signal-proposal.md](attention-retrieval-signal-proposal.md) | P2 | — | Accumulate real MCP usage, then run `memory-seed ranking-ab --signal attention --query ...` bef… |
| [benchmarking-decision-quality-exploration.md](benchmarking-decision-quality-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [capability-status-and-publishability-boundary-proposal.md](capability-status-and-publishability-boundary-proposal.md) | P3 | — | After React Trail parity, perform an explicit security/privacy review before deciding whether t… |
| [claude-proposal-synergy-evaluation.md](claude-proposal-synergy-evaluation.md) | — | — | shipped implementations of every evaluated proposal + `docs/2_Todo/0_NEXT_STEPS.md` (2026-07-14… |
| [codex-proposal-synergy-evaluation.md](codex-proposal-synergy-evaluation.md) | — | — | shipped implementations of every evaluated proposal + `docs/2_Todo/0_NEXT_STEPS.md` (2026-07-14… |
| [constitutional-principles-decision-efficiency-exploration.md](constitutional-principles-decision-efficiency-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [constitutional-principles-deterministic-agents-exploration.md](constitutional-principles-deterministic-agents-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [decision-supersession-and-evolution-exploration.md](decision-supersession-and-evolution-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [declarative-retrieval-specification-proposal.md](declarative-retrieval-specification-proposal.md) | P1 | [] | Keep the delivered M0-M3 retrieval and Task Packet contracts stable; design M4 Trace/Evidence E… |
| [derived-review-queue-and-document-lineage-proposal.md](derived-review-queue-and-document-lineage-proposal.md) | P3 | — | After React Trail parity and the named prerequisite contracts, define deterministic fixtures fo… |
| [deterministic-context-assembly-exploration.md](deterministic-context-assembly-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [deterministic-sidecar-generation-exploration.md](deterministic-sidecar-generation-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [entry-intent-metadata-exploration.md](entry-intent-metadata-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [evidence-envelope-and-task-packet-reference-proposal.md](evidence-envelope-and-task-packet-reference-proposal.md) | P2 | — | After React Trail parity, decide whether a stable cross-surface evidence hand-off is needed; if… |
| [evidence-model-and-packets-exploration.md](evidence-model-and-packets-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [file-touch-decision-surfacing-proposal.md](file-touch-decision-surfacing-proposal.md) | P2 | — | Observe the hook in real sessions; extend to Codex/Gemini/Cursor events when their PostToolUse … |
| [harness-engineering-comparison-claude.md](harness-engineering-comparison-claude.md) | — | — | ../1_Inbox/memory-seed-harness-gap-opportunity-report.md |
| [harness-engineering-comparison-codex.md](harness-engineering-comparison-codex.md) | — | — | ../1_Inbox/memory-seed-harness-gap-opportunity-report.md |
| [high-signal-knowledge-lenses-exploration.md](high-signal-knowledge-lenses-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [idea-to-ship-trace-model-exploration.md](idea-to-ship-trace-model-exploration.md) | — | — | ../7_Replaced/memory-seed-workflow-evidence-and-review-workbench-plan.md |
| [independent-validation-brief.md](independent-validation-brief.md) | P1 | — | Hand this file to an agent that has not worked on Memory Seed's experiments; it derives its own… |
| [information-theoretic-evolution-exploration.md](information-theoretic-evolution-exploration.md) | — | — | ../4_Reference/information-theoretic-evolution-disposition.md |
| [integrated-implementation-sequence-exploration.md](integrated-implementation-sequence-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [link-audit-decision-judgment-swarm-proposal.md](link-audit-decision-judgment-swarm-proposal.md) | P2 | — | Batching and retention are shipped. Design the broader vendor-neutral queue orchestration aroun… |
| [memory-provenance-and-authority-taxonomy-proposal.md](memory-provenance-and-authority-taxonomy-proposal.md) | P1 | — | Steps 5–6 (GATED on the participant/role model + a user go): implement actionability as a polic… |
| [memory-seed-ontology-evidence-set-index-exploration.md](memory-seed-ontology-evidence-set-index-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [memory-seed-ontology-exploration.md](memory-seed-ontology-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [memory-seed-relevance-set-index-exploration.md](memory-seed-relevance-set-index-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [memory-seed-semantic-record-and-signal-foundation-plan.md](memory-seed-semantic-record-and-signal-foundation-plan.md) | P1 | — | Evaluate the remaining record_kind and retrieval-signal work after the provenance and quality g… |
| [memory-seed-semantic-workflow-exploration-index.md](memory-seed-semantic-workflow-exploration-index.md) | — | — | mse_ddba1ztxqhasfbwf |
| [memory-seed-typed-entries-adr-sidecar-proposal.md](memory-seed-typed-entries-adr-sidecar-proposal.md) | — | — | ../7_Replaced/memory-seed-semantic-record-and-signal-foundation-plan.md |
| [memory-seed-workflow-evidence-and-review-workbench-plan.md](memory-seed-workflow-evidence-and-review-workbench-plan.md) | P2 | — | Reconstruct three completed project journeys from existing entries, documents, and Git referenc… |
| [memory-signal-hierarchy-exploration.md](memory-signal-hierarchy-exploration.md) | — | — | ../7_Replaced/memory-seed-semantic-record-and-signal-foundation-plan.md |
| [memory-trace-evidence-annotations-and-projection-architecture.md](memory-trace-evidence-annotations-and-projection-architecture.md) | — | — | proposed |
| [memory-trace-frontend-architecture-and-design-system-proposal.md](memory-trace-frontend-architecture-and-design-system-proposal.md) | — | — | proposed |
| [memory-trace-graph-and-workspace-proposal-set-index.md](memory-trace-graph-and-workspace-proposal-set-index.md) | P1 | — | promoted-to-todo |
| [memory-trace-graph-visualisation-and-temporal-topology-proposal.md](memory-trace-graph-visualisation-and-temporal-topology-proposal.md) | P1 | — | promoted-to-todo |
| [memory-trace-hosted-product-and-security-architecture.md](memory-trace-hosted-product-and-security-architecture.md) | — | — | — |
| [memory-trace-next-generation-coverage-matrix.md](memory-trace-next-generation-coverage-matrix.md) | — | — | active-integration-matrix |
| [memory-trace-next-generation-implementation-roadmap.md](memory-trace-next-generation-implementation-roadmap.md) | — | — | proposed |
| [memory-trace-product-and-system-architecture-blueprint.md](memory-trace-product-and-system-architecture-blueprint.md) | — | — | proposed-canonical-plan |
| [memory-trace-three-region-workspace-and-dockable-inspector-proposal.md](memory-trace-three-region-workspace-and-dockable-inspector-proposal.md) | P1 | — | promoted-to-todo |
| [plan-reflection-ledger.md](plan-reflection-ledger.md) | P1 | — | Documentary evidence only. Do not compile or launch these prototype dispatches; use the sequent… |
| [reflection-ledger-workstream-evolution-plan.md](reflection-ledger-workstream-evolution-plan.md) | P1 | — | Complete integrated launch verification and first-board evaluation; track public retention-exte… |
| [reflection-prototype-retirement-plan.md](reflection-prototype-retirement-plan.md) | P1 | — | Verify the retired prototype stays absent in the integrated launch matrix and first-board evalu… |
| [seeded-document-lifecycle-control-plane-proposal.md](seeded-document-lifecycle-control-plane-proposal.md) | — | — | ../5_Completed/document-lifecycle-system-plan.md |
| [sidecar-lens-architecture-exploration.md](sidecar-lens-architecture-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [topic-vocabulary-concentration-review.md](topic-vocabulary-concentration-review.md) | P2 | — | SUPERSEDED 2026-07-26 as to remedy - the measurements here stand, but the flat splits recommend… |
| [type-specific-trace-projections-exploration.md](type-specific-trace-projections-exploration.md) | — | — | ../8_Deferred/memory-trace-semantic-projections-plan.md |
| [worktree-gc-proposal.md](worktree-gc-proposal.md) | — | — | ../5_Completed/agent-worktree-and-branch-hygiene-plan.md |
| [write-time-sidecar-consolidation-proposal.md](write-time-sidecar-consolidation-proposal.md) | P2 | — | M1 topics-and-links transaction is in progress on `codex/feature/decision-sidecar-transaction`;… |
<!-- docs-index:end -->
