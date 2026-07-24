---
title: "Capability Status and Publishability Boundary Proposal"
date: "2026-07-16"
project: "memory-seed"
status: "superseded"
priority: "P3"
next_action: "After React Trail parity, perform an explicit security/privacy review before deciding whether to split and promote either advisory contract."
dependencies:
  - "React Trail parity and B0b acceptance"
  - "security and privacy review"
related:
  - "docs/2_Todo/memory-trace-ai-timeline-summarisation-plan.md"
  - "docs/2_Todo/memory-trace-structural-graph-enrichment-provider-proposal.md"
  - "docs/CONSTITUTION.md"
replaced_by: "../2_Todo/memory-trace-evidence-annotations-and-projection-architecture.md"
replaced_on: "2026-07-16"
---

# Capability Status and Publishability Boundary Proposal

Status: **SUPERSEDED 2026-07-16**. Capability Status moved into section 11.2 of the existing evidence
architecture; publishability split into
[`memory-seed-publishability-check-evaluation.md`](../8_Deferred/memory-seed-publishability-check-evaluation.md).
Priority: P3 after React Trail parity and explicit security/privacy review.
Source: The 2026-07-16 post-Trail platform review triage.

## Problem

Optional local capabilities (semantic retrieval, timeline summarisation, structural enrichment) need a common,
honest way to state whether they are available, how they run, and what data boundary applies. Separately, a
project needs a local pre-publication warning surface that can identify obvious private or restricted material
without claiming to decide whether publication is safe.

## Proposal

Evaluate two deliberately advisory contracts together, then split them before promotion if their security
review or owners diverge:

1. A `CapabilityStatus` envelope for optional providers: `provider_id`, `capability`, `version`,
   `execution_mode`, `network_requirement`, `privacy_scope`, `revision`, `freshness`, `cache_location`, and
   explicit warnings/unavailable state.
2. A local `memory-seed publish check` that scans declared Memory Seed metadata and artifact manifests for
   explicit private/restricted markers and common secret patterns. Its output is advisory and records
   `unknown`; it never uploads, edits, or certifies a repository.

The existing timeline summarisation and structural-provider proposals remain the owners of actual provider
behaviour. This proposal only considers shared status and boundary disclosure.

## Non-goals

- No model download, provider invocation, remote scan, telemetry, or hosted registry.
- No guarantee that secret detection is complete or that a clean report makes publication safe.
- No automatic publish block, source modification, or change to canonical document authority.
- No provider may alter ranking, actionability, or canonical decision semantics through this envelope.

## Dependencies and sequence

Do not start until React Trail parity is accepted. Before implementation, perform a targeted local
security/privacy review, identify false-positive and false-negative handling, and decide whether the two
contracts should become separate proposals. Existing provider-specific plans must retain their own capability
and data-handling requirements.

## Acceptance criteria

- Status fixtures are deterministic, local, and clearly distinguish unavailable from stale or degraded.
- The advisory check requires no network access and never modifies source files.
- Reports identify their limitations, inputs, and the source metadata that produced each warning.
- The design does not claim publication approval or conflate provider availability with authority.
