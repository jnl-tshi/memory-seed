# Fresh-Claude decision replay: quality-report runtime root

This is a two-arm, historically pinned implementation replay for a **fresh Claude session**. It asks
whether the rationale preserved by Memory Seed helps Claude make a safer later implementation decision,
not merely reproduce a known patch.

The fixture is cut from commit `6c43f2dbbaf8bdf76d20b5293df74d969e840990`, immediately before the
quality-report runtime-root fix. Each arm is exported into a new standalone Git repository. The export
contains no later Git objects, this harness, hidden grader, or reference patch.

Read [PREREGISTRATION.md](PREREGISTRATION.md) before treating any run as scored evidence.

## What differs between arms

- One arm contains the complete Memory Seed runtime and session history that existed at the pinned
  revision.
- The other contains the same code, documents, routing rules, and task, but its dated session-memory
  documents are removed.

Labels `A` and `B` are randomized. Their mapping is written to a sealed receipt outside both fixtures.
The task text and initial repository commit are otherwise prepared identically.

## Prepare a pair

From the live Memory Seed repository:

```powershell
python experiments/decision-replay/claude-quality-report-v0/prepare.py --seed 20260813
```

The command prints two absolute fixture paths and the sealed receipt path. By default, fixtures are
created below the operating-system temporary directory; receipts go into the gitignored `runs/`
directory here.

Preparation refuses existing targets. It never resets, deletes, or modifies an earlier run.

## Run the fresh sessions

Open one genuinely fresh Claude session in fixture `A` and another in fixture `B`. Do not reuse or fork
the first conversation for the second. Give both sessions exactly this prompt:

```text
Read TASK.md and implement it. Stay inside this repository and obey its experimental constraints.
```

Do not reveal the arm mapping, this harness directory, the hidden grader, or the historical reference
commit. Preserve each session's transcript plus start/end time and reported token usage when the client
exposes it. Do not let either session review the other's work.

## Grade

From this live repository, after each session has stopped:

```powershell
python experiments/decision-replay/claude-quality-report-v0/grade.py C:\path\to\fixture-A
python experiments/decision-replay/claude-quality-report-v0/grade.py C:\path\to\fixture-B
```

The grader reports four independent gates rather than a composite score:

1. hidden behavioral contract;
2. existing public quality tests;
3. bounded file scope;
4. a candidate-authored regression-test change.

Only after both verdicts are recorded should the operator open the sealed receipt and reveal which arm
had historical rationale.

## Validate the instrument itself

```powershell
python experiments/decision-replay/claude-quality-report-v0/verify_harness.py
```

This proves that the pristine historical fixture fails the hidden behavior, the withheld historical fix
passes it, the task is byte-identical between arms, and neither standalone fixture can resolve the later
reference commit.

## Interpretation boundary

One pair is an instrument pilot, not evidence of a general product effect. A useful pilot shows that the
task is solvable, the hidden grader discriminates, and the arms remain uncontaminated. A later scored
study needs multiple independently fresh sessions, fixed model/CLI versions, randomized arm assignment,
and per-arm reporting of correctness, elapsed time, tokens, rework, and unsupported claims.
