# Recovery trial: operating boundaries

This is an **offline reconstruction experiment**, not a live decision detector.
The existing capture adapter and frozen deterministic parser are unchanged.
Semantic drafts are inert and still require curator verification.

Current outcome: [RECOVERY-RESULTS.md](RECOVERY-RESULTS.md). Implementation is
unmerged, with one marker-coordinate compatibility fix awaiting authorization.
Two development prompt versions did not improve complete recovery; no further
tuning or live integration is authorized by this experiment.

## Privacy and execution

Keep datasets, source text, prompts, model responses and review packets in an
owner-local directory outside Git. The runner makes no network calls.
When existing Codex agents interpret packets, inference uses the existing
Codex service: it is not fully local inference. No separate provider credentials,
OAuth flow, deployment, training or automatic promotion is introduced.

## What a passing test requires

Use the frozen thresholds in [RECOVERY-PLAN.md](RECOVERY-PLAN.md). Source-label
review and extraction-output review are different steps: two people/agents
agreeing that a source supports a label does not establish output equivalence.
Exact quotations and correct source coordinates are mechanical safeguards,
not proof that a model interpreted the conversation correctly.

The prior fourteen held-out cases are now regression-only. Previously examined,
gold-selected evidence can be useful for development, but cannot supply a fresh
test, measure automatic retrieval, or establish real marker availability.

## Freshness blocker found on 2026-10-01

The current repository has no independently reviewed real hard-negative dataset.
The inventory identified 410 previously unsampled Codex decision identities,
but neither their support nor their lineage freshness is certified.

Historical exposure cannot be reconstructed completely from the tracked files:

- A discarded raw-log search recorded in COHORT-100-STATUS.md has no full
  source-identity ledger.
- NEARBY-SESSION-FALLBACK-RESULTS.json stores an eligible-rollout count and digest,
  not the full searched ID list.
- Semantic reviews lack reviewer logical-session/root identities.
- The capture corpus's cited-rollout-set hash is not actual parent-collapsed
  lineage and must not be used as a freshness proof.

A safe fresh cohort can instead exclude every root in a frozen snapshot of
existing rollout metadata, including this recovery session and descendants,
and collect cases from subsequently created independent roots. Freeze a private
exposure manifest with physical rollout IDs, logical sessions, actual parents
and roots, source hashes/cutoff, run references and explicit completeness.
Review at least thirty supported positives and thirty real hard negatives.
Unknown support, unresolved lineage and missing exposure coverage stay
ineligible. Do not relabel unresolved positives as negatives.

Until that dataset and two independently reviewed model runs pass, the empirical
gate is **inconclusive**. Live polling/restart integration and automatic discovery
remain gated follow-ups, not completed functionality.

## Offline commands

Run from the repository root with Python. Point every output at a private
directory outside the repository. Existing differing output files are not
overwritten; use a new run directory when inputs or configuration change.

```text
python -m hosted.evaluation.recovery freeze --dataset dataset.json --model-config model-config.json --output frozen.json
python -m hosted.evaluation.recovery requests --frozen frozen.json --output requests.json
python -m hosted.evaluation.recovery import-run --frozen frozen.json --run-id A --responses responses-a.json --output run-a.json
python -m hosted.evaluation.recovery import-run --frozen frozen.json --run-id B --responses responses-b.json --output run-b.json
python -m hosted.evaluation.recovery control --frozen frozen.json --repo REPOSITORY --output control.json
python -m hosted.evaluation.recovery review-packets --frozen frozen.json --runs run-a.json run-b.json --control control.json --output review-bundle.json
python -m hosted.evaluation.recovery score --frozen frozen.json --runs run-a.json run-b.json --control control.json --reviews review-1.json review-2.json --output score.json
```

The commands do not execute a model. Give only extractor packets to the two
independent extraction runs, save their actual responses, and import them.
Only after both outputs are frozen, give the masked review packets—not their
answer key—to two independent reviewers. Do not share one review with the
other reviewer. Record actual model, reasoning setting, prompt, source exposure
and participant identities in the private experiment record. Distinct names
alone do not prove independent execution.

The control refuses changed parser files or an unavailable pinned spaCy
pipeline. Control and semantic inference receive the same selected source
messages; an absent marker is explicitly treated as an oracle reconstruction
anchor for the deterministic control. Neither arm establishes autonomous
marker placement or full-stream discovery.

Hash binding detects accidental changes; it does not prove that source labels,
reviewer independence or exposure-completeness declarations are truthful.
Those remain independently auditable experiment inputs.
