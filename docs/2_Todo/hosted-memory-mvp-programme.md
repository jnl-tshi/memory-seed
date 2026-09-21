---
title: "Hosted Memory MVP programme"
date: "2026-09-19"
priority: P0
status: accepted-programme
next_action: "Run P0.2 Codex capture and approval feasibility spike using synthetic data, then build the authenticated P0.3/P0.4 thin slice."
blocked_by: []
source:
  - "docs/4_Reference/archived/hosted-memory-seed-01-hosted-memory-seed-curator.md"
  - "docs/4_Reference/archived/hosted-memory-seed-02-curator-evaluation-framework.md"
  - "docs/4_Reference/archived/hosted-memory-seed-03-multi-signal-retrieval-ranking.md"
  - "docs/4_Reference/archived/hosted-memory-seed-04-derived-knowledge-lifecycle.md"
  - "docs/4_Reference/archived/hosted-memory-seed-05-local-and-central-deployment.md"
  - "docs/4_Reference/archived/hosted-memory-seed-06-mvp-80-20-plan.md"
---

# Hosted Memory MVP Programme

Status: **ACCEPTED P0 PROGRAMME.** This is the single active plan for the hosted product. It replaces the
older hosted, next-generation Trace, curator, provenance and workbench programme documents listed below.

## Outcome

Prove a team-capable hosted memory service for AI-assisted software developers. A developer continues using
their existing working agent. An authenticated Codex-first adapter captures the accessible work evidence once;
an event-driven curator turns grounded evidence into governed project memory; authenticated MCP retrieval gives
the working agent the right memory and approval requests without requiring a new chatbot or dashboard.

## Product boundary

- **Local OSS:** offline-capable, Markdown-authoritative, useful without an account or hosted service.
- **Hosted:** SQL-authoritative, team-capable, Markdown export, private raw evidence with project-governed
  curated sharing.
- **No MVP synchronization:** no repository settlement, dual authority, federation, CRDT, custom graph database
  or bidirectional local/hosted sync.
- **No launch UI dependency:** no hosted chatbot, dashboard or Memory Trace approval surface is required.
- **Future Trace:** a focused project-intelligence experience may later show decisions, topics, links, branch
  status, conflicts, evidence-linked Q&A and approvals. It consumes the same governed domain and retrieval tools
  but receives no background curator write privilege.

## Primary user journey

1. A project lead creates or enables a hosted project, assigns members and configures explicit ADR delegation.
2. A developer opts that project into capture while working through an existing coding agent.
3. The local adapter emits ordered, idempotent deltas for accessible conversation, tool calls, tool results and
   exposed reasoning summaries. It never claims access to hidden raw reasoning.
4. The hosted service verifies identity, project, repository and branch context, stores the accepted event once,
   and queues an event-driven curator run.
5. The curator produces evidence-grounded Decision or Documentation candidates, controlled topics and supported
   relationships. Deterministic validation applies permissions, authority and mutation policy.
6. Ordinary safe records become curated memory. Reversals or elevated decisions become exact pending mutations.
7. The working agent retrieves curated memory first and presents pending approvals on a proven authenticated
   interaction. The server validates the approving identity, scope and exact change.

## Capture contract

Capture is per-project opt-in. MCP alone is not considered a complete transcript-capture mechanism; P0 begins
with a Codex adapter feasibility spike against the actual client surfaces available at that time.

Every accepted event needs:

- tenant and project identity;
- authenticated user identity and membership;
- client, agent and session identity;
- repository identity plus source branch and commit when available;
- capture time, service receipt time, monotonic sequence and idempotency key;
- event kind and content digest;
- explicit unavailable fields rather than inferred identity or hidden reasoning.

The adapter refreshes repository, branch, commit and client context when they change. A transcript saying “the
user approved” cannot substitute for authenticated identity.

Pause stops new capture and upload. Events already accepted by the service may drain through the queue, after
which the curator idles. Resuming does not backfill the paused interval without explicit permission.

## Authoritative hosted entities

The initial SQL model must cover only the required entities:

- organisation/tenant, project, membership, role and scoped delegation;
- integration/client, capture session and immutable event;
- evidence item and permission-aware evidence span;
- curated record, record kind, append-only version and source/origin metadata;
- controlled topic attribution and supported lifecycle relationship;
- branch identity, branch observation and branch outcome;
- proposal/pending mutation, approval decision and exact authorizing identity;
- curator job, run, provider/schema version and validation result;
- retention/deletion state, export receipt and security audit event.

Large-object storage is not an MVP assumption. First measure real text, tool-result and model-input sizes. Add a
separate object store only if measured payloads or retention behavior justify it.

## Branch and applicability contract

A normalized branch registry separates identity, existence and outcome:

- existence: `present`, `deleted`, `unknown`;
- outcome: `in-progress`, `merged`, `abandoned`, `unresolved`;
- non-Git and detached HEAD are separate capture contexts, not branch-existence values;
- observations record source evidence, target branch where known and last-checked time;
- branch identity survives name reuse.

Deletion does not mean abandonment. Merge often precedes deletion. Abandoned-work decisions remain searchable
history but are not adopted current guidance. Decisions adopted elsewhere, independently approved, or promoted
to an ADR can remain applicable after their source branch disappears.

Ordinary decisions are branch-scoped. `related` links may cross branches; cross-branch replacement is forbidden.
Unknown status does not block capture or related links, but it holds branch-dependent adoption/replacement. One
consolidated warning is shown per affected retrieval and identifies the affected records. Muting changes the
notification, not the metadata or guard.

Whether merge adoption is automatic or batch-approved remains open and must not be inferred by implementation.

## Curator pipeline

The curator is event-driven over accepted deltas, not a periodic full-history scan:

1. normalize, deduplicate, redact prohibited fields and bound the evidence window;
2. retrieve plausible existing decisions/topics/edges so comparison is bounded rather than all-pairs;
3. make typed judgments through a provider-neutral interface;
4. write evidence-grounded record prose through a separate provider-neutral interface;
5. validate structured output, evidence quotations, supported relationship kinds, authority and permissions;
6. commit an ordinary record, hold a pending mutation, or abstain with a reason.

Jev is an initial candidate for typed durable-content, topic and bounded-edge judgments. It does not write
narrative. Cerebras Qwen3.8 27B is an initial candidate for Decision/Documentation prose. Vendor latency,
throughput and price claims are hypotheses, not end-to-end service commitments. Provider confidence is never
authority. Fakes and deterministic baselines must exercise the complete pipeline without a paid provider.

## Governance and autonomy

- New ordinary records may be autonomous when their evidence, scope, identity and authority pass validation.
- Ordinary replacement may be autonomous only from clear actual user direction, captured evidence and sufficient
  authority. Ritual approval wording is unnecessary, but an inferred broader goal or an agent claiming user
  intent is insufficient.
- An agent-originated reversal without user evidence stays pending and leaves the existing decision authoritative.
- Approval binds one exact mutation to one authenticated, authorized identity.
- The Constitution is project-wide and amendable only by the project lead.
- ADR promotion/replacement requires elevated approval and then applies across branches. The lead may explicitly
  delegate a specific ADR or defined area; cross-area work returns to the lead. ADR delegation never delegates
  Constitution authority.
- Topic inference and work assignment confer no governance rights.

The supported authored lifecycle vocabulary is `related`, `evolves` and `replaces`. Existing projections may
render the historical term `supersedes`; the hosted contract does not invent new relationship kinds.

## Privacy, retention and sharing

- Raw conversations and tool evidence are private by default. A project lead does not automatically receive
  access to every member's raw chats.
- The team-shared default is curated records plus selected evidence excerpts, permission-checked at retrieval and
  source-link time.
- Full raw evidence has a 30-day rolling retention window. Curated memory and its permitted evidence persist
  until deliberate deletion.
- Retrieval is curated-first. Raw fallback is allowed only when curated context is insufficient, the evidence is
  inside its retention window and the caller has access. It is labelled source evidence, never an approved decision.
- When original context expires, the curated record states that the source is no longer available.

Backup expiry, secret handling, oversize tool-result rules and cross-user excerpt-sharing defaults are release
gates, not settled assumptions.

## Retrieval parity

Hosted retrieval preserves the current canonical ranking contract behind a storage adapter: semantic relevance,
chronology, preferred keywords, successor lift, replacement damping and supported relationship evidence. Signals
remain inspectable. Attention does not influence default ranking until its existing real-usage A/B gate passes.
Permission, tenant and project filters apply before candidates are ranked. Live history is down-ranked, never
silently hidden; exclusion remains an explicit caller choice.

## Entry gate for each tranche

The [Next Steps tranche gate](0_NEXT_STEPS.md#tranche-entry-gate--design-discovery-first) applies to each
P0, P1, and P2 tranche below. Before a new tranche's implementation begins, start a dedicated design
discovery conversation with JNL, challenge the proposal's assumptions, resolve the tranche's open design
choices and acceptance criteria, and write a bounded detailed plan. This programme sets sequence and
release gates; its candidate architecture and model examples do not pre-approve implementation details.

## Programme sequence

### P0 — prove authority, capture and one useful loop

1. **P0.1 Authority closeout — integrated:** Constitution v2.0, the edition contract, ADR evolution and
   lifecycle consolidation are in the project baseline.
2. **P0.2 Codex feasibility spike:** prove accessible event kinds, ordering, idempotency, identity refresh, pause,
   queue drain and authenticated approval delivery without collecting private production data.
3. **P0.3 Authenticated substrate:** tenant/project/membership/delegation, immutable event store, branch registry,
   retention states and audit skeleton.
4. **P0.4 Thin slice:** one captured user decision becomes one evidence-linked curated record and is returned by
   authenticated MCP to a team member with the right permissions.

### P1 — prove curator safety and team readiness

5. Run the [decision-layer model tournament](decision-layer-model-tournament-plan.md) on reviewed, provenance-checked
   labels. Compare stable-schema classifiers (Model2Vec + Logistic Regression, Model2Vec + XGBoost, SetFit)
   with deterministic and generalized candidates per task, and evaluate the prose writer separately. Dynamic
   Area/Activity attribution must receive each project's current candidate hierarchy; within-project label-ID
   accuracy is not cross-project evidence. Freeze temporal and held-out tests, add independent-project and
   unseen-ontology tests when data exists, and measure calibration, abstention, high-risk errors and full-pipeline
   cost before choosing a provider or resident worker.
6. Add guarded replacement, elevated approval and branch applicability behavior.
7. Complete privacy, retention, deletion, export, secret-handling and payload-size decisions.
8. Prove retrieval parity, permission isolation and a seconds-scale team pilot. Select a numerical p95 only from
   measured workloads.

### P2 — focused experience, after service value

9. Focused Memory Trace decisions/topics/links/branches/conflicts view, evidence-linked Q&A and approval
   controls. [Decision storyline retrieval](../8_Deferred/decision-storyline-retrieval-proposal.md) is a later
   evaluated mode after the governed capture/retrieval loop and bounded lineage fixtures work.
10. Additional client adapters and enterprise controls only after the Codex/team loop is proven.

A [persistent Laya worker](../8_Deferred/laya-local-decision-worker-proposal.md) remains deferred until
task-specific results and measured queue load justify it. The [decision-knowledge report](../4_Reference/archived/decisions-first-class-knowledge-report.md), [governance report](../4_Reference/archived/decision-governance-architecture-report.md), and [combined architecture report](../4_Reference/archived/decision-intelligence-reference-architecture-report.md) are source references for this sequence, not parallel active programmes.

## Release gates

- **Capture:** representative golden sessions cover every accessible event type exactly once; ordering,
  reconnect, duplicate replay, pause and unavailable fields pass.
- **Approval delivery:** an exact pending mutation is reliably surfaced through the authorized user's working
  agent on a defined authenticated interaction; no claim of arbitrary MCP push.
- **Curator quality:** labelled and sealed sets measure durable-content, topic, relationship, faithfulness,
  citation, abstention and high-risk false positives. Numerical thresholds are selected before autonomous use.
- **Privacy/security:** tenant/project negative controls, role/delegation tests, raw-access denial, excerpt checks,
  injection fixtures, deletion and audit pass before private-project release.
- **Branches:** merge, squash, cherry-pick, deletion-after-merge, reused names, unknown, non-Git and detached HEAD
  fixtures pass. Automatic versus batch merge adoption remains a named open decision.
- **Retention/export:** active-store deletion, backup-expiry policy, expired-source markers and complete Markdown
  export pass.
- **Retrieval:** current canonical quality fixtures remain at least as good after the SQL adapter; permission
  filters cannot be bypassed through ranking or raw fallback.
- **Operations:** measured latency, volume, provider availability, cost and privacy meet selected launch targets.

## Open decisions

1. Numerical end-to-end p95 target.
2. Provider correctness, abstention, cost and privacy thresholds.
3. Automatic versus batch-approved merge adoption.
4. Backup expiry after active raw deletion.
5. Secret detection, redaction and oversize payload handling.
6. Default policy for sharing selected excerpts across team members.
7. Exact delivery contract for pending approvals.

## Consolidated source ownership

This programme incorporates the hosted curator, evaluator, ranking, derived-lifecycle and deployment drafts; the
provenance/authority taxonomy; semantic-record and residual signal work; workflow journey fixtures; link-judgment
validation; Evidence Pack/privacy contracts; relevant write-time transaction semantics; and old next-generation
Trace architecture/roadmap requirements. Source documents move to Replaced or archived Reference and point here.
Surviving local OSS and Trace obligations remain separate in Todo or Deferred.

## Non-goals

No product code, infrastructure, hosted data collection, provider purchase, paid model call, fine-tuning, broad
enterprise feature set, custom graph database, synchronization or UI implementation is authorized by this plan.
