# V4 amendment plan

## V3 preservation boundary

The v3 instrument is frozen. Its historical package, grade schema, qualification vectors, documentation,
and any results remain v3-specific and must not be edited or pooled with v4 observations. The v4 package
is a separately named instrument with an independent schema and qualification run.

## V4 amendments

1. Make semantic safety the primary result: visibility, non-projection, and robustness behavior define
   `semantic_safety_pass`; public command success and bounded scope remain validity conditions.
2. Retain the nonempty equal-suite/candidate-pass/pristine-assertion-failure-with-zero-errors requirement
   as separately reported `candidate_test_quality`, so deficient candidate tests do not reverse an
   otherwise semantically safe valid top-level pass.
3. Require an externally captured `pre_coding_receipt` in supplied protocol JSON. It records context
   receipt, evidence IDs or `none`, rationale propositions or `none`, and acknowledgement. It is validated
   as protocol evidence and is never a candidate-fixture write.
4. Bump package-specific names and report versions to v4 and qualify a semantic-safe candidate with
   defective candidate-test quality receiving top-level semantic pass.
