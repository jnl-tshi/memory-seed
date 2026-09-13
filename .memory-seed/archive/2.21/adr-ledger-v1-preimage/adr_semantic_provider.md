---
format: memory-seed-adr/1
schema_version: 1
adr_id: adr_semantic_provider
title: Model2Vec default provider; silent lexical degrade; model2vec the only required dep
topics:
  - retrieval
  - package
created_at: 2026-08-06T20:02:00Z
user_initials: JNL
agent_type: claude
source: derived
---

# Model2Vec default provider; silent lexical degrade; model2vec the only required dep

## Current view

<!-- memory-seed-derived-current-view:start -->
Status: **Accepted**

Authoritative decision: `founding:.memory-seed/index.md#L85`

### Decision

`model2vec` is a REQUIRED dependency and the package's only one. MCP memory search uses the static embedding provider `model2vec:minishlab/potion-base-8M` by default and falls back to lexical, metadata and recency ranking when semantic scoring fails or is disabled. `pip install --no-deps memory-seed` is the supported lightweight install without semantic ranking, and a test pins that `project.dependencies` contains exactly one entry.

### Why

A local static embedding provider gives semantic ranking with no network, no API key and no per-query cost, which is what a local-first memory substrate requires. Making it required rather than an extra means the default install ranks well; `--no-deps` remains the documented escape for a genuinely minimal install. Degrading silently to lexical keeps retrieval working when the provider cannot load - and because a silent degrade is a trust hazard, `esr` reports it on every run.

### How it evolved

Founded from the control file: the lightweight install was settled as `--no-deps` rather than an extra, pinned by a test asserting model2vec is the sole required dependency.

### Constitution

- `constitution:v1#model-independence` (governing)
- `constitution:v1#ownership` (supporting)

<!-- memory-seed-derived-current-view:end -->

## Event ledger

### revision-proposed - 2026-08-06T20:02:00Z

```json
{
  "constitution_refs": [
    {
      "ref": "constitution:v1#model-independence",
      "role": "governing"
    },
    {
      "ref": "constitution:v1#ownership",
      "role": "supporting"
    }
  ],
  "event_id": "adre_5641978d0da225ea3da1",
  "founding_quote": "`model2vec` is a REQUIRED dependency and the package's only one",
  "founding_source": ".memory-seed/index.md#L85",
  "source": "derived",
  "supporting_decisions": [
    "mse_9r00krq403dsmdnq:d1"
  ]
}
```

#### Decision

`model2vec` is a REQUIRED dependency and the package's only one. MCP memory search uses the static embedding provider `model2vec:minishlab/potion-base-8M` by default and falls back to lexical, metadata and recency ranking when semantic scoring fails or is disabled. `pip install --no-deps memory-seed` is the supported lightweight install without semantic ranking, and a test pins that `project.dependencies` contains exactly one entry.

#### Why

A local static embedding provider gives semantic ranking with no network, no API key and no per-query cost, which is what a local-first memory substrate requires. Making it required rather than an extra means the default install ranks well; `--no-deps` remains the documented escape for a genuinely minimal install. Degrading silently to lexical keeps retrieval working when the provider cannot load - and because a silent degrade is a trust hazard, `esr` reports it on every run.

#### Evolution

Founded from the control file: the lightweight install was settled as `--no-deps` rather than an extra, pinned by a test asserting model2vec is the sole required dependency.

### revision-accepted - 2026-08-06T21:23:00Z

```json
{
  "event_id": "adre_91aa7e2447fa0be5721c",
  "founding_source": ".memory-seed/index.md#L85",
  "source": "derived"
}
```

#### Reason

Accepted under JNL's delegated ratification (live instruction, 2026-08-06). Campaign-founded from the control file; grounding quote verified mechanically.
