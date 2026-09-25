# Origin, timing, and reviewer-signal hypothesis check

## Question

Do the current gold alignments support these proposed priors?

1. User-origin decisions are normally front-loaded before execution.
2. Agent-origin decisions normally arise during implementation or review.
3. Decision records are normally written after implementation is complete.
4. Reviewer agents can be detected reliably, with names as an optional hint rather than a dependency.

## Result

The strong versions of the first three claims are **not established by this cohort**.

- Only **7/50** gold rows carry explicit `user|agent` origin metadata. That is too little coverage for a reliable origin-conditioned timing rule.
- The explicit subset contains 3 user-origin and 4 agent-origin rows.
- User-origin rows are not cleanly pre-execution: 3/3 include implementation-shaped source evidence and 0/3 cite tool-shaped evidence.
- Agent-origin rows do lean toward execution/review evidence: 2/4 are implementation-shaped and 1/4 are review-shaped. The sample is too small to turn that tendency into a rule.
- 50/50 records are contemporaneous with or later than their latest cited causal evidence, allowing one minute for heading precision. The median lag is 2.2 minutes. This supports record time as an upper search boundary, but it does **not** prove implementation was complete.

The reviewer-detection assumption holds only partially:

- 8 rows are manually marked as review-shaped.
- A reviewer-like nickname/path identifies 1/8.
- Child dispatch-prompt text identifies 1/8 and review-shaped output in the cited turn identifies 8/8.
- Combining name, prompt, and output signals identifies 8/8, but also fires on 26 non-review rows. Names alone also fire on 0 non-review rows.
- Against these phase labels, the combined signal's apparent precision is 23.5%; this is a ranking feature, not a reliable reviewer classifier.

## Design implication

Treat origin, reviewer identity, Plan mode, and phase position as **ranking features**, not hard filters:

- `origin=user` may raise the weight of earlier user instructions and approvals.
- `origin=agent` may raise the weight of implementation discoveries, review findings, and assistant reasoning.
- Reviewer naming should be encouraged for observability, but core detection should combine child lineage, dispatch prompt, review output, and workflow metadata.
- Decision-record time is an upper search boundary. A separately detected implementation/review phase boundary is still needed before claiming the record follows completed execution.

## Limits

- Explicit origin coverage is only 7/50 and is concentrated in recent records.
- Source-coordinate verification corrected 21 mismatched declared timestamp(s) during analysis (5 over one second; maximum 1296000.0 seconds); the source JSONL coordinate is treated as authoritative.
- Phase labels are conservative heuristics over manually cited source-role and actor metadata; they are not independently annotated phase gold labels.
- Reviewer-signal evaluation is row-level and small. A prospective cohort should record reviewer role, phase boundaries, and decision time directly.
- No raw conversation or reasoning-summary text is serialized in the result artifact.
