# Next Steps

Status: **ACTIVE — navigation and sequencing guide**
Updated: 2026-09-23

The hosted Memory Seed programme is now the primary product workstream. The local OSS edition remains
complete and Markdown-authoritative; the separate hosted edition will be SQL-authoritative and expose a
complete Markdown export. The two editions share semantics, not writable persistence.

## Tranche entry gate — design discovery first

This document is a high-level sequence, not an implementation specification. At the start of **every new
tranche of work in this roadmap**, the agent must automatically open a dedicated design discovery
conversation with JNL before doing implementation work for that tranche. This applies even when a linked
proposal or the hosted programme already contains substantial detail. Do not infer that an earlier tranche
answered the new tranche's questions.

The discovery conversation should actively test assumptions and ask targeted, probing questions about the
user outcome, current workflow, data and evidence access, affected users and permissions, design options,
constraints, failure cases, privacy and governance, dependencies, evaluation, and measurable acceptance
criteria. It should identify decisions that only JNL can make, document answers and open questions, then
produce a bounded, tranche-specific implementation plan for review. Begin that tranche's implementation
only after the detailed design and unresolved choices have been settled with JNL. Keep subsequent work
within the agreed tranche scope; repeat discovery when a materially new tranche starts.

## Hosted roadmap

1. **P0.1 authority — integrated.** Constitution v2.0, the edition contract, ADR evolution, and
   lifecycle consolidation form the baseline for the [Hosted Memory MVP Programme](hosted-memory-mvp-programme.md).
2. **P0.2 capture feasibility — discovery in progress.** Follow the [bounded tranche plan](codex-capture-feasibility-plan.md) to use synthetic data to prove Codex event access, authenticated identity,
   ordering and replay, pause/queue behavior, and approval delivery. Hosted code lives in a self-contained
   top-level `hosted/` folder for local development only. It is excluded from the published package (see the
   [repository boundary](hosted-memory-mvp-programme.md#repository-boundary)).
3. **P0.3–P0.4 useful loop.** Build the minimum authenticated SQL event/curated-memory substrate, then capture
   one user decision and return one evidence-linked record to an authorized team member over MCP. Prove
   permission-filtered retrieval and provider fail-closed behavior.
4. **P1 curator quality and team readiness.** Run the [decision-layer model tournament](decision-layer-model-tournament-plan.md)
   on reviewed labels: Model2Vec + Logistic Regression, Model2Vec + XGBoost, and SetFit are fixed-schema
   baselines, with generalized candidates tested by task. Dynamic Area/Activity assignment needs the current
   candidate hierarchy and independent-project evaluation; the local corpus alone cannot prove transfer.
   Select a model only after calibration, abstention, high-risk error, privacy, latency, and cost gates. Add
   guarded replacement/approval, branch applicability, retention/export, and retrieval parity for a team pilot.
5. **P2 experience.** Consider focused Trace and
   [decision storyline retrieval](../8_Deferred/decision-storyline-retrieval-proposal.md) once the service loop works.
   A [persistent Laya worker](../8_Deferred/laya-local-decision-worker-proposal.md) remains deferred until
   task-specific tournament results and measured queue load justify it.

No hosted service, provider call, upload, paid trial, release, or remote-setting change is authorized by
the documentation amendment alone.

## Open decisions by tranche

Each tranche's design discovery must settle these open decisions before its implementation starts. The
[programme's open decisions](hosted-memory-mvp-programme.md#open-decisions) hold the full wording.

- **P0.2:** the Codex capture discovery choices in the
  [tranche plan](codex-capture-feasibility-plan.md#design-discovery-decisions-for-jnl). The spike must also
  verify two policies settled on 2026-09-23: that Codex can show a human-confirmed approval prompt (otherwise
  use the signed-page fallback), and that it separates user input from agent and tool items (otherwise every
  replacement stays pending).
- **P1.5:** provider thresholds.
- **P0.2, P0.4, P1.5:** weigh the carried elements of the
  [atomic facts and decisions report](../4_Reference/atomic-facts-and-decisions-report.md), listed in the
  [programme](hosted-memory-mvp-programme.md#carry-into-tranche-discovery-atomic-facts-and-decisions).
  The Fact kind and premise tracking are [deferred](../8_Deferred/fact-items-and-premise-tracking-proposal.md).
- **P1.6:** automatic versus batch-approved merge adoption.
- **P1.7:** backup expiry and content purge, secret/oversize handling, and the default for sharing excerpts.
- **P1.8:** the numerical end-to-end p95 target, chosen from measured workloads.

Settled in the 2026-09-23 hosted design discovery
([summary](hosted-memory-mvp-programme.md#resolved-in-the-2026-09-23-design-discovery)):
- P0.3: PostgreSQL, one shared schema with row-level security, a local server through P0.4 and managed
  PostgreSQL for the pilot, and GitHub OAuth device flow.
- P0.4: curated records are shared by default, raw evidence is visible only to its owner, decisions change
  through the lifecycle, and removal is a last resort that leaves a tombstone.
- P1.5: the prose writer is evaluated in a writer track of the tournament.

## Local OSS obligations that remain active

- [Memory quality metrics v0](memory-quality-metrics-v0-proposal.md): maintainer review of the existing
  baseline remains the next gate.
- [Task Packet source following and orientation lite](../5_Completed/task-packet-sources-and-orientation-lite-plan.md):
  completed 2026-09-24. Task Packet v2 embeds the subagent orientation-lite skill and pins the full rules for
  digest-verified on-demand loading. This cuts packets by 42-74%. Its deferred follow-ups remain open:
  - log Task Packet compile, preview, activate and governance-load calls to the retrieval log as their own
    event type, excluded from attention ranking, so packet usage is measurable;
  - retire the stalled [Task Packet hardening plan](task-packet-hardening-progressive-provenance-plan.md) to
    `7_Replaced/` with a pointer to the completed plan: its compiler items are delivered and its Seed Pod
    steps lapsed;
  - make P0.2 workers the first real consumers of v2 packets.
- [Task Packet calibration](task-packet-calibration-harness-plan.md): freeze the representative
  development population and sealed holdout, then run M2-M5. This includes calibrating the 4,000-token
  per-source cap for followed `S:` sources.
- [Memory Trace UX reference plan](memory-trace-ux-reference-model-implementation-plan.md) and
  [interaction matrix](memory-trace-ux-m0-interaction-matrix.md): M3 bounded graph perspectives remain
  the next local UI slice.

## Parked and historical work

- Post-MVP product ideas live in [`8_Deferred/`](../8_Deferred/), each with a revisit condition.
- Consolidated or superseded plans live in [`7_Replaced/`](../7_Replaced/) with successor pointers.
- Reflection Board v1 launch verification was withdrawn when the runtime was retired; the
  [historical plan](../7_Replaced/reflection-launch-verification-closeout.md) is not an active gate.
- Shipped plans live in [`5_Completed/`](../5_Completed/); external account or submission choices are
  references/checklists, not active engineering plans.
- The full 41-document disposition is recorded in the
  [2026-09-19 consolidation audit](../4_Reference/hosted-roadmap-consolidation-audit-2026-09-19.md).

## Decisions still requiring JNL

- Whether and when to authorize any hosted implementation tranche beyond local documentation/design.
- Provider, hosting, billing, and retention choices once the MVP gates require them.
- Whether to submit the completed Memory Index dry run externally.
- Any remote OpenSSF, branch-protection, vulnerability-reporting, or organisation-owner settings.

The folder remains lifecycle authority. Do not reopen a replaced plan to recover one requirement: carry
the requirement into the canonical hosted programme or a new bounded successor instead.
