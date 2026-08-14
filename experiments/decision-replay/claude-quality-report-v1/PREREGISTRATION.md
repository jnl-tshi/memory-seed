# Preregistration: corrected three-arm fresh-Claude decision replay

Status: **FROZEN FOR ONE CORRECTED INSTRUMENT PILOT.** One subject per condition is not scored evidence
of a general Memory Seed effect. Do not change this protocol, the task, or grader schema v2 after
fixture preparation; a change requires a new run ID and a recorded amendment.

## Question and contrasts

Does preserved pre-fix rationale help a fresh Claude session make a safer later implementation
decision, and is normal Memory Seed routing sufficient to expose that rationale?

Three blinded conditions separate the mechanisms:

- `historical-available` versus `no-dated-memory` tests the product-level effect of making normal dated
  memory available;
- `relevant-rationale-pushed` versus `no-dated-memory` tests the content effect when the exact relevant
  pre-fix rationale is guaranteed available through a bounded packet;
- `relevant-rationale-pushed` versus `historical-available` diagnoses retrieval/exposure as a possible
  bottleneck.

## Frozen historical case and evidence

- Source revision: `6c43f2dbbaf8bdf76d20b5293df74d969e840990`.
- Withheld reference revision: `b851cb04f7240caa5aec5493d0c1399a50ba05b1`.
- Frozen grader: schema v2 in `../claude-quality-report-v0/grade.py`.
- Relevant pre-fix evidence: entry `mse_gbc4m5m71dqmen75`, recorded 2026-08-03 20:14. Its rationale
  says runtime resolution walks upward and fixture boundaries matter; its follow-up flags the
  `quality report` cwd path-join bug as a separate, deliberately unfixed task.

The pushed packet contains only that bounded pre-fix evidence. It contains no later commit, patch,
test, hidden behavior, or reference answer.

## Conditions

### No dated memory

The historical export has dated session documents removed. Its experiment-context file contains only
an opaque receipt and a neutral statement that no supplemental rationale is supplied.

### Historical rationale available

The complete historical export retains dated sessions. Its experiment-context file is otherwise
identical to the no-memory file except for an opaque same-length receipt. Claude follows normal project
routing and may or may not retrieve the relevant entry.

### Relevant rationale pushed

The export has dated session documents removed, matching the no-memory arm, and its experiment-context
file supplies the bounded relevant entry and opaque receipt explicitly.

Labels and execution order are randomized from the recorded seed. The mapping is sealed outside all
fixtures. Every fixture is a new standalone Git repository made by `git archive` and fresh `git init`,
so the withheld fix and later objects are absent.

## Manipulation check

The byte-identical task requires every subject to read `EXPERIMENT_CONTEXT.md`, repeat its opaque
receipt, and report memory entry IDs actually relied on or `none`. Subjects are told not to retrieve
memory merely to populate the field.

Transcript audit separately records:

1. whether a tool call requested the context file;
2. whether its receipt reached a model-facing tool result;
3. whether the final response repeated the receipt;
4. whether the relevant entry ID appeared in model-facing context;
5. whether the final response claimed to use that entry.

Receipt confirmation establishes packet uptake. Relevant-rationale uptake is confirmed only when the
entry reached model-facing context and the subject reported relying on it. Availability without those
checks is not treated as content exposure.

## Frozen gates and outcomes

The primary outcome is the existing all-or-nothing four-gate result per subject:

1. hidden behavioral contract under grader schema v2;
2. public `test_quality.py` regression suite;
3. bounded changed-file scope;
4. candidate-authored regression-test change.

Secondary outcomes are descriptive per subject:

- runner elapsed time and transcript elapsed time;
- time to the last structured `Edit`/`Write` call and the post-edit tail (unavailable for shell edits);
- unique assistant messages, tool calls, output tokens, and validation commands;
- treatment exposure and claimed uptake;
- unsupported claims and residual-risk quality on later human review.

Time is not substituted for correctness. Total time is not interpreted as reasoning speed because
subjects may choose different validation breadth. The structured-edit and post-edit-tail split is a
declared proxy that makes some of that difference visible rather than forcing an unsafe maximum
validation budget.

## Contamination, exclusion, and stop rules

- Use genuinely fresh sessions with the same Claude CLI version, model argument, effort, permission
  mode, prompt, and task.
- Subjects may not use network tools, remotes, parent checkouts, other fixtures, the harness, or the
  sealed receipt.
- A run is excluded only for a recorded harness failure, provider outage, timeout, accidental reveal,
  or cross-fixture access. Wrong code, refusal, missing uptake, or failed tests remain results.
- Do not repair a completed subject. A rerun gets a new run ID, fixtures, receipts, and sessions.
- Stop if tasks differ, a fixture resolves the withheld commit, the pristine source passes the hidden
  grader, the reference fix fails, or model/configuration differs between conditions.
- Open the sealed receipt only after all three raw transcripts and blinded grader/audit outputs exist.

## Interpretation

This pilot tests instrument behavior and produces three observations only. It reports no significance,
confidence interval, or general product effect.

- Pushed passes where no-memory fails, with confirmed uptake: evidence that the supplied rationale
  helped on this case.
- Available resembles pushed with confirmed uptake: evidence that normal routing exposed useful
  rationale on this case.
- Available resembles no-memory while pushed differs: evidence that retrieval/exposure, rather than
  preserved content, is the likely bottleneck.
- All pass: current source/task is sufficient; compare process measures descriptively.
- Any faster result without confirmed relevant-rationale uptake remains a replication target, not a
  rationale effect.

No outcome changes production behavior, retrieval defaults, quality targets, or constitutional status.
