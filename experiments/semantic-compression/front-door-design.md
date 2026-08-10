# Front-door carry-forward ablation

Status: selector and protocol specified before answer-key authoring or first scoring run. This is a
development-set diagnostic, not confirmatory Stage 2 and not a natural-authoring experiment.

## Question

Can the useful lessons from the failed lean-DRAFT pilot improve retrieval or reduce first-view context
without repeating its semantic loss?

This experiment tests two separable changes:

1. rank the complete canonical decision while exposing exact identifiers through a dedicated lexical
   field;
2. present a lossless complete-D/R/A front door, optionally followed by one query-selected F/T evidence
   block, while keeping the complete raw decision immediately available.

It does **not** test whether people write better entries under new guidance, whether a reader understands
or remembers them, or whether a preview may replace canonical prose.

## Frozen development corpus

Reuse the prior pilot's exact frozen source revision, 100-decision sample, 30 rationale-plus-identifier
targets, and 60 independently worded queries. This makes the comparison paired with the existing
`raw` and `lean_front_door` results. It also inherits the enriched-target limitation: results do not
generalize to all decisions.

Before scoring, assert the source revision, corpus fingerprint, selected-target fingerprint, existing
query SHA-256, new selector SHA-256, and source-only answer-key/review hashes. The selector code is
committed before answer-key authoring. Answer keys contain only exact canonical source spans and are not
available to projection or ranking code.

## Retrieval ablation

Every retrieval arm ranks the complete raw decision body. Titles, headings, topics, tags, inferred
topics, semantic embeddings, and recency stay disabled so the identifier field is the only changed
variable.

1. `body_only`: raw body with no lexical-term metadata, matching the prior raw control.
2. `current_lexical_terms`: raw body plus Memory Seed's current extracted lexical terms.
3. `authored_exact_terms`: raw body plus every uncapped, boundary-checked backtick-authored identifier
   term from canonical D/R/F fields. No basename or location-stripped alias is synthesized.
4. `union_terms`: raw body plus the union of current and authored terms.

Use the shipped BM25F field weight without tuning. Report semantic and identifier queries separately.
Bootstrap paired differences by the 30 target decisions, not as 60 independent observations.

## Presentation ablation

Presentation happens only after ranking. Assert identical rank vectors for every display arm.

1. `raw`: complete canonical decision block.
2. `current_lean`: the already-measured first-D/first-R/two-boundary/six-anchor selector.
3. `complete_dra`: every D, R, and A field block, byte-for-byte and in source order.
4. `query_evidence`: `complete_dra` plus at most one complete F/T block chosen solely from the query and
   source by exact-identifier match, then content-token overlap. It cannot inspect target labels,
   rankings, answer keys, or scores.

`A:` remains visibly rejected material and is never renamed as an accepted constraint. No sentence is
summarized, normalized, capped, or relabelled. The projection falls back to byte-identical raw on a
missing D or R, an unknown field-like bullet, malformed structure, an exception, or a projection that
is not shorter than raw. Every result retains a source reference and full-source affordance; their fixed
transport overhead is reported separately from body bytes.

## Source-only evidence key

For each of the 60 frozen queries, a context-minimal author receives only opaque packet ID, query, and
canonical source. It records one to three exact source spans sufficient to support an answer. Mechanical
validation requires every span to occur verbatim in source, rejects duplicates and whole-source keys,
and binds exactly one key to every query. A separate source-only review accepts or rejects sufficiency
before the first scoring run.

Evidence-span recall is a stricter deterministic presentation diagnostic than token overlap. It is not
human comprehension: a visible span may still be misunderstood, and an omitted span may have an
equivalent formulation elsewhere.

## Measurements and gates

Preserve raw measurements; no composite may hide a regression.

- Retrieval: Recall@1/3/5 and MRR for semantic and identifier queries, plus paired 95% bootstrap
  intervals by target.
- Presentation: mean/median body-byte and token-proxy ratios, exact required-evidence recall, all-spans
  retained rate, fallback rate/reasons, D/R/A exact-span integrity, identifier boundary precision and
  recall, and fixed source-affordance overhead.
- Invariants: raw text is the ranking body in every arm; display rank vectors are identical; every
  projected character is source-derived except the fixed source affordance; every displayed identifier
  has exact source-boundary proof.

Development success requires all of:

1. retrieval/display rank parity is 100%;
2. projection and identifier source-grounding is 100%;
3. semantic MRR does not fall by more than 0.02 versus `body_only`;
4. identifier MRR improves over both `body_only` and `current_lexical_terms`; a confidence interval
   crossing zero is reported as promising, not validated;
5. `query_evidence` retains at least 95% of required evidence spans and has no more than a 5 percentage
   point all-spans-retained loss versus raw;
6. median first-view body context is at least 20% lower than raw after including fixed affordance
   overhead.

Any provenance, rank-parity, or structural-integrity failure rejects the implementation regardless of
efficiency. Passing these development gates would justify a new, preregistered human task measuring
answer correctness, expansion behaviour, bytes-to-correct-answer, reading time, and delayed recall. It
would not authorize a DRAFT-format or canonical-storage change.
