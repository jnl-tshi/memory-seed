---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_markdown_substrate
title: Plain-Markdown core for file-reading agents
topics:
  - documentation
  - seed-core
  - control-plane
created_at: 2026-08-06T17:18:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Plain-Markdown core for file-reading agents

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Proposed**

Authoritative decision: not yet accepted

### Decision

The memory core is kept as plain Markdown and predictable for file-reading agents. All critical control-plane files, session logs, and decision records are encoded in readable, human-editable Markdown rather than binary or structured formats.

### Why

Plain Markdown preserves local ownership, direct human editing, attribution, and immutable source entries while remaining accessible to file-reading agents without special parsing libraries. This enables append-only discipline and supports both human review and automated agent access.

### How it evolved

Control-plane behavioral constraint. Session decision mse_ddba1ztxqhasfbwf:d1 (2026-07-16) ratified partitioned Markdown authority with an append-only ADR sidecar, formalizing that original entries and decision updates own rationale/evidence while derived artifacts (registries, indexes, databases) remain secondary.

### Constitution

- `constitution:v1#markdown-authority` (governing)
- `constitution:v1#evidence-first` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:18:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#evidence-first",
      "role": "supporting"
    }
  ],
  "event_id": "adre_0b47a345aeeeef259039",
  "founding_quote": "Keep the memory core plain Markdown and predictable for file-reading agents.",
  "founding_source": ".memory-seed/policy.md#L21",
  "source": "derived"
}
```

#### Decision

The memory core is kept as plain Markdown and predictable for file-reading agents. All critical control-plane files, session logs, and decision records are encoded in readable, human-editable Markdown rather than binary or structured formats.

#### Why

Plain Markdown preserves local ownership, direct human editing, attribution, and immutable source entries while remaining accessible to file-reading agents without special parsing libraries. This enables append-only discipline and supports both human review and automated agent access.

#### Evolution

Control-plane behavioral constraint. Session decision mse_ddba1ztxqhasfbwf:d1 (2026-07-16) ratified partitioned Markdown authority with an append-only ADR sidecar, formalizing that original entries and decision updates own rationale/evidence while derived artifacts (registries, indexes, databases) remain secondary.
