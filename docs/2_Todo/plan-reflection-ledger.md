---
title: "Plan-Scoped Reflection Ledger"
date: "2026-09-06"
project: "memory-seed"
status: "active"
priority: "P1"
next_action: "Review the temporary-ledger contract and the three dispatch drafts; then land the serial foundation before any worker creates a reflection fragment."
source:
  - "docs/CONSTITUTION.md"
  - ".memory-seed/skills/agent_collaboration.md"
  - ".memory-seed/skills/session_logging.md"
  - "experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md"
  - "docs/2_Todo/task-packet-hardening-progressive-provenance-plan.md"
scope: "Add a plan-scoped, multi-writer reflection ledger with a guarded fuse, derived common view, Task Packet handoffs, and explicit promotion of reusable lessons into ordinary sessions."
non_goals:
  - "Do not place reflection records in .memory-seed/sessions/ or alter past session history."
  - "Do not make the ledger a permanent retrieval corpus, ADR source, index, or database."
  - "Do not add worker dispatch, worktree creation, provider, network, or autonomous decision authority."
  - "Do not infer a durable lesson or session entry from a worker report without an orchestrator decision."
dependencies:
  - "Current branch-session fuse and session merge-branch primitives."
  - "Current Task Packet v1 compiler, measured binding, and clean-session worker contract."
  - "A reviewed plan manifest that names every participant, branch, output directory, and report contract."
acceptance_criteria:
  - "Each authorized worker can commit an append-only, source-provenanced reflection fragment in only its assigned plan path."
  - "The reflection fuse rejects every membership, ownership, sequence, ID, report-provenance, correction, duplicate, or collision violation before an integration write."
  - "A derived common view exposes all admitted opinions and their corrections without silently selecting an opinion as truth."
  - "Only the orchestrator can author resolution or promotion records, and durable lessons are written through the ordinary guarded session append path during the plan."
  - "Sealing retains the completed temporary ledger as append-only archive evidence after all promoted lessons are evidenced; only derived views may be discarded."
---

# Plan-scoped reflection ledger

## Outcome and decision

Create a narrowly scoped reflection facility for a single approved plan. It collects independent worker
opinions and first-hand handoff evidence while the plan is active, then becomes a sealed, explicitly
addressed archive after the orchestrator has resolved the plan and selectively promoted reusable lessons into
normal append-only sessions.

This is deliberately not a second session layout. Durable sessions remain the chronological rationale
authority. The reflection ledger is temporary coordination evidence: it is Markdown/YAML while live, is fused
with the same fail-closed principles as sessions, is visible to humans and agents through a derived common
view, and is not discovered by ordinary memory retrieval. A lesson becomes durable only through the
existing guarded session writer and an explicit orchestrator promotion record. Temporary means no durable
memory or retrieval role after closure, not destroyable evidence: Constitution invariants #2, #3, #4, #6,
and #7 require the canonical attributable history to remain. Only generated views/exports are disposable; no
constitutional amendment is assumed.

The five-question test: this primarily improves **Validation**, **Trust**, and **Application**. It makes
parallel opinions inspectable and attributable before an orchestrator acts on them, without pretending that
worker agreement creates authority.

## Constraints carried forward

- Constitution invariants #2, #3, #4, #6, and #7 govern the design: append rather than rewrite; retain
  attribution; keep current-file truth separate from historical reasoning; use Markdown as the only
  authority; and never hide admissible history behind a ranking.
- A derived result cannot silently override a first-hand statement. The common view is a projection and
  displays provenance, corrections, and disagreements. It has no effective-winner field.
- `adr_branch_session_fuse` and `adr_merge_branch_primitive` establish the useful precedent: Git handles
  topology, but Memory Seed must validate identity, provenance, chronology, and immutability in an explicit
  fuse rather than trust a text merge driver.
- `adr_control_file_authority` and `adr_session_decision_authority` retain the authority partition. The
  plan ledger has no standing control-plane authority and an ADR may cite a promoted session decision, not a
  transient fragment.
- `adr_mcp_decision_envelope_review` and Constitution write-surface parity require CLI and MCP writers to
  call the same validator. No convenience MCP path may hand-write a fragment.
- A plan is not permission to land, delete, or promote. The existing `integration_mode`, `merge_trigger`,
  worktree guard, and live-user approval rules continue to control those actions.

## Current-code reuse points

| Existing surface | Reuse | Deliberate boundary |
| --- | --- | --- |
| `memory_seed/core.py`: `SessionFuseResult`, `_SessionFusePlan`, `_changed_session_paths`, ref readers, chronological record sort/render helpers, `session_fuse()` | Model the preview/apply result, three-dot source/base comparison, parse-before-write workflow, deterministic rendering, `already_present` reporting, and failure wording. | Do not widen `iter_session_documents()` or session parsers to treat reflections as sessions. Reflection records get their own parser, renderer, file classifier, and result type. |
| `memory_seed/core.py`: `session_merge_branch()` | Follow the one-step sequence: preview, no-ff merge, reset protected paths to base, apply only an approved fuse plan, stage, commit, and abort a refusal before a usable merge exists. | Reflection fusion is an additional plan-family phase, not a fallback raw merge and not a Git merge driver. |
| `tests/test_session_fuse_and_merge.py` | Reuse its temporary-Git-project fixtures and negative-control style for chronology, sidecar parentage, immutable base records, source decoding, duplicate keys, and apply-only-in-merge behavior. | Add a dedicated `tests/test_reflection_ledger.py`; do not turn session tests into reflection-format tests. |
| `memory_seed/task_packet.py`: `normalize_task_dispatch()`, `compile_task_packet()`, measured `runtime_binding`, `expected_absent`, acceptance observables, `execution_defaults` | Use existing semantic dispatches to give a worker exact reflection output paths, expected report artifact, preflight, validation, and handoff contract. Packets remain derived and ephemeral. | V1 initially needs no new dispatch field: exact paths and observables express the reflection contract. A future native field is out of scope unless the pilot proves repetition or ambiguity. |
| `memory_seed/cli.py` and `memory_seed/mcp_server.py` | Mirror existing parser/handler and structured-preview conventions; preserve CLI/MCP canonical-result parity. | MCP read operations are inline and non-mutating; any writer calls the same core validation used by CLI. No MCP operation merges a branch or seals a ledger without the same gates as CLI. |
| `.memory-seed/skills/agent_collaboration.md` and the Seed twin | Reuse Task Packet ownership, clean-session, worktree, worker-checkpoint, final-handoff, and serial-integration rules. | Extend the runbook only after core behavior passes tests; a reflection fragment is not a worker permission to write a durable session. |
| `experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md` | Preserve its useful dimensions: source coverage, authority fidelity, extra-hop classification, scope accuracy, exact receipts, and independently reviewed limitations. | It remains an experiment-specific log. The plan ledger is not a general-purpose replacement for it. |

## Worker Task Packet governance baseline

Every project-worker Task Packet, including a clean-session worker, must materialize the **full active**
`.memory-seed/agent-rules.md` as baseline governance. This supersedes the older Worker Context Contract
assumption that clean workers omit agent rules. Full orientation remains lazy: the baseline does not automatically add
orientation, index, policy, sessions, or every skill.

The compiler additionally materializes the **full active** `.memory-seed/skills/session_logging.md` when either
`memory_update_policy: worker_checkpoint` is selected or `execution.allowed_files` contains any session path.
Such a packet must state that the only session write is the canonical MCP/CLI append route with automatic
clock ownership: omit timestamp and accept the MCP/CLI returned value (a dry run may carry its returned
timestamp into the real append). Direct session Markdown edits and manual/explicit timestamp overrides are
forbidden unless a named repair/backfill authorization is explicitly granted in the packet and validated by the existing repair
authority. The same rule applies to every packet surface; it is not a model instruction that a caller may
silently omit.

Implementation extends the compiler's mandatory materialized evidence and input ledger with components
`baseline_agent_rules` and, when applicable, `session_logging_guard`. The ledger records each source digest,
line range, and token estimate separately, and cost/token accounting includes those components before budget
enforcement. Tests cover clean worker inclusion, session-path/checkpoint inclusion, missing files, direct-edit
and timestamp-override refusal, explicit repair/backfill authorization behavior, token-budget accounting, and
unchanged lazy orientation. Ada's observed clean packet omitted agent rules/session-logging and accepted a
future timestamp; the Auditor must record that as a source-linked risk finding and tests must include it as a
negative fixture. The Surface/packet track owns compiler and task-packet test changes for this
cross-cutting packet contract; it must not duplicate Kernel or integration reflection tests.

## Plan family, storage, and lifecycle

The canonical family is distinct from `sessions/` and starts in its permanent archive location; later closure
does not delete or move evidence:

```text
.memory-seed/reflections/archive/reflection-ledger-v1/
  manifest.yaml
  reports/ledger-kernel/rpr_01KERNELLEDGER0000001.md
  fragments/kernel/ledger-kernel/001-rfl_01KERNELLEDGER000001.md
  reports/ledger-surfaces/rpr_01SURFACELEDGER0000001.md
  fragments/surfaces/ledger-surfaces/001-rfl_01SURFACELEDGER00001.md
  reports/ledger-auditor/rpr_01AUDITLEDGER00000001.md
  fragments/verification/ledger-auditor/001-rfl_01AUDITLEDGER000001.md
  reports/codex-orchestrator/rpr_01ORCHLEDGER00000001.md
  fragments/integration/codex-orchestrator/001-rfl_01ORCHLEDGER000001.md
  seal.md
```

Archive means retained evidence, not session membership or a reusable retrieval corpus. Reflection commands
address a sealed plan only by explicit ID. `reflection view` writes no stored view: canonical Markdown goes
to stdout; a guarded explicit output path is a disposable derived export. JSON is non-authoritative transport
or export only.

`reflection init` is orchestrator-only and runs only after the Kernel parser/fuse lands. It generates a
256-bit `reservation_seed`, creates canonical `manifest.yaml`, validates it, and commits it before Task
Packet compilation. IDs are `prefix + Crockford(base32(SHA-256(seed || plan_id || participant || sequence ||
slot))[0:20])`; they never depend on prose, timestamps, report bytes, or branch tips. Each literal tuple
`(participant, branch, track, sequence, report_id, fragment_id, report_path, fragment_path)` is committed in
the manifest, so Task Packets have no content-derived path cycle.

```yaml
schema: memory-seed/reflection-plan
version: 1
plan_id: reflection-ledger-v1
base_branch: main
base_sha: <40-character resolved SHA>
state: active                         # active -> sealed; never reopened
reservation_algorithm: sha256-crockford-v1
reservation_seed: <64-lowercase-hex>
participants_seal: <sha256 canonical participant-roster bytes>
orchestrator:
  participant: codex-orchestrator
  branch: codex/feature/reflection-ledger-integration
participants:
  - participant: ledger-kernel
    role: worker
    branch: codex/feature/reflection-ledger-kernel
    track: kernel
    reservations: [{sequence: 1, report_id: rpr_..., fragment_id: rfl_..., report_path: reports/..., fragment_path: fragments/...}]
  - participant: ledger-surfaces
    role: worker
    branch: codex/feature/reflection-ledger-surfaces
    track: surfaces
    reservations: [{sequence: 1, report_id: rpr_..., fragment_id: rfl_..., report_path: reports/..., fragment_path: fragments/...}]
  - participant: ledger-auditor
    role: validator
    branch: codex/feature/reflection-ledger-audit
    track: verification
    reservations: [{sequence: 1, report_id: rpr_..., fragment_id: rfl_..., report_path: reports/..., fragment_path: fragments/...}]
  - participant: codex-orchestrator
    role: orchestrator
    branch: codex/feature/reflection-ledger-integration
    track: integration
    reservations: [{sequence: 1, report_id: rpr_..., fragment_id: rfl_..., report_path: reports/..., fragment_path: fragments/...}]
```

The participant roster bytes are the canonical YAML rendering of `plan_id`, `base_branch`, `base_sha`, and
ordered participant/reservation tuples; `participants_seal` is their SHA-256. The manifest is authoritative;
the seal detects alteration, and both are checked against the base tree. A worker cannot self-enrol, amend a
reservation, write an unreserved path, or use a new sequence. More slots require a serial manifest revision
and recompiled packets before dispatch. The family is ignored by retrieval, session-target resolution,
compacting, links, ADR membership, and seed initialization unless an explicit reflection command is invoked.

Lifecycle:

1. **Kernel bootstrap.** Kernel lands parser/fuse/integration without a reflection record; a parser exists
   before ledger dogfood.
2. **Initialize.** Orchestrator commits the manifest and compiles packets with its exact reservations.
3. **Collect/fuse.** Subsequent workers and the auditor commit their reserved pair; each is admitted by the
   coordinated integration primitive.
4. **Resolve/promote/seal.** Orchestrator writes its reserved pair, promotes reusable lessons immediately,
   and appends `seal.md` when every disposition resolves.
5. **Close.** Derived views/exports may disappear. Canonical Markdown/YAML archive evidence remains
   read-only and explicitly inspectable.

## Fragment and report schema

### Report receipt

Each worker commits a canonical Markdown/YAML report before or with its fragment. It is evidence for the
fragment, not a claim that the report itself is accepted:

```markdown
---
schema: memory-seed/reflection-report
version: 1
report_id: rpr_<manifest-reserved-id>
plan_id: reflection-ledger-v1
participant: ledger-kernel
track: kernel
working_branch: codex/feature/reflection-ledger-kernel
base_sha: <manifest-base-sha>
task_packet_fingerprint: sha256:<64-lowercase-hex>
status: DONE|DONE_WITH_CONCERNS|BLOCKED
created_at: RFC3339-UTC
validation:
  - command: "..."
    exit_code: 0
---

# Worker report

Concise implementation/audit handoff and measured limitations.
```

Canonical authority is UTF-8 without BOM, Unicode NFC, LF, no trailing spaces, fixed schema-field order,
two-space YAML indentation, preserved list order, and exactly one final LF. The strict parser re-renders the
file and requires byte equality with the Git blob. Canonical report/fragment/manifest/seal files must be
regular mode `100644`; symlinks, executables, submodules, directories, and every mode drift refuse. Kernel
owns byte-exact golden fixtures for all four forms.

The report contains no `head_sha`, report-byte hash, or self-claim of acceptance. The preview fuse resolves
the named branch to the authoritative `source_tip`, then measures `(path, blob_oid, raw_sha256, mode)` for
every reserved report/fragment. Its admission receipt lives outside mutable report text in the fuse plan and
merge trailer: `(plan_id, manifest_blob, manifest_sha256, participant, branch, source_tip, base_sha,
blob tuples)`. Apply resolves the branch again and rejects a tip change. This proves repository consistency
and traceability, not an adversarial signature.

### Fragment

Fragments are Markdown with a timestamped heading and canonical YAML envelope. Manifest-reserved IDs are
rendered, never minted from content. Record IDs derive from the reserved fragment ID plus ordinal. No caller
invents an ID, and no body text can affect an output path.

```markdown
## 2026-09-06T12:34:56Z - Kernel fuse review

```yaml
schema: memory-seed/reflection-fragment
version: 1
fragment_id: rfl_<manifest-reserved-id>
plan_id: reflection-ledger-v1
participant: ledger-kernel
track: kernel
working_branch: codex/feature/reflection-ledger-kernel
sequence: 1
source: write-time
report_id: rpr_<manifest-reserved-id>
base_sha: <manifest base SHA>
```

### R1 - Separate the temporary parser from session discovery

```yaml
record_id: rlr_<manifest-derived-id>-01
kind: opinion
subject: parser-boundary
confidence: medium
```

The session fuse parser is a safety-pattern reference, but reflection files must not be returned by
`iter_session_documents()` or ordinary retrieval.
```

Record kinds have intentionally narrow authority:

| Kind | Worker | Orchestrator | Meaning |
| --- | --- | --- | --- |
| `observation` | yes | yes | First-hand fact or measured result; must cite its report. |
| `opinion` | yes | yes | A bounded recommendation or interpretation; it is not a decision. |
| `risk` | yes | yes | A concern with evidence and requested owner/disposition. |
| `correction` | yes, own prior record only | yes, own prior record only | New record with `corrects: <record_id>` and reason; original remains visible. |
| `resolution` | no | yes | Explicit plan-level choice, citing the opinions/risks it considered and rejected. |
| `promotion` | no | yes | Links a selected reusable lesson to a newly written ordinary session `entry_id` and decision reference when applicable. |
| `seal` | no | yes | Declares every fragment/report disposition and successful closure preconditions without deleting evidence. |

Every record carries a stable ID, explicit subject, source (`write-time` or `derived`), and report provenance
unless it is an orchestrator resolution, promotion, or seal. Corrections must target an earlier record
from the same participant; they cannot erase it, alter another participant's evidence, or turn an opinion
into a resolution. A derived record may fill a missing statement but never silently override a write-time
record; an attempted override requires a correction citing the exact prior record and resolution evidence.

## Reflection fuse and common-view behavior

`reflection fuse --preview --plan <id> --branch <branch>` is read-only. It resolves `source_tip` and base,
validates the base-established manifest/participant seal, examines three-dot changes, and rejects a manifest
edit, foreign family, unknown participant, wrong branch/base/track/sequence/ID/path, unreserved record,
malformed or noncanonical bytes, uncited/missing report, duplicate/collision, invalid correction/authority,
or a source not descended from manifest base. It also rejects changed bytes, deletion, rename/copy, extra
canonical path, and every mode change of base/archive evidence. `already_present` requires equal canonical
bytes **and** mode, not merely an equal ID.

The preview produces only approved canonical additions plus its measured admission receipt. Its `--apply`
route is internal-only and refuses unless the coordinated integration primitive presents an unexpired preview
token for the same source tip *and* both a reflection and session fuse plan.

The only integration route for a branch that changes reflections is
`memory-seed session merge-branch --branch <branch> --reflection-plan <id>`:

1. require clean worktree/integration mode, resolve base/source, then preview **both** fuses at the same tip;
   any issue leaves no merge state;
2. run `git merge --no-ff --no-commit`; a protected reflection/session conflict aborts fail-closed;
3. take the union of every path changed by either plan, including source-only additions; restore each
   base-present path's exact blob/mode and remove each base-absent merged addition, rejecting untracked
   collisions;
4. recheck tips/tokens, apply the approved session plan then reflection plan from parsed canonical bytes; a
   failure in either applies aborts the merge and restores the clean pre-merge state; and
5. stage only approved paths plus ordinary non-protected merge changes, post-check, and create one merge
   commit containing `Session-Fuse` and `Reflection-Fuse` trailers (plan, manifest digest, participant, tip).

`.gitattributes` marks canonical reflection paths non-mergeable. The integration checker rejects any merge
commit changing archive reflection paths without a successful matching reflection-fuse trailer; raw merge,
manual post-merge edit, and standalone reflection apply therefore fail closed.

`reflection view --plan <id>` consumes the same parsed records and writes canonical Markdown only to stdout:
raw records, measured source-tip receipt, correction chains, risks, resolutions, promotions, and participant
coverage, sorted by `(created_at, participant, sequence, fragment_id, record_ordinal)`. It may group but
must show every source record and label grouping derived. It never picks a majority or effective winner.
JSON/MCP structured data are non-authoritative projections of this same result.

## CLI, MCP, and orchestration surfaces

| Surface | Operation | Write policy |
| --- | --- | --- |
| CLI | `memory-seed reflection init --manifest-file …` | Orchestrator-only; validates identity, reservation paths/IDs, and roster seal before the initial manifest commit. |
| CLI | `reflection append --report-file … --fragment … [--dry-run]` | Checks guarded worktree, reservation ownership, sequence/IDs, and canonical bytes. Dry run returns exact rendered Markdown/YAML bytes. |
| CLI | `reflection check --plan`, `reflection view --plan`, `reflection fuse --plan --branch --preview` | Read-only. View is stdout Markdown; `--json` is transport only. Apply is internal to the coordinated merge primitive. |
| CLI | `reflection seal --plan --apply` | Orchestrator-only; validates dispositions/promotions and appends seal evidence. It deletes no canonical path. |
| MCP | `memory_reflection_view`, `memory_reflection_fuse_preview` | Non-mutating projections of the same core result as CLI. |
| MCP | `memory_reflection_append`, `memory_reflection_seal` | Added only with success/error parity tests; call shared validators and cannot merge or bypass live approval. |
| Orchestrator | Task Packet compile + coordinated integration | Compiles exact pre-reserved paths, checks binding/admission receipt, and owns resolution, promotion, integration, and seal. |

CLI and MCP must expose identical valid core result dictionaries/rendered bytes and identical structured
errors `{code, path, message, details}` for every shared fixture. No MCP writer hand-writes files. No export
path exists except stdout or a caller-scoped derived file guarded by the normal worktree policy. No new
dispatch engine is introduced: the ledger is evidence inside the existing flow.

## Authority, promotion, and sealing rules

- Workers can state only first-hand observations, opinions, risks, and corrections within their assigned
  prefix. They cannot resolve a cross-track disagreement, promote a lesson, modify the manifest, change
  another participant's record, integrate, or seal the plan.
- The orchestrator's `resolution` names the considered record IDs, the chosen conclusion, the rejected or
  deferred alternatives, and any remaining risk owner. It never rewrites a worker's prose.
- Promotion is selective and happens during the plan. The orchestrator uses ordinary `session append` / MCP
  append with normal chronology, DRAFT, topic, linkage, ADR-review, and branch guards. The durable session
  must retain a human-readable `D:`/`R:` explanation of conclusion and reason plus plan and source
  fragment/record IDs in `F:` prose; a bare pointer is invalid. The promotion record stores the resulting
  session `entry_id`, explanatory decision ID, and exact source records.
- A promotion is not automatic consolidation. One-off status, duplicate opinion, transient debugging,
  personal data, and unresolved disagreement are explicitly `not-promoted` with a concise disposition.
- Sealing is an explicit closure record, not cleanup. It is allowed only after `seal.md` covers every reserved
  and admitted fragment/report with blob/hash/mode receipt, every required durable promotion/disposition
  resolves, and no resolution is unresolved. It changes no old canonical byte or name. Runtime readers do not
  treat a sealed plan as active, but explicit inspection remains available.

## Delivery sequence and ownership

### Serial foundation

1. Add `memory_seed/reflection_ledger.py` with canonical Markdown/YAML schemas, manifest-reservation ID
   derivation, strict parsers/renderers,
   manifest/report/fragment validators, common-view projection, and a fuse-plan/result model. Extract only
   genuinely neutral Git/ref-diff helpers from `core.py` if reuse cannot stay internal without circular
   imports.
2. Add `reflection` CLI routes and the one coordinated session/reflection integration sequencing. Add
   `.gitattributes` protection for the sealed archive family so a raw line merge fails rather than fabricates
   a valid-looking record.
3. Add the read-only MCP preview/view surfaces. Add writers only after the shared validator and CLI behavior
   are fully covered.

### Parallel tracks after the foundation lands

| Track | Owned files | Deliverable | Dependency |
| --- | --- | --- | --- |
| Kernel fuse (serialized bootstrap) | `memory_seed/reflection_ledger.py`, minimal shared `memory_seed/core.py` helper extraction, `.gitattributes`, `tests/test_reflection_ledger.py`, canonical fixtures | Schema, manifest IDs, report validation, view, preview/internal apply fuse, coordinated merge, seal preconditions. It emits no ledger record. | Foundation base only. |
| Surfaces and packets | `memory_seed/cli.py`, `memory_seed/mcp_server.py`, `memory_seed/task_packet.py`, `tests/test_reflection_ledger_surfaces.py`, `tests/test_task_packet.py`, packet/worker documentation and its Seed twin | CLI/MCP parity, active-rules/session-logging packet baseline, pre-reserved paths, handoff validation, then its reserved pair. | Kernel API frozen and manifest committed. |
| Orchestrator integration test | `tests/test_reflection_ledger_integration.py` and integration fixture helpers | Multi-worktree simulation, dual-fuse reset/application, archive sealing, and negative controls. | Kernel + surfaces integrated; serialized owner only. |
| Independent auditor | Its pre-reserved report/fragment only | Read-only integrated-tree verdict and evidence handoff. | Kernel + surfaces integrated; no product/test edits. |

The orchestrator owns `.memory-seed/reflections/archive/<plan_id>/manifest.yaml`, the integration fragment,
branch ordering, resolution/promotion, durable session appends, seal, and the integration test. No worker
owns shared control-plane files, dependency files, existing sessions, ADRs, policy, index, or seed files.
This assigns each test file to one owner. The auditor writes only its reserved evidence pair and otherwise
reviews the integrated diff.

### Serial integration

1. Merge the format/parser foundation before any branch contains reflection data; Kernel is the serialized
   bootstrap and does not dogfood an unparseable format.
2. Orchestrator creates the frozen manifest/reservations, then compiles packets from its exact paths and IDs.
3. Require each worker to commit implementation, report, and fragment before review. Validate its base/head,
   report receipt, owned paths, and `reflection fuse --dry-run` output.
4. Integrate one branch at a time only with the coordinated dual-fuse primitive; rerun targeted checks after
   each merge. No octopus merge or raw conflict resolution for reflection paths.
5. Have an independent validator review the integrated behavior and negative controls. Route rework to the
   owning worker up to the existing bounded review-loop limit.
6. The orchestrator writes resolution/promotion/seal records, runs ordinary session promotion, validates
   sealing, leaves canonical archive evidence intact, then validates the integrated tree again.

## Test matrix and acceptance observables

| Area | Required proof |
| --- | --- |
| Manifest and ownership | Unknown/duplicate participant, roster-seal mismatch, changed manifest, foreign plan, wrong branch/base/track/reservation, a worker writing an orchestrator kind, and an uncited resolution all refuse. |
| Canonical IDs/bytes | Manifest-derived dry-run IDs; malformed/forged IDs; duplicate source ID; base collision same bytes/mode=`already_present`; changed bytes/mode refusal; duplicate sequence; invalid UTF-8/NFC/LF/final LF; golden manifest/report/fragment/seal bytes. |
| Report provenance | Missing report, wrong plan/participant/branch/base, unreserved path, malformed fingerprint, uncited report, changed source tip, and altered measured blob/hash/mode all refuse. Reports cannot claim a head SHA. |
| Archive immutability | Delete, rename, copy, source-only extra path, symlink/executable/submodule, and any mode change of an archive report/fragment/manifest refuse. |
| Corrections and derived view | Correction cannot edit or target another participant; original and correction remain visible; derived cannot outrank write-time without explicit correction; stdout Markdown and transport JSON are deterministic; disagreement is visible rather than collapsed. |
| Coordinated application | Both previews are required; no-commit merge resets every union path and removes additions; second apply failure aborts; raw/post-merge reflection integration fails closed; one commit has both receipts. |
| CLI/MCP parity | Same valid rendered fragment/result and `{code,path,details}` errors from both paths; MCP read surfaces and stdout view are non-mutating; unsupported export arguments fail closed; no writer bypasses core validation. |
| Packet governance baseline | Every worker packet materializes active agent-rules; worker-checkpoint/session-path packets also materialize session_logging, reject direct session Markdown/future timestamp overrides, preserve lazy orientation, and account both components in input/cost tokens. |
| Task Packet integration | Exact pre-reserved worker paths/IDs and expected-absent paths are materialized; stale binding blocks; packet evidence is not refetched; compilation is measured for all three drafts. |
| Promotion and seal | Promotion requires existing ordinary session entry, exact source, and durable explanatory conclusion/reason; invalid promotion/disposition blocks seal; archive bytes remain; only derived exports may be removed. |
| Regression | Existing `session_fuse`, `session_merge_branch`, Task Packet, docs, and MCP tests stay green. Add a negative control that deliberately corrupts a fragment/report and proves the new checker refuses it. |

Minimum final commands (run from the integration checkout using the checkout's own module) are:

```powershell
python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_reflection_ledger_integration.py tests/test_reflection_ledger_surfaces.py tests/test_session_fuse_and_merge.py tests/test_task_packet.py tests/test_task_packet_surfaces.py
python -X utf8 -m memory_seed.cli docs check
python -X utf8 -m memory_seed.cli docs index --check
python -X utf8 -m memory_seed.cli links check
git diff --check
```

## Task Dispatch drafts

These are semantic Task Dispatch v1 drafts, not hand-authored complete packets. They contain no path/ID
placeholder: the exact reflection artifacts are pre-reserved before compilation. The selected pins deliberately
ground the session-fuse and one-step merge contract; topics supply neighbouring context without depending on
this plan's mutable text. Each draft below was compiled against a measured binding in the verification step.

### A. Kernel bootstrap (no ledger record)

~~~yaml
schema: memory-seed/task-dispatch
version: 1
objective: "Implement the reflection-ledger parser, canonical Markdown/YAML renderer, fuse, golden bytes, and coordinated session/reflection integration primitive before any worker writes reflection evidence."
constitution_refs: [constitution:v1#append-only, constitution:v1#provenance, constitution:v1#markdown-authority, constitution:v1#write-surface-parity]
project_context:
  project_type_and_purpose: "Memory Seed is a local-first Markdown memory substrate whose Git-aware validators preserve attributable append-only reasoning."
  relevant_subsystem: "A separate reflection parser/fuse reuses session-fuse safety mechanics while the coordinated merge primitive applies both approved plans atomically."
  task_fit: "The parser and fuse must exist before a worker can safely author a ledger record, and raw Git merging cannot prove provenance or immutable bytes."
  downstream_use: "Surfaces, packets, auditors, and the orchestrator consume the frozen kernel; it grants no durable session or decision authority."
  non_goals: ["Do not author a reflection record during bootstrap.", "Do not alter sessions, ADRs, policy, index, seed, or Task Packet schema."]
execution:
  role: worker
  persona: none
  capability_tier: frontier
  write_intent: writing
  allowed_files: [memory_seed/reflection_ledger.py, memory_seed/core.py, .gitattributes, tests/test_reflection_ledger.py, tests/fixtures/reflection_ledger/canonical/manifest.yaml, tests/fixtures/reflection_ledger/canonical/report.md, tests/fixtures/reflection_ledger/canonical/fragment.md, tests/fixtures/reflection_ledger/canonical/seal.md]
  forbidden_files: [AGENTS.md, .memory-seed/agent-rules.md, .memory-seed/index.md, .memory-seed/policy.md, docs/CONSTITUTION.md, memory_seed/seed/AGENTS.md, memory_seed/cli.py, memory_seed/mcp_server.py, tests/test_reflection_ledger_integration.py]
  validation: ["python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_session_fuse_and_merge.py", "git diff --check"]
  output_contract: ["Return a committed kernel checkpoint and measured validation; no reflection report/fragment is allowed before the parser exists.", "Do not merge, resolve, promote, or seal."]
  expected_absent: [memory_seed/reflection_ledger.py, tests/test_reflection_ledger.py, tests/fixtures/reflection_ledger/canonical/manifest.yaml, tests/fixtures/reflection_ledger/canonical/report.md, tests/fixtures/reflection_ledger/canonical/fragment.md, tests/fixtures/reflection_ledger/canonical/seal.md]
  acceptance_observables:
    - {name: reflection-kernel-tests, command: "python -X utf8 -m pytest -q tests/test_reflection_ledger.py", expected_exit_code: 0}
    - {name: session-fuse-regression, command: "python -X utf8 -m pytest -q tests/test_session_fuse_and_merge.py", expected_exit_code: 0}
  implements: []
retrieval:
  profile: architecture
  profile_version: 1
  overrides:
    selectors:
      pinned:
        - {kind: decision, id: mse_9c151e4gbkkv1w5v:d1, reason: "branch-session fuse invariant"}
        - {kind: decision, id: mse_dr5eprnhrctqeeg3:d1, reason: "one-step merge primitive"}
    filters: {topics: [session-fuse, git-workflow], paths: [memory_seed/core.py]}
budget: {supplemental_input_tokens: 6000, output_tokens: 5000, over_soft_cap: fail, over_soft_cap_reason: null}
memory_update_policy: orchestrator
~~~

### B. Surfaces and packet contract (reserved evidence pair)

~~~yaml
schema: memory-seed/task-dispatch
version: 1
objective: "Expose the merged reflection-ledger kernel through parity-preserving CLI/MCP surfaces and document the pre-reserved Task Packet evidence contract without creating a dispatcher or durable-session writer."
constitution_refs: [constitution:v1#append-only, constitution:v1#write-surface-parity, constitution:v1#authority, constitution:v1#model-independence]
project_context:
  project_type_and_purpose: "Memory Seed provides one local Markdown authority through CLI/MCP and compiles bounded worker context from semantic dispatches."
  relevant_subsystem: "This track adapts frozen reflection core results to CLI/MCP parity, makes full active agent-rules mandatory in every worker packet, and adds full session-logging plus automatic-clock append guards for session-writing packets."
  task_fit: "Operators need identical valid/error behavior, while workers need pre-reserved evidence paths rather than content-derived output names."
  downstream_use: "Auditors compare surfaces and the orchestrator uses the report/fragment only as evidence, never as an integration shortcut."
  non_goals: ["Do not alter the Task Packet semantic schema.", "Do not write sessions, governance files, manifest, resolution, promotion, or seal."]
execution:
  role: worker
  persona: none
  capability_tier: frontier
  write_intent: writing
  allowed_files: [memory_seed/cli.py, memory_seed/mcp_server.py, memory_seed/task_packet.py, tests/test_reflection_ledger_surfaces.py, tests/test_task_packet.py, .memory-seed/skills/agent_collaboration.md, memory_seed/seed/.memory-seed/skills/agent_collaboration.md, .memory-seed/reflections/archive/reflection-ledger-v1/reports/ledger-surfaces/rpr_01SURFACELEDGER0000001.md, .memory-seed/reflections/archive/reflection-ledger-v1/fragments/surfaces/ledger-surfaces/001-rfl_01SURFACELEDGER00001.md]
  forbidden_files: [AGENTS.md, .memory-seed/agent-rules.md, .memory-seed/index.md, .memory-seed/policy.md, docs/CONSTITUTION.md, tests/test_reflection_ledger.py, tests/test_reflection_ledger_integration.py]
  validation: ["python -X utf8 -m pytest -q tests/test_reflection_ledger_surfaces.py tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_mcp_server.py", "git diff --check"]
  output_contract: ["Return committed CLI/MCP parity and packet-baseline evidence (full active agent-rules; full session-logging/automatic-clock guard where applicable), plus the two pre-reserved report/fragment paths.", "Do not merge, resolve, promote, or seal."]
  expected_absent: [tests/test_reflection_ledger_surfaces.py, .memory-seed/reflections/archive/reflection-ledger-v1/reports/ledger-surfaces/rpr_01SURFACELEDGER0000001.md, .memory-seed/reflections/archive/reflection-ledger-v1/fragments/surfaces/ledger-surfaces/001-rfl_01SURFACELEDGER00001.md]
  acceptance_observables:
    - {name: reflection-surface-parity, command: "python -X utf8 -m pytest -q tests/test_reflection_ledger_surfaces.py", expected_exit_code: 0}
    - {name: task-packet-regression, command: "python -X utf8 -m pytest -q tests/test_task_packet.py tests/test_task_packet_surfaces.py", expected_exit_code: 0}
  implements: []
retrieval:
  profile: implementation
  profile_version: 1
  overrides:
    selectors:
      pinned:
        - {kind: decision, id: mse_dr5eprnhrctqeeg3:d1, reason: "one-step merge primitive"}
        - {kind: decision, id: mse_17d0qqh34a07qp5b:d1, reason: "shared write authority"}
    filters: {topics: [session-fuse, agent-collaboration], paths: [memory_seed/cli.py, memory_seed/mcp_server.py]}
budget: {supplemental_input_tokens: 5000, output_tokens: 4500, over_soft_cap: fail, over_soft_cap_reason: null}
memory_update_policy: orchestrator
~~~

### C. Independent auditor (reserved evidence pair, no product edits)

~~~yaml
schema: memory-seed/task-dispatch
version: 1
objective: "Independently verify the integrated reflection ledger for provenance, collision, coordinated merge, explanatory promotion, and sealed-retention behavior; write only the pre-reserved audit evidence pair."
constitution_refs: [constitution:v1#append-only, constitution:v1#provenance, constitution:v1#markdown-authority, constitution:v1#authority]
project_context:
  project_type_and_purpose: "Memory Seed retains attributable project reasoning as local Markdown while integration tools fail closed on malformed concurrent history."
  relevant_subsystem: "The auditor exercises merged kernel/surfaces, coordinated fuse receipts, session-promotion boundary, and archive seal without owning product code."
  task_fit: "Cross-worktree collision, post-merge bypass, and Ada's missing-rules/session-logging plus future-timestamp incident require an independent integrated-tree verdict and attributable evidence handoff."
  downstream_use: "The orchestrator uses the verdict for bounded rework or promotion/seal; the auditor cannot perform either action."
  non_goals: ["Do not edit implementation, tests, control-plane, seed, session, manifest, resolution, promotion, or seal.", "Do not equate packet compilation with implementation correctness."]
execution:
  role: validator
  persona: none
  capability_tier: frontier
  write_intent: writing
  allowed_files: [.memory-seed/reflections/archive/reflection-ledger-v1/reports/ledger-auditor/rpr_01AUDITLEDGER00000001.md, .memory-seed/reflections/archive/reflection-ledger-v1/fragments/verification/ledger-auditor/001-rfl_01AUDITLEDGER000001.md]
  forbidden_files: [AGENTS.md, .memory-seed/agent-rules.md, .memory-seed/index.md, .memory-seed/policy.md, docs/CONSTITUTION.md, memory_seed/reflection_ledger.py, memory_seed/core.py, memory_seed/cli.py, memory_seed/mcp_server.py, tests/test_reflection_ledger.py, tests/test_reflection_ledger_surfaces.py, tests/test_reflection_ledger_integration.py]
  validation: ["python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_reflection_ledger_integration.py tests/test_reflection_ledger_surfaces.py tests/test_session_fuse_and_merge.py tests/test_task_packet.py tests/test_task_packet_surfaces.py", "python -X utf8 -m memory_seed.cli docs check", "python -X utf8 -m memory_seed.cli docs index --check", "git diff --check"]
  output_contract: ["Return committed PASS, FAIL, or NEEDS_CONTEXT audit evidence at the two reserved paths with exact command results, including Ada's missing full agent-rules/session-logging and future-timestamp finding.", "State separately what was tested, inferred, and still requires live orchestrator action; do not merge, promote, or seal."]
  expected_absent: [.memory-seed/reflections/archive/reflection-ledger-v1/reports/ledger-auditor/rpr_01AUDITLEDGER00000001.md, .memory-seed/reflections/archive/reflection-ledger-v1/fragments/verification/ledger-auditor/001-rfl_01AUDITLEDGER000001.md]
  acceptance_observables:
    - {name: integrated-reflection-suite, command: "python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_reflection_ledger_integration.py tests/test_reflection_ledger_surfaces.py", expected_exit_code: 0}
    - {name: documentation-lifecycle, command: "python -X utf8 -m memory_seed.cli docs check", expected_exit_code: 0}
  implements: []
retrieval:
  profile: architecture
  profile_version: 1
  overrides:
    selectors:
      pinned:
        - {kind: decision, id: mse_9c151e4gbkkv1w5v:d1, reason: "branch-session fuse invariant"}
        - {kind: decision, id: mse_17d0qqh34a07qp5b:d1, reason: "shared write authority"}
    filters: {topics: [session-fuse, agent-collaboration], paths: [tests/test_session_fuse_and_merge.py, memory_seed/core.py]}
budget: {supplemental_input_tokens: 5000, output_tokens: 4500, over_soft_cap: fail, over_soft_cap_reason: null}
memory_update_policy: orchestrator
~~~

### Measured draft compilation

The pre-commit verification must compile all three blocks from this checkout with the compiler-measured
binding for the target branch/worktree and main base. This table records its exact fingerprints, evidence
counts, and token ledger. A compile failure blocks the plan; no hand-edited packet is an alternative.

| Draft | Result | Dispatch fingerprint | Evidence / tokens |
| --- | --- | --- | --- |
| Kernel bootstrap | compiled 2026-09-06 | `sha256:32e0ae2a830b611759c149ba29d0e97e7931ec7f837960ee9296d21d2d8108f6` | 36 materialized; input 31,584; envelope 36,584; within target |
| Surfaces | compiled 2026-09-06 | `sha256:bf327eaf43fb859bda5a5aa1c6544792b0426573e22c5dede2ba88682f779681` | 9 materialized; input 15,200; envelope 19,700; within target |
| Auditor | compiled 2026-09-06 | `sha256:51447a6ee022c81ec470b797f9ef87dc7ac643075d6e727f4dcab026745e6292` | 34 materialized; input 29,500; envelope 34,000; within target |

The current compiler lacks the planned `baseline_agent_rules` and `session_logging_guard` ledger components;
these successful compiles are the pre-change baseline, not evidence that the new governance behavior already
exists. The Surface track must add component-level assertions and remeasure all three drafts after it lands.

## Migration, compatibility, and explicit non-goals

There is no migration or backfill. Existing sessions, diagrams, links, topics, ADRs, Task Packets, and
experiment reflection logs retain their current readers and semantics. The first ledger is an opt-in pilot
with no automatic initialization and no change to `memory-seed init` or seed payloads. A completed pilot is
sealed in its canonical archive while promoted session lessons carry reusable explanation. Any later decision
to make the family reusable across projects, include it in retrieval, add native Task Dispatch schema, or add
a server/sync layer needs separate evidence and a new proposal.

Known risks to hold visible during implementation:

- Cleanup can look like history deletion; seal retention, promotion receipt, and archive byte immutability
  must be testable and visible in preview.
- Reporting fields can become decorative. Negative controls must prove wrong branch/base/source-tip/blob/path
  provenance blocks fusion.
- A common view can accidentally become an authority projection. Tests must assert it retains dissent and
  does not expose a winner/effective decision field.
- The format cannot be introduced and used on one branch; parser/CLI/MCP capability lands before any ledger
  data, just as session/ADR fuse rules require.
- Reflection reports may include private worker details. Treat sealed archive evidence as potentially
  publishable, write minimally, and promote only sanitized reusable lessons.

## Review checkpoint

The plan is ready for independent review when the reviewer can answer yes to all of these:

1. Reflection storage is distinct from durable sessions and has a bounded active lifecycle with a retained,
   sealed archive.
2. Every writer is manifest-authorized and every fragment is traceable to a committed, binding-matched
   report.
3. The fuse blocks unsafe state before merge/apply, while the common view exposes disagreement rather than
   manufacturing consensus.
4. Resolution/promotion/seal remain orchestrator-only, and promotion uses ordinary session safeguards and
   retains an explanatory durable rationale.
5. Task Packet drafts compile from pre-reserved exact paths/IDs plus measured binding; no hidden
   dispatch, worktree, provider, or authority feature is implied.
