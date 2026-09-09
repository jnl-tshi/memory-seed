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

## Plan Test Strategy

Before implementing a plan, declare viable tests and/or proportionate alternative checks, the affected
scope, and explicit justified exceptions. Use tests for behavior that can be tested; non-code outputs,
integration environments, and exploratory trials may need rendered inspection, contract checks,
bounded experiments, or manual observations. State what each check establishes and why it is suitable.
Select the strategy before behavior changes; execution results are recorded separately afterward.

The existing planning evidence contract carries `test_strategy`: `tests`, `alternative_checks`,
`exceptions`, `behavior_changes`, and `tests_before_behavior_change: true`. Lists may be empty, but
tests or alternative checks must be present. Declare behavior changes honestly; when true, the compiler
requires tests as well. This preserves this project's stricter tests-before-behavior policy, including
for integration or exploratory work that changes behavior. Run those tests before behavior edits and
retain the result; no new automatic test runner or completion controller is introduced.

Every exception records `reason`, `affected_scope` (planned exact paths), `compensating_checks`, `risk`,
and `authority_reference` (supplied selected evidence). Verify the source's actual authority and scope.
An exception is never itself a pass and cannot weaken the Constitution, concern-owning control files,
accepted ADRs, or a stricter project policy. A reason or approval reference does not override a stop.
If a required test cannot run, report blocked/unavailable and resolve the governing constraint before
a behavior change; do not label the plan non-behavioral to bypass it.

The compiler checks shape and bound references, not semantic adequacy, real approval, or test execution.
The planner reviews suitability and governing compatibility; the worker records actual checks and
fresh outcomes under the procedure below. Keep unrun, failed, blocked, unavailable, and waived evidence
visible at handoff.

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
