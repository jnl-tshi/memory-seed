# Independent semantic-review handoff

Two fresh, read-only reviewers independently read all fourteen masked held-out packets,
all candidate meanings and supplied source evidence. Both completed; neither read parser code,
raw-results.json or paired-results.json. HEAD unchanged, git diff --exit-code -- hosted/capture passed.
Both judged ZERO complete matches for either arm. This is descriptive AI review, not human gold.
Field reconciliation has NOT been completed.

Vectors: issue/action/scope/acceptance_actor/conditions/reasons, E equivalent, D different,
I insufficient. Best candidate indices are zero-based. Unlisted arms emitted no candidates:
index null, IIIIII, complete false. Every listed complete flag is false.

| Case | Arm | Reviewer1 index/vector | Reviewer2 index/vector |
| --- | --- | --- | --- |
| ms-38098d7a:d1 | A | 0 / IIIDDE | 0 / IIIDDE |
| ms-38098d7a:d1 | B | 0 / IIIEDE | 0 / IIIEDE |
| ms-3cad2a35:d2 | A | 2 / IDIDDI | 2 / IIIDDI |
| mse_a58avhtbcy9djpa0:d1 | A | 0 / IDIDDI | 0 / IDIIDE |
| mse_eszq6qxf2jck32e8:d1 | A | 0 / IDIDDI | 0 / IDIDDD |
| mse_fx1gm0x6p1sts4y2:d1 | A | 0 / IIIEDI | 0 / IIIEDI |
| mse_fx1gm0x6p1sts4y2:d1 | B | 0 / IDIEDD | 0 / IDIDDD |
| mse_nttx32yw5ejypz5m:d2 | A | 0 / IDIDDI | 0 / IDIDDI |
| mse_nw47r0vpcj5tr2pj:d1 | A | 0 / IDIDDI | 0 / IDIDDI |
| mse_ssxkdsjq8d0knk4v:d1 | B | 0 / IDIDDI | 1 / IDIDEI |
| mse_v7pdg66vgfbctyfj:d1 | B | 0 / IDIDDE | 0 / IDIDDE |
| mse_vjb1kgdq26c5b38y:d1 | A | 2 / IIIEDI | 2 / IIIEDI |
| mse_vpqwta8c6m8yj6nk:d1 | A | 0 / IIIDDD | 0 / IIIDDD |
| mse_z61np2tq3zkg01ew:d1 | B | 0 / IDIDDE | 1 / IDIIDE |
| mse_z8tp67yhcrtkq110:d1 | A | 1 / IEIEDI | 1 / IEIEDI |
| mse_ztcsrx4hw0b6kxdv:d2 | A | 1 / IDIDDD | 1 / IIIDDD |

## Shared findings

- Generic issue and null scope were never filled from gold.
- Drafts frequently select startup/configuration prose, an unrelated proposal, or an implementation directive
  without extracting the concrete chosen action.
- Several candidates borrow acceptance from agent reports or an earlier implementation authorization.
- Material conditions often disappear; conditions extracted from wrappers are not decision conditions.
- One candidate substantially preserves the accepted design-system choice, but still lacks issue/scope
  and a material palette constraint.
- Missing reasons were not penalized when none was stated in the supplied source.

## Disagreements to preserve or reconcile

- ms-3cad2a35 action: wrong release sequence versus insufficient truncated action.
- mse_a58avhtbcy9djpa0 acceptance/reason: wrong attribution/missing target reason versus source insufficient
  for acceptance and no explicit reason stated.
- mse_eszq6qxf2jck32e8 reason: absent target reason versus conflicting startup-search rationale.
- mse_fx1gm0x6p1sts4y2 B acceptance: grounded user acceptance versus acceptance attached to wrong action.
- mse_ssxkdsjq8d0knk4v B best candidate: index0 avoids false rejected/actor claim; index1 preserves more
  procedure conditions but still false overall.
- mse_z61np2tq3zkg01ew B best candidate: index0 coherent backend recommendation versus index1 closer
  frontend content; neither captures target design-system recommendation.
- mse_ztcsrx4hw0b6kxdv action: wrong broad package plan versus unextracted filter commitment.

## Evidence locations

The corresponding masked private packet in owner-local temporary storage contains exact rollout, turn,
and source_ordinal for each case. Do not commit the raw packet. Arm mappings are in the sanitized
`paired-results.json`, outside reviewer packets.
Full reviewer narratives were returned to the source thread by semantic_review_one and semantic_review_two;
this handoff preserves all categorical judgments and disagreements, not their full narrative text.
