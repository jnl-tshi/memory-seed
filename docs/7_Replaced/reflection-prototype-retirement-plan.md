---
superseded_by: "reflection-launch-verification-closeout.md"
superseded_on: "2026-09-19"
disposition_note: "Implementation is substantially complete; the remaining bounded launch verification moved to the successor closeout plan."
title: "Reflection Prototype Retirement and First Board v1 Plan"
date: "2026-09-07"
project: "memory-seed"
status: "active"
priority: "P1"
next_action: "Verify the retired prototype stays absent in the integrated launch matrix and first-board evaluation."
source:
  - "docs/7_Replaced/reflection-ledger-workstream-evolution-plan.md"
  - "docs/7_Replaced/plan-reflection-ledger.md"
  - "docs/CONSTITUTION.md"
  - "memory_seed/reflection_ledger.py"
scope: "Remove the unused participant-fragment prototype completely and designate the first real sequential workstream Reflection Board as v1 before CLI/MCP launch."
non_goals:
  - "No product implementation, migration, board creation, historical rewrite, merge, push, release, or Seed Pod P0/P1 execution in this planning tranche."
  - "No constitutional amendment or grandfathered reflection format."
  - "No relaxation of sequential ledger authority, receipt, approval, compaction, or retention guards."
dependencies:
  - "Independent approval of this plan and its corrected workstream schema annex."
  - "Repeat the no-board inventory at the exact implementation base before removing code or changing hash domains."
acceptance_criteria:
  - "One sequential Reflection Board v1 ledger per branch/workstream is the only supported reflection format."
  - "All prototype-only models, readers, codecs, verifiers, writers, reservations, fuse/expiry machinery, fixtures, and success tests are removed."
  - "Only low-level helpers with demonstrated reachability from the sequential ledger remain."
  - "Schemas, hash domains, golden vectors, APIs, diagnostics, packet bindings, tests, active documentation, and Seed Pod P0 references agree on v1."
  - "No compatibility shim, integration path, or stale Task Packet preserves an alternate writer."
---

# Reflection prototype retirement and first board v1

The first real reflection board uses one sequential ledger per branch/workstream and is **Reflection Board
v1**. The abandoned shared-document participant-fragment implementation is the **prototype**, with no
product version. The user's 2026-09-07 instruction replaces the previous read-only compatibility decision:
remove its entire unused runtime and tests, not just its writers.

This amendment owns the removal, naming, and non-migration boundary. The
[workstream plan](reflection-ledger-workstream-evolution-plan.md) owns the retained sequential architecture,
including strict parsing, trusted Git history, receipt coverage, and admitted compaction. The
[original plan](../7_Replaced/plan-reflection-ledger.md) is documentary evidence only; its dispatches must
never be compiled or launched. Prototype removal and the sequential v1 public CLI/MCP, ESR, hook, and
runbook surfaces are now implemented in the current source tree. The first real board and launch
evaluation remain planned. The measured inventory below is historical evidence at its stated revision;
it does not stand in for the integrated launch checks. See the
[operator guide](../4_Reference/reflection-board-v1-operator-guide.md) for implemented syntax and limits.

## Measured absence and reproducible inventory

Measured on 2026-09-07 at main `590481ed339831b0e537c9bc69b5d84871403ac9`, with the new planning branch
initially at that same SHA:

| Checked source | Measured result |
| --- | --- |
| Current tracked tree, including nested runtime paths | Zero files under any `.memory-seed/reflections/` family. |
| All 45 local branch tips, enumerated individually | Zero reflection-family paths. |
| All 1,978 commits reachable from local refs (`git rev-list --all`) | Path-history and reachable-object inventories contain zero reflection-family paths/objects. |
| All 14 registered working trees, including primary and this planning tree | Zero reflection files, including untracked/ignored files in the scanned reflection families. |
| Primary physical tree, including worktree directories and residual directories | The same recursive file inventory finds zero reflection files. |
| Source and tests | Both the participant-fragment prototype and sequential implementation exist; constructed test data and prose examples are not real boards. |

The negative result is limited to the inspected repository, its locally reachable Git history, and local
working trees. It makes no claim about un-fetched remotes, unreachable/pruned objects, deleted uncommitted
files, external installations, or unknown alternate storage paths. No external-data migration or deletion
is authorized. Within that measured scope, no prototype board ever entered active runtime state and there
is no old reflection data to preserve, freeze, grandfather, or migrate.

Repeat this read-only procedure immediately before implementation and again before the first real board.
Capture exit codes, exact base SHA, every branch tip SHA, every worktree HEAD, counts, and exceptions in the
implementation receipt. An error is not an empty inventory.

```powershell
git rev-parse HEAD
git status --short
git for-each-ref --format='%(refname) %(objectname)' refs/heads
git worktree list --porcelain
git ls-files
# Filter tracked paths for (^|/)\.memory-seed/reflections/.
# For EVERY enumerated local branch, run git ls-tree -r --name-only <ref> and apply the same filter.
git rev-list --all
git log --all --format= --name-only -- '.memory-seed/reflections/**' ':(glob)**/.memory-seed/reflections/**'
git rev-list --all --objects
# Filter reachable object paths for (^|/)\.memory-seed/reflections(/|$).
# For primary and EVERY registered worktree:
rg --files --hidden --no-ignore -g '**/.memory-seed/reflections/**' -g '!**/.git/**' -g '!**/.venv/**' -g '!**/node_modules/**' <worktree>
```

The broad primary scan covers residual worktree directories too. Git inventories cover tracked content
even in excluded dependency directories. Temporary test repositories under dependency/generated output are
not project runtime evidence. `git ls-tree` does not support `:(glob)` magic; enumerate its complete path
list and filter afterwards (the initial unsupported invocation failed and was replaced, never counted as
zero). Search source/tests/docs for exact schema names and investigate any candidate claiming persisted
board data outside the canonical family. Preserve a path-by-path finding for any such exception.

If any real board, durable prototype receipt, or independently authored sequential pre-v1 board is found,
stop the destructive/format-changing portion, leave every byte unchanged, and return the evidence for a
new scoped decision. Do not invent a migration, silently relabel records, or install a compatibility reader.

## Constitutional disposition

Withdraw the previously proposed v1 retirement transition in full. Do not edit
`docs/CONSTITUTION.md`, bump its version, add a retirement carve-out, or seek ratification for this
nonexistent population.

Constitution 1.12's `constitution:v1#temporary-reflection-expiry` governs actual chains created inside
declared boards. There are no prototype chains to freeze and no elapsed chains whose cleanup obligation
would be abandoned. Removing unused implementation and synthetic tests does not rewrite or delete
historical memory. The ratified clause already governs the first real sequential v1 board, including
required validation, synthesis, complete durable receipts, chain-level close, seven-day default retention,
and guarded expiry. Source cleanup is ordinary implementation evolution under §11. Historical plans,
session entries, ADRs, and Git history remain evidence under the append-only invariant.

The earlier compatibility rationale was preservation of hypothetical old records; the measured empty
population removes that premise. This improves Trust and Application by making one supported implementation
and its governance inspectable. Existing sequential early-expiry and historical elapsed-time admission
limitations stay fail-closed until their own reviewed contracts are implemented; renaming never enables
a currently refused cleanup path.

## Exact version and identity contract

| Surface | Required v1 result |
| --- | --- |
| Product | Reflection Board v1; one sequential workstream ledger. The combined board view remains a derived read-only projection. |
| Canonical path | `.memory-seed/reflections/active/<workstream_id>/ledger.md`; no version segment, manifest, reports, fragments, or closeout companion. |
| Ledger discriminator | `schema: memory-seed/reflection-workstream-ledger`, `version: 1`. Exact schema plus version, never integer version alone. |
| Retention preflight / approval | Existing `memory-seed/reflection-retention-preflight` and `memory-seed/reflection-retention-approval` schema names, both `version: 1`, and `id_domain: memory-seed/reflection-workstream-ledger/v1`. |
| Other independent schemas | Retention trust anchor and compaction receipt stay at their existing version 1. Task Packet v1, Retrieval Specification v2, ADR versions, and package/Constitution versions are unrelated and unchanged. |
| Hash domains | `memory-seed/reflection-workstream-ledger/v1\0`, `.../v1/ledger\0`, and `.../v1/detail\0`; NUL is the actual final byte. |
| IDs | Keep `rwl_`, `rlr_`, `rlc_`, `rrc_`, 96-bit framing and 20-character Crockford suffixes. Recompute every golden vector and dependent digest with v1 domains; no old-to-new ID aliases or remapping service. |
| Python API | Keep semantic `Workstream*`, `workstream_*`, `parse_workstream_ledger`, `load_trusted_workstream_ledger`, and guarded adapter names where still accurate. `WORKSTREAM_LEDGER_VERSION = 1`; rename every `_v2_*` / `*_v2_*` internal to `_workstream_*` / `*_workstream_*` (use a narrower semantic name where needed). No old aliases. |
| Discriminator result | Replace the current `v1`/ `v2` family switch with one supported `workstream-v1` result; everything else is unsupported/malformed. No prototype parser delegation. |
| CLI / MCP | Use the existing planned unversioned `reflection ledger init/append/check/view/close/expire` and `reflection board view` names; all route to v1. No public version selector or prototype inspection command. |
| Packets | `execution.reflection.format: workstream-v1`, exact ledger path/id, allowed operations and measured trusted binding. Task Packet schema version remains independent. |
| Diagnostics / tests / docs | Replace sequential-v2 names and prose with v1; do not globally replace unrelated version numbers. Remove `legacy-reflection-read-only` and frozen-format success semantics. Use `unsupported-reflection-format` for unsupported reflected input; removed commands use ordinary unknown-command/operation errors. |

Use **prototype** only in documentary history, removal inventories, and a test's explanation of refused
unsupported input. Do not introduce `legacy-prototype` as a runtime family, retain `Prototype*` production
classes, or keep old fixture builders/success tests. A few minimal hostile byte strings in v1 rejection
tests are negative controls, not a compatibility corpus. Historical source strings/version claims in
append-only memory and replaced plans remain verbatim historical evidence; prefix them with a current
disposition only in the documentary router, not by rewriting history.

## Removal inventory and helper proof

| Existing production area in `memory_seed/reflection_ledger.py` | Required disposition |
| --- | --- |
| `ReflectionManifest`, `ReflectionParticipant`, `ReflectionReservation`, roster/seal and reservation functions/constants | Delete models, constructors, parsers, renderers, validators, ID allocation, and exports. |
| `ReflectionReport`, `ReflectionFragment`, prototype `ReflectionRecord`, their codecs and relationship/admission helpers | Delete complete prototype object graph and report/fragment provenance mechanics. |
| `AdmittedReflectionSet`, `admit_reflection_git_tree`, prototype live-head/common-view functions | Delete. The sequential ledger's own board view is the only reflection reader. |
| `ReflectionReceipt`, `AdmittedReflectionReceipt`, `ReflectionChainClose`, `AdmittedChainClose`, prototype closeout and receipt resolution/validation | Delete all prototype-only models, constructors, codecs, admission, and historical read routes. Preserve only independently needed neutral session-locator primitives after proof. |
| `EarlyExpiryApprovalReceipt`, prototype approval codecs/verification, `eligible_expiry_paths` | Delete. Keep cryptographic primitives only when used by sequential retention admission; do not retain the prototype approval schema. |
| `_ReflectionFusePlan`, `ReflectionFuseResult`, `reflection_fuse_preview`, `reflection_fuse`, `_apply_reflection_fuse_plan`, fuse-only Git delta helpers | Delete complete preview/apply/token machinery and exports. Ordinary session fusion is unaffected. |
| Shared canonical text/YAML/scalar/path/clock/digest helpers, `crockford`, `ed25519_verify`, Git blob/commit and session scope helpers, `ReflectionDiagnostic` / validation error | Keep only each helper's transitive call graph rooted in the sequential v1 public core/adapters. Remove dead siblings; rename ambiguous ownership (for example `ReflectionBlob` to a neutral Git-blob type) or extract only when it simplifies actual reuse. |
| `tests/test_reflection_ledger.py` | Remove prototype suites, fixtures, builders, and imports. Move only independently useful shared-helper tests to v1/neutral tests and rewrite their fixtures without prototype models. If nothing remains, delete the file. |
| `tests/test_reflection_workstream_ledger.py` and surface/integration tests | Rename sequential-v2 tests and regenerate all canonical v1 vectors, signatures, receipts, IDs, and byte digests. Preserve adversarial authority tests. |
| `.gitattributes` reflection protection | Keep `.memory-seed/reflections/active/** -merge`; replace fuse rationale with sequential ledger validation and guarded integration. |
| CLI, MCP, packets, core integration, docs, live/Seed runbooks | Do not implement unshipped prototype routes. Remove any now-found imports, exports, feature switches, fallback dispatches, or compatibility branches. |

The core owner supplies a before/after symbol inventory with one explicit reason and a sequential call site
for every retained helper originally located in the prototype region. An import existing only in old tests
is not proof of product need. Keep no alternate object graph merely to exercise old tests. At baseline
`workstream_board_view` and `_trusted_active_ledgers_at_commit` skip manifest-only candidates; remove those
silent exclusions. Every reserved-family candidate must be shown/refused, never hidden as a supported
historical family.

## Integration and Task Packet boundaries

Keep one shared pure reflection capability validator plus measured binding adapter. A writing packet with
any normalized allowed exact path under the active runtime's `.memory-seed/reflections/` requires the
explicit `workstream-v1` capability. Its exact fields are `format`, `workstream_id`, `ledger_path`,
and non-empty `operations` from `append`, `close`, `expire`, `rebind`. Initialization belongs to the
orchestrator before worker compilation. The canonical bound ledger is its sole reflection write path.
Apply current case/separator/path normalization and segment boundaries; missing files, `expected_absent`,
or stripped legacy metadata do not escape the reserved-path guard. Unknown fields/formats or wider scopes
refuse. Operations narrow existing role/phase/expected-identity/approval authority and cannot grant it.

Use that validator during dispatch compilation, activation, `_read_activation_artifact`, and
`core._activated_packet_base_sha`, and inventory every hook/cadence/implements consumer. Old packet hashes
or receipts grant no exemption. Generic Task Packet schema-v1 source-code work and read-only evidence
packets remain valid; read-only packets still cannot activate writer attribution. A source-code edit to
`memory_seed/reflection_ledger.py` is not a runtime reflection write.

Sanctioned integration preview/apply/prepare/merge/integrate and MCP routes share the sequential reflection
preflight. Inventory canonical reserved paths from exact base, source, merge-base, and proposed result
trees with modes/blob IDs. Only valid sequential v1 history can enter active state; unsupported families,
unknown reserved files, mixed directories, stale bindings, symlinks, ambiguous topology, and raw
non-monotonic changes refuse before any mutation. Recheck preview bindings on apply. There is **no**
destination-resident prototype carry-through exception and no prototype fuse inside ordinary session fuse.
Unrelated session-only integration preserves current transitive import behavior. If unsupported data is
encountered, report it and leave it in place; refusal is not authorization to delete it.

## Delivery, ownership, and acceptance

1. **Plan reviewer:** independently verify this amendment, evidence bounds, schema annex and no-exception
   reasoning. The orchestrator records the verdict. No constitutional ratification work item remains.
2. **Sequential core owner:** remeasure the exact base; remove the full prototype and rename the sequential
   format in one coherent workstream before public launch or real board creation. Own core, focused tests,
   shared helper proof, and `.gitattributes`. Keep unresolved cleanup authorization failures closed.
3. **Integration/packet owner:** after the core API freezes, own shared integration admission and packet
   compile/activate/artifact-reader guards and regression tests. The orchestrator owns overlapping
   `core.py` and `task_packet.py` changes; execute serially.
4. **Surface/workflow owner:** after core and admission review, implement the existing CLI/MCP/ESR work,
   active/Seed instructions, and public docs using only Reflection Board v1. No prototype command or shim.
5. **Independent validator:** run the full supported v1 and ordinary-session suites plus the matrix below;
   inspect final imports/exports and retained-helper evidence. Report unresolved expiry contract work as a
   launch blocker if required lifecycle behavior remains unavailable.
6. **Orchestrator:** integrate the format/removal change before creating the first real board. A disposable
   test fixture is not the first real board. Only an actual approved workstream through the governed v1 init
   earns that designation after launch gates pass. Update the existing experiment reflection log with
   measured results; Seed Pod P0 consumes the stabilized foundation later and remains separately gated.

| Acceptance proof | Observable result |
| --- | --- |
| Zero-data preflight | Full branch/history/worktree inventory succeeds with zero real boards/receipts; any discovery blocks destructive cleanup and renaming until separately resolved. |
| Prototype removal | Former model/codec/reader/verifier/fuse/expiry APIs and fixture builders are absent, with zero production imports/exports or compatibility aliases. |
| Supported v1 | Init, sequential roles/rework, append commit/CAS, trusted history, dependencies, durable receipts, rebind, close and governed expiry satisfy the workstream plan; stale/forged/unadmitted variants refuse. |
| Format rename | Exact v1 ledger/preflight/approval bytes, domains and independently computed vectors agree; old version-2 sequential bytes and prototype schemas refuse with zero writes. |
| Reserved-family visibility | Manifest-only, orphan fragment/report, unknown and mixed candidates are reported as malformed/unsupported; none disappears from board/ESR/integration discovery. |
| Writer closure | Compile/activation/artifact-reader, CLI/MCP and every sanctioned integration path refuse prototype/stale/wider-scope requests before filesystem/index/ref/session/config/cache mutation. Generic Task Packet v1 and ordinary session integration positive controls pass. |
| One authority | Two parallel workstreams have separate v1 ledgers; each serializes roles, combined inspection is read-only, and no participant reservations, fragment pairs, or reflection fuse exists. |
| P0 | Root-only v1 references and `workstream-v1` packet contract agree. Pod writes still refuse `pod-reflection-not-supported-p0`; no P0/P1 execution occurs in this tranche. |

Search the full tracked implementation/test/active-guidance surface after removal. Include hidden live/Seed
runtime files explicitly. Inspect every hit; a repository-wide zero `v1` or `v2` count is meaningless.

```text
rg -n 'ReflectionManifest|ReflectionParticipant|ReflectionReservation|ReflectionReport|ReflectionFragment|AdmittedReflectionSet|ReflectionReceipt|AdmittedReflectionReceipt|ReflectionChainClose|AdmittedChainClose|EarlyExpiryApprovalReceipt|reflection_fuse|ReflectionFuse|eligible_expiry_paths|reservation_id|participants_seal|parse_manifest|render_manifest|parse_fragment|render_fragment|parse_closeout|render_closeout|admit_reflection_git_tree|legacy-reflection-read-only' memory_seed tests memory-trace
rg -n 'v2|V2|version: 2|version.*2|workstream-v2' memory_seed/reflection_ledger.py tests/test_reflection* docs/2_Todo/reflection* docs/8_Deferred/seed-pod-p0-reconciliation-plan.md
rg -n --hidden 'reflection|Reflection' .memory-seed/agent-rules.md .memory-seed/skills memory_seed/seed/.memory-seed memory_seed/cli.py memory_seed/mcp_server.py memory_seed/task_packet.py memory_seed/core.py .gitattributes README.md
```

Delete no durable session/ADR/history to make searches pass. Record legitimate negative-control literals
and documentary references separately from forbidden runnable compatibility. Confirm API export lists,
dynamic dispatch/imports, CLI help, MCP tool registrations, packet schemas, and Seed twins, not only static
symbol counts. Run checkout-local v1 focused tests, packet/surface/session integration tests, then
`python -X utf8 -m pytest` (both Memory Seed and Trace suites), docs/index/link checks, ESR, and
`git diff --check`. Invoke only test files present at that baseline. Planning validation is docs/index/
links/ESR/whitespace only; it does not prove product behavior.

## Non-migration and rollback

There is no migration command, version toggle, reader adapter, ID bridge, automatic adoption, fixture
backfill, data conversion, or cleanup pass over real files. Fresh v1 boards are initialized empty through
the governed writer. Synthetic vectors change with the hash domains and are regenerated in tests; they are
not migrated project records. Existing ordinary sessions and documentary references keep their exact
historical meaning.

Before the first real v1 board, rollback is a normal reviewed code-branch revert with no runtime data to
convert. Once real v1 data exists, that no-data premise is no longer available: any future schema change,
retirement or rollback must inventory and preserve it under the ordinary Constitution and an independently
reviewed compatibility/migration decision. Do not reuse this plan as permanent authority to discard boards.
