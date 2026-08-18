# Codex decision-edge replay v4

This package prepares fixtures and grades candidate patches for a blinded, three-arm replay of the
historical decision-qualified Trail defect. It is a **Codex collaboration-subagent instrument**. Its
observations must never be silently pooled with the sibling Claude study: subject delivery, transcript
surfaces, and exposure guarantees differ.

## Prepare a run

The harness uses only the Python standard library and local Git objects. Supply an explicit seed and
either a new caller-owned output directory or let the command use the gitignored default
`f/<run-id>-artifacts`:

```powershell
python experiments/decision-replay/codex-decision-edge-v4/prepare.py `
  --seed 20260816 `
  --run-id qualification-01
```

Preparation verifies that withheld revision `0ba56be3...` directly descends from source revision
`21749f40...`, exports the source with `git archive`, sanitizes the shared baseline, creates eight
randomized blocks of three opaque subjects, initializes 24 independent Git repositories, verifies
object isolation and clean state, and fails on any unexpected non-treatment difference. Symmetric
sanitation removes the exported `.codex/`, `.claude/`, `.cursor/`, `.gemini/`, and `.vscode/` trees plus
root `.mcp.json` in full. It also removes only the agent-active portions of `.github`:
`.github/mcp.json`, `.github/hooks/`, and `.github/copilot-instructions.md`; ordinary `.github` metadata
remains. Every removed file is manifested before adding
`CODEX_EXPERIMENT_CONTRACT.md` to every fixture. `AGENTS.md` and `.memory-seed/` remain as task context;
fixture Git hooks are disabled with repository-local `core.hooksPath`.

The transformation manifest also records the pinned source-tree name audit. Remaining MCP/settings/hook
name matches are classified as inert package or UI source, inactive seed templates, a manually invoked
script, or tests—not active root/project configuration.

Dispatch subjects only from `public-manifest.json`. The condition map and evidence metadata live in
`sealed/condition-map.json`; the exact permitted session/context delta is recorded separately in
`sealed/treatment-deltas.json`. Both are outside every subject directory. Existing output roots are
refused. Neutral contexts use clearly labeled inert padding and exactly match pushed contexts in byte
length and whitespace-token count.

## Verify

```powershell
python -m unittest discover `
  -s experiments/decision-replay/codex-decision-edge-v4/tests `
  -p "test_*.py"

python experiments/decision-replay/codex-decision-edge-v4/verify_harness.py
```

`verify_harness.py` uses one temporary three-subject block, executes the Task 1 preparation controls,
and grades real reference/mutant working trees in external temporary sandboxes. It writes no tracked run
artifact. The positive reference is the exact visibility commit plus its direct robustness follow-up;
the pre-freeze reason and immutable commit chain are recorded in `V4-AMENDMENTS.md`.

## Grade a candidate

```powershell
python experiments/decision-replay/codex-decision-edge-v4/grade.py `
  C:\path\to\standalone-subject `
  --public-manifest C:\path\to\public-manifest.json `
  --subject-id subject-0123456789abcdef `
  --output C:\caller-owned\grade.json
```

Alternatively, a caller that has already resolved the condition-free manifest may pass
`--expected-baseline <fixture-commit>`. Grading rejects before archive unless that commit exists in the
candidate repository and is exactly its current `HEAD`/tree. The candidate's current `HEAD` is never
accepted as its own authority.

The schema-v6 JSON reports separate decision-row, two-way focus, non-projection equality, entry-ref,
invalid-ordinal, singular-`d1`, public-test, scope, and candidate-test-quality gates. The hidden oracle lives
outside every candidate and builds minimal temporary `.memory-seed` corpora. The grader never reads the
sealed condition map. An optional `--protocol-json` records final-evidence completeness independently
from correctness. When supplied, it must contain a mandatory `pre_coding_receipt` captured by
orchestration before candidate edits. The object records the context receipt, evidence IDs (or `none`),
rationale propositions (or `none`), and a nonempty acknowledgement; it is external protocol evidence,
not an in-fixture candidate write.

Candidate-test discrimination uses `candidate_test_runner.py`, an external harness-owned runner that
loads the candidate test file under a fixed module name, discovers stable test IDs, and records
`unittest.TestResult` failures/errors/skips as structured JSON while suppressing candidate stdout/stderr.
Runner-owned loader, suite, result, and execution methods are created/bound before candidate import.
The pristine and candidate copies must discover the identical nonempty suite and run count; pristine
must produce at least one real assertion failure and zero errors, while candidate must produce zero
failures/errors. This mandatory result is reported as secondary `candidate_test_quality`; it does not
turn an otherwise semantically safe candidate into a top-level failure. Printed or fabricated unittest
transcripts are never scoring evidence. The runner's SHA-256 and version are included in each grade.

A preliminary AST policy rejects obvious mutation/introspection of unittest or runner infrastructure,
`__main__`/`sys.modules` runner access, and dynamic `exec`/`eval`. This is defense against accidental or
straightforward protocol interference, not a Python security boundary. See `THREAT-MODEL.md` before
running submissions from outside the intended non-adversarial agent population.

The non-projection gate covers exact sidecar-versus-control equality at these stable Python boundaries:
the Trace entry graph edge set, Trace search payload, Trace entry/chunk payload, historical
`memory_seed.retrieval.search_memory`, and historical `memory_seed.retrieval.get_chunk`. At the frozen
source revision the CLI and MCP search/get adapters delegate to those retrieval functions. Qualification
tests the shared retrieval boundary directly; it does not independently launch or certify CLI/MCP
serialization, transport, configuration, or process startup.

### Qualification vectors

`verify_harness.py` asserts every gate, plus top-level `status`, `ready_for_scoring`, and baseline status.
Semantic safety is primary: visible decision-row behavior, non-projection, and robustness behavior must
all pass. The public command and bounded scope remain separate validity conditions. Candidate-test
quality is evaluated and reported separately from that primary status.
Gate order below is decision target, focus, non-projection, entry-ref, invalid ordinal, singular `d1`,
public tests, scope, candidate discrimination.

| Control | Exact vector | Top-level |
| --- | --- | --- |
| pristine | F F P P P F F P F | fail / ready |
| unamended `0ba56be3...` | P P P P F P P P P | fail / ready |
| composite reference | P P P P P P P P P | pass / ready |
| semantic-safe / defective candidate test | P P P P P P P P F | pass / ready |
| projection mutant | F F F P F P P P P | fail / ready |
| filter mutant | F F P P P P P P P | fail / ready |
| ordinal-fallback mutant | P P P P F P P P P | fail / ready |

Separate absent-commit and mismatched-`HEAD` controls require a top-level error, `ready_for_scoring=false`,
baseline error, and all nine gates marked not-run/error.

## Interpretation boundary

Codex collaboration-subagent sessions do not provide the canonical CLI JSONL and canonical tool-result
transcript surfaces assumed by the Claude preregistration. The pushed arm therefore guarantees exposure
by embedding the bounded pre-fix D2 projection directly in the fresh subject packet. In the historical
arm, rationale uptake remains self-report and artifact evidence unless an independent capture mechanism
records model-facing delivery. That difference precludes silent cross-instrument pooling.

Removing every project-level agent configuration surface still cannot programmatically disable a
collaboration subagent's user-level tool inventory or connectors. The fixture-local contract forbids
their use, and external or cross-fixture tool use is an exclusion, but compliance requires runner/audit
enforcement. This is an instrument limitation, not a claim of structural isolation.

The candidate command is `python RUN_TASK_TESTS.py`. Every generated fixture contains this local,
cross-platform runner. It prepends that fixture's `memory-trace` directory to `sys.path`, loads only
the candidate-authored task module, and returns its unittest exit status. The candidate module is intentionally absent
from pristine source because the task requires the candidate to create it. Task 1 proves the pristine
command fails for that expected missing-module reason and that the command succeeds with a temporary
minimal module. Task 2 additionally requires actual candidate test code, a behavioral failure on
pristine source (not module/import failure), and a pass on the candidate.

Tasks 1-2 prepare/qualify fixtures and grade patches. They do not launch subjects, audit transcripts,
run maintainer reconstruction, reveal conditions, summarize scored results, or claim
transcript-confirmed retrieval.
