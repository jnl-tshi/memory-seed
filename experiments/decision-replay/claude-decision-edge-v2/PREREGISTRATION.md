# Preregistration: decision-edge semantic-safety replay

Status: **DESIGN COMPLETE; NOT FROZEN FOR EXECUTION.** Freeze only after the harness passes every
qualification control in `HARNESS-SPEC.md`. After freezing, any change to task text, fixture
transformation, treatment packet, grader, audit logic, model/configuration, sample, exclusion rule, or
analysis creates a new instrument version and run ID. Pilot data from instrument qualification is not
pooled with the scored study.

## Research question

When current source permits two plausible implementations, does preserved pre-fix rationale help a
fresh coding agent choose the implementation that preserves the authored semantic boundary, and does
normal Memory Seed routing expose that rationale reliably enough to produce the same effect?

This study tests three distinct mechanisms:

- **content effect:** `relevant-rationale-pushed` versus `no-dated-memory`;
- **product retrieval effect:** `historical-available` versus `no-dated-memory`;
- **exposure bottleneck:** `relevant-rationale-pushed` versus `historical-available`.

The primary contrast is pushed versus no dated memory. The other contrasts are secondary.

## Historical case

- Source revision: `21749f40e1173d0862201921ff6f41de24f3b914`.
- Withheld implementation revision: `0ba56be3b08a2fcf44090e90e754da3350526045`.
- Withheld revision subject: `feat(trace): decision-level sidecar edges reach the Trail decision row`.
- Pre-fix rationale: `mse_j55kt6mq230zj2p4:d2`, recorded 2026-07-21 20:19.
- Concern: a link-sidecar ref to `<entry_id>:dN` is parsed and validated, but the Trail does not yet
  render the decision-qualified edge.

The pre-fix decision says a decision edge is a distinct edge set and must not be unioned into
entry-level lifecycle lists. Its decisive proposition is that a claim about one decision of an entry
does not license the broader claim about the whole entry. The withheld implementation therefore:

1. reads decision edges separately;
2. resolves their targets after decision rows exist;
3. adds the far entry to a focused view as membership only; and
4. leaves entry-level consumers indistinguishable from a sidecar-free control.

The pushed arm receives only the bounded, pre-fix `memory_get_chunk` projection for
`mse_j55kt6mq230zj2p4:d2`: its Summary, D/R/A block, Validation, and Follow-up. It receives no later
session, withheld patch, hidden test, grader rule, or reference answer.

## Symmetric fixture transformation

The source revision contains a public draft and one code comment that repeat the decisive proposition.
Leaving them present would let every arm discover the treatment content outside dated memory. Every
fixture is therefore made from the same minimally sanitized source before arm-specific memory changes:

1. export source revision `21749f40...` with `git archive`;
2. remove `docs/3_Spec/draft/decision-level-link-sidecar-refs.md`;
3. remove only the answer-bearing explanatory comment in `memory_seed/retrieval.py` that says a
   decision-qualified edge does not license its entry-level equivalent; do not change executable code;
4. write and record a transformation manifest containing path, original hash, transformed hash, and
   exact removed line hashes;
5. initialize a fresh standalone Git repository so the withheld commit and later objects do not exist.

The harness must prove that all non-treatment files are byte-identical across arms. It must also search
the no-memory fixture for the normalized decisive phrase and its registered variants; any occurrence
outside the neutral experiment context invalidates preparation. This controlled sanitation narrows the
claim: the experiment measures the causal value of rationale content under constrained context, not the
natural discoverability of every answer-bearing document in the historical repository.

## Conditions

Each block contains one fresh subject from each condition. Labels and execution order are randomized
from a recorded seed and sealed until every artifact in the block exists.

### No dated memory

Dated session documents are removed. `EXPERIMENT_CONTEXT.md` contains an opaque receipt and a neutral,
length-padded statement that no supplemental rationale is supplied.

### Historical available

The complete pre-fix dated sessions remain available through the historical Memory Seed runtime.
`EXPERIMENT_CONTEXT.md` is otherwise neutral and length-padded. The subject follows ordinary project
routing and may retrieve or fail to retrieve the relevant entry.

### Relevant rationale pushed

Dated session documents are removed, matching the no-memory arm. `EXPERIMENT_CONTEXT.md` contains the
bounded pre-fix projection described above, plus an opaque receipt. Padding and wrapper structure match
the other arms; unavoidable treatment-token differences are recorded.

## Sample and randomization

- Eight independently initialized fresh builder sessions per arm: 24 total.
- Eight randomized blocks of three, each containing all conditions exactly once.
- The same Claude Code version, model, effort, permission mode, task, timeout, environment, and fixture
  resource limits within and across blocks.
- Blocks run sequentially. Order within each block is randomized. A provider or harness failure stops
  the block; the entire block is rerun under a new block ID and none of its partial results are scored.
- No subject is repaired, resumed, or reused.

Eight per arm is sized only to detect a large case-specific difference. For example, a near-complete
pushed-arm success rate and a low control rate can separate under an exact binary comparison. Smaller
differences will remain unresolved. No result is generalized beyond this task/model configuration.

## Manipulation check: proposition-level exposure

Entry-ID exposure is insufficient. The registered non-leading span is
`"D2 of B supersedes D1 of A" does not license "B supersedes A"`. After Unicode quote/dash folding and
whitespace collapse, its UTF-8 SHA-256 is
`4b09d8c7c23cc27937f9d497c1bc7a38030692eac9fabfea4bd36d75b2b3df32`. The auditor performs no semantic
paraphrase matching.

For each transcript the auditor records:

1. context-file request and receipt delivery;
2. receipt repeated in the final JSON;
3. relevant entry ID in model-facing content;
4. exact decisive proposition in model-facing content;
5. a direct read or retrieval action that delivered the proposition;
6. the subject's declared memory evidence and rationale propositions used.

`confirmed_content_uptake` requires items 4 and 5 plus a non-`none` final declaration consistent with
the proposition. Item 3 alone remains ID-level exposure. The pushed arm must reach 8/8 proposition
delivery or the instrument fails. Claimed use is an outcome, not an exclusion.

## Primary outcome

The primary binary outcome is `semantic_safety_pass`. It requires all of:

1. the decision-qualified edge is visible and terminates on the named decision row;
2. focusing either endpoint at depth one keeps the far entry visible;
3. no equivalent edge appears in the entry-level graph, search, CLI, MCP, or derived entry lifecycle
   lists; the entry-level edge set equals a sidecar-free control;
4. existing entry-level sidecar refs retain their behavior; and
5. the implementation changes only the allowed files and its candidate-authored regression test passes.

The first three requirements distinguish the intended semantic decision. A patch that makes the edge
visible by projecting it onto entries fails even if its visible Trail test passes.

## Secondary outcomes

- `visible_behavior_pass`: the decision edge is visible in overview and focused Trail views.
- `non_projection_pass`: entry-level consumers remain equivalent to the control.
- `robustness_pass`: a nonexistent ordinal on a multi-decision entry draws nothing, while `d1` on a
  genuinely single-decision entry may terminate on its entry row.
- `candidate_test_discriminates`: the subject's test fails on pristine source and passes on its patch.
- `protocol_complete`: the final response contains valid JSON for every required field.
- implementation-choice classification, assigned from the blinded diff before hidden tests:
  `separate-stream`, `hybrid`, `entry-projection`, or `other`.
- time to first edit, last edit, required-test completion, and protocol-complete final response;
  validation-tail time is reported separately from implementation time.
- tool calls, output tokens, validation commands, changed-file count, unsupported claims, and residual
  risk disclosure.
- confirmed content uptake and self-reported use.

Missing final fields never make a subject look faster: elapsed time is recorded, but a subject without a
protocol-complete final response is classified `protocol_incomplete` and excluded from completion-time
comparisons while remaining in correctness results.

## Maintainer reconstruction and safe override

Every builder artifact is passed to a new, condition-blinded maintainer session using
`MAINTAINER-REPLAY.md`. The maintainer sees the patch, candidate tests, public validation output, and the
builder's final evidence JSON, but no original condition, dated memory, hidden-test detail, or reference
patch.

The maintainer must explain the invariant and respond to a counterfactual request to make the same
decision edge visible in an entry-only consumer. The reconstruction outcome is binary:

- identifies that decision-level and entry-level claims are not equivalent; and
- refuses projection while proposing a decision-aware surface or explicit requirement change.

Fresh maintainer sessions provide an independent discontinuity/reconstruction measure, not a human-cost
measure. A human calibration is reported separately and is required before claiming anything about
human review effort: a condition-blinded human reviews a preregistered random sample of 12 packets (four
per arm, sampled and sealed before condition reveal) using the same rubric and records active seconds,
confidence, corrections, and safe-override verdict. If independent human packets cannot be assigned
without repeated-case learning, report the timings as calibration only, not an arm comparison.

## Analysis

- Intention-to-treat: all valid sessions stay in their assigned arm regardless of retrieval or claimed
  use.
- Report arm counts, rates, exact binomial intervals, and risk differences.
- Primary inference: pushed versus no-memory `semantic_safety_pass`, two-sided Fisher exact test and an
  exact risk-difference interval. Treat the p-value as case-specific evidence, not a product claim.
- Secondary contrasts and all timing/token outcomes are descriptive and clearly labeled exploratory.
- Report historical-arm results twice: intention-to-treat and stratified descriptively by confirmed
  proposition uptake. The uptake-stratified view is not causal because retrieval is post-treatment.
- Do not combine builder and maintainer outcomes into one score. Report whether safe builder patches
  produce more reconstructable evidence as a separate transition table.
- Do not compare elapsed times for protocol-incomplete subjects. Use median and full range; no normality
  assumption and no substitution of speed for correctness.

## Exclusions and stop rules

A run is excluded only for a recorded provider outage, harness failure, timeout, accidental reveal,
cross-fixture access, non-fresh session, or model/configuration mismatch. Wrong code, refusal, missing
memory uptake, failed tests, or incomplete protocol remain outcomes.

Stop before scored execution if any qualification control fails, including:

- tasks or non-treatment files differ across arms;
- the withheld commit resolves in a fixture;
- the pristine source passes the visibility oracle;
- the known entry-projection mutant passes non-projection;
- the reference patch fails any semantic gate;
- the truncated-proposition transcript is counted as content exposure;
- an interim/waiting response passes the final-schema gate; or
- the pushed packet contains post-fix material.

Stop during execution for a reveal, cross-arm contamination, or configuration drift. Freeze completed
valid blocks; do not silently replace individual outcomes.

## Interpretation matrix

- Pushed outperforms no-memory with confirmed pushed uptake: evidence that the preserved rationale
  changed the implementation choice on this case.
- Historical resembles pushed with confirmed uptake: evidence that normal routing delivered useful
  rationale on this case.
- Historical resembles no-memory while pushed differs: evidence that exposure/retrieval is the likely
  bottleneck.
- All arms choose the separate stream: another correctness ceiling; current source/task was sufficient.
- All arms project: the task or oracle may be underspecified, or the rationale packet is insufficient.
- Pushed improves builder safety but not maintainer reconstruction: rationale helped the immediate
  choice but was not converted into durable, reviewable evidence.
- Maintainers reconstruct from all arms equally: the resulting code/tests dominate the later handoff,
  even if memory influenced the builder.

No outcome changes production behavior, retrieval ranking, constitutional status, or quality targets.
