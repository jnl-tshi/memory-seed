# Adaptive decision evidence reconstruction — implementation status

Date: 2026-10-01. Status: offline experimental path implemented; accuracy gate inconclusive.

This is a new approach after the stopped prompt-only recovery trial. It does **not** supersede that trial's observed zero complete recoveries on its five historically examined diagnostic cases. No model was run against the new path in this implementation, and no new complete-decision rate is claimed.

## What is implemented

- `hosted/capture/disclosure.py`: current Codex turn plus two preceding turn numbers per expansion, at most twenty preceding turns/ten expansions, same-rollout/session boundary, exact source coordinates and an atomic source-character cap. It records expansion, request usage and stop reason without estimating tokens or price.
- `hosted/capture/evidence_ledger.py`: controlled cited answers for issue, selected action, deciding actor, acceptance, scope, conditions, proposal reference, topic origin and reason. Exact source spans, user-authored commitment, chronology, and multi-span antecedent links are checked. Missing reason does not erase an otherwise established choice. Structural checks are not semantic verification or memory authority.
- `hosted/evaluation/adaptive_replay.py`: provider-independent round-by-round request/response protocol. Each request sends only the new source batch and bounded cited state; responses are validated, repeat imports are idempotent, and missing provider token counts remain unavailable.
- `hosted/evaluation/adaptive_arms.py`: deterministic paired source packets for adaptive, fixed twenty-turn, and full causal-session views. The full view is unavailable rather than clipped if it exceeds a safety cap; character-budget-limited fixed spans are labelled partial.
- `hosted/evaluation/adaptive_comparison.py`: blinded, independently reviewed three-arm/two-run comparison with separate source sufficiency, complete decision, reference accuracy, rationale completeness, false acceptance, wrong actor, request counts, provider-reported tokens, and stop reasons. Unavailable comparisons are null, not zero.
- `hosted/evaluation/recovery.py`: repaired marker-coordinate allowlist for a valid `rollout_id`, with a regression test.

## Evidence and remaining gate

Synthetic focused tests validate protocol, limits, privacy shape, chronology, ambiguity, review blinding, conservative scoring and cross-module round trips. They do not validate semantic correctness on real conversations. The prior diagnostic was retrospective and selected around known decisions; the tracked corpus does not provide the required independently reviewed fresh positives and real hard negatives. The scorer cannot independently attest owner-declared root lineage or exposure and therefore keeps the fresh gate inconclusive until a separately verified upstream freshness artifact is bound to a comparison. No live capture, automatic memory promotion, provider integration, model dependency, or new API credential was added.

Next empirical step: assemble and independently source-review a root-disjoint, previously unseen corpus with complete causal rollout windows and real hard negatives; freeze source/configuration and exposure audit before extracting; run two model trials per arm and two blinded semantic reviews; then compare complete recovery and precision against the existing gate. A case whose needed context lies beyond twenty preceding turns remains incomplete under the currently approved bound, even if a full-session diagnostic arm can recover it.
