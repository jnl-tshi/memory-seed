# Lightweight Top-K and Terra Smoke Findings

Date: 2026-08-05  
Status: exploratory; not the preregistered 360-cell trial

## Result

The current decision retriever does not meet the proposed 95% Top-K target:

| K | Complete-query recall |
|---|---:|
| 1 | 13/60 (21.7%) |
| 3 | 38/60 (63.3%) |
| 5 | 47/60 (78.3%) |

No K is recommended. The Terra smoke therefore used K=5 as the best available current context, not as a passing candidate.

Terra (`gpt-5.6-terra`, Codex CLI 0.146.0) answered one frozen variant from each of the 12 tasks across three arms, for 36 cells. The corrected run produced 36/36 schema-valid answers.

| Exact check | Decision only | ADR current | ADR + Constitution |
|---|---:|---:|---:|
| ADR IDs | 0/12 | 12/12 | 12/12 |
| Authoritative refs | 0/12 | 12/12 | 12/12 |
| ADR statuses | 0/12 | 12/12 | 12/12 |
| Typed lineage edges | 6/12 | 2/12 | 2/12 |
| Constitution bindings | 1/12 | 1/12 | 8/12 |
| Evidence-bounded citations | 7/12 | 7/12 | 9/12 |
| Insufficient-evidence verdict | 1/12 | 2/12 | 12/12 |
| Completely exact cells | 0/12 | 0/12 | 0/12 |

## What this means

ADR context did its most important job: it moved concern identity, accepted authority, and status from 0/12 to 12/12. Adding Constitution context then moved exact revision-to-clause bindings from 1/12 to 8/12 and made every insufficient-evidence verdict correct.

The remaining errors are strongly mechanical:

- Terra systematically reversed lineage direction. It commonly emitted predecessor → successor, while the contract defines the revision as source and its predecessor as target. This affected branching, converging, evolved, and replaced histories.
- Terra selected extra historical or supporting bindings even when the packet already contained exact revision-scoped binding rows.
- On the missing-evidence task it correctly abstained, but also invented a `related` edge to the absent benchmark and cited a Constitution principle as material evidence.
- The first pass returned fluent answers in the wrong inner shape because the prompt named the schema without enumerating its fields. After the fields were stated explicitly, all 36 answers were schema-valid.

## Recommendation

Do not spend more model intelligence on work the resolver already knows. The MCP packet should mechanically provide—and the answer layer should copy rather than infer—ADR IDs, accepted refs/statuses, typed edge orientation, and exact revision-to-Constitution bindings. The subject should mainly explain the supplied facts and decide whether source evidence is missing.

Before a larger subject run, improve decision retrieval: Recall@5 is 78.3%, so 13 of 60 queries still lack all required entry decisions even at the largest tested K. After that, repeat this 12×3 smoke with the edge/binding fields explicitly described or prefilled; only then is the full 60-query Terra arm worth its cost.

Raw generated packets, answers, and mechanical cell scores remain gitignored under `generated/lightweight-current/smoke/`. The committed machine-readable summary is `results/lightweight-terra-smoke.v1.json`.
