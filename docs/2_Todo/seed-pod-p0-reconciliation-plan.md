---
title: "Seed Pod P0 architecture reconciliation plan"
date: "2026-09-07"
project: "memory-seed"
status: "active"
priority: "P0"
blocked_by: "G0 independent re-review approval and stabilized Reflection Ledger v2/retirement foundation"
next_action: "Independently re-review this v2-aligned P0 plan; record G0 approval and verify the reflection retirement/governance prerequisites before compiling implementation Task Packets."
source:
  - "Approved Seed Pod P0 contract recorded on historical branch b7e623b"
  - "docs/2_Todo/task-packet-hardening-progressive-provenance-plan.md"
  - "docs/2_Todo/reflection-ledger-workstream-evolution-plan.md"
  - "docs/2_Todo/reflection-v1-authoring-retirement-plan.md"
  - "docs/CONSTITUTION.md"
scope: "Reconstruct Seed Pod P0 on current main: governed .memory-seed-pod boundaries, pod-owned provenance, selected-pod Task Packets, root-only P0 reflections, root promotion summaries, explicit inspection, receipted lifecycle transactions, qualified session fusion, migration compatibility, and verification."
non_goals:
  - "Do not merge, rebase, cherry-pick, delete, or otherwise alter b7e623b, 9284ef4, f6bc92c, ada4f2e, or 4fb275e."
  - "Do not implement, merge, push, release, or begin P1 federated retrieval in this planning change."
  - "Do not rewrite, delete, or silently relocate historical session or provenance records."
dependencies:
  - "Ratified Constitution v1.12: append-only, evidence-first, and identical write-surface invariants."
  - "adr_subproject_scoping, adr_branch_session_fuse, adr_worktree_convention, and adr_session_decision_authority."
  - "Task-Packet hardening prerequisite and its independent review gate."
  - "Merged Reflection Ledger v2 core; reviewed v2 surfaces/packet guards and v1 retirement, including explicit ratification of its v1 expiry transition."
acceptance_criteria:
  - "An independently reviewed implementation can establish the approved .memory-seed-pod hierarchy without treating a nested .memory-seed runtime as a pod."
  - "A pod writes and reads its own provenance ledger; roots retain only promoted summaries and explicit, pod-qualified navigation."
  - "Selected-pod Task Packets carry the exact pod identity and inherited root worker governance, while root-default compilation performs zero pod traversal."
  - "P0 reflection state uses one sequential v2 ledger per root workstream; pod-originated writes fail with pod-reflection-not-supported-p0 and historical v1 remains read-only."
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

The previous revision incorporated the independent review's missing cross-cutting
contracts: selected-pod Task Packets are supported rather than refused, P0
reflection remains root-only, all fusable pod records are classified and
receipted, and adoption replaces destructive fixture conversion.  These are
constraints on future implementation, not permission to begin it. This revision
aligns reflection with the merged v2 core and the v1 retirement plan while
preserving those P0 constraints. G0 approval is still missing.

The branch for this document is based directly on `main` at
`12186feb062c70fe1f88df357c4c02698be76ae0`. This baseline contains the v2
core and the retirement planning document; it does not establish that v1
retirement, its public surfaces, or its constitutional transition have shipped.
The [retirement plan](reflection-v1-authoring-retirement-plan.md) retains its
focused re-review and explicit maintainer-ratification gates. Seed Pod P0
must consume that stabilized foundation; it must not implement retirement or
infer ratification itself. This branch stops for independent re-review.
No product code, fixture adoption, merge, push, release, or P1 work
is authorised by this plan document.

## Evidence baseline and reconciliation rule

The historical P0 checkpoint is useful evidence, not an integration source.
It and its children all share the pre-current-main base `fde49b1e`; applying
any of them wholesale would overwrite later provenance and session-fusion
work.  Keep the branches and their plans intact.

| Historical branch and head | Audited commits / extent | Reconciliation disposition |
|---|---|---|
| `codex/feature/seed-pods` — `b7e623b` | `fde49b1e..b7e623b`: 45 paths outside `.memory-seed/sessions/**`; +1501/-4662. | Preserve contract and test ideas only: three-role boundary, pod marker, root promotion, and maintained demo intent. Reconstruct current APIs; no wholesale import. |
| `codex/feature/seed-pods-core-governance` — `9284ef4` | `c636cc26`, `9284ef48` | Port validation scenarios only after the resolver interface freezes; rewrite lifecycle transactions against the receipted contract below. |
| `codex/feature/seed-pods-fixtures-verification` — `f6bc92c` | `1e7a455d`, `9fad83ce`, `f6bc92c0` | Retain active-demo and independent-fixture assertions after receipted adoption; do not replay old conversion edits. |
| `codex/feature/seed-pods-surfaces-diagnostics` — `ada4f2e` | `fda35161`, `12ee790e`, `ff5c7aa9`, `ada4f2e3` | Retain parity and error scenarios; rebuild adapters around the frozen current resolver and provenance contracts. |
| `codex/docs/seed-pods-p0` — `4fb275e` | `6f8b3d7f`, `2a91370a`, `4fb275ef` | Historical checkpoint evidence only; rewrite current delivery documentation from verified results. |

The checkpoint count is not the full current-main difference. With the same
root-session exclusion, `12186feb..b7e623b` differs in 112 files, +1582/-22689.
Use the recorded commit range when interpreting the audit; later main work
accounts for the broader comparison. Reproduce both measurements with:

```powershell
git diff --shortstat fde49b1e b7e623b -- . ':(exclude).memory-seed/sessions'
git diff --shortstat 12186feb b7e623b -- . ':(exclude).memory-seed/sessions'
```

The read-only audit identified seven historical session entries absent from
this main baseline:

| Historical owner | Entry IDs |
|---|---|
| Parent | `mse_zwbmhqv9mvgvcnt1`, `mse_z29mmqx2tgbn3wvr`, `mse_ynyx8kn8wx8stfvm` |
| Core | `mse_qqypknpb1v69p852` |
| Fixtures | `mse_3f0kk38nczh22246` |
| Surfaces | `mse_5g8cwehd1m7ppceg` |
| Docs | `mse_12hwx5246h8sxgvd` |

The child branches repeat the parent's three entries. These IDs are evidence
locators, not live lifecycle references or an import manifest. Any separately
authorized historical import must deduplicate by entry ID, preserve original
branch/author attribution and bytes, and pass canonical session-fuse review.
This plan update authorizes neither import nor cherry-picking. Future workers
must remeasure the named commits against their recorded base before reusing a
scenario; a matching filename does not establish compatibility.

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

### Discovery scope and identity initialization

P0 discovery is never a repository-wide marker scan.  Starting from a caller
path, the resolver walks physical ancestors only; an explicit `--pod-id` is
resolved against one governing root's measured active-pod index.  The index
may be built once for an explicit pod/lifecycle/fuse operation, but the
following trees are categorically excluded from root pod discovery:

```text
.git/
memory_seed/seed/
tests/
tests/fixtures/
```

That exclusion prevents shipped seed templates and test fixtures from becoming
live descendants merely because they contain a marker.  A maintained `demo/`
pod is not excluded, but is visible only when the owning root explicitly runs
a pod operation; it is never reached by ordinary root retrieval, Task Packet
compilation, ESR, or link checking.  Unit tests create runtime trees outside
these repository paths rather than weakening this rule.

Current roots that lack `project.yaml.runtime.id` are not silently assigned an
identity during a read.  The root-only, dry-run-first command is
`memory-seed pods root-id init`.  It writes exactly
`runtime: {role: root, id: msr_<16 Crockford characters>}` through a journaled
transaction and emits a `root-identity-init` receipt containing the root's
physical path, pre/post `project.yaml` SHA-256, generated id, base Git SHA,
and transaction id.  Existing root sessions, decisions, and provenance bytes
are inventory-only inputs and remain unchanged.  Until that receipt exists,
P0 pod creation, promotion, detachment, selected-pod compilation, and
provenance migration refuse with `root-identity-uninitialized`; unrelated
pre-P0 root commands retain their current behaviour.

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

### Mixed-version grammar is a hard boundary

The parser selects one grammar from the first runtime event and never infers a
hybrid ledger.  A v1 runtime event permits only the existing v1 ledger grammar
(`runtime_path`, `owner`, and `sidecar_path`) and is classified as
`legacy-provisional` when it names a pod.  It is readable through explicit
compatibility `show/check` only.  A v2 runtime event requires a v2 ledger and
the identity-derived sidecar path in this plan.  A v1 event followed by a v2
ledger/migration event, a v2 event carrying v1 path fields, a missing initial
runtime event, an event reorder, or an undeclared version is
`mixed-provenance-version` and refuses before projection or append.

The only bridge is a newly created v2 pod-local ledger: its first event is the
v2 runtime, its second is the exact v1-source migration receipt above, and
its later binding/replacement events are normalised copies.  The receipt must
name the legacy ledger's canonical root-relative path, full file digest,
normalised v1 runtime payload, sorted binding/replacement ids, and the
generated v2 owner identity.  It does not alter the v1 file or grant the v1
file an active status.  A root v1 sidecar receives the analogous one-time
root-v2 migration only after the receipted root identity initialization; P0
never invents an `msr_` id while parsing a ledger.

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
3. An explicit `provenance migrate-pod --legacy-id <legacy-id>` requires a
   dry-run receipt first and has a deliberately narrow caller boundary: the
   current physical directory must resolve to the active target
   `.memory-seed-pod`, whose manifest supplies the only accepted `msp_` id.
   A root caller, a sibling caller, `--pod-id`, an arbitrary source path, and
   a detached/retired caller all refuse.  The command derives (rather than
   accepts) `<root>/.memory-seed/provenance/pods/<legacy-id>.md`; it validates
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

The focused negative suite includes: a v1/v2 grammar splice; a forged v2
runtime path field; identity initialization retry/collision/tamper; no root
identity; root/sibling/detached `migrate-pod` caller; path traversal in
`legacy-id`; a mismatched manifest/root id; an unchanged legacy-file digest
after both dry run and application; and an activation whose runtime does not
equal the packet's measured selected root or pod.

## Cross-cutting Task Packet and reflection contract

### Selected-pod Task Packets are supported

P0 extends the measured runtime binding with one optional, canonical target;
absence remains the backwards-compatible root target:

```json
"target_runtime":
  {"kind": "root", "root_id": "msr_<...>"}
  | {"kind": "pod", "root_id": "msr_<...>", "pod_id": "msp_<...>"}
```

The compiler must measure the target rather than trust this object.  A root
target requires the initialized measured root id.  A pod target requires an
explicit `pod_id`, one active governed pod in that root's measured index, a
manifest/root-id match, and a canonical physical pod path below the root.
The packet serializes the measured `target_runtime`, `root_id`, `pod_id` when
applicable, derived pod-relative path, and the root Git worktree/binding; it
does not serialize a caller-selected sidecar or reclassify an independent
root.  `task-packet preview|compile --pod-id <msp>` and MCP
`memory_task_packet_preview|compile` with the same binding target return the
same canonical packet or the same structured refusal.

Root-default compilation is a performance and authority invariant: with no
pod target it invokes neither `discover_pods` nor pod session/decision/index
readers, even if malformed or valid pod markers exist below the root.  The
selected-pod path resolves that one pod once and reads only its local corpus
and explicitly supplied evidence.  It does not retrieve sibling pods,
descendants, detached snapshots, independent roots, templates, or fixtures.

Every selected-pod worker packet materializes the **governing root's** full
`.memory-seed/agent-rules.md`.  If the packet delegates a session write or a
worker checkpoint, it also materializes the governing root's full
`.memory-seed/skills/session_logging.md`.  A pod never copies either document
and cannot substitute a local baseline.  The packet's input ledger records
both root-source digests/token counts and the measured pod identity, so a
reviewer can distinguish inherited governance from pod-local decision
evidence.

Session-write admission is exact, not a permissive prefix or glob.  For a
root target, the existing root session target grammar remains unchanged.  For
a pod target, the only admitted `execution.allowed_files` and
`memory_checkpoints.session_paths` values are the resolver-derived forms:

```text
<pod-relative>/.memory-seed-pod/sessions/YYYY-MM/YYYY-MM-DD.md
<pod-relative>/.memory-seed-pod/sessions/YYYY-MM/YYYY-MM-DD/<user>.md
```

The date/user values must pass the existing session target validators; the
path must have exactly the selected pod prefix after canonical slash/case
normalisation; it must be named once in both fields; and
`branch_local_only: true` plus `guarded_append: true` remain mandatory.  Root
session paths in a selected-pod packet, a selected-pod path in a root packet,
a sibling/descendant path, a template/fixture path, a wildcard, a Windows
alias, direct Markdown write instructions, and an explicit timestamp override
all refuse.  The packet directs the worker to the shared sanctioned append
surface, whose P0 adapter resolves the current pod before writing.

Activation preserves this target exactly.  `activate_task_packet` remeasures
the root worktree, target root/pod identity, current active state, and allowed
file identities; then the provenance activation is checked against the target
runtime's v2 ledger.  A pod activation cannot stamp a root decision or bind a
root ledger, and a root activation cannot consume a pod decision.  The local
Git activation artifact and its history retain the packet fingerprint,
measured target identity, and normal `Memory-Implements:` receipt; they never
copy session or source code text.

P0 makes that activation contract public on both surfaces rather than leaving
a selected pod with an undocumented Python-only path: CLI
`task-packet activate --packet-file ... --apply` and MCP
`memory_task_packet_activate {packet, apply: true}` share the same measured
activation planner.  Without `--apply`/`apply: true`, both return the exact
would-activate receipt and write no Git-local artifact.  With application,
both run the worktree guard and shared remeasurement, then return the same
canonical activation receipt or stable refusal code.  They do not dispatch a
worker, create a worktree, export a packet, or bypass the existing
`Memory-Implements:` hook contract.

Required focused coverage is in `tests/test_task_packet.py` and
`tests/test_task_packet_surfaces.py`: root default does zero discovery/read
into pods; selected active pod has the inherited root baselines and one exact
admitted path; missing/retired/detached/sibling/independent/template/fixture
targets refuse; packet token accounting includes inherited baseline material;
activation detects root/pod identity drift; and CLI/MCP preview, compile, and
activation return byte-equal canonical packets/receipts or matching reason
codes, including dry-run/no-artifact and apply/artifact cases.  The
existing Task Packet v1 fixture remains a root fixture; a separate temporary
real-Git pod fixture proves the selected path without making repository test
fixtures discoverable.

### P0 reflection is root-only

Each root workstream uses exactly one v2 ledger at
`.memory-seed/reflections/active/<workstream_id>/ledger.md`. Planner,
implementer, reviewer, and orchestrator append sequentially to that ledger
under its existing per-chain role/phase and branch-ownership rules. Parallel
root workstreams use separate ledgers; combined inspection is derived and
read-only. No root reflection operation discovers pod memory, and P0 creates
no `.memory-seed-pod/reflections/` authority.

Reuse the merged v2 core's trusted Git-history admission, expected tip/blob/
digest/history checks, ledger-only append commit transaction, explicit rebind,
durable session receipts, closure, and proof-checked expiry. P0 adds only the
physical root/pod boundary checks; it must not weaken those guards or introduce
a second persistence mechanism. Normal session fusion remains distinct from
reflection integration: it never fuses participant fragments or merges two
workstream ledgers into one authority.

Before planning or applying any v2 reflection mutation (init, append, close,
expire, or rebind), its shared planner must reject a caller resolved inside a
pod, a pod target selector, or a pod-local reflection path with
`pod-reflection-not-supported-p0`. CLI, MCP, Task Packet compile/activation,
and activation-artifact readers must preserve that same refusal. Resolve the
physical caller before normalizing a request to its governing root; a pod
caller cannot gain a root writer by naming the root ledger. Refusal precedes
ledger, session, Git ref/index, config, cache, or artifact writes. This is a
stable P0 boundary; later pod reflection authority requires its own governing
decision and independent review.

A selected-pod packet may cite explicitly supplied root reflection evidence,
but cannot carry a reflection write capability or authorize a root ledger
path. Generic Task Packet schema v1 is unrelated to reflection format v1 and
must remain valid. Root reflection-writing packets use the retirement plan's
exact v2 capability/scope validator through compile, activation, and artifact
loading; P0 adds the measured runtime check to that shared admission path.

New work has no v1 manifest, reservation, fragment authoring, fuse, closeout,
or expiry path. Historical v1 remains explicit read-only inspection and
verification, with its IDs, bytes, receipts, and attribution preserved.
After the retirement foundation lands, root-originated legacy mutation
requests retain `legacy-reflection-read-only` (or the documented removed-
command error), while pod-originated writes use the P0 code above. Historical
v1 carry-through uses the retirement plan's destination-resident exact-tree
integration preflight; it is not permission to import absent v1 records.

The **Packet/reflection track** exclusively owns `memory_seed/task_packet.py`,
`memory_seed/reflection_ledger.py`, `tests/test_task_packet.py`,
`tests/test_task_packet_surfaces.py`, `tests/test_reflection_ledger.py`, and
`tests/test_reflection_workstream_ledger.py`. It adds root-only caller/target
checks, no-discovery spies, real-Git admission probes, and receipt-preservation
tests. Keep v2 trusted-history, stale-write, role/phase, rebind, closure,
expiry, and two-workstream isolation tests green; retain only historical v1
read/verify and mutation-refusal assertions, not obsolete v1 write successes.
The **Fuse/transaction track** is the
sole owner of `.gitattributes`: it preserves the existing root reflection
`-merge` rule and adds the pod memory `-merge` rules below.  No other track
edits that file.

## Receipted adoption and detachment transactions

The maintained demo and any legacy nested runtime are converted only through
the same explicit adoption transaction; there is no `rm`, hand move, or
destructive fixture rewrite in P0.  `memory-seed pods adopt --path <relative
candidate>` is root-only and dry-run-first.  It refuses an independent root,
a path outside the root, both markers at one boundary, a malformed legacy
runtime, a duplicate pod id, or any uninitialised root identity.

The dry-run result is a deterministic adoption plan and receipt containing:
the root/pod ids, canonical source and destination paths, base SHA, sorted
inventory of every moved local-history file (relative path, regular-file mode,
SHA-256, byte length), session entry ids, decision ids, archive paths, and a
transaction id.  Application writes a root transaction journal before any
move, copies each inventory item to the staged `.memory-seed-pod` layout,
creates `pod.yaml`, verifies every hash/mode and parsed session/decision id,
then archives the legacy `.memory-seed` tree under the governing root's
adoption archive with its original inventory.  Only after that verification
does it publish the active pod marker and a completed adoption receipt.

Every intermediate journal state is recoverable.  `pods recover --transaction
<id>` either restores the exact source tree from verified staged/archive bytes
and removes only transaction-created paths, or refuses `recovery-diverged`
without overwriting an unexpected byte.  A failed move leaves the journal and
both inventories for review; it never reports a half-adopted pod as active.
Post-transaction proof reruns physical resolution, verifies the new active
pod's local sessions/decisions hashes and ids against the receipt, checks the
archived legacy inventory, and confirms no unmarked nested `.memory-seed`
boundary remains.  The demo conversion test must exercise dry run, apply,
failure injection/recovery, and this proof.

`memory-seed pods detach --pod-id <msp>` is similarly root-only and
dry-run-first.  P0 limits it to a leaf active pod; a pod with active
descendants refuses rather than guessing subtree ownership.  Its journal
invents a new independent-root `msr_` only through the root-identity procedure,
copies/validates the pod local inventory into a staged independent
`.memory-seed` runtime, and writes the former root's immutable detached-pod
snapshot at the derived archive path.  The detachment receipt records former
root/pod/new-root identities, source/destination inventories and hashes,
snapshot digest, base SHA, and recovery state.  It publishes the independent
root and removes the pod marker only after all proofs pass.  Recovery follows
the same non-overwriting rule; root citations thereafter resolve only through
the retained snapshot and the former pod remains non-writable.

## Staged reconstruction and exclusive file ownership

Work begins only after the Task-Packet prerequisite, the stabilized reflection
foundation (including retirement governance), and this plan's G0 re-review
have passed. The stages use fresh worktrees from the then-current
integration base.  No stage cherry-picks an old P0 branch; an implementation
packet may cite its reports and tests as evidence.

| Stage | Depends on | Exclusive owner and files | Deliverable / hand-off gate |
|---|---|---|---|
| 0. Baseline | G0 approval and prerequisite receipts | **Integration owner:** fresh packet, branch/base receipt, stale-branch evidence table, baseline tests. | Freeze the exact base and reflection API/test inventory; verify retirement and ratification receipts, protected primary-checkout exclusions, and root-default zero pod discovery. |
| 1. Boundary/lifecycle core | 0 | **Core/fuse owner:** all `memory_seed/core.py` P0 edits, `memory_seed/situate.py`, `tests/test_seed_pod_core.py`, `tests/test_project_lifecycle.py`, and core temporary-Git helpers. | Typed physical resolver, root-id initialization, discovery exclusions, adoption/detachment/update journals, and the interface consumed by every later track. No other track edits `core.py`. |
| 2. Provenance ownership | 1 | **Provenance owner:** `memory_seed/provenance.py`, `memory_seed/provenance_git.py` only where required, `tests/test_provenance.py`, `tests/test_provenance_engine.py`, `tests/test_provenance_surfaces.py`. | V1/v2 grammar split, root identity dependency, target-owned activation, migration receipt, and physical-caller checks are pure before adapters consume them. |
| 3. Packet/reflection | 1; target-runtime and reflection interfaces frozen | **Packet/reflection owner:** `memory_seed/task_packet.py`, `memory_seed/reflection_ledger.py`, `tests/test_task_packet.py`, `tests/test_task_packet_surfaces.py`, `tests/test_reflection_ledger.py`, `tests/test_reflection_workstream_ledger.py`. | Selected-pod compile/activation and inherited governance work; root-default zero traversal, root-only v2 reflection, historical v1 read-only behavior, and pod-write refusal are real-Git proven. |
| 4. Fuse/transaction integration | 1; classifier interface frozen | **Core/fuse owner:** remaining `memory_seed/core.py` fuse changes, `tests/test_session_fuse_and_merge.py`, `tests/test_seed_pod_surfaces.py`, and **only this track** edits `.gitattributes`. | Root/pod record classification, reset/stage/render proof, `-merge` protection, qualified receipts, and adoption/detachment recovery probes pass. |
| 5. Public adapters | 2–4 | **Surfaces owner:** `memory_seed/cli.py`, `memory_seed/mcp_server.py`, `memory_seed/esr.py`, `tests/test_mcp_read_parity.py`, `tests/test_mcp_session_append.py`, and adapter portions of `tests/test_seed_pod_surfaces.py`. | CLI/MCP/ESR are thin, shared-planner adapters with equivalent result shapes and refusal codes. |
| 6. Maintained demo and docs | 1–5 interface freeze | **Fixtures/docs owner:** `demo/`, generated fixture definitions, `tests/test_seed_pod_fixtures.py`, docs/spec/audit/index entries. | Demo adopts through a receipted transaction; generated standalone runtimes remain explicit independent roots; docs state only verified delivery. |
| 7. Integration evidence | 1–6 accepted individually | **Integration owner only:** session-fuse previews, receipt review, final current-main verification, and worktree cleanup receipts. | Serial integration after each gate; no P1 retrieval, release, or publishing. |

No two tracks edit the same production file.  The Core/fuse owner keeps the
otherwise shared `core.py` serial, and the `.gitattributes` owner is singular.
If an API change crosses a track, the producing track first commits the
documented interface and test; the consumer rebases its **new** worktree on
that accepted integration base.  The integration owner alone updates shared
current-state documentation and fuses branch-local sessions.  Historical P0
reports and plans are retained in place; a current document can link to them
as evidence but must not reclassify them as shipped.

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

### Qualified record classification, reset, staging, and receipts

The fuse extends its current root-only classifier to one measured record
identity, never a loose nested path:

```text
<runtime-id>::session::<entry-id>
<runtime-id>::decision::<decision-id>
<runtime-id>::link::<entry-id>::<timestamp>
<runtime-id>::topic::<entry-id>::<timestamp>
<runtime-id>::diagram::<entry-id>::<timestamp>
```

`runtime-id` is the initialized `msr_` root id or the measured `msp_` pod id.
The accepted root locations remain `.memory-seed/sessions/**` and
`.memory-seed/decisions/**`.  A pod location is accepted only when a changed
path resolves to its measured active pod and is one of:

```text
<pod-relative>/.memory-seed-pod/sessions/**
<pod-relative>/.memory-seed-pod/decisions/**
<pod-relative>/.memory-seed-pod/sessions/links/**
<pod-relative>/.memory-seed-pod/sessions/topics/**
<pod-relative>/.memory-seed-pod/sessions/diagrams/**
```

The existing date, block, decision-ordinal, sidecar-parent, chronology, and
append-only validators apply inside that selected runtime.  A root and pod may
not silently collide on a bare entry id: a duplicate raw `mse_` id across
qualified records is a fuse refusal until a supported repair establishes the
historical identity.  This retains the existing `Memory-Entry: <mse_...>`
commit-trailer grammar.  The fuse receipt, rather than a rewritten trailer,
carries the qualified runtime id, original source path, source commit, record
id, rendered target path, and already-present disposition.  Thus every normal
trailer remains byte-compatible while a later auditor can prove which pod
record was carried.

The source-path probe is bounded and has no discovery side effect.  It obtains
only the three-dot changed paths, classifies root paths directly, and for a
candidate pod path ascends that path to one `.memory-seed-pod/pod.yaml`, then
validates it against the governing root.  It does not call broad pod discovery,
walk unrelated directories, parse an unchanged pod, or traverse templates,
fixtures, independent roots, or detached archives.  An unrecognised changed
`.memory-seed`/`.memory-seed-pod` path is a refusal, not a path the merge
resets or ignores.

Before applying an approved plan, `session merge-branch` resets every changed,
recognised root or pod session/decision/link/topic/diagram path that exists on
base to its base blob.  It then renders only the qualified planned records and
stages the exact returned path set, including pod decisions and all sidecars.
It verifies staged blob ids against the render plan before committing; a
missing path, an unclassified conflict, an unexpected staged path, a changed
pre-existing record, or a receipt mismatch aborts the merge rather than
dropping work.  The merge commit retains the normal trailer for every imported
entry plus the fused qualified receipt set in the integration result.

The Fuse/transaction owner changes `.gitattributes` in the same first core
fuse change, adding these protections alongside the existing root rules:

```gitattributes
.memory-seed/decisions/** -merge
**/.memory-seed-pod/sessions/** -merge
**/.memory-seed-pod/decisions/** -merge
```

The existing `.memory-seed/reflections/active/** -merge` remains root-only.
The dedicated focused suite must use bounded real-Git probes for: root and pod
same-day additions; every pod sidecar family; an unchanged malformed sibling
pod proving no discovery; an independent-root and fixture/template marker
proving exclusion; duplicate raw entry id; changed existing record; sidecar
whose parent is absent or cross-pod; `-merge` conflict/reset/application;
staged-blob and qualified-receipt preservation; and fail/abort/no-write
behaviour.  These tests belong in `tests/test_session_fuse_and_merge.py`,
`tests/test_seed_pod_core.py`, and `tests/test_seed_pod_surfaces.py`; they do
not broaden the ordinary retrieval test corpus.

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
| Adoption and detachment | A dry-run receipt inventories/hash-locks the source; apply, recovery, and post-resolver proof preserve every local-history byte and archive/snapshot evidence. | Hand conversion, an independent-root adoption, marker collision, inventory/hash/mode mismatch, active descendants on detach, an interrupted transaction, rollback over divergent bytes, and a missing final receipt refuse. |
| Promotion | An active descendant promotes a root summary whose every numbered decision has valid `pod_sources`; root search returns only the summary. | Missing ordinal, non-existent source, sibling/independent source, duplicate use, postdated source, wrong root, incomplete mapping, and implicit root search for source text fail. |
| Provenance | V2 runtime/ledger normalisation, reference-only bindings, local projection, append-only check, migration receipt, and binding verification produce matching CLI/MCP results. | Tampered/reordered event, cross-runtime ledger, mismatched sidecar, v1 write, code-bearing payload, unavailable Git classification, source digest mismatch, duplicate migration, and an in-place legacy rewrite fail without a write. |
| Version and caller boundary | Root identity initialization precedes a v2 root/pod ledger; the physical target pod migrates its derived v1 legacy source through one receipt. | Mixed v1/v2 grammar, v2 path fields, absent/forged root id, root/sibling/retired/detached migration caller, arbitrary source path, and target/runtime activation mismatch fail before write. |
| Task Packet | Root default compiles without pod reads; an explicit active selected pod produces a measured packet with inherited root agent-rules/session guidance and one exact pod session target. | Missing, malformed, retired, detached, sibling, independent-root, template, or fixture target; unselected-pod/root session path; wildcard/alias; direct write/timestamp override; and activation target drift all refuse with CLI/MCP parity. |
| Reflection | One sequential v2 ledger per root workstream preserves trusted history, phase/ownership checks, append commits, receipts, rebind, close, and expiry; historical v1 is read-only. | A pod caller (including one naming a root ledger), pod selector/path, or selected-pod reflection-writing packet returns `pod-reflection-not-supported-p0` before any write; root v1 authoring/fuse/reservation paths remain unavailable. |
| Fuse | Root and pod sessions, decisions, link/topic/diagram sidecars are rendered/staged by qualified identity and retain normal entry trailers plus a qualified receipt. | Unclassified marker path, duplicate bare entry id, parentless/cross-pod sidecar, changed historical record, raw merge, missing staged blob, receipt mismatch, or unrelated-pod discovery aborts without dropping bytes. |
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
| G0 — plan | This revised document, merged v2 core, retirement/governance gates, seven historical entry IDs, stale-branch dispositions, scope, and non-goals. | Independent re-review approval is still missing. Record the verdict and prerequisite receipts before implementation dispatch; this branch stops here. |
| G1 — boundary/schema | Resolver API, root-id initialization, v2 schemas, mixed-version/migration semantics, ownership table, and compatibility refusals. | Focused core/provenance tests plus a written interface-freeze receipt. |
| G2 — packet/reflection | Selected-pod target binding, inherited root baselines, exact session admission, root-default zero traversal, activation/artifact loading, one sequential v2 root ledger, and v1 read-only compatibility. | CLI/MCP canonical parity; real-Git no-discovery, pod-refusal/no-write, v2 authority/receipt, and historical v1 tests. |
| G3 — surface/lifecycle/fuse | CLI/MCP shared planner, receipted adoption/detachment/update, diagnostics, explicit inspection, `-merge`, reset/stage, and qualified sidecars. | Real-Git positive/negative matrix, dry-run/write parity, recovery proof, and staged-blob/receipt evidence. |
| G4 — integration | Changed-path ownership, session-fuse preview, sidecar parents, no P1 expansion, and docs truthfulness. | Current-main rebase, clean fuse preview, full verification matrix, and diff review. |
| G5 — closure | Final review of implementation evidence and cleanup boundaries. | Explicit user integration/release direction; neither is implied by this plan. |

For the future implementation, run the focused suites at each track hand-off,
then on the reconstructed integration candidate run:

```powershell
python -B -X utf8 -m pytest -q tests/test_seed_pod_core.py tests/test_seed_pod_fixtures.py tests/test_seed_pod_surfaces.py tests/test_project_lifecycle.py tests/test_context_derivation_strategies.py tests/test_session_fuse_and_merge.py tests/test_provenance.py tests/test_provenance_engine.py tests/test_provenance_surfaces.py tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_reflection_ledger.py tests/test_reflection_workstream_ledger.py tests/test_hooks.py tests/test_mcp_read_parity.py tests/test_mcp_session_append.py
python -B -X utf8 -m pytest -q
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" docs check
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" docs index --check
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" links check
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" topics check
python -X utf8 -c "from memory_seed.cli import main; raise SystemExit(main())" esr --json
git diff --check
```

Run seed/live parity and the relevant maintained demo checks after receipted
adoption. Any existing baseline warning must be reported separately from a
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

Obtain an independent G0 re-review against the merged v2 core and retirement
contract. Record the verdict and verify the prerequisite implementation and
ratification receipts; approval of this document alone does not satisfy those
foundation gates. Only then compile fresh Task Packets from the reviewed
contract and begin Stage 0. Do not resume or import an old Seed Pod branch,
integrate this planning change, or start P1 federated retrieval.
