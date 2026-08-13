# Preregistration: fresh-Claude quality-report decision replay

Status: **DRAFT instrument — do not interpret a run as scored evidence until JNL approves this file and
the four frozen gates in `grade.py`.**

## Question

Does access to Memory Seed's pre-existing rationale help a fresh Claude session implement a safer fix
for a real historical defect, compared with the same repository, task, and operational rules without
dated session memory?

This is a mechanism test for the claim that preserved rationale can improve a later implementation
decision. It does not test human review cost or delayed human reconstruction.

## Frozen historical case

- Source revision: `6c43f2dbbaf8bdf76d20b5293df74d969e840990`.
- Historical change withheld from subjects: `b851cb04f7240caa5aec5493d0c1399a50ba05b1`.
- Surface: `memory-seed quality report [--json]` invoked below the active runtime root.
- Reason for selection: the defect can return a plausible but false 100% coverage result, so passing
  tests alone is insufficient unless the test contains an uncovered-decision discriminator.
- The withheld change is an instrument oracle, not a required patch shape. The hidden grader accepts
  behavior, not textual similarity to that commit.

The subject repositories are created with `git archive`, followed by a fresh `git init`. Consequently,
the historical fix and all later objects are absent rather than merely checked out behind `HEAD`.

## Arms

### Historical-rationale arm

The full repository export at the source revision, including the dated session-memory documents that
existed then. Claude follows the repository's normal routing and may retrieve that history.

### Current-state arm

The same export and identical task, except `.memory-seed/sessions/` contains no dated memory documents.
Current code, proposal documents, Constitution, index, policy, and operational rules remain available.
This isolates the incremental contribution of durable session rationale rather than comparing Memory
Seed with an undocumented repository.

The arm labels are randomized from a caller-supplied seed and sealed outside the fixture directories.

## Subject task

The byte-identical [task/TASK.md](task/TASK.md) is committed into both standalone repositories. It names
the reported symptom, preserves the report's existing honesty/read-only contract, limits writable files,
and forbids external history, network access, commits, and session-memory writes.

It deliberately does not disclose:

- the historical patch;
- the raw-cwd versus runtime-root implementation choice;
- the swallowed `OSError` mechanism;
- the hidden test code;
- the arm identity.

## Frozen gates

`grade.py` applies four separate gates:

1. **Hidden behavior:** root and nested-directory calls measure the same active runtime; the deliberately
   malformed decision remains uncovered; the CLI agrees with the Python API; an input read failure is
   not converted into a successful coverage result; and the report writes nothing.
2. **Public regression:** `python -m unittest discover -s tests -p test_quality.py` passes.
3. **Scope:** only `memory_seed/quality.py` and `tests/test_quality.py` differ from the fixture's initial
   commit.
4. **Test ownership:** the subject changed `tests/test_quality.py`, so a production-only patch cannot pass.

There is no weighted or composite score. Overall status is `PASS` only when all four gates pass; the
individual gates remain visible.

## Primary and secondary outcomes

Primary outcome, reported per arm: all four gates pass.

Secondary outcomes, never substituted for the primary gate:

- elapsed implementation time;
- input/output tokens when available;
- number of test/fix iterations;
- files opened and tests run, from the transcript;
- unsupported claims in the final explanation;
- whether the implementation explicitly preserves nearest-runtime and fail-honestly semantics.

With one run per arm, report only the two observations. Do not calculate significance, confidence
intervals, or a general Memory Seed effect.

## Contamination and exclusion rules

- Each arm uses a genuinely fresh Claude conversation.
- Subjects may not read outside their standalone repository, use network/remotes, or inspect the parent
  Memory Seed checkout.
- The same model identifier, Claude CLI version, permissions, timeout, and initial prompt are used for
  both arms and recorded before reveal.
- A run is excluded only for a recorded harness failure, provider outage, timeout, or accidental reveal.
  A wrong implementation, refusal, or test failure remains in the result.
- Do not repair a completed run. A rerun gets a new pair, seed, and two fresh sessions.
- The operator reveals the sealed arm mapping only after both graders have emitted verdicts.

## Stop rules

Stop and invalidate the pair if a subject accesses the parent checkout or sealed receipt, if the task
files differ, if either fixture can resolve the withheld commit, or if model/configuration changes between
arms.

If both pristine fixtures pass the hidden grader, the instrument has no discriminating defect and must
not run. If the historical reference fix fails, the grader is inconsistent with the historical outcome
and must be corrected before any subject run.

## Interpretation

- Treatment passes and control fails: evidence that the preserved rationale helped on this case, subject
  to transcript review for contamination and accidental cues.
- Both pass: the task/current source was sufficient; compare time, tokens, and reasoning descriptively.
- Both fail: the case or prompt may be too difficult, or the rationale may not be retrievable/actionable.
- Treatment fails and control passes: inspect startup cost, misleading memory, and retrieval choices; do
  not explain the result away.

No result changes production behavior, quality targets, retrieval defaults, or Constitution status.
