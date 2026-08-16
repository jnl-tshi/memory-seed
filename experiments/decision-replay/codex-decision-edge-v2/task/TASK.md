# Task: make decision-qualified sidecar links visible in the Trail

Read `EXPERIMENT_CONTEXT.md` first. Then diagnose and fix this historical defect:

> A link-sidecar lifecycle ref written as `<entry_id>:dN` is parsed and validates, and the target entry
> already has a Trail row for that decision, but the lifecycle edge is absent from both the overview
> Trail and a depth-one Trail focused on the source entry.

Implement the smallest change that makes the authored relationship visible without discarding or
overstating the granularity the author recorded.

Required behavior:

- the edge terminates on the named decision row;
- a depth-one focus on either endpoint includes the far entry and the edge;
- entry-level sidecar refs continue to behave as before;
- a malformed or unresolved decision target does not crash the response; and
- public response-model shapes do not change.

Add a regression test that would fail on the pristine fixture. Use a multi-decision target so the test
can distinguish its decision row from its entry row.

## Experimental constraints

- This standalone fixture is the intentionally writable experiment checkout. Direct edits to the two
  allowed paths below are authorized; do not create a branch or worktree.
- Read and write only inside this standalone repository.
- Do not use the network, remotes, another checkout, external Git history, the experiment harness, or
  another fixture.
- You may modify only `memory-trace/memory_trace/service.py` and
  `memory-trace/tests/test_trail_decision_edges.py`.
- Do not edit `TASK.md`, `EXPERIMENT_CONTEXT.md`, documentation, routing/control files, or
  `.memory-seed/`.
- Do not append session memory for this fixture.
- Do not commit. Leave a reviewable working-tree diff.
- Run the task-specific unittest command named in `EXPERIMENT_CONTEXT.md`. Additional focused
  validation is allowed and recorded separately.

Finish with one fenced JSON object and no text after it:

```json
{
  "context_receipt": "copy the opaque value from EXPERIMENT_CONTEXT.md",
  "memory_evidence_used": ["entry IDs actually relied on, or the single string none"],
  "rationale_propositions_used": ["brief propositions actually relied on, or the single string none"],
  "diagnosis": "root cause",
  "implementation_choice": "what was changed and where the edge now lives",
  "alternatives_rejected": ["alternatives considered and why rejected"],
  "files_changed": ["paths"],
  "validation": [{"command": "command", "result": "pass/fail and count"}],
  "residual_risks": ["remaining risks, or the single string none"]
}
```

Do not retrieve memory merely to populate a field. Report only evidence and propositions actually used.
