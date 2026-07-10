---
memory-system-version: 2.17
tags:
  - memory-seed
  - proposal
  - mermaid
  - skills
---

# Compact Mermaid Diagram Skill Proposal

> Status: IMPLEMENTED 2026-07-07 (unreleased), moved to `docs/2_Todo/completed/`.
> Priority: P3.
> Source: User-supplied runbook for compact rectangular Mermaid diagram generation.
> Scope: Add a lazy-loaded Memory Seed skill that teaches agents how to structure Mermaid diagrams
> into compact rectangular layouts, avoiding runaway horizontal rows and isolated bottom nodes.
> Non-goals: Do not add Mermaid rendering, semantic validation, or a new diagram parser. Do not change
> the existing rule that Mermaid should be reserved for spatial, temporal, or concurrent structure.
> Dependencies: Existing Mermaid usage guidance in `docs/2_Todo/completed/mermaid-usage-guidance-plan.md`;
> existing skill registry at `.memory-seed/skills/index.md`; seed skill registry at
> `memory_seed/seed/.memory-seed/skills/index.md`.
> Acceptance criteria: Done - `compact_mermaid_diagrams.md` exists in live and seed skill directories;
> the skill is registered in both trigger registries so it is lazy-loaded only for Mermaid layout
> tasks; seed inventory includes the skill; tests and `doctor` confirm no orphan skill.

## Problem

Mermaid's default `graph TD` and `graph LR` layout can stretch diagrams into a wide single row or
push one loose node into a long vertical baseline. That makes diagrams hard to read in IDE previews,
Memory Trace, and 1080p screenshots.

## Proposed Implementation

Add a `compact_mermaid_diagrams.md` skill with these rules:

- Build large diagrams from explicit tier rows.
- Use invisible `~~~` links to force grid rows instead of leaving many unlinked nodes in one row.
- Partition large mixed containers into internal sub-clusters.
- Break long labels with `<br>` or short slash-separated phrases.
- Check output against a compact, rectangular aspect-ratio checklist.

Register the skill in the live and seed `skills/index.md` trigger registries with layout-specific
triggers, so agents read the runbook only when authoring or repairing Mermaid diagrams.
