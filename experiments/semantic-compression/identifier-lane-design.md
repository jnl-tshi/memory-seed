# Identifier-lane normalization holdout

Status: completed held-out diagnostic. This file records the protocol frozen before scoring; selector
and target pins landed in `6b810e7b`, query/review pins landed in `8e4adb94`, and the one official score
run produced `identifier-lane-results.md` plus the interpretation in `identifier-lane-audit.md`.

## Question

Does normalizing exact identifier evidence at the BM25F field boundary improve retrieval over the
current raw `lexical_terms` representation without reducing semantic-query performance?

The first front-door run is not reused as evidence. It exposed the defect on 30 development targets;
this test uses 30 decisions from different source entries within the same frozen 100-decision sample
and newly authored queries. This is a narrow identifier-enriched holdout, not an independent corpus or
a general-production estimate.

## Arms

Every arm ranks the complete raw decision body through the shipped BM25F implementation, with its
weights unchanged. Headings, topics, tags, semantic embeddings, and recency remain disabled.

1. `body_only`: raw decision body, no lexical-term field.
2. `current_lexical_terms`: current extracted values, unchanged.
3. `normalized_current_terms`: the same current values after the scorer's own `_normalize` function.
4. `normalized_authored_terms`: exact notable identifiers from author-backticked D/R/F evidence,
   normalized with the same production function; no basename or location alias.
5. `normalized_union_terms`: normalized union of current and authored exact terms.

The normalized-current arm is the minimal defect correction. Authored and union arms are upper-bound
ablations, not automatic implementation recommendations.

## Held-out targets and queries

Select 30 rationale-bearing decisions with at least one exact authored identifier already represented
in the current extracted lexical field, excluding every
source entry represented in the earlier 30-decision pilot. Stratify by source-length tertile and pin
the ordered target fingerprint. The non-authoring `freeze-info` command is the only operation allowed
while these pins are pending; `query-packets` fails closed until selector and target pins match.

For each target, a source-only author creates:

- one 6-32 word semantic query with no exact identifier;
- one 6-32 word identifier query containing exactly one declared, boundary-exact source identifier.

Three authors each receive ten disjoint packets. They see source and allowed identifiers, but no arm,
scorer, earlier result, or ranking, and the query artifact records that access contract plus author IDs
and models. Mechanical validation rejects metadata/arm leakage, duplicate queries, wrong identifier
boundaries, any declared source identifier in a semantic query, and copied five-word source windows.
A separate source-only reviewer must record a reason and explicitly accept target specificity,
naturalness, and absence of source-copying before query and review hashes unlock scoring.

## Measurements and controls

- Recall@1/3/5 and MRR, reported separately for semantic and identifier queries.
- Paired 95% bootstrap intervals by target decision.
- Per-query target rank/score, lexical-field exposure, top five, and full-order hash for every arm.
- Counts of full-order, target-score, and target-rank changes versus body-only.
- A synthetic sensitivity control where the current raw `rare_symbol.py` representation must remain
  unreachable and the normalized representation must score through `lexical_terms` and rank first.

The sensitivity control is a harness validity check, not a performance result.
It runs before retrieval and fails closed. After retrieval, the run also fails closed unless every
declared identifier query reaches its target through the normalized current, authored, and union lexical
fields. Scored output goes only to a nonexistent directory that the harness creates, and carries a
completion manifest with artifact hashes.

## Decision rules

The experiment is invalid if corpus, selection, selector, query, or review pins fail; if queries overlap
the earlier target set; if review is incomplete; or if the sensitivity control fails.

A normalized arm is classified mechanically from paired effects against **both** body-only and current
terms. Semantic non-inferiority requires the lower 95% paired-bootstrap bound to remain at or above
-0.02 against both controls. An arm is:

- **regressive** if the semantic-MRR point estimate is more than 0.02 below either control;
- **semantic non-inferiority not established** if the point estimate is within the margin but either
  lower confidence bound falls below -0.02;
- **promising** if identifier MRR improves over both body-only and current terms while semantic MRR is
  non-inferior, but an identifier-effect confidence interval crosses zero;
- **validated on this holdout** only if the identifier-MRR effect is positive with a 95% interval lower
  bound above zero and semantic MRR remains non-inferior.

Any positive result remains a retrieval candidate only. Because selection deliberately requires an
authored identifier and rationale, even a validated holdout result does not generalize to all Memory Seed
decisions. It does not authorize compact canonical entries, a semantic sidecar, or a production change
without a separate implementation review, broader regression testing, and corpus replication.
