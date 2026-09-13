---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_hook_merge_framework
title: Hook installation is a per-agent merge, idempotent on script filename
topics:
  - hooks
  - agent-collaboration
  - control-plane
created_at: 2026-08-08T03:08:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Hook installation is a per-agent merge, idempotent on script filename

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

Hook configuration is merged per agent rather than copied, across every supported agent's own config file. Hooks install unconditionally for the selected agents, and update is idempotent by matching on the script filename rather than the full command, so a flag change in a later version upserts instead of appending a duplicate.

### Why

Merging preserves configuration the project already owns, which copying would destroy. Matching on the script filename is what makes upgrade safe: the command line changes between versions, so comparing full commands would leave a stale entry beside the new one every time. Installing unconditionally keeps the seed model-agnostic rather than betting on which agent a contributor uses.

### How it evolved

2026-05-27 established merge-not-clobber for the Claude settings file, then added a Cursor session-start hook; 2026-05-29 made upsert idempotent by script filename; 2026-06-11 wired the remaining agents and brought Copilot into the supported set.

### Constitution

- `constitution:v1#ownership` (governing)
- `constitution:v1#prove-automation` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-08T03:08:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#ownership",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#prove-automation",
      "role": "supporting"
    }
  ],
  "decision_ref": "ms-5e366ef4:d2",
  "event_id": "adre_63d3523695e95e31525b",
  "source": "derived",
  "supporting_decisions": [
    "ms-7c4e1f9a:d1",
    "ms-5e1a9d44:d1",
    "ms-7b3f1e92:d1"
  ],
  "update_entry_id": "ms-5e366ef4"
}
```

#### Decision

Hook configuration is merged per agent rather than copied, across every supported agent's own config file. Hooks install unconditionally for the selected agents, and update is idempotent by matching on the script filename rather than the full command, so a flag change in a later version upserts instead of appending a duplicate.

#### Why

Merging preserves configuration the project already owns, which copying would destroy. Matching on the script filename is what makes upgrade safe: the command line changes between versions, so comparing full commands would leave a stale entry beside the new one every time. Installing unconditionally keeps the seed model-agnostic rather than betting on which agent a contributor uses.

#### Evolution

2026-05-27 established merge-not-clobber for the Claude settings file, then added a Cursor session-start hook; 2026-05-29 made upsert idempotent by script filename; 2026-06-11 wired the remaining agents and brought Copilot into the supported set.
