---
title: "Reflection Board v1 operator guide"
date: "2026-09-08"
project: "memory-seed"
status: "historical"
---

# Reflection Board v1 operator guide

Historical reference only. Reflection Board v1 commands, MCP tools, runtime modules, and
automatic retention are retired; the commands below no longer exist in the current OSS
edition. A first real chain was evaluated and closed on 2026-09-08; the later
integrated launch-verification Todo was withdrawn rather than completed. The
[retirement plan](../5_Completed/reflection-runtime-retirement-superpowers-plan.md) and
[functionality audit](../3_Spec/functionality-audit.md) describe the current state.

The remainder of this guide records the former v1 operating contract, not instructions
to run against a current checkout.

A board is a derived view of branch-owned temporary ledgers. Its sole supported authored format is
`memory-seed/reflection-workstream-ledger` v1, stored at
`.memory-seed/reflections/active/<workstream_id>/ledger.md`. The fragment-and-fuse prototype has no
runtime reader, writer, migration, or compatibility alias. The trusted v1 reader can validate admitted
compacted history; that is not prototype compatibility. Ordinary sessions remain the durable memory.

## Command reference

Run from the checkout being operated on. In a source checkout, replace `memory-seed` with
`python -B -X utf8 -m memory_seed.cli` to select its code. Every mutating command defaults to a
non-writing preview. Review it and repeat with `--apply`; apply recomputes and revalidates the operation.
All listed commands support `--json`. Placeholders below must come from actual tool output or the
declared task, never invented identifiers.

| CLI command | Operation-specific inputs | Result |
| --- | --- | --- |
| `reflection trust init` | none | CLI-only one-time trust bootstrap preview/apply on the resolved integration/default branch |
| `reflection ledger init` | `--retention-days`, `--expected-head` | Initialize the current branch's ledger; use the returned applied `workstream_id` |
| `reflection ledger append` | workstream ID; `--role`, `--conclusion`, `--reasoning`, `--source`; optional `--chain-id`, `--relationship`, `--parent`, `--no-related-thread`, `--confidence`, `--to-phase`, `--expected-head`, `--expected-ledger-digest` | Append one phase-owned record |
| `reflection ledger view` | workstream ID | Read trusted committed ledger text; `--json` also exposes classification and close receipt status |
| `reflection ledger check` | workstream ID | Validate committed history; use `--json` to inspect missing close receipts |
| `reflection board view` | none | Read every active candidate, including malformed or unsupported candidates |
| `reflection ledger close` | workstream ID; `--chain-id`; optional `--receipts`, `--expected-head`, `--expected-ledger-digest` | Draft receipt requirements or close a resolved, integrated chain |
| `reflection ledger rebind` | workstream ID; `--source`, `--reason` | Preview/apply exact local integration evidence on the target branch |
| `reflection ledger prepare` | workstream ID | CLI-only preview/apply of a local PR handoff on the final source branch |
| `reflection ledger finalize` | workstream ID; `--source`, `--reason` | Preview/apply PR rebind on the target using the prepared single-use handoff |
| `reflection ledger expire` | workstream ID; `--chain-id` | Preview/apply normal elapsed-retention chain cleanup and ordinary compaction receipt |

For init/append/close, use the preview's `head` as `--expected-head`; for append/close also use its
`pre_ledger_digest` as `--expected-ledger-digest`. These are stale-state expectations, not authority
over Git objects. Preview identities are not caller-selectable; the apply response is the committed result.
Rebind/finalize/expiry expose no such override flags and remeasure their exact history inside apply.

## MCP parity

MCP calls accept `cwd` (default `.`). Mutation tools default `apply` to false. Use JSON booleans,
not strings such as `"false"`; unknown fields are refused. CLI `--parent` corresponds to the MCP
`parents` array, and CLI `--receipts` JSON corresponds to the MCP `receipts` array.

| Tool | Required fields |
| --- | --- |
| `memory_reflection_board_view` | none |
| `memory_reflection_ledger_view` | `workstream_id` |
| `memory_reflection_ledger_check` | `workstream_id` |
| `memory_reflection_ledger_init` | none |
| `memory_reflection_ledger_append` | `workstream_id`, `role`, `conclusion`, `reasoning`, `source` |
| `memory_reflection_ledger_close` | `workstream_id`, `chain_id` |
| `memory_reflection_ledger_rebind` | `workstream_id`, `source`, `reason` |
| `memory_reflection_ledger_finalize` | `workstream_id`, `source`, `reason` |
| `memory_reflection_ledger_expire` | `workstream_id`, `chain_id` |

`memory_esr` includes the same read-only Reflection projection as `memory-seed esr`.
Trust/key operations and PR prepare have no MCP surface. There is no public receipt-finalize command,
early-expiry tool, reflection fuse, raw ledger writer, target-ref override, or caller proof/signature input.

## Safe lifecycle and phase ownership

1. Check the owned worktree, clean state, task authority, integration mode, and merge trigger.
   Before establishing any new ledger base, the maintainer previews and explicitly applies
   `reflection trust init` on the resolved integration/default branch. It validates the key pair,
   commits only `.memory-seed/reflections/trust/retention-approval.yaml`, and keeps the private
   Ed25519 material beneath the Git common directory with restrictive local permissions.
   Start the workstream from a commit containing that anchor; adding trust later cannot retrofit its base.
2. Preview/apply `reflection ledger init` on the workstream branch. Seven days is the usable public
   retention default. The schema recognizes 14/30, but their admitted host-preflight authoring path
   is not exposed by the public facade: **retention-extension authoring is planned** and those requests
   currently fail closed.
3. Open a root with planner role, `--relationship no_related_thread --no-related-thread`, conclusion,
   reasoning, and source. The apply result supplies a record ID; use ledger view for its chain ID.
   Continue with that `--chain-id` and actual `--parent` record IDs. Use `--to-phase` explicitly
   when the role has more than one permitted transition.
4. Complete the reviewed implementation, independent validation where required, and orchestrator synthesis.
   Resolve divergent heads or explicitly dispose them; one unresolved divergent head blocks close.
   Read/check the ledger before handing it to the next role. Role labels do not prove independent review.
5. Integrate and rebind, then prepare receipts, close, and finalize receipts as below.
6. After authenticated retention elapses, preview/apply expiry on the effective integration owner.
   Recheck ledger/board history and ESR and retain the ordinary compaction receipt.

| Current phase | Owner's action |
| --- | --- |
| `plan` | Planner records planning and advances to `implement` |
| `implement` | Implementer records work and advances to `review` |
| `review` | Reviewer selects `implement` for rework or `orchestrate` for synthesis |
| `orchestrate` | Orchestrator records synthesis; the close operation advances to `closed` only after the gates |
| `closed` | No append; finalize durable receipts and wait for eligible expiry |

The existing [collaboration](../../.memory-seed/skills/agent_collaboration.md),
[session logging](../../.memory-seed/skills/session_logging.md), and
[end-of-turn](../../.memory-seed/skills/end_of_turn.md) runbooks and exact Seed twins own the reusable steps.

## Local and PR integration

Keep the live source ref until rebind/finalize succeeds. Use the existing guarded integration workflow
and its configured approval gates; session fusion remains ordinary session integration, never reflection
fragment fusion. The reflection operations perform no network action, push, PR creation, or source-ref deletion.

In local mode, integrate as an exact two-parent target/source merge, then preview/apply
`reflection ledger rebind <workstream_id> --source <source-branch> --reason <reason>` on the target.
Rebind appends integration evidence and transfers effective ownership; it never rewrites old records.

### Inherited-family carrier for later ordinary branches

After a board has reached the target branch, an unrelated normal descendant or sibling branch may still
use `session merge-branch` when it has not changed **any** Reflection reserved state. The guarded preview
admits this only if target and source have exactly one merge base and the complete Reflection inventory —
every reserved path, canonical mode, and blob OID, including the retention anchor — is identical at
target, source, and that merge base. The ordinary no-FF merge/fuse/trailer workflow remains intact; the
trusted ledger reader follows the deterministic target parent because no ledger transition occurred.

This is not a fast-forward alternative and it does not transfer board ownership, so do not run rebind
for that unrelated branch. A source that changes, adds, removes, aliases, or corrupts any Reflection
path, or a parent pair without exactly one merge base and complete matching inventory, still refuses
before mutation.

In PR mode, finish source preparation against the current target and commit all source changes first.
Preview/apply `reflection ledger prepare <workstream_id>` on that final source tip. It stores a
canonical non-secret single-use handoff under the Git common directory, not in tracked memory.
After separately authorized integration, preview/apply `reflection ledger finalize <workstream_id>
--source <source-branch> --reason <reason>` on the target.

Finalize derives the target, source tip, merge event, and ledger identity. It requires the exact
same-repository two-parent merge, target parent first and the still-live prepared source tip second.
Squash/rebase merges, moved/deleted source refs, or changed ledger bytes refuse. Target advancement is
allowed only through descendants preserving the ledger; a later CAS head is distinct from the merge event.

## Receipt preparation and finalization

Close requires an integrated, rebound, orchestrate-phase chain with one resolved head, complete
committed member receipts, immutable-base trust, and the matching local private key.

Preview close without receipts to inspect every exact missing member. Preview a new ordinary DRAFT session
entry with the existing `session append --dry-run` / `memory_session_append` writer; use its canonical
session path and entry ID plus the exact uppercase decision locator, e.g. `D1`. Follow that writer's
preview/replay identity contract; never invent a timestamp or ID. If identity changes, re-draft before commit.

Supply `--receipts` as a JSON array of locators with `session_path`, `entry_id`, `decision_id`,
and `disposition`, optionally `record_id`. No `record_id` means all existing chain members.
Use `promoted-to-decision` or `already-covered-by-decision` for durable decision-backed coverage;
use `expired-unpromoted` for the unpromoted disposition. The private validator's historical
`early-expired-unpromoted` spelling does not enable public early expiry.

Copy each exact `required_receipts` mapping returned by close preview into its own fenced YAML block
inside the named DRAFT decision. Preserve every returned field and digest. Append through the ordinary
writer and commit with the ordinary session workflow; receipt mappings in arguments or uncommitted files
are not coverage. Re-preview until `ready_to_close` with empty `missing_receipts`, then apply close.

Close creates a new member and closure outcome, so success initially reports `closed_receipts_pending`.
Do not paste the immediate response's mappings into the already-committed pre-close entry. Preview a
**new** ordinary entry, then call close again without apply using its new locator to draft the two exact
post-close mappings. Append/commit that new entry. Run
`memory-seed reflection ledger check <workstream_id> --json` to inspect `closed_receipts_pending`
and `missing_receipts`; non-JSON ledger view/check prints raw ledger text. Recheck until the chain
is `closed` with empty `missing_receipts`; board view and ESR expose the same receipt state.
No separate receipt-finalize command is needed.

## Elapsed expiry, trust, and recovery

Normal expiry removes only the selected complete closed chain after full receipts and elapsed retention.
The verifier uses authenticated host close-time observation and signed provenance, not a caller-authored
`closed_at`, Git date, filesystem mtime, supplied timestamp, or task-packet assertion. It anchors at the
ledger base and binds the record set, closing record, receipt identities, retention, integration evidence,
pre/post ledger identities, and cleanup. Cleanup and its ordinary compaction-receipt commit are constructed
off-ref and published with one ref compare-and-swap. The existing ordinary session author handles the
compaction entry, including per-user frontmatter. Surviving chain records and all ordinary session history
remain intact.

Working-tree disappearance is **not cryptographic erasure**. Historical and unreachable Git objects may
remain until Git garbage collection; expiry does not imply garbage collection or privacy-grade deletion.

| Refusal or limit | Operator response |
| --- | --- |
| Stale preview, dirty state, or changed authority | Inspect the diff, preserve owned/concurrent work, reload view/check, and make a fresh preview judgment |
| `closed_receipts_pending` | Draft the missing close member/outcome mappings against a new ordinary entry, append/commit, and recheck with `reflection ledger check <workstream_id> --json` |
| Retention not elapsed | Keep the chain; a later sanctioned expiry may succeed. ESR never expires it automatically |
| Missing/mismatched local key or immutable-base anchor | Stop; no public rotation, replacement, or recovery command exists. A later anchor does not fix an old ledger |
| Legacy pre-proof close | Readable but non-expirable; no historical proof retrofit |
| PR finalize fails before handoff claim | Inspect the diagnostic and re-preview if the original prepared history still qualifies |
| PR finalize fails after handoff claim, including CAS failure | The handoff is consumed. Re-preparation needs an eligible final source state; the same tip cannot be prepared twice and an already-integrated ledger cannot be prepared. Automatic post-merge recovery is unavailable; escalate without deleting the claim |
| `append-rollback-conflict` / `preserved_paths` | Concurrent content was preserved; inspect it before retry. Do not reset or delete it to restore apparent cleanliness |
| Hook cannot import shared admission | Repair the current package/interpreter installation; do not bypass the hook |

Live and Seed prepare-commit-msg hooks invoke the same reserved-family admission before normal
Memory-Entry stamping. Only sanctioned kernel transactions, the one-time canonical trust bootstrap,
and exact integration carriers pass. Manually staging reserved paths, aliases, or divergent trust anchors
is refused. Invented Reflection trailers cannot grant admission or bypass reserved-family checks;
ordinary commits without reserved paths may not read the message.

This is local host trust: compromise of the host account, clock, or private key defeats its assumptions.
The dependency-free pure-Python Ed25519 signer is **not constant-time** and is not hardware-backed.
Extended-retention authoring remains planned. Early expiry, key rotation/recovery, automatic post-merge
handoff recovery, and a prototype compatibility path are unavailable.
