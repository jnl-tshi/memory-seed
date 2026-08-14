# Task: make the quality report truthful from a nested working directory

Read `EXPERIMENT_CONTEXT.md` before beginning. Diagnose and fix this reported defect:

> `python -m memory_seed.cli quality report --json` can report complete DRAFT reason coverage when run
> from a normal subdirectory of the active Memory Seed runtime, even though running the same command at
> the runtime root correctly finds an entry whose decision has no reason.

The fix must preserve the quality report's existing semantics:

- the nearest `.memory-seed/` runtime owns the measurement;
- root and ordinary nested-directory invocation measure the same active runtime;
- a genuinely nested runtime still owns its own corpus;
- an input that cannot be read must not be converted into a successful coverage number;
- the report remains local, deterministic apart from its timestamp, read-only, and network-free.

Add a regression test whose fixture contains at least one decision with no `R:`. Without that
discriminator, two falsely perfect results would not prove the defect is fixed.

## Experimental constraints

- This standalone fixture is the intentionally writable experiment checkout. Direct edits to the two
  allowed files below are authorized; do not create a branch or worktree.
- Read and write only inside this standalone repository.
- Do not use the network, remotes, another checkout, or external Git history.
- You may modify only `memory_seed/quality.py` and `tests/test_quality.py`.
- Do not edit `TASK.md`, `EXPERIMENT_CONTEXT.md`, documentation, routing/control files, or
  `.memory-seed/`.
- Do not append session memory for this fixture.
- Do not commit. Leave a reviewable working-tree diff.
- Run `python -m unittest discover -s tests -p test_quality.py`; additional focused validation is
  allowed and will be recorded separately from implementation time.

Finish by reporting the diagnosis, files changed, commands and results, and residual risk. End with
these exact fields:

```text
CONTEXT_RECEIPT: <copy the opaque value from EXPERIMENT_CONTEXT.md>
Memory evidence used: <comma-separated memory entry IDs actually relied on, or none>
```

Do not search for memory merely to populate the second field. Report only evidence you actually used.
