---
title: Retrieval Specification M0-M1 implementation plan
status: active
priority: P1
next_action: Complete Task 1 schema and fixture acceptance, then deliver the Task 2 resolver/MCP vertical slice.
sources:
  - declarative-retrieval-specification-proposal.md
spec_binding: null
---

# Retrieval Specification M0-M1 Implementation Plan

This is the executable critical path for the active [Declarative Retrieval Specification
proposal](declarative-retrieval-specification-proposal.md). It deliberately covers only M0 then M1.

## Global constraints

- Retrieval Specification is declarative data, never executable instructions or permissions.
- The v1 slice accepts inline specs only. Profiles, profile composition, Task Packet profile binding, Trace
  UI, cache/get APIs, semantic providers, ADR selectors, and advanced selectors are out of scope.
- Existing `memory_search` ranking and its public contract remain unchanged.
- The resolver is read-only: preview and resolve must not write under `.memory-seed/`.
- Unknown keys and unsupported clauses fail before retrieval; required gaps fail closed, optional gaps are
  reported; path scope stays within the active runtime.
- CLI and MCP return byte-equivalent canonical JSON for the same request/revision. Ordered references and
  fingerprints are reproducible at one corpus revision.
- Every emitted evidence reference must be fetchable from canonical Markdown without a Trace dependency.

## Task 1 - M0 schema and fixture contract

Freeze the narrow v1 inline schema and build the fixture corpus that defines its observable behaviour.

Deliverables:

- Implement strict validation and canonical normalization for the M1-supported inline clauses: schema,
  version, `required` Constitution/related-decision/evidence declarations, optional neighbouring sessions,
  topic/path filters, deterministic ordering, limits, `on_missing`, and output trace/excerpt flags.
- Reject unknown keys and every deferred v1 clause with an exact, actionable validation error.
- Define canonical fingerprint input so semantically identical YAML/JSON mappings fingerprint identically.
- Add fixture-backed tests for valid normalization, unsupported/unknown fields, limits, required-vs-optional
  failure classification, and a topic-sidecar-shaped inline request.
- Document the explicit reader mapping for each supported clause in code or fixture metadata so Task 2 does
  not invent unsupported semantics.

Acceptance:

- No field has an ambiguous default or an implicit broadening behaviour.
- Equivalent mapping order produces identical normalized JSON and fingerprint.
- Tests prove that unsupported clauses fail before selection.

## Task 2 - M1 resolver and MCP vertical slice

Build the shared read-only resolver and expose the minimum usable CLI/MCP slice over Task 1's frozen
contract.

Deliverables:

- Implement `resolve_retrieval_spec()` through one shared service, using the existing canonical session,
  topic, link, Constitution, and Markdown readers plus deterministic ordering and bounded limits.
- Emit an ephemeral Evidence Pack with corpus revision, canonical refs, reasons, completeness, warnings,
  resolution trace, and fingerprint. Return it inline; no cache or `get` registry is introduced.
- Add MCP `memory_retrieval_spec_preview` and `memory_retrieval_spec_resolve`, plus a CLI preview command.
  Preview validates/plans without creating a pack; resolve remains read-only and returns the pack inline.
- Add a Task Packet inline example to the developer-facing documentation without presenting it as a profile
  API.
- Add fixture, parity, missing-required, forbidden-path, truncation, timeout, corpus-change, stale-pack,
  and fetchability tests. Use a deterministic local test seam for timeouts/corpus change rather than a
  network or provider dependency.

Acceptance:

- The topic-sidecar example yields a bounded, fetchable pack to a real MCP call.
- CLI and MCP payloads are byte-equivalent canonical JSON at one revision.
- Repeated resolution at one revision yields identical refs and fingerprint.
- Required, forbidden, truncation, timeout, corpus-change, and stale-pack outcomes are proven.
- No resolution path writes to `.memory-seed/`, changes existing search ranking, or depends on Trace.

## Completion boundary

M0 and M1 are complete only after task-level reviews and a whole-branch review pass. The source proposal
stays active until this critical path is shipped; later milestones remain separate enabling work.
