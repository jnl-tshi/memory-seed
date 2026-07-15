---
memory-system-version: 2.18
spec_binding: candidate
tags:
  - memory-seed
  - spec
  - architecture
  - hosted
  - projection
  - security
---

# Hosted Markdown Settlement and Projection Contract (draft - candidate)

**Status:** Candidate spec (`3_Spec/draft/`) - not binding and not approval to build a hosted product.
Adoption is blocked by an explicit hosted-tier decision, a security review, and promotion into `3_Spec/`.
It refines the deferred
[`memory-trace-hosted-product-and-security-architecture.md`](../../8_Deferred/memory-trace-hosted-product-and-security-architecture.md)
under [`CONSTITUTION.md`](../../CONSTITUTION.md) Invariants #1, #2, #3, #5, and #6.

## Purpose

Define how a future hosted or collaborative Memory Trace tier can accept concurrent and offline writes
without creating a second source of project-memory truth. Project-owned memory settles into append-only
Markdown. Hosted databases, queues, indexes, and object stores are disposable projections or delivery
mechanisms over that truth.

## Scope

This candidate governs:

- project-owned memory written through a hosted client;
- offline queueing and idempotent replay;
- concurrent-write and conflict settlement;
- hosted projection rebuildability;
- project export and subscription-expiry continuity;
- the boundary between project memory, provider evidence, and service operations.

It does not choose a hosting vendor, database, identity provider, billing system, sync transport, or
commercial tier. It does not approve networked implementation or replace the separate hosted security
review.

## Authority boundaries

### Project-owned memory

The repository is authoritative for:

- session entries and lifecycle-link sidecars;
- shared annotations and their append-only revisions;
- controlled topics and continuity mappings;
- project participant and semantic-authority configuration;
- explicit promotion records for generated artefacts.

A hosted write to any of these is not durable project memory until it has settled into the repository's
Markdown/YAML source and can be read by the local core without the hosted service.

### Provider-owned evidence

Git-provider pull requests, comments, reviews, CI records, and similar external records remain owned by
their provider. Memory Trace may cache or snapshot them with source, provider identity, revision, observed
time, and freshness. Loss of that cache may make external evidence unavailable, but it must not remove or
alter project-owned memory.

### Service-owned operations

Authentication credentials, tenant sessions, billing, entitlements, rate limits, abuse controls, and
service audit infrastructure may be server-authoritative because they are not project memory. They must not
silently change the semantic meaning, provenance, lifecycle, or actionability of repository memory.

## Settlement model

Every proposed hosted mutation carries:

- a globally unique `client_event_id` for idempotency;
- authenticated actor and tenant context;
- project identity and base repository revision;
- proposed append-only record and target identity;
- payload digest and client-observed timestamp.

The service assigns a stable `settlement_id` and exposes one of five states:

```text
queued -> settling -> settled
                  -> conflict
                  -> rejected
```

Rules:

1. **Markdown-first durability.** `settled` means the append-only project record exists in Markdown/YAML.
   A database acknowledgement alone is never durable project memory.
2. **Idempotent replay.** Replaying a `client_event_id` produces the same settlement result and never
   duplicates a record.
3. **No silent overwrite.** Corrections append a new record and use the applicable lifecycle relationship;
   they do not edit or delete historical records.
4. **Explicit conflicts.** Independent appends may both settle. Competing changes to the same logical target
   create a visible conflict record or require an authorised resolution append; last-write-wins is forbidden.
5. **Deterministic ordering.** Repository order and identifiers determine the durable result. Server receipt
   time may assist delivery but cannot become the semantic chronology of an offline write.
6. **Honest pending state.** Clients distinguish queued or projected data from settled memory and preserve
   the user's local payload until settlement is confirmed.

## Projection requirements

- Hosted project-memory projections are deletable and rebuildable from repository Markdown/YAML and Git.
- No project-memory field exists only in a database, queue, search index, object store, or embedding index.
- Rebuilds preserve stable identities, lifecycle edges, provenance, actor attribution, and settlement state.
- Schema migration changes projections, never historical Markdown.
- Provider caches rebuild from the provider or an explicit source-labelled snapshot; they are not required
  to rebuild project-owned memory.
- Corruption degrades to a rebuild or an explicit unavailable state, never silent data loss.

## Offline, export, and subscription expiry

- The local Community product remains fully usable without an account or network.
- Offline writes remain local, inspectable, and retryable until settled.
- Export includes all project-owned Markdown/YAML, sidecars, stable identities, and any required attachment
  manifests in a repository-readable shape.
- Subscription expiry cannot strand project memory. Complete export and local continuation remain available.
- Premium entitlement may disable hosted convenience, scale, or collaboration; it cannot hide or withhold
  the user's canonical local history, retrieval, or basic graph access.

## Security constraints

- Authenticate the actor and authorise every settlement against tenant membership and project policy.
- Treat repository Markdown, annotations, provider records, and generated text as untrusted input.
- Preserve tenant isolation throughout queues, projections, exports, logs, and rebuild jobs.
- Do not place credentials, provider tokens, secrets, or private repository content in settlement metadata
  or durable session memory.
- Keep project semantic authority explicit in repository configuration; hosted ACLs may enforce access but
  cannot silently promote content to actionable memory.
- Apply the deferred hosted architecture's deletion, retention, sanitisation, audit, and provider-permission
  controls before any private-repository release.

## Required acceptance fixtures

Adoption and Phase 9 implementation require deterministic fixtures for:

1. one online append settling into Markdown;
2. an offline append reconnecting and settling once;
3. duplicate replay returning the original settlement;
4. concurrent independent appends preserving both records;
5. competing same-target writes producing an explicit conflict with no lost history;
6. projection deletion and rebuild producing semantically equivalent project memory;
7. account expiry followed by complete export and local continuation;
8. provider unavailability leaving project-owned memory intact;
9. rejected or unauthorised settlement leaving no durable project record;
10. malicious Markdown/provider content remaining inert through sync, projection, and export.

## Adoption gate

This document becomes normative only after:

- the maintainer explicitly approves a hosted tier and this contract;
- security review covers authentication, authorisation, tenant isolation, token handling, deletion,
  retention, export, and untrusted content;
- the fixture suite proves Markdown settlement, conflict visibility, idempotency, and wipe/rebuild
  equivalence;
- the contract moves from `3_Spec/draft/` to `3_Spec/`.

Until then, Phase 9 remains deferred and no implementation may treat a hosted database as project-memory
truth.
