# Fresh-Claude decision replay v2: rationale-sensitive implementation choice

This is the design package for the third Memory Seed decision-replay experiment. It replaces the
quality-report case, where every arm reached the same correct behavior, with a historical case that has
two plausible implementation paths and a hidden semantic distinction.

The case asks a fresh Claude session to make a parsed decision-qualified lifecycle edge visible in
Memory Trace. The easy shortcut projects the edge onto its entry and overstates the authored claim. The
safe path keeps the decision edge separate, terminates it on the decision row, and expands focused-view
membership without adding an entry-level edge.

Read these files in order:

1. [PREREGISTRATION.md](PREREGISTRATION.md) — hypotheses, fixture, arms, outcomes, sample, exclusions,
   analysis, and stop rules.
2. [task/TASK.md](task/TASK.md) — the byte-identical builder task supplied to every arm.
3. [HARNESS-SPEC.md](HARNESS-SPEC.md) — the implementation contract for preparation, running,
   transcript audit, grading, and negative controls.
4. [MAINTAINER-REPLAY.md](MAINTAINER-REPLAY.md) — the blinded reconstruction and safe-override follow-up.

## Status

**DESIGN COMPLETE; NOT YET FROZEN OR RUNNABLE.** No preparation, runner, auditor, or grader code exists
in this directory yet. The protocol becomes frozen only after the harness implements
[HARNESS-SPEC.md](HARNESS-SPEC.md), all negative controls pass, and the resulting instrument version and
hashes are recorded in the preregistration.

Running the scored study will create 24 external Claude builder sessions and up to 24 fresh maintainer
sessions. That is outside the earlier authorization for the completed three-session pilot and requires
fresh user approval before any fixture is sent to Anthropic.

## What this experiment can establish

- whether guaranteed exposure to preserved rationale changes a safety-relevant implementation choice
  on this historical case;
- whether normal Memory Seed routing exposes that same proposition without being pushed;
- whether a later fresh maintainer can reconstruct the invariant and refuse an unsafe override from the
  resulting patch and evidence;
- how much review work the evidence packet creates, with actual human time reported only when an
  independent human completes the blinded calibration.

It cannot establish a general Memory Seed effect, a cross-model effect, or a human-review-time effect
without the human calibration.
