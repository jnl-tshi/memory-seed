---
memory-system-version: 2.11
tags:
  - memory-seed
  - skill
  - memory-consolidation
---

# Memory Consolidation Skill

Use this skill when compacting session history, reviewing recent work, or promoting durable facts into runtime memory.

## Procedure

1. Run `memory-seed compact` from the active runtime root.
2. Read the generated summary.
3. Identify facts that changed topology, active state, policy, skills, release behavior, runtime assumptions, or durable risk.
4. Promote active-state facts into `.memory-seed/index.md`.
5. Promote behavioral constraints into `.memory-seed/policy.md`.
6. Promote reusable procedures into `.memory-seed/skills/*.md`.
7. Leave one-off debugging traces, temporary hypotheses, superseded experiments, and raw command output in sessions only.

## Reason Boundary

- sessions preserve reason and tradeoffs.
- index.md receives only durable current conclusions.
- policy.md receives only durable behavioral constraints.
- Preserve DRAFT decision records in sessions.
- Do not copy full reason into index.md unless a short reason note is needed to prevent likely misuse.
- Preserve alternatives, rejected paths, inferred reason, and unknown-reason markers in session history.

## Commands

```bash
memory-seed compact
memory-seed compact --days 30
memory-seed compact --all
memory-seed compact --output summary.md
```

## Output

- Key session facts.
- Recommended promotions.
- Files updated or intentionally left unchanged.
- Residual stale-memory risk.
