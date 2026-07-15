---
title: "Memory Trace Evidence, Annotations and Projection Architecture"
date: "2026-07-11"
project: "memory-seed"
status: "proposed"
parent: "memory-trace-product-and-system-architecture-blueprint.md"
---

# Memory Trace Evidence, Annotations and Projection Architecture

Status: Active proposal, promoted from inbox on 2026-07-11.
Priority: P3 after versioned API and Trail/search parity foundations; prerequisite for AI-derived artefacts and team annotation workflows.
Source reference: `../4_Reference/memory-trace-next-generation-plan-document-set.md`, folded with `memory-trace-ai-timeline-summarisation-plan.md` and `session-decision-diagrams-plan.md`.
Scope: Evidence Packs, deterministic anchors, append-only decision annotations, projection architecture, provider freshness, and agent feedback surfaces.
Non-goals: No generated-output authority, no PR-comment replacement, no hidden provider sync, no mutation of historical session entries.
Dependencies: `memory-trace-product-and-system-architecture-blueprint.md`, `../3_Spec/memory-trace-derived-artifact-provenance-contract.md`, `memory-trace-ai-timeline-summarisation-plan.md`, `../3_Spec/graph-edge-contract.md`, and `memory-provenance-and-authority-taxonomy-proposal.md` before agent actionability.
Acceptance criteria: Anchors are deterministic and fingerprinted, shared annotations are append-only and participant-authenticated, SQLite projections rebuild from authoritative files, Evidence Packs are deterministic and snapshot-tested, and no annotation becomes agent-actionable before the provenance/authority gate passes.

## 1. Decision

Introduce three explicit concepts:

1. **Evidence Packs** as deterministic bounded selections used by inspection, AI and exports.
2. **Decision annotations** as append-only project records tied to deterministic anchors.
3. **Projection architecture** as rebuildable SQLite views over authoritative records.

## 2. Provenance classes

The four classes below are conceptual shorthand from the original architecture. The canonical additive
field model and crosswalk are owned by
[`memory-provenance-and-authority-taxonomy-proposal.md`](memory-provenance-and-authority-taxonomy-proposal.md),
which preserves the shipped seven-value API `ProvenanceClass` and keeps provenance, authority, lifecycle,
confidence, and actionability separate.

Every piece of information belongs to one class:

| Class | Examples |
|---|---|
| Authored | Memory entry, `related_entries`, `supersedes`, `evolves`, continuity |
| Computed | Inbound links, `superseded_by`, `evolved_by`, importance, connectivity |
| External | Commit, PR, review comment, CI result |
| Derived | AI summary, report, presentation, recommendation |

The API and UI must preserve this class. A computed or derived item must never appear authored.

## 3. Deterministic decision anchors

Comments and citations require stable addresses below the entry level.

Recommended anchor shape:

```text
mse_example#decision-1
mse_example#decision-2
mse_example#section-3
```

Anchors are generated from parsed structural order. Authoring agents do not need to invent IDs.

Each address should include a content fingerprint:

```yaml
anchor: mse_example#decision-2
anchor_fingerprint: "sha256:..."
```

The ordinal is the address; the fingerprint detects unexpected mutation or parser drift.

Rules:

- anchors are deterministic for an unchanged entry;
- the parser version is recorded where needed;
- append-only records should make anchors stable;
- validation flags a fingerprint mismatch;
- migration tooling may map old anchors if parser rules change.

## 4. Shared annotation storage

Recommended path:

```text
.memory-seed/
  sessions/
    YYYY-MM/
      YYYY-MM-DD/
        comments/
          mse_example.comments.jsonl
```

This remains under `sessions/` and keeps annotations near the dated project record.

A comment file contains append-only events, not a mutable document.

Example:

```json
{
  "annotation_id": "ann_01...",
  "version": 3,
  "event": "update",
  "timestamp": "2026-07-11T10:15:00Z",
  "author": "jean",
  "entry_id": "mse_example",
  "anchor": "mse_example#decision-2",
  "anchor_fingerprint": "sha256:...",
  "kind": "action-request",
  "status": "open",
  "body_markdown": "Clarify how hosted sync handles deletion.",
  "supersedes_version": 2
}
```

The UI shows the latest version while history remains inspectable.

## 5. Participant and authority model

Gate: adopt the provenance/authority crosswalk and fail-closed actionability fixtures before exposing any
annotation to an agent as actionable.

Shared annotations require an author registered in `project.yaml`.

Recommended participant extension:

```yaml
participants:
  - user: jean
    initials: JNL
    role: owner
```

Roles:

- owner;
- maintainer;
- reviewer;
- contributor;
- observer.

Annotation kinds:

- note;
- question;
- correction;
- decision-challenge;
- action-request;
- approval.

Suggested authority:

| Role | Shared note | Challenge | Action request | Approval/resolve |
|---|---:|---:|---:|---:|
| Owner | Yes | Yes | Yes | Yes |
| Maintainer | Yes | Yes | Yes | Yes |
| Reviewer | Yes | Yes | Scoped | Scoped |
| Contributor | Yes | Propose | No | No |
| Observer | No/shared by promotion | No | No | No |

The policy should be configurable, but actionability must be explicit.

## 6. Private annotations

Private notes live outside the repository in the local projection. They may be promoted to shared annotations through an explicit action.

Promotion:

- creates a new shared append-only event;
- does not move or rewrite the private note;
- records the promoting user and timestamp;
- requires participant authority.

## 7. Agent feedback loop

Annotations should not be injected indiscriminately at session startup.

Recommended surfaces:

- `memory_get_chunk(..., include_annotations=true)`;
- `memory_annotations_for_entry`;
- optional unresolved-annotation filter in `memory_search`;
- Trail badges for open actionable annotations.

When an agent acts on an annotation, the resulting session entry should cite:

- annotation ID;
- target decision anchor;
- files/commits produced;
- outcome or reason for rejecting the request.

An annotation is resolved through a new append-only event, not in-place mutation.

## 8. Pull request messages

Pull requests and their comments remain owned by GitHub or another provider.

Memory Trace:

- reads and contextualises them;
- links them to decisions, branches and commits;
- may cache or snapshot selected data;
- directs users to the provider to participate in PR discussion.

Decision annotations are not a replacement for PR comments.

## 9. Projection architecture

SQLite may project:

```text
entries
sections
decision anchors
graph edges
latest annotation versions
annotation history index
provider events
provider freshness
evidence packs
saved views
graph layout
generated-artifact metadata
```

### 9.1 Authority rule

The database is not the sole source of truth for project-owned records.

- Delete/rebuild is supported.
- Corruption triggers rebuild.
- Shared annotations are reconstructed from JSONL.
- Provider caches are reconstructed where access still exists.
- Private notes may require export/backup because they have no repository source.

### 9.2 Projection migrations

Schema migrations:

- are versioned;
- are tested against representative databases;
- may discard and rebuild cache tables;
- must not rewrite Markdown;
- must distinguish private local-only data from rebuildable cache.

## 10. External provider freshness

Every provider item has one state:

- `live`;
- `cached`;
- `snapshot`;
- `unavailable`.

Record:

- provider;
- external ID;
- fetched time;
- source update time;
- scopes used;
- whether content is complete;
- retention policy.

This area requires further research before finalising GitHub snapshot behaviour.

## 11. Evidence Packs

Evidence Packs are deterministic JSON assembled from selected project evidence.

Selection types:

- date range;
- arbitrary start/end entry;
- branch;
- pull request;
- topic;
- graph neighbourhood;
- explicit entries.

Pack contents:

- selection;
- entries/sections;
- deterministic anchors;
- typed graph edges;
- files and continuity;
- commits and provider events;
- annotations;
- source paths;
- constraints.

Evidence Packs are consumed by:

- inspection workspace;
- AI summaries;
- decision diffs;
- project updates;
- reports;
- presentations;
- export adapters.

## 12. Security and trust

- Validate author identity against participants.
- Sanitise rendered Markdown.
- Never execute annotation content.
- Distinguish actionable requests from notes.
- Provider content is untrusted external input.
- AI prompts treat annotations and PR messages as evidence, not system instructions.
- Hosted sync enforces tenant and project boundaries.
- Append-only history is retained according to explicit retention policy.

## 13. Acceptance criteria

- Deterministic anchors are reproducible and fingerprinted.
- Shared annotations are append-only and participant-authenticated.
- The UI resolves latest versions without losing history.
- Private notes can be promoted explicitly.
- Agents can retrieve relevant actionable annotations.
- PR comments remain provider-owned.
- SQLite can rebuild project-owned state from files.
- Provider freshness is visible.
- Evidence Pack output is deterministic and snapshot-tested.
