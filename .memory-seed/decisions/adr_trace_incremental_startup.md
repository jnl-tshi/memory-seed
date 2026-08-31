---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_trace_incremental_startup
title: Trace startup incremental; immutable git derivations persist
topics:
  - memory-trace
  - performance
  - seed-core
created_at: 2026-08-06T17:11:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Trace startup incremental; immutable git derivations persist

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_gtn504wfjt3c34p6:d1`

### Decision

Memory Trace startup is incremental. Immutable git derivations—fork points, commit parents, and changed-path trees—are computed once per commit and persisted in the SQLite projection to carry across rebuilds. History harvesting uses bulk single-pass git log operations rather than per-item subprocess spawns.

### Reason

Direct profiling showed the prior design spawned 990 git subprocesses on a full rebuild, with 17.4 seconds spent on fork reconstruction and 15.2 seconds on file-entry indexing alone. Profiling revealed per-historical-item subprocess calls at 50–90 ms each on Windows were the entire bottleneck. Persisting immutable facts to the SQLite schema (the same contract that requires derived projections to stay rebuildable) eliminates recomputation on server restart, while bulk-read git history passes (fork-point resolution via maximal-common-ancestor and changed paths via single `git log --diff-merges=first-parent` passes) drop subprocess overhead from 990 to 7 calls.

### Impact

This decision consolidated startup performance in one session (2026-07-21), with no prior chain members. The work built a profiling harness first to confirm subprocess overhead was the root cause, then implemented immutable derivation caching and bulk-read patterns simultaneously.

### Constitution

- `constitution:v1#markdown-authority` (governing)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:11:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "event_id": "adre_e9d0e103353c2c5dc178",
  "founding_quote": "Memory Trace startup is incremental as of 2026-07-21: immutable git derivations (fork points, commit parents, changed paths) persist across rebuilds, reconciliation is incremental, and the file-entry index is lazy.",
  "founding_source": ".memory-seed/index.md#L83",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Memory Trace startup is incremental: immutable git derivations (fork points, commit parents, changed paths) persist across rebuilds, reconciliation is incremental, and file-entry index is lazy.

#### Reason

Incremental startup drastically improves performance. Warm start reduced from 44.25s to ~308ms; persisted derivations and lazy indexing enable efficient rebuilds and reconciliation.

#### Impact

Implemented 2026-07-21 (mse_42e8zzd7); completed the derived-projection plan's final deferred piece.

### revision-accepted - 2026-08-06T21:29:00Z

```json
{
  "event_id": "adre_50fd63670bdba836dc6c",
  "founding_source": ".memory-seed/index.md#L83",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L83.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L83 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:15:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_gtn504wfjt3c34p6:d1",
  "event_id": "adre_5bdb568e4e42319f22a3",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Memory Trace startup is incremental: immutable git derivations (fork points, commit parents, changed paths) persist across rebuilds, reconciliation is incremental, and file-entry index is lazy.

#### Reason

Rests on the session decision that instituted it: "immutable git facts (a merge's fork point, a commit's parents, its first-parent changed paths) are computed once per commit EVER" (mse_gtn504wfjt3c34p6:d1). This decision established both architectural principles: persisting immutable git derivations and bulk-reading history in single passes.

#### Impact

Founded from .memory-seed/index.md#L83; this revision moves the concern off that control-file line onto mse_gtn504wfjt3c34p6:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:23:00Z

```json
{
  "decision_ref": "mse_gtn504wfjt3c34p6:d1",
  "event_id": "adre_df8d93fe35c386016017",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_gtn504wfjt3c34p6:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_gtn504wfjt3c34p6:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:23:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#markdown-authority",
      "role": "governing"
    }
  ],
  "decision_ref": "mse_gtn504wfjt3c34p6:d1",
  "event_id": "adre_4b5f272b1844419435b1",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Memory Trace startup is incremental. Immutable git derivations—fork points, commit parents, and changed-path trees—are computed once per commit and persisted in the SQLite projection to carry across rebuilds. History harvesting uses bulk single-pass git log operations rather than per-item subprocess spawns.

#### Reason

Direct profiling showed the prior design spawned 990 git subprocesses on a full rebuild, with 17.4 seconds spent on fork reconstruction and 15.2 seconds on file-entry indexing alone. Profiling revealed per-historical-item subprocess calls at 50–90 ms each on Windows were the entire bottleneck. Persisting immutable facts to the SQLite schema (the same contract that requires derived projections to stay rebuildable) eliminates recomputation on server restart, while bulk-read git history passes (fork-point resolution via maximal-common-ancestor and changed paths via single `git log --diff-merges=first-parent` passes) drop subprocess overhead from 990 to 7 calls.

#### Impact

This decision consolidated startup performance in one session (2026-07-21), with no prior chain members. The work built a profiling harness first to confirm subprocess overhead was the root cause, then implemented immutable derivation caching and bulk-read patterns simultaneously.

### revision-accepted - 2026-08-08T23:23:40Z

```json
{
  "decision_ref": "mse_gtn504wfjt3c34p6:d1",
  "event_id": "adre_371870a41ebde6b8b502",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L83",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_gtn504wfjt3c34p6:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_gtn504wfjt3c34p6:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
