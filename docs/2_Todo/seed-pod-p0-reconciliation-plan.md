---
title: "Seed Pod P0 architecture reconciliation plan"
date: "2026-09-06"
project: "memory-seed"
status: "active"
priority: "P0"
blocked_by: "independent plan review approval"
next_action: "Independently review this reconciliation plan before staging any Seed Pod P0 implementation work."
source:
  - "Approved Seed Pod P0 contract recorded on historical branch b7e623b"
  - "docs/2_Todo/task-packet-hardening-progressive-provenance-plan.md"
  - "docs/CONSTITUTION.md"
scope: "Reconstruct Seed Pod P0 on current main: governed .memory-seed-pod boundaries, pod-owned provenance, root promotion summaries, explicit inspection, lifecycle/diagnostic parity, migration compatibility, and verification."
non_goals:
  - "Do not merge, rebase, cherry-pick, delete, or otherwise alter b7e623b, 9284ef4, f6bc92c, ada4f2e, or 4fb275e."
  - "Do not implement, merge, push, release, or begin P1 federated retrieval in this planning change."
  - "Do not rewrite, delete, or silently relocate historical session or provenance records."
dependencies:
  - "Ratified Constitution v1.12: append-only, evidence-first, and identical write-surface invariants."
  - "adr_subproject_scoping, adr_branch_session_fuse, adr_worktree_convention, and adr_session_decision_authority."
  - "Task-Packet hardening prerequisite and its independent review gate."
acceptance_criteria:
  - "An independently reviewed implementation can establish the approved .memory-seed-pod hierarchy without treating a nested .memory-seed runtime as a pod."
  - "A pod writes and reads its own provenance ledger; roots retain only promoted summaries and explicit, pod-qualified navigation."
  - "Legacy root-owned provisional pod ledgers remain readable evidence but cannot receive writes or become implicit authority."
  - "All lifecycle, CLI, MCP, ESR, session-fuse, docs, and real-Git verification gates specified here pass on the reconstructed current-main work."
---

# Seed Pod P0 architecture reconciliation plan

## Decision and stopping point

This is a **reconstruction plan**, not a continuation of the old implementation
branches.  It makes the previously approved P0 contract executable against
current `main`, where progressive provenance has since landed with a temporary
and incompatible interpretation of pods.  The contract is authoritative:

- a governed pod is marked by `.memory-seed-pod/`, not a nested
  `.memory-seed/`;
- the pod-local runtime owns its decisions, sessions, provenance ledger, and
  provenance write authority;
- the governing root receives only deliberately promoted summaries, with exact
  pod-decision citations; and
- cross-pod source inspection is an explicit, pod-qualified evidence action,
  never an implicit root search.

The branch for this document is based directly on `main` at
`6e461a27765d811a07928f189530e01771ff08d4`.  It stops after independent plan
review.  No product code, fixture conversion, merge, push, release, or P1 work
is authorised by this plan document.

## Evidence baseline and reconciliation rule

The historical P0 checkpoint is useful evidence, not an integration source.
It and its children all share the pre-current-main base `fde49b1e`; applying
any of them wholesale would overwrite later provenance and session-fusion
work.  Keep the branches and their plans intact.

| Evidence | What to retain | Why it cannot be merged wholesale |
|---|---|---|
| `b7e623b` (`codex/feature/seed-pods`) | The approved three-role boundary, `.memory-seed-pod/pod.yaml`, root-only promotion, update transaction, and maintained demo intent. | It predates current progressive provenance and changes broad root, demo, docs, and surface files. |
| `9284ef4` (`codex/feature/seed-pods-core-governance`) | Resolver/lifecycle test ideas, promotion-source completeness checks, and transaction-recovery cases. | It is a child of the stale checkpoint and its core APIs must be reconstructed around current APIs. |
| `f6bc92c` (`codex/feature/seed-pods-fixtures-verification`) | The distinction between a maintained active pod and generated independent-root fixtures. | Its fixture paths and baseline assumptions are stale. |
| `ada4f2e` (`codex/feature/seed-pods-surfaces-diagnostics`) | CLI/MCP/situate/ESR boundary-error and parity coverage. | It conflicts with the present provenance adapter surface and runtime selector. |
| `4fb275e` (`codex/docs/seed-pods-p0`) | The explicit "checkpoint under review; P1 excluded" documentation posture. | It describes the unmerged checkpoint rather than the reconciled current-main design. |

Current `main` instead has a provisional v1 provenance runtime record:
`runtime_path`, `owner`, and a derived **root-owned**
`.memory-seed/provenance/pods/<id>.md` path.  Its tests also create a nested
`.memory-seed` as a pod.  This conflicts with the P0 boundary in two ways:
the marker has the wrong meaning and the root, rather than the pod, owns the
ledger.  The implementation must therefore reconstruct the interfaces in the
order below; it must not adapt the P0 contract to the provisional layout.

## Normative topology, ownership, and identifiers

There are exactly three runtime roles.

| Role | Physical marker and identity | Owns | Parent operation boundary |
|---|---|---|---|
| Root | `.memory-seed/`; `project.yaml.runtime.role: root`, `runtime.id: msr_<16 Crockford characters>` | Shared policy, skills, hooks, agents, bootstrap, profiles, topics, root sessions/decisions, root provenance, and root promotion summaries. | Governs its active pod descendants. |
| Governed pod | `.memory-seed-pod/pod.yaml`; `pod_id: msp_<16 Crockford characters>` | Its pod manifest, index, sessions, decisions, archive, and pod provenance ledger. | Inherits governance from the root; may not shadow or weaken it. |
| Independent root | Nested `.memory-seed/`; `runtime.role: independent-root` and its own `msr_` identity. | Its own complete runtime. | Is excluded from every enclosing-root discovery, update, audit, retrieval, and Task Packet traversal. |

The v1 pod manifest remains the minimum on-disk pod contract:

```yaml
schema: memory-seed/pod
schema_version: 1
pod_id: msp_<16 Crockford characters>
name: <non-empty display name>
root_id: msr_<governing root id>
parent_id: <governing root id or direct parent pod id>
status: active # or retired
```

The resolver derives source path and depth from canonical physical paths.  It
never serialises them as authority.  It fails closed for a malformed manifest,
duplicate id, root mismatch, parent cycle, path escape, alias/junction
ancestry, both markers at one boundary, a missing governing root, or a nested
`.memory-seed` without `runtime.role: independent-root`.  A retired pod is
still a pod and still readable; it is not an independent root.

Root-only files are `local.yaml`, `project.yaml`, `topics.yaml`, policies,
skills, hooks, agent rules, bootstrap content, retrieval profiles, and shared
configuration.  A pod may read the effective root configuration, but cannot
copy, pin, override, disable, or weaken it.  Pod-local files are precisely
`pod.yaml`, `index.md`, `sessions/`, `decisions/`, `archive/`, and the
pod-local provenance sidecar described next.

## Exact provenance contract and compatibility boundary

### V2 runtime and ledger schemas

Keep binding and replacement payloads reference-only and byte-for-byte
compatible at their existing v1 schemas.  Split the current global version
constant so that only runtime/ledger ownership changes:

| Schema | Version after P0 | Rule |
|---|---:|---|
| `memory-seed/provenance-binding` | 1 | Unchanged: Git-object, blob, range, digest, and actor references only; no code or patch text. |
| `memory-seed/provenance-replacement` | 1 | Unchanged append-by-replacement semantics. |
| `memory-seed/packet-implements-activation` | 1 | Carries the v2 runtime object but otherwise remains compatible. |
| `memory-seed/provenance-runtime` | 2 | Replaces caller-selected `runtime_path`/`sidecar_path` authority with resolved runtime identity. |
| `memory-seed/provenance-ledger` | 2 | Contains a v2 runtime and the existing binding/replacement lists. |
| `memory-seed/provenance-migration` | 1 | One append-only receipt when a legacy provisional pod ledger is explicitly adopted. |

The canonical v2 runtime event is exactly:

```json
{
  "schema": "memory-seed/provenance-runtime",
  "version": 2,
  "root_id": "msr_<16 Crockford characters>",
  "owner": {
    "kind": "root | pod | detached-pod",
    "id": "msr_<...> | msp_<...>",
    "state": "active | retired | detached"
  }
}
```

Validation rules are part of the schema: a root owner has `id == root_id` and
`state == active`; a pod owner has an active/retired manifest whose `pod_id`
and `root_id` match; a detached-pod owner has an `msp_` id and can occur only
inside the former root's retained snapshot.  There is no serialised runtime
path, sidecar path, leaf-name identity, or user-supplied ownership selector.

The resolver alone derives the paths:

```text
root active ledger:     <root>/.memory-seed/provenance/bindings.md
pod active/retired:     <pod>/.memory-seed-pod/provenance/bindings.md
detached pod snapshot:  <former-root>/.memory-seed/archive/detached-pods/<msp_id>/provenance/bindings.md
```

Only the runtime that physically owns the first two paths may append.  A
retired or detached ledger is inspectable but read-only.  Root audit discovers
metadata and validates references; it does not become an alternate write
surface for a pod ledger.

The new migration event appears after the v2 runtime event and before copied
binding/replacement events:

```json
{
  "schema": "memory-seed/provenance-migration",
  "version": 1,
  "migration_id": "mspa_<sha256>",
  "source": {
    "kind": "legacy-root-pod-ledger",
    "path": ".memory-seed/provenance/pods/<legacy-id>.md",
    "file_digest": "sha256:<64 lowercase hex>",
    "runtime": { "schema": "memory-seed/provenance-runtime", "version": 1 }
  },
  "binding_ids": ["msb_<sha256>"],
  "replacement_ids": ["msr_<sha256>"]
}
```

`migration_id` is the deterministic SHA-256 identity of every field except
itself.  The original v1 Markdown bytes remain untouched.  The subsequent
v1 binding/replacement events are normalised copies, and the receipt declares
that this local authority is reconstructed from the immutable legacy source.
It is not a new code claim and it never stores source text.

### Promotion and explicit inspection

Root decisions remain summaries.  Each numbered promoted root decision must
carry a complete `pod_sources` mapping of source decision ordinals to exact
active-pod citations:

```yaml
pod_sources:
  d1:
    - msp_<pod-id>:mse_<entry-id>:dN
```

Validation rejects an unqualified reference, a root or sibling-pod source, a
missing entry/ordinal, source/root identity mismatch, a future/postdated
source, duplicate source reuse, incomplete source coverage, and any source
from an independent root.  A retired source can remain an auditable historical
citation labelled `retired-source`; no retired or detached pod can create a
new promotion.

The public read shape is deliberately explicit:

```text
memory-seed provenance show --pod-id msp_<pod-id> <entry-id>:dN
memory-seed provenance check --pod-id msp_<pod-id>
memory_pod_inspect {"pod_id":"msp_<pod-id>", "decision_ref":"<entry-id>:dN"}
```

The MCP operation is read-only and returns the same normalised runtime,
sidecar location, decision projection, and append-only/reference verdict as
the CLI.  Root-default `provenance show`, root search, ESR, and Task Packet
compilation do **not** traverse pod sessions or provenance.  `--pod-id` is
required for a pod decision; `--runtime-file` is removed from mutating paths
and, during compatibility, accepted only by a labelled legacy read adapter.

### Legacy migration and refusal behaviour

There are no committed provenance sidecars on the current-main baseline, but
P0 must be safe for repositories that used the provisional feature.

1. Detect a v1 record with a root-owned
   `.memory-seed/provenance/pods/<id>.md` path as `legacy-provisional`.  It is
   readable only through an explicit compatibility/read result and is never an
   active pod authority.
2. Do not auto-migrate and do not change the legacy file.  Default bind,
   promotion, activation, and update refuse with `legacy-provisional-owner`.
3. An explicit `provenance migrate-pod --pod-id <msp> --from-legacy ...`
   requires a dry-run receipt first.  It validates one active physical pod,
   exact root identity, no existing v2 pod ledger, the source digest, unique
   bindings/replacements, and no cross-root records.  The applied form creates
   only the new pod-local v2 sidecar and migration receipt.
4. Repeating the same completed migration is idempotently reported; differing
   source digest, a pre-existing v2 ledger, duplicate identities, or a
   root/pod state mismatch fails without writes.  An in-place rewrite, rename,
   deletion, or silent movement of the v1 file is never a migration mode.
5. V1 `--runtime-file` records remain available only to `show/check` as
   `compatibility: legacy-provisional`; they cannot select an append target.
   Newly compiled packet activations and all v2 CLI/MCP mutation requests use
   physical resolution only.

## Staged reconstruction and exclusive file ownership

Work begins only after the Task-Packet prerequisite and this plan have passed
independent review.  The stages use fresh worktrees from the then-current
integration base.  No stage cherry-picks an old P0 branch; an implementation
packet may cite its reports and tests as evidence.

| Stage | Depends on | Single owning track and files | Deliverable / hand-off gate |
|---|---|---|---|
| 0. Baseline | Review approval | Integration owner: packet, branch/base receipt, stale-branch evidence table, current tests. | Freeze the exact base; run the baseline matrix; confirm no untracked user artifact is in scope. |
| 1. Boundary core | 0 | **Core:** `memory_seed/core.py`, runtime discovery/lifecycle helpers, `memory_seed/situate.py`, root/pod seed/update plumbing, `tests/test_seed_pod_core.py`, focused core fixtures. | One typed physical resolver and v1 manifest validation; all callers consume it or remain unchanged. |
| 2. Provenance ownership | 1 | **Provenance:** `memory_seed/provenance.py`, `memory_seed/provenance_git.py` only if its adapter needs the resolved owner, `tests/test_provenance.py`, `tests/test_provenance_engine.py`. | V2 runtime/ledger/migration validation is pure and has no CLI/MCP filesystem policy. |
| 3. Public surfaces | 1 and 2 | **Surfaces:** `memory_seed/cli.py`, `memory_seed/mcp_server.py`, `memory_seed/esr.py`, adapter-specific tests including `tests/test_provenance_surfaces.py` and `tests/test_seed_pod_surfaces.py`. | Every write flows through the resolver and shared planner; CLI/MCP/ESR contract is identical. |
| 4. Lifecycle, maintained fixture, and docs | 1–3 interface freeze | **Fixtures/docs:** `demo/.memory-seed-pod/`, generated fixture definitions, `tests/test_seed_pod_fixtures.py`, root docs/spec/audit/index entries. | Demo is an active pod, standalone generated runtimes are explicit independent roots, and docs state only verified delivered behaviour. |
| 5. Integration evidence | 1–4 accepted individually | **Integration owner only:** session-fuse previews, review receipts, final current-main verification, and worktree cleanup receipts. | Serial integration after each gate; no P1 retrieval, release, or publishing. |

No two tracks edit the same production file.  If an API change crosses a
track, the producing track first commits the documented interface and test;
the consumer rebases its **new** worktree on that accepted integration base.
The integration owner alone updates shared current-state documentation and
fuses branch-local sessions.  Historical P0 reports and plans are retained in
place; a current document can link to them as evidence but must not reclassify
them as shipped.

## Session-fuse strategy and performance guard

Each implementation track appends only its own branch-local session entry
through the sanctioned writer.  The entry names the exact active base, files,
test results, reconstruction provenance, and any `Memory-Implements:`
decision references.  Pod-local work logs inside the pod; root entries record
only promotion summaries, lifecycle decisions, and integration evidence.
There is no raw concatenation of pod session files into the root.

Before every integration, the integration owner runs the session-fuse preview
against the actual base and source branch, then reviews the changed paths,
entry/sidecar parents, chronology, `Memory-Entry` trailers, and fuse report.
Only an accepted preview can use the project-configured local merge path.  A
failed, ambiguous, or stale preview stops integration; it is not repaired by
editing branch attribution or copying an entry.  The current transitive-fuse
P0 gate remains independent and must not be bypassed.

Performance is a correctness guard here: root inspection must not become an
implicit federation scan.  The reconstructed resolver creates one immutable
topology snapshot per command, canonicalises each path once, and performs at
most one pruned descendant walk.  It prunes `.git`, root/pod memory
directories after recording their boundary, and every independent-root tree.
Root default provenance operations inspect root data only; an explicit
`--pod-id` opens at most that selected pod's session and ledger.  Promotion
audit may inspect cited pods, but resolves each distinct pod once.

The append-only fast path compares the working ledger with its `HEAD` prefix;
full history scanning is opt-in (`provenance check --history`) and batches
tracked sidecar discovery rather than issuing a Git history walk per binding.
Tests must instrument directory traversal and Git invocations to prove those
properties, rather than rely on a timing threshold:

- a root-default show/check opens zero pod sessions and zero pod ledgers;
- a `--pod-id` show/check opens one selected pod only;
- a 100-pod fixture performs one topology walk, not one per decision or
  sidecar; and
- session-fuse preview reads only the changed session/sidecar paths in its
  bounded branch window and never discovers pods as a side effect.

## Acceptance observables and negative matrix

The following are release-blocking P0 observables, not aspirational examples.

| Area | Positive observable | Required refusals / negative cases |
|---|---|---|
| Boundary resolver | A root, nested active pod, nested pod, retired pod, and independent root resolve to their declared roles with derived path/depth and governing ids. | Unmarked nested `.memory-seed`; duplicate IDs; malformed manifest; wrong root/parent; cycle; junction/alias escape; missing root; and both markers at one path fail with a stable boundary reason. |
| Ownership | Root bind writes only its root ledger; pod bind from the pod writes only `.memory-seed-pod/provenance/bindings.md`; a root decision contains a valid promoted summary/citation only. | Root-side `provenance/pods/*.md` cannot be an active pod ledger; arbitrary `runtime_path`, leaf-name ids, `--runtime-file` writes, sibling/parent writes, code/patch payloads, and unqualified pod refs are rejected. |
| Lifecycle | Init classifies root/pod/explicit independent root; root-only update preflights, journals, recovers, and preserves active pod histories; retirement leaves a readable tombstone. | Pod-local update, retired/detached append or promotion, retirement with active descendants, update crossing an independent root, failure after any journal stage, and dry-run/write divergence refuse or recover exactly. |
| Promotion | An active descendant promotes a root summary whose every numbered decision has valid `pod_sources`; root search returns only the summary. | Missing ordinal, non-existent source, sibling/independent source, duplicate use, postdated source, wrong root, incomplete mapping, and implicit root search for source text fail. |
| Provenance | V2 runtime/ledger normalisation, reference-only bindings, local projection, append-only check, migration receipt, and binding verification produce matching CLI/MCP results. | Tampered/reordered event, cross-runtime ledger, mismatched sidecar, v1 write, code-bearing payload, unavailable Git classification, source digest mismatch, duplicate migration, and an in-place legacy rewrite fail without a write. |
| Explicit inspection | The named pod decision is readable through the CLI and MCP and returns its physical owner and labelled state. | Missing `--pod-id`, different-pod id/decision mismatch, retired write attempt, detached active lookup, and root default traversal into a pod fail or return no pod data as specified. |
| Session and diagnostics | Situate, doctor, ESR, Task Packet, CLI, and MCP expose the same boundary/provenance reason codes without crashing. | A malformed boundary and an unavailable Git repository return structured diagnostics; no surface falls back to the old implicit nested-runtime interpretation. |

Use real temporary Git repositories for every append-only, migration, and
session-fuse case.  Tests must assert both zero-write dry-run results and the
subsequent applied result, then inspect the exact touched paths.  CLI/MCP
parity means equal normalised payload/reason code and equivalent mutation
outcome, not merely both returning a non-error response.

## Review gates and full verification matrix

| Gate | Independent reviewer must inspect | Evidence required before proceeding |
|---|---|---|
| G0 — plan | This document, authority sources, stale-branch comparison, scope, and non-goals. | Approval to start reconstructed P0 work; this branch stops here. |
| G1 — boundary/schema | Resolver API, v2 schemas, migration semantics, ownership table, and compatibility refusals. | Focused core/provenance tests plus a written interface-freeze receipt. |
| G2 — surface/lifecycle | CLI/MCP shared planner, update transaction, diagnostics, explicit inspection, and fixture conversion. | Real-Git positive/negative matrix and dry-run/write parity evidence. |
| G3 — integration | Changed-path ownership, session-fuse preview, sidecar parents, no P1 expansion, and docs truthfulness. | Current-main rebase, clean fuse preview, full verification matrix, and diff review. |
| G4 — closure | Final review of implementation evidence and cleanup boundaries. | Explicit user integration/release direction; neither is implied by this plan. |

For the future implementation, run the focused suites at each track hand-off,
then on the reconstructed integration candidate run:

```powershell
python -B -X utf8 -m pytest -q tests/test_seed_pod_core.py tests/test_seed_pod_fixtures.py tests/test_seed_pod_surfaces.py tests/test_provenance.py tests/test_provenance_engine.py tests/test_provenance_surfaces.py
python -B -X utf8 -m pytest -q
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" docs check
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" docs index --check
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" links check
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" topics check
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" esr --json
git diff --check
```

Run seed/live parity and the relevant maintained demo checks after fixture
conversion.  Any existing baseline warning must be reported separately from a
new P0 regression; it is never hidden by weakening a check.

## Worktree and artifact cleanup protocol

All planning and future implementation writes use agent-owned worktrees in the
configured namespace, created from the recorded current integration base.
Before creating one, record its absolute path, branch, base SHA, and a clean
`worktree guard --write-intent` result.  Never write in the primary checkout.
In particular, its protected untracked 2026-09-03 session, link sidecar, and
decision-replay run directory are outside this plan and must remain untouched.

At a completed or abandoned track: save its test and fuse receipts in its
branch session entry; confirm `git status --short`; remove only generated,
ignored artifacts owned by that worktree; then use `git worktree remove` only
after its branch is either deliberately retained for review or its owner has
explicitly authorised removal.  Do not delete the historical P0 worktrees or
branches.  The present planning worktree remains available for G0 independent
review; it is not cleaned up merely because this document is committed.

## Next action

Obtain an independent G0 review.  On approval, compile fresh Task Packets from
the reviewed contract and begin Stage 0 only.  Do not resume an old Seed Pod
branch, integrate it, or start P1 federated retrieval.
