---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_trace_boundary
title: Trace ships as memory-seed[trace]; core carries no web framework
topics:
  - memory-trace
  - release-packaging
created_at: 2026-08-06T20:05:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Trace ships as memory-seed[trace]; core carries no web framework

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_etm5m5682sseasgm:d1`

### Decision

Memory Trace ships as an optional extra in the root `memory-seed` package, not as a separate PyPI project. The `memory-trace` command, FastAPI web stack, and static assets live in `memory-trace/` as a separate source tree. Core `memory_seed` carries no web framework; Trace consumes the public retrieval API.

### Why

Separating Trace as its own distribution cleanly extracted presentation and web concerns from core, with Trace importing only public API symbols. Bundling back into the root package as an optional extra resolved practical constraints: PyPI rejected the standalone `memory-trace` project name, and the commercial strategy no longer required installation-layer separation. The release path changed to fold Trace into the root install rather than maintain separate distribution coordination.

### How it evolved

The decision first extracted Trace into a separate distribution with its own `pyproject.toml`, package, command, and assets, moving `lense.py` and static files out of core (2026-07-06). Seven days later, when PyPI naming barriers emerged and commercialisation strategy shifted, the decision bundled Trace back into the root package as an optional `trace` extra while retaining the source-tree separation (2026-07-12).

### Constitution

- `constitution:v1#open-core` (governing)
- `constitution:v1#ownership` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T20:05:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#open-core",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#ownership",
      "role": "supporting"
    }
  ],
  "event_id": "adre_e8ba7b5ae76a63355a1a",
  "founding_quote": "plain `memory-seed` must still ship no web framework",
  "founding_source": ".memory-seed/index.md#L101",
  "source": "derived",
  "supporting_decisions": [
    "mse_fcecj9hpq4qj16ay:d1"
  ]
}
```

#### Decision

`memory-trace/` is a separate source package owning the `memory-trace` command, the web stack (`fastapi`/`uvicorn`) and the static assets, consuming `memory_seed/retrieval.py` as a library. The release strategy folds Trace into the root `memory-seed[trace]` install path rather than shipping a separate PyPI project, and plain `memory-seed` must still ship no web framework.

#### Why

Keeping the UI's dependencies out of the core package is what lets the core stay a local-first, importable memory substrate with a single required dependency - a plain install must never pull a web server. Separating the source package enforces the boundary at import time rather than by convention. Folding distribution back into one project with an extra removes a second release to coordinate while preserving that boundary.

#### Evolution

Founded from the control file: Trace began as a separate distribution with its own pyproject and console command, and the release strategy later folded it into the root package as the `[trace]` extra while the no-web-framework rule for plain installs held throughout.

### revision-accepted - 2026-08-06T21:28:00Z

```json
{
  "event_id": "adre_e2c9e9f70614a85489a9",
  "founding_source": ".memory-seed/index.md#L101",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

### revision-proposed - 2026-08-08T19:14:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#open-core",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#ownership",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_etm5m5682sseasgm:d1",
  "event_id": "adre_630052ccaf7f6ba21ffe",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

`memory-trace/` is a separate source package owning the `memory-trace` command, the web stack (`fastapi`/`uvicorn`) and the static assets, consuming `memory_seed/retrieval.py` as a library. The release strategy folds Trace into the root `memory-seed[trace]` install path rather than shipping a separate PyPI project, and plain `memory-seed` must still ship no web framework.

#### Why

Rests on the session decision that instituted it: "Ship `memory_trace` and the `memory-trace` command from the root `memory-seed` package behind the optional `trace` extra." (mse_etm5m5682sseasgm:d1). This decision made the concern: shipping Trace as an optional extra in the root package rather than a separate required distribution.

#### Evolution

Founded from .memory-seed/index.md#L101; this revision moves the concern off that control-file line onto mse_etm5m5682sseasgm:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:22:00Z

```json
{
  "decision_ref": "mse_etm5m5682sseasgm:d1",
  "event_id": "adre_b1a2e1975104a8486b0c",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

### revision-proposed - 2026-08-08T23:22:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#open-core",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#ownership",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_etm5m5682sseasgm:d1",
  "event_id": "adre_7bb883894c88c9e3879b",
  "source": "derived",
  "supporting_decisions": [
    "mse_fcecj9hpq4qj16ay:d1"
  ],
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Memory Trace ships as an optional extra in the root `memory-seed` package, not as a separate PyPI project. The `memory-trace` command, FastAPI web stack, and static assets live in `memory-trace/` as a separate source tree. Core `memory_seed` carries no web framework; Trace consumes the public retrieval API.

#### Why

Separating Trace as its own distribution cleanly extracted presentation and web concerns from core, with Trace importing only public API symbols. Bundling back into the root package as an optional extra resolved practical constraints: PyPI rejected the standalone `memory-trace` project name, and the commercial strategy no longer required installation-layer separation. The release path changed to fold Trace into the root install rather than maintain separate distribution coordination.

#### Evolution

The decision first extracted Trace into a separate distribution with its own `pyproject.toml`, package, command, and assets, moving `lense.py` and static files out of core (2026-07-06). Seven days later, when PyPI naming barriers emerged and commercialisation strategy shifted, the decision bundled Trace back into the root package as an optional `trace` extra while retaining the source-tree separation (2026-07-12).

### revision-accepted - 2026-08-08T23:22:40Z

```json
{
  "decision_ref": "mse_etm5m5682sseasgm:d1",
  "event_id": "adre_84a58314db3539f501f5",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L101",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```
