# 7_Replaced — replaced, with a forward pointer

Documents that were valid but have been replaced by a newer one. Kept so the reasoning trail stays
intact; each points forward to what replaced it.

**Required YAML:** `superseded_by:` (doc path or session entry id), `superseded_on:`.

**Contents** (reclassified 2026-07-14):

- `claude-proposal-synergy-evaluation.md`, `codex-proposal-synergy-evaluation.md` — the two per-agent
  cross-proposal reviews (2.13-era snapshots). Every proposal they weighed has since shipped and both
  self-declare "no further research loop is open," so they are superseded by the shipped work plus the
  refreshed `2_Todo/0_NEXT_STEPS.md`.

The P2 migration (2026-07-17) moved the whole `2_Todo/completed/` archive into `5_Completed/` as-is and
retired the folder. Docs there marked "SOURCE RESOLVED / folded into <canonical>" may still deserve
reclassification into this lane — that is a per-doc judgement call, deliberately not folded into the
mechanical migration.

<!-- docs-index:begin -->
| Document | Priority | Blocked by | Next action / pointer |
|---|---|---|---|
| [agent-namespaced-branch-worktree-lifecycle-proposal.md](agent-namespaced-branch-worktree-lifecycle-proposal.md) | — | — | ../5_Completed/agent-worktree-and-branch-hygiene-plan.md |
| [agent-workflow-observability-exploration.md](agent-workflow-observability-exploration.md) | — | — | ../2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md |
| [benchmarking-decision-quality-exploration.md](benchmarking-decision-quality-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [capability-status-and-publishability-boundary-proposal.md](capability-status-and-publishability-boundary-proposal.md) | P3 | — | After React Trail parity, perform an explicit security/privacy review before deciding whether t… |
| [claude-proposal-synergy-evaluation.md](claude-proposal-synergy-evaluation.md) | — | — | shipped implementations of every evaluated proposal + `docs/2_Todo/0_NEXT_STEPS.md` (2026-07-14… |
| [codex-proposal-synergy-evaluation.md](codex-proposal-synergy-evaluation.md) | — | — | shipped implementations of every evaluated proposal + `docs/2_Todo/0_NEXT_STEPS.md` (2026-07-14… |
| [constitutional-principles-decision-efficiency-exploration.md](constitutional-principles-decision-efficiency-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [constitutional-principles-deterministic-agents-exploration.md](constitutional-principles-deterministic-agents-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [decision-supersession-and-evolution-exploration.md](decision-supersession-and-evolution-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [derived-review-queue-and-document-lineage-proposal.md](derived-review-queue-and-document-lineage-proposal.md) | P3 | — | After React Trail parity and the named prerequisite contracts, define deterministic fixtures fo… |
| [deterministic-context-assembly-exploration.md](deterministic-context-assembly-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [deterministic-sidecar-generation-exploration.md](deterministic-sidecar-generation-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [entry-intent-metadata-exploration.md](entry-intent-metadata-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [evidence-envelope-and-task-packet-reference-proposal.md](evidence-envelope-and-task-packet-reference-proposal.md) | P2 | — | After React Trail parity, decide whether a stable cross-surface evidence hand-off is needed; if… |
| [evidence-model-and-packets-exploration.md](evidence-model-and-packets-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [high-signal-knowledge-lenses-exploration.md](high-signal-knowledge-lenses-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [idea-to-ship-trace-model-exploration.md](idea-to-ship-trace-model-exploration.md) | — | — | ../2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md |
| [integrated-implementation-sequence-exploration.md](integrated-implementation-sequence-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [memory-seed-ontology-evidence-set-index-exploration.md](memory-seed-ontology-evidence-set-index-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [memory-seed-ontology-exploration.md](memory-seed-ontology-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [memory-seed-relevance-set-index-exploration.md](memory-seed-relevance-set-index-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [memory-seed-semantic-workflow-exploration-index.md](memory-seed-semantic-workflow-exploration-index.md) | — | — | mse_ddba1ztxqhasfbwf |
| [memory-seed-typed-entries-adr-sidecar-proposal.md](memory-seed-typed-entries-adr-sidecar-proposal.md) | — | — | ../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md |
| [memory-signal-hierarchy-exploration.md](memory-signal-hierarchy-exploration.md) | — | — | ../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md |
| [seeded-document-lifecycle-control-plane-proposal.md](seeded-document-lifecycle-control-plane-proposal.md) | — | — | ../2_Todo/document-lifecycle-system-plan.md |
| [sidecar-lens-architecture-exploration.md](sidecar-lens-architecture-exploration.md) | — | — | ../4_Reference/INBOX-CAPABILITY-CROSSWALK.md |
| [type-specific-trace-projections-exploration.md](type-specific-trace-projections-exploration.md) | — | — | ../2_Todo/memory-trace-semantic-projections-plan.md |
| [worktree-gc-proposal.md](worktree-gc-proposal.md) | — | — | ../5_Completed/agent-worktree-and-branch-hygiene-plan.md |
<!-- docs-index:end -->
