---
memory-system-version: 2.18
tags:
  - memory-seed
  - skill
  - memory-doctor
---

# Memory Doctor Skill

Use this skill when validating a Memory Seed runtime, migration, bootstrap repair, or package seed change.

## Checks

- `AGENTS.md` exists and routes to nearest `.memory-seed/`.
- `.memory-seed/agent-rules.md` exists and defines operating-mode workflow.
- `.memory-seed/project-bootstrap.md` exists and is bootstrap/repair only.
- `.memory-seed/index.md` contains topology, active state, inheritance, and skill pointers.
- `.memory-seed/policy.md` contains behavioral constraints only.
- `.memory-seed/skills/` contains task runbooks.
- `.memory-seed/sessions/` contains dated append-only logs.
- `.memory-seed/archive/` contains archived prior control-plane snapshots when versions were replaced.
- Every `.memory-seed/skills/*.md` runbook is registered in `skills/index.md`; an unregistered file is an orphan skill (warned, non-fatal).
- When a `.memory-seed/` runtime exists, each present entry-point file (`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`.github/copilot-instructions.md`) routes into it — either ours (has `memory-system-version` frontmatter) or a foreign file carrying our `<!-- BEGIN memory-seed -->` block. A foreign file with no block is an orphaned runtime (warned, non-fatal); run `memory-seed update` to inject the block.
- No stale `.AGENTS/` paths are presented as the v2 target shape.
- Legacy `.AGENTS/` fallback remains tested when compatibility is required.

## Commands

```bash
memory-seed doctor
memory-seed compact --days 30
python -m unittest discover -s tests
```

## Output

- Pass/fail status.
- Missing or stale files.
- Version mismatches.
- Suggested repair path.
