---
title: "Codex capture feasibility tranche"
date: "2026-09-21"
priority: P0
status: first-hand-submission-offline-trial
next_action: "Complete the bounded offline post-write advisory trial, then separately design authenticated submission and approval delivery before any sign-in."
blocked_by: "No OAuth action is authorized; hosted write identity, owner-only source access, and curator quality remain unvalidated."
source:
  - "docs/2_Todo/hosted-memory-mvp-programme.md"
---

# Codex capture feasibility tranche

Status: **FIRST-HAND SUBMISSION PIVOT; OFFLINE ADVISORY TRIAL ONLY; AUTHENTICATED TRIAL NOT STARTED.** This is a bounded subplan of the [Hosted Memory MVP Programme](hosted-memory-mvp-programme.md). The earlier local capture implementation is landed. No sign-in or approval mutation may begin.

## Accepted pivot (2026-10-03)

The write agent, with decision-time context, explicitly authors and submits a decision. The guarded hosted write
accepts an ordinary record before the curator runs. The curator is a secondary, asynchronous sense check:
it compares topics and `related`/`evolves`/`replaces` links against current project candidates, proposes
cited changes for an authorized reviewer, and flags clear actor, timing, scope or source-support conflicts.
It does not author decision prose, silently mutate accepted records, or gate every ordinary write.

Use the existing decision-known adaptive locator only for targeted source checks. It discloses user/assistant
dialogue in two-turn batches, at most twenty preceding historical turns, excluding tool calls. If support is
not found within that bound, leave the review incomplete and flag it; source reachability is not semantic
validation. Preserve first-hand authored values separately from later reconstructed curator suggestions.

P0.2 first proves this as an offline, provider-neutral contract and [synthetic trial](../../hosted/evaluation/ADVISORY-TRIAL.md).
That trial exercises the handoff and catches one deliberately false but correctly cited suggestion; it
does not measure model accuracy. The live submission
surface, authenticated identity, owner-only raw-evidence access, durable advisory queue, and approval path
remain separate design and feasibility gates. Do not import local Markdown sessions into hosted SQL implicitly.
Historical retrospective extraction work below remains diagnostic rather than a product deliverable.

## Historical accepted extraction revision (2026-09-29; now diagnostic only)

JNL approved the following contract, recorded in `mse_ad9xz2f1kpyygw9b`:

1. Begin at the marker and retain extracted components. Expansion processes only previously unseen source messages; it does not run NLP over the accumulated prefix again.
2. Close a draft only with a clear issue, chosen action, scope, and grounded acceptance. Preserve stated reasons and conditions. References such as “that approach” remain incomplete until resolved.
3. Resolve missing context from earlier session/lineage evidence in bounded steps. Reveal later evidence only as it arrives; earlier acceptance cannot authorize a newly introduced proposal.
4. Clarification can remain within the original decision only before implementation and intervening decisions. A changed choice after either boundary requires a new evolving/replacing decision; never silently rewrite the earlier decision.
5. Compare extracted decisions with known records by meaning, allowing different wording. Evaluate issue, action, scope, acceptance/actor, conditions and reasons separately. Word overlap is not semantic equivalence. Keep gold content hidden from extraction.

### Current implementation and remaining buckets

- Evidence: corpus identity/splits remain frozen; prior retrieval results are diagnostic, not extraction accuracy.
- Parser: experimental per-coordinate extraction cache and causal agreement assembly implemented; targeted regression tests cover delta-only processing and explicit lifecycle boundaries. This is call-local state, not yet a persistent live subscription.
- Lifecycle: explicit boundary flags halt expansion. Deriving those flags from actual captured tool/marker events, safely interpreting pre-implementation clarifications, and generating curator-reviewed evolving/replacing drafts remain to be integrated.
- Evaluation: preserve the historical report. The revised runner labels gold-anchor envelope coverage as an oracle diagnostic, exposes unmeasured recall/semantic gates as null, and requires a separate output directory.
- Remaining: causal event-by-event corpus replay without post-record leakage; exact source-span scoring; blind field-level semantic adjudication; live retained-state integration and reliability; independent review and one final full suite before landing.

The bounded parser currently abstains on language it cannot resolve. It must not be presented as full semantic extraction or production memory, nor treated as the primary capture path after the pivot. Stop before requesting the OAuth identifier, device flow, human approval mutation, or token storage.

## Historical offline finding (2026-09-29; corrected interpretation)

- The frozen corpus contains 103 formal records: 100 typed Decisions and three Documentation controls. The permitted partitions are 80 development decisions, 15 clean descriptive held-out cases, and 13 audit-only controls, contaminated rows, or post-audit amendments.
- The prior report recorded valid marker recovery, deterministic output, synthetic accepted-state precision, replay deduplication, pause/no-backfill semantics, and 23.64 ms p95 local capture latency. These are historical results, not validation of the revised parser.
- **89.6% (60/67)** checked whether gold-cited turns fit a four-turn envelope around a gold-selected anchor. It did not reproduce session-to-window-to-span retrieval or prove extraction correctness. The reported **80.6%** checked candidate presence in gold-selected windows, not genuine unmarked discovery recall. Both original recall-gate claims require a new measurement design; the frozen report remains as historical evidence.
- [`hosted/evaluation/REPORT.md`](../../hosted/evaluation/REPORT.md) records the results and limitations. [`hosted/evaluation/LIVE-TRIAL.md`](../../hosted/evaluation/LIVE-TRIAL.md) is prepared but has not requested an OAuth identifier, started device flow, presented/executed an approval mutation, or stored a token.

## Outcome and boundary

Use synthetic data to decide whether an opt-in Codex adapter can capture the evidence the hosted MVP needs and surface an exact pending approval to an authenticated, authorized user. Produce a supported-surface inventory, executable golden-session evidence, a go/no-go finding, and a costed next-step recommendation. Do not use private production conversations, build the hosted service, choose a provider, or assume access to hidden reasoning.

The programme's P0.2 checks remain the acceptance frame: accessible event kinds, ordering, idempotency and duplicate replay, user/project/repository context refresh, pause and queue drain, explicit unavailable fields, and authenticated approval delivery. A no-go finding is a valid result if a required surface is unavailable.

## Evidence available at tranche entry

- The repository contains local Codex MCP configuration and workflow hooks, but no hosted capture adapter, event-ingestion service, upload queue, or authenticated approval endpoint. The prior synthetic experiment in `experiments/agent-capture/` parses Codex event streams and can inform fixtures; it is not the hosted adapter.
- [Official Codex App Server documentation](https://developers.openai.com/codex/app-server) describes a client-owned session with streamed thread, turn, item, tool, and approval events. It does not establish passive attachment to every already-running desktop conversation or supply a hosted member identity.
- [Codex advanced configuration](https://developers.openai.com/codex/config-advanced) documents OpenTelemetry export as a second capture candidate. It is a telemetry surface and does not by itself settle approval delivery or hosted identity.

These are documentation and repository findings, not a successful end-to-end feasibility test.

## Design discovery decisions for JNL

1. **Target workflow:** must capture work in the existing Codex desktop app, a Codex CLI session, an App Server-owned client session, or more than one? This determines whether the documented surface satisfies the product journey.
2. **Evidence boundary:** capture all accessible conversation/tool events, only explicitly marked decisions, or both? Decide whether tool-result bodies are needed in the first proof or metadata/digests suffice.
3. **Identity and approval:** choose how a local session binds to an authenticated hosted member and project, and what user-visible interaction may present an exact approval. A transcript statement cannot prove approval identity.
4. **Trial boundary:** choose local-only synthetic replay versus a disposable live Codex session, permitted network/provider use, timebox, and what missing event or identity capability makes the trial a no-go.
5. **Acceptance:** set the required golden sessions, negative controls, replay/pause cases, and evidence needed before moving to P0.3.

Record JNL's answers, realistic alternatives and selected option here before this becomes an implementation plan.

## Provisional execution shape

These are task boundaries for planning, not authorized implementation tasks. First settle a minimal event and golden-fixture contract. Then assign independent work with explicit file ownership and separate worktrees where writing can safely overlap:

- **Capture surface:** prove the selected Codex event stream and map each accessible kind; report unsupported fields explicitly.
- **Context and identity:** bind opt-in project, session, repository, branch/commit, and authenticated user without inferring missing fields.
- **Reliability:** exercise ordering, reconnect/replay, idempotency, pause, queue drain, and no automatic backfill across a paused interval.
- **Approval path:** prove an exact request reaches the authorized user through the selected interaction and a response can be verified.
- **Join and review:** run golden sessions and negative controls, measure cost/time, and issue a go/no-go decision.

Use the subagent-driven-development workflow for the approved multi-task implementation plan and its per-task review. Parallelize independent read-only investigations and, if discovery confirms disjoint writing boundaries, use isolated worktrees with sequential integration. Keep shared contracts, authentication decisions, and final validation under one owner. Allocate small-capability workers for bounded tasks and independent reviewers for security and whole-slice findings. Any failed prerequisite blocks only dependent tasks; revise the plan when evidence changes.
