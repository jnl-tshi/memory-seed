---
title: "Codex capture feasibility tranche"
date: "2026-09-21"
priority: P0
status: discovery-in-progress
next_action: "Complete interactive design discovery with JNL, then approve a bounded synthetic-data implementation plan."
blocked_by: "Target Codex workflow, capture boundary, identity binding, and approval interaction are unresolved."
source:
  - "docs/2_Todo/hosted-memory-mvp-programme.md"
---

# Codex capture feasibility tranche

Status: **ACTIVE P0.2 DISCOVERY.** This is a bounded subplan of the [Hosted Memory MVP Programme](hosted-memory-mvp-programme.md), not a separate programme. Implementation begins only after the [tranche discovery gate](0_NEXT_STEPS.md#tranche-entry-gate--design-discovery-first) is completed with JNL.

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
