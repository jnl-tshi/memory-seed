# ADR attachment candidates (topic-matched)

Decisions ranked by topics shared with the ADR. Topics come from the decision-level sidecar, which is the authority (precedence sidecar -> authored, never a union).

- ADRs with no attached decision and at least one topic: **20**
- of those, with candidates: **20**

Candidates only. Attaching a decision means a `revise` event, which moves the ADR head - the same stakes as a lineage move - so nothing here is applied without being named.

## adr_agent_config_merge
*Agent-config JSON/TOML merge, never seed-copy*
- ADR topics: cli, control-plane, process-correction
- `mse_m6amd5db4c7s8sfw:d3` (2 shared: control-plane, process-correction)
    - D3 - Keep live and seed runtime behavior aligned
- `ms-1bcfcc91:d2` (1 shared: control-plane)
    - D2 - Persist selection in project.yaml; absent = ALL (backward-compat)
- `ms-1bcfcc91:d3` (1 shared: cli)
    - D3 - `agents add/remove` with strip-in-place uninstall
- `ms-1bcfcc91:d4` (1 shared: control-plane)
    - D4 - Cursor needs no routing file (researched)
- `ms-1c7b9e3a:d1` (1 shared: cli)
    - D1 - help leans on argparse, not a hand-curated duplicate

## adr_archive_before_replace
*Archive control-plane snapshots before replacing versioned artifacts*
- ADR topics: control-plane, process-management, release
- `ms-5c3b8e12:d2` (2 shared: control-plane, release)
    - D2 - Patch release 2.2.1 for control-plane version bump
- `ms-757053d4:d4` (2 shared: control-plane, release)
    - D4 - Version bump 2.5→2.6 (release content)
- `ms-a939b6b4:d1` (2 shared: control-plane, release)
    - D1 - Bundle three baseline seed promotions into 2.7.0
- `ms-e30b9c47:d2` (2 shared: control-plane, release)
    - D2 - Control-plane bump 2.2 -> 2.3 is required, not optional
- `mse_w0jh7s6adamfkyt5` (2 shared: control-plane, process-management)
    - 2026-08-03 19:16 - Remove stale Codex worktree residue

## adr_branch_session_fuse
*Branch-session fuse: branch-only, chronological, immutable relative to base*
- ADR topics: branch-history, git-workflow
- `mse_2x8yysgezex3tbys` (1 shared: git-workflow)
    - 2026-07-30 14:26 - Verify visible safe-merge worktree cleanup
- `mse_3x2d61jkn3jstpyg:d1` (1 shared: git-workflow)
    - D1 - Decision
- `mse_4z9wcanedg82wp16` (1 shared: git-workflow)
    - 2026-07-15 19:01 - Integrate ranking and long-horizon workstream into main
- `mse_5mv4dvxfp1tr8v16` (1 shared: git-workflow)
    - 2026-07-10 15:35 - Lifecycle clarification: merge-branch evolves the fuse workfl
- `mse_61bnt9ty6rfgpw1e:d3` (1 shared: git-workflow)
    - D3 - Wrote around a concurrent session rather than through it

## adr_community_detection_rejected
*Topology-community detection measured and rejected*
- ADR topics: design-evaluation, graph, memory-trace
- `mse_07veztrwd4w9tfby:d4` (2 shared: design-evaluation, memory-trace)
    - D4 - Reheat uses d3-force; the global layout stays cose
- `mse_0qycwt519qdggrpe:d1` (2 shared: design-evaluation, graph)
    - D1 - Topic is not a relationship, so it is not a default edge
- `mse_0qycwt519qdggrpe:d3` (2 shared: design-evaluation, graph)
    - D3 - Losing 152 nodes is the honest outcome, and they are old
- `mse_3yvakpxdshc95e68:d1` (2 shared: design-evaluation, graph)
    - D1 - Communities come from authored topics, not from structural detection
- `mse_3yvakpxdshc95e68:d2` (2 shared: design-evaluation, graph)
    - D2 - Most distinctive, not most common, and never first-listed

## adr_docs_lifecycle_folders
*Docs taxonomy: folder is lifecycle state*
- ADR topics: docs-lifecycle, documentation, governance-profile
- `ms-bde55cc2:d1` (2 shared: docs-lifecycle, documentation)
    - D1 - Decision
- `mse_21d4kcx6g1vxt0ky:d1` (2 shared: docs-lifecycle, documentation)
    - D1 - Decision
- `mse_5hgxywp0n3qsz0dw:d1` (2 shared: docs-lifecycle, documentation)
    - D1 - Decision
- `mse_9s1yhyh43qp1k3mx:d1` (2 shared: docs-lifecycle, documentation)
    - D1 - Decision
- `mse_a0bxp5n1wcnsjxvw:d4` (2 shared: docs-lifecycle, documentation)
    - D4 - Reconcile the canonical planning surfaces

## adr_draft_format
*DRAFT single-decision baseline; D/R mandatory; numbered decisions canonical*
- ADR topics: schema, session-logging
- `ms-0bd3d8b2:d2` (1 shared: session-logging)
    - D2 - Keep sub-project logs local but summarize parent-visible changes
- `ms-2e9c5f31:d2` (1 shared: session-logging)
    - D2 - Embed DRAFT labels in the staleness hook reminder
- `ms-2e9c5f31:d3` (1 shared: session-logging)
    - D3 - Add DRAFT reminder to retrieval hook too
- `ms-3a7c5f2b:d1` (1 shared: session-logging)
    - D1 - Times are approximate for retroactively logged entries
- `ms-3a9a99a6:d1` (1 shared: session-logging)
    - D1 - Decision

## adr_edge_kinds
*Four never-merged edge kinds, forward-only and acyclic*
- ADR topics: graph, lifecycle-edges
- `mse_07veztrwd4w9tfby:d1` (1 shared: graph)
    - D1 - "462 of 603" was two faults sharing one number
- `mse_07vwfbgsk31ec7d6:d1` (1 shared: graph)
    - D1 - Decision
- `mse_0842kjv76f4btrr8:d2` (1 shared: graph)
    - D2 - Fixed Graph tab + efficiency
- `mse_0qycwt519qdggrpe:d1` (1 shared: graph)
    - D1 - Topic is not a relationship, so it is not a default edge
- `mse_0qycwt519qdggrpe:d2` (1 shared: graph)
    - D2 - The measurement that justified it was wrong the first time

## adr_encoding_policy
*Encoding policy owned by Seed, never duplicated in Trace*
- ADR topics: control-plane, seed-core, windows-encoding
- `ms-1bcfcc91:d2` (1 shared: control-plane)
    - D2 - Persist selection in project.yaml; absent = ALL (backward-compat)
- `ms-1bcfcc91:d4` (1 shared: control-plane)
    - D4 - Cursor needs no routing file (researched)
- `ms-5c3b8e12:d2` (1 shared: control-plane)
    - D2 - Patch release 2.2.1 for control-plane version bump
- `ms-6e1aadec:d1` (1 shared: control-plane)
    - D1 - Decision
- `ms-74475f71:d1` (1 shared: control-plane)
    - D1 - Decision

## adr_entry_id_scheme
*Deterministic 80-bit mse_ ids; legacy ms- never rewritten*
- ADR topics: schema
- `ms-8e44a1c7:d1` (1 shared: schema)
    - D1 - Decision
- `ms-a4282580:d2` (1 shared: schema)
    - D2 - Entry IDs and related links
- `mse_4670mpw532yec14w:d1` (1 shared: schema)
    - D1 - Decision
- `mse_5zg50mzrmtx80c80:d2` (1 shared: schema)
    - D2 - Deterministic evidence score joins the edge-confidence spec as a derived re
- `mse_67y44fsj2srz0eyz:d2` (1 shared: schema)
    - D2 - A decision-level edge suppresses its pair in link audit

## adr_experiment_isolation
*Experiment fixture isolation is structural via nearest-runtime discovery*
- ADR topics: functionality-audit, seed-core, testing
- `mse_b1q6bjqv5w1zyn2k:d3` (2 shared: seed-core, testing)
    - D3 - Pinned the coupling to core's format parser with a test
- `ms-4e1b8a07:d1` (1 shared: functionality-audit)
    - D1 - Decision
- `ms-757053d4:d3` (1 shared: seed-core)
    - D3 - Hygiene: per-prompt hook reconcile + test trims + index staleness
- `ms-8308e577:d1` (1 shared: testing)
    - D1 - Decision
- `ms-8e44a1c7:d1` (1 shared: testing)
    - D1 - Decision

## adr_integration_mode
*Configurable integration_mode: local-merge vs PR*
- ADR topics: control-plane, git-workflow
- `ms-1bcfcc91:d2` (1 shared: control-plane)
    - D2 - Persist selection in project.yaml; absent = ALL (backward-compat)
- `ms-1bcfcc91:d4` (1 shared: control-plane)
    - D4 - Cursor needs no routing file (researched)
- `ms-5c3b8e12:d2` (1 shared: control-plane)
    - D2 - Patch release 2.2.1 for control-plane version bump
- `ms-6e1aadec:d1` (1 shared: control-plane)
    - D1 - Decision
- `ms-74475f71:d1` (1 shared: control-plane)
    - D1 - Decision

## adr_legacy_agents_compat
*Legacy .AGENTS/ compatibility retained until intentional removal*
- ADR topics: agent-collaboration, control-plane, memory-repair
- `mse_sw54jn8k80g9t5mg:d1` (2 shared: agent-collaboration, control-plane)
    - D1 - Ship Phase 1 only, move the plan to completed with deferred follow-ons note
- `ms-1bcfcc91:d2` (1 shared: control-plane)
    - D2 - Persist selection in project.yaml; absent = ALL (backward-compat)
- `ms-1bcfcc91:d4` (1 shared: control-plane)
    - D4 - Cursor needs no routing file (researched)
- `ms-5c3b8e12:d2` (1 shared: control-plane)
    - D2 - Patch release 2.2.1 for control-plane version bump
- `ms-6e1aadec:d1` (1 shared: control-plane)
    - D1 - Decision

## adr_markdown_substrate
*Plain-Markdown core for file-reading agents*
- ADR topics: control-plane, documentation, seed-core
- `ms-a7d29f64:d2` (2 shared: control-plane, documentation)
    - D2 - Restore two-step skill-registry wording in AGENTS.md
- `mse_03bwbpzck2qdkeh7:d1` (2 shared: documentation, seed-core)
    - D1 - Decision
- `mse_52cw7g10wmaha5h4:d1` (2 shared: control-plane, documentation)
    - D1 - Decision
- `mse_5p94m2c3rwy7kbtj:d2` (2 shared: control-plane, documentation)
    - D2 - Developer persona evolution: verify ground-truth STATE from source of truth
- `mse_5y962348e85x7grr:d1` (2 shared: control-plane, documentation)
    - D1 - Decision

## adr_release_topology
*Publish via GitHub Release with manual PyPI gate*
- ADR topics: git-publishing, release, release-packaging
- `ms-3cad2a35:d1` (1 shared: release)
    - D1 - 2.8.0 release boundary
- `ms-5c3b8e12:d2` (1 shared: release)
    - D2 - Patch release 2.2.1 for control-plane version bump
- `ms-6b21d9f4:d1` (1 shared: release)
    - D1 - Decision
- `ms-72aa01ec:d1` (1 shared: release)
    - D1 - Decision
- `ms-757053d4:d4` (1 shared: release)
    - D4 - Version bump 2.5→2.6 (release content)

## adr_runtime_discovery
*Runtime discovery walks to the nearest .memory-seed*
- ADR topics: agent-rules, control-plane
- `mse_q0csfqb2darg474m:d1` (2 shared: agent-rules, control-plane)
    - D1 - Decision
- `ms-1bcfcc91:d1` (1 shared: agent-rules)
    - D1 - Central AGENTS registry + per-agent tagging
- `ms-1bcfcc91:d2` (1 shared: control-plane)
    - D2 - Persist selection in project.yaml; absent = ALL (backward-compat)
- `ms-1bcfcc91:d4` (1 shared: control-plane)
    - D4 - Cursor needs no routing file (researched)
- `ms-2e9c5f31:d1` (1 shared: agent-rules)
    - D1 - Move Reason Rules before Entry Shapes

## adr_topic_backfill_rejected
*Scored topic auto-backfill rejected; curated-evidence premise adopted*
- ADR topics: decision-harvest, topic-vocabulary
- `mse_0n9nwq9qj6dp493f:d2` (1 shared: decision-harvest)
    - D2 - Fix: Decision Harvest + sidecar positive-trigger tightening missing/stale
- `mse_25zzy3cmdjgrsf69:d1` (1 shared: topic-vocabulary)
    - D1 - Declare the axis on roots only and let children inherit it
- `mse_25zzy3cmdjgrsf69:d2` (1 shared: topic-vocabulary)
    - D2 - Promote only the aliases the corpus actually authored
- `mse_25zzy3cmdjgrsf69:d3` (1 shared: topic-vocabulary)
    - D3 - Flag three aliases as wrong in place rather than rehome them
- `mse_25zzy3cmdjgrsf69:d4` (1 shared: topic-vocabulary)
    - D4 - Promote licensing and re-file audit against the incoming suspicion

## adr_topic_vocabulary
*Controlled topic vocabulary with axis hierarchy and seed/live parity*
- ADR topics: governance-profile, schema, topic-vocabulary
- `ms-8e44a1c7:d1` (1 shared: schema)
    - D1 - Decision
- `ms-a4282580:d2` (1 shared: schema)
    - D2 - Entry IDs and related links
- `mse_03fpxwznab7efk1r:d1` (1 shared: governance-profile)
    - D1 - Decision
- `mse_25zzy3cmdjgrsf69:d1` (1 shared: topic-vocabulary)
    - D1 - Declare the axis on roots only and let children inherit it
- `mse_25zzy3cmdjgrsf69:d2` (1 shared: topic-vocabulary)
    - D2 - Promote only the aliases the corpus actually authored

## adr_trace_incremental_startup
*Trace startup incremental; immutable git derivations persist*
- ADR topics: memory-trace, performance, seed-core
- `mse_3yvakpxdshc95e68:d4` (2 shared: memory-trace, performance)
    - D4 - Selection restyle memoised on its two real inputs
- `mse_5ezgxb11ssjzqjsr:d1` (2 shared: memory-trace, performance)
    - D1 - The 150-node live-motion bound was withdrawn, with the measurement that bro
- `mse_74f1jkr8rv4b7hrp:d5` (2 shared: memory-trace, performance)
    - D5 - The settle re-measures the camera 4x a second, and a warm mount stops early
- `mse_qerqhsqw8hfzp5d3:d2` (2 shared: memory-trace, performance)
    - D2 - Share one parsed topic vocabulary per Trace request
- `mse_r5m6rdypd34dz9j0:d1` (2 shared: memory-trace, performance)
    - D1 - Zonal settling is declined on measurement, not on taste

## adr_trail_derived_lanes
*Trail derives display lanes without authored graph edges*
- ADR topics: graph, memory-trace, trail
- `mse_fadg58mgtypvypzt` (2 shared: graph, memory-trace)
    - 2026-07-16 09:18 - Integrate B0a renderer-neutral graph contract
- `mse_07veztrwd4w9tfby:d1` (1 shared: graph)
    - D1 - "462 of 603" was two faults sharing one number
- `mse_07veztrwd4w9tfby:d2` (1 shared: memory-trace)
    - D2 - Edgeless entries get a computed halo, not a simulation
- `mse_07veztrwd4w9tfby:d3` (1 shared: memory-trace)
    - D3 - Overflow was minZoom clamping the fit, not a missing fit
- `mse_07veztrwd4w9tfby:d4` (1 shared: memory-trace)
    - D4 - Reheat uses d3-force; the global layout stays cose

## adr_worktree_convention
*Worktree=session, branch=task, agent-namespaced branch names*
- ADR topics: agent-collaboration, continuity, git-workflow
- `mse_27jbk0z5nkg4jabe:d2` (1 shared: agent-collaboration)
    - D2 - A branch existing at all can contaminate a concurrent session's entries
- `mse_2x8yysgezex3tbys` (1 shared: git-workflow)
    - 2026-07-30 14:26 - Verify visible safe-merge worktree cleanup
- `mse_3x2d61jkn3jstpyg:d1` (1 shared: git-workflow)
    - D1 - Decision
- `mse_4z9wcanedg82wp16` (1 shared: git-workflow)
    - 2026-07-15 19:01 - Integrate ranking and long-horizon workstream into main
- `mse_5mv4dvxfp1tr8v16` (1 shared: git-workflow)
    - 2026-07-10 15:35 - Lifecycle clarification: merge-branch evolves the fuse workfl

