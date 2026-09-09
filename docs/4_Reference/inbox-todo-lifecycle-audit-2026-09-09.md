---
title: Inbox and Todo proposal lifecycle audit — 2026-09-09
status: reference
reviewed_scope: "docs/1_Inbox/*.md and docs/2_Todo/*.md, excluding lane indexes and 0_NEXT_STEPS.md as work items"
---

# Inbox and Todo proposal lifecycle audit — 2026-09-09

## Result

This read-and-reconcile audit covered every direct Markdown work item in `docs/1_Inbox/` (9) and
`docs/2_Todo/` (45). It used current lane contents, frontmatter and next actions, the existing
2026-09-08 Todo audit, targeted session decisions, decision-level lifecycle links where relevant,
and narrow current-code checks for claims of shipped behavior.

- **Inbox retained: 9.** No Inbox item has an explicit promote, reject, replace, defer, or reference
  disposition that overrides the recorded open review or user exception.
- **Todo retained: 45.** Each still owns live work, an explicit gate, a partial implementation with
  an open remainder, or an unresolved user decision.
- **Moves made in this pass: 0.** The prior ten Completed moves and one Replaced move are already
  present on `main` (see the 2026-09-08 audit and `mse_j6bqhepzg8b1p4rs`). No content was deleted,
  duplicated, or reclassified on weaker evidence.
- **Index repair:** lane indexes and front-door counts were checked against current `main`; the Inbox
  prose was corrected to account for the two September 8 captures and the living-document exception.
- **Roadmap navigation cleanup:** `docs/2_Todo/0_NEXT_STEPS.md` was reduced from 1363 lines / 107,880
  bytes to a 131-line / 7,421-byte route. It now separates ready next actions, dependency-blocked
  programmes, unresolved user decisions, the grouped Trace backlog, and the separately owned
  Superpowers plan. `docs/2_Todo/README.md` now points readers to that route while retaining its
  generated complete metadata table for lookup. Full proposal detail and shipped-phase history remain
  in the source plans and existing `CHANGELOG.md`; the root changelog was not relocated.

## Inbox

| Original document | Outcome | Evidence / decision refs | Destination or why retained |
|---|---|---|---|
| `1_Inbox/active-truth-execution-control-proposal.md` | Retain, unassessed | `4_Reference/INBOX-ASSESSMENT-2026-08-20-DROP.md`; assessment isolates possible gaps but explicitly applies no disposition | Remains Inbox pending an explicit decision; do not infer rejection from the assessment's recommendation against building it as submitted. |
| `1_Inbox/memory-seed-first-principles-proposal.md` | Retain, unassessed | `4_Reference/INBOX-ASSESSMENT-2026-08-20-DROP.md` | Remains Inbox; strategic input is not an accepted engineering plan and no user disposition is recorded. |
| `1_Inbox/memory-seed-governed-interactive-retrieval-proposal.md` | Retain, unassessed | `4_Reference/INBOX-ASSESSMENT-2026-08-20-DROP.md` | Remains Inbox; assessment calls it a scoped candidate but does not promote it. |
| `1_Inbox/memory-seed-evidence-first-governed-retrieval-plan.md` | Retain, review-pending | `mse_qg9p71qx57rtq99n`; `mse_a1hemwzpbeqxq6t5` | Remains Inbox because it was explicitly captured for user review and later reconciled with semantic-compression work; no promotion or rejection decision is recorded. |
| `1_Inbox/semantic-compression-benchmark-proposal.md` | Retain, narrowed by evidence | `4_Reference/INBOX-ASSESSMENT-2026-08-20-DROP.md`; `mse_kxhnmwzb9w0dw21y`; `mse_a1hemwzpbeqxq6t5` | The automatic-compression benchmark and diagnostics are complete and archived under `experiments/semantic-compression/`; only the separately gated natural-authoring study remains, so the proposal stays Inbox rather than being marked complete or rejected. |
| `1_Inbox/memory-seed-harness-gap-opportunity-report.md` | Retain, unassessed register | `4_Reference/INBOX-ASSESSMENT-2026-08-13-DROP.md`; `mse_ask8e72zq76fdm9f` | Remains Inbox until the O1–O10 register and its proposed sequence receive an explicit disposition. |
| `1_Inbox/agent-interaction-storylines-review.md` | Retain by explicit exception | Inbox README; `mse_vjb1kgdq26c5b38y`, `mse_spn9wdhjasq6r344` | Remains Inbox as a living review synchronized with shipped behavior; this is not an untriaged capture. |
| `1_Inbox/reflection-board-cumulative-handoff-and-decision-harvest-proposal.md` | Retain, unassessed | `mse_j6bqhepzg8b1p4rs` D2 explicitly captures it as an unassessed Inbox proposal | Remains Inbox pending assessment against the current v1 transaction contract. |
| `1_Inbox/adr-ledger-evolution-and-reasoning-semantics-plan.md` | Retain, review-gated | `mse_jt93a64rsc17bdas` D1 explicitly requires independent semantic/current-main review before promotion or implementation | Remains Inbox; the stale v3 branch is evidence only, not a completed or superseding implementation. |

The lane's generated `README.md` index is a control document, not a proposal; it stays in place and
is updated only through the marker-scoped index mechanism. The nine proposal rows above account for
all direct Inbox work items.

## Todo — retained active or unresolved work

The following 45 documents remain in `2_Todo/`. The shared evidence baseline is
`docs/4_Reference/todo-lifecycle-audit-2026-09-08.md` and its receipt-bearing session entry
`mse_j6bqhepzg8b1p4rs`; each row was checked against its current next action, blocked-by field, and
any explicit shipped/remaining-scope statement. A partial first phase does not move a document when
the same document still owns an explicit follow-up.

| Original document | Outcome | Evidence / why retained |
|---|---|---|
| `2_Todo/seed-pod-p0-reconciliation-plan.md` | Retain active | P0 G0 re-review and provenance migration remain gated; Reflection launch evidence is a prerequisite, not completion. |
| `2_Todo/task-packet-hardening-progressive-provenance-plan.md` | Retain active | P0 hardening and progressive provenance work remain in the current next action. |
| `2_Todo/declarative-retrieval-specification-proposal.md` | Retain active | M0–M3 are delivered, but M4/M5 design remains explicit. |
| `2_Todo/derived-projection-implementation-plan.md` | Retain partial | Phase 1 and incremental ingest shipped; git-rooted integrity follow-up remains. |
| `2_Todo/independent-validation-brief.md` | Retain open | Independent agent validation is still the next action. |
| `2_Todo/memory-index-dry-run-plan.md` | Retain decision-gated | Run 9 is evidence, but submission and unresolved S4/S6 usefulness decisions remain. |
| `2_Todo/memory-provenance-and-authority-taxonomy-proposal.md` | Retain gated | Steps 1–4 shipped; steps 5–7 remain behind participant/role and maintainer approval gates. |
| `2_Todo/memory-quality-metrics-v0-proposal.md` | Retain review-gated | v0 baseline shipped; usefulness review and any graduation decision remain. |
| `2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md` | Retain active | Remaining record-kind and retrieval-signal work is explicitly owned here. |
| `2_Todo/memory-seed-workflow-evidence-and-review-workbench-plan.md` | Retain active | Three real project journeys must be reconstructed before defining the workbench fixture. |
| `2_Todo/memory-trace-ai-timeline-summarisation-plan.md` | Retain active | Optional provider remains disabled-by-default and is sequenced after packaging/release gates. |
| `2_Todo/memory-trace-children-proposal.md` | Retain partial | Topic slugs/attribution shipped; activity and validity work remain open. |
| `2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md` | Retain proposed | Versioned API, Trail/search parity, and annotation architecture remain proposed work. |
| `2_Todo/memory-trace-frontend-architecture-and-design-system-proposal.md` | Retain proposed | Frontend architecture remains a proposal with explicit prerequisites. |
| `2_Todo/memory-trace-graph-and-workspace-proposal-set-index.md` | Retain active set | Proposal-set index remains the owner for the related Graph/Workspace documents. |
| `2_Todo/memory-trace-graph-visualisation-and-temporal-topology-proposal.md` | Retain proposed | Graph topology and visual semantics remain roadmap work. |
| `2_Todo/memory-trace-living-archive-and-editorial-focus-proposal.md` | Retain partial | Community Decision Brief slice is approved, while naming/commercial and other sections remain parked or gated. |
| `2_Todo/memory-trace-next-generation-coverage-matrix.md` | Retain active matrix | Matrix remains the integration/planning authority for the next-generation Trace set. |
| `2_Todo/memory-trace-next-generation-implementation-roadmap.md` | Retain proposed roadmap | Roadmap sequencing remains the next-generation planning source. |
| `2_Todo/memory-trace-product-and-system-architecture-blueprint.md` | Retain canonical plan | Blueprint remains the P0 planning entry point before the next-generation implementation. |
| `2_Todo/memory-trace-semantic-projections-plan.md` | Retain active | Decision projection validation remains gated on B0b and semantic foundation evidence. |
| `2_Todo/memory-trace-structural-graph-enrichment-provider-proposal.md` | Retain proposed | Provider adoption remains fixture/benchmark-gated. |
| `2_Todo/memory-trace-three-region-workspace-and-dockable-inspector-proposal.md` | Retain proposed | Workspace composition remains a proposed Trace surface. |
| `2_Todo/memory-trace-ux-m0-interaction-matrix.md` | Retain active | M3 bounded graph perspectives and controlled expansion remain the next action. |
| `2_Todo/memory-trace-ux-reference-model-implementation-plan.md` | Retain active | Same M3 implementation remains explicitly owned here. |
| `2_Todo/openssf-credibility-proposals.md` | Retain partial | In-repo slice shipped; external security-setting/user action and remaining credibility work remain. |
| `2_Todo/ranking-ab-unit-change-gate-proposal.md` | Retain proposed | Whether a unit-change gate is needed remains undecided. |
| `2_Todo/reflection-ledger-workstream-evolution-plan.md` | Retain partial | v1 public lifecycle and first real closed board now exist, but the plan still owns integrated launch/retention-extension follow-up. |
| `2_Todo/reflection-prototype-retirement-plan.md` | Retain partial | Prototype retirement shipped; integrated launch-matrix verification remains explicit. |
| `2_Todo/retrieval-recall-fixes-proposal.md` | Retain proposed | Lifecycle-label derivation and held-out recall work remain unimplemented. |
| `2_Todo/session-decision-diagrams-plan.md` | Retain proposed | Diagram sidecar workflow remains a live plan. |
| `2_Todo/sidecar-editable-lens-refinement-proposal.md` | Retain narrowed | Append-only blocked-entry case is solved; true in-place diagram/link editing still awaits a shape decision. |
| `2_Todo/skillopt-fit-analysis.md` | Retain proposal | Analysis remains unaccepted and identifies external-provider/control-plane risks. |
| `2_Todo/superpowers-collaboration-integration-proposal.md` | Retain active | Phase 0 routing and first suitable approved multi-task trial remain the next action; a separate user-owned plan is out of scope here. |
| `2_Todo/task-packet-calibration-harness-plan.md` | Retain active | Representative population and sealed holdout design remain open. |
| `2_Todo/write-time-sidecar-consolidation-proposal.md` | Retain partial | Accepted writer tranche is in progress; diagrams/ADR lenses/parsed fusion fixtures remain. |
| `2_Todo/adjudication-queue.md` | Retain decision queue | JNL rulings are explicitly still required. |
| `2_Todo/adr-attached-decisions-earn-a-diagram-proposal.md` | Retain gated | Accepted direction remains blocked on ADR backlog and unresolved attachment/write-time questions. |
| `2_Todo/attention-retrieval-signal-proposal.md` | Retain partial | Capture/exposure shipped; default-ranking flip remains gated on real usage and ranking A/B evidence. |
| `2_Todo/decision-level-topics-proposal.md` | Retain gated | Inference remains behind the decision-level graph and the declared-attribution design. |
| `2_Todo/document-lifecycle-system-plan.md` | Retain partial | Migration, docs check, and docs index shipped; secondary-YAML backfill remains. |
| `2_Todo/file-touch-decision-surfacing-proposal.md` | Retain partial | Claude hook shipped; other-agent observation and extension remain deferred. |
| `2_Todo/hierarchical-topic-vocabulary-proposal.md` | Retain partial | Core build shipped; project-type starter vocabulary still needs a maintainer call. |
| `2_Todo/lifecycle-link-authoring-assist-proposal.md` | Retain partial | Steps 1–3 shipped; optional authoring extensions remain. |
| `2_Todo/link-audit-decision-judgment-swarm-proposal.md` | Retain active | Batching/retention shipped; vendor-neutral queue/controller orchestration remains. |

### Exact filename evidence ledger

The following is the latest exact filename-bearing `F:` decision match found for each Todo document
(searched before relying on the live document's metadata). These references establish the most recent
recorded work touching the path; the outcome column above is based on the document's observed
remaining scope, not on a stale `next_action` field alone. A shipped slice therefore remains retained
when the same document still names an open remainder or gate.

| Todo document | Latest exact `F:` decision match |
|---|---|
| `adjudication-queue.md` | `mse_xvvswqb4n3zcwbcq` (2026-08-14) |
| `adr-attached-decisions-earn-a-diagram-proposal.md` | `mse_g3r6ba77w23c1y3w` (2026-08-26) |
| `attention-retrieval-signal-proposal.md` | `mse_57e1ek08qq9smwv3` (2026-08-05) |
| `decision-level-topics-proposal.md` | `mse_xc3f1we7p4808mra` (2026-07-26) |
| `declarative-retrieval-specification-proposal.md` | `mse_b7rhhtfx01cafwke` (2026-09-01) |
| `derived-projection-implementation-plan.md` | `mse_c70ze3saqsw6mcme` (2026-07-15) |
| `document-lifecycle-system-plan.md` | `mse_ntkt6m0pqd0g8c9j` (2026-07-17) |
| `file-touch-decision-surfacing-proposal.md` | `mse_xhmnrwf8yxjcspeb` (2026-08-04) |
| `hierarchical-topic-vocabulary-proposal.md` | `mse_g3r6ba77w23c1y3w` (2026-08-26) |
| `independent-validation-brief.md` | `mse_xvvswqb4n3zcwbcq` (2026-08-14) |
| `lifecycle-link-authoring-assist-proposal.md` | `mse_v26pem9hsvsbjbge` (2026-07-16) |
| `link-audit-decision-judgment-swarm-proposal.md` | `mse_h297nf3qghp7ysyk` (2026-07-24) |
| `memory-index-dry-run-plan.md` | `mse_ht4mgktz806d7m10` (2026-09-01) |
| `memory-provenance-and-authority-taxonomy-proposal.md` | `mse_9xfpvhqrm44jedce` (2026-07-17) |
| `memory-quality-metrics-v0-proposal.md` | `mse_9cx2d9g233vz4xhq` (2026-08-13) |
| `memory-seed-semantic-record-and-signal-foundation-plan.md` | `mse_2geqfa8tg182a77p` (2026-07-20) |
| `memory-seed-workflow-evidence-and-review-workbench-plan.md` | `mse_ddba1ztxqhasfbwf` (2026-07-16) |
| `memory-trace-ai-timeline-summarisation-plan.md` | `mse_v26pem9hsvsbjbge` (2026-07-16) |
| `memory-trace-children-proposal.md` | `mse_4pz7vzgh7jrwedq2` (2026-07-27) |
| `memory-trace-evidence-annotations-and-projection-architecture.md` | `mse_ddba1ztxqhasfbwf` (2026-07-16) |
| `memory-trace-frontend-architecture-and-design-system-proposal.md` | `mse_tttwp31gjv8g409d` (2026-07-20) |
| `memory-trace-graph-and-workspace-proposal-set-index.md` | `mse_a0bxp5n1wcnsjxvw` (2026-07-15) |
| `memory-trace-graph-visualisation-and-temporal-topology-proposal.md` | `mse_pkd8hbh3qbbahydn` (2026-07-30) |
| `memory-trace-living-archive-and-editorial-focus-proposal.md` | `mse_2geqfa8tg182a77p` (2026-07-20) |
| `memory-trace-next-generation-coverage-matrix.md` | `mse_r6tyarbkzz18st4w` (2026-07-31) |
| `memory-trace-next-generation-implementation-roadmap.md` | `mse_mazbt6cek8m8a6st` (2026-07-16) |
| `memory-trace-product-and-system-architecture-blueprint.md` | `mse_a0bxp5n1wcnsjxvw` (2026-07-15) |
| `memory-trace-semantic-projections-plan.md` | `mse_ddba1ztxqhasfbwf` (2026-07-16) |
| `memory-trace-structural-graph-enrichment-provider-proposal.md` | `mse_a0bxp5n1wcnsjxvw` (2026-07-15) |
| `memory-trace-three-region-workspace-and-dockable-inspector-proposal.md` | `mse_a0bxp5n1wcnsjxvw` (2026-07-15) |
| `memory-trace-ux-m0-interaction-matrix.md` | `mse_r6tyarbkzz18st4w` (2026-07-31) |
| `memory-trace-ux-reference-model-implementation-plan.md` | `mse_r6tyarbkzz18st4w` (2026-07-31) |
| `openssf-credibility-proposals.md` | `mse_ksp4agbh7rpn21wq` (2026-07-17) |
| `ranking-ab-unit-change-gate-proposal.md` | `mse_fvqs26sdqbvcem9r` (2026-08-05) |
| `reflection-ledger-workstream-evolution-plan.md` | `mse_d4cqp1pkqr6qr2m4` (2026-09-07) |
| `reflection-prototype-retirement-plan.md` | `mse_d4cqp1pkqr6qr2m4` (2026-09-07) |
| `retrieval-recall-fixes-proposal.md` | `mse_dka59wfne2be5fr0` (2026-08-05) |
| `seed-pod-p0-reconciliation-plan.md` | `mse_arj9sav2yzmqrh00` (2026-09-09) |
| `session-decision-diagrams-plan.md` | `mse_gyrdzvd2wj3qhj51` (2026-07-13) |
| `sidecar-editable-lens-refinement-proposal.md` | `mse_zq69mbr57qnppm36` (2026-07-26) |
| `skillopt-fit-analysis.md` | `mse_eap4caz71kggmf7h` (2026-07-30) |
| `superpowers-collaboration-integration-proposal.md` | `mse_hbcz7yz5q4yhqwsx` (2026-07-29) |
| `task-packet-calibration-harness-plan.md` | `mse_a58avhtbcy9djpa0` (2026-09-01) |
| `task-packet-hardening-progressive-provenance-plan.md` | `mse_6npe4ys5j6gfj89s` (2026-09-05) |
| `write-time-sidecar-consolidation-proposal.md` | `mse_ddeat5w29spep3qw` (2026-07-30) |

## Previously resolved documents already moved on `main`

The audit did not repeat these moves because they are already in their terminal lanes:

- **Completed (10):** `branch-field-provenance.md`, `evolution-type-refines-builds-on-proposal.md`,
  `excerpt-fallback-defect.md`, `storyline-gap-tranche-implementation-plan.md`,
  `test-suite-protection-value-audit.md`, `related-entries-p2-mutation-plan.md`,
  `retrieval-specification-m0-m1-implementation-plan.md`, `transitive-session-fusion-refinement-plan.md`,
  `vocabulary-proposal-mode-proposal.md`, `write-time-topic-envelope-closure-proposal.md`.
- **Replaced (1):** `topic-vocabulary-concentration-review.md`, replaced by the hierarchical vocabulary
  proposal; its measurements remain in `docs/7_Replaced/`.

These are corroborated by `docs/4_Reference/todo-lifecycle-audit-2026-09-08.md`, the receipt-bearing
session entry `mse_j6bqhepzg8b1p4rs`, and the current Git tree. No duplicate source remains in `2_Todo/`.

## Verification

- Current direct-work-item inventory: 9 Inbox, 45 Todo.
- `docs check`: passed with 14 pre-existing incomplete-Todo metadata warnings and no lifecycle errors.
- `docs index --check`: the generated index update is pending because the inherited OneDrive ACL
  denied the CLI's write to `docs/4_Reference/README.md`; the existing index was current before this
  new report was added. The Inbox lane README was repaired directly.
- `links check`: completed after the two navigation session entries; the required date sweep added two
  inert `classify_pending` stubs. The repository still reports three pre-existing session duplicate-ID
  errors and numerous pre-existing lifecycle/sidecar warnings. No dangling-link error for the audit,
  Next Steps, or Inbox README paths was observed.
- `git diff --check`: passed.
- All proposal contents were preserved; no `git rm`, broad archival, or blanket terminal move was used.
