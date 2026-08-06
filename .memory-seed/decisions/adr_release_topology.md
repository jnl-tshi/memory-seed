---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_release_topology
title: Publish via GitHub Release with manual PyPI gate
topics:
  - release
  - release-packaging
  - git-publishing
created_at: 2026-08-06T17:10:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Publish via GitHub Release with manual PyPI gate

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/policy.md#L72`

### Decision

Publishing is triggered by GitHub Release creation, which activates the publish.yml workflow. The pypi environment has a manual-approval gate that a reviewer must approve before the PyPI push executes.

### Why

GitHub Release creation produces labeled versions in the Actions UI. Manual approval gate ensures human review before the irreversible PyPI deployment and catches any unintended releases.

### How it evolved

Founded May 2026 (ms-1e38c75c); established as core release policy with multiple releases following the pattern.

### Constitution

- `constitution:v1#prove-automation` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:10:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#prove-automation",
      "role": "governing"
    }
  ],
  "event_id": "adre_37f74f40bbb87b8e9c41",
  "founding_quote": "Publishing should be triggered by GitHub Release creation, not direct workflow dispatch.",
  "founding_source": ".memory-seed/policy.md#L72",
  "source": "derived"
}
```

#### Decision

Publishing is triggered by GitHub Release creation, which activates the publish.yml workflow. The pypi environment has a manual-approval gate that a reviewer must approve before the PyPI push executes.

#### Why

GitHub Release creation produces labeled versions in the Actions UI. Manual approval gate ensures human review before the irreversible PyPI deployment and catches any unintended releases.

#### Evolution

Founded May 2026 (ms-1e38c75c); established as core release policy with multiple releases following the pattern.

### revision-accepted - 2026-08-06T21:21:00Z

```json
{
  "event_id": "adre_d74a70d35153c3ae635e",
  "founding_source": ".memory-seed/policy.md#L72",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
