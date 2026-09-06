---
title: "Reflection Ledger Workstream Evolution Plan"
date: "2026-09-07"
project: "memory-seed"
status: "active"
priority: "P1"
next_action: "Independently review the history-aware admitted-compaction amendment before any further v2 implementation; do not reopen or implement it without that review."
source:
  - "docs/2_Todo/plan-reflection-ledger.md"
  - "docs/CONSTITUTION.md"
  - "memory_seed/reflection_ledger.py"
  - "tests/test_reflection_ledger.py"
scope: "Evolve new reflection boards from participant fragments plus cross-branch fuse into one append-only temporary ledger owned by one feature workstream branch."
non_goals:
  - "Do not rewrite the original reflection-ledger plan, historical fragments, past sessions, or their receipts."
  - "Do not make a combined board authoritative, durable, or part of ordinary memory retrieval."
  - "Do not permit concurrent writers to one workstream ledger or infer dependencies between unrelated workstreams."
  - "Do not migrate or backfill existing fragment/fuse boards."
dependencies:
  - "The ratified temporary reflection-board exception in Constitution 1.12."
  - "The landed reflection-ledger parser, receipt, closeout, and expiry evidence."
  - "Existing guarded session append, ESR, worktree, CLI, and MCP parity mechanisms."
acceptance_criteria:
  - "A feature workstream has exactly one branch-bound, append-only temporary ledger; planner, implementer, reviewer, and orchestrator append to it sequentially."
  - "A write refuses a stale branch tip, stale ledger digest, invalid target-chain phase successor, malformed append, or a writer not authorised for that chain."
  - "Active cross-workstream inspection is read-only and derived; it never fuses records or makes a combined view authoritative."
  - "Promotion, receipt resolution, closeout, and per-chain expiry preserve the Constitution 1.12 boundary and work after the active ledger is removed."
  - "Old fragment/fuse boards remain readable and verifiable through compatibility readers without conversion."
---

# Reflection ledger workstream evolution

## Decision and boundary

The landed participant-fragment and fuse kernel remains historical truth. It was the right safety model for
the original plan's independent, parallel participant branches. The next architecture has a different
operating fact: within one feature workstream, planner, implementer, reviewer, and orchestrator phases are
sequential. Therefore each feature branch owns one authoritative temporary reflection ledger. Each role
appends dated, conclusion-first blocks to that same ledger in its turn.

Parallel features have different ledgers. A combined board is a read-only derived index or view over active
ledgers, not a fused source of truth. A cross-ledger link is permitted only when the writer records a real
dependency; proximity, similar topics, and simultaneous work are not dependencies.

Durable outcomes do not change: a compact normal Memory Seed decision, written by the guarded session
writer, carries the human-readable result and an embedded reflection receipt. The temporary ledger remains
outside normal session discovery and retrieval, and chains expire only through the ratified governed
lifecycle.

This is an evolution plan. It does not revise `plan-reflection-ledger.md`, reclassify its past decisions, or
change the meaning of existing `manifest.yaml`, report, fragment, fuse, closeout, or receipt evidence.

### 2026-09-07 architecture amendment — admitted compaction

Implementation review at `3ccf36252f419107b5c1709a48c2b6960d2014be` found that removing a complete chain
changes the preceding bytes of a later surviving block. Its immutable `pre_ledger_digest` must therefore
fail a normal standalone re-check, even though rewriting that block would violate the frozen byte rule. This
is a real contradiction in the original expiry wording, not permission to make normal validation permissive.

This amendment adds one narrow, separately admitted read path for a compacted v2 ledger. It keeps both
frozen rules: every surviving header and block is byte-identical, and a fresh normal ledger still requires
every `pre_ledger_digest` to bind the exact preceding canonical bytes. Shannon's review adds the necessary
history rule: a successful standalone parse never by itself proves that a trusted Git-backed image is normal.
Every such load must also prove a monotonic append/rebind-only path history with no record deletion; any
non-monotonic path transition enters the same proof-gated compaction path or refuses. This introduces neither
a new durable compaction index nor a new authority sidecar: ordinary committed session entries plus Git
objects are the only proof authority; any receipt/proof index is a disposable, rebuildable cache.

## Why the workstream model is simpler

The old model pays for distributed coordination inside one plan: roster sealing, deterministic reservations,
one immutable report/fragment pair per participant, a branch admission fuse, and a coordinated
session/reflection merge. Those controls prevent concurrent authors from colliding. They are unnecessary for
one serial branch writer and obscure the actual unit of work: a feature workstream.

The new invariant is small and explicit:

```text
one workstream branch -> one active ledger -> one guarded writer at a time -> append-only records
parallel workstreams  -> separate ledgers -> derived combined inspection only
durable decision      -> ordinary session + embedded receipt -> temporary chain may expire
```

The ledger is branch-bound, not branch-named. Its immutable header records a generated `workstream_id`, its
declared `working_branch`, and the base commit from which the workstream began. Renaming a branch does not
silently transfer ownership: a deliberate orchestrator-owned rebind record is required and is visible in the
ledger and its closeout receipt.

## Target contract

### One canonical ledger

New boards live at one canonical path:

```text
.memory-seed/reflections/active/<workstream_id>/ledger.md
```

`ledger.md` has a frozen canonical header with `schema`, `version`, `workstream_id`, `working_branch`,
`base_sha`, `created_at`, `reflection_retention_days`, `retention_extension_receipt`,
`retention_approval_key_id`, and `id_salt`. State and phase are derived from the
validated ordered blocks; they are not mutable header fields. Normal operation has append-only dated blocks.
The only sanctioned non-append rewrite is the compare-and-swap expiry compaction specified in the frozen v2
annex below. Every block contains:

- a globally stable `record_id` and the clock-owned `created_at` timestamp;
- `role` (`planner`, `implementer`, `reviewer`, or `orchestrator`) and the declared phase transition;
- a required conclusion before required reasoning, plus optional assumptions, alternatives, evidence, and
  next step;
- `chain_id`, parent record IDs, and a relationship (`refines`, `responds`, `challenges`, `corrects`,
  `combines`, or an explicitly judged orphan);
- optional real `depends_on` entries for another `{workstream_id, record_id, content_digest}`; and
- source/provenance and any normal decision references.

`record_id` and `chain_id` are generated by the canonical writer, not supplied by callers. The annex freezes
their framing, prefixes, and golden vectors. The record's canonical content digest makes identity auditable
after expiry. Existing `rlr_` and `rlc_` identifiers remain valid compatibility forms, but a v2 identifier is
never inferred from a v1 object.

### Sequential-writer enforcement

The writer takes the expected Git `HEAD` and the digest of the complete current `ledger.md`. It reopens both
immediately before append. A mismatch refuses with a structured stale-write diagnostic and no file change.
It atomically writes only the newly rendered suffix, then returns the new tip/digest/record identity. A caller
must reload and make any relationship judgment again; it must not mechanically replay stale prose.

Each chain's state machine allows the normal loop:

```text
plan -> implement -> review -> (implement correction -> review)* -> orchestrate -> close
```

Only the role allowed by the target chain's current phase can append a phase-advancing record. A planner may
start a root chain after ledger initialization;
an implementer may add observations, opinions, risks, and corrections; a reviewer may respond, challenge, or
approve/reject with evidence; and only the orchestrator may resolve, promote, close, rebind, or dispose. The
same role can add an explanatory non-advancing record only when it owns that target chain's current phase.
This is an authorization and sequence check, not a lock inferred from agent prose. A ledger can contain
multiple chains, each with an independent phase, but every append remains globally serialized by the expected
head/digest compare-and-swap; no two writers can succeed against the same ledger state.

Git/worktree isolation remains the outer guard: an append may run only from the ledger's owned workstream
branch. Branches are never treated as evidence of a different person's identity.

### Chains and dependencies

Parents are local to a ledger by default. The parser rejects a parent in another ledger. A local chain starts
only after the writer records an explicit `no_related_thread` judgment; one mechanically clear head may be
selected automatically, while multiple plausible heads stop for relationship judgment. `refines`,
`corrects`, and `combines` advance local heads; `responds` and `challenges` retain divergent heads. The view
always displays divergent live heads.

A cross-ledger dependency is an edge in `depends_on`, not a parent and not a fuse input. It must name an
active or durably receipted target and state why the result blocks, constrains, or supplies the current work.
The resolver verifies the target record digest when the target remains active; after expiry it verifies the
embedded receipt. A missing, changed, unrelated, or self-workstream dependency refuses. It never imports the
target record into the local chain.

### Cross-branch integration and combined views

`reflection ledger view --workstream <id>` reads one canonical ledger. `reflection board view --active`
enumerates every candidate active-ledger directory and produces a sorted derived projection. Valid ledgers are
labelled with source workstream and cross-ledger dependencies. Malformed or unsupported candidates are also
shown, with path, raw digest, recoverable owner fields, and a diagnostic; they are never silently omitted.
The view has no effective winner, consensus, merge, promotion, or write operation.

Feature integration does not run the old reflection fuse for a new-format ledger. Protected active-ledger
paths remain append-only: a raw merge, in-place change, rename, or deletion is rejected unless it is the
sanctioned branch integration or eligible expiry operation. Integrating feature code does not combine its
reasoning with another feature's ledger. The integration receipt records the workstream and final ledger
digest, then the orchestrator closes the relevant chains. A dependency is resolved by the normal feature
integration order and durable receipts, never by copying another branch's ledger blocks.

## Retain, simplify, retire

| Landed component | Next treatment | Reason |
| --- | --- | --- |
| Canonical UTF-8/NFC/LF parser/renderer and structured diagnostics | Retain | The same byte-stable, fail-closed boundary protects a single ledger. |
| Conclusion-first record shape, local relationships, divergent-head view | Retain, simplified to ledger blocks | They directly support review without manufacturing consensus. |
| Git-admitted receipt resolution, chain close validation, retention from `closed_at`, and per-chain expiry | Retain | They implement Constitution 1.12 and survive temporary-detail removal. |
| Early unpromoted expiry approval verification | Retain; adapt its Ed25519 host-signing and Git-admission mechanics for v2 retention extensions | Arbitrary caller text must not authorise either early disposal or longer retention. |
| `ReflectionManifest` roster, participant seal, reservation seed, report/fragment IDs and paths | Retire for new boards; retain readers | A single branch needs no participant allocation or pre-dispatch pair. |
| Worker reports paired with fragments and report-provenance admission | Simplify | A record carries measured evidence/commit references directly; optional handoff reports remain Task Packet artifacts, not ledger authority. |
| Per-participant fragment ownership and source-branch fuse | Retire for new boards; retain `v1` compatibility fuse | They solve concurrent same-plan writers, which the new design disallows. |
| Coordinated session/reflection fuse and reflection trailers | Simplify to branch append/integration receipt | There is one current ledger writer, so no union of independently authored reflection paths is required. |
| Per-plan active common view | Retain as a derived one-ledger view | It still exposes all local records and dissent. |
| Cross-branch common view | Replace with derived board view | It inspects separately authoritative ledgers; it never fuses them. |
| Pre-reserved Task Packet reflection paths/IDs | Retire | A workstream writer receives the canonical ledger path and expected digest at append time; no content-independent participant reservation is needed. |

The implementation must mark all old-format public names as `v1` compatibility behavior in help and
reference docs. It must not silently reinterpret a v1 manifest as a workstream ledger or write a v2 record
into a v1 directory.

## Promotion, receipt, closure, and expiry

End-of-turn inspects records actually used by the turn and shows complete local chains plus any declared
dependencies. ESR additionally finds open chains, unresolved heads, stale phase handoffs, missing evidence,
receipt gaps, and eligible expiry candidates. Both are advisory discovery; the orchestrator makes the durable
judgment.

For promotion, the orchestrator writes a normal guarded session decision first. Its decision body contains a
compact canonical `reflection_receipts` block: workstream ID, chain ID, member and head record IDs, one
sentence conclusion, disposition, record-content digest, local ledger digest, and promoted decision locator.
It names no temporary path. The session writer's normal chronology, DRAFT, topics, lifecycle-link, ADR review,
and branch checks still apply.

A chain closes only after that chain's required implementation and independent review coverage, an orchestrator
synthesis or explicit disposition, every one of its divergent heads resolved/disposed, and durable receipt
coverage for every one of its members. Its own `closed_at` starts the configured retention window; its
`expires_at` is derived, never caller-selected. Ordinary
expiry removes only that eligible chain's blocks through the canonical cleanup operation. It refuses an open,
unreviewed, unelapsed, incomplete, or cross-ledger-dependent chain. Early removal remains limited to an
unpromoted, otherwise valid chain with a verified live-user approval and durable disposition. A board-wide
wipe remains forbidden.

Receipt resolution accepts both v1 and new ledger receipts. It scans ordinary sessions only, rejects
conflicting duplicate receipts, and proves that a cross-ledger dependency still has a durable target after
active detail expires. The derived receipt index may accelerate this lookup but is rebuildable and never
authoritative.

## Surface and control-plane changes

| Surface | Required evolution |
| --- | --- |
| Core | Add a versioned standalone parser, canonical append planner, phase/etag validator, local-chain resolver, dependency resolver, and derived board projection. Keep `parse_workstream_ledger` and public normal validation strict; the shared trusted-Git loader must classify the complete path history as monotonic normal or proof-admitted compaction before returning either. Put the structural-only primitive behind a private verifier that can run only after its exact Git/session proof succeeds. Preserve v1 parser, fuse, receipt, and closeout readers behind explicit compatibility routing. |
| CLI | Add outcome-level `reflection ledger init`, `append`, `check`, `view`, `close`, and `expire`; init permits only retention 7, 14, or 30, reloads a host-owned admitted preflight for 14/30, and mints its own candidate identity for 7; append owns time/identity/head lookup. `check`, `view`, `append`, `close`, and `expire` load through the one history-aware trusted-Git core loader. `expire --apply` owns the protected two-commit proof pair; it accepts no caller-supplied proof fields. Add read-only `reflection board view`. Make old fragment/fuse commands visibly v1-only. |
| MCP | Add parity read operations for ledger and board views and guarded append/close/expire paths that call the same history-aware core loader, planner, and Git/session adapter. Return identical rendered bytes and `{code, path, message, details}` errors. MCP accepts no raw proof, commit/blob, post-image, or arbitrary file-write input; it has no merge or early-expiry-approval bypass. |
| ESR | Report per-chain workstream-ledger phase state, unresolved chains/heads, missing receipt coverage, broken real dependencies, per-chain expiry candidates, and each trusted ledger's `normal` or `admitted-compaction` history classification/proof diagnostic. It must distinguish v1 fragment boards from fresh and admitted-compacted v2 ledgers. |
| `agent_collaboration.md` and Seed twin | Replace new-board guidance that assigns fragment reservations with the one-branch sequential handoff: planner -> implementer -> reviewer -> orchestrator; retain separate worktrees for parallel features. |
| `session_logging.md` and Seed twin | Specify the compact embedded receipt locator for the new ledger and preserve v1 receipt reading. Do not make a reflection append a session write. |
| `end_of_turn.md` and Seed twin | Add ESR discovery of a current workstream ledger and promotion/close/expiry review prompts. |
| `policy.md`, `agent-rules.md`, Constitution | No change is planned: the current append-only, write-parity, workstream, and Constitution 1.12 rules already authorize this evolution. Amend only if implementation finds a real contradiction, not to restate mechanics. |
| Documentation | Add a live spec only after implementation and ratified review; update the new plan, generated Todo/front-door indexes, CLI/MCP references, and task-packet guidance together. |

## Migration and compatibility posture

There is no migration, conversion, or backfill. Existing v1 plans keep their participant fragments, manifests,
fuse trailers, closeouts, expiry semantics, record IDs, and receipts. Their current readers and verifier tests
remain required regression coverage. A new workstream ledger begins only through the new explicit init path.

The compatibility boundary is a discriminator, not heuristic detection: v1 paths retain `manifest.yaml` and
`memory-seed/reflection-plan`; v2 paths contain only the declared workstream-ledger schema. A path that mixes
forms or asks a v2 command to write v1 data fails closed. No existing Task Packet or experiment log is
rewritten.

## Test matrix and acceptance criteria

| Area | Positive proof | Required negative controls |
| --- | --- | --- |
| Ledger identity and append | Canonical init/append produces reproducible bytes, generated IDs, and a conclusion-first block. | Forged ID, manual timestamp, noncanonical bytes, stale ledger digest, stale Git tip, and direct file overwrite all refuse. |
| Phase ownership | Multiple independent root chains may each complete a planner/implementer/reviewer/orchestrator loop, including implementer rework after review. | Wrong target-chain role, skipped review, phase regression, concurrent/stale writer, and orchestrator-only action by another role refuse. |
| Chains | Local parent, correction, challenge, combine, and all-head view work. | Cross-ledger parent, orphan without judgment, dangling/cyclic parent, silent derived override, and hidden divergent head refuse. |
| Dependencies | A real dependency resolves first from an active ledger then from its durable receipt after expiry. | Similar-topic link without dependency reason, wrong digest, self-dependency, missing target, expired target without receipt, and dependency-as-parent refuse. |
| Board view | Multiple active ledgers produce a labelled, sorted, read-only combined projection, including malformed candidates as diagnostics. | A board command that omits a malformed active candidate, emits a winner, writes a ledger, fuses records, or promotes a decision fails/refuses. |
| Promotion and receipts | Many chains to one decision and one chain to several decisions resolve from ordinary sessions alone. | Temporary path reference, missing member coverage, conflicting duplicate receipt, bad decision locator, malformed digest, and receipt from an uncommitted session blob refuse. |
| Close and expiry | Validated reviewed chains close independently and expire at that chain's `closed_at + retention`; peers remain active. | Board wipe, open/unreviewed/unresolved chain, a retention value outside 7/14/30, missing/forged/replayed/expired or Git-unadmitted extension approval, early promoted cleanup, and cleanup of a dependency target still required by an open chain refuse. |
| Admitted compaction proof | Real-Git fixtures prove both strict-invalid middle removal and strict-valid tail-chain or sole-chain/header-only removal are admitted only by their canonical two-commit session/Git proof. The loader proves every pre/post blob and digest, chain/member closure receipts, byte-removal derivation, then accepts a fresh suffix append whose predecessor binds the compacted bytes. Repeated tail and header-only compactions recurse through each earlier proof. | Raw tail-chain or sole-chain/header-only deletion without a proof; missing/uncommitted/noncanonical receipt; wrong session trailer, entry, decision, path, workstream, pre-tip, commit, blob, mode, digest, parent, reachability, or restricted diff; receipt/event replay, conflicting duplicate/incomparable proof, stale non-prefix bytes, missing/forged close or member receipt, partial-chain/extra-ID/rebind removal, re-rendered retained block/header, inserted cleanup block, altered separator derivation, raw `verify_predecessors=False`, and caller-supplied CLI/MCP proof all refuse. |
| History-aware readers and board | Ledger check/view, guarded append/close/expiry, dependency resolution, ESR, and a board with normal plus compacted candidates all route through the same trusted-history loader; a normal image is so labelled only after append/rebind-only history proof, while a proven compacted candidate is `valid` with `validation: admitted-compaction`. The board remains read-only. | A strict-valid tail or sole deletion classified as normal; a reader that bypasses history/admission, chooses an ambiguous proof, hides a missing/forged proof candidate, converts v1, writes a cache as authority, or lets a stale append/cleanup write fails. |
| Compatibility | Existing `tests/test_reflection_ledger.py` v1 fixtures still parse, view, close, expire, and fuse. | A v2 writer pointed at a v1 board, v1 fuse pointed at v2 data, or mixed family directory refuses. |
| Surface parity | CLI and MCP return the same valid result, rendered bytes, and diagnostics for shared fixtures. | One surface accepting an invalid append or bypassing phase/approval validation fails parity tests. |

Acceptance is complete only when the existing v1 suite and new focused ledger, real-Git compaction, surfaces,
ESR, session, and worktree integration suites pass; `docs check`, `docs index --check`, `links check`, and
`git diff --check` pass; and an independent reviewer confirms that no v2 path reintroduces per-participant
fusion as authority or a general predecessor-validation bypass.

## Delivery sequence and owners

1. **Architecture gate — independent amendment review required.** The v2 schema, phase policy, record/chain
   vectors, dependency semantics, and v1 boundary remain frozen. The review must approve this narrowly scoped
   history-aware admitted-compaction correction before implementation restarts; it must not turn a
   structural-only check into a public parser mode or classify a strict-valid deletion as normal.
2. **Core ledger track — one implementation owner.** Add standalone strict versus trusted-history loading,
   canonical raw-block removal derivation, bounded Git path-history classification, real-Git proof-pair
   verification, recursive repeated-compaction validation, append etag/phase checks, local chain logic,
   dependency resolver, derived board view, close/expiry adaptation, and v1 routing. Own focused
   normal/admitted and real-Git negative tests. No CLI/MCP/control-plane edits in this track.
3. **Surface track — one owner after core API freeze.** Add the shared CLI/MCP Git-session adapter, protected
   two-commit expiry composition, parity reads/writes, ESR proof reporting, help/reference text, and surface
   tests. It consumes the core loader; it does not duplicate history/admission validation or accept raw proof
   data.
4. **Workflow track — one owner after surface behavior is tested.** Update active/seed skill twins and
   Task Packet materialization only where the old fragment reservation instruction would mislead new work.
   Do not broaden worker authority or add a dispatcher.
5. **Integration and compatibility gate — orchestrator.** Run a real multi-worktree simulation with two
   parallel feature ledgers and a genuine dependency, then promote/close/expire one chain while the other
   remains active. Run all v1 regressions before landing.
6. **Independent final review.** Review the final diff, receipts after simulated expiry, CLI/MCP error
   parity, and absence of a fused or combined authority. Any format change lands before the first v2 ledger
   data, and no v2 data is authored on the format branch.

The orchestrator owns workstream initialization, branch integration, durable session append, promotion,
closeout, and cleanup. Planner, implementer, and reviewer own only their sequential blocks in the branch
ledger. Parallel features get separate worktrees and separate ledger owners. The reviewer never validates
from an unmerged implementer assumption when an integrated branch is available.

## Measurable complexity reduction

The implementation review must report these counts before and after, with a short explanation for every
exception:

| Measure | v1 baseline | v2 target |
| --- | ---: | ---: |
| Authoritative active files required for one workstream contribution | manifest + report + fragment (3) | one ledger (1) |
| Per-worker identifiers/paths that must be reserved before work | report ID/path + fragment ID/path (4) | none |
| Cross-branch reflection integration mechanism | participant fuse plus coordinated merge | none for v2; normal branch integration plus ledger receipt |
| Authoring round trips before a record can be written | manifest reservation, report, fragment, fuse | one guarded append with expected tip/digest |
| New-board writer roles that can mutate authority concurrently | multiple reserved participants | exactly one CAS-protected append at a time, authorised per target chain |
| New-board authoritative combined views | one plan common view built from fused fragments | zero; all multi-ledger views are derived |

The target is not fewer safeguards. It is fewer independently coordinated artifacts while preserving canonical
append validation, ownership, provenance, receipt coverage, and controlled expiry. If the v2 implementation
does not reach one active file and one guarded append for the ordinary sequential path, it must document why
and return to architecture review rather than retaining v1 machinery by habit.

## Review questions

1. Does one ledger per branch accurately match the actual writer sequence without preventing a review/rework loop?
2. Are old fragment/fuse boards preserved as read-only historical truth, with no hidden migration?
3. Can a real cross-workstream dependency resolve after the source chain expires, without importing or
   ranking its temporary detail?
4. Does every writer surface share the same append, phase, stale-write, receipt, and early-expiry checks?
5. Is the combined board visibly derived and incapable of selecting truth, fusing history, or creating a
   durable decision?
6. Does every compacted read prove its exact committed pre-image, deletion derivation, and ordinary-session
   receipt pair while leaving fresh normal validation unchanged?

## V2 schema annex — frozen implementation contract

This is the normative v2 contract; it controls over earlier illustrative text. It does not alter v1
`memory-seed/reflection-plan`, historical plans, or past session evidence.

### Family, bytes, and identity

| Item | Frozen rule |
| --- | --- |
| Discriminator | v2 front matter is exactly `schema: memory-seed/reflection-workstream-ledger` and `version: 2`; v1 remains `memory-seed/reflection-plan` at version 1. Absent, duplicate, mixed, or unsupported forms are malformed, never inferred. |
| Path | The only active v2 path is `.memory-seed/reflections/active/<workstream_id>/ledger.md`; its directory contains no `manifest.yaml`. v2 commands reject v1 paths and conversely. |
| Bytes | UTF-8 without BOM, Unicode NFC, LF only, no trailing whitespace, exactly one final LF. YAML has two-space indentation and the exact field order below. Digests are lowercase `sha256:` plus 64 hex. |
| Header order | `schema`, `version`, `workstream_id`, `working_branch`, `base_sha`, `created_at`, `reflection_retention_days`, `retention_extension_receipt`, `retention_approval_key_id`, `id_salt`. No other header field is accepted. `base_sha` is 40 lowercase hex; every timestamp is UTC RFC 3339 in `YYYY-MM-DDTHH:MM:SSZ` form; `id_salt` is 64 lowercase hex from OS entropy. Header bytes never change. State and phase derive per chain from validated blocks. |
| Retention | `reflection_retention_days` is exactly integer `7`, `14`, or `30`. At `7`, `retention_extension_receipt` and `retention_approval_key_id` are literal `null`. At `14` or `30`, both are required and must pass the admitted host-approval contract below. No other value, caller string, or environment variable is an authority. |
| Digests | Ledger digest is `sha256(LEDGER_DOMAIN || canonical_ledger_bytes)` and detail digest is `sha256(DETAIL_DOMAIN || canonical_record_block_bytes)`. `LEDGER_DOMAIN` is ASCII `memory-seed/reflection-workstream-ledger/v2/ledger` plus NUL; `DETAIL_DOMAIN` substitutes `detail` for `ledger`. |

### Retention extension approval — admitted host contract

The v2 extension gate normatively reuses the landed v1 model: an Ed25519 private key stays with the approving
host; the repository receives only canonical signed bytes; and a verifier trusts the key only through a
Git-admitted immutable anchor. This retention-setting approval is distinct from the existing v1 early-expiry
approval; neither form can substitute for the other.

The v2 trust anchor is `.memory-seed/reflections/trust/retention-approval.yaml` as it exists at the ledger's
immutable `base_sha`. It is a Git-admitted UTF-8/NFC/LF document with this exact YAML mapping and no extra
keys:

```yaml
schema: memory-seed/reflection-retention-approval-trust
version: 1
key_id: <stable-token>
public_key: ed25519:<32-byte-lowercase-hex>
```

`reflection ledger init` derives `base_sha` from the workstream's protected integration base; it accepts no
caller-provided base SHA. The base must already be reachable from that protected integration history, so a
feature branch cannot introduce its own trust anchor. Init resolves that exact anchor blob from `base_sha`; for
a 14- or 30-day header its `retention_approval_key_id` must equal `key_id`. It accepts no public key from CLI,
MCP, task packet, or working-tree file. The verifier uses the anchor's `public_key`, the landed RFC 8032
Ed25519 verifier, and no agent callback or private key.

For 14/30, the only entry point is a canonical host-owned retention preflight. It derives the protected base
and current branch, mints the OS-random `id_salt` and `nonce`, takes the host clock's `created_at`, computes
the workstream ID with the frozen 96-bit ID procedure, and selects the requested period. It has no caller
parameters for `id_salt`, `created_at`, `workstream_id`, branch, base, nonce, approval timestamps, or session
identity. The host first obtains the normal session writer's planned `session_path`/`entry_id`, then persists
this exact candidate as one canonical fenced YAML block under `### Reflection retention preflight` in that
normal Memory Seed session entry. The entry is committed before the host signs anything.

The persisted preflight has this exact ordered YAML mapping and no extra keys:

```yaml
schema: memory-seed/reflection-retention-preflight
version: 2
key_id: <stable-token>
id_domain: memory-seed/reflection-workstream-ledger/v2
id_kind: workstream
workstream_id: <computed-rwl_...>
working_branch: <exact-origin-branch>
base_sha: <40-lowercase-hex>
id_salt: <64-lowercase-hex>
created_at: <UTC-RFC3339-seconds>
retention_days: 14|30
scope: ledger
chain_id: null
nonce: <64-lowercase-hex>
approved_at: <UTC-RFC3339-seconds>
expires_at: <UTC-RFC3339-seconds>
reason: <non-empty-text>
session_path: .memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md
entry_id: <mse_...>
```

`id_domain`, `id_kind`, `id_salt`, `working_branch`, `base_sha`, and `created_at` are every workstream-ID
preimage element; the verifier recomputes `workstream_id` from them and rejects any mismatch. `scope` is
literal `ledger` and `chain_id` literal `null`: one immutable header supplies retention for all chains. The
host mints `nonce`, `approved_at`, and `expires_at` before the approval signature; expiry is after approval
and at most 24 hours later. The planned path/entry must equal the entry actually persisted by the normal
session writer.

After that session entry is committed, the host reloads it from Git, resolves its `commit` and exact `blob`,
and signs this canonical v2 payload. It has the preflight fields plus the complete admitted locator; no caller
may render, complete, or recompute it. The signature covers canonical UTF-8 bytes through `blob`, excluding
only `signature`:

```yaml
schema: memory-seed/reflection-retention-approval
version: 2
key_id: <stable-token>
id_domain: memory-seed/reflection-workstream-ledger/v2
id_kind: workstream
workstream_id: <computed-rwl_...>
working_branch: <exact-immutable-origin-branch>
base_sha: <40-lowercase-hex>
id_salt: <64-lowercase-hex>
created_at: <UTC-RFC3339-seconds>
retention_days: 14|30
scope: ledger
chain_id: null
nonce: <64-lowercase-hex>
approved_at: <UTC-RFC3339-seconds>
expires_at: <UTC-RFC3339-seconds>
reason: <non-empty-text>
session_path: .memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md
entry_id: <mse_...>
commit: <full-lowercase-git-commit-oid>
blob: <full-lowercase-git-blob-oid>
signature: ed25519:<64-byte-lowercase-hex>
```

The immutable header's `retention_extension_receipt` is an ordered mapping: `nonce`, `session_path`,
`entry_id`, `commit`, `blob`, `signature`. Every one of those fields, plus all candidate preimages and
bindings, must equal the signed payload; `retention_approval_key_id` equals its `key_id`. `commit` and `blob`
name the preflight session file (`blob == object_at(commit, session_path)`). At 7 days the receipt and key ID
are literal `null` and no preflight, signature, or trust-anchor lookup occurs.

The signed branch must exactly equal the immutable header's origin `working_branch`. After a valid trusted
rebind, a verifier may operate only on that rebind's validated target branch; the signed origin binding remains
unchanged and no caller-supplied branch is accepted. This binds the approval to workstream identity, every ID
preimage, ownership, period, and committed locator without creating a header/digest circularity.

For 14/30, init accepts only an opaque host-issued preflight handle. It reloads the preflight session from the
committed locator and asks the host for the matching signed payload; it accepts no candidate values, rendered
approval, signature, or preimage from CLI/MCP/task-packet callers and never recomputes a replacement candidate.
Admission succeeds only when payload and persisted preflight both parse/re-render canonically; their common
fields are byte-for-byte equal; schema/version, types, allowed period, timestamps, nonce, and signature syntax
are valid; the frozen workstream-ID algorithm recomputes the payload ID; the signature verifies under the
`base_sha` trust anchor and matching key ID; `now < expires_at`; every signed ID preimage, workstream ID,
branch/base/period/scope binding, and header receipt field equals its required header value; any post-rebind
checkout is the exact verified target; the cited committed session entry passes normal session parsing and
contains the exact preflight; `commit` is reachable from the init checkout; and `blob` equals the session-file
object at that commit.

The exact nonce replay identity is `(schema, version, key_id, nonce)` from the signed approval. The exact
locator replay identity is `(session_path, entry_id, commit, blob)`. The verifier scans Git-admitted v2 headers
and refuses if either identity is already bound by another immutable ledger header; the preflight session's
single original occurrence is not itself consumption. A successful init reserves both identities for exactly
one header. Any missing anchor, untrusted key, noncanonical/mismatched preflight or payload, malformed locator,
wrong object binding, unreachable commit, changed session block, bad signature, expired approval, candidate or
header binding mismatch, or either replay returns structured `retention-approval` and writes no ledger. A raw
`--retention-days`, `--approval`, `--id-salt`, `--created-at`, `--workstream-id`, MCP field, environment value,
copied signed text, or agent assertion cannot bypass these checks.

The normal seven-day path needs no extension approval: the canonical init writer mints `id_salt` and
`created_at`, derives branch/base and computes `workstream_id` inside its one guarded init transaction, then
renders `retention_extension_receipt: null` and `retention_approval_key_id: null`. It accepts no caller
preimage material and does no preflight/session/host-signature/trust-anchor lookup.

The ID domain is ASCII `memory-seed/reflection-workstream-ledger/v2` plus NUL. For each ID,
`frame = ID_DOMAIN || hex_decode(id_salt) || components`, where each component is
`uint32_be(len(UTF-8(component))) || UTF-8(component)`. SHA-256 the frame, interpret the first 12 digest
bytes as one unsigned 96-bit big-endian integer, then encode that integer as exactly 20 lowercase Crockford
Base32 characters (`0123456789abcdefghjkmnpqrstvwxyz`), left-padded with zero characters. The canonical
writer supplies all components. This is a 96-bit procedure: the first four bits of the 20-character encoding
are zero padding, not additional digest bits.

| ID | Prefix and ordered components |
| --- | --- |
| workstream | `rwl_`; `workstream`, `working_branch`, `base_sha`, `created_at` |
| record | `rlr_`; `record`, `workstream_id`, `created_at`, `pre_ledger_digest` |
| chain | `rlc_`; `chain`, `workstream_id`, `first_record_id` |
| receipt | `rrc_`; `receipt`, `workstream_id`, `chain_id`, `detail_digest` |

Golden vector: with `id_salt` = `8f` repeated 32 times, branch `codex/feature/example`, `base_sha` = `a`
repeated 40 times, and creation at `2026-09-06T12:00:00Z`, workstream ID is
`rwl_1j3nf0zkee6vx8zgg4v3`. With pre-digest `sha256:` + 64 zeroes and time `2026-09-06T12:01:00Z`, record ID
is `rlr_0fcr9wh0xh9yn0nhyqyn`; chain ID is `rlc_1mhbzbsjzv646b2k845s`; with detail digest `sha256:` + 64
ones, receipt ID is `rrc_0hge300ydfdke03v8hfh`. For exact bytes `example\n`, vectors are
`sha256:aa964f81fd64a3e391f79079266e4e8f5e4dfe27a36f29078228a57762af46fc` under `LEDGER_DOMAIN` and
`sha256:520584969953ed7b72863bf987e267e297e4afed3ed2af2f6691e6bd6915014c` under `DETAIL_DOMAIN`.

### Records, chains, and transitions

Every ordinary block begins `## Record <record_id>` and lists, in order: `record_id`, `created_at`, `role`,
`from_phase`, `to_phase`, `closed_at`, `chain_id`, `parents`, `relationship`, `no_related_thread`,
`depends_on`, `source`, `related_decisions`, `confidence`, `pre_ledger_digest`, `detail_digest`. Headings are
`### Conclusion`, `### Reasoning`, then optionally in order `### Assumptions`, `### Alternatives`,
`### Evidence`, and `### Next step`. Conclusion and reasoning are non-empty. Lists are canonical sorted lists,
never scalars. `detail_digest` is computed over the canonical whole block with its own value replaced by 64
zeroes.

`parents` is a list of local `rlr_` identifiers. `relationship` is exactly one of `no_related_thread`,
`refines`, `responds`, `challenges`, `corrects`, `combines`, or `orphan`; `orphan` requires an explicit
judgment in Reasoning. `no_related_thread` is a required JSON/YAML boolean: it is `true` only for a root
record with `parents: []` and relationship `no_related_thread`; it is `false` for every non-root record and
forbids that relationship. A root is legal after ledger initialization at any time and creates a new chain;
it does not inherit another chain's phase. `closed_at` is literal `null` except on an
`orchestrate -> closed` record, where it is a UTC timestamp exactly equal to `created_at`. Thus chain phase,
closure, retention, and expiry are all per-chain, not ledger-wide.

Each newly created root chain begins in phase `plan`. A block must use precisely one transition below for its
own `chain_id`. A non-advancing note has equal `from_phase`/`to_phase` and is allowed only to that chain
phase's owner. Different chains may be at different phases, but a successful append still serializes the
whole ledger through one expected-head/digest compare-and-swap.

| From | To | Role | Rule |
| --- | --- | --- | --- |
| `plan` | `implement` | planner | Establishes an implementable conclusion. |
| `implement` | `review` | implementer | Submits evidence for independent review. |
| `review` | `implement` | reviewer | Specific correction or rejection. |
| `review` | `orchestrate` | reviewer | Approved review handoff. |
| `orchestrate` | `closed` | orchestrator | Post-merge receipt/disposition only. |

No transition skips review or regresses except `review -> implement`; a closed chain accepts no ordinary
append. A root has no parents and requires `no_related_thread`; every later parent is local to its own chain
and validated. A ledger begins with zero chains. Each root record creates one new chain; that chain cannot be
renamed, merged across ledgers, or reconstructed from a board.

### Dependencies, board visibility, and branch collision

`depends_on` is a list of ordered objects: `workstream_id`, `record_id`, `record_digest`, `reason`,
`receipt`. `receipt` is `null` only while the target is guaranteed active, otherwise it is the ordered fallback
`session_path`, `entry_id`, `decision_id`, `receipt_id`, `receipt_digest`. The fallback identifies a normal,
committed session receipt for that exact workstream/record/detail digest. An active dependency that could
outlive its target must include a fallback at append time; append-only records are never patched later.
Target-chain closeout refuses a still-open dependent without verified fallback. Resolution prefers the active
record then the verified receipt; a dependency is never a parent or imported detail.

`reflection board view --active` scans every immediate directory under `reflections/active`, including a
directory that cannot parse. Each output item has `path`, status `valid`/`malformed`/`unsupported`, raw file
digest when readable, safely recoverable `workstream_id`, origin `working_branch`, effective owner branch, and
structured diagnostic.
Only valid ledgers enter the derived graph. The command returns the complete view and non-zero if any candidate
is malformed or unsupported: it must not hide an unhealthy active ledger.

Exactly one valid active v2 ledger may effectively own a branch (the immutable header branch until a validated
trusted rebind, then the rebind target). Init rejects a second claim, copied directory, duplicate workstream
ID, or malformed candidate whose recoverable header claims the branch. A malformed ownerless candidate blocks
init rather than being ignored. Rebind rejects any active or ambiguous target claim. Required negatives cover
duplicate valid claims, copied directories, malformed same-branch claim, malformed ownerless candidate, and
rebind into an occupied branch.

### Trusted rebind and closeout authority

Before merge, the feature branch is sole owner: planner, implementer, reviewer, and orchestrator may make only
their permitted append. The orchestrator may synthesize readiness but may not create a durable session receipt,
close a chain, expire data, or transfer ownership. A branch name alone never proves transfer.

After successful normal feature integration, only the orchestrator on the integration branch may promote,
close, or clean up. The integration operation is the only trusted rebind mechanism: preview creates an opaque
token bound to source branch/tip, target branch/pre-merge tip, workstream ID, and pre-rebind ledger digest.
Apply verifies token, integrated source tip, and current target tip. Arbitrary CLI/MCP `--to-branch` rebind is
forbidden.

Trusted integration appends `## Rebind <record_id>` before closeout with this exact order: `record_id`,
`created_at`, `role` (always `orchestrator`), `from_branch`, `to_branch`, `source_tip`,
`target_pre_merge_tip`, `integration_commit`, `pre_ledger_digest`, `detail_digest`, `reason`. It uses the
ordinary record ID framing and zero-substitution detail digest, has no parents/transition, and changes the
effective owner only after validation. The immutable header remains origin evidence.

Post-merge closeout appends the guarded Memory Seed decision and embedded receipt, then one target chain's
`orchestrate -> closed` block in that integration checkout. It requires trusted rebind, integrated source tip,
that chain's complete review/disposition, resolved heads, and durable member receipts. The receipt states
origin branch, integration branch/commit, pre-close digest, and that chain's closed IDs. A source checkout
cannot manufacture it.

### Safe expiry and compaction

Expiry replaces only complete eligible chain blocks; it never changes durable sessions, header bytes, retained
blocks, v1 data, or a whole board. Preview reads current HEAD and canonical bytes and returns `expected_head`,
`pre_ledger_digest`, sorted `removed_chain_ids`, sorted `removed_record_ids`, exact `post_ledger_digest`, and
the fixed disclosure `git_blobs_remain: true`, `privacy_grade_erasure: false`. Thus every preview states that
Git history/blob retention may preserve removed data and that expiry is lifecycle cleanup, not privacy-grade
erasure. The resulting expiry result and durable cleanup receipt repeat the same disclosure. It appends no
cleanup block. The following admitted-compaction contract replaces only the unsafe assumption that this
post-image remains normally self-validating.

#### Standalone parser and trusted-history loader

`parse_workstream_ledger` is the **standalone** v2 parser. It continues to reject any block whose
`pre_ledger_digest` is not the digest of the preceding canonical bytes. Its public validator has no
`verify_predecessors=False` escape hatch. It answers only whether supplied bytes are a canonical standalone
ledger; it does not read Git history and must not label a strict-valid image as a trusted normal ledger.

Every product read obtains its result from one private `load_trusted_workstream_ledger` operation. It accepts
only the host-selected trusted ledger head and canonical `ledger_path`, reads that exact tree blob rather than
a worktree copy, and returns either `NormalTrustedLedger` or `AdmittedCompactedLedger`. The trusted head is the
admitted workstream branch before integration and the trusted integration branch after a validated rebind.
`check`, `view`, guarded append/close/expiry, dependency resolution, ESR, and active-board discovery cannot
select another loader, a Git ref, a blob, or a validation mode. A trusted image is **normal** only when both its
standalone parse and its complete trusted path history prove canonical initialization followed exclusively by
monotonic canonical append blocks (including the canonical appended rebind record). No record block may be
deleted, rewritten, reordered, or inserted before existing bytes in that classification.

The loader builds the unique ledger lineage from the canonical init image reachable after the immutable
header's `base_sha` through the trusted head. A merge may carry exactly one already-valid ledger parent while
the other parent has no ledger path, as normal branch integration does. Any merge with two unequal
ledger-bearing parents, an untraceable genesis, or an ambiguous predecessor lineage refuses; it is never
silently resolved by Git first-parent order. Each lineage transition is classified against its two committed
tree blobs: an exact canonical suffix append/rebind is monotonic; every other ledger-path change is
non-monotonic. Thus removal of a middle chain, a tail chain whose survivors still pass standalone validation,
or the only chain leaving a header-only ledger all require compaction admission. A later suffix appended to a
compacted image retains that admitted classification even if the resulting bytes pass the standalone parser.

`admit_compacted_workstream_ledger` is the internal branch of that loader for a non-monotonic transition. It
is not a permissive parser: it accepts an otherwise structurally valid v2 byte sequence only after it
reconstructs a chain of committed compaction proofs from ordinary sessions and Git. Its structural helper is
private and receives no caller-selected boolean or raw proof. A returned `AdmittedCompactedLedger` carries the
exact current bytes, ordered verified proof chain, and ordinary suffixes after each proof; callers cannot turn
an arbitrary `WorkstreamLedger` into that type.

#### Bounded lineage traversal and derived cache

The trusted-history walk is deterministic, streaming, and bounded. It examines path-affecting commits in
chronological order, in pages of at most `128` transitions and at most
`MAX_TRUSTED_LEDGER_HISTORY_TRANSITIONS = 4096` transitions per load. It keeps only the active page, current
lineage state, and proof stack in memory. Crossing that limit, a missing required ancestor, or an ambiguous
path topology returns `compaction-proof-history-limit`, `compaction-proof-history-missing`, or
`compaction-proof-history-ambiguous`; it does not truncate the walk or guess that older history was normal.

An optional bounded LRU cache may retain parsed transition facts and proof results, but it is derived only. Its
key is the loader version plus a recomputed history fingerprint:
`sha256` of the ordered `(commit, canonical_parent, ledger_path, parent_mode, parent_blob, mode, blob,
transition_kind)` tuples, the init commit, and the trusted head. The loader recomputes that fingerprint from
Git before a cache hit can be used, then rechecks each cached proof's tree/blob bindings. Cache loss,
corruption, eviction, or a changed ref merely causes the bounded Git/session scan; no cache file, session
entry, or sidecar can create authority or make an over-limit/invalid history acceptable.

#### Canonical cleanup receipt and Git pair

One compacted image is authorised by exactly one canonical fenced YAML document named
`memory-seed/reflection-workstream-compaction`, version `1`, inside one ordinary session entry under
`### Reflection workstream compaction`. The normal session writer owns the entry timestamp, identity, DRAFT
shape, decision review, and final `Memory-Entry: <entry_id>` trailer. The receipt's fields are ordered exactly
as below; no additional field is permitted.

```yaml
schema: memory-seed/reflection-workstream-compaction
version: 1
workstream_id: <rwl_...>
ledger_path: .memory-seed/reflections/active/<workstream_id>/ledger.md
pre_ledger_digest: sha256:<64-lowercase-hex>
post_ledger_digest: sha256:<64-lowercase-hex>
pre_tip: <40-lowercase-hex>
pre_blob: <40-lowercase-hex>
cleanup_commit: <40-lowercase-hex>
post_blob: <40-lowercase-hex>
removed_chain_ids:
  - <rlc_...>
removed_record_ids:
  - <rlr_...>
closure_receipts:
  - chain_id: <rlc_...>
    closed_record_id: <rlr_...>
    closed_record_digest: sha256:<64-lowercase-hex>
    session_path: .memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md
    entry_id: <mse_...>
    decision_id: D1
    commit: <40-lowercase-hex>
    blob: <40-lowercase-hex>
    receipt_digest: sha256:<64-lowercase-hex>
member_receipts:
  - chain_id: <rlc_...>
    record_id: <rlr_...>
    detail_digest: sha256:<64-lowercase-hex>
    session_path: .memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md
    entry_id: <mse_...>
    decision_id: D1
    receipt_id: <rrc_...>
    receipt_digest: sha256:<64-lowercase-hex>
    commit: <40-lowercase-hex>
    blob: <40-lowercase-hex>
    disposition: promoted-to-decision|already-covered-by-decision|expired-unpromoted|early-expired-unpromoted
reason: <non-empty canonical text>
git_blobs_remain: true
privacy_grade_erasure: false
```

The sorted `closure_receipts` list contains exactly one admitted close receipt for every removed chain. The
sorted `member_receipts` list contains exactly one admitted durable disposition/promotion receipt for every
removed record; its locator and parsed contents must equal the referenced ordinary-session receipt. Therefore
the cleanup receipt names all closure and promotion evidence, but does not duplicate their authority.

A Git object ID cannot truthfully name the commit that contains itself. The cleanup therefore uses a protected,
atomic **two-commit pair**, not an impossible self-referential one:

1. `cleanup_commit` has exactly one parent, `pre_tip`, changes only `ledger_path` from regular `100644`
   `pre_blob` to regular `100644` `post_blob`, and has no other tree change. `pre_blob` is the object at
   `pre_tip:ledger_path`; `post_blob` is the object at `cleanup_commit:ledger_path`.
2. `receipt_commit` has exactly one parent, `cleanup_commit`, changes only the receipt's `session_path`, and
   contains exactly one canonical matching compaction receipt in the named entry. Its final trailer block has
   exactly one matching `Memory-Entry: <entry_id>`. `receipt_commit` is derived from the admitted session
   locator; it is deliberately not a self-referential receipt field.
3. The CLI/MCP Git-session adapter constructs both commits off-ref, then compare-and-swaps the protected
   branch from `pre_tip` to `receipt_commit`. It never exposes or publishes a one-commit rewrite without its
   receipt companion. A crash before the ref update leaves only unreachable objects; a raw rewrite is refused.

This pair binds the session receipt to the exact rewrite by topology, without creating a new authoritative
index or relaxing ordinary session append validation.

#### Exact removal and proof validation

For **every** non-monotonic transition found in the trusted lineage, the loader resolves one and only one
canonical cleanup receipt and its Git pair. It resolves every OID as a commit/blob, confirms reachability from
the current trusted ledger head, and reads its path from the named immutable tree; it never trusts a
worktree copy, a branch label, an uncommitted session, or caller-supplied bytes. The receipt's `pre_tip` must
be that transition's canonical lineage parent and its `cleanup_commit` must be the non-monotonic child. A
strict-valid raw tail or header-only deletion has no such pair and therefore fails with
`compaction-proof-missing`, rather than being reclassified as normal. The pre-image itself must already have
validated as `NormalTrustedLedger` or `AdmittedCompactedLedger`; this ordered recursion is how repeated
compactions stay verifiable.

For one proof, the verifier performs all of the following before it accepts the post-image:

1. The canonical path, header `workstream_id`, lineage parent/child Git trees, blob modes, and the four
   digest/blob bindings agree exactly. `pre_ledger_digest` and `post_ledger_digest` are recomputed from their
   respective blob bytes; `cleanup_commit` is the single-parent child of the exact `pre_tip`; and the receipt
   pair has the exact restricted diffs above.
2. The committed pre-image has the named complete, closed, eligible chains. Its removed chain and record IDs
   are the exact sorted sets described by the receipt—no partial chain, unknown ID, trusted rebind, or retained
   record may be named for removal. Every named closure and member receipt is independently reloaded from its
   declared committed session blob, is reachable no later than `cleanup_commit`, and matches that pre-image's
   close/record/detail/disposition facts.
3. A canonical raw-block scanner derives the post-image from the committed pre-image. It preserves the header
   bytes, order, and bytes of every retained record and rebind block; it removes only the selected record-block
   spans and normalises only their intervening canonical separators. It neither reparses-and-renders retained
   blocks nor inserts a cleanup block. The resulting bytes must equal `post_blob` byte-for-byte. This exact
   derivation, not a structural parse or equal digest alone, is the removal proof.
4. The post-image receives every structural, identity, detail-digest, relationship, phase, dependency, and
   ownership check that remains meaningful after an authorised removal. The predecessor check is satisfied by
   the validated pre-image/removal proof, never skipped as a general parser option.

Receipt discovery scans only ordinary session blobs reachable from the trusted ledger head. For each
non-monotonic lineage transition, the loader demands exactly one receipt whose declared `pre_tip`,
`cleanup_commit`, path, workstream, pre/post blob, and digests bind that transition; it also demands exactly
one matching reachable `receipt_commit`. No receipt may authorise two transition events, and no transition may
choose among duplicate, later, or incomparable receipts. A derived cache may map the recomputed history
fingerprint to candidate session locators, but deleting or corrupting it merely triggers the bounded
Git/session rescan described above. It is not an authoritative durable compaction-proof index.

For a current ledger with later appends, each admitted proof's `post_blob` is the exact image at its cleanup
transition, and every subsequent normal suffix block binds the digest of its actual preceding bytes. The
history classifier preserves the earlier admitted result; it never treats that suffix or a strict-valid tail
post-image as fresh normal history. A later non-monotonic cleanup repeats the exact proof pair against the
then-admitted pre-image, so the returned proof stack contains every prior cleanup in chronological order.

#### Reader routing, continuations, and refusal

Every trusted v2 consumer uses `load_trusted_workstream_ledger`: `reflection ledger check` and `view`, guarded
append/close/expiry, dependency resolution, ESR, and `reflection board view --active`. The loader evaluates
both the strict standalone result and the full history classification on every Git-backed load; it never uses
strict success as an early return. A board still returns every candidate: an append/rebind-only ledger is
`valid` with `validation: normal`, a proven compacted ledger is `valid` with
`validation: admitted-compaction`, and missing, ambiguous, over-limit, or bad proof/history is `malformed`
with its structured diagnostic and makes the board command non-zero. No board reader creates a proof, writes a
cache as authority, silently omits the candidate, or treats a compacted image as a new normal ledger.

An append after compaction reloads the admitted state through that same loader, rechecks expected head, exact
current digest, and history fingerprint, and adds only a canonical new suffix block. That new record's
`pre_ledger_digest` binds the actual compacted bytes that precede it. It never re-renders or rehashes a
retained block. A later compaction repeats the same pair against that admitted pre-image, so a second proof
recursively proves the first and any intervening normal suffix. Old append/cleanup previews become stale and
return `stale_head`, `stale_ledger_digest`, or `stale_ledger_history` without a write; the adapter must reload
and require a fresh judgment.

The verifier fails closed with stable `compaction-proof-*` diagnostics: missing proof or no reachable receipt;
forged/noncanonical session content, entry, trailer, locator, field, digest, blob, path, workstream, coverage,
or derivation; replayed receipt locator/event or conflicting duplicate proof; strict-valid or strict-invalid
non-monotonic transition without its pair; stale current bytes that are not the proven post-image plus normal
suffixes; and unreachable, non-parent, merge, wrong-tree, ambiguous-lineage, over-limit, or no-longer-ancestor
Git evidence. There is no fallback to `verify_predecessors=False`, an arbitrary Git ref, a raw CLI/MCP proof
object, or a cache assertion.

The family discriminator remains the v1 boundary. These receipts and this reader apply only to the declared
v2 ledger path/schema. A v1 manifest, fragment, fuse, closeout, or receipt cannot supply a v2 compaction
proof; v1 retains its existing readers and expiry semantics without conversion.

### Gates and reduction proof

Independent review must approve this amendment before implementation resumes. Golden tests must prove all
vectors, field order, the receipt grammar, two-commit topology, and the trusted-history classifier. Standalone
parser tests reject every forbidden discriminator, header field, byte rule, ID/digest, transition, dependency
fallback, collision, and rebind form; they also prove that a compacted middle image may fail strict parsing
while raw tail-chain removal and sole-chain/header-only removal can remain strict-valid. Real-Git loader tests
then prove that both kinds are refused without their unique cleanup pair and are `admitted-compaction` only
with it. They cover raw tail and sole deletion, valid two-commit tail and sole/header-only deletion, a suffix
append after admission, and repeated trailing then header-only compaction whose proof stack recursively proves
each earlier cleanup.

Admission tests prove exact pre-image/post-image blob and digest bindings, full session/trailer/receipt
coverage, raw byte-removal derivation, monotonic append/rebind-only classification, unique lineage selection,
bounded-history/cache fingerprints, and the absence of an authoritative index. They include the
rebind-then-close rendering round trip that review found untested. Retention tests prove 7 accepts no extension
receipt or preflight, 14/30 reload an exact host-owned committed preflight and require the matching host-signed
schema, and every other value refuses; they cover caller-supplied/recomputed candidate fields, wrong
anchor/key, bad signature, expired payload, any ID-preimage/header mismatch, changed session text,
unreachable commit, wrong blob, and both exact nonce and locator replay identities. Integration tests prove
pre-merge close/expiry refusal, trusted-token rebind, arbitrary rebind refusal, stale append after compaction,
the protected pair never exposes an unreceipted rewrite, and the Git-blob/non-erasure disclosure. CLI, MCP,
ESR, and board parity fixtures must return the same normal/admitted classification and same malformed
diagnostic for all tail, sole/header-only, suffix, repeated, missing-proof, ambiguous-history, and forged-proof
cases. Board tests additionally prove malformed candidates are reported and non-zero. The v1 suite remains
unchanged. The normal v2 path is accepted only with one active authority file, one guarded append, zero
participant reservations, zero v2 fuse operations, append/rebind-only trusted history, and no public
predecessor-validation bypass; every exception is counted and justified as v1 reader/receipt compatibility,
never hidden v2 coordination.
