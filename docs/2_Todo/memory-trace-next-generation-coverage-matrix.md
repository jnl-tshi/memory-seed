---
title: "Memory Trace Next-Generation Coverage Matrix"
date: "2026-07-11"
project: "memory-seed"
status: "active-integration-matrix"
parent: "memory-trace-product-and-system-architecture-blueprint.md"
---

# Memory Trace Next-Generation Coverage Matrix

Status: Active companion matrix for the Memory Trace next-generation plan set.
Priority: P0 for Memory Trace planning hygiene before React/API/evidence-pack implementation.
Source reference: Integration pass applied from `../4_Reference/memory-trace-next-generation-plan-document-set.md` on 2026-07-11.
Scope: Classify existing Memory Trace, Trail, graph, topic, AI-summary, report, and distribution plans against the new blueprint/spec set.
Non-goals: No code implementation, no retirement of partially complete active plans, no change to canonical graph semantics.
Dependencies: `memory-trace-product-and-system-architecture-blueprint.md`, `memory-trace-next-generation-implementation-roadmap.md`, `../3_Spec/graph-edge-contract.md`, `../3_Spec/functionality-audit.md`.
Acceptance criteria: Every existing substantive Memory Trace plan is classified as preserved, active-unique, completed-history, reference, or deferred; no unique active acceptance criteria are lost.

## Summary

The new Memory Trace document set should become the top-level planning entry point, but it does not fully replace the active implementation plans already in `docs/2_Todo/`.

Resolution:

- Promote the next-generation blueprint, roadmap, frontend, evidence/annotations/projection, hosted/security, and commercialisation documents into `docs/2_Todo/`.
- Promote the Trail/search/graph UX and derived-artifact provenance contracts into `docs/3_Spec/`.
- Keep existing active implementation plans where they still own concrete remaining work.
- Preserve completed plans as historical evidence; cross-link them to the new governing documents rather than reopening them.

## Coverage Matrix

| Existing document | Status after integration | Coverage decision | Unique active requirements preserved |
|---|---|---|---|
| `docs/2_Todo/memory-trace-distribution-plan.md` | Keep active | Blueprint preserves the separate Trace source/product boundary, public retrieval service, and no-fork parser/ranker rule. | Optional-extra packaging, deprecation shim, no-default-web-dependency guarantees, and release/documentation follow-through remain here. |
| `docs/2_Todo/memory-trace-ai-timeline-summarisation-plan.md` | Keep active | Derived-artifact provenance contract governs evidence/citation packaging; AI plan remains implementation-specific. | Local/BYOK provider first, terminal-agent adapter later, schema-constrained output, disabled-by-default AI, no session mutation. |
| `docs/2_Todo/memory-trace-topic-neighbourhoods-plan.md` | Keep active | UX spec governs graph/Trail presentation; topic plan owns core `topics:` contract and remaining Trace/MCP topic work. | Phase 4 indexed-topic rendering, MCP topic-management tools, optional `topics suggest`. |
| `docs/2_Todo/session-decision-diagrams-plan.md` | Keep active | Derived-artifact contract and evidence-pack plan cover export provenance; diagram plan owns sidecar convention and Phase 3 report/handover pack. | Exportable report/handover pack acceptance criteria and Mermaid sidecar constraints. |
| `docs/2_Todo/completed/memory-trace-product-and-trail-view-plan.md` | Completed history | Blueprint and UX spec now govern future product/Trail evolution. | Naming, `branch:` capture, package/command name, and initial Trail concept remain historical decisions. |
| `docs/2_Todo/completed/memory-trace-ui-audit.md` | Completed baseline/reference | Frontend architecture plan supersedes future UI architecture; audit evidence remains a baseline for parity fixtures. | Token baseline, microcopy fixes, edge/status color semantics, and contrast follow-ups are preserved as baseline evidence. |
| `docs/4_Reference/memory-seed-market-fit-report.md` | Reference | Commercialisation report preserves the strategic pricing/positioning read. | Market-problem fit distinction, institutional-memory wedge, and competitor landscape remain source evidence. |
| `docs/4_Reference/21st-dev-components.md` | Reference | React decision makes component references more relevant, but direct adoption still requires license/design review. | Inspiration-only posture remains; no copied dependency without separate evaluation. |
| `docs/3_Spec/graph-edge-contract.md` | Canonical spec | Not superseded. New UI docs consume it. | Edge kinds, authored/computed distinction, validation authority, and read surfaces. |
| `docs/3_Spec/functionality-audit.md` | Current-system baseline | Not superseded. Updated only to record the promoted next-generation planning set. | Existing implemented/unreleased functionality inventory. |

## Resolved Clashes

- **Vanilla UI vs React migration.** Resolved by sequencing: keep vanilla as fallback until parity, package-wheel smoke tests, and product-owner sign-off.
- **Free Trail vs commercial wedge.** Resolved by making local single-project Trail free and monetising advanced analysis, cross-project views, hosted collaboration, managed AI, exports, and enterprise controls.
- **Graph as primary surface vs Trail-first product.** Resolved by role separation: Trail is the primary chronological evidence surface; graph is a specialised topic/document/relationship exploration surface.
- **AI summaries vs authoritative memory.** Resolved by Evidence Packs and provenance manifests: generated output is derived, cited, and non-authoritative unless explicitly promoted.
- **UI docs vs graph contract.** Resolved by authority boundary: `graph-edge-contract.md` remains canonical; UI docs cannot redefine edge semantics.

## Active Follow-Through

1. Use `memory-trace-product-and-system-architecture-blueprint.md` as the top-level Memory Trace plan.
2. Use `memory-trace-next-generation-implementation-roadmap.md` for phase sequencing.
3. Keep old active plans linked from the blueprint where their implementation details remain unique.
4. Do not move distribution, AI summarisation, topic-neighbourhood, or decision-diagram plans to completed until their remaining acceptance criteria are done or explicitly split.
