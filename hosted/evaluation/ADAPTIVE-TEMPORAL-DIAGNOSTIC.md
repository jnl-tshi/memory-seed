# Decision-time versus later-log diagnostic

Status: historical development diagnostic, 2026-10-02. No fresh accuracy claim.

The later session entry is **not** the decision-time answer key in its entirety.
Review each field against the dialogue disclosed at the decision anchor first.
Only then compare the later log, distinguishing (a) information already in the
dialogue, (b) contemporaneous non-dialogue context, (c) facts established after
the decision, and (d) unknown provenance. A field absent at decision time is
not an extraction miss just because the eventual log contains it.

`temporal_decision_review.py` provides an aggregate-only, two-reviewer offline
diagnostic for these labels. It requires dialogue references for `at_turn`,
later source references for `later_only`, and contemporaneous external
references for `outside_dialogue_at_turn`. Disagreement is unresolved. It
does not change the adaptive controller, the fresh-data gate, or live capture.

## Source-anchored inspection of the two Terra pilot cases

These observations are a single inspection of historically exposed cases, not
the two independent reviews required for quantitative scoring. Raw dialogue
and model responses remain owner-private outside Git.

| Case | Decision-time evidence | Model result versus that evidence | Later-log distinction |
| --- | --- | --- | --- |
| `ms-38098d7a:d1` | The assistant's turn-15 proposal at source ordinal 1001 names the 2.10.0 user-aware session-target plan, opt-in identity, legacy fallback, scope, exclusions and tests. The user gives a brief implementation approval at turn 16, ordinal 1007. | The skill-aware run selected only the generic approval instruction rather than binding it to the proposal. That is a reference/action reconstruction miss for content already visible at the decision point, separate from its citation-offset and chronology failures. | The later log says the work was **added**, names changed files, and reports tests/smoke results. Those implementation outcomes were not established by the approval itself; post-approval execution begins at least by ordinal 1027. Do not require an at-turn extractor to report completed work or test results. |
| `mse_nw47r0vpcj5tr2pj:d1` | The assistant's turn-1 statement at ordinal 374 explicitly selects a core `worktree_reconciliation.md` runbook, explains why two alternative owners are inadequate, and preserves immediate post-merge cleanup in `agent_collaboration.md`. | The skill-aware run named the new runbook but populated only one field. Missing the stated boundary and rationale is a candidate-completeness problem. However, the corpus labels acceptance `unlabelled`; this cited statement is an agent-origin design choice, not evidence of a user approval. A rule requiring user-authored acceptance for every decision may misclassify this case. | The later entry additionally records planned file inventory and baseline-test results. Their decision-time availability was not established in this inspection, so they are not scored as extraction misses. |

The two failures therefore are **not** explained solely by the logging agent
having more context. The first case has a clear, visible proposal-binding
failure. The second exposes both missing semantic fields and a possible
evaluation/validator mismatch around agent-origin decisions. Later
implementation details create a separate temporal-scoring confound. A
field-by-field verdict needs independent source review and private raw model
outputs before publishing counts or attributing every difference.

Next: freeze the anchor and dialogue-only packet for each case; obtain two
independent reviews of each field with exact source IDs and time phase; compare
candidate fields against only `at_turn` evidence; report later enrichment,
external-context gaps, extractor misses and unresolved provenance separately.
The existing 30/30 fresh gate remains unavailable.
