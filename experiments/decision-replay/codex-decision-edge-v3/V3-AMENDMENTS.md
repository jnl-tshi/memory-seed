# Codex decision-edge replay v3 amendments

This is a new instrument, not a continuation of the Codex decision-edge v2 pilot.
No v2 pilot subject, fixture, candidate patch, score, transcript, or data point is
pooled with v3. A future v3 result is interpreted only within this v3 instrument.

The fixture contract changes the subject-facing test command to the fixture-local,
cross-platform `python RUN_TASK_TESTS.py`. It also makes the decision-reference
boundary explicit: singular `d1` resolves to the entry row, while an invalid
ordinal on an expanded target produces no edge and does not widen.

Generated run artifacts default to the short, primary-checkout-relative,
gitignored `f/` root. This keeps fixture paths patch-writable by
fresh Codex agents through primary-relative `apply_patch` paths and avoids the
previous long package-relative output path on Windows.
