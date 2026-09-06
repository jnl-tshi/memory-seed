---
title: "Reflection Ledger Workstream Evolution Plan"
date: "2026-09-06"
project: "memory-seed"
status: "active"
priority: "P1"
next_action: "Independently review the single-ledger workstream contract before implementation."
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
  - "A write refuses a stale branch tip, stale ledger digest, invalid phase successor, malformed append, or a writer not authorised for the current phase."
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

## Why the workstream model is simpler

The old model pays for distributed coordination inside one plan: roster sealing, deterministic reservations,
one immutable report/fragment pair per participant, a branch admission fuse, and a coordinated
session/reflection merge. Those controls prevent concurrent authors from colliding. They are unnecessary for
one serial branch writer and obscure the actual unit of work: a feature workstream.

The new invariant is small and explicit:

```text
one workstream branch -> one active ledger -> one current writer -> append-only records
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
`base_sha`, `created_at`, `reflection_retention_days`, and `id_salt`. State and phase are derived from the
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

The header's phase policy allows the normal loop:

```text
plan -> implement -> review -> (implement correction -> review)* -> orchestrate -> close
```

Only the role allowed by the current phase can append a phase-advancing record. A planner may start a chain;
an implementer may add observations, opinions, risks, and corrections; a reviewer may respond, challenge, or
approve/reject with evidence; and only the orchestrator may resolve, promote, close, rebind, or dispose. The
same role can add an explanatory non-advancing record only when it owns the current phase. This is an
authorization and sequence check, not a lock inferred from agent prose.

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
| Early unpromoted expiry approval verification | Retain | The user-gated exception remains necessary. The trust-anchor mechanics are reviewed separately for proportionate implementation. |
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

A chain closes only after required implementation and independent review coverage, an orchestrator synthesis
or explicit disposition, every divergent head resolved/disposed, and durable receipt coverage for every member.
`closed_at` starts the configured retention window; `expires_at` is derived, never caller-selected. Ordinary
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
| Core | Add a versioned single-ledger parser, canonical append planner, phase/etag validator, local-chain resolver, dependency resolver, and derived board projection. Preserve v1 parser, fuse, receipt, and closeout readers behind explicit compatibility routing. |
| CLI | Add outcome-level `reflection ledger init`, `append`, `check`, `view`, `close`, and `expire`; append owns time/identity/head lookup. Add read-only `reflection board view`. Make old fragment/fuse commands visibly v1-only. |
| MCP | Add parity read operations for ledger and board views and a guarded append/close path that calls the same core planner/validator. Return identical rendered bytes and `{code, path, message, details}` errors. No MCP merge, arbitrary file write, or bypass of early-expiry approval. |
| ESR | Report workstream-ledger phase state, unresolved chains/heads, missing receipt coverage, broken real dependencies, and per-chain expiry candidates. It must distinguish v1 fragment boards from new workstream ledgers. |
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
| Phase ownership | A planner/implementer/reviewer/orchestrator loop, including implementer rework after review, records the permitted successor states. | Wrong role, skipped review, phase regression, concurrent/stale writer, and orchestrator-only action by another role refuse. |
| Chains | Local parent, correction, challenge, combine, and all-head view work. | Cross-ledger parent, orphan without judgment, dangling/cyclic parent, silent derived override, and hidden divergent head refuse. |
| Dependencies | A real dependency resolves first from an active ledger then from its durable receipt after expiry. | Similar-topic link without dependency reason, wrong digest, self-dependency, missing target, expired target without receipt, and dependency-as-parent refuse. |
| Board view | Multiple active ledgers produce a labelled, sorted, read-only combined projection, including malformed candidates as diagnostics. | A board command that omits a malformed active candidate, emits a winner, writes a ledger, fuses records, or promotes a decision fails/refuses. |
| Promotion and receipts | Many chains to one decision and one chain to several decisions resolve from ordinary sessions alone. | Temporary path reference, missing member coverage, conflicting duplicate receipt, bad decision locator, malformed digest, and receipt from an uncommitted session blob refuse. |
| Close and expiry | Validated reviewed chains close independently and expire at `closed_at + retention`; peers remain active. | Board wipe, open/unreviewed/unresolved chain, wrong retention deadline, early promoted cleanup, forged approval, and cleanup of a dependency target still required by an open chain refuse. |
| Compatibility | Existing `tests/test_reflection_ledger.py` v1 fixtures still parse, view, close, expire, and fuse. | A v2 writer pointed at a v1 board, v1 fuse pointed at v2 data, or mixed family directory refuses. |
| Surface parity | CLI and MCP return the same valid result, rendered bytes, and diagnostics for shared fixtures. | One surface accepting an invalid append or bypassing phase/approval validation fails parity tests. |

Acceptance is complete only when the existing v1 suite and new focused ledger, surfaces, ESR, session, and
worktree integration suites pass; `docs check`, `docs index --check`, `links check`, and `git diff --check`
pass; and an independent reviewer confirms that no v2 path reintroduces per-participant fusion as authority.

## Delivery sequence and owners

1. **Architecture gate — orchestrator and independent reviewer.** Freeze the v2 schema, phase policy,
   record/chain vectors, dependency semantics, expiry/dependency interaction, and v1 compatibility boundary.
   Review before implementation because these are durable format and control-plane choices.
2. **Core ledger track — one implementation owner.** Add parser/renderer, append etag/phase checks, local
   chain logic, dependency resolver, derived board view, close/expiry adaptation, and v1 routing. Own new
   focused core tests. No CLI/MCP/control-plane edits in this track.
3. **Surface track — one owner after core API freeze.** Add CLI/MCP parity, ESR reporting, help/reference
   text, and surface tests. It consumes the core API; it does not duplicate validation.
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
| New-board writer roles that can mutate authority concurrently | multiple reserved participants | exactly one current phase writer |
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

## V2 schema annex — frozen implementation contract

This is the normative v2 contract; it controls over earlier illustrative text. It does not alter v1
`memory-seed/reflection-plan`, historical plans, or past session evidence.

### Family, bytes, and identity

| Item | Frozen rule |
| --- | --- |
| Discriminator | v2 front matter is exactly `schema: memory-seed/reflection-workstream-ledger` and `version: 2`; v1 remains `memory-seed/reflection-plan` at version 1. Absent, duplicate, mixed, or unsupported forms are malformed, never inferred. |
| Path | The only active v2 path is `.memory-seed/reflections/active/<workstream_id>/ledger.md`; its directory contains no `manifest.yaml`. v2 commands reject v1 paths and conversely. |
| Bytes | UTF-8 without BOM, Unicode NFC, LF only, no trailing whitespace, exactly one final LF. YAML has two-space indentation and the exact field order below. Digests are lowercase `sha256:` plus 64 hex. |
| Header order | `schema`, `version`, `workstream_id`, `working_branch`, `base_sha`, `created_at`, `reflection_retention_days`, `id_salt`. No other header field is accepted. `base_sha` is 40 lowercase hex; every timestamp is UTC RFC 3339 in `YYYY-MM-DDTHH:MM:SSZ` form; `id_salt` is 64 lowercase hex from OS entropy. Header bytes never change. State and phase derive from validated blocks. |
| Digests | Ledger digest is `sha256(LEDGER_DOMAIN || canonical_ledger_bytes)` and detail digest is `sha256(DETAIL_DOMAIN || canonical_record_block_bytes)`. `LEDGER_DOMAIN` is ASCII `memory-seed/reflection-workstream-ledger/v2/ledger` plus NUL; `DETAIL_DOMAIN` substitutes `detail` for `ledger`. |

The ID domain is ASCII `memory-seed/reflection-workstream-ledger/v2` plus NUL. For each ID,
`frame = ID_DOMAIN || hex_decode(id_salt) || components`, where each component is
`uint32_be(len(UTF-8(component))) || UTF-8(component)`. SHA-256 the frame, encode the low 100 bits of its
first 12 bytes as 20 lowercase Crockford Base32 characters (`0123456789abcdefghjkmnpqrstvwxyz`), and prepend
the prefix. The canonical writer supplies all components.

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
`from_phase`, `to_phase`, `chain_id`, `parents`, `relationship`, `depends_on`, `source`,
`related_decisions`, `confidence`, `pre_ledger_digest`, `detail_digest`. Headings are `### Conclusion`,
`### Reasoning`, then optionally in order `### Assumptions`, `### Alternatives`, `### Evidence`, and
`### Next step`. Conclusion and reasoning are non-empty. Lists are canonical sorted lists, never scalars.
`detail_digest` is computed over the canonical whole block with its own value replaced by 64 zeroes.

The derived phase begins `plan`. A block must use precisely one transition below. A non-advancing note has
equal `from_phase`/`to_phase` and is allowed only to that phase's owner.

| From | To | Role | Rule |
| --- | --- | --- | --- |
| `plan` | `implement` | planner | Establishes an implementable conclusion. |
| `implement` | `review` | implementer | Submits evidence for independent review. |
| `review` | `implement` | reviewer | Specific correction or rejection. |
| `review` | `orchestrate` | reviewer | Approved review handoff. |
| `orchestrate` | `closed` | orchestrator | Post-merge receipt/disposition only. |

No transition skips review or regresses except `review -> implement`; `closed` accepts no ordinary append.
The first record has no parents and requires `no_related_thread`. Every later parent is local and validated.
A chain is created from the first record, cannot be renamed, and is never reconstructed from a board.

### Dependencies, board visibility, and branch collision

`depends_on` is a list of ordered objects: `workstream_id`, `record_id`, `record_digest`, `reason`,
`receipt`. `receipt` is `null` only while the target is guaranteed active, otherwise it is the ordered fallback
`session_path`, `entry_id`, `decision_id`, `receipt_id`, `receipt_digest`. The fallback identifies a normal,
committed session receipt for that exact workstream/record/detail digest. An active dependency that could
outlive its target must include a fallback at append time; append-only records are never patched later.
Target closeout refuses a still-open dependent without verified fallback. Resolution prefers the active record
then the verified receipt; a dependency is never a parent or imported detail.

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

Post-merge closeout appends the guarded Memory Seed decision and embedded receipt, then the
`orchestrate -> closed` block in that integration checkout. It requires trusted rebind, integrated source tip,
complete review/disposition, resolved heads, and durable member receipts. The receipt states origin branch,
integration branch/commit, pre-close digest, and closed IDs. A source checkout cannot manufacture it.

### Safe expiry and compaction

Expiry replaces only complete eligible chain blocks; it never changes durable sessions, header bytes, retained
blocks, v1 data, or a whole board. Preview reads current HEAD and canonical bytes and returns `expected_head`,
`pre_ledger_digest`, sorted `removed_chain_ids`, sorted `removed_record_ids`, and exact
`post_ledger_digest` made from byte-identical header plus retained blocks. It appends no cleanup block.

Apply compare-and-swaps only if HEAD and bytes still equal preview. In the same trusted integration change, a
normal session cleanup receipt lists in order: `workstream_id`, `removed_chain_ids`, `removed_record_ids`,
`pre_ledger_digest`, `post_ledger_digest`, `cleanup_pre_tip`, `reason`, closure/decision receipt locators.
The resulting normal session trailer binds receipt and rewrite to the commit. Refuse an open, unreviewed,
unelapsed, unreceipted chain; a live dependency target lacking verified fallback; malformed post bytes; or any
digest mismatch.

Append needs `expected_head` and `pre_ledger_digest`; compaction makes any earlier append stale. Stale append
or cleanup returns `stale_head` or `stale_ledger_digest`, writes nothing, and requires reload/rejudgment. It
must not rebase, replay, or append stale prose. Early expiry retains verified live-user approval and
unpromoted-chain constraints and emits the same pre/post receipt.

### Gates and reduction proof

Before implementation, golden tests must prove all vectors and field order. Parser tests reject every forbidden
discriminator, header field, byte rule, ID/digest, transition, dependency fallback, collision, and rebind form.
Integration tests prove pre-merge close/expiry refusal, trusted-token rebind, arbitrary rebind refusal, and
stale append after compaction. Board tests prove malformed candidates are reported and non-zero. The v1 suite
remains unchanged. The normal v2 path is accepted only with one active authority file, one guarded append,
zero participant reservations, and zero v2 fuse operations; every exception is counted and justified as v1
reader/receipt compatibility, never hidden v2 coordination.
