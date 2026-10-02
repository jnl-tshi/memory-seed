# Adaptive decision evidence reconstruction — implementation status

Updated: 2026-10-02. Status: offline experimental path implemented; accuracy gate inconclusive.

The two-case [temporal diagnostic](ADAPTIVE-TEMPORAL-DIAGNOSTIC.md) now separates
decision-time dialogue, contemporaneous external context, and later log
enrichment. It is a historical, single-inspection analysis, not a scored
accuracy result; the fresh gate below remains unchanged.

This is a new approach after the stopped prompt-only recovery trial. It does **not** supersede that trial's observed zero complete recoveries on its five historically examined diagnostic cases. No model was run against the new path in this implementation, and no new complete-decision rate is claimed.

## What is implemented

- `hosted/capture/disclosure.py`: user/assistant dialogue from the current Codex turn plus two preceding turn numbers per expansion, at most twenty preceding turns/ten expansions, same-rollout/session boundary, exact source coordinates and an atomic source-character cap. Tool events still define turns but their content is excluded from every decision window and its character budget (2026-10-02 amendment). It records expansion, request usage and stop reason without estimating tokens or price.
- `hosted/capture/evidence_ledger.py`: controlled cited answers for issue, selected action, deciding actor, acceptance, scope, conditions, proposal reference, topic origin and reason. Exact source spans, user-authored commitment, chronology, and multi-span antecedent links are checked. Missing reason does not erase an otherwise established choice. Structural checks are not semantic verification or memory authority.
- `hosted/evaluation/adaptive_replay.py`: provider-independent round-by-round request/response protocol. Each request sends only the new source batch and bounded cited state; responses are validated, repeat imports are idempotent, and missing provider token counts remain unavailable.
- `hosted/evaluation/adaptive_arms.py`: deterministic paired source packets for adaptive, fixed twenty-turn, and full causal-session views. The full view is unavailable rather than clipped if it exceeds a safety cap; character-budget-limited fixed spans are labelled partial.
- `hosted/evaluation/adaptive_comparison.py`: blinded, independently reviewed three-arm/two-run comparison with separate source sufficiency, complete decision, reference accuracy, rationale completeness, false acceptance, wrong actor, request counts, provider-reported tokens, and stop reasons. Unavailable comparisons are null, not zero.
- `hosted/evaluation/recovery.py`: repaired marker-coordinate allowlist for a valid `rollout_id`, with a regression test.

## Evidence and remaining gate

Synthetic focused tests validate protocol, limits, privacy shape, chronology, ambiguity, review blinding, conservative scoring and cross-module round trips. They do not validate semantic correctness on real conversations. The prior diagnostic was retrospective and selected around known decisions; the tracked corpus does not provide the required independently reviewed fresh positives and real hard negatives. The scorer cannot independently attest owner-declared root lineage or exposure and therefore keeps the fresh gate inconclusive until a separately verified upstream freshness artifact is bound to a comparison. No live capture, automatic memory promotion, provider integration, model dependency, or new API credential was added.

Next empirical step: assemble and independently source-review a root-disjoint, previously unseen corpus with complete causal rollout windows and real hard negatives; freeze source/configuration and exposure audit before extracting; run two model trials per arm and two blinded semantic reviews; then compare complete recovery and precision against the existing gate. A case whose needed context lies beyond twenty preceding turns remains incomplete under the currently approved bound, even if a full-session diagnostic arm can recover it.

## Data-readiness audit (2026-10-01)

A metadata-only inventory found 43 source-coordinate-verified rows in the historical extension (potentially 47 after its post-audit), but their labels remain provisional and some roots overlap development or previously examined groups. The clean descriptive held-out subset has only 15 rows, 14 with verified sources. These are candidate source material, not a frozen, independently reviewed fresh gate corpus.

The eight tracked negative controls are parser fixtures, not source-reviewed real hard negatives; four are marked `not_accepted`, three `proposed`, and one `accepted`, with no true-root or exposure audit. No qualifying 30-case hard-negative set was found in the tracked evaluation artifacts. Local raw rollout files exist, but their existence alone does not establish negative labels, root independence, source sufficiency, or prior exposure. Therefore the 30-positive/30-negative gate remains **inconclusive**; no adaptive model trial or live capture is authorized by this inventory. Field coverage remains a measure of recorded evidence, not confidence in semantic correctness.

Audit sources: `experiments/decision-chat-alignment/COHORT-100-REPORT.md`, `experiments/decision-chat-alignment/cohort-100/postaudit-write-anchor/POSTAUDIT-REPORT.md`, `hosted/evaluation/results/manifest.json`, and `hosted/evaluation/negative_controls.jsonl`. Only counts and classification metadata were examined for this audit; raw private conversations were not copied into the repository.

Verification: a fresh full repository run of `python -X utf8 -m pytest -q -n 0` exited 0 with 2,277 passed, 2 skipped, and 290 subtests passed. This verifies the existing offline implementation, not its real-world extraction accuracy.
