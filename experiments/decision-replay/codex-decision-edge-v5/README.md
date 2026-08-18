# Codex decision-edge replay v5: prescribed Memory Seed retrieval

V5 is a new, unpooled instrument. It tests the intended Memory Seed workflow rather than whether an
agent happens to discover that historical memory exists. V4 remains frozen as a failed feasibility
pilot and must not be rescored or pooled with this package.

## Question

When an agent is explicitly instructed to use Memory Seed retrieval before coding, does its implementation
pass the withheld semantic contract more often than a task-only planning control?

The primary outcome is semantic safety. Retrieval compliance and candidate-test quality are recorded
separately and never convert a semantically safe patch into a failure.

## Two blinded arms

| Arm | Fixture state and required pre-edit workflow |
| --- | --- |
| `task-only-control` | Dated session memory is removed. The agent creates a task-only pre-edit plan from the task and source. |
| `prescribed-memory-retrieval` | Dated session memory is retained. Before editing, the agent must run the fixture-local Memory Seed adapter, search the calibrated query, fetch the returned D2 section chunk, then make a plan grounded in that result. |

Both packets have identical byte and whitespace-token lengths. Both require an invariant, affected code
path, acceptance cases, and non-goals before editing; the treatment differs only by the prescribed
retrieval workflow and the historical memory needed to execute it.

The treatment commands are deliberately explicit:

```powershell
python RUN_MEMORY_RETRIEVAL.py search --query "decision edge never projected entry level"
python RUN_MEMORY_RETRIEVAL.py get --chunk-id mse_j55kt6mq230zj2p4#decisions/d2-decision-edges-are-a-distinct-edge-set-never-projected-up-to-entry-level
```

`RUN_MEMORY_RETRIEVAL.py` calls the fixture's real `memory_seed.retrieval.search_memory` and `get_chunk`
APIs with lexical ranking. It is not a canned evidence response.

## Prepare and qualify

```powershell
python experiments/decision-replay/codex-decision-edge-v5/prepare.py `
  --seed 20260818 `
  --run-id v5-qualification

python -m unittest discover `
  -s experiments/decision-replay/codex-decision-edge-v5/tests `
  -p "test_*.py"

python experiments/decision-replay/codex-decision-edge-v5/verify_harness.py
```

Preparation uses local Git objects only, sanitizes project agent configuration, creates eight randomized
two-subject blocks by default, and emits a condition-free public manifest plus sealed allocation and
treatment-delta manifests. The task and semantic oracle remain the qualified v4 task/oracle family;
the changed experimental factor is delivery through an instructed retrieval workflow.

## Run subjects

Dispatch each subject from `public-manifest.json`, in its recorded block order. The orchestration layer
must run a receipt-only stage before allowing candidate edits:

1. Read `CODEX_EXPERIMENT_CONTRACT.md`, `EXPERIMENT_CONTEXT.md`, and `TASK.md`.
2. For treatment, execute the two stated retrieval commands and inspect their output.
3. Record `pre_coding_receipt` and `retrieval_receipt` externally.
4. Only then permit edits to the two task-authorized paths and run `python RUN_TASK_TESTS.py`.
5. Persist the final report and grade the candidate without opening the condition map.

Every `retrieval_receipt.pre_edit_plan` must contain nonempty `invariant`, `affected_code_path`,
`acceptance_cases`, and `non_goals`. In this non-adversarial experiment, externally captured receipts
are compliance evidence—not a security attestation that a model could not fabricate.

Use [PILOT-RUNBOOK.md](PILOT-RUNBOOK.md) for the exact receipt, blinded-grading, reveal, and compliance-
audit order.

## Grade

Use the condition-free semantic grade while the allocation is sealed:

```powershell
python experiments/decision-replay/codex-decision-edge-v5/grade.py `
  C:\path\to\subject `
  --public-manifest C:\path\to\public-manifest.json `
  --subject-id subject-0123456789abcdef `
  --protocol-json C:\path\to\transcript.json `
  --output C:\caller-owned\grade.json
```

After every grade and blinded summary is persisted, the controller may reveal the sealed allocation and
re-grade with `--expected-retrieval required` or `--expected-retrieval not-required`. That flag produces
`retrieval_compliance` separately; it does not affect semantic status. The grader never reads condition
allocation files.

## Interpretation boundary

V5 can test whether the specified Memory Seed workflow improves this one historical implementation task.
It cannot establish general model performance, long-horizon maintainer reconstruction, or causal effect
sizes from a small feasibility cohort. Scale only after a fresh blinded feasibility run has at least one
semantic-safety pass and no unresolved protocol defect.
