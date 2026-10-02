# Adaptive reconstruction: historical source-coverage audit

Status: partial diagnostic, 2026-10-02. **This is not a semantic accuracy result or a fresh-gate pass.** No model call, paid trial, live capture, or automatic memory promotion occurred.

## Method and provenance

The audit replays the fourteen previously examined held-out positive cases from the P0.2 paired replay. Their forty adjudicated cited source coordinates are used only to score whether the new disclosure window could expose evidence; they are never supplied as model answers. The anchor is still the last known cited event, so autonomous candidate discovery is not measured. Every source file matched its SHA-256 digest in the frozen paired replay. Per-case metadata stays in a private, untracked output file; no conversation text is written to the repository.

For each case, `audit_adaptive_sources.py` prepares the adaptive, fixed twenty-turn, and full causal-session arms. It sends null answers through the provider-independent replay to force every permitted two-turn expansion, then records the earliest batch at which all cited coordinates were visible. This is an *oracle-earliest evidence-coverage bound*, not a claim that a model would answer all controlled questions at that point. Two source projections are compared: user/assistant dialogue only, matching the older paired replay; and dialogue plus normalized tool-call inputs. The parser does not include tool results in either projection. The same 50,000-source-character and 100,000-request-character safety limits apply. Character counts are not provider tokens or prices.

| Historical positive cases (14; 40 cited refs) | Dialogue only | Dialogue + tool-call inputs |
| --- | ---: | ---: |
| All cited refs visible in initial anchor turn | 9 | 7 |
| All cited refs reachable by bounded adaptive expansion | **14** | **11** |
| Expansions needed when reachable | 0: 9; 1: 4; 2: 1 | 0: 7; 1: 4 |
| All cited refs in available fixed twenty-turn arm | 14 | 11 |
| All cited refs in available full-session arm | 9 | 7 |
| Character limit reached before all cited refs | 0 | **3** |
| Full-session arm unavailable at source cap | 5 | 7 |

All forty cited coordinates were present in both underlying projections. The twenty-turn limit did not exclude a cited reference in this selected set; large source batches were the constraint. In dialogue-only replay, five cases eventually hit the character cap **after** the cited evidence was already visible because null answers deliberately prevented early stopping. Those five are not evidence-recovery failures and must not be interpreted as expected model cost. The two projections have different evidence policies, so the better dialogue-only coverage is not proof that omitting tools is semantically safe.

A new prospective exposure snapshot found 1,709 rollout files but still 631 roots—**zero new independent roots** relative to the frozen baseline. The required fresh 30-positive/30-real-hard-negative cohort remains unavailable. The historical negative-candidate pilots had zero reviewer-agreed real hard negatives. Precision, false acceptance, wrong actor, co-reference accuracy, completeness, stopping behavior, and token/currency cost remain unmeasured for the new method.

## Improvement opportunities to test, not yet adopted

1. **Source budgeting:** tool-call inputs can consume an entire two-turn batch and block earlier dialogue. Test an explicit, provenance-preserving relevance policy for tool material on development cases; never silently clip, pretend omitted tool evidence was reviewed, or change the approved two-turn/20-turn bound.
2. **Reference binding:** the old replay commonly captured “implement the plan” without the plan. The new proposal-reference ledger needs a real semantic trial that scores antecedent linkage, amendments, and topic origin separately from source-coordinate coverage.
3. **Evidence versus confidence:** a filled field or visible citation is not a verified decision. Preserve separate scores for source sufficiency, correct issue/action/scope, acceptance actor, conditions, and rationale; missing reason may remain unknown without erasing an established choice.
4. **Cost and early stopping:** run actual provider responses before estimating calls or tokens. The null-response exhaustion used here intentionally overstates requests after an oracle could have found all cited refs, but citation visibility also does not guarantee the question contract is complete.
5. **Freshness and negatives:** source-review a root-disjoint prospective cohort with real hard negatives and a model/reviewer exposure ledger before claiming recall or precision. Do not tune the frozen held-out cases or turn these historical results into the fresh gate.

Reproduce only in a private directory outside Git: `python -X utf8 experiments/decision-chat-alignment/audit_adaptive_sources.py --private-output <new-private-json-path>`. The command refuses overwrite and Git destinations and prints aggregate counts only. Synthetic tests cover two-turn oracle coverage, unavailable references, character-budget refusal, tool-call bulk, direct CLI loading, and frozen source-hash rejection.
