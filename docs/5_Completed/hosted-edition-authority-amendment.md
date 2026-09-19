---
title: "Hosted edition authority amendment"
completed_on: "2026-09-19"
source: "Maintainer-ratified hosted MVP and roadmap consolidation"
implemented_in:
  - "docs/CONSTITUTION.md"
  - "docs/3_Spec/edition-authority-contract.md"
  - "docs/2_Todo/hosted-memory-mvp-programme.md"
---

# Hosted edition authority amendment

Status: **RATIFIED AND APPLIED 2026-09-19 by JNL.**

## Decision

Memory Seed has two explicitly separate editions with one authority in each:

- the lean OSS/local edition remains offline-capable and Markdown-authoritative;
- the hosted team edition is SQL-authoritative and offers Markdown export;
- neither edition depends on the other, and there is no dual-authority synchronization or repository-settlement protocol.

The hosted edition is the canonical new-product development direction. The local edition remains a complete,
useful memory substrate rather than a cache or client for the hosted service.

## Why the Constitution changed

Constitution v1.14 and `adr_markdown_substrate` deliberately rejected a SQL-authoritative hosted tier because
one Markdown truth model was simpler and preserved direct repository ownership. The maintainer reconsidered
that product boundary after defining a team-capable hosted MVP. Concurrent team capture, private raw evidence,
server-enforced permissions, retention, branch state, event-driven curation and low-latency retrieval form a
different operational product. Treating its database as a disposable projection would recreate settlement and
sync machinery while leaving neither edition with a clear single writer.

The amendment preserves the earlier rationale where it remains valid: Markdown still owns the complete local
edition, the hosted edition must export readable Markdown, and the local core never depends on an account,
server, database or network.

## Consequential changes

- Constitution v2.0 changes Invariants #1 and #6, the open-core principle, implementation map and resolved
  collaboration question.
- `adr_markdown_substrate` is revised from “Markdown everywhere” to edition-scoped authority.
- The candidate hosted Markdown settlement contract is rejected and retained in the rejected lane.
- The old Memory Trace architecture and roadmap are replaced by the hosted MVP programme plus the surviving
  local Trace M3 plans.
- Shared contracts cover record meaning, provenance, lifecycle semantics and retrieval behavior. They do not
  imply shared persistence, synchronization or interchangeable authority.

## Non-authorizations

This amendment does not authorize product implementation, data upload, provider procurement, model trials,
billing, deployment, or collection of user conversations. Those remain gated by the hosted MVP programme.
