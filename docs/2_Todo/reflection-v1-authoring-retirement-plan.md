---
title: "Reflection v1 Authoring Retirement Plan"
date: "2026-09-07"
project: "memory-seed"
status: "active"
priority: "P1"
next_action: "Independent plan review, then retire v1 authoring after the reviewed v2 core lands and before reflection surfaces launch."
source:
  - "docs/2_Todo/reflection-ledger-workstream-evolution-plan.md"
  - "docs/2_Todo/plan-reflection-ledger.md"
  - "docs/CONSTITUTION.md"
  - "memory_seed/reflection_ledger.py"
scope: "Remove active v1 reflection authoring and fusion infrastructure; preserve only historical reading and verification."
non_goals:
  - "No migration, conversion, backfill, historical deletion, or session rewrite."
  - "No change to v2 IDs, receipt grammar, sequential phase ownership, retention, or trusted Git history admission."
  - "No change to ordinary session fusion or its transitive branch-history support."
dependencies:
  - "Independent approval of this removal plan."
  - "Reviewed Reflection Ledger v2 core integrated before code retirement."
acceptance_criteria:
  - "New reflection work has one sequential ledger per workstream; no v1 creation, reservation, fragment append, fuse apply, close, or expire route remains."
  - "Historical v1 manifests, reports, fragments, closeouts, approvals, and receipts remain readable and verifiable without writes."
  - "CLI, MCP, Task Packets, active guidance, and Seed twins offer only v2 reflection authoring."
  - "Tests distinguish historical verification from prohibited new v1 mutations, and preserve all v2 authority guards."
---

# Retire reflection v1 authoring

Each new feature workstream uses one temporary ledger. Its planner, implementer, reviewer, and orchestrator
append sequentially; parallel features use different ledgers. The old participant-fragment mechanism is
removed from executable authoring and integration flows. Historical v1 records keep their identities and
meaning through a small read-only compatibility boundary.

This is a narrow amendment to the active workstream evolution plan. It supersedes that plan's allowance for
v1 compatibility **fuse operations and ongoing expiry semantics**, including its requirement that the old
mutation tests stay unchanged. Its remaining v2 contract stays in force. The original
`plan-reflection-ledger.md` remains historical planning evidence, with its unimplemented v1 dispatches
ineligible for launch. Approval of this plan is the implementation gate; this document does not claim removal
has already shipped.

The user explicitly requested this removal on 2026-09-07. The earlier reason for compatibility was to avoid
rewriting historical boards. Read-only verification meets that need without maintaining a second authoring
model. This improves Application and Trust under the Constitution's five-question test, and implements
`constitution:v1#single-source` and `constitution:v1#path-of-least-resistance`. It preserves
`constitution:v1#append-only`, `constitution:v1#write-surface-parity`, and
`constitution:v1#temporary-reflection-expiry`: removing a command does not authorize deleting its data.

## Measured inventory

Baseline: main `9667ccb59d1df30725d0d60de8cebdc0b8d6e01d`. The v2 core is concurrently being reviewed on
`codex/feature/reflection-ledger-v2-core`; implementation must repeat this inventory after that branch lands.
The inventory distinguishes shipped code from commands that appear only in plans.

| Surface | Present at baseline | Required disposition |
|---|---|---|
| `memory_seed/reflection_ledger.py` | v1 manifest/reservation/report/fragment models; canonical renderers and parsers; Git admission; common view; receipt/closeout/approval verification | Keep only the transitive dependency set required to read and verify historical v1 objects and shared v2 primitives. Explicitly identify retained helpers as compatibility internals. |
| Same module, `reflection_fuse_preview`, `reflection_fuse`, `_ReflectionFusePlan`, `ReflectionFuseResult`, `_apply_reflection_fuse_plan` | Source-branch additions, preview tokens, and a real filesystem apply primitive | Delete the apply primitive, write-plan/token machinery, and fuse API. A read-only historical validator may verify an already committed tree; it must never return a writable fuse plan or apply token. |
| Same module, `eligible_expiry_paths` | Computes deletion candidates and authorizes early expiry using admitted close/receipt objects | Remove the deletion-planning API from the product. Keep only private verification of existing historical closure/approval evidence where used by the reader; do not produce actionable v1 cleanup paths. |
| Same module, `render_manifest`, `render_report`, `render_fragment`, `render_closeout`, ID derivation | Pure byte construction; parsers use canonical render equality, reservation IDs prove old identity | Retain minimal pure canonicalization/ID helpers privately when required to validate old bytes. Remove author-facing constructors/exports and unused helpers. Tests may retain fixture builders. Renaming a pure helper alone is not sufficient retirement of a reachable writer. |
| Same module, `admit_reflection_git_tree`, `admit_reflection_receipt`, `admit_reflection_closeout`, `validate_chain_close`, `validate_board_close`, `common_view` | Reads exact committed historical evidence and checks integrity | Keep the required read/verify behavior behind explicit v1 compatibility routing. A validation result describes recorded facts, carries `read_only: true`, and contains no mutation token, writable reservation, or executable cleanup plan. |
| `memory_seed/cli.py`, `memory_seed/mcp_server.py` | No reflection route at baseline | Do not implement old plan routes. Add only the v2 operations from the evolution plan and explicit historical inspection where needed. Stale v1 writer requests return `legacy-reflection-read-only` with a v2 init pointer and zero writes; unknown removed commands may use the standard unknown-command diagnostic. No hidden compatibility write flag. |
| `memory_seed/task_packet.py` | No reflection-specific reservation/manifest binding at baseline | Never add the v1 reservation generator. Compile only the v2 workstream/ledger binding. Explicit v1 authoring dispatch intent fails before materialization/activation. Historical read tasks may receive v1 evidence but no authoring entitlement. Already compiled legacy artifacts remain archival evidence and cannot activate for new writes. |
| `memory_seed/core.py`, session fuse | No reflection-kernel import or coordinated-reflection integration at baseline | Keep session merge/fuse intact. Never wire the old reflection apply primitive into it. Integrate v2 ownership/rebind through its approved contract only. |
| `.gitattributes` | `.memory-seed/reflections/active/** -merge`, comment says reflection fuse owns it | Keep the protective attribute; update its rationale for structural validation and sequential v2 integration. Removing line-merge protection is not part of retirement. |
| Active `agent-rules.md`, `skills/agent_collaboration.md`, `skills/session_logging.md`, `skills/end_of_turn.md`, `skills/index.md` | No shipped reflection authoring runbook or reservation workflow found | Add v2 routing only when surfaces land. Instructions must name one ledger per workstream, sequential roles, shared read visibility, and normal durable decisions. No fragment pairs or reservation prerequisites. Preserve the mandatory full-agent-rules packet baseline and canonical session clock procedure. |
| Matching files under `memory_seed/seed/.memory-seed/` | Shipped reusable twins | Apply the same routing/guidance changes in the owning workflow commit. Keep live/Seed parity; no separate runtime compatibility writer. |
| `docs/2_Todo/plan-reflection-ledger.md` | Old planned init/report/fragment/fuse routes and embedded dispatches, never all shipped | Retain historical content; update lifecycle/router metadata when its remaining work is replaced, with links to the evolution and retirement plans. Do not compile its old dispatches. Do not mark its unshipped surface work completed. |
| `docs/2_Todo/reflection-ledger-workstream-evolution-plan.md` | v2 plan with explicit v1 fuse/expiry compatibility allowance | This amendment replaces those allowances with read-only compatibility; update the active requirements to avoid contradictory worker instructions. |
| `tests/test_reflection_ledger.py` | Pure canonical/ID/ownership/graph/receipt/approval tests and `TestFuse` integration/apply tests | Preserve historical reader negatives and shared cryptographic vectors. Replace operational fuse/expiry successes with historical validation and removal/refusal assertions. Store representative immutable v1 fixture bytes rather than relying on retired runtime builders. |
| `tests/test_reflection_ledger_surfaces.py`, `tests/test_reflection_ledger_integration.py` | Planned, absent on baseline | Create under later surfaces/integration owners with explicit v1 read-only and v2 parity tests; do not resurrect old write APIs to satisfy an obsolete test plan. |

The active root has no tracked `.memory-seed/reflections/**` objects at this baseline (`git ls-files` returned
none). This is not proof that other users or branches have none. Do not delete, move, or convert discovered
v1 files. No standalone CLI/MCP reference document exists under an obvious matching filename; the surface
owner must update actual README/help/doc registrations found at its implementation baseline, rather than
create redundant reference files.

## Compatibility contract

1. Discriminate v1 and v2 by their exact schema/version and path rules. Never infer v2 identity from v1
   IDs or reinterpret a fragment as a ledger. Mixed/unsupported input fails with a structured diagnostic.
2. Historical inspection is read-only, including its error paths. It may reconstruct a view in memory from
   admitted committed v1 records and resolve embedded receipts in ordinary sessions. It may verify old
   closeout/expiry evidence; it cannot execute another close, promotion, rebind, fuse, or expiry on v1.
3. Keep the minimum canonical codecs, frozen ID verification, Git object admission, signature validation,
   and receipt resolution needed by those reads. The v2 core currently shares low-level YAML, Git, digest,
   and signature helpers; remove code by reachability and ownership, not by a blanket `v1` string search.
   Extract only when it simplifies a real dependency. No mandatory module split or second format registry.
4. Old open v1 boards remain inspectable and frozen. The refusal directs the operator to initialize a fresh
   v2 workstream and record any adopted conclusion through the normal session writer. There is no automatic
   copying, promotion, or historical rewrite. A later migration/cleanup request requires its own reviewed
   scope and the existing constitutional safeguards.
5. Preserve historical IDs, receipts, stored trailers, and Git objects. Ordinary memory retrieval continues
   to resolve durable decisions and their receipts. An active v2 dependency may use a historical receipt only
   if its existing typed contract explicitly permits it; retirement adds no cross-version identity bridge.
6. Supported API/help/docs stop advertising v1 writes. Any retained compatibility shim fails before filesystem,
   Git ref, index, session, cache, or config mutation. There is no `force`, version toggle, environment override,
   or direct internal apply path that revives v1 authoring. Pure fixture serialization is not a product writer.

## Delivery and ownership

All implementation remains on isolated worktrees with exact baseline SHAs, full active agent rules, and
canonical session-writing instructions. The orchestrator owns conflicts, integration, and current plan status.

1. **Plan review (read-only reviewer):** approve this removal boundary and inventory against the integrated
   v2 core. Record residual shared-helper dependencies. This plan may be reviewed while core fixes continue;
   the retirement implementer must remeasure after the core merge.
2. **Core retirement (one sequential owner):** own `memory_seed/reflection_ledger.py`,
   `tests/test_reflection_ledger.py`, v1 immutable fixtures, and `.gitattributes`. Remove v1 mutators, write
   plans, reservation issuance interfaces, and deletion planning. Preserve historical codecs/verifiers and
   v2 shared helpers. Add positive historical reads and negatives proving removal. Independently review
   before integrating. Do not overlap the active v2 core worker's files.
3. **Surfaces (one owner after core freeze):** own CLI/MCP routing, Task Packet reflection binding, their
   focused tests, and actual public usage/help documentation. Only v2 authoring is available. Historical
   reads are explicitly labeled. Reject explicit legacy write intent before activation or mutation.
4. **Workflow/control plane (one owner after surface names freeze):** own active/Seed rules and skills,
   registry, relevant docs, and plan routing. Replace obsolete dispatch instructions and reserve only v2
   ledger context. Existing plans and session history retain their recorded meaning. Coordinate generated
   docs indexes serially. Add no unrelated skill, policy, or Constitution change.
5. **Integration/evaluation (independent owner):** run the two-workstream v2 simulation, historic v1 reads,
   stale packet/refusal controls, receipt retrieval after v2 expiry, and the full suite. Record removed vs
   retained API inventory and explain every retained v1 production helper. The orchestrator integrates
   serially and updates the existing experiment reflection log with measured results.

The retirement is part of the remaining Reflection Ledger work, not a parallel replacement feature. The
surface/workflow tasks should absorb these requirements instead of implementing obsolete paths and deleting
them afterward. Seed Pod reconstruction waits for this stabilized reflection foundation. Push, release,
Seed Pod P1, and historical-data cleanup remain outside this plan.

## Acceptance and verification

| Case | Required observable |
|---|---|
| Existing committed v1 board with report/fragment pairs, divergent heads, closeout, approvals, and receipts | Historical parser/view/verification returns the same IDs, bytes, graph meaning, and receipt resolution; no tracked/untracked/config/ref changes. |
| Corrupt v1 bytes, wrong reservation identity, forged report, missing Git object, forged approval, missing member receipt | Same refusal strength as the old verification path; compatibility never means weaker validation. |
| Attempt old init/reserve/report/append/fuse/apply/close/expire via every exposed surface | Function is absent or returns the documented read-only/unknown-operation error before writing anything. No apply token, writable path plan, or success-shaped fallback. |
| v1 writer dispatch, stale compiled v1 activation, or v2 writer targeting a v1 directory | Refusal before authority is established; existing bytes, Git refs/index, sessions, and settings unchanged. Historical evidence-only dispatch remains allowed. |
| Two v2 workstreams and all sequential roles | Independent ledgers work through normal append, review, synthesis, receipt, close, and expiry; board view reads both and has no write/fuse path. |
| v2 receipt/shared-helper regression | Trusted history, exact session decision receipt binding, retention/approval, dependency protection, stale-write CAS, and tamper negatives remain green. |
| Guidance and inventory | No live task, packet, help, seeded skill, or activation route prescribes participant fragments/reservations/fusion. Historical prose is explicitly excluded from the active-route assertion. |
| Session merge | Existing session fuse and transitive import tests still pass; unchanged v1 historical bytes may travel as ordinary already-recorded history, never as newly authored v1 reflection additions. |

Use checkout-local commands. The implementation baseline must confirm the named test files before invocation:

```text
python -X utf8 -m pytest -q tests/test_reflection_ledger.py
python -X utf8 -m pytest -q tests/test_reflection_workstream_ledger.py
python -X utf8 -m pytest -q tests/test_reflection_ledger_surfaces.py tests/test_reflection_ledger_integration.py
python -X utf8 -m pytest -q tests/test_task_packet.py tests/test_task_packet_surfaces.py tests/test_mcp_server.py tests/test_session_fuse_and_merge.py
python -X utf8 -m pytest
python -X utf8 -m memory_seed.cli docs check
python -X utf8 -m memory_seed.cli docs index --check
python -X utf8 -m memory_seed.cli links check
python -X utf8 -m memory_seed.cli esr
git diff --check
```

The planning tranche runs docs/index/link/ESR/whitespace checks only. No product-code claim is established by
those checks. Report all failures and distinguish baseline issues from this change. For runtime removal,
record a final symbol-to-disposition inventory rather than a raw zero-occurrence search: v1 historical
references and validation helpers are expected to remain.

## Risks and completion

The principal risk is removing a canonical helper still required by historical validation or v2 authority.
The retained-helper inventory and shared regression tests address it. A second risk is preserving old write
code behind a compatibility label; absence/refusal tests must exercise public and formerly internal apply
entry points. A third risk is silently abandoning old open boards; explicit frozen-state diagnostics and
normal decision capture preserve a clear continuation path without inventing a migration.

Completion requires reviewed core removal, v2-only active surfaces and guidance, historical read parity,
integrated verification, and the measured experiment update. The orchestrator then marks this supplemental
plan complete and links it from the evolution plan; approval alone never implies implementation completion.
