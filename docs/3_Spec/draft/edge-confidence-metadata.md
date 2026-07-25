---
title: Per-edge confidence metadata in link sidecars
status: draft
spec_binding: draft
parent: ../lifecycle-edge-linking-sidecars.md
---

# Per-Edge Confidence Metadata in Link Sidecars

Status: **DRAFT — STORED, NOT YET CONSUMED (as of 2026-07-25).** The live contract is
[lifecycle-edge-linking-sidecars.md](../lifecycle-edge-linking-sidecars.md), which this extends. The
field is written by the link-inference campaign and **tolerated** by `links check` today; teaching the
graph/Trail to read it is a deliberately deferred later stage.

## Why

The lifecycle-link judgment swarm (`link_swarm.md`) suggests edges at scale, each with a model
confidence. Discarding the weak ones throws away work already paid for; writing them indistinguishably
from human-authored edges would let an unverified guess masquerade as fact. The resolution is to store
the edge **and** its confidence, structured so a later graph stage can weight, filter, or de-emphasise
low-confidence edges without re-parsing prose.

## Shape

A sidecar block MAY carry an `edge_confidence:` key: a list of mappings, one per authored ref, each
`{ref, confidence, tier}`.

```yaml
entry_id: ms-845042c7
evolves:
  - d1 -> ms-db2d715c
  - d1 -> ms-f83a27d3:d1
edge_confidence:
  - ref: "d1 -> ms-db2d715c"
    confidence: 0.95
    tier: high
  - ref: "d1 -> ms-f83a27d3:d1"
    confidence: 0.58
    tier: low
note: haiku-swarm link-campaign 2026-07-25, mechanically validated (quote+ordinal); machine-suggested, unverified (retained for a later verification cycle) - per-edge confidence in edge_confidence
```

- **`ref`** is the exact token as authored in the `replaces:`/`evolves:`/`related_entries:` list above
  (quoted, because the arrow and `:dN` forms contain YAML-significant characters). A consumer joins the
  metadata to the edge by string-matching this token. One ref per source ordinal — a multi-source-ordinal
  verdict expands to one `dN -> target` ref each, since the source arrow grammar takes a single `dN`.
- **`confidence`** is a float in `[0, 1]`, the suggesting model's confidence at judgment time.
- **`tier`** is a derived label — `high` (≥0.9), `review` (≥0.7), `low` (<0.7) — carried for cheap
  styling without re-deriving the threshold. `confidence` is authoritative; `tier` is a convenience.

The `note:` records provenance and the block's overall status (a block is `machine-suggested,
unverified` when its weakest edge is `low`, else `validator-approved`). Per-edge truth lives in
`edge_confidence`, not the note.

## Tolerance, not consumption

`links check` scans only the known ref-list keys (`replaces`/`evolves`/`related_entries`/`supersedes`)
and `entry_id`; an unknown sibling key like `edge_confidence` is invisible to it, exactly as `note:`
is. So the field needs **no parser change** to be written safely — verified by probe: a corpus with
`edge_confidence` present reports `Session memory integrity OK`. Human-authored edges carry no
`edge_confidence`; its absence means "authored, not scored", never "confidence zero".

## Deferred (later stages)

Reading the field into the graph is intentionally out of scope here. When taken up it entails: carrying
confidence alongside the edge on the read side (`entry_link_sidecars` → the sidecar edge tuples →
`semantic_cache`/`service`), exposing it on the graph payload, and a Trail/graph affordance that weights
or filters low-confidence edges. Until then the data sits structured and durable, ready to consume.
