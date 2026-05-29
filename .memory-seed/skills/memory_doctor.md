---
memory-system-version: 2.1
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
