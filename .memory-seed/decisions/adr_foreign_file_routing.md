---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_foreign_file_routing
title: Non-destructive routing into foreign entry-point files
topics:
  - control-plane
  - cli
created_at: 2026-08-06T20:03:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Non-destructive routing into foreign entry-point files

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L146`

### Decision

The four routing destinations (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) follow one 4-way ownership branch shared by `init` and `update`: absent writes the full seed file; ours (carrying `memory-system-version` frontmatter) gets a version-gated archive-and-replace; foreign carrying our markers has the managed block re-synced in place; foreign without markers gets a marker-delimited routing block injected. A foreign file is never overwritten, even under `--force`.

### Why

These files are entry points a project may already own and have written by hand, so overwriting one would destroy work Memory Seed did not author. Marker-delimited injection gives the routing Memory Seed needs while leaving every foreign line intact, and markers make the managed region re-syncable later without re-reading intent. Sharing one branch between init and update keeps the two paths from diverging into different notions of ownership.

### How it evolved

Founded from the control file as the 4-way ownership branch shipped in 2.8.0, shared by `init_project` and `update_project` across the four routing destinations.

### Constitution

- `constitution:v1#ownership` (governing)
- `constitution:v1#single-source` (supporting)

### Awaiting review

- `ms-7c2f1d90:d1` - The four routing destinations (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`)...

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T20:03:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#ownership",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#single-source",
      "role": "supporting"
    }
  ],
  "event_id": "adre_f24b6d8b5fba8f06b7db",
  "founding_quote": "Non-destructive routing into foreign entry-point files (2.8.0)",
  "founding_source": ".memory-seed/index.md#L146",
  "source": "derived",
  "supporting_decisions": [
    "ms-7c2f1d90:d1"
  ]
}
```

#### Decision

The four routing destinations (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) follow one 4-way ownership branch shared by `init` and `update`: absent writes the full seed file; ours (carrying `memory-system-version` frontmatter) gets a version-gated archive-and-replace; foreign carrying our markers has the managed block re-synced in place; foreign without markers gets a marker-delimited routing block injected. A foreign file is never overwritten, even under `--force`.

#### Why

These files are entry points a project may already own and have written by hand, so overwriting one would destroy work Memory Seed did not author. Marker-delimited injection gives the routing Memory Seed needs while leaving every foreign line intact, and markers make the managed region re-syncable later without re-reading intent. Sharing one branch between init and update keeps the two paths from diverging into different notions of ownership.

#### Evolution

Founded from the control file as the 4-way ownership branch shipped in 2.8.0, shared by `init_project` and `update_project` across the four routing destinations.

### revision-accepted - 2026-08-06T21:14:00Z

```json
{
  "event_id": "adre_4fb83e207e8f9b8f5c0d",
  "founding_source": ".memory-seed/index.md#L146",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-08T19:07:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#ownership",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#single-source",
      "role": "supporting"
    }
  ],
  "decision_ref": "ms-7c2f1d90:d1",
  "event_id": "adre_663c9774715e56da26e7",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

The four routing destinations (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) follow one 4-way ownership branch shared by `init` and `update`: absent writes the full seed file; ours (carrying `memory-system-version` frontmatter) gets a version-gated archive-and-replace; foreign carrying our markers has the managed block re-synced in place; foreign without markers gets a marker-delimited routing block injected. A foreign file is never overwritten, even under `--force`.

#### Why

Rests on the session decision that instituted it: "Added a 4-way ownership branch (shared `_maybe_merge_foreign_routing` used by both `init_project` and `update_project`) over the four `ROUTING_DESTINATIONS`" (ms-7c2f1d90:d1). This decision implemented the complete non-destructive routing mechanism for foreign entry-point files through structured ownership and version-gated handling.

#### Evolution

Founded from .memory-seed/index.md#L146; this revision moves the concern off that control-file line onto ms-7c2f1d90:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.
