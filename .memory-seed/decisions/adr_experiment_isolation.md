---
format: memory-seed-adr/2
schema_version: 2
adr_id: adr_experiment_isolation
title: Experiment fixture isolation is structural via nearest-runtime discovery
topics:
  - testing
  - seed-core
  - functionality-audit
created_at: 2026-08-06T17:17:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Experiment fixture isolation is structural via nearest-runtime discovery

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `mse_gbc4m5m71dqmen75:d1`

### Decision

Experimental fixtures achieve isolation through structural design using nearest-runtime discovery. Each fixture is generated as a standalone git repository by running the real init_project with documented per-level strips applied. The MCP server is pinned to the local working tree via absolute interpreter path and PYTHONPATH. Hand-written index.md, policy.md, and vocabulary files remain byte-identical across fixture levels. Each fixture's .memory-seed/sessions/ directory serves as the experiment readout, while generated templates/ and runs/ directories are gitignored.

### Reason

Running real init_project on actual installations ensures results generalize beyond hand-assembled approximations. Standalone git repositories and identical stubs address verified hazards: the commit hook installs into the nearest git common directory, the parent's prepare-commit-msg globs nested session stores, and resolve_runtime walks upward without a boundary guard. Using the generator as provenance avoids complexity from tracking nested git repos in the parent.

### Impact

The architecture was designed as a single integrated system encompassing isolation topology, fixture generation methodology, runtime pinning, stub handling, and experiment readout location.

### Constitution

- `constitution:v1#authority` (governing)
- `constitution:v1#prove-automation` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T17:17:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#prove-automation",
      "role": "supporting"
    }
  ],
  "event_id": "adre_88cc5c2e833623560d62",
  "founding_quote": "Isolation is structural (nearest-runtime discovery) and was proven at build time: a fixture write left the parent corpus counts unchanged.",
  "founding_source": ".memory-seed/index.md#L107",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Experimental fixtures achieve isolation through structural design via nearest-runtime discovery. Each generated fixture is a standalone git repository with its own `.memory-seed/` runtime. Fixture runtimes are throwaway sub-project runtimes deliberately not individually registered in the parent index.

#### Reason

Isolation is structural and was proven at build time: a fixture write left the parent corpus counts unchanged. Nearest-runtime discovery provides automatic, predictable fixture isolation without requiring manual registration or explicit isolation machinery.

#### Impact

Founded from the control file; outlined in the agent-capture experiment specification. Session decision mse_vaz9d3h7x4bcmd1t:d1 (2026-08-04) narrowed isolation assertion to the parent session store specifically, refining the validation claim while preserving structural isolation.

### revision-accepted - 2026-08-06T21:13:00Z

```json
{
  "event_id": "adre_6dbed6aaba81a0747e0e",
  "founding_source": ".memory-seed/index.md#L107",
  "impact_provenance": "preserved",
  "source": "derived"
}
```

#### Decision

Accept founding:.memory-seed/index.md#L107.

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.

#### Impact

founding:.memory-seed/index.md#L107 becomes the authoritative decision; later contrary evidence requires a successor revision.

### revision-proposed - 2026-08-08T19:06:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#prove-automation",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_gbc4m5m71dqmen75:d1",
  "event_id": "adre_51e2d1ee46650eeb718d",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_kqna9hegj35dwsqj"
}
```

#### Decision

Experimental fixtures achieve isolation through structural design via nearest-runtime discovery. Each generated fixture is a standalone git repository with its own `.memory-seed/` runtime. Fixture runtimes are throwaway sub-project runtimes deliberately not individually registered in the parent index.

#### Reason

Rests on the session decision that instituted it: "treat each fixture's own `.memory-seed/sessions/` as the experiment readout" (mse_gbc4m5m71dqmen75:d1). This decision directly established structural fixture isolation through isolated runtime environments with per-fixture session directories.

#### Impact

Founded from .memory-seed/index.md#L107; this revision moves the concern off that control-file line onto mse_gbc4m5m71dqmen75:d1, the decision that made it. Selected by semantic recall over the concern text, grounded verbatim, and confirmed by an independent refutation pass.

### revision-rejected - 2026-08-08T23:07:00Z

```json
{
  "decision_ref": "mse_gbc4m5m71dqmen75:d1",
  "event_id": "adre_1a0e5903842cb03466fb",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Reject mse_gbc4m5m71dqmen75:d1.

#### Reason

Wording retired, not the decision. This summary restated a single decision (or, for a founded concern, the control-file line) instead of synthesising every live member of the chain. Re-proposed on the same decision with that synthesis.

#### Impact

mse_gbc4m5m71dqmen75:d1 is not adopted and the current authoritative decision remains unchanged.

### revision-proposed - 2026-08-08T23:07:20Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#authority",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#prove-automation",
      "role": "supporting"
    }
  ],
  "decision_ref": "mse_gbc4m5m71dqmen75:d1",
  "event_id": "adre_8eaa920489274ce78ee8",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Experimental fixtures achieve isolation through structural design using nearest-runtime discovery. Each fixture is generated as a standalone git repository by running the real init_project with documented per-level strips applied. The MCP server is pinned to the local working tree via absolute interpreter path and PYTHONPATH. Hand-written index.md, policy.md, and vocabulary files remain byte-identical across fixture levels. Each fixture's .memory-seed/sessions/ directory serves as the experiment readout, while generated templates/ and runs/ directories are gitignored.

#### Reason

Running real init_project on actual installations ensures results generalize beyond hand-assembled approximations. Standalone git repositories and identical stubs address verified hazards: the commit hook installs into the nearest git common directory, the parent's prepare-commit-msg globs nested session stores, and resolve_runtime walks upward without a boundary guard. Using the generator as provenance avoids complexity from tracking nested git repos in the parent.

#### Impact

The architecture was designed as a single integrated system encompassing isolation topology, fixture generation methodology, runtime pinning, stub handling, and experiment readout location.

### revision-accepted - 2026-08-08T23:07:40Z

```json
{
  "decision_ref": "mse_gbc4m5m71dqmen75:d1",
  "event_id": "adre_e0aa0ee607d240a6a5e7",
  "expected_authoritative_decision": "founding:.memory-seed/index.md#L107",
  "impact_provenance": "preserved",
  "source": "derived",
  "update_entry_id": "mse_rfw60ctv535cbseq"
}
```

#### Decision

Accept mse_gbc4m5m71dqmen75:d1.

#### Reason

Reason was not recorded in the schema-v1 event.

#### Impact

mse_gbc4m5m71dqmen75:d1 becomes the authoritative decision; later contrary evidence requires a successor revision.
