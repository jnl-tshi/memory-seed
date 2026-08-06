---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_integration_mode
title: Configurable integration_mode: local-merge vs PR
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
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

integration_mode is a project-local default read fail-open as local-merge, surfaced by ESR, obeyed by live+seed agent contracts, and implemented by mode-aware session integrate plus session open-pr.

### Why

Different workflows require different integration strategies: local-merge for single-developer rapid iteration, PR for team review gates. Configurable mode lets projects choose without code changes.

### How it evolved

Founded from the control file; completed 2026-07-15 per the control plane history.

### Constitution

- `constitution:v1#integration-mode` (governing)

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
