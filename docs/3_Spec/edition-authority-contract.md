---
memory-system-version: 2.21
spec_binding: live
tags:
  - memory-seed
  - authority
  - hosted
  - local
---

# Edition Authority Contract

Status: **LIVE** under Constitution v2.0.

## Purpose

Define the authority, compatibility and movement boundaries between the lean OSS/local Memory Seed edition and
the hosted team edition. This contract prevents a client, exporter or future integration from silently creating
two writable truths.

## Local edition

The local edition is Markdown-authoritative. Its sessions, decisions, ADRs, policies and declared sidecars live
in the user's project files. Local caches, indexes, embeddings, Memory Trace projections and databases are
derived and rebuildable. The local edition remains usable without an account, network, hosted service or SQL
database.

## Hosted edition

The hosted edition is SQL-authoritative. Its accepted events, curated records, versions, permissions,
delegations, branch registry, approvals, retention state and audit evidence are durable service records. Hosted
search indexes, embeddings and caches may be derived from that SQL authority.

Hosted project memory is not required to settle into a Git repository or local Markdown before it is durable.
A client acknowledgement is durable only after the hosted transaction commits under the service's
idempotency, authorization and audit rules.

## Shared semantic contract

Both editions may share:

- typed Decision and Documentation semantics;
- evidence, origin, provenance, authority and confidence vocabulary;
- the supported lifecycle relationships `related`, `evolves` and `replaces` (legacy readers may expose
  `supersedes` as the historical spelling of `replaces`);
- controlled-topic meaning;
- retrieval response concepts and quality fixtures;
- Markdown export conventions.

Shared semantics do not make local sidecar placement, Git fusion, repository ordering or hosted SQL tables a
cross-edition storage contract.

## Export boundary

The hosted edition provides a human-readable Markdown export containing curated records, their versions,
provenance, lifecycle relationships, branch context, approval state and evidence-availability markers.

An export is a point-in-time user-owned copy, not a second live authority. The MVP provides no continuous
import, repository settlement, bidirectional synchronization or conflict-free replicated state. A future
one-way migration must be explicitly specified and must transfer authority rather than silently duplicate it.

## Identity and authority boundary

Hosted authorization comes from authenticated service identity, project membership and explicit delegation.
Transcript role labels, agent assertions, topic inference and work assignment do not confer authority.
Constitution authority remains with the project lead. ADR authority may be delegated only for named decisions
or defined areas; it does not imply Constitution authority.

## Compatibility and failure behavior

- A local project cannot silently become hosted-authoritative by connecting an MCP client.
- A hosted project cannot silently become Markdown-authoritative by exporting files.
- Losing hosted availability does not corrupt or redefine exported memory, but an export is not promised to
  accept offline writes for later replay.
- Hosted implementation must expose unavailable, expired, unverified and permission-denied evidence states
  rather than inventing data or authority.
- Subscription or service changes cannot prevent complete export of the user's curated memory.

## Acceptance fixtures

1. Local operation succeeds with no hosted configuration or network.
2. A hosted write commits and is retrievable without a repository write.
3. Replaying one hosted client event is idempotent.
4. Export is complete and readable but cannot be mistaken for a synchronized checkout.
5. Connecting a local client never changes the authority of existing local files.
6. Tenant and project identifiers cannot be altered to access another project's records.
7. Deletion, retention and evidence-expiry states remain explicit in exports and retrieval.
