---
memory-system-version: 2.20
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
5. Before claiming a changed scope complete, run the relevant check after that scope's last
   change. Earlier or pre-change results are stale and cannot support the claim.
6. Record the command or check, changed scope, post-change execution point or freshness
   marker, outcome, and validation status. Use exactly one of `passed`, `failed`, `blocked`,
   `unavailable`, or `waived`.
7. Treat only `passed` as a passing result. `blocked` and `unavailable` state why the check
   could not run; `waived` also names its reason and the authority that granted it. A waiver
   is not a pass and does not make a completion claim verifiable.
8. Record failures with exact command, failure class, and next action. Do not use this
   proportional route to weaken a stricter project rule requiring tests before behavior changes.

## Output

- Commands run.
- Changed scope and post-change freshness marker.
- Outcome and status (`passed`, `failed`, `blocked`, `unavailable`, or `waived`).
- Omission reason where a check did not run; waiver authority where it was waived.
- Important warnings or skipped checks.
- Follow-up required before release or handoff.
