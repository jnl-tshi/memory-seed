# Front-door first-run audit

Status: **failed development gate**. The exact first-run outputs remain in
`front-door-ablation-metrics.json` and `front-door-results.md`; this audit records the interpretation
after checking the measurement against production code and Memory Seed's recorded rationale.

## What the run established

- The frozen corpus, queries, selector, exact-span oracle, and source-only review all passed their
  integrity gates.
- `query_evidence` retained 88/90 required source spans and all required spans for 58/60 queries.
- Median first-view context, including the full-source affordance, was 86.2% of raw. That is only a
  13.8% reduction and fails the frozen requirement of at least 20%.
- `complete_dra` retained exactly the same answer evidence with less context. The selected F/T block
  therefore added no measured benefit on this set.
- `current_lean` was smaller but exposed only 16/90 required answer spans, consistent with the earlier
  fidelity failure.

The display candidate does not advance to a human Stage 2 study.

## Why the retrieval zero is not a performance conclusion

All reported target-rank effects were zero, so the instrument was checked before interpreting the
number. The current production path stores punctuation-bearing values such as `rare_symbol.py` in
`lexical_terms`, but BM25F normalizes each query term before lookup while leaving the field value raw.
A synthetic probe scored 0.0 in the current representation and 0.545 after normalizing the field,
which moved the intended chunk to rank 1.

On the frozen 60-query development set:

- `current_lexical_terms` produced zero lexical-field matches and changed zero full result orders;
- the broader `authored_exact_terms` arm changed ten full orders because it also admitted ordinary
  backtick words such as `update`, so it was not equivalent to the current identifier field;
- the committed artifact retained only target ranks, not full-order or exposure diagnostics.

The run is valid evidence that the current field is inert under this scorer, not evidence that exact
identifier evidence has no retrieval value.

## Next bounded test

Use a new held-out target/query set and compare current raw identifier terms with the minimal
normalization correction. Freeze query/review hashes before scoring, persist per-query ranks and field
exposure, and require a synthetic sensitivity control to prove the treatment reaches BM25F. Do not
modify production retrieval until that holdout is measured.

## Post-integration reproducibility repair (2026-08-25)

A fresh checkout exposed that the recorded oracle pin did not match the oracle bytes committed under the
repository's LF policy. The committed oracle is
`sha256:5888f16cace1791e811a348c1abddff4d9f7633337a6d112d5f10583df981f64`; the obsolete pin was
`sha256:f5567e33a2ac839bab5ef797a6e3fc7ba43b777df7a73569466f0d71d46757e5`.

The repair changes no answer span, review verdict, selector, query, score, or result. It updates the
harness and metadata to the committed oracle hash, then re-pins the review wrapper whose only changed
field is that oracle reference. The corrected review hash is
`sha256:dd1e5908d92727e298dc8ce0cc11994aac5c81b627d80f58e76df3b93a664adc`.
