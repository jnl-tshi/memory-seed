---
tags:
  - memory-seed
  - governance
  - constitution
  - mcp-tools
implemented_by: mse_d1h4mf4z40epm8jz (Constitution v1.11 and adr_outcome_level_composition)
shipped: 2026-09-05
---

# Outcome-Level Composition Constitutional Amendment

**Status:** Ratified by JNL on 2026-09-05, implemented as Constitution v1.11, and verified.

## Purpose

Make correct use of Memory Seed easier than manually recreating its governed workflows. The amendment does not require fewer visible operations at any cost. It requires deterministic continuations to be composed while preserving explicit judgment, authority, validation, and provenance boundaries.

## Constitution clause

Add the following anchored principle to §3:

<!-- constitution-ref: constitution:v1#path-of-least-resistance -->
- **Make the correct path the easiest path.** Memory Seed composes mechanically determined steps behind outcome-level operations so humans and agents do not spend attention or model tokens reconstructing deterministic workflows. It stops where relevance, authority, risk, scope, or intent requires judgment, and every composed operation preserves the same validation, provenance, explainability, and human control as its underlying steps. The result must expose what was selected, what was omitted, why execution continued or stopped, and which governing guards were applied. *(Cited: `1_Inbox/agent-interaction-storylines-review.md`; `8_Deferred/agent-skill-workflow-architecture-proposal.md`; 2026-09-05 session decision.)*

## Operational interpretation

A continuation is eligible for automatic composition only when:

1. validated inputs and governing rules determine one supported continuation;
2. the continuation remains within the caller’s declared scope and budget;
3. no authority conflict, risk gate, or human approval is crossed;
4. the same core validation is used on every surface; and
5. the result remains inspectable and attributable.

Otherwise the operation returns the smallest useful evidence and an explicit judgment request.

## First proving slice

Evaluate retrieval composition: parse and rank the corpus, then hydrate the highest-confidence exact decision chunks within a declared evidence budget. Compare the composed operation with the existing search-then-fetch sequence for round trips, input tokens, evidence completeness, authority fidelity, and provenance.

## Non-goals

- No opaque all-in-one workflow engine.
- No automatic resolution of ambiguous relevance or conflicting authority.
- No weakening of validation to reduce clicks or calls.
- No immediate router framework or broad rewrite of existing MCP tools.
- No product-code change in this governance tranche.
