---
title: "Plan-Scoped Reflection Ledger"
date: "2026-09-06"
project: "memory-seed"
status: "replaced"
superseded_by: "docs/2_Todo/reflection-ledger-workstream-evolution-plan.md"
priority: "P1"
next_action: "Documentary evidence only. Do not compile or launch these prototype dispatches; use the sequential Reflection Board v1 and complete prototype-retirement plans."
source:
  - "docs/CONSTITUTION.md"
  - ".memory-seed/skills/agent_collaboration.md"
  - ".memory-seed/skills/session_logging.md"
  - "experiments/seed-pod-task-packet-evaluation/REFLECTION_LOG.md"
  - "docs/2_Todo/task-packet-hardening-progressive-provenance-plan.md"
scope: "Add a plan-scoped, multi-writer reflection board with a guarded fuse, topic-aware active retrieval, timely promotion into ordinary sessions, embedded durable receipts, and automatic configured expiry of complete chains."
non_goals:
  - "Do not place active reflection records in .memory-seed/sessions/ or alter past session history."
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
  - "Each reflection starts with a concise conclusion and carries enough reasoning, assumptions, uncertainty, and alternatives for another worker to challenge or refine it without reconstructing the author's work."
  - "End-of-turn identifies reflection chains whose conclusions the turn used; after required validation, the orchestrator synthesizes the relevant implementer, reviewer, and orchestrator reflections before promoting and closing each accepted chain. ESR catches unresolved or missed candidates without making the durable judgment automatically."
  - "Promoted conclusions become compact ordinary Memory Seed decisions containing embedded reflection receipts; non-promoted dispositions are embedded in the ESR session entry, so no separate authoritative receipt sidecar is introduced."
  - "After the configurable retention window (seven days by default), the next sanctioned cleanup automatically removes each eligible chain individually without breaking durable references; only early deletion of an unpromoted chain requires live user approval."
---

# Plan-scoped reflection ledger

> Replaced 2026-09-07. This document records the unused participant-fragment prototype, which
> never created a real board in the inspected repository. Historical version labels below are
> documentary evidence, not supported product versions. All remaining implementation is owned by the
> [Reflection Board v1 workstream plan](../2_Todo/reflection-ledger-workstream-evolution-plan.md) and
> [complete prototype retirement plan](../2_Todo/reflection-prototype-retirement-plan.md).
> Embedded dispatches below are inactive and must not be launched.

## Outcome and decision

Create a narrowly scoped reflection facility for a single approved plan. It collects independent worker
reasoning while the plan is active, lets overlapping tracks challenge and refine the working proposal, and
uses ESR to promote only reusable conclusions into normal append-only sessions. The active board is working
memory, not a second permanent memory corpus.

This is deliberately not a second session layout. Durable sessions remain the chronological rationale
authority. The reflection board is temporary coordination material: it is Markdown/YAML while live, is fused
with fail-closed identity and ownership checks, is visible through a derived common view, and is excluded from
ordinary memory retrieval. A lesson becomes durable only through the existing guarded session writer after
orchestrator judgment. Promotion occurs at the end of the first turn that adopts the conclusion rather than
waiting for ESR. A chain may produce several decisions and a decision may synthesize several chains. Compact
receipts are embedded with every resulting decision; a chain that expires without promotion gets its receipt
in the ESR closeout entry. A rebuildable derived index
may collect those receipts for lookup, but it owns no truth.

Temporary detail uses `reflection_retention_days`, a user-configurable project setting that defaults to seven
days. A chain cannot expire while open. After required validation and orchestrator synthesis, its successful
chain-level close records `closed_at`; `expires_at` is that timestamp plus the configured window. At or
after that timestamp the next sanctioned cleanup automatically removes that chain, never the whole board.
Early deletion of an unpromoted chain requires live user approval and a durable disposition; ordinary expiry
does not. Git history may still retain earlier committed blobs, so this is active-state cleanup rather than a
promise of privacy-grade erasure. Any hard-erasure capability is a separate security and governance concern.

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
| `memory_seed/cli.py` and `memory_seed/mcp_server.py` | Mirror existing parser/handler and structured-preview conventions; preserve CLI/MCP canonical-result parity. | MCP read operations are inline and non-mutating; any writer calls the same core validation used by CLI. No MCP operation merges a branch, closes a board, or expires detail without the same gates as CLI. |
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
unchanged lazy orientation. The immutable timestamp evidence is
`.memory-seed/sessions/2026-07/2026-07-18.md` decision `mse_6pj7hkwwp5va9jaq:d1`: it proves authored future
timestamps, not packet context. The alleged Ada packet omission is **orchestrator-observed, unverified**
until the compiler correction captures a committed input dispatch, binding, materialized-evidence receipt,
and output report that show omitted full agent-rules/session_logging. The Auditor records those separately;
tests use the future-timestamp decision only for clock behavior and a newly captured fixture for packet
contents. The Surface/packet track owns compiler and task-packet test changes for this
cross-cutting packet contract; it must not duplicate Kernel or integration reflection tests.

## Plan family, storage, and lifecycle

The active family is distinct from `sessions/` and exists only for the plan's working and review window.
The following names are a **deterministic planning vector**, not a live
manifest or pre-dispatch authority:

```text
.memory-seed/reflections/active/reflection-ledger-v1/
  manifest.yaml
  reports/ledger-kernel/rpr_14fyc35b2ze6e1ygw4ft.md
  fragments/kernel/ledger-kernel/001-rfl_14h1h37xrrp19qb9s1kd.md
  reports/ledger-surfaces/rpr_1dpbhdmzfa851rd1zpem.md
  fragments/surfaces/ledger-surfaces/001-rfl_0nd1t66xbshxx7rnth8w.md
  reports/ledger-auditor/rpr_08xgwfza8t5v5x2jg537.md
  fragments/verification/ledger-auditor/001-rfl_0bxzy7ezgekptyqgpv12.md
  reports/codex-orchestrator/rpr_14t6r8y0wmsnt0dthw68.md
  fragments/integration/codex-orchestrator/001-rfl_0efanjnv9sxj2hxarpbk.md
  closeout.md
```

Active reflection material is coordination state, not session membership or a reusable retrieval corpus.
`reflection view` writes no stored view: canonical Markdown goes
to stdout; a guarded explicit output path is a disposable derived export. JSON is non-authoritative transport
or export only. After automatic configured expiry, durable lookup uses embedded session receipts rather than
these paths.

`reflection init` is orchestrator-only and runs only after the Kernel parser/fuse lands. It generates a
cryptographically random 256-bit `reservation_seed`, creates canonical `manifest.yaml`, validates it, and
commits it before Task Packet compilation. It writes the literal tuple `(participant, branch, track,
sequence, report_id, fragment_id, report_path, fragment_path)` into that manifest, so Task Packets have no
content-derived path cycle.

The executable sha256-crockford-v1 canonicalization is: UTF-8 encode each component; prepend the literal
domain memory-seed/reflection-reservation/v1\0 and the 32 seed bytes; append each component as its four-byte
big-endian length followed by its bytes; SHA-256; take the first 12 digest bytes; encode with the project
Crockford alphabet 0123456789abcdefghjkmnpqrstvwxyz; and require the resulting 20-character suffix. Prefix
it with rpr_, rfl_, or rlr_. The planning-vector seed is
8f2c5e8d4ab1c0ffeeddccbbaa99887766554433221100fedcba9876543210ab; it is a published test vector, not a
seed that reflection init may reuse.

~~~python
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"

def crockford(raw):
    if len(raw) != 12:
        raise ValueError("ID digest must be exactly 12 bytes")
    number = int.from_bytes(raw, "big")
    return "".join(CROCKFORD[(number >> (5 * shift)) & 31] for shift in range(19, -1, -1))

def canonical_id(prefix, seed, *parts):
    frame = b"memory-seed/reflection-reservation/v1\0" + bytes.fromhex(seed)
    for part in parts:
        raw = part.encode("utf-8")
        frame += len(raw).to_bytes(4, "big") + raw
    return prefix + crockford(sha256(frame).digest()[:12])  # exactly 20 suffix chars

def reservation_id(prefix, seed, plan, participant, track, sequence, slot):
    return canonical_id(prefix, seed, plan, participant, track, str(sequence), slot)

def record_id(seed, fragment_id, ordinal):
    if ordinal < 1 or ordinal > 9999:
        raise ValueError("record ordinal must be 1..9999")
    slot = f"record:{ordinal:04d}"  # exact slot input, e.g. record:0001
    return canonical_id("rlr_", seed, "reflection-record-v1", fragment_id, slot)
~~~

record_id is deliberately not another participant reservation: it binds the already reserved fragment_id and
an ordinal. The display form is only rlr_<20-crockford>; ordinal stays a separate canonical record field, so
no -01 suffix is appended to the ID. The second-record vectors prove ordinal changes the exact slot rather
than rewriting a first record.

| Participant / slot | Report ID | Fragment ID | record:0001 ID | record:0002 golden ID | Suffix validation |
| --- | --- | --- | --- | --- | --- |
| ledger-kernel, kernel, 1 | rpr_14fyc35b2ze6e1ygw4ft | rfl_14h1h37xrrp19qb9s1kd | rlr_1an0dh39bsnjxfnpqtqh | rlr_0v66ws242aeshw23ppwr | all suffixes are 20 chars, lower-case Crockford; no I/L/O/U |
| ledger-surfaces, surfaces, 1 | rpr_1dpbhdmzfa851rd1zpem | rfl_0nd1t66xbshxx7rnth8w | rlr_16fs0ft3dwctpcgtx9wb | rlr_0gvzqfath1krwcaq9k9n | all suffixes are 20 chars, lower-case Crockford; no I/L/O/U |
| ledger-auditor, verification, 1 | rpr_08xgwfza8t5v5x2jg537 | rfl_0bxzy7ezgekptyqgpv12 | rlr_0mekt438381w6av338xz | rlr_1r9bdzc11bk83b9x8f0e | all suffixes are 20 chars, lower-case Crockford; no I/L/O/U |
| codex-orchestrator, integration, 1 | rpr_14t6r8y0wmsnt0dthw68 | rfl_0efanjnv9sxj2hxarpbk | rlr_04jaq3n1997v9vgqz0k0 | rlr_05qsdkcrkkz5ndayph7p | all suffixes are 20 chars, lower-case Crockford; no I/L/O/U |

```yaml
schema: memory-seed/reflection-plan
version: 1
plan_id: reflection-ledger-v1
base_branch: main
base_sha: <40-character resolved SHA>
state: active                         # active -> review -> closed when every chain is closed; never reopened
created_at: <RFC3339-UTC from the canonical writer>
reflection_retention_days: 7          # project-configurable positive integer
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
ordered participant/reservation tuples; `participants_seal` is their SHA-256. The manifest is authoritative
while the board is active; its digest detects alteration and is checked against the base tree. A worker cannot self-enrol, amend a
reservation, write an unreserved path, or use a new sequence. More slots require a serial manifest revision
and recompiled packets before dispatch. The family is ignored by retrieval, session-target resolution,
compacting, links, ADR membership, and seed initialization unless an explicit reflection command is invoked.

Lifecycle:

1. **Kernel bootstrap.** Kernel lands parser/fuse/integration without a reflection record; a parser exists
   before ledger dogfood.
2. **Initialize.** Orchestrator commits the manifest and compiles packets with its exact reservations.
3. **Collect/fuse.** Subsequent workers and the auditor commit their reserved pair; each is admitted by the
   coordinated integration primitive.
4. **Resolve/promote.** End-of-turn checks the reflections used by that turn and presents promotion candidates.
   ESR groups unresolved records, checks existing decisions, and catches missed candidates. After required
   validation, the orchestrator synthesizes the relevant implementer, reviewer, and orchestrator records,
   resolves disagreement, and promotes any adopted conclusion; neither discovery path promotes automatically.
5. **Close chains and board.** The orchestrator appends a chain-level synthesis and close record only after
   required validation and complete receipt coverage. Independent chains close separately when their own review
   cycles finish. `closeout.md` accumulates those immutable chain close records; the plan moves to `closed` only
   after every admitted chain is closed.
6. **Expire.** At the configured deadline (seven days by default), the next sanctioned cleanup automatically
   removes each eligible chain whose complete receipt is durable. Only early removal of an unpromoted chain
   requires live user approval; cleanup never removes the whole board or embedded receipts.

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
file and requires byte equality with the Git blob. Canonical report/fragment/manifest/closeout files must be
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
record_id: rlr_<20-crockford>
ordinal: 1
kind: opinion
chain_id: rlc_<deterministic-chain-id>
parents: []
relationship: orphan
area: reflection-ledger
activity: implementation-review
topics: [agent-collaboration, reflection]
related_decisions: []
confidence: medium
```

#### Conclusion

Keep the temporary reflection parser outside session discovery.

#### Reasoning

The session fuse is a useful safety-pattern reference, but treating reflections as sessions would create a
second durable memory route. Reflection files therefore stay outside `iter_session_documents()` and ordinary
retrieval.

#### Assumptions and uncertainty

The active-board query can satisfy cross-branch collaboration without widening durable memory retrieval.

#### Challenge or next step

Test whether topic and plan filters let another worker find this conclusion without knowing its branch.
```

The conclusion is required and comes first, acting as an abstract for humans and agents. Reasoning is required
and may be more detailed than the promoted decision because it exists to expose assumptions and let peers
challenge the proposal during implementation. Assumptions/uncertainty, alternatives/objections, and a question
or next step are optional structured sections. `area`, `activity`, and `topics` support active-board grouping;
`parents` links to the preceding reflection record or records; `relationship` is `refines`, `responds`,
`corrects`, `challenges`, `combines`, or `orphan`. A new record searches active chain heads first and may use
`orphan` only after an explicit `no-related-thread` judgment. `refines` and `corrects` advance a chain head;
`responds` and `challenges` retain divergent live heads; `combines` names two or more parents and creates a
new shared head. Related decisions are optional. Files, commits, patches, and test
logs are not standard reflection fields and appear only when the thought cannot be understood without them.

Record kinds have intentionally narrow authority:

| Kind | Worker | Orchestrator | Meaning |
| --- | --- | --- | --- |
| `observation` | yes | yes | First-hand fact or measured result; must cite its report. |
| `opinion` | yes | yes | A bounded recommendation or interpretation; it is not a decision. |
| `risk` | yes | yes | A concern with evidence and requested owner/disposition. |
| `correction` | yes, own prior record only | yes, own prior record only | New record with `corrects: <record_id>` and reason; original remains visible. |
| `resolution` | no | yes | Explicit plan-level choice, citing the opinions/risks it considered and rejected. |
| `promotion` | no | yes | Links a selected reusable lesson to a newly written ordinary session `entry_id` and decision reference when applicable. |
| `closeout` | no | yes | Declares every reflection disposition, retention choice, and embedded-receipt destination before expiry can be proposed. |

Every record carries a stable ID, explicit subject, source (`write-time` or `derived`), and report provenance
unless it is an orchestrator resolution, promotion, or closeout. Corrections must target an earlier record
from the same participant; they cannot erase it, alter another participant's evidence, or turn an opinion
into a resolution. A derived record may fill a missing statement but never silently override a write-time
record; an attempted override requires a correction citing the exact prior record and resolution evidence.

## Reflection fuse and common-view behavior

`reflection fuse --preview --plan <id> --branch <branch>` is read-only. It resolves `source_tip` and base,
validates the base-established manifest/participant seal, examines three-dot changes, and rejects a manifest
edit, foreign family, unknown participant, wrong branch/base/track/sequence/ID/path, unreserved record,
malformed or noncanonical bytes, uncited/missing report, duplicate/collision, invalid correction/authority,
or a source not descended from manifest base. While active, it also rejects changed bytes, deletion, rename/copy, extra
canonical path, and every mode change of base reflection material. `already_present` requires equal canonical
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

`.gitattributes` marks active reflection paths non-mergeable. The integration checker rejects any merge
commit changing reflection paths without a successful matching reflection-fuse trailer; raw merge,
manual post-merge edit, and standalone reflection apply therefore fail closed.

`reflection view --plan <id> [--area ...] [--activity ...] [--topic ...] [--related-decision ...]
[--chain ...] [--responds-to ...]` consumes the same parsed records and writes canonical Markdown only to stdout:
raw records, measured source-tip receipt, correction chains, risks, resolutions, promotions, and participant
coverage, sorted by `(created_at, participant, sequence, fragment_id, record_ordinal)`. Filters are confined
to active reflections and allow a worker to pull relevant thinking from other branches without broad discovery.
`--responds-to` returns the direct children by default and accepts `--transitive` for the complete descendant
chain. No selector ranks away dissent or returns only one live head. It may group but
must show every source record and label grouping derived. It never picks a majority or effective winner.
JSON/MCP structured data are non-authoritative projections of this same result.

## CLI, MCP, and orchestration surfaces

| Surface | Operation | Write policy |
| --- | --- | --- |
| CLI | `memory-seed reflection init --manifest-file …` | Orchestrator-only; validates identity, reservation paths/IDs, and roster seal before the initial manifest commit. |
| CLI | `reflection append --report-file … --fragment … [--dry-run]` | Accepts conclusion, reasoning, topics, and optional relationship judgment. It adds clock-owned metadata, searches active heads, links one mechanically clear match, and asks only when the relationship is ambiguous or no-related-thread must be confirmed. Dry run returns exact rendered Markdown/YAML bytes. |
| CLI | `reflection check --plan`, `reflection view --plan`, `reflection fuse --plan --branch --preview` | Read-only. View is stdout Markdown; `--json` is transport only. Apply is internal to the coordinated merge primitive. |
| CLI | `reflection close --plan --chain <id> --apply` | Orchestrator-only; validates required review coverage, synthesis, dispositions/promotions, complete receipts, and appends one immutable chain close record. The plan closes only when every admitted chain has closed. |
| CLI | `reflection expire --plan [--chain ...] --preview|--apply` | Preview shows age, receipt coverage, and exact eligible chain paths. Apply automatically removes only elapsed chains. `--early` is restricted to unpromoted chains and requires a live-user approval receipt the agent cannot mint. |
| MCP | `memory_reflection_view`, `memory_reflection_fuse_preview` | Non-mutating projections of the same core result as CLI. |
| MCP | `memory_reflection_append`, `memory_reflection_close` | Added only with success/error parity tests; call shared validators and cannot merge or bypass live approval. |
| Orchestrator | Task Packet compile + coordinated integration | Compiles exact pre-reserved paths, checks binding/admission receipt, and owns resolution, promotion, integration, and closeout. Elapsed-chain expiry is mechanical; early unpromoted deletion remains user-gated. |

CLI and MCP must expose identical valid core result dictionaries/rendered bytes and identical structured
errors `{code, path, message, details}` for every shared fixture. No MCP writer hand-writes files. No export
path exists except stdout or a caller-scoped derived file guarded by the normal worktree policy. No new
dispatch engine is introduced: the ledger is evidence inside the existing flow.

The append surface is an outcome-level operation under `constitution:v1#path-of-least-resistance`. The caller
supplies the thought, not storage mechanics: the shared core stamps time and identity, resolves the active plan,
normalizes topics, searches active chain heads, and validates and writes the record in one call. It automatically
continues only when one relationship is mechanically justified. Multiple plausible heads, an unclear relationship,
or a proposed orphan are judgment boundaries returned to the caller with concise candidates. End-of-turn uses the
same principle to inspect reflections actually referenced or adopted by the turn and offer their complete chains
for promotion review; validation and orchestrator synthesis still precede the durable judgment.

## Authority, ESR promotion, receipts, and expiry

- Workers can state only first-hand observations, opinions, risks, and corrections within their assigned
  prefix. They cannot resolve a cross-track disagreement, promote a lesson, modify the manifest, change
  another participant's record, integrate, or close the plan.
- The orchestrator's `resolution` names the considered record IDs, the chosen conclusion, the rejected or
  deferred alternatives, and any remaining risk owner. It never rewrites a worker's prose.
- Promotion is selective and happens during ESR or earlier when a conclusion is already settled. ESR mechanically
  finds unresolved records, groups overlap, and checks whether an existing decision already covers the lesson;
  the orchestrator makes every durable judgment. The orchestrator uses ordinary `session append` / MCP
  append with normal chronology, DRAFT, topic, linkage, ADR-review, and branch guards. The durable session
  must retain a human-readable `D:`/`R:` explanation of conclusion and reason plus plan and source
  explanation plus an embedded `reflection_receipts` block. Each receipt contains the reflection ID, authored
  timestamp, author, area/activity/topics, one-sentence conclusion, content digest, disposition, and promoted
  decision references. The decision does not point to a temporary path.
- A promotion is not automatic consolidation. One-off status, duplicate opinion, transient debugging,
  personal data, and unresolved disagreement are explicitly disposed. Receipts for non-promoted reflections
  live in the ESR session entry rather than a separate receipt sidecar.
- A rebuildable receipt index may accelerate lookup by reflection ID, topic, or decision ref. It is derived
  solely from ordinary session entries, can be deleted at any time, and owns no authority.
- The canonical embedded receipt shape is:

  ```yaml
  reflection_receipts:
    - schema: memory-seed/reflection-receipt
      version: 1
      receipt_id: rrc_<deterministic-id>
      plan_id: reflection-ledger-v1
      chain_id: rlc_<chain-id>
      head_record_ids: [rlr_<head-id>]
      member_record_ids: [rlr_<record-id>, rlr_<record-id>]
      conclusion: "One sentence describing what survived the discussion."
      disposition: promoted|already-covered|expired-unpromoted|early-deletion
      promoted_to: [mse_<entry-id>:d1]
      recorded_at: <RFC3339-UTC>
      detail_digest: sha256:<digest-of-canonical-member-bytes-in-record-order>
  ```

  `member_record_ids` contains every reachable member absorbed by the named live head or heads. Promoting a
  chain means promoting that complete set, not only its newest record. Several receipts may attach to one
  decision and one chain receipt may name several decisions. Repeated copies of the same receipt are allowed
  only when their canonical bytes are identical; conflicting duplicates fail validation. The receipt-only
  resolver scans ordinary sessions by `(plan_id, chain_id, record_id)` and never requires an expired active
  file. `promoted_to` must resolve to the decision containing the receipt or to another decision authored in
  the same promotion checkpoint.
- Closing is distinct from expiry. `closeout.md` contains immutable per-chain close records naming the relevant
  implementer, reviewer, and orchestrator records; required validation receipt; synthesis; promotion,
  existing-decision coverage, or non-promotion disposition; complete member receipt coverage; `closed_at`;
  measured `retention_days`; and deterministic `expires_at = closed_at + retention_days`. An open, unvalidated,
  unsynthesized, or unresolved chain has no ordinary expiry deadline. Independent chains may close while peers
  remain active; board close requires every admitted chain to have a valid close record.
- At or after `expires_at`, the next sanctioned cleanup automatically removes that chain after verifying a
  durable receipt covers every member. It does not require a per-chain approval and never removes another
  chain. The user changes future retention through the project setting; a shorter value never retroactively
  deletes a chain without a fresh preview.
- Early deletion is allowed only for an unpromoted chain with the user's live approval. The approval is
  recorded in the ESR/session disposition with the exact chain, member IDs, reason, approval time, and
  pre-expiry `expires_at`; an agent cannot self-assert it. Git may retain historical blobs, so no hard-erasure
  claim is made.

## Delivery sequence and ownership

### Serial foundation

1. Add `memory_seed/reflection_ledger.py` with canonical Markdown/YAML schemas, manifest-reservation ID
   derivation, strict parsers/renderers,
   manifest/report/fragment validators, common-view projection, and a fuse-plan/result model. Extract only
   genuinely neutral Git/ref-diff helpers from `core.py` if reuse cannot stay internal without circular
   imports.
2. Add `reflection` CLI routes and the one coordinated session/reflection integration sequencing. Add
   `.gitattributes` protection for the active reflection family so a raw line merge fails rather than fabricates
   a valid-looking record.
3. Add the read-only MCP preview/view surfaces. Add writers only after the shared validator and CLI behavior
   are fully covered.

### Parallel tracks after the foundation lands

| Track | Owned files | Deliverable | Dependency |
| --- | --- | --- | --- |
| Kernel fuse (serialized bootstrap) | `memory_seed/reflection_ledger.py`, minimal shared `memory_seed/core.py` helper extraction, `.gitattributes`, `tests/test_reflection_ledger.py`, canonical fixtures | Schema, manifest IDs, report validation, conclusion-first records, topic filters, preview/internal apply fuse, coordinated merge, and closeout/expiry preconditions. It emits no ledger record. | Foundation base only. |
| Surfaces and packets | `memory_seed/cli.py`, `memory_seed/mcp_server.py`, `memory_seed/task_packet.py`, `tests/test_reflection_ledger_surfaces.py`, `tests/test_task_packet.py`, packet/worker documentation and its Seed twin | CLI/MCP parity, active-rules/session-logging packet baseline, pre-reserved paths, handoff validation, then its reserved pair. | Kernel API frozen and manifest committed. |
| Orchestrator integration test | `tests/test_reflection_ledger_integration.py` and integration fixture helpers | Multi-worktree simulation, cross-branch topic retrieval, end-of-turn and ESR promotion, embedded receipts, automatic chain expiry, and negative controls. | Kernel + surfaces integrated; serialized owner only. |
| Independent auditor | Its pre-reserved report/fragment only | Read-only integrated-tree verdict and evidence handoff. | Kernel + surfaces integrated; no product/test edits. |

The orchestrator owns `.memory-seed/reflections/active/<plan_id>/manifest.yaml`, the integration fragment,
branch ordering, resolution/promotion, durable session appends, closeout, automatic chain expiry, and the integration test. No worker
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
6. After each chain's required validation, the orchestrator synthesizes its records, writes any resolution and
   promotion, embeds complete receipts in ordinary session entries, closes that chain, and validates again.
   The board closes only when all admitted chains have closed.
7. At each ESR or process checkpoint, preview exact elapsed chains and cleanup paths, then automatically expire
   eligible chains. Require live user approval only for early deletion of an unpromoted chain. The integration
   test proves every durable link resolves through an embedded receipt afterward.

## Test matrix and acceptance observables

| Area | Required proof |
| --- | --- |
| Manifest and ownership | Unknown/duplicate participant, roster-seal mismatch, changed manifest, foreign plan, wrong branch/base/track/reservation, a worker writing an orchestrator kind, and an uncited resolution all refuse. |
| Canonical IDs/bytes | Manifest-derived dry-run IDs; malformed/forged IDs; duplicate source ID; base collision same bytes/mode=`already_present`; changed bytes/mode refusal; duplicate sequence; invalid UTF-8/NFC/LF/final LF; golden manifest/report/fragment/closeout bytes. |
| Report provenance | Missing report, wrong plan/participant/branch/base, unreserved path, malformed fingerprint, uncited report, changed source tip, and altered measured blob/hash/mode all refuse. Reports cannot claim a head SHA. |
| Active immutability | Before sanctioned chain expiry, delete, rename, copy, source-only extra path, symlink/executable/submodule, and any mode change of a report/fragment/manifest refuse. |
| Chains and derived view | Refines/responds/corrects/challenges/combines edges validate, cycles and dangling parents refuse, orphan requires `no-related-thread`, divergent heads remain visible, and direct/transitive cross-branch selectors work without ranking away dissent. |
| Coordinated application | Both previews are required; no-commit merge resets every union path and removes additions; second apply failure aborts; raw/post-merge reflection integration fails closed; one commit has both receipts. |
| CLI/MCP parity | Same valid rendered fragment/result and `{code,path,details}` errors from both paths; MCP read surfaces and stdout view are non-mutating; unsupported export arguments fail closed; no writer bypasses core validation. |
| Packet governance baseline | Every worker packet materializes active agent-rules; worker-checkpoint/session-path packets also materialize session_logging, reject direct session Markdown/future timestamp overrides, preserve lazy orientation, and account both components in input/cost tokens. |
| Task Packet integration | Exact pre-reserved worker paths/IDs and expected-absent paths are materialized; stale binding blocks; packet evidence is not refetched; compilation is measured for all three drafts. |
| Outcome-level friction | One append call stamps canonical time/identity, resolves the plan, normalizes topics, and links a single clear active head; ambiguous heads and orphan creation stop for judgment; no caller must daisy-chain deterministic parser, search, hydration, validation, and write calls. |
| Promotion and receipts | End-of-turn identifies candidates when a turn uses a reflection; ESR catches leftovers; promotion waits for required validation and orchestrator synthesis; many-chains-to-one-decision and one-chain-to-many-decisions work; receipt grammar/digests validate; session-only resolution and index rebuild refuse duplicates, conflicts, malformed digests, and decision mismatches. |
| Validation and closure | Implementer records remain open for reviewer confirmation, challenge, correction, or refinement; close refuses without required validation, relevant implementer/reviewer/orchestrator coverage, synthesis, resolved or disposed divergent heads, and complete receipts; independent chains close while peers remain active; board close refuses until all chains close. |
| Expiry | Default seven-day and configured windows derive only from chain `closed_at`; elapsed closed chains delete automatically and individually; open, unvalidated, unelapsed, or incompletely receipted chains refuse; early unpromoted deletion requires an unforgeable live-approval receipt; general board wipes refuse. |
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

These are semantic Task Dispatch v1 source forms, not already compiled packets. A is usable during the
serialized Kernel bootstrap and intentionally authorizes no reflection record. B and C are pre-init forms:
they contain no manifest-reserved reflection path and must not be compiled, dispatched, or described as bound
until Kernel has merged and reflection init has committed the live manifest. Only then does the dispatch
generator inject exact reserved paths/IDs and save a measured binding plus compiler receipt. The selected pins
ground the session-fuse and one-step merge contract; topics supply neighbouring context without depending on
this plan's mutable text.

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
  allowed_files: [memory_seed/reflection_ledger.py, memory_seed/core.py, .gitattributes, tests/test_reflection_ledger.py, tests/fixtures/reflection_ledger/canonical/manifest.yaml, tests/fixtures/reflection_ledger/canonical/report.md, tests/fixtures/reflection_ledger/canonical/fragment.md, tests/fixtures/reflection_ledger/canonical/closeout.md]
  forbidden_files: [AGENTS.md, .memory-seed/agent-rules.md, .memory-seed/index.md, .memory-seed/policy.md, docs/CONSTITUTION.md, memory_seed/seed/AGENTS.md, memory_seed/cli.py, memory_seed/mcp_server.py, tests/test_reflection_ledger_integration.py]
  validation: ["python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_session_fuse_and_merge.py", "git diff --check"]
  output_contract: ["Return a committed kernel checkpoint and measured validation; no reflection report/fragment is allowed before the parser exists.", "Do not merge, resolve, promote, close, or expire."]
  expected_absent: [memory_seed/reflection_ledger.py, tests/test_reflection_ledger.py, tests/fixtures/reflection_ledger/canonical/manifest.yaml, tests/fixtures/reflection_ledger/canonical/report.md, tests/fixtures/reflection_ledger/canonical/fragment.md, tests/fixtures/reflection_ledger/canonical/closeout.md]
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

### B. Surfaces and packet contract (post-init dispatch form)

This is the pre-init semantic source form. It deliberately does **not** claim a report/fragment path. After
Kernel merges, `reflection init` commits the live manifest and the dispatch generator injects the two exact
reservation paths/IDs into `allowed_files` and `expected_absent`, then compiles the resulting dispatch with
its committed binding/receipt. It is a refusal to compile or assign this track before that point.

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
  non_goals: ["Do not alter the Task Packet semantic schema.", "Do not write sessions, governance files, manifest, resolution, promotion, closeout, or expiry state."]
execution:
  role: worker
  persona: none
  capability_tier: frontier
  write_intent: writing
  allowed_files: [memory_seed/cli.py, memory_seed/mcp_server.py, memory_seed/task_packet.py, tests/test_reflection_ledger_surfaces.py, tests/test_task_packet.py, .memory-seed/skills/agent_collaboration.md, memory_seed/seed/.memory-seed/skills/agent_collaboration.md]
  forbidden_files: [AGENTS.md, .memory-seed/agent-rules.md, .memory-seed/index.md, .memory-seed/policy.md, docs/CONSTITUTION.md, tests/test_reflection_ledger.py, tests/test_reflection_ledger_integration.py]
  validation: ["python -X utf8 -m pytest -q tests/test_reflection_ledger_surfaces.py tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_mcp_server.py", "git diff --check"]
  output_contract: ["Return committed CLI/MCP parity and packet-baseline evidence (full active agent-rules; full session-logging/automatic-clock guard where applicable).", "After init, use only the generator-injected reserved report/fragment paths; do not merge, resolve, promote, close, or expire."]
  expected_absent: [tests/test_reflection_ledger_surfaces.py]
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

### C. Independent auditor (pre-init read-only form)

This is intentionally read-only until Kernel + `reflection init` establish a committed live manifest. The
post-init dispatch generator changes only its evidence scope/intent to the manifest-reserved pair and stores
the generated dispatch, measured binding, and compiler receipt. No audit participant may claim a reservation
from the planning vector.

~~~yaml
schema: memory-seed/task-dispatch
version: 1
objective: "Independently verify the integrated reflection board for provenance, collision, coordinated merge, cross-branch retrieval, ESR promotion, embedded receipts, and approved-expiry behavior; write only the pre-reserved audit evidence pair."
constitution_refs: [constitution:v1#append-only, constitution:v1#provenance, constitution:v1#markdown-authority, constitution:v1#authority]
project_context:
  project_type_and_purpose: "Memory Seed retains attributable project reasoning as local Markdown while integration tools fail closed on malformed concurrent history."
  relevant_subsystem: "The auditor exercises merged kernel/surfaces, coordinated fuse receipts, active-board retrieval, session-promotion boundary, embedded receipts, and expiry gate without owning product code."
  task_fit: "Cross-worktree collision, post-merge bypass, the immutable future-timestamp decision mse_6pj7hkwwp5va9jaq:d1, and a separately captured Ada packet-context fixture require an independent verdict."
  downstream_use: "The orchestrator uses the verdict for bounded rework or promotion/closeout; the auditor cannot perform either action."
  non_goals: ["Do not edit implementation, tests, control-plane, seed, session, manifest, resolution, promotion, closeout, or expiry state.", "Do not equate packet compilation with implementation correctness."]
execution:
  role: validator
  persona: none
  capability_tier: frontier
  write_intent: read-only
  allowed_files: []
  forbidden_files: [AGENTS.md, .memory-seed/agent-rules.md, .memory-seed/index.md, .memory-seed/policy.md, docs/CONSTITUTION.md, memory_seed/reflection_ledger.py, memory_seed/core.py, memory_seed/cli.py, memory_seed/mcp_server.py, tests/test_reflection_ledger.py, tests/test_reflection_ledger_surfaces.py, tests/test_reflection_ledger_integration.py]
  validation: ["python -X utf8 -m pytest -q tests/test_reflection_ledger.py tests/test_reflection_ledger_integration.py tests/test_reflection_ledger_surfaces.py tests/test_session_fuse_and_merge.py tests/test_task_packet.py tests/test_task_packet_surfaces.py", "python -X utf8 -m memory_seed.cli docs check", "python -X utf8 -m memory_seed.cli docs index --check", "git diff --check"]
  output_contract: ["Return a read-only PASS, FAIL, or NEEDS_CONTEXT pre-init verdict with exact command results; cite mse_6pj7hkwwp5va9jaq:d1 only for future timestamps and require the separately committed Ada packet fixture before asserting missing context.", "State separately what was tested, inferred, and still requires live orchestrator action; do not merge, promote, close, expire, or claim an evidence path before init."]
  expected_absent: []
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

### Reproducible pre-work proof and staged compilation

No Task Packet compile is claimed from this plan revision. The old reported compiles depended on an ephemeral
worktree binding and (for B/C) paths that cannot exist before Kernel + reflection init; they were removed
rather than presented as reproducible evidence. The committed-plan pre-work proof is deliberately narrower:
extract the three fenced Task Dispatch maps and run normalize_task_dispatch() against each. That has no
binding, generated artifact, or manifest claim. It verifies schema shape and that the pre-init B/C forms cannot
authorize a reflection path.

| Pre-work measurement | Reproducible input | Required result |
| --- | --- | --- |
| A Kernel source form | this committed fenced YAML | normalizes; no reflection report/fragment path; no worker reflection record |
| B Surface source form | this committed fenced YAML | normalizes; no reflection evidence path before init |
| C Auditor source form | this committed fenced YAML | normalizes read-only with no writable path before init |
| Reservation vector | fixed seed + executable function above | all eight IDs/paths match the 20-character Crockford table |

Actual compilation has staged committed inputs and receipts:

1. Kernel: when its worktree/branch is allocated, save the dispatch source, measured runtime-binding JSON,
   compiler packet/receipt JSON, and verification output under the Kernel handoff artifact directory; record
   their SHA-256 values in its normal handoff. Do not quote a fingerprint before those files exist.
2. B/C: only after Kernel merges and reflection init commits a manifest may the dispatch generator read the
   manifest, inject the exact reservations, save generated dispatch plus measured binding and compiler
   receipt, then compile. The generator refuses a missing/uncommitted manifest or digest mismatch.
3. Surface tests add baseline_agent_rules/session_logging_guard component assertions and remeasure token
   ledgers from those stored receipts. A hand-edited packet or stdout-only claim is not evidence.

## Migration, compatibility, and explicit non-goals

There is no migration or backfill. Existing sessions, diagrams, links, topics, ADRs, Task Packets, and
experiment reflection logs retain their current readers and semantics. The first board is an opt-in pilot
with no automatic initialization and no change to `memory-seed init` or seed payloads. A completed pilot is
closed, its durable receipts live inside ordinary sessions, and its detailed chains expire automatically at
their configured deadlines. Any later decision
to make the family reusable across projects, include it in retrieval, add native Task Dispatch schema, or add
a server/sync layer needs separate evidence and a new proposal.

Known risks to hold visible during implementation:

- Cleanup can look like guaranteed erasure. The preview must state that expiry removes active-tree detail,
  while ordinary Git history may retain committed blobs; privacy-grade erasure is out of scope.
- Receipt summaries can become too large or duplicate the reflection. Enforce a compact one-sentence
  conclusion plus identity, topics, disposition, digest, and decision links only.
- Reporting fields can become decorative. Negative controls must prove wrong branch/base/source-tip/blob/path
  provenance blocks fusion.
- A common view can accidentally become an authority projection. Tests must assert it retains dissent and
  does not expose a winner/effective decision field.
- The format cannot be introduced and used on one branch; parser/CLI/MCP capability lands before any ledger
  data, just as session/ADR fuse rules require.
- Reflection reports may include private worker details. Treat active board content as potentially
  publishable, write minimally, and promote only sanitized reusable lessons.

## Review checkpoint

The plan is ready for independent review when the reviewer can answer yes to all of these:

1. Reflection storage is distinct from durable sessions, defaults to a configurable seven-day window, and
   expires automatically per chain only after ordinary sessions contain complete embedded receipts.
2. Every writer is manifest-authorized and every fragment is traceable to a committed, binding-matched
   report.
3. The fuse blocks unsafe state before merge/apply, while the common view exposes disagreement rather than
   manufacturing consensus.
4. Resolution, promotion, and closeout remain orchestrator judgments; elapsed expiry is deterministic, while
   early unpromoted deletion requires live user approval. Decisions reference embedded receipts rather than
   temporary paths.
5. Task Packet drafts compile from pre-reserved exact paths/IDs plus measured binding; no hidden
   dispatch, worktree, provider, or authority feature is implied.
6. Active retrieval can find overlapping reflections across branches by plan, area, activity, topic, related
   decision, or response link without making the board part of ordinary long-term memory retrieval.
7. The ratified Constitution 1.12 reflection-expiry exception and this plan agree on the temporary boundary,
   chain deletion unit, receipt prerequisite, configured deadline, and early-deletion approval gate.
