---
title: "Task-Packet Hardening Before Progressive Code Provenance"
date: "2026-09-05"
project: "memory-seed"
status: "active"
priority: "P0"
next_action: "Harden and independently review Task Packet compilation, then dogfood the improved packets while implementing progressive hunk provenance."
source:
  - "experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md"
  - "docs/CONSTITUTION.md"
scope: "Improve Task Packet precision, authority projection, execution contracts, and size reporting before implementing forward-only decision-to-code provenance across roots and pods."
non_goals:
  - "Do not backfill historical code provenance."
  - "Do not add language-specific symbol parsers, call graphs, test edges, or retrieval-ranking changes."
  - "Do not continue, merge, push, or release Seed Pod P0 until this prerequisite is integrated."
dependencies:
  - "Existing Task Packet v1 compiler, Retrieval Specification v2, accepted ADR heads, and per-clause Constitution anchors."
  - "Existing session commits field, Memory-Entry trailers, decision-level F fields, and Seed Pod runtime resolver."
acceptance_criteria:
  - "Improved packets project complete relevant Constitution clauses, avoid unrelated policy-reference decisions, expose component token composition, and carry exact creation, acceptance, implementation, and worktree contracts."
  - "Clean-context Terra workers implement progressive provenance from improved packets without re-fetching supplied governance evidence."
  - "Memory Seed stores only Git references while CLI and MCP generate bounded before/after code projections on demand."
  - "Dynamic cadence diagnostics and a ten-new-entry ceiling prevent pathological uncheckpointed batches without limiting prior decisions implemented by a commit."
---

# Task-Packet hardening before progressive code provenance

## Ordered delivery

1. Freeze Seed Pod P0 branches.
2. Harden Task Packet compilation and independently review it.
3. Recompile the original four Seed Pod packets and record before/after evidence in the existing reflection log.
4. Commit this provenance design and compile improved, track-specific packets with exact `implements` decision references.
5. Establish shared provenance interfaces serially, implement isolated tracks in parallel, then integrate and review serially.
6. Merge the foundation into the paused Seed Pod branches and resume their scoped reviews.

## Task Packet prerequisite

- Project Constitution clauses by stable `constitution:vN#slug` anchors. Prefer explicit dispatch refs, then selected ADR refs, then ranked whole clauses, and fall back to the full Constitution when confidence is insufficient.
- Carry clause path, ratified version, heading, line range, full-document and clause digests, selection reason, and full-document reference. Never truncate governing evidence silently.
- Make path selection exact by default; retrieving entries whose `F:` metadata mentions a path requires an explicit opt-in selector.
- Extend dispatch execution with `expected_absent`, directly testable `acceptance_observables`, and exact decision-level `implements` refs.
- Include absolute worktree/branch command context, explicit escalated-shell location verification, exact base/head/all-commit report receipts, and allowlist-backed scope-blocker checks.
- Preserve the current economy/balanced/frontier total budgets and add component measurements. Constitution projection targets are 2k/4k/8k tokens respectively; governing overages remain complete and explicit.

## Progressive provenance

- `Memory-Entry:` means a commit carries a newly authored entry. `Memory-Implements:` names earlier decisions implemented by the commit and is populated automatically from the activated Task Packet.
- Resolve code evidence from explicit implementation refs, entry-introducing non-merge commits, explicit `commits:` SHAs, and then valid non-merge entry trailers. Merge commits are integration evidence.
- Intersect exact paths in each decision's `F:` field with commit-changed files. Attribute unique matches automatically and return shared/unmatched hunks as candidates for agent confirmation. Many decisions may validly share a commit, file, or hunk.
- Persist only append-only binding references: decision, commit/parent, file, old/new blob IDs, hunk fingerprints/ranges/context hints, authorship, and replacement link. Never persist code blocks, patches, or generated snapshots.
- CLI and MCP `provenance show` generate verified before/after projections from Git with three context lines by default and a bounded 0-20 override. Add parity `bind` and read-only `check` surfaces plus ESR reporting.
- The decision's runtime owns its sidecar. Pods write their own bindings; roots navigate active descendants explicitly; retired pods are read-only; detached former roots retain metadata only.

## Commit cadence

- Warn on any high signal or two moderate signals across newly authored entries, decisions, changed non-memory files, and non-memory churn. Moderate thresholds are 3/5/8/300; high thresholds are 6/10/16/750.
- Surface health through situate, worktree guard, ESR, Task Packet compilation, and integration previews.
- Refuse more than ten newly authored entries in one ordinary commit without live user approval and a durable bulk reason. Do not count `Memory-Implements:` refs or previously authored integration entries, and never truncate attribution.

## Verification and reflection

- Preserve the measured baseline: 87.9% one-entry trailer commits; controlled exact changed-path coverage 75.8%; fully unique file attribution 54.0%; five historical 167-520 trailer outliers followed by a maximum of 14.
- Test complete clause projection, exact/opt-in path semantics, budget composition, new dispatch fields, fingerprints, CLI/MCP parity, and clean-context packet reconstruction.
- Test many-to-many commit/file/hunk provenance, projections without stored code, tamper/missing-Git/correction cases, root/pod lifecycle boundaries, cadence thresholds, and bulk-sidecar negative controls.
- Continue `experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md` with expected versus compiled versus used evidence, token composition, extra-hop classification, authority fidelity, self-sufficiency, instruction compliance, provenance, scope accuracy, and follow-on compiler recommendations.

