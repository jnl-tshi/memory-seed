# Strong ADR–Constitution Context: experiment notes

Status: **DRAFT — no production contract change**

## Hypothesis

For a high-ranked canonical decision result, an answer needs three mechanically
joined layers: the full decision block, each ADR whose validated lineage
contains that decision, and the text of the Constitution sections bound to the
relevant ADR revision. Lower-ranked results should remain compact and only
name their ADR references. `related` remains supporting evidence, never a
lineage or ADR-discovery edge.

The offline sweep measures whether that tiering preserves the required
decision, authority, typed lineage, ADR, and Constitution evidence at the
smallest token proxy. Recall at K=1/2/3/5/8 measures ranking quality only; it
is not an MCP setting, field, or persistence surface. The present
`strong`/`weak`/`none` band is explicitly uncalibrated at live scale, so it is
only a side-by-side diagnostic; rank decides expansion in this experiment.

## Proposed ADR representation to evaluate

The current fixture binding is deliberately ADR-wide because it is an
experiment input. A living ADR can evolve across different Constitutional
constraints, so an eventual production representation should bind sections to
the `revision-proposed` event that owns the synopsis:

```json
{
  "decision_ref": "mse_example:d2",
  "constitution_refs": [
    {"ref": "constitution:v1#recoverability", "role": "governing"},
    {"ref": "constitution:v1#provenance", "role": "supporting"}
  ]
}
```

The current view would derive its Constitution references from the accepted
revision. Historical, pending, and rejected revisions retain their own
bindings alongside their typed `evolves`/`replaces` predecessors. This makes a
rejected branch inspectable without allowing it to govern the current concern.

## Compatibility and migration

- This is additive, revision-scoped metadata; existing ADRs remain valid with
  no Constitution binding until explicitly enriched.
- The experiment must first create versioned fixture and gold definitions with
  revision-specific requirements. The existing ADR-wide fixture binding is a
  control, not a production-format decision.
- No ADR parser, Markdown ledger, MCP output, retrieval response, or ranking
  default changes from this document. Any such change needs a separately
  approved ADR transition after the experiment recommendation.

## Current implementation boundary

`strong_context_fixture_v2.py` joins generated fixture Constitution blocks,
parsed ADR ledgers, and production lexical decision ranking in memory only.
`strong_context_sweep_v2.py` evaluates allocation configurations in bounded
parallel workers and labels Constitution targets derived from the legacy gold
as provisional. It cannot freeze a candidate or authorize a provider run.
