---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_integration_mode
title: "Configurable integration_mode: local-merge vs PR"
topics:
  - control-plane
  - git-workflow
created_at: 2026-08-06T17:07:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Configurable integration_mode: local-merge vs PR

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L173`

### Decision

integration_mode is a project-local default read fail-open as local-merge, surfaced by ESR, obeyed by live+seed agent contracts, and implemented by mode-aware session integrate plus session open-pr.

### Why

Different workflows require different integration strategies: local-merge for single-developer rapid iteration, PR for team review gates. Configurable mode lets projects choose without code changes.

### How it evolved

Founded from the control file; completed 2026-07-15 per the control plane history.

### Constitution

- `constitution:v1#integration-mode` (governing)

### Awaiting review

- `mse_t388apx6evvmmd1r:d1` - integration_mode is a project-local default read fail-open as local-merge, surfaced by ESR, obeyed by...

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:07:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#integration-mode",
      "role": "governing"
    }
  ],
  "event_id": "adre_d24036a214861e465f99",
  "founding_quote": "Configurable integration mode (completed 2026-07-15): `integration_mode: local-merge|pr` is a project-local default read fail-open as `local-merge`, surfaced by ESR, obeyed by live+seed agent contracts, and implemented by mode-aware `session integrate` plus `session open-pr`.",
  "founding_source": ".memory-seed/index.md#L173",
  "source": "derived"
}
```

#### Decision

integration_mode is a project-local default read fail-open as local-merge, surfaced by ESR, obeyed by live+seed agent contracts, and implemented by mode-aware session integrate plus session open-pr.

#### Why

Different workflows require different integration strategies: local-merge for single-developer rapid iteration, PR for team review gates. Configurable mode lets projects choose without code changes.

#### Evolution

Founded from the control file; completed 2026-07-15 per the control plane history.

### revision-accepted - 2026-08-06T21:16:00Z

```json
{
  "event_id": "adre_30ba7762d6095876e88c",
  "founding_source": ".memory-seed/index.md#L173",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-08T19:08:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#integration-mode",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_t388apx6evvmmd1r:d1",
  "event_id": "adre_6d87567885756f5efb18",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

integration_mode is a project-local default read fail-open as local-merge, surfaced by ESR, obeyed by live+seed agent contracts, and implemented by mode-aware session integrate plus session open-pr.

#### Why

Rests on the session decision that instituted it: "`INTEGRATION_MODES = ("local-merge", "pr")`" (mse_t388apx6evvmmd1r:d1). Implemented the P0.1 configurable integration-mode feature with the core INTEGRATION_MODES setting.

#### Evolution

Founded from .memory-seed/index.md#L173; this revision moves the concern off that control-file line onto mse_t388apx6evvmmd1r:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
