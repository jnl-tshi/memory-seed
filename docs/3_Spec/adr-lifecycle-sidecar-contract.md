---
title: Living ADR sidecar contract
status: live
spec_binding: live
parent: ../2_Todo/memory-seed-semantic-record-and-signal-foundation-plan.md
---

# Living ADR Sidecar Contract

Status: **IMPLEMENTED AND NORMATIVE — 2026-08-03**.

This contract replaces the deprecated pointer-only prototype. Memory Seed keeps one living ADR per
architectural concern. The ADR stays concise and current, while an append-only event ledger preserves every
decision chain that produced, challenged, or changed it.

## Authority boundary

Authority is partitioned rather than duplicated:

| Concern | Canonical owner |
|---|---|
| Detailed decision narrative, alternatives, files, tests, and provenance | Immutable session decision `(entry_id, dN)` |
| Architectural-concern membership and stable ADR identity | Living ADR sidecar |
| Concise Decision, Why, and Evolution synopsis | The ADR revision proposal that curates them |
| Governing decision | The latest valid `revision-accepted` event |
| Status, pending/rejected lists, and Current view | Replay of the ADR ledger |
| Current implementation truth | Current project files and live specs |
| Search indexes, registries, SQLite caches, API responses, and Trace views | Rebuildable projections |

An ADR never rewrites its source session decisions. A session decision remains the detailed evidence
authority; the ADR owns the curated architectural reading and which accepted decision currently governs the
concern.

## Storage and stable identity

ADRs live at `.memory-seed/decisions/<adr_id>.md`. A missing `decisions/` directory is a valid empty corpus.

```markdown
---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_local_index
title: Local indexing strategy
topics:
  - retrieval
created_at: 2026-08-03T12:00:00Z
user_initials: JNL
agent_type: codex
source: write-time
---

# Local indexing strategy

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_current:d1`

### Decision

Use the incremental local index.

### Why

It preserves local speed without rebuilding the corpus.

### How it evolved

Replaces the full-rebuild strategy after scale testing.
<!-- memory-seed-derived-current-view:end -->

## Event ledger
```

Frontmatter is stable identity metadata. Writers preserve `format`, `schema_version`, `adr_id`, `title`,
`topics`, creation attribution, and provenance; structural branch reconciliation rejects divergent values
instead of choosing one silently. Lifecycle changes are new ledger events. Metadata repair is an explicit
file-repair operation, not a lifecycle event. `Current view` is generated from replay and is never an
independent status store.

## Event ledger

Each event is a `### <kind> - <timestamp>` block with a fenced JSON envelope. Event IDs are unique and
content-stable within the ADR.

### `revision-proposed`

Introduces a candidate revision. It records a canonical `decision_ref`, `update_entry_id`, provenance,
zero or more direct lineage predecessors, optional supporting decisions, and concise `Decision`, `Why`, and
`Evolution` prose owned by the ADR. A proposal is pending and never changes authority by itself.

### `revision-accepted`

Makes a previously proposed revision authoritative. It records the accepted decision, reason, source, update
entry, and `expected_authoritative_decision` when a head already exists. The expected-head guard prevents
stale or competing acceptance. An accepted revision must descend from the current accepted head through
validated lineage. Branching and converging predecessors are valid; cycles and competing heads are not.

### `revision-rejected`

Rejects a proposal without changing the accepted head. The rejected decision remains visible in history and
continues to participate in mandatory-review membership.

### `reviewed-no-change`

Records that an ADR head was reviewed and remains current. In the append-review path it names the matched
lineage decisions and a concise reason; the standalone recorder instead reviews the current head and uses a
named existing session entry as its evidence anchor. Both shapes change neither lineage nor authority.

### `adr-superseded`

Retires the entire architectural concern in favour of a separately identified ADR. It is not a synonym for
accepting a revision inside the same concern.

## Replay and integrity

Replay derives status, the superseding ADR, the single authoritative decision and synopsis, pending and
rejected revisions, the complete branching/converging lineage, and the generated Current view.

Validation rejects unsupported schemas, malformed or duplicate IDs, unresolved decision references, invalid
provenance or timestamps, illegal event order, rejected/unknown acceptances, stale expected heads, cycles,
and competing authority.

Bare references to an entry with exactly one decision normalize to `<entry_id>:d1` for membership and replay.
`evolves` and `replaces` define lineage. `related` and supporting references provide context but never trigger
lineage semantics.

## Mandatory append review gate

Before CLI `session append` or MCP `memory_session_append` writes anything, one shared preflight inspects every
decision-scoped `evolves` and `replaces` target against a reverse ADR-membership index. Membership includes
current authority; every proposed, accepted, rejected, and historical revision; and every curated direct or
transitive predecessor.

If any target belongs to an ADR, the first call is fail-closed and writes zero bytes. It returns
`ok: false`, `written: false`, `review_required: true`, every affected ADR, canonical trigger references,
the current accepted synopsis and authority, compact full ledger, pending proposals, relevant source excerpts,
the returned timestamp, and a deterministic `adr_review_receipt`.

The receipt binds workspace/runtime identity; the exact proposed title, body, timestamp, decision envelope,
and lifecycle links; and matched ADR IDs plus canonical ledger digests. Any change invalidates it. A retry
must supply exactly one outcome for every matched ADR:

- `revise`: append a `revision-proposed` event with concern-specific Decision/Why/Evolution prose; or
- `no-change`: append `reviewed-no-change` with a short reason.

Missing, extra, duplicate, malformed, stale, or replayed outcomes are refused. `revise` never silently accepts
its proposal.

Decision envelopes use plural ADR actions because one decision can affect several concerns:

```json
{
  "decision": "d1",
  "links": {"evolves": ["mse_previous:d2"]},
  "adrs": [
    {
      "adr_id": "adr_local_index",
      "outcome": "revise",
      "decision": "Use the incremental index",
      "why": "It preserves local speed without rebuilding the corpus.",
      "evolution": "Replaces the full-rebuild strategy after scale testing."
    }
  ]
}
```

The retry carries `adr_review_receipt` at the top level. `memory_session_append` and
`memory_session_integrate` remain the only MCP writers.

## Transactions and branch reconciliation

Session narrative is the parent. Topic, link, ADR, and review events publish after it through the existing
recoverable parent-first transaction and journal. Interrupted enrichment recovers idempotently; an ADR event
cannot become authoritative before its source session decision exists.

Branch-local ADRs reconcile structurally: identical events deduplicate; independent events merge
chronologically; divergent content under one event ID conflicts; competing acceptances conflict; and Current
view regenerates after fusion. Historical session files remain unchanged.

## Public interfaces

CLI operations: `adr promote`, `adr revise`, `adr transition`, `adr reviewed`, `adr list`, `adr show`, and
`adr check`.

Read-only MCP tools: `memory_adrs_list`, `memory_adr_show`, `memory_adr_review`, and `memory_adrs_check`.

MCP write tool: `memory_adr_reviewed`, the validation-parity twin of CLI `adr reviewed`; both require an
existing evidence entry plus a non-empty reason and call the same append-only writer.

Trace exposes `GET /api/v1/adrs` and `GET /api/v1/adrs/{adr_id}` plus the ADR workspace. It renders accepted
authority, the concise synopsis, pending/rejected states, branching/converging history, collapsed no-change
reviews, worktree scope, and exact source-decision navigation into Inspector.

## As-built proof

Three independent concerns are dogfooded under `.memory-seed/decisions/`: mandatory MCP review, parent-first
sidecar transactions, and session-decision authority versus ADR-curated synopsis. The fixtures include
multi-revision history, historical/pending/rejected membership, a decision shared by two ADRs, and a converging
predecessor chain. The first gated call was byte-for-byte inert; its exact receipt retry created proposals,
and only explicit later transitions changed authority.
