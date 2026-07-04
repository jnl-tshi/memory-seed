---
memory-system-version: 2.15
tags:
  - memory-seed
  - skill
  - local-compilation
---

# Local Compilation Skill

Use this skill when validating that a local project builds, tests, packages, or runs from the current workspace.

## Inputs

- Project root or sub-project root.
- Relevant package, build, test, or run commands.
- Known environment constraints.

## Procedure

1. Identify the nearest `.memory-seed/` runtime and project root.
2. Inspect existing scripts before inventing commands.
3. Run the smallest relevant verification command first.
4. Escalate to broader tests only when the change affects shared behavior.
5. Record failures with exact command, failure class, and next action.

## Output

- Commands run.
- Pass/fail result.
- Important warnings or skipped checks.
- Follow-up required before release or handoff.
