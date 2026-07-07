---
memory-system-version: 2.13
tags:
  - memory-seed
  - codex
  - proposal-review
  - roadmap
status: draft
---

# Proposal Synergy Evaluation

## Summary

Codex reviewed the active `docs/2_Todo/` proposals against `docs/3_Spec/functionality-audit.md`, `docs/2_Todo/NEXT_STEPS.md`, shipped 2.12/2.13 behavior, and the existing Memory Seed runtime model.

The roadmap is directionally coherent, but several proposals were written before later shipped work and now need reconciliation. The main theme is that Memory Seed already has more of the substrate than some plans assume: Memory Lense V1 exists in-package, `build_related_entry_graph()` is shipped, `link suggest`/`link show` are read-only graph surfaces, `links check` validates entry YAML in both layouts, and `agent_collaboration.md` already owns Git-first fanout patterns.

## Cross-Proposal Dependency Graph

```text
related_entries P1 shipped
  -> supersedes P1
      -> supersession-aware importance_score
          -> optional ranking experiments

git commit linking P1
  -> commit-reference term in importance metadata

failed-approaches logging
  -> better evidence for future related/supersedes entries

Mermaid guidance
  -> roadmap diagrams checked for semantic freshness

Memory Lense V1 shipped
  -> Pillar B distribution decision narrowed
  -> graph edge contract needed before more UI/ranking work

agent fanout workflow
  -> agent_collaboration.md recipe
  -> possible future CLI scaffolding evaluation

DOCX Windows render lessons
  -> seed-skill proposal
  -> possible render-verification workflow evaluation
```

## Clashes To Resolve

- `3.0-plan.md` still presents Pillar B as a decided separate UI package, while Memory Lense V1 shipped in 2.13 as `memory-seed[lense]`. The active decision is now resolved: the UI has been extracted as `memory-trace`; the canonical plan is [`../memory-trace-distribution-plan.md`](../memory-trace-distribution-plan.md).
- `user-interface-deep-research-report.md` still reads as pre-Lense research and mentions no persistent cache, while shipped Lense has an outside-repo rebuildable SQLite cache and graph/search UI.
- `related-entries-generation-plan.md` correctly says P1 shipped read-only, but stale P1/Definition-of-Done wording still includes `link add`.
- `interaction-frequency-ranking-plan.md` claims Option C P1 can ship now while relying on supersession dampening that cannot exist until `supersedes` ships. Split raw related-degree exposure from supersession-aware scoring.
- `functionality-audit.md` previously said "4 of 5" logic-capture proposals remained proposed while listing all five; the audit should say "5 of 5" until any one ships or is rejected.
- A roadmap Mermaid label still implies the migration command is deferred even though it shipped in 2.12.
- `docx-render-windows-seed-lessons.md` is an active seed-skill proposal but is missing from `NEXT_STEPS.md` and `functionality-audit.md`.
- `Memory-Seed Logic Capture Improvement.md` is source material now that its actionable ideas have been split into scoped plan docs; leaving it without a status block makes it look like a competing active plan.
- `agent-fanout-workflow-plan.md` should not treat worker agents as `participants:`. Workers are handoff sources by default; only the orchestrator writes shared memory/control-plane files unless explicitly delegated.

## Hidden Synergies

- `link show` should become the read surface for decision-graph metadata: `related_entries`, `supersedes` / `superseded_by`, `commits`, `related_degree`, and eventually `importance_score`.
- `links check` should use one entry-YAML validation path for `related_entries`, `supersedes`, and `commits` rather than growing parallel validators.
- `importance_score` should be exposed before it influences default search ranking. Ranking behavior stays stable until fixture-backed ranking experiments prove value.
- `build_related_entry_graph()` is the canonical source for explicit curated edges and backlinks. Memory Lense can layer derived `topic`, `agent`, and `day` edges over it without forking explicit-edge parsing.
- Failed-approach logging strengthens future supersession decisions: failed attempts recorded under `A` are empirical evidence, not a new graph edge type.
- The DOCX Windows render lessons reinforce the fanout workflow's bounded automation and verification-split rules: one writer should own mutation/render cleanup, while separate read-only validators can inspect rendered pages.

## Recommended Priority Order

P0 - Roadmap hygiene and shared contracts:

1. Fix stale roadmap/documentation state: stale P1 wording, stale UI status, proposal counts, missing roadmap entries, and stale Mermaid labels.
2. Keep the shared graph/validation contract aligned for `related_entries`, `supersedes`, `commits`, `inbound_relation_count`, and `importance_score` so CLI, MCP, Lense, and `links check` do not diverge.

P1 - Low-risk guidance and graph semantics:

3. Ship failed-approaches logging guidance and Mermaid usage guidance independently; both are small control-plane changes with low implementation risk.
4. Ship `supersedes` P1 before any surface claims supersession-aware scoring.
5. Ship git commit linking P1 after choosing the shared entry-YAML validation shape.

P2 - Read-only surfacing before behavior changes:

6. Expose raw `related_degree` metadata via read-only surfaces before changing default ranking.
7. Add commit-reference contribution only after commit linking exists and commit validation is in place.
8. Expose `importance_score` as inspectable metadata before allowing it to influence default search ranking.

P3 - Deferred automation and mutation:

9. Defer related-entry backfill / `link add` until real hand-editing pain appears.
10. Defer access-frequency telemetry until raw metadata has usage evidence and privacy/retention rules are specified.
11. Keep fanout CLI scaffolding and render-verification workflows in evaluation until the documentation recipes have been exercised manually.

## New Research And Evaluation Loops

### Pillar B Distribution Decision - RESOLVED 2026-07-05

Evaluate whether Memory Lense should remain an in-package optional extra or spin out into a separate companion package.

**Outcome:** decided to spin out a separate companion package, now named `memory-trace`; the scoped
plan is [`../memory-trace-distribution-plan.md`](../memory-trace-distribution-plan.md).
This evaluation loop is closed.

Inputs (as weighed):

- shipped `memory-seed lense` behavior
- package footprint and dependency isolation
- graph/contributor/stats gaps
- possible VS Code or desktop shells

### Fanout CLI Scaffolding

Evaluate a local-first command that emits task packets, suggested branches/worktrees, validation checklists, and handoff templates.

Constraint: it must not spawn agents, mutate branches, or become a hosted orchestration platform.

### Render Verification Workflow

Evaluate whether a future Windows DOCX render skill should include an agent-collaboration subrecipe:

- one writer renders and performs cleanup
- read-only validators inspect page images/contact sheets
- findings return to the orchestrator
- bounded rework loop applies

## Proposed Document Updates

- Update `3.0-plan.md` to mark shipped 2.12/2.13 increments and reopen Pillar B distribution.
- Update `user-interface-deep-research-report.md` as historical research partially superseded by Memory Lense V1.
- Update `related-entries-generation-plan.md` so P1 is read-only and `link add` is deferred.
- Update `supersession-edges-plan.md` to choose `supersedes` and state it gates supersession-aware scoring.
- Update `interaction-frequency-ranking-plan.md` into raw related-degree first, supersession-aware score second, ranking experiments later.
- Update `git-commit-entry-linking-plan.md` with precise newest-entry/same-turn edit rules and full commit validation.
- Update `failed-approaches-logging-plan.md` to keep failed approaches as `A` evidence, not graph edges.
- Update `mermaid-usage-guidance-plan.md` to include semantic freshness, not just syntax.
- Update `agent-fanout-workflow-plan.md` with Level 2/3 justification, handoff-only workers, `shared_file_policy`, bounded loop fields, and no agent-spawning CLI.
- Update `docx-render-windows-seed-lessons.md` into a normal active seed-skill proposal/status.
- Update `NEXT_STEPS.md` and `docs/3_Spec/functionality-audit.md` to reflect all active proposal surfaces.
