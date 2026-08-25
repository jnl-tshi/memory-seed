# Lean DRAFT feasibility-pilot design

## Question and claim boundary

Does a compact, source-grounded decision card preserve more retrieval utility than naive shortening
while materially reducing the variable prose an agent must read?

This pilot tests **derived decision blocks** from the same 100 frozen Stage-1 decisions. It does not
test natural authoring, whole-entry size, human delayed recall, or a production DRAFT-format change.
Those require a separately preregistered paired authoring study.

## Recorded arms

1. `raw`: the canonical decision block.
2. `decision_only`: the first accepted `D:` sentence. This is the naive-shortening failure control.
3. `lean_no_supplemental_anchors`: first `D:`, first `R:`, and up to two distinct accepted D/R sentences carrying
   explicit modality, negation, or scope.
4. `lean_front_door`: `lean_no_supplemental_anchors` plus at most six exact, backtick-authored identifiers from
   accepted D/R or file evidence. Long prose-like spans and generic literals are excluded.

No `A:` text can become an accepted constraint. Every semantic clause is an exact source span, and
every anchor is an exact source token. The output uses existing D/R/F labels; no `C:` grammar is added.
The query artifact was pinned before ranking and the Stage-1 corpus already had revision and
fingerprint locks, which this pilot also asserts directly. The selector-code hash was added after the
first scored run; it covers local arm/selection functions plus the imported Stage-1 helper module, and
the selected-target fingerprint is asserted separately. These locks make later reruns detect relevant
drift, but they are not a pre-outcome preregistration. Therefore this pilot supports only a narrow
feasibility rejection, not a confirmatory effect claim.

## Queries and isolation

Thirty targets are chosen deterministically across source-length tertiles. Each must contain a
rationale and a compact exact identifier, because the anchor ablation cannot be evaluated otherwise.
Three context-minimal query-authoring passes received disjoint source-only packets with opaque IDs and
instructions excluding representations, arm names, ranking output, target refs, and benchmark metrics.
The saved artifacts verify packet coverage, query constraints, and pre-ranking review, but do not
independently attest author identity or access logs.

Each target gets:

- one semantic query written without an exact source identifier;
- one identifier query containing one exact identifier but otherwise independently worded.

Mechanical validation rejects metadata/arm vocabulary, source phrase copying, missing identifier
separation, duplicate packet coverage, and malformed lengths. The public query artifact contains only
opaque packet IDs and query text. Its SHA-256 is pinned in the scorer before the first rank run.

## Measurements

- representation-body UTF-8 bytes/4 token proxy, mean and median;
- mean words per sentence and repeated-content-token fraction as structural diagnostics, not human
  readability claims;
- BM25F Recall@1/3/5 and MRR over the same 100-document corpus, with every title, path, topic, tag,
  heading, lexical-term, semantic, and recency signal disabled;
- semantic-query and identifier-query results reported separately;
- exact source-anchor coverage using identifier-boundary matching rather than substring matching;
- an arm-label-hidden, same-model source-grounded audit with two ratings per card. All four candidates
  for a source were shown together, so raw remained recognizable by exact source match and form.

The important comparisons are `lean_front_door` versus `decision_only` (does the package beat naive
shortening?), `lean_front_door` versus `lean_no_supplemental_anchors` (do supplemental exact anchors earn their cost?), and
`lean_front_door` versus `raw` (what utility remains at the smaller context size?).

## Pilot gates

The theory receives provisional support only if:

- lean context is at least 20% lower than raw;
- semantic Recall@5 and MRR are no worse than raw by more than 0.05 absolute;
- adding anchors improves identifier-query MRR without reducing semantic-query MRR;
- every emitted semantic clause and anchor is source-grounded.

These are feasibility gates, not confirmatory non-inferiority intervals. A clean pilot can justify the
larger paired study; it cannot change the authoring standard.

## Confirmatory study if the pilot passes

Use at least 160 fixed, constraint-bearing task packets. Have different, counterbalanced writers
author current-guidance and lean-guidance records from the same atomic fact keys. Freeze queries before
records exist. Blinded readers then measure open-book comprehension, time to answer, delayed recall,
and critical fidelity errors. The hard gates remain no more than +2 percentage points critical harm
and no worse than -5 percentage points comprehension/recall, with paired decision-level confidence
intervals. Do not introduce a hard word cap: omission can masquerade as concision.
