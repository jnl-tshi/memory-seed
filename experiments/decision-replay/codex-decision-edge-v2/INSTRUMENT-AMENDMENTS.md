# Instrument amendments

## Pre-freeze reference correction: invalid ordinal no-widening

Status: **incorporated before scored execution; no pilot/scored data exists.**

The original visibility revision is
`0ba56be3b08a2fcf44090e90e754da3350526045`, whose direct parent is the frozen source
`21749f40e1173d0862201921ff6f41de24f3b914`. Qualification found that its target resolver used
`decision_row.get(...) or entry_row.get(...)`. Consequently, an invalid `:d99` on a multi-decision
target was widened to the target entry row, contradicting the preregistered robustness endpoint.

The exact direct follow-up
`12884ac96c428d18d7e26079e03583a600fe1973` (parent
`0ba56be3b08a2fcf44090e90e754da3350526045`) fixes only that endpoint by allowing the entry-row
fallback when the target has no expanded decision rows. The qualified positive reference is therefore
the exact two-commit composite:

```text
21749f40e1173d0862201921ff6f41de24f3b914
  -> 0ba56be3b08a2fcf44090e90e754da3350526045
  -> 12884ac96c428d18d7e26079e03583a600fe1973
```

`verify_harness.py` also retains unamended `0ba56be3...` as a near-reference negative control: it must
pass decision-row visibility, focus membership, and non-projection, while failing invalid-ordinal
no-widening. The ordinal-fallback mutant independently recreates the same prohibited behavior.

This correction does not alter subject fixtures, task text, treatment assignment, or pushed evidence.
The primary historical intervention remains the bounded **pre-fix** D2 rationale from
`mse_j55kt6mq230zj2p4:d2`. Neither follow-up code, post-fix rationale, hidden-oracle content, nor this
amendment is copied into a subject packet.

## Pre-freeze grader hardening: trusted baseline and schema v2

Status: **incorporated before scored execution; no pilot/scored data exists.**

Review found that grader v1 implicitly trusted the candidate's current `HEAD` as pristine source. Grader
schema v2 instead requires the expected prepared fixture commit from `public-manifest.json` (or an
explicit equivalent), verifies object presence plus exact `HEAD`/tree identity before archive, and emits
an explicit baseline error with all behavioral gates not run when identity fails.

The same pre-freeze amendment makes oracle execution fail closed on timeout/nonzero exit, scrubs inherited
Python and Git redirections, strengthens candidate-test discrimination to same-count assertion failure,
validates nested protocol/report shapes, and expands non-projection equality across Trace graph/search/
chunk plus the shared historical retrieval search/get boundary. CLI/MCP adapters are not launched as
independent processes; the Codex instrument claims the shared Python boundary only.

## Pre-freeze grader hardening: structured candidate tests and schema v3

Status: **incorporated before scored execution; no pilot/scored data exists.**

Review demonstrated that parsing candidate-controlled unittest text could mistake a fabricated
`FAIL`/`Ran N` transcript for a behavioral regression. Schema v3 adds the external, checksum-recorded
`candidate_test_runner.py`. It captures test output, discovers the suite under a fixed module name, and
emits only harness-owned structured result events. Discrimination now requires identical nonempty test
IDs/counts, a real pristine `unittest` assertion failure with no errors, and a clean candidate result.
AST presence remains only a preliminary source-shape check. A live fabricated-transcript negative
control and a live ordinary assertion positive control freeze this distinction.

## Pre-freeze runner binding, AST policy, and schema v4

Status: **incorporated before scored execution; no pilot/scored data exists.**

Review then demonstrated the remaining ordinary monkeypatch path: candidate import could replace
`unittest.TestResult` callbacks or `TestSuite.run`. Runner v2 creates/binds its loader, root suite,
result callbacks, and execution methods before candidate import. The preliminary AST policy rejects
direct unittest/result/suite/loader mutation, runner introspection through `__main__`/`sys.modules`, and
dynamic `exec`/`eval`. A live reviewer-reproduction control proves the source is rejected and that the
pre-bound structured result still records the assertion failure.

Schema v4 records runner v2's new checksum. `THREAT-MODEL.md` simultaneously narrows the assurance:
candidate Python execution is not sandboxed, arbitrary malicious grader-subversion is out of scope,
and these controls are not cryptographic tamper-proofing.
