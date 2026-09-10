---
memory-system-version: 2.20
tags:
  - memory-seed
  - skill
  - systematic-debugging
---

# Systematic Debugging

Use this skill when diagnosing an unexpected failure, regression, or behaviour whose cause is not already
established. It makes debugging evidence-led while not creating a parallel execution controller, task queue,
or branch workflow.

## Required Debugging Record

Keep a concise record in the existing task, plan, issue, or handoff surface. Before editing, record:

1. **Observation or reproduction** — the actual behaviour, expected behaviour, and a reproducible command,
   check, or observation when one is available. If reproduction is unavailable, state the evidence boundary
   rather than guessing.
2. **Relevant recent changes and scope** — inspect the changes, inputs, environment, and affected boundary
   most likely to explain the observation. Do not begin from an unbounded codebase search or an assumed
   culprit.
3. **Causal trace** — follow the relevant control flow, data flow, state transition, or external boundary
   far enough to identify where the observed and expected paths diverge.
4. **Falsifiable causal hypothesis** — state the claimed cause, why it would produce the observation, and
   the discriminating observation that would falsify it. Name the causal premise so equivalent wording or a
   patch variant remains recognisably the same hypothesis.
5. **Smallest discriminating change** — make the least invasive change or observation that distinguishes the
   hypothesis from realistic alternatives. A syntax repair, rerun, or larger speculative rewrite is not a
   discriminating hypothesis test by itself.
6. **Actual verification** — rerun the relevant reproduction or another current check after the change.
   Record the command/check, outcome, and any unavailable or blocked verification with its reason.

## Failed-Hypothesis Threshold

Track failed **independent causal hypotheses**, not edits or command executions. A failure counts only when
an independently stated causal hypothesis was tested by a discriminating observation and that observation
did not support it.

- Repeating a command, repairing syntax, or trying several patches for the same causal premise does not add
  another independent failure.
- Variants of the same hypothesis remain one attempt even when their wording, implementation, or test input
  changes. State a new causal mechanism and its discriminating observation before counting a new attempt.
- The tracked project default is **three** failed independent hypothesis-led attempts. It is a default to
  evaluate, not a universal empirical truth.

Resolve the nearest runtime's tracked `delivery_quality.failed_hypothesis_threshold` with
`memory_seed.planning.parse_delivery_quality` (or `resolve_delivery_quality` for a supplied mapping),
including any permitted tightening-only local/task override. Record the effective threshold before the first
hypothesis test. Missing configuration uses the default of three; malformed recognized configuration stops
explicitly. Obey the effective value, including tightened values of 1 or 2.

At the effective threshold of failed independent hypotheses, stop blind patching and reconsider the
architecture, boundaries, assumptions, or observation model. Continuing is allowed only after recording a
new rationale for why the next step is justified and what architectural reconsideration ruled in or out.
Any further blind patch is rejected until that rationale exists.

## Procedure

1. Reproduce or observe the problem, then inspect relevant recent changes and scope before proposing a fix.
2. Trace the causal path and write one falsifiable causal hypothesis with its discriminating observation.
3. Make the smallest discriminating change or collect the observation. Record whether it supported or
   falsified the hypothesis.
4. If the hypothesis failed, count it only when it is independent under the threshold rule. Do not inflate
   the count for repeated execution, syntax repair, or variants of the same cause.
5. At the effective threshold, perform and record architectural reconsideration before any
   further change. If continuing, record the new rationale first.
6. Verify the accepted change against the current observation. Do not call a remembered or pre-change result
   verification.

## Handoff

Report the initial observation, causal trace, hypotheses and discriminating evidence, independent-failure
count, any architectural reconsideration and continuation rationale, the accepted change, and fresh
verification. Preserve existing worktree, Task Packet, review, integration, and session-memory ownership.

## Do Not Load When

- The cause is already established and the task is a narrow, routine implementation with proportionate
  verification.
- The task is a normal code review, planning activity, or execution handoff with no unexpected behaviour to
  diagnose.
