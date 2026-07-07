---
memory-system-version: 2.13
tags:
  - memory-seed
  - plan
  - agent-rules
  - documentation
---

# Mermaid Usage Guidance - Scope

> **Status: IMPLEMENTED 2026-07-03 (unreleased).** The Working Principles bullet below was added to
> `agent-rules.md` (live + seed twin) as specced, including the semantic-freshness clause. Source:
> external review doc `Memory-Seed Logic Capture Improvement.md` (its polymorphic-rendering /
> Mermaid-restraint recommendation).

## Motivation

Nothing in `agent-rules.md`, `session_logging.md`, or any skill states when Mermaid is or isn't
appropriate. Mermaid is already used ad hoc in this repo's own docs (`docs/2_Todo/3.0-plan.md`,
`docs/3_Spec/functionality-audit.md`, `docs/2_Todo/completed/multi-user-deep-research-report.md`,
`docs/2_Todo/user-interface-deep-research-report.md`) with no consistent rule for when it earns its
keep versus when a plain sentence or list would communicate the same thing with less risk. A broken
Mermaid block (a stray bracket, an unclosed string, a wrong arrow direction) degrades to raw,
unreadable syntax with no fallback for any renderer, human or otherwise.

## Design

A single new bullet, not a new subsystem. Add to `agent-rules.md`'s **Working Principles** section
(the existing home for short, cross-cutting rules like the POC-gate and verification-split
principles) - this is a "how to write content" rule, not session-log schema, so it doesn't belong
in `session_logging.md`.

Proposed wording:

> **Default to plain text; reserve Mermaid for spatial, temporal, or concurrent structure.** Use a
> plain sentence or list for a decision's rationale by default. Reach for a Mermaid diagram only
> when the content is genuinely spatial, temporal, or concurrent - sequence flows across
> components, entity/schema relationships, or topology - where a diagram is clearly higher-signal
> than prose. Keep Mermaid blocks small, and double-check bracket/arrow/quote syntax before
> committing. Also check semantic freshness: roadmap diagrams must be updated when shipped work
> changes status, not merely kept syntactically valid. A broken or stale block renders as misleading
> raw text with no fallback.

## Why Not More

The source doc proposes a "specialized validation tag" that forces syntax verification before
committing a diagram to memory. That's infrastructure (a parser, a gate, something that runs and
can fail) for a problem a one-line self-check rule already covers, and it doesn't fit this
project's existing lightweight-guidance style - none of the current Working Principles rely on
tooling; they're short, self-applied rules. If broken Mermaid blocks turn out to be a recurring
real problem once this guidance is in place, a deterministic `doctor` check (parse fenced
` ```mermaid ` blocks, flag unbalanced brackets) would be the natural next step - but that's
speculative infrastructure for a problem not yet observed, so it's explicitly out of scope here.

## Definition of Done

- One bullet added to `agent-rules.md` Working Principles (and its seed twin under
  `memory_seed/seed/`).
- No code changes, no new validation tooling, no control-plane version bump beyond the normal one
  that accompanies any `agent-rules.md` content change.
- Roadmap/audit docs touched in the same change are checked for semantic diagram freshness, not only
  Mermaid syntax.
