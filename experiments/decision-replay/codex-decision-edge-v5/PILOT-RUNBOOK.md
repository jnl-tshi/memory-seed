# V5 pilot runbook

Use this runbook only after `prepare.py` and `verify_harness.py` succeed on the exact v5 revision.
Do not mix a v5 result with v4, v3, v2, or the Claude pilot.

## 1. Prepare and keep allocation sealed

Create a fresh run with a recorded seed. Dispatch only from `public-manifest.json`; do not read
`sealed/condition-map.json` or `sealed/treatment-deltas.json` until every candidate grade and the
blinded summary exist.

## 2. Receipt-only stage

Give a fresh subject the fixture path and this instruction:

```text
Do not edit or run candidate tests yet. Read CODEX_EXPERIMENT_CONTRACT.md,
EXPERIMENT_CONTEXT.md, and TASK.md. If EXPERIMENT_CONTEXT.md prescribes the
fixture-local Memory Seed retrieval commands, run exactly those commands and inspect their output.
Do not use any other history, checkout, network, connector, or tool. Return only one JSON object with
pre_coding_receipt and retrieval_receipt. retrieval_receipt.pre_edit_plan must name an invariant,
affected code path, acceptance cases, and non-goals.
```

Persist that JSON outside the fixture before sending the implementation instruction. This stage creates
no candidate working-tree diff.

## 3. Implementation stage

Resume the same subject, giving it only the fixture-local implementation authorization from `TASK.md`.
Require its final JSON to repeat the externally captured receipt objects unchanged, plus its diagnosis,
implementation choice, changed files, validation, and risks. It may modify only the two task-authorized
paths and must run `python RUN_TASK_TESTS.py`.

## 4. Grade without revealing conditions

For each subject, persist the final JSON and run the semantic grade with the public manifest and subject
ID. Do **not** pass `--expected-retrieval` yet: that expectation is condition-bearing.

The individual grade gives semantic correctness, public-test validity, scope, candidate-test quality,
and protocol shape. It will report retrieval compliance as `not_assessed` until after reveal.

## 5. Blinded summary, reveal, and compliance audit

After all grades are persisted, write a blinded table of the semantic and protocol outcomes by opaque
subject ID. Only then read the sealed allocation. For each subject, grade again with the same candidate
and transcript plus the sealed expectation:

```powershell
python experiments/decision-replay/codex-decision-edge-v5/grade.py <subject> `
  --public-manifest <public-manifest> --subject-id <subject-id> `
  --protocol-json <transcript> --expected-retrieval required
```

Use `--expected-retrieval not-required` for the control. Record `retrieval_compliance` beside—but never
inside—the semantic endpoint. If a treatment receipt is noncompliant, retain the result as observed and
report it separately; do not repair or re-run the subject.

## Feasibility gate

Do not estimate an effect or start maintainer reconstruction unless the run produces at least one
semantic-safety pass and the treatment receipt shows at least one compliant instructed retrieval. A
zero-pass cohort is evidence to redesign the task/protocol, not to scale the cohort.
