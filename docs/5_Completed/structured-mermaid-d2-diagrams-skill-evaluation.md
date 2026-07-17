---
tags:
  - memory-seed
  - completed
  - skill-proposal
  - diagrams
  - mermaid
  - d2
source: C:/Users/johnn/Downloads/structured_mermaid_d2_diagrams_skill.md
created: 2026-07-07
---

# Structured Mermaid And D2 Diagrams Skill Evaluation

Status: IMPLEMENTED 2026-07-07 - folded into `compact_mermaid_diagrams.md`
Priority: P3 unless D2 rendering/export support becomes active; P2 if folded into the existing
diagramming profile as Mermaid-first selection guidance only.
Source: `C:/Users/johnn/Downloads/structured_mermaid_d2_diagrams_skill.md`
Scope: Evaluate whether the proposed skill should become a new Memory Seed skill, replace the
current `compact_mermaid_diagrams.md` skill, or be split into current Mermaid guidance plus future
D2 support.
Non-goals: Do not implement D2 rendering, change session sidecar validation, or add dependencies from
this inbox evaluation alone.
Dependencies: `compact_mermaid_diagrams.md`, `session-decision-diagrams-plan.md`,
`mermaid-usage-guidance-plan.md`, Memory Trace rendering/export plans.
Acceptance criteria: A promoted plan decides whether D2 is documentation-only guidance, a future
rendered artifact format, or out of scope for core Memory Seed.

## Summary

The proposed skill is directionally useful. It gives agents a clear language-selection rule:
Mermaid remains the default for Markdown-native documentation, while D2 is reserved for dense,
nested, architecture-heavy diagrams where Mermaid becomes awkward or hard to maintain.

The proposal should not be implemented as a second parallel diagram skill in its current form. It
substantially duplicates the existing `compact_mermaid_diagrams.md` runbook and could create trigger
ambiguity inside the new `diagramming` profile. The strongest path is to treat it as a refinement
proposal for the diagramming profile:

- Keep Mermaid-first compact-layout rules in the current skill.
- Add a short "language selection" section that says Mermaid is default.
- Keep D2 as a future optional extension until Memory Trace/export tooling can render or validate it.

## What Is Strong

- The Mermaid-first default matches the existing Memory Seed guidance: default to plain text, use
  diagrams only when they carry spatial, temporal, dependency, or concurrent structure.
- The D2 criteria are sensible: nested architecture maps, module boundaries, service dependencies,
  repeated containers, and before/after architecture states are exactly where Mermaid can become
  hard to control.
- The D2 examples are maintainable: stable IDs, human labels, meaningful edges, and container-first
  structure are good constraints for agents.
- The shared quality checklist reinforces the current compact Mermaid skill rather than weakening it.

## Main Fit Issues

### 1. It duplicates the existing compact Mermaid skill

The Mermaid section is mostly the same as `compact_mermaid_diagrams.md`: tier rows, invisible
`~~~` links, sub-clusters, short labels, and semantic freshness. If added as a second skill, agents
could load both and get redundant guidance.

Recommendation: fold useful language-selection and D2 criteria into the existing diagramming skill
or supersede it with one renamed skill, rather than adding a separate parallel skill.

### 2. D2 is not currently part of the Memory Seed rendering contract

The active session decision diagrams plan validates and surfaces Mermaid sidecars. It does not yet
scope D2 sidecars, D2 validation, D2 rendering in Memory Trace, or D2 export. Introducing D2 as a
skill-level recommendation before the toolchain exists could produce diagrams that do not render in
GitHub or the current Explorer/Trace path.

Recommendation: D2 guidance should be conditional:

- Use D2 only in docs where the target renderer is known to support it, or where raw text is
  acceptable until rendering support exists.
- Do not use D2 for `.memory-seed/sessions/diagrams/YYYY-MM-DD.md` sidecars unless the session
  decision diagrams plan is explicitly extended from Mermaid-only to Mermaid-or-D2.

### 3. It may conflict with the no-new-default-dependency posture

Memory Seed core is intentionally local-first, Markdown-readable, and lightweight. D2 rendering would
likely add a dependency or require an external renderer if Memory Trace/export needs first-class
preview. That may be appropriate for the companion UI/export package, but not for core init.

Recommendation: keep D2 out of the core default. If adopted, it belongs behind the optional
`diagramming` profile or Memory Trace/report export work.

## Recommended Disposition

Do not promote this as a standalone skill yet. Promote it only after choosing one of these paths:

1. **Small merge into current diagramming skill (recommended now).**
   Update `compact_mermaid_diagrams.md` with a concise "Mermaid vs D2" selection rule, while keeping
   all current Mermaid layout guidance. Keep the skill filename and profile unchanged.

2. **Supersede with a broader structured-diagrams skill.**
   Rename or replace `compact_mermaid_diagrams.md` with a broader skill such as
   `structured_diagrams.md`. This requires updating `SEED_FILES`, package data, seed/live registry
   entries, tests, the `diagramming` profile, and any docs that refer to the old skill.

3. **Defer D2 to Memory Trace/export.**
   Leave the current Mermaid skill unchanged and create a future Memory Trace proposal for D2
   rendering/export support, including dependency, validation, and fallback behavior.

## Suggested Next Proposal Shape

If promoted, the active todo proposal should decide:

- Whether D2 is allowed only in ordinary docs or also in session diagram sidecars.
- Whether Memory Trace must render D2 before agents are encouraged to author it.
- Whether D2 support belongs in core Memory Seed, the optional `diagramming` profile, or the
  companion Memory Trace package.
- Whether the existing `compact_mermaid_diagrams.md` skill is updated in place or superseded by a
  renamed broader skill.

## Draft Implementation Notes If Accepted

- Update `.memory-seed/skills/compact_mermaid_diagrams.md` and
  `memory_seed/seed/.memory-seed/skills/compact_mermaid_diagrams.md`.
- If renamed, update `memory_seed/core.py` skill catalog, `SEED_FILES`, `pyproject.toml`,
  `.memory-seed/skills/index.md`, seed registry, tests, README, and functionality audit.
- If D2 sidecars are allowed, extend `session-decision-diagrams-plan.md`, `check_session_links()`,
  retrieval sidecar metadata, and Memory Trace rendering expectations.
- Add tests that a new minimal project can add the `diagramming` profile and gets the expected
  diagramming skill and registry entry.

## Evaluation Verdict

Useful idea, but not ready as a standalone skill. The current best use is as a refinement source for
the existing diagramming profile: Mermaid-first by default, D2 only when renderer support and
architecture complexity justify the extra format.

## Final Disposition

Implemented the small-merge path on 2026-07-07. The existing `compact_mermaid_diagrams.md` skill now
includes Mermaid-first/D2-specialist language selection guidance, the trigger registry routes D2
selection questions to the same skill, and the `diagramming` profile description reflects the broader
guidance. No D2 sidecar, renderer, validation, export, or dependency support was added.
