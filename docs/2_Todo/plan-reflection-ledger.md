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
  - "Retirement removes only a completed temporary plan family after all promoted lessons are evidenced; no durable session, ADR, policy, index, or seed artifact is deleted or rewritten."
---

# Plan-scoped reflection ledger

## Outcome and decision

Create a narrowly scoped reflection facility for a single approved plan. It collects independent worker
opinions and first-hand handoff evidence while the plan is active, then disappears after the orchestrator
has resolved the plan and selectively promoted reusable lessons into normal append-only sessions.

This is deliberately not a second session layout. Durable sessions remain the chronological rationale
authority. The reflection ledger is temporary coordination evidence: it is Markdown while live, is fused
with the same fail-closed principles as sessions, is visible to humans and agents through a derived common
view, and is not discovered by ordinary memory retrieval. A lesson becomes durable only through the
existing guarded session writer and an explicit orchestrator promotion record.

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
| `memory_seed/cli.py` and `memory_seed/mcp_server.py` | Mirror existing parser/handler and structured-preview conventions; preserve CLI/MCP canonical-result parity. | MCP read operations are inline and non-mutating; any writer calls the same core validation used by CLI. No MCP operation merges a branch or retires a ledger without the same gates as CLI. |
| `.memory-seed/skills/agent_collaboration.md` and the Seed twin | Reuse Task Packet ownership, clean-session, worktree, worker-checkpoint, final-handoff, and serial-integration rules. | Extend the runbook only after core behavior passes tests; a reflection fragment is not a worker permission to write a durable session. |
| `experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md` | Preserve its useful dimensions: source coverage, authority fidelity, extra-hop classification, scope accuracy, exact receipts, and independently reviewed limitations. | It remains an experiment-specific log. The plan ledger is not a general-purpose replacement for it. |

## Plan family, storage, and lifecycle

The active family is under a distinct directory, never under `sessions/`:

```text
.memory-seed/reflections/<plan_id>/
  manifest.yaml                         # created/changed only by the orchestrator before dispatch
  reports/<participant>/<report_id>.json # immutable worker handoff receipts
  fragments/<track>/<participant>/<sequence>-<fragment_id>.md
  view.json                             # optional ignored/exported derived view; never authoritative
```

`<plan_id>` is a lower-case, collision-checked identifier allocated by `reflection init`; the reviewed
first plan reserves `reflection-ledger-v1`. The manifest is committed before worker dispatch and includes:

```yaml
schema: memory-seed/reflection-plan
version: 1
plan_id: reflection-ledger-v1
base_branch: main
base_sha: <40-character resolved SHA>
retention: temporary
orchestrator:
  participant: codex-orchestrator
  branch: codex/feature/reflection-ledger-integration
participants:
  - participant: ledger-kernel
    role: worker
    branch: codex/feature/reflection-ledger-kernel
    track: kernel
    fragment_prefix: fragments/kernel/ledger-kernel/
    report_prefix: reports/ledger-kernel/
    allowed_kinds: [observation, opinion, risk, correction]
  - participant: ledger-surfaces
    role: worker
    branch: codex/feature/reflection-ledger-surfaces
    track: surfaces
    fragment_prefix: fragments/surfaces/ledger-surfaces/
    report_prefix: reports/ledger-surfaces/
    allowed_kinds: [observation, opinion, risk, correction]
  - participant: codex-orchestrator
    role: orchestrator
    branch: codex/feature/reflection-ledger-integration
    track: integration
    fragment_prefix: fragments/integration/codex-orchestrator/
    report_prefix: reports/codex-orchestrator/
    allowed_kinds: [observation, opinion, risk, correction, resolution, promotion, retirement]
```

The manifest is immutable while workers run. Adding a participant, changing a branch, or changing a prefix
is a new serial orchestrator amendment with a new manifest digest and an explicit re-dispatch; a worker may
never self-enrol or broaden its file ownership. The plan family is ignored by retrieval, session-target
resolution, compacting, links checks, ADR membership, and seed initialization unless an explicit reflection
command is invoked.

Lifecycle:

1. **Initialize.** Orchestrator creates, validates, commits, and distributes the manifest; the plan ID,
   base SHA, participant roster, manifest SHA-256, and per-worker output prefixes enter each Task Packet.
2. **Collect.** Each worker writes one or more immutable report/fragment pairs in its own branch and commits
   them with its implementation checkpoint. A later thought is a new fragment, never an edit.
3. **Preview and fuse.** From the integration tree, the orchestrator runs the reflection fuse against one
   worker branch at a time before applying the standard branch integration sequence.
4. **Resolve and promote.** The orchestrator writes only its resolution/promotion fragment. It promotes
   reusable conclusions promptly through ordinary `session append`; promotion does not wait for plan close.
5. **Retire.** Once all fragments are fused, the resolution is complete, and every promotion record names a
   durable session entry or declares `disposition: not-promoted`, the orchestrator runs guarded retirement.
   Retirement removes the entire temporary plan family from the integration tree in one explicit operation.
   It does not remove worker commits, durable session entries, or their Git history.

Temporary retention is intentional rather than a loophole in append-only history: the manifest labels the
family `temporary`, it is excluded from durable-memory readers, and promotion preserves every lesson judged
reusable before deletion. A retire command refuses a non-temporary family, an unresolved plan, an unfused
known participant branch, a missing disposition, or an unverified promotion target.

## Fragment and report schema

### Report receipt

Each worker commits a canonical JSON report before or with its fragment. It is evidence for the fragment,
not a claim that the report itself is accepted:

```json
{
  "schema": "memory-seed/reflection-report",
  "version": 1,
  "report_id": "rpr_<80-bit-crockford-id>",
  "plan_id": "reflection-ledger-v1",
  "participant": "ledger-kernel",
  "track": "kernel",
  "working_branch": "codex/feature/reflection-ledger-kernel",
  "base_sha": "<manifest base SHA>",
  "head_sha": "<source branch commit containing this report and fragment>",
  "task_packet_fingerprint": "sha256:<compiled-packet-fingerprint>",
  "validation": [{"command": "...", "exit_code": 0}],
  "status": "DONE|DONE_WITH_CONCERNS|BLOCKED",
  "created_at": "RFC3339 UTC"
}
```

The fuse checks the report is canonical UTF-8 JSON, lies under the participant's prefix, has a stable ID,
matches the manifest plan/participant/track/branch/base, is present in the source commit, and is cited by
at least one fragment. `head_sha` must resolve to the source branch and be an ancestor of the source tip;
the packet fingerprint is format-checked and is required for writing-packet tracks. This is provenance, not
cryptographic attestation: a repository writer can alter local files, so the fuse proves consistency and
traceability rather than adversarial security.

### Fragment

Fragments are Markdown with a timestamped heading and a canonical YAML envelope. The fragment ID is an
80-bit Crockford-base32 digest of `plan_id`, participant, branch, sequence, timestamp, and the canonical
record envelope; `reflection append --dry-run` mints it and renders the exact bytes. Record IDs are derived
from fragment ID plus record ordinal and kind. No caller invents either ID.

```markdown
## 2026-09-06T12:34:56Z - Kernel fuse review

```yaml
schema: memory-seed/reflection-fragment
version: 1
fragment_id: rfl_<80-bit-crockford-id>
plan_id: reflection-ledger-v1
participant: ledger-kernel
track: kernel
working_branch: codex/feature/reflection-ledger-kernel
sequence: 1
source: write-time
report_id: rpr_<80-bit-crockford-id>
report_sha256: <sha256-of-exact-report-bytes>
base_sha: <manifest base SHA>
```

### R1 - Separate the temporary parser from session discovery

```yaml
record_id: rlr_<80-bit-crockford-id>
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
| `retirement` | no | yes | Declares every fragment/report disposition and the successful retirement preconditions. |

Every record carries a stable ID, explicit subject, source (`write-time` or `derived`), and report provenance
unless it is an orchestrator resolution, promotion, or retirement. Corrections must target an earlier record
from the same participant; they cannot erase it, alter another participant's evidence, or turn an opinion
into a resolution. A derived record may fill a missing statement but never silently override a write-time
record; an attempted override requires a correction citing the exact prior record and resolution evidence.

## Reflection fuse and common-view behavior

`reflection fuse` follows the session-fuse phases but accepts only the reflection family for its named plan:

1. Resolve source/base commits and calculate the three-dot changed paths.
2. Require an identical, base-established manifest; reject source manifest edits, foreign plan families, and
   files outside the declaring participant's prefixes.
3. Parse all changed reports and fragments strictly as UTF-8. Reject malformed envelopes, invalid dates,
   unknown record kinds, noncanonical IDs, unmatched paths, report digest mismatch, mismatched base/branch,
   missing source report, invalid report ancestry, duplicate IDs, and duplicate `(participant, sequence)`.
4. Compare against every base and already-admitted plan record. Existing IDs must have byte-identical text;
   a changed byte is an immutable-history refusal. An identical retry is `already_present`, while two source
   records with the same ID or sequence are a collision and block.
5. Validate correction targets, participant ownership, correction ordering, and source/recency precedence.
   Validate resolution/promotion/retirement authority against the manifest role, including referenced record
   IDs and session entry IDs where they exist.
6. Produce a sorted plan keyed by `(created_at, participant, sequence, fragment_id, record_ordinal)`. The
   `--apply` route writes only during the controlled integration operation, regenerating canonical target
   files from parsed records rather than accepting a text merge.

`reflection view --plan <id>` consumes the same parsed records and returns a deterministic, read-only common
view: raw records, source/report fields, correction chains, unresolved risks, resolutions, promotions, and
participant coverage. It may group a subject and show the latest statement within each provenance class, but
it must show all source records and label the grouping as derived. It never picks a majority, synthesizes a
new conclusion, or treats agreement as authority.

## CLI, MCP, and orchestration surfaces

| Surface | Operation | Write policy |
| --- | --- | --- |
| CLI | `memory-seed reflection init --manifest-file …` | Orchestrator-only; validates plan identity and roster, writes the initial manifest. |
| CLI | `reflection append --report-file … --fragment … [--dry-run]` | Checks worktree guard, manifest membership, exact path ownership, report digest, sequence, IDs, and append-only file state. Dry run returns rendered bytes and IDs. |
| CLI | `reflection check --plan`, `reflection view --plan`, `reflection fuse --plan --branch [--apply]` | Check/view/preview are read-only. Apply uses the integration/merge gate and emits planned imports, `already_present`, and issues. |
| CLI | `reflection retire --plan --apply` | Orchestrator-only, explicit, blocked until resolution/dispositions/promotions are validated; reports every removed temporary path. |
| MCP | `memory_reflection_view`, `memory_reflection_fuse_preview` | Read-only projections with the same result schema as CLI preview. |
| MCP | `memory_reflection_append`, `memory_reflection_retire` | Added only with CLI parity tests; call the identical core validators, never direct file writes. Retire remains subject to the same integration/merge and live-approval checks. |
| Orchestrator | Task Packet compile + worker handoff | Compiles exact output paths and report contract into each worker packet; checks packet binding and report receipt before trusting a handoff; owns resolution, promotion, integration, and retirement. |

No new dispatch engine is introduced. The orchestrator still creates worktrees, assigns branches, compiles
packets, and integrates serially. The ledger gives that existing flow a temporary evidence channel; it never
dispatches a worker by itself.

## Authority, promotion, and retirement rules

- Workers can state only first-hand observations, opinions, risks, and corrections within their assigned
  prefix. They cannot resolve a cross-track disagreement, promote a lesson, modify the manifest, change
  another participant's record, integrate, or retire the plan.
- The orchestrator's `resolution` names the considered record IDs, the chosen conclusion, the rejected or
  deferred alternatives, and any remaining risk owner. It never rewrites a worker's prose.
- Promotion is selective and happens during the plan. The orchestrator uses ordinary `session append` / MCP
  append with normal chronology, DRAFT, topic, linkage, ADR-review, and branch guards. Its session body
  states the plan ID and source fragment/record IDs in `F:` or `A:` prose; the matching promotion record
  stores the resulting session `entry_id` plus the exact durable decision reference where one exists.
- A promotion is not automatic consolidation. One-off status, duplicate opinion, transient debugging,
  personal data, and unresolved disagreement are explicitly `not-promoted` with a concise disposition.
- Retirement is an explicit cleanup of scratch, not an archival rewrite. It is allowed only after the
  retirement record covers every admitted fragment/report, all required durable promotions resolve, and no
  unresolved resolution remains. Git history retains the pre-retirement plan for audit; runtime readers no
  longer see a completed plan family in the working tree.

## Delivery sequence and ownership

### Serial foundation

1. Add `memory_seed/reflection_ledger.py` with canonical schemas, ID generation, strict parsers/renderers,
   manifest/report/fragment validators, common-view projection, and a fuse-plan/result model. Extract only
   genuinely neutral Git/ref-diff helpers from `core.py` if reuse cannot stay internal without circular
   imports.
2. Add `reflection` CLI routes and core integration sequencing. Add `.gitattributes` protection for the
   temporary reflection family so a raw line merge fails rather than fabricates a valid-looking record.
3. Add the read-only MCP preview/view surfaces. Add writers only after the shared validator and CLI behavior
   are fully covered.

### Parallel tracks after the foundation lands

| Track | Owned files | Deliverable | Dependency |
| --- | --- | --- | --- |
| Kernel fuse | `memory_seed/reflection_ledger.py`, minimal shared `memory_seed/core.py` helper extraction, `.gitattributes`, `tests/test_reflection_ledger.py` | Schema, parser, IDs, report validation, view, preview/apply fuse, retirement preconditions. | Foundation base only. |
| Surfaces and packets | `memory_seed/cli.py`, `memory_seed/mcp_server.py`, `tests/test_reflection_ledger_surfaces.py`, packet/worker documentation and its Seed twin | CLI/MCP parity, packet-output contract examples, orchestrator handoff validation. | Kernel API frozen. |
| Integration and adversarial verification | New fixture helpers plus `tests/test_reflection_ledger_integration.py`; narrowly scoped additions to merge/fuse surface tests | Multi-worktree simulation, branch merge sequencing, cleanup/retirement, negative controls, stable observations. | Kernel + surfaces heads merged into an integration branch. |

The orchestrator owns `.memory-seed/reflections/<plan_id>/manifest.yaml`, the integration fragment, branch
ordering, resolution/promotion, durable session appends, and retirement. No worker owns shared control-plane
files, dependency files, existing sessions, ADRs, policy, index, or seed files unless a later packet explicitly
creates a non-overlapping documentation track. Validators remain read-only and review the integrated diff.

### Serial integration

1. Merge the format/parser foundation before any branch contains reflection data; this preserves the existing
   rule that a fuse cannot parse a format introduced on the same unmerged branch.
2. Compile packets from the frozen manifest and dispatch independent tracks to distinct worktrees.
3. Require each worker to commit implementation, report, and fragment before review. Validate its base/head,
   report receipt, owned paths, and `reflection fuse --dry-run` output.
4. Integrate one branch at a time with the standard one-step branch flow plus reflection fuse; rerun targeted
   checks after each merge. No octopus merge and no raw conflict resolution for reflection paths.
5. Have an independent validator review the integrated behavior and negative controls. Route rework to the
   owning worker up to the existing bounded review-loop limit.
6. The orchestrator writes resolution/promotion records, runs ordinary session promotion, validates retirement,
   removes the temporary family, then validates the integrated tree again.

## Test matrix and acceptance observables

| Area | Required proof |
| --- | --- |
| Manifest and ownership | Unknown/duplicate participant, changed manifest, foreign plan, wrong branch/base/track/prefix, a worker writing an orchestrator kind, and an orchestrator resolution missing cited records all refuse. |
| IDs and chronology | Deterministic dry-run IDs; malformed/forged IDs; duplicate source ID; base collision same bytes=`already_present`; base collision changed bytes=refusal; duplicate sequence; out-of-order fragment/record; invalid UTF-8. |
| Report provenance | Missing report, wrong digest, wrong plan/participant/branch/base, report outside prefix, unresolved/nonancestor head, malformed packet fingerprint, and uncited report all refuse. |
| Corrections and derived view | Correction cannot edit or target another participant; original and correction remain visible; derived cannot outrank write-time without explicit correction; view ordering and JSON/Markdown output are deterministic; disagreement is visible rather than collapsed. |
| Fuse application | Preview has no filesystem mutation; apply requires the controlled integration state; raw reflection merge conflict is not hand-resolved; target files are rebuilt canonically; re-run is idempotent; source removals and rollback/abort preserve a clean tree. |
| CLI/MCP parity | Same valid rendered fragment/result and same structured errors from both paths; MCP read surfaces are non-mutating; unsupported output/file arguments fail closed; no writer bypasses core validation. |
| Task Packet integration | Exact worker paths, expected absent paths, report requirement, preflight, validation, and handoff are materialized; stale binding blocks; packet evidence is not refetched; compile preview/CLI/MCP packet parity remains unchanged. |
| Promotion and retirement | Promotion requires an existing ordinary session entry and exact source record; a missing/invalid promotion blocks retirement; `not-promoted` needs a disposition; retirement removes only the declared temporary family; sessions/ADRs/index/policy are byte-identical; a retired plan is unreadable by reflection view. |
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

These are semantic Task Dispatch v1 drafts, not hand-authored complete packets. Before compilation, the
orchestrator replaces only the declared plan/branch/path placeholders from the committed manifest, measures
the binding, pins the current corpus revision through the compiler, and verifies the packet. A placeholder
remaining after that substitution is a refusal. `execution.implements` stays empty deliberately: this is a
new capability, not implementation of an already selected decision; the plan and Constitution clauses are
the materialized governing evidence.

### A. Kernel fuse track

```yaml
schema: memory-seed/task-dispatch
version: 1
objective: "Implement the temporary plan-scoped reflection ledger kernel: canonical manifest/report/fragment parsing, stable IDs, guarded preview/apply fusion, derived common view, and retirement preconditions without admitting reflections to sessions or retrieval."
constitution_refs:
  - constitution:v1#append-only
  - constitution:v1#write-surface-parity
  - constitution:v1#provenance
  - constitution:v1#markdown-authority
project_context:
  project_type_and_purpose: "Memory Seed is a local-first, Markdown-authoritative memory substrate. Git supplies branch topology while core validators preserve readable, attributable records without a service or database."
  relevant_subsystem: "The kernel reuses session-fuse safety mechanics but creates a separate temporary reflection family, parser, renderer, and deterministic view. Durable sessions remain the only chronological rationale ledger."
  task_fit: "Parallel worker reflections need provenance, ownership, collision, correction, and chronology guards before an orchestrator can inspect or integrate them. A raw Git text merge cannot prove those properties."
  downstream_use: "CLI, MCP, Task Packets, orchestrators, reviewers, and tests consume the kernel result. The result permits bounded temporary coordination evidence, not autonomous dispatch or durable-memory writes."
  non_goals:
    - "Do not modify session discovery, ordinary retrieval, ADR authority, or historical session files."
    - "Do not add a database, network service, merge driver, or worker dispatch engine."
execution:
  role: worker
  persona: none
  capability_tier: frontier
  write_intent: writing
  allowed_files:
    - memory_seed/reflection_ledger.py
    - memory_seed/core.py
    - .gitattributes
    - tests/test_reflection_ledger.py
    - tests/test_reflection_ledger_integration.py
  forbidden_files:
    - AGENTS.md
    - .memory-seed/agent-rules.md
    - .memory-seed/index.md
    - .memory-seed/policy.md
    - docs/CONSTITUTION.md
    - memory_seed/seed/AGENTS.md
  validation:
    - "python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_reflection_ledger_integration.py tests/test_session_fuse_and_merge.py"
    - "git diff --check"
  output_contract:
    - "Return committed implementation, a source-provenanced reflection report/fragment, exact head SHA, and all negative-control results."
    - "Do not resolve cross-track behavior, promote sessions, integrate branches, or retire the ledger."
  expected_absent:
    - memory_seed/reflection_ledger.py
    - tests/test_reflection_ledger.py
    - tests/test_reflection_ledger_integration.py
  acceptance_observables:
    - name: reflection-kernel-tests
      command: "python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_reflection_ledger_integration.py"
      expected_exit_code: 0
    - name: session-fuse-regression
      command: "python -X utf8 -m pytest -q tests/test_session_fuse_and_merge.py"
      expected_exit_code: 0
  implements: []
retrieval:
  profile: architecture
  profile_version: 1
  overrides:
    filters:
      paths:
        - docs/2_Todo/plan-reflection-ledger.md
        - memory_seed/core.py
budget:
  supplemental_input_tokens: 6000
  output_tokens: 5000
  over_soft_cap: fail
  over_soft_cap_reason: null
memory_update_policy: orchestrator
```

### B. Surfaces and Task Packet track

```yaml
schema: memory-seed/task-dispatch
version: 1
objective: "Expose the reviewed reflection-ledger kernel through parity-preserving CLI and MCP surfaces, and document exact Task Packet worker output/report contracts without adding a new dispatch engine or durable-session writer."
constitution_refs:
  - constitution:v1#append-only
  - constitution:v1#write-surface-parity
  - constitution:v1#authority
  - constitution:v1#model-independence
project_context:
  project_type_and_purpose: "Memory Seed offers local CLI/MCP tools over one Markdown authority. Its Task Packet compiler reconstructs measured, bounded worker context from semantic dispatches and immutable profiles."
  relevant_subsystem: "This track adapts the finished reflection kernel into explicit read and guarded write surfaces, then teaches orchestrators how existing Task Packet fields carry reflection output ownership and report evidence."
  task_fit: "Workers need a single validated path on either CLI or MCP, and orchestrators need a compact packet contract that prevents a fragment from becoming an unauthorized session or integration action."
  downstream_use: "Clean-session workers receive compiled packets; operators inspect previews; validators compare CLI/MCP results; the orchestrator remains responsible for resolution, session promotion, branch integration, and retirement."
  non_goals:
    - "Do not alter Task Dispatch v1 schema or build provider/network/worker dispatch features."
    - "Do not write sessions, ADRs, policy, index, seed files, or plan manifests from this worker."
execution:
  role: worker
  persona: none
  capability_tier: frontier
  write_intent: writing
  allowed_files:
    - memory_seed/cli.py
    - memory_seed/mcp_server.py
    - tests/test_reflection_ledger_surfaces.py
    - .memory-seed/skills/agent_collaboration.md
    - memory_seed/seed/.memory-seed/skills/agent_collaboration.md
  forbidden_files:
    - AGENTS.md
    - .memory-seed/agent-rules.md
    - .memory-seed/index.md
    - .memory-seed/policy.md
    - docs/CONSTITUTION.md
    - memory_seed/task_packet.py
  validation:
    - "python -X utf8 -m pytest -q tests/test_reflection_ledger_surfaces.py tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_mcp_server.py"
    - "git diff --check"
  output_contract:
    - "Return committed CLI/MCP parity evidence, a source-provenanced reflection report/fragment, and exact packet-output-contract documentation changes."
    - "Do not merge, resolve, promote durable lessons, or retire a plan family."
  expected_absent:
    - tests/test_reflection_ledger_surfaces.py
  acceptance_observables:
    - name: reflection-surface-parity
      command: "python -X utf8 -m pytest -q tests/test_reflection_ledger_surfaces.py"
      expected_exit_code: 0
    - name: task-packet-regression
      command: "python -X utf8 -m pytest -q tests/test_task_packet.py tests/test_task_packet_surfaces.py"
      expected_exit_code: 0
  implements: []
retrieval:
  profile: implementation
  profile_version: 1
  overrides:
    filters:
      paths:
        - docs/2_Todo/plan-reflection-ledger.md
        - memory_seed/cli.py
        - memory_seed/mcp_server.py
budget:
  supplemental_input_tokens: 5000
  output_tokens: 4500
  over_soft_cap: fail
  over_soft_cap_reason: null
memory_update_policy: orchestrator
```

### C. Independent integration/retirement verifier

```yaml
schema: memory-seed/task-dispatch
version: 1
objective: "Independently verify the integrated reflection-ledger implementation with a multi-worktree fixture, adversarial provenance and collision cases, ordinary-session promotion proof, and temporary-ledger retirement proof; return findings without editing product code."
constitution_refs:
  - constitution:v1#append-only
  - constitution:v1#provenance
  - constitution:v1#markdown-authority
  - constitution:v1#authority
project_context:
  project_type_and_purpose: "Memory Seed preserves project reasoning as local Markdown with attribution. Integration tools must reject malformed concurrent history rather than silently produce a plausible but corrupt result."
  relevant_subsystem: "The verifier exercises the reflection fuse, derived view, Task Packet receipts, session promotion boundary, and retirement preconditions only after the kernel and surfaces are integrated on the named review branch."
  task_fit: "The highest risks are cross-branch collision, unauthorized resolution, false report provenance, accidental session inclusion, and deletion of unpromoted evidence. These require an independent integrated-tree read, not worker self-review."
  downstream_use: "The orchestrator consumes a source-linked verdict to decide bounded rework or completion. The verifier has no authority to merge, promote, retire, or amend the plan manifest."
  non_goals:
    - "Do not edit implementation, control-plane, seed, session, or ledger files."
    - "Do not infer that passing packet compilation proves worker correctness or durable promotion quality."
execution:
  role: validator
  persona: none
  capability_tier: frontier
  write_intent: read-only
  allowed_files: []
  forbidden_files: []
  validation:
    - "python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_reflection_ledger_integration.py tests/test_reflection_ledger_surfaces.py tests/test_session_fuse_and_merge.py tests/test_task_packet.py tests/test_task_packet_surfaces.py"
    - "python -X utf8 -m memory_seed.cli docs check"
    - "python -X utf8 -m memory_seed.cli docs index --check"
    - "git diff --check"
  output_contract:
    - "Return a read-only PASS, FAIL, or NEEDS_CONTEXT verdict with exact command results and source locations for every finding."
    - "State separately what was directly tested, what was inferred, and whether retirement/promotion needs live orchestrator action."
  expected_absent: []
  acceptance_observables:
    - name: integrated-reflection-suite
      command: "python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_reflection_ledger_integration.py tests/test_reflection_ledger_surfaces.py"
      expected_exit_code: 0
    - name: documentation-lifecycle
      command: "python -X utf8 -m memory_seed.cli docs check"
      expected_exit_code: 0
  implements: []
retrieval:
  profile: architecture
  profile_version: 1
  overrides:
    filters:
      paths:
        - docs/2_Todo/plan-reflection-ledger.md
budget:
  supplemental_input_tokens: 5000
  output_tokens: 4500
  over_soft_cap: fail
  over_soft_cap_reason: null
memory_update_policy: orchestrator
```

## Migration, compatibility, and explicit non-goals

There is no migration or backfill. Existing sessions, diagrams, links, topics, ADRs, Task Packets, and
experiment reflection logs retain their current readers and semantics. The first ledger is an opt-in pilot
with no automatic initialization and no change to `memory-seed init` or seed payloads. A completed pilot may
be retired, leaving only promoted session lessons and ordinary Git history. Any later decision to make the
family reusable across projects, include it in retrieval, retain an archive, add native Task Dispatch schema,
or add a server/sync layer needs separate evidence and a new proposal.

Known risks to hold visible during implementation:

- Temporary cleanup can look like history deletion; the manifest classification, promotion receipt, and
  guarded retirement preconditions must be testable and visible in dry run.
- Reporting fields can become decorative. Negative controls must prove wrong branch/base/head/digest/path
  claims block fusion.
- A common view can accidentally become an authority projection. Tests must assert it retains dissent and
  does not expose a winner/effective decision field.
- The format cannot be introduced and used on one branch; parser/CLI/MCP capability lands before any ledger
  data, just as session/ADR fuse rules require.
- Reflection reports may include private worker details. Treat them as potentially publishable while live and
  promote only sanitized, reusable lessons.

## Review checkpoint

The plan is ready for independent review when the reviewer can answer yes to all of these:

1. Reflection storage is distinct from durable sessions and has a bounded deletion lifecycle.
2. Every writer is manifest-authorized and every fragment is traceable to a committed, binding-matched
   report.
3. The fuse blocks unsafe state before merge/apply, while the common view exposes disagreement rather than
   manufacturing consensus.
4. Resolution/promotion/retirement remain orchestrator-only, and promotion uses ordinary session safeguards.
5. Task Packet drafts can be rendered with only manifest substitution plus measured binding; no hidden
   dispatch, worktree, provider, or authority feature is implied.
