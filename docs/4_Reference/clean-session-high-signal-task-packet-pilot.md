# Clean-session high-signal Task Packet pilot

> **Status:** corrected compiler-backed pilot rerun 2026-09-01. The
> versioned fixture is reproducible; each exported packet is derived and ephemeral.
> The older M1 convention pilot remains below as historical evidence.

## Purpose and authority boundary

This example turns an accepted clean-worker Evidence Pack pilot into a repeatable
handoff shape. It applies the packet convention established by
[`mse_4jbfzs490zcy9q06`](../../.memory-seed/sessions/2026-08/2026-08-31.md): an
orchestrator selects and materializes bounded evidence, while the worker reports
only what that evidence establishes. The accepted curated pilot is recorded by
[`mse_r0z6p0gfxap0ps23`](../../.memory-seed/sessions/2026-08/2026-08-31.md).

The current surface retains inline `memory-seed/retrieval-spec` v1 compatibility and adds exact
project-local profile resolution, Retrieval Specification v2, Evidence Pack v2, semantic
`memory-seed/task-dispatch` v1, and compiled `memory-seed/task-packet` v1. The worker has no implied
write, shell, merge, network, or broad durable-memory authority.

Evidence Pack v2 uses `id` consistently: ADR evidence carries its frontmatter
`adr_id`, session decision evidence carries its canonical decision ID, `kind`
distinguishes `adr` from `decision`, and `source` remains the canonical Markdown
path. `content_digest` verifies the selected content; it is not another identity.
The v1 fingerprints and counts later in this document are retained as historical
pilot evidence and must not be sent as a current pack without re-resolution.

## Current compiler-backed clean-session pilot (2026-09-01)

The frontier-authored artifact is the minimal semantic dispatch in
`tests/fixtures/task_packet_pilot/dispatch.json`. It does not duplicate resolved sources or hand-author a
complete packet. The deterministic compiler combines that dispatch with `implementation:v1`, the measured
binding of a fresh offline Git fixture, and the pinned corpus revision to reconstruct the complete Task
Packet. The versioned fixture corpus, exact caller-supplied worker environment, and recorded clean-worker
assessment are committed. The exported packet and fresh
fixture checkout are derived, ephemeral output and stay untracked.

Every worker-visible document counts toward input. Resolver `token_estimate` is evidence-only; it is not
total worker input or actual provider usage. Materialized sources are present once under
`materialized_evidence`; the worker contract says not to refetch them. The input ledger is the
compiler-accounted caller-supplied envelope (serialized packet plus the exact fixed instructions and tool
manifest), while the output/reasoning reserve and cost ledger remain distinct. It is not actual provider
input: hidden platform/system/tool overhead and provider total input are unavailable because the runtime did
not surface them. Actual provider usage, latency, and cost are also post-run evidence only. Compilation performs no registry write,
worker dispatch, worktree creation, authority expansion, provider/pricing lookup, or network access.

The recorded assessment is worker self-report evidence. Its no-refetch, zero-supplemental-call, and
no-broad-discovery fields are not mechanically replayed proof: independent tool-call instrumentation was
unavailable. Regression tests validate its JSON shape, evidence references, and ledger consistency, not
execution provenance the harness could not observe.

The fixture compiled to packet fingerprint
`sha256:699016efbbc7c5ed95d0228238d29f7ce240403567f74b3337d31c29c2a5276a` at corpus revision
`git:dcc00d65ff1d917a8ba7c59adc5ef1f3d248c1b8:sha256:ddfb66e8981d6656267e9d5287bea87029c795203bd895675cdd41d42255ce51`.

| Compiler/pilot measurement | Result |
|---|---:|
| Frontier semantic-dispatch handoff estimate | 574 tokens |
| Resolver evidence estimate / materialized content estimate | 352 / 352 tokens |
| Serialized complete packet input | 3,347 tokens |
| Exact caller fixed instructions | 447 tokens |
| Stable caller tool manifest | 124 tokens |
| Supplemental-input reserve | 1,000 tokens |
| Total input ledger | 4,918 tokens |
| Output/reasoning reserve | 2,500 tokens |
| Total context envelope | 7,418 tokens |
| Selected tier / soft cap / status | balanced / 48,000 / within target |
| Materialized evidence IDs | `mse_packetpilot:d1`, `adr_task_packet_pilot`, `docs/CONSTITUTION.md`, `docs/pilot-support.md` |

A genuinely fresh clean worker (`/root/m2_task4_impl/m2_task4_pilot_round2_clean`, `gpt-5.6-terra`, medium reasoning,
`fork_turns: none`) received only the exact packet and `worker_environment` paths. Its recorded self-report
found the pack sufficient and returned three source-linked conclusions using all four valid materialized
evidence IDs. It reported no missing questions, supplemental sources/calls, unsupported assertions,
repeated fetches, or broad discovery. The latter two claims remain worker self-report because independent
tool-call instrumentation was unavailable.

The assessment records `caller_supplied_harness_accounting` as available with 447 fixed-instruction tokens
and 124 tool-schema tokens from the compiler ledger. It records `hidden_platform_overhead` separately as
unavailable because the runtime did not surface it. Actual provider total input, usage, latency, and cost
were likewise not surfaced and remain unavailable. The compiler-accounted values above are not substitutes
for post-run provider telemetry.

The offline regression test recompiles the fixture twice and asserts canonical byte identity, exact
profile/binding use, nonzero fixed-instruction/tool-manifest accounting, single-copy materialization,
recorded assessment shape/reference/ledger consistency, balanced-cap compliance, unavailable provider and
cost evidence when telemetry/pricing are absent, and
absence of registry/dispatch/worktree/network/authority expansion fields.

## Historical M1 convention pilot

The remaining sections preserve the August 2026 inline-only pilot. Its numbers and terminology are
point-in-time evidence, not the current compiled-packet contract.

## Worker launch contract

```yaml
context_load: packet
role: researcher
capability_tier: standard
memory_update_policy: orchestrator
working_revision: <rerun corpus revision>
evidence_pack: <manifest or returned inline result>
materialized_evidence:
  - id: <matching manifest evidence ID>
    kind: <matching evidence kind>
    source: <canonical Markdown path>
    lines: <inclusive source range>
    content_digest: <matching manifest digest>
    content: <bounded source-linked slice>
context_budget: <ledger path or inline ledger>
```

Use `memory_update_policy: orchestrator` for normal delegated work: the
worker writes no memory, and the orchestrator decides whether the durable result
warrants logging. An explicitly delegated, branch-local pilot may instead use
`worker_checkpoint`; that is the sole narrow exception and grants only the named
guarded checkpoints, not control-plane ownership.

The `standard` worker in this example was routed under the accepted provisional
balanced packet-budget band: a 32K starting target, 48K soft cap, and 64K shard
threshold. This routing/budget band is contextual planning guidance, not another
Task Packet field or a replacement capability-tier value.

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
      "docs/7_Replaced/declarative-retrieval-specification-proposal.md",
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
38,002 projection, 9,998 below the provisional balanced packet-budget band's
48K soft cap. It was not a
provider-reported realized total. Record every supplemental call with its missing
question, source/range, estimate, and whether it returned evidence or only a
measurement. Stop discretionary reads at the soft cap and return `NEEDS_CONTEXT`
when a required gap exceeds budget, scope, or authority. Applicable Memory Seed
read and retrieval tools remain available, but their use is subject to those same
recorded-gap and debit rules; availability does not authorize broad discovery.

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

For the Task 3 planning view under that provisional balanced packet-budget band,
non-evidence categories total 22,700 tokens: 2,000 brief/dispatch, 200 project
context, 1,500 procedure pointers, 3,500 accepted report, 1,500 scoped
instructions, 6,000 tool/schema reserve, and 8,000 supplemental/synthesis
headroom. If an orchestrator materializes this rerun's 19,335 selected evidence
estimate, the conservative all-inclusive planning projection is 42,035 tokens
(19,335 + 22,700), 5,965 below the 48K soft cap and below the 64K shard threshold.
This is a planning calculation, not a measured model-context total; the 2,500
manifest/materialized-evidence line in the original 25,200 packet plan must be
replaced, not added, when using the resolved estimate.

This checkpoint made two required resolver calls—preview and resolve—but made no
supplemental canonical-source fetch or materialized-evidence reread. With
`include_excerpts: false`, their returned packs provide selection metadata and
fetch recipes, not 19,335 tokens of source text. For a later worker, each chosen
source-range fetch must still be logged and debited before synthesis.

## Pilot limitations

The supplied evidence established a read-only inline interface and runtime path
containment. It did not independently re-prove byte parity, no-write behavior,
timeouts, corpus-change handling, provider accounting, cache behavior, or proposed
execution/write `allowed_files`/caller-permission, redaction, and network controls. Those file lists do
not filter memory reads or prevent task-scoped evidence materialization. Do not turn
those reported or proposed properties into fresh claims without targeted evidence.
