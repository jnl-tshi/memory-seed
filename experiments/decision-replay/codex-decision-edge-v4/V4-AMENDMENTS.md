# Codex decision-edge replay v4 amendments

This is a separate, non-pooled instrument. Its primary result is semantic safety: visibility,
non-projection, and robustness behavior. Public command success and bounded scope remain validity
conditions. Candidate-test discrimination remains mandatory and reported as `candidate_test_quality`,
but it does not overturn a semantic-safe valid result.

Protocol JSON may contain a mandatory externally captured `pre_coding_receipt`; its absence or invalid
shape makes the protocol incomplete. The receipt is orchestration evidence and is never a candidate
fixture write.
