# Harness implementation specification

This file defines the runnable instrument that must be implemented and qualified before the
preregistration can be frozen. The implementation may split these responsibilities across scripts, but
must not weaken them.

## Required commands

The package should expose these local, deterministic entry points:

```text
verify_harness.py     qualify source, transformations, graders, audits, and negative controls
prepare.py            create one sealed randomized run and standalone fixtures
run.py                launch fresh builder sessions block by block and preserve raw artifacts
audit.py              inspect transcript exposure and protocol completion without revealing arms
grade.py              run semantic, public-test, scope, and candidate-test gates
maintainer_prepare.py create condition-blinded reconstruction packets
maintainer_run.py     launch fresh read-only maintainer sessions
summarize.py          reveal only after all required blinded artifacts exist
```

All raw outputs live under gitignored `runs/<run-id>-artifacts/`. Every source, prompt, context,
transcript, patch, test output, audit, grade, model/configuration record, timing record, receipt, mapping,
and summary is checksummed before reveal.

## Fixture preparation

1. Verify the source and withheld commit IDs and parent relationship.
2. Export the source with `git archive`; never clone the live `.git` object database.
3. Apply the symmetric sanitation declared in the preregistration and emit
   `fixture-transformation.json` with before/after hashes and removed-line hashes.
4. Apply condition-specific dated-memory/context changes only after the shared transformed tree is
   hashed.
5. Initialize a new Git repository, commit the pristine fixture, and verify that the withheld SHA and
   later objects do not resolve.
6. Pin the fixture's Memory Seed MCP server to the fixture's historical code and disable user-level MCP
   servers/settings.
7. Write `TASK.md` byte-identically and `EXPERIMENT_CONTEXT.md` from one template. Record unavoidable
   treatment-token counts.
8. Compare every non-treatment file across all fixtures by path and SHA-256.

The context file names the task-specific public command after dependencies are inspected. The likely
surface is `python -m unittest memory-trace/tests/test_trail_decision_edges.py`, but the harness must
prove the exact invocation against the historical package layout rather than copying this guess.

## Frozen semantic grader

The grader runs from a clean external copy of each candidate and imports hidden tests from outside the
fixture. It reports these gates separately:

- decision-row target;
- focused membership from source and target;
- entry-level edge-set equality against a sidecar-free control;
- entry-level ref regression;
- invalid-ordinal no-widening;
- single-decision `d1` behavior;
- public task tests;
- bounded file scope; and
- candidate-authored discriminating test.

The candidate test gate temporarily applies the candidate's test delta to pristine source and requires
at least one candidate test to fail, then restores the candidate patch and requires the same test set to
pass. Existing tests alone do not satisfy the gate.

The grader never reads the sealed condition mapping. Its JSON schema is versioned and frozen before the
first scored fixture.

## Required negative and positive controls

`verify_harness.py` must demonstrate all of these:

1. **Pristine source:** fails decision-edge visibility.
2. **Reference patch:** passes every semantic gate.
3. **Projection mutant:** adds the decision target to entry-level lifecycle lists; passes an obvious
   visibility assertion but fails edge-set equality.
4. **Filter mutant:** resolves the decision-row target but routes it through the entry-ID visibility
   filter; fails focused or overview visibility.
5. **Ordinal-fallback mutant:** silently falls back from a nonexistent `dN` to the entry row; fails the
   robustness gate.
6. **Truncated exposure transcript:** contains the entry ID but not the decisive phrase; audit must
   report ID exposure true and content exposure false.
7. **Pushed exposure transcript:** contains the registered exact phrase in a model-facing tool result;
   audit must report content delivery true.
8. **Interim final transcript:** ends with a waiting/progress message or malformed/missing JSON; audit
   must report protocol incomplete.
9. **Cross-arm equality:** deliberate mutation of one neutral file must make preparation fail.
10. **Object isolation:** deliberate inclusion of the withheld object must make preparation fail.

A tidy all-pass scored result is not trustworthy unless these controls first prove that the instrument
can produce every important failure state.

## Transcript and timing contract

Preserve both the CLI event stream and canonical timestamped Claude transcript. Record:

- process start/stop and exit code;
- assistant messages, tool calls, output tokens, and command strings;
- first and last edit timestamps;
- required-test completion;
- final valid JSON timestamp;
- background task start/stop/output; and
- whether the process exited while a task remained unresolved.

Total elapsed, implementation time, validation tail, and protocol completion are separate fields. A
shell pipeline's final exit code is not treated as the underlying test result without preserving and
checking the actual command output.

## Exposure audit

Before a run, store the normalized decisive span and SHA-256 in a sealed audit fixture. The audit scans
only model-facing tool results and the final response, not hidden harness files. It reports booleans and
the first matching event index; it does not print the treatment mapping.

Exact matching is deliberately conservative. Paraphrase claims are retained as self-report but do not
upgrade `confirmed_content_uptake`.

## Reveal gate

`summarize.py` refuses to open the mapping until, for every valid block:

- three raw builder transcripts and metadata files exist;
- three blinded grades and audits exist;
- three patch/evidence packets exist;
- required maintainer outputs exist or the run is explicitly summarized as builder-only; and
- all checksums verify.

Human calibration packets are sampled and sealed before reveal. Their absence blocks human-cost claims,
not the builder result.
