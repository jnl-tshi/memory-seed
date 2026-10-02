# Adaptive decision evidence reconstruction

Status: approved in conversation on 2026-10-01; offline implementation complete, empirical accuracy validation pending. See [implementation status](ADAPTIVE-RESULTS.md).
This is a new offline development experiment after the stopped prompt-only trial.
It does not reopen that trial's prompt-revision budget or its failed accuracy claim.

## Intent and boundaries

For a decision candidate at a current Codex turn, inspect that turn and then
look backward in batches of two historical turns. Preserve the original Codex
turn grouping: a user input and the assistant messages/tool events under its
task-started boundary count as one turn. Only user and assistant dialogue is
disclosed as evidence; tool calls remain part of turn grouping but not the
window or its character budget (user amendment, 2026-10-02). Inspect no more
than twenty preceding turns, ten expansion batches, and never cross the session
start. The current turn is available initially, so the maximum is twenty
preceding turns plus the current turn, matching the historical lookback. The code must also cap
source characters and serialized requests; a huge turn can exhaust the text
budget earlier without clipping a quoted source silently.

Track evidence-backed answers for issue, selected action, deciding actor,
acceptance/commitment, scope and exclusions, conditions, referenced
proposal/version, topic origin, and stated reason. A reason can be unknown
without invalidating an otherwise confirmed choice. An explicit user direction
may be the topic origin. Each populated answer has exact original-source
citations. Only source text can establish acceptance. If a reference such as
"that plan" points to several statements, all necessary antecedents are
listed; uncertainty remains unresolved. No answer is inferred from a
summary, generic model knowledge, or later events.

The controller stops when every question has a supported answer, or when the
historical window, session start, or safe text budget is exhausted. Exhaustion
with gaps is an incomplete result. It must never become semantic completeness
or memory authority automatically. Evidence already read is retained; each
new request contains only newly disclosed source messages plus the bounded
evidence ledger. Freeze input and model configuration before any scoring.
Keep raw source and actual responses in owner-private output outside Git.

Open-source coreference models may propose local span links, but may not
authoritatively resolve proposal/whole-discussion references. The offline
comparison should include a no-library baseline first. Any optional model
must have a checked license, pinned version and domain-specific held-out
evaluation; do not silently add a new dependency or provider credential.

## Tasks

### Task 1 — Marker coordinate compatibility

Correct the known marker-coordinate whitelist regression. Add rollout_id
   to permitted marker fields and test a valid full marker as well as a
   rejected evaluation-metadata key. Keep source privacy validation.
### Task 2 — Bounded two-turn disclosure controller

Add a provider-independent offline adaptive controller. It yields the
   current turn and successive two-turn backward batches from one session,
   validates exact coordinates and source order, enforces the twenty-turn and
   character budgets, and records requests/response usage. Its state and
   retry semantics are deterministic. No live adapter or model call.
### Task 3 — Cited question and reference ledger

Add a typed, cited question and reference ledger. Validate answer spans
   and multi-statement antecedents against disclosed source messages,
   preserve unknowns, and distinguish confirmed decision from fully
   explained decision. Require independent coverage checks before complete
   status, not model self-assertion. Topic origin is either a supported
   introduction, the explicit user direction itself, or unresolved.
### Task 4 — Offline comparison and measurement

Extend offline evaluation with a blinded comparison against fixed and
   full-window source baselines on source-reviewed cases. Report source
   sufficiency, candidate completeness, reference-link accuracy, false
   acceptance/wrong actor, tokens and requests per case, and stop reasons
   separately. Previously examined cases are development/regression only.
   Existing fresh-data gate remains 30 supported unseen positives and 30
   independently reviewed real hard negatives across disjoint true roots,
   two independent model runs and two masked reviewers, 80% complete
   recovery, 95% precision, zero false acceptance/wrong actor. Unknown
   exposure or labels keep the gate inconclusive.

## Validation

Write failing focused tests before each behavior change. Cover direct user
choice without a stated reason, agreement to a multi-message proposal,
amendments and exclusions, ambiguous "that", false acceptance, separate
topics, earliest session boundary, exactly twenty preceding turns, huge
turn, repeat/retry, unchanged coordinates, and no duplicate token charges
for already disclosed evidence. Verify private packet shape, run-targeted
tests and independent reviews. Run full suite at the stable point, classify
environment/baseline failures honestly, and do not land while a load-bearing
review finding remains.
