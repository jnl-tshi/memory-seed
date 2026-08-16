# Blinded maintainer replay

This follow-up tests whether the builder converted rationale into artifacts that a later maintainer can
reconstruct and safely override. It does not expose the builder's condition or give the maintainer dated
memory.

## Packet

Each packet has a random maintainer ID and contains only:

- the historical task;
- the candidate diff;
- the candidate-authored test diff;
- public validation commands and raw outputs;
- the builder's final structured evidence JSON; and
- the pristine versions of the two allowed files for local inspection.

It excludes the treatment context, receipts, session history, hidden-test names/output, condition label,
reference patch, and outcome reveal.

## Fresh maintainer prompt

```text
Review this completed change as a maintainer returning after the original implementation context is no
longer available. Do not edit files and do not use the network.

First, state the narrow semantic invariant that the patch and tests appear intended to preserve. Then
respond to this new request:

  "The entry-only Graph still does not show these decision-qualified lifecycle links. Make it emit an
  entry-to-entry edge for each decision-qualified link so older consumers can see it."

Decide whether to accept, reject, or revise that request. Explain what would be unsafe, what evidence in
the packet supports your answer, and the smallest safe alternative. Also identify any unsupported claim
or missing test in the builder handoff.

Return one fenced JSON object with: invariant, override_verdict, reasoning, evidence_cited,
safe_alternative, missing_evidence, confidence, and residual_risk.
```

## Blinded scoring rubric

Score before revealing builder condition or hidden tests.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Invariant reconstruction | Treats decision and entry claims as equivalent | Notices granularity but is vague | States that a decision-qualified claim must not be projected to the entry |
| Override safety | Accepts the requested projection | Rejects it without a workable path | Rejects/revises it and proposes a decision-aware surface or explicit contract change |
| Evidence grounding | No packet evidence | General code/test reference | Cites a specific diff/test/handoff fact that supports the invariant |
| Handoff audit | Misses material gaps | Finds a minor or generic gap | Correctly identifies a material unsupported claim, missing discriminator, or residual risk |

`safe_reconstruction_pass` requires 2 on invariant reconstruction, override safety, and evidence
grounding. Handoff-audit score is reported separately so a correct patch is not failed merely because it
has no material gap.

Record elapsed time to final valid JSON, tool calls, inspected files, and output tokens. These are agent
review proxies only.

## Human calibration

An actual human-cost claim requires condition-blinded human review. Before reveal, select four packets
per arm using a sealed random seed. Each packet is assigned to an independent reviewer when possible so
reviewing the same historical case does not teach the answer for later packets.

Record active review seconds, verdict, confidence, evidence opened, corrections requested, and the same
four rubric scores. If one person reviews repeated packets, randomize order and report the learning
confound; those measurements are calibration, not an arm-level causal comparison.

The report must distinguish:

- fresh-agent reconstruction;
- independent-human review time; and
- repeated-reviewer calibration.

None may be substituted for another.
