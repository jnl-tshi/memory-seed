# V3 amendment plan

## Global constraints

- Create a new **Codex decision-edge v3** instrument; retain v2 and its pilot report unchanged.
- Do not change production code, the Claude instrument, historic source/withheld commits, or the pushed
  pre-fix D2 rationale.
- Run a fresh three-subject blinded pilot only after all amended harness tests and qualification controls
  pass. Never pool v2 and v3 subjects.
- Keep agents condition-blind and use a short, gitignored, patch-writable fixture root under the primary
  checkout.

## Task 1 — Amend and qualify the v3 fixture contract

Create a separate `codex-decision-edge-v3/` package by adapting v2. Its subject context must name a
fixture-local cross-platform test runner, `python RUN_TASK_TESTS.py`, that prepends `memory-trace` to
the local import path and runs the candidate-created test module. Add that generated runner identically
to every fixture and qualify it from a subject fixture after a reference patch.

Amend `TASK.md` so that required behavior explicitly includes: valid `target:d1` on a singular-decision
target resolves to the target entry row; invalid `target:dN` on a multi-decision target draws no edge and
does not widen to the entry; and the candidate regression suite covers multi-decision d2, singular d1,
and invalid d99. Update task/context tests and the public command used by the grader accordingly.

Make actual-run output default or be documented as a short root under `.codex/fixtures/` in the primary
checkout. Ensure that root is gitignored and verify fresh Codex agents can patch fixtures through a
primary-relative apply_patch path. Preserve v2's no-network, baseline, scope, sanitation, and semantic
grader controls; update only version/instrument names and schema where necessary. Add a `V3-AMENDMENTS.md`
explaining why v2 is not pooled.

## Task 2 — Review, qualify, and run the fresh v3 pilot

Independently review Task 1. After approval, run the complete v3 suite and full one-block qualification.
Prepare one sealed, randomized three-subject v3 block in the short primary-checkout fixture root. Launch
three fresh `gpt-5.6-terra` high-reasoning Codex subagents with only their opaque fixture path and the
standard task prompt. Preserve final JSON, diffs, and grade reports; grade against the public manifest
before reveal. Reveal only when the block is artifact-complete.

Report arm-level semantic, visible, non-projection, robustness, candidate-test, and protocol outcomes.
Do not scale to 24 in this task: state whether the v3 pilot is clean enough to justify it.
