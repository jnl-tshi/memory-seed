# Clean-session high-signal Task Packet pilot

> **Status:** worked pilot reference, derived at a point in time. It documents an
> orchestration convention; it is not a new API, policy, or authority source.
> Rerun the inline Retrieval Specification preview and resolve against the intended
> dispatch revision before relying on any values below.

## Purpose and authority boundary

This example turns an accepted clean-worker Evidence Pack pilot into a repeatable
handoff shape. It applies the packet convention established by
[`mse_4jbfzs490zcy9q06`](../../.memory-seed/sessions/2026-08/2026-08-31.md): an
orchestrator selects and materializes bounded evidence, while the worker reports
only what that evidence establishes. The accepted curated pilot is recorded by
[`mse_r0z6p0gfxap0ps23`](../../.memory-seed/sessions/2026-08/2026-08-31.md).

The shipped M1 surface is an inline `memory-seed/retrieval-spec` v1 request and
an ephemeral Evidence Pack result. `context_load`, packet fields, materialized
evidence, budget ledgers, and `memory_update_policy` are operating conventions,
not schema-enforced API fields. The worker has no implied write, shell, merge,
or broad durable-memory authority.

## Worker launch contract

```yaml
context_load: packet
worker_role: researcher
capability_tier: balanced
memory_update_policy: orchestrator
working_revision: <rerun corpus revision>
evidence_pack: <manifest or returned inline result>
materialized_evidence:
  - <bounded source-linked slice>
context_budget: <ledger path or inline ledger>
```

Use `memory_update_policy: orchestrator` for normal delegated work: the
orchestrator owns durable session memory. An explicitly delegated,
branch-local pilot may instead use `worker_checkpoint`; that exception grants
only the named guarded checkpoints, not control-plane ownership. Use `none` for
workers that must not write session memory at all.

## Compact project context example

Memory Seed is a Markdown-authoritative, local-first project-memory system with
guarded append-only session history. Its inline Retrieval Specification makes
selection reproducible; the resolver returns a bounded, ephemeral Evidence Pack;
and Task Packets bound delegated work. Assess the supplied curated authority and
implementation evidence only, distinguish what is implemented from procedural
convention, debit any supplemental reads, and leave product and policy files
unchanged. This packet is for a clean worker, so it supplies the decision context
and source-linked material needed for the task without authorizing broad discovery
or durable-memory writes.

## Inline Retrieval Specification

The accepted pilot used this effective inline v1 specification. Preserve it as
data with the packet; do not substitute a named profile or registry reference.

```json
{
  "schema": "memory-seed/retrieval-spec",
  "version": 1,
  "required": {
    "constitution": true,
    "evidence": {"mode": "latest"},
    "related_decisions": {"depth": 1}
  },
  "filters": {
    "paths": [
      "docs/2_Todo/declarative-retrieval-specification-proposal.md",
      ".memory-seed/decisions/adr_retrieval_entry_granularity.md",
      ".memory-seed/decisions/adr_mcp_metadata_and_filters.md"
    ],
    "topics": []
  },
  "limits": {"max_entries": 20, "max_tokens": 20000},
  "ordering": ["required_first", "graph_distance", "recency", "stable_identity"],
  "on_missing": {"required": "fail", "optional": "report"},
  "optional": {"sessions": null},
  "output": {"include_excerpts": false, "include_resolution_trace": true}
}
```

The orchestrator runs both read-only operations before dispatch. `preview` shows
the planned selection without creating a pack; `resolve` returns the inline pack,
effective-spec fingerprint, corpus revision, resolver version, selection metadata,
trace, warnings/omissions, and pack fingerprint. A manifest with excerpts disabled
is a fetch recipe, not proof that whole referenced files were injected.

## Evidence selection and materialization

The accepted Task 2 run at corpus revision
`git:2e839ba39fa91ea8f80bd900c9ceff41a7b4a046:sha256:9606aa46842fed745bffcb95b01f51d74708d7a454e88bfd0252c6448ba5b0c6`
had effective-spec fingerprint
`sha256:416e808c16e8395912b70135b43d3ca4d61e1f4e52200198622036a48e3b1f7c`
and pack fingerprint
`sha256:ba926d5f107b9441e35daba36b4cbea595a654251f38991253911863e26b209e`.
It selected 14 records, estimated 18,966 evidence-content tokens, and reported no
warnings or omissions. These values are historical pilot facts, not stable IDs for
a later dispatch.

Materialize bounded, source-linked slices beside the manifest:

| Artifact | Purpose | Estimate |
|---|---|---:|
| Curated authority | Constitution clauses, ADR current views, proposal/API boundary | 5,751 |
| Curated decisions | Current convention and linked rationale | 3,086 |
| Curated contract code | Inline v1 validation and MCP boundary | 2,331 |
| Curated resolver code | Runtime guard, readers, limiter, preview/resolve | 3,323 |

Every slice should retain canonical path, inclusive line range, selection reason,
and revision. Treat accepted ADR current-view material as the current statement and
session slices as rationale: M1 path filtering selected ADR Markdown but did not
provide a native lifecycle-aware ADR selector.

## Context-budget ledger

Account for all worker-visible context, rather than treating the resolver estimate
as the model-context total.

| Category | Pilot estimate |
|---|---:|
| Brief, manifest, curated evidence | 17,350 |
| Budget artifact and dispatch/project frame | 1,550 |
| Tool/schema reserve | 6,000 |
| Supplemental retrieval reserve | 2,000 |
| Synthesis headroom | 4,000 |
| **Planning envelope** | **30,900** |

In the accepted assessment, three bounded supplemental calls (two rereads of
materialized evidence plus one measurement-only check) totalled 9,102 estimated
tokens. Replacing—not adding to—the 2,000-token reserve produced a conservative
38,002 projection, 9,998 below the balanced 48K soft cap. It was not a
provider-reported realized total. Record every supplemental call with its missing
question, source/range, estimate, and whether it returned evidence or only a
measurement. Stop discretionary reads at the soft cap and return `NEEDS_CONTEXT`
when a required gap exceeds budget, scope, or authority.

## Dispatch checklist

1. Bind the inline spec to the intended checkout and run preview then resolve.
2. Record the returned revision, effective-spec and pack fingerprints, selected
   count/estimate, tier decision, warnings, and omissions.
3. Materialize only the selected, task-relevant source slices; label each as
   evidence rather than treating a manifest reference as injected content.
4. Include the compact project frame, explicit allowed outputs, budget ledger,
   and `memory_update_policy`.
5. Require source-linked claims, supplemental debit, and a clear boundary between
   implementation facts, conventions, historical reports, and unproven claims.

## Checkpoint validation: rerun at this reference revision

At `f113354ed7f23f4b7edcc6656ab2a023e2f8991d`, this reference reran the exact
inline specification above in read-only preview and resolve. Both completed on
the first revision attempt with corpus revision
`git:f113354ed7f23f4b7edcc6656ab2a023e2f8991d:sha256:0fa775cfb613f511f69d88c37a5ac87aec17e4bd78e7c47495aade3bb093555d`,
effective-spec fingerprint
`sha256:416e808c16e8395912b70135b43d3ca4d61e1f4e52200198622036a48e3b1f7c`,
and resolver version 1. The preview was valid and explicitly reported
`read-only; no Evidence Pack created`; resolve returned a complete ephemeral
pack with fingerprint
`sha256:0cc537d9c63abb0a0445ae4fc1289fd8e836b23a655fa7eb893d31812d3e3d64`.

| Rerun result | Value |
|---|---:|
| Prepared/selected evidence records | 15 |
| Evidence-content estimate | 19,335 |
| Warnings | 0 |
| Omissions | 0 |
| Candidate records | 15 |
| Related-decision roots / visited decisions | 3 / 11 |
| Excerpts materialized by this operation | 0 |

The additional record relative to the accepted Task 2 run is the accepted curated
pilot decision at graph distance one; that is an expected consequence of rerunning
the same depth-one graph after the pilot was recorded. It refines the point-in-time
example without changing the bounded-packet premise.

For the Task 3 balanced-tier planning view, non-evidence categories total 22,700
tokens: 2,000 brief/dispatch, 200 project context, 1,500 procedure pointers,
3,500 accepted report, 1,500 scoped instructions, 6,000 tool/schema reserve, and
8,000 supplemental/synthesis headroom. If an orchestrator materializes this
rerun's 19,335 selected evidence estimate, the conservative all-inclusive planning
projection is 42,035 tokens (19,335 + 22,700), 5,965 below the 48K soft cap and
below the 64K shard threshold. This is a planning calculation, not a measured
model-context total; the 2,500 manifest/materialized-reference line in the original
25,200 packet plan must be replaced, not added, when using the resolved estimate.

This checkpoint made two required resolver calls—preview and resolve—but made no
supplemental canonical-source fetch or materialized-evidence reread. With
`include_excerpts: false`, their returned packs provide selection metadata and
fetch recipes, not 19,335 tokens of source text. For a later worker, each chosen
source-range fetch must still be logged and debited before synthesis.

## Pilot limitations

The supplied evidence established a read-only inline interface and runtime path
containment. It did not independently re-prove byte parity, no-write behavior,
timeouts, corpus-change handling, provider accounting, cache behavior, or proposed
`allowed_files`/caller-permission, redaction, and network controls. Do not turn
those reported or proposed properties into fresh claims without targeted evidence.
