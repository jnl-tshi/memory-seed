# Implementation plan

## Scope

Implement the fixture-preparation and frozen semantic-grading slices of the Codex decision-edge replay
without changing production code or the Claude instrument. Launch, transcript audit, reveal, summary,
and maintainer stages remain out of scope.

## Preparation pipeline

1. Resolve the pinned source and withheld commits and require the source to be the withheld commit's
   direct parent.
2. Export the source once with `git archive` into a private build directory and extract regular files
   with traversal and link rejection.
3. Delete the preregistered draft and exact explanatory comment. Recursively remove the complete
   exported `.codex/`, `.claude/`, `.cursor/`, `.gemini/`, and `.vscode/` surfaces plus root `.mcp.json`,
   plus `.github/mcp.json`, `.github/hooks/`, and `.github/copilot-instructions.md`, regardless of
   filenames/content. Preserve other `.github` metadata. Add the fixture-local agent contract. Record
   source/transformed hashes plus a SHA-256 for every removed line while retaining `AGENTS.md` and
   `.memory-seed/`; record and classify inert source/template filename matches from the pinned tree audit.
4. Copy the resulting symmetric baseline into 24 opaque subject directories: eight blocks, each with
   one randomly assigned subject per arm and a separately randomized execution order.
5. Apply only the allowed treatments: the exact sanitized-baseline set of session Markdown paths and
   `EXPERIMENT_CONTEXT.md`. Copy the same `TASK.md` bytes into every fixture and pad neutral contexts to
   pushed-context byte/token dimensions.
6. Initialize and commit each fixture in a fresh Git repository, prove the source/withheld objects do
   not resolve, and require a pristine working tree.
7. Compare all path/hash pairs after excluding only paths enumerated in the sealed treatment-delta
   manifest; keep `.gitkeep` and unexpected session paths in the comparison and abort on any difference.
8. Write a condition-free public manifest, mapping and treatment-delta manifests under `sealed/`, and an
   artifact checksum index.

## Qualification

The standard-library unittest suite covers revision ancestry, sanitation evidence, treatment session
counts, task identity, sealed mapping placement, object isolation, clean fixtures, output refusal, and
cross-arm `.gitkeep`/unexpected-file mutation controls. It also imports the withheld object locally into
a disposable copied fixture repository and proves the isolation guard rejects it.

`grade.py` first requires a caller-supplied prepared fixture commit (directly or via the condition-free
public manifest), proves that object exists and equals the candidate's current `HEAD`/tree, then exports
that verified baseline into an external temporary sandbox. It overlays the full working-tree delta and
runs the frozen external semantic oracle, the exact public task command, an
exact two-path scope gate, and candidate-test discrimination. Discrimination applies only the candidate
test delta to pristine source, then uses an external harness-owned runner and runner-owned
`unittest.TestResult` to require identical nonempty discovered test IDs/counts, at least one pristine
assertion failure with zero errors, and zero candidate failures/errors. Candidate stdout/stderr and
fabricated unittest transcript text are suppressed and never interpreted. Missing modules, imports,
runtime/teardown errors, unreachable AST tests, conditional test counts, runner schema failures, and
timeouts do not count.
Git/Python redirection variables and inherited Python paths are removed from every subprocess. The
external candidate-test runner's version and SHA-256 are recorded in grader schema v4. Its loader,
suite, result, and bound execution methods are created before candidate import. Preliminary AST checks
reject obvious unittest/result/suite/loader mutation, `__main__`/`sys.modules` runner introspection, and
`exec`/`eval`; `THREAT-MODEL.md` defines why this remains a non-adversarial experiment control rather
than a security sandbox.

The non-projection gate compares sidecar and sidecar-free controls at the Trace graph/search/chunk and
historical retrieval search/get boundaries. Frozen-source CLI/MCP search/get adapters share those
retrieval functions; serializer/transport startup is intentionally outside this gate and is not claimed.

`verify_harness.py` prepares one three-subject block in a temporary directory and re-executes the Task 1
controls on that block. It qualifies executable candidates for pristine source, the composite reference,
the unamended visibility reference, and projection/filter/ordinal-fallback mutants. See
`INSTRUMENT-AMENDMENTS.md` for the pre-freeze composite-reference correction. No qualification artifact
is written under `runs/`. Every control has a frozen complete nine-gate vector; an unexpected extra
failure/error, top-level status change, readiness change, or baseline failure aborts qualification.

## Remaining stages

Builder launch, transcript/timing audit, maintainer reconstruction, condition reveal, and analysis are
not implemented by Tasks 1-2. A manual three-subject Codex pilot is recorded in
`PILOT-20260816.md`; it exposed a subject-facing public-command defect and an unstated `d1` fallback
requirement, so it is not a scored result and must not be pooled. The instrument is not ready for scored
execution until those defects, the remaining launch/audit/reveal stages, and their controls are resolved
under a newly frozen instrument version.

## Explicit limitation

Pushed exposure is guaranteed by packet construction. Historical uptake is not transcript-confirmed
without independent capture and is assessed only from self-report/artifacts. Results are not pooled with
Claude runs. Repository files cannot disable user-level subagent tools/connectors; subjects are forbidden
to use them, and detected external or cross-fixture use excludes the run.
