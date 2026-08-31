---
format: memory-seed-adr/2
schema_version: 2
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
Status: **Accepted**

Authoritative decision: `mse_gn2kmdenk0p4cn7z:d1`

### Decision

The memory core is encoded in plain Markdown throughout all tiers. All critical files—session logs, decision records, control policies—are human-editable Markdown. Even in future collaborative or hosted implementations, Markdown remains the authoritative source of truth; any database, cache, or index is a derived, rebuildable projection, never a second source of truth.

### Reason

Markdown is readable for file-reading agents and human maintainers, directly supporting the core differentiation. The open-core, layered-implementation model allows optional accelerators (DuckDB, vector indices, hosted backends) without splitting the truth model. Keeping Markdown authoritative everywhere simplifies the invariant landscape—one source of truth across core, derived-local, and optional-hosted tiers—and preserves the ability for any tier to re-derive all databases from the Markdown source.

### Impact

Reframed Markdown within the Constitution's derived-layer/optional-tier model as Invariant #6, making the source-of-truth principle explicit and extending it to all implementation tiers. This resolved a design fork about whether collaborative or hosted tiers could make a server database authoritative; the answer is no, to maintain the unified truth model.

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
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

The memory core is kept as plain Markdown and predictable for file-reading agents. All critical control-plane files, session logs, and decision records are encoded in readable, human-editable Markdown rather than binary or structured formats.

#### Reason

Plain Markdown preserves local ownership, direct human editing, attribution, and immutable source entries while remaining accessible to file-reading agents without special parsing libraries. This enables append-only discipline and supports both human review and automated agent access.

#### Impact

Control-plane behavioral constraint. Session decision mse_ddba1ztxqhasfbwf:d1 (2026-07-16) ratified partitioned Markdown authority with an append-only ADR sidecar, formalizing that original entries and decision updates own rationale/evidence while derived artifacts (registries, indexes, databases) remain secondary.

### revision-accepted - 2026-08-06T21:19:00Z

```json
{
  "event_id": "adre_c47b07517f893153ed66",
  "founding_source": ".memory-seed/policy.md#L21",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/policy.md#L21.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/policy.md#L21 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:10:00Z

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
  "decision_ref": "mse_gn2kmdenk0p4cn7z:d1",
  "event_id": "adre_99867bc87afd17e57d2f",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

The memory core is kept as plain Markdown and predictable for file-reading agents. All critical control-plane files, session logs, and decision records are encoded in readable, human-editable Markdown rather than binary or structured formats.

#### Reason

Rests on the session decision that instituted it: "**Markdown is authoritative *everywhere*** (Invariant #6 reframed)" (mse_gn2kmdenk0p4cn7z:d1). Established Markdown as the authoritative substrate by reframing it as Invariant #6 in the Constitution, making it the core for all file-reading agents.

#### Impact

Founded from .memory-seed/policy.md#L21; this revision moves the concern off that control-file line onto mse_gn2kmdenk0p4cn7z:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:12:00Z

```json
{
  "decision_ref": "mse_gn2kmdenk0p4cn7z:d1",
  "event_id": "adre_3bfe901ffc96ef5743c5",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_gn2kmdenk0p4cn7z:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_gn2kmdenk0p4cn7z:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:12:20Z

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
  "decision_ref": "mse_gn2kmdenk0p4cn7z:d1",
  "event_id": "adre_9e2985580dcb295da6a7",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

The memory core is encoded in plain Markdown throughout all tiers. All critical files—session logs, decision records, control policies—are human-editable Markdown. Even in future collaborative or hosted implementations, Markdown remains the authoritative source of truth; any database, cache, or index is a derived, rebuildable projection, never a second source of truth.

#### Reason

Markdown is readable for file-reading agents and human maintainers, directly supporting the core differentiation. The open-core, layered-implementation model allows optional accelerators (DuckDB, vector indices, hosted backends) without splitting the truth model. Keeping Markdown authoritative everywhere simplifies the invariant landscape—one source of truth across core, derived-local, and optional-hosted tiers—and preserves the ability for any tier to re-derive all databases from the Markdown source.

#### Impact

Reframed Markdown within the Constitution's derived-layer/optional-tier model as Invariant #6, making the source-of-truth principle explicit and extending it to all implementation tiers. This resolved a design fork about whether collaborative or hosted tiers could make a server database authoritative; the answer is no, to maintain the unified truth model.

### revision-accepted - 2026-08-08T23:12:40Z

```json
{
  "decision_ref": "mse_gn2kmdenk0p4cn7z:d1",
  "event_id": "adre_4f3ba99ed77325b63488",
  "expected_authoritative_decision": "founding:.memory-seed/policy.md#L21",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_gn2kmdenk0p4cn7z:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_gn2kmdenk0p4cn7z:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
