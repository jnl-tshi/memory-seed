# Delivery-quality scenario harness

This is a local, offline, derived scorer for structured delivery-quality evidence. It does not import
skills, call a model, fetch a provider, invoke Superpowers, or modify Reflection artifacts.

`scenarios.json` is the declared corpus. Every scenario states its complexity, expected routing,
required observations, prohibited observations, measurement availability, a valid fixture, and one or
more deliberately failing controls. The corpus covers discovery (including Reflection Board reuse),
systematic debugging, fresh verification, governed authority and topic applicability, scoped-evidence
freshness, routine non-trigger routing, optional implementation planning with a declared test strategy,
evidence-aware review, and the narrow external Superpowers boundary (both allowed routes and its local
fallback). Every fixture remains instrument evidence rather than real workflow evidence.

## Run the instrument controls

From the repository root:

```powershell
python experiments/delivery-quality/evaluate.py --fixture valid
python experiments/delivery-quality/evaluate.py --fixture negative
```

Both commands exit zero only when their expected outcome holds: every valid fixture passes, and every
negative control fails. These are instrument checks, not observations of agent behavior. In particular,
a complete-looking observation without a referenced non-empty upstream evidence record fails.

## Baseline and post-adoption real runs

Create a JSON result using `delivery-quality-result-input/v1` below, then run the same command for either
comparison phase:

```powershell
python experiments/delivery-quality/evaluate.py --input baseline-result.json
python experiments/delivery-quality/evaluate.py --input post-adoption-result.json
```

Set `comparison_phase` to `baseline` or `post_adoption`; do not change the scenario to make unlike tasks
look comparable. A passing `real_agent_behavior` result is eligible as one item of workflow evidence. It
does not itself establish an improvement, lower cost, or a general workflow claim. The caller must compare
comparable runs and report limitations, selection bias, uncertainty, and rework/reopen causes.

## Result-input schema

```json
{
  "schema": "delivery-quality-result-input/v1",
  "scenario_id": "fresh-completion-verification",
  "evidence_class": "real_agent_behavior",
  "comparison_phase": "baseline",
  "execution_provenance": {
    "run_id": "runner-2026-09-09-001",
    "execution_surface": {"id": "named-runner", "kind": "actual_execution_surface"},
    "artifact_path": "execution-artifact.json",
    "artifact_sha256": "sha256 of that exact artifact"
  },
  "limitations": ["external execution metrics unavailable"],
  "selection_bias": ["task was selected for its verification surface"],
  "rework_reopen_events": [{"event": "reopen", "cause": "stale verification discovered"}],
  "evidence": [{"id": "verification-1", "source": "run artifact", "record": "post-change test output"}],
  "observations": [{
    "action": "execute_check",
    "subject": "changed_scope",
    "status": "observed",
    "evidence_ids": ["verification-1"]
  }],
  "measurements": {
    "provider_token_usage": {"availability": "unavailable", "reason": "surface did not expose usage"},
    "latency": {"availability": "unavailable", "reason": "surface did not expose latency"},
    "cost": {"availability": "unavailable", "reason": "surface did not expose cost"}
  }
}
```

The evaluator returns `delivery-quality-result/v1` with the scenario complexity, failures, measurements,
limitations, selection bias, rework/reopen events, and a claim boundary. It only reads structured `action`,
`subject`, `status`, and evidence references; it never scores phrase matches in skill prose or narrative
output.

Measurements are `unavailable` by default. Do not fill provider token usage, latency, or cost from token
estimates, budget reserves, local elapsed time, or price ceilings. Mark a measurement `available` only when
the actual execution surface supplies a `value`; its `source` must equal the bound execution-surface ID.

## Real-run provenance binding

Changing a fixture's `evidence_class` label never makes it workflow evidence. A real-run input must bind to
a separate, relative JSON artifact whose SHA-256 matches `artifact_sha256`. The artifact uses
`delivery-quality-execution-artifact/v1` and repeats the exact `run_id`, execution-surface object,
scenario ID, comparison phase, evidence records, observations, and measurements from the input. The evaluator
rejects missing, escaped, stale, mismatched, or malformed artifacts; a fixture has no artifact binding and
its measurements must remain unavailable. This rejects an artifact whose baseline phase is relabeled as
post-adoption, a scenario substitution, or evidence added or altered after the artifact was recorded.

This local binding proves that the scorer consumed an independently stored claimed execution record. It does
not authenticate a remote provider or turn one passing run into a comparative conclusion; the orchestrator
still owns provenance review and any workflow claim.
