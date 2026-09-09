---
title: Superpowers-informed delivery quality uplift
status: inbox-unassessed
source: "JNL interactive design discussion and verified local/official sources, 2026-09-09"
priority_if_promoted: P1
next_action: "Review the proposed policy defaults and unresolved representation decisions, then promote only the accepted implementation plan."
---

# Superpowers-informed delivery quality uplift

## Purpose and intended uplift

This is a concrete proposal to improve delivery quality, reduce avoidable rework, and avoid unnecessary
compute by making important decisions explicit primarily **before** implementation. It preserves the
three requested phases; a small trial is an acceptance technique inside the phases, not a replacement for
Phase 1 or a reason to postpone debugging and verification.

Memory Seed should not import Superpowers wholesale. It should add or amend narrowly scoped native
guidance where Memory Seed owns authority, project memory, task packets, verification evidence, and
integration; it should retain only the two already-approved external execution routes where Superpowers
owns the disposable execution process. The target is an easier, evidence-grounded planning path—not a
new generic agent framework.

### Outcomes to test, not promises to assert

- More consequential changes begin with alternatives, constraints, and a stated choice rather than an
  unexamined first implementation.
- Planning carries the selected evidence and any permitted departure into a Task Packet, so execution
  does not repeatedly rediscover broad project context.
- Debugging records a reproducible observation and a written hypothesis before changing code; completion
  cites fresh, actual verification rather than a remembered earlier result.
- Review feedback is evaluated against the local rationale and exact changed range, not accepted or
  rejected by reflex.
- Routine work that has already been assessed remains light-weight.

No percentage improvement, cost reduction, or comparative advantage is claimed here. Baselines and
measurements are a deliverable because no local comparative cost/rework dataset was found in the inspected
sources.

## Verified baseline and boundaries

| Surface | What the inspected source establishes | Consequence for this proposal |
| --- | --- | --- |
| Existing Superpowers adapter | [`.memory-seed/skills/superpowers_integration.md`](../../.memory-seed/skills/superpowers_integration.md) permits only verified official `dispatching-parallel-agents` for independent read-only work and `subagent-driven-development` for approved same-session implementation. It keeps Memory Seed responsible for worktrees, integration, durable records, and cleanup. | Preserve this boundary; do not broaden it by implication. |
| Existing collaboration proposal | [`docs/2_Todo/superpowers-collaboration-integration-proposal.md`](../2_Todo/superpowers-collaboration-integration-proposal.md) already adopts the two external routes and identifies baseline validation, exact-range review, SDD return receipts, and behavioural routing evaluation as Memory Seed-owned improvements. | This proposal extends that work; it does not replace or relitigate its boundary. |
| Existing native owners | [`agent_collaboration.md`](../../.memory-seed/skills/agent_collaboration.md) owns Task Packets, plan gates, worktree and integration safety. [`local_compilation.md`](../../.memory-seed/skills/local_compilation.md), [`end_of_turn.md`](../../.memory-seed/skills/end_of_turn.md), and [`session_logging.md`](../../.memory-seed/skills/session_logging.md) own verification and durable evidence. | Amend these owners where the concern already belongs; do not create parallel controllers. |
| Constitution and authority | [`docs/CONSTITUTION.md`](../CONSTITUTION.md) makes files authoritative for current truth, preserves append-only history, and requires the correct path to preserve validation and human control. The accepted control-file ADR likewise partitions Constitution, control files, ADR heads, and sessions by concern. | Any resulting policy must preserve those boundaries; it cannot silently override an invariant. |
| Topic implementation | [`.memory-seed/topics.yaml`](../../.memory-seed/topics.yaml) is schema v3 and currently represents `area` and `activity` as separate top-level branches with nested children. | The agreed future rule is instead to use the existing topic-tree hierarchy for applicability: area/activity are topic types, not a second independent policy-metadata axis. Reconcile this deliberately; do not claim the current schema already has the agreed interpretation. |
| ADR scope work | [`docs/1_Inbox/adr-ledger-evolution-and-reasoning-semantics-plan.md`](adr-ledger-evolution-and-reasoning-semantics-plan.md) is unassessed and explicitly defers an ADR-model/migration decision. | Reuse its ADR scope/authority investigation. This plan must not pre-empt an ADR schema, migration, or constitutional decision. |
| Reflection Board evidence | The tracked ledger at [`.memory-seed/reflections/active/rwl_0xf1x07gms0zk0q1fa31/ledger.md`](../../.memory-seed/reflections/active/rwl_0xf1x07gms0zk0q1fa31/ledger.md), and session decisions `mse_qrh0wtg81prbfqmn:d1` and `mse_awe4krg10x9t2acs:d1`, record a first real v1 launch evaluation and close. Several older planning/reference documents still describe it as planned. | Preserve the closed ledger and code. Reconcile stale descriptions separately; use the board as an acceptance scenario for capability discovery and trade-off assessment, never as proof that it is redundant or more costly. No board off switch is proposed here. |

The official Superpowers repository currently describes fourteen listed skills, and its current plugin
manifest identifies version 6.3.0. This is evidence about the upstream catalogue, not evidence that a
particular client has every skill exposed. The active client must still verify availability and the
adapter's supported range before an external route runs. Sources: [upstream skill catalogue](https://github.com/obra/superpowers#skills-library), [current plugin manifest](https://github.com/obra/superpowers/blob/main/.cursor-plugin/plugin.json).

## Agreed planning and decision policy

### Trigger and stages

1. **Design discovery / brainstorming** is the primary uplift. Trigger it for a consequential new
   decision, including a small code change that creates a new product, architectural, data, safety, or
   workflow choice. It inspects existing project and tool capabilities, researches relevant options,
   compares alternatives, gaps, costs, and a proportionate trial. The user need not already know which
   capability exists. Routine implementation that follows an already assessed decision stays light.
2. **Planning is the primary policy checkpoint.** It validates the selected approach against current
   authority and carries the selected evidence, constraints, conflicts, allowed departures, and effective
   policy into the Task Packet.
3. **Execution rechecks only when necessary:** a new consequential decision, material scope expansion, or
   a new topic branch outside the assessed plan returns to discovery/planning. It does not replay broad
   retrieval after every ordinary edit.

### Authority, applicability, and conflict handling

- Relevant evidence includes the current ratified Constitution, current accepted ADR heads, and active,
  unsuperseded individual or session decisions. The latter do not lose authority merely with age;
  superseded material remains explanatory rather than binding.
- Candidate narrowing is staged: Constitution first, then accepted ADRs, then active individual
  decisions. A higher source does not erase compatible, narrower constraints. Existing concern-owning
  control-file authority is inspected and reconciled rather than silently overwritten.
- Applicability follows the **existing topic tree**: evaluate the same topic and its ancestors, then a
  narrower branch when the task reaches it. Topic relevance only selects candidates; it never proves a
  contradiction. The plan must show a concrete proposed action beside the applicable decision. Semantic
  retrieval may suggest candidates but must not invent coverage, particularly for legacy untagged records.
- A constitutional conflict stops for user approval through the formal amendment process. Warning-only
  treatment cannot bypass it. ADR conflicts default to stop for approval, with shared configurable
  warn/proceed only where the governing authority allows it. Individual pre-ADR decision conflicts default
  to visible warning and proceed; the project policy may tighten that to stop.
- Every departure from an individual decision records the prior decision, reason, actual departure, and a
  later promote/supersede/retain review. Warn/proceed never silently retires the older record.
- Shared policy belongs in Git-tracked project YAML. Task Packets capture the effective settings. An
  agent's local recommendation cannot weaken the shared policy; an explicit user acceptance is distinct
  from a recommendation.

## Full disposition of the fourteen official Superpowers skills

| Official skill | Disposition | Proposed treatment and reason |
| --- | --- | --- |
| `brainstorming` | **Add** | Add a narrow native design-discovery runbook. It is the primary uplift, but it must inspect local capability and make a proportionate choice rather than copy the upstream Socratic script. |
| `systematic-debugging` | **Add** | Add a native debugging runbook: reproduce, inspect recent changes, trace the root cause, write a hypothesis before a fix, and reassess the architecture after three failed hypothesis-led attempts. The threshold is proposed, not yet accepted policy. |
| `verification-before-completion` | **Adapt** | Amend current completion/validation ownership to require fresh actual verification evidence for the claimed change, with explicit skipped/blocked reasons. |
| `test-driven-development` | **Adapt** | Require a viable test strategy and justified exceptions; do not impose absolute TDD where exploratory, integration, legacy, or non-code work makes another validation strategy better. |
| `writing-plans` | **Adapt** | Extend existing planning and Task Packet owners with design evidence, authority checks, effective policy, departures, and freshness/invalidation data. |
| `executing-plans` | **Defer** | Do not introduce a second native execution controller. Revisit only after the planning and review evidence has been evaluated against real work. |
| `dispatching-parallel-agents` | **Retain external** | Keep the verified optional route for independent read-only domains only; Memory Seed supplies the boundary and reconciles the evidence. |
| `requesting-code-review` | **Adapt** | Add a proportionate request checklist to the existing review owner: exact range, acceptance criteria, evidence, and local rationale. |
| `receiving-code-review` | **Adapt** | Add an explicit feedback-evaluation path: confirm the finding against local rationale and evidence, accept/reject/defer with recorded reason, then reverify the actual result. |
| `using-git-worktrees` | **Reject** | Memory Seed already owns worktree identity, namespace safety, Task Packets, and recovery. Copying the generic route would weaken that ownership. |
| `finishing-a-development-branch` | **Reject** | Memory Seed must retain `integration_mode`, `merge_trigger`, session fusion, integration validation, and cleanup. The external generic finish routine remains outside the adapter. |
| `subagent-driven-development` | **Retain external** | Keep it only for a verified, approved multi-task same-session plan, inside the Memory Seed safety envelope and with an SDD return receipt. |
| `writing-skills` | **Defer** | Use Memory Seed's existing skill-architecture owner when a later approved change actually adds or refactors a native skill; do not adopt an upstream authoring framework now. |
| `using-superpowers` | **Reject** | Its global bootstrap would conflict with Memory Seed runtime discovery, authority routing, and lazy project skill selection. The narrow adapter remains the local entry point. |

## Delivery plan

### Phase 1 — discovery, debugging, and fresh verification

Deliver the complete first phase; do not reduce it to brainstorming alone.

1. Define the design-discovery trigger, lightweight bypass, required evidence, alternatives comparison,
   and trial decision in a narrow new native runbook or the smallest existing owner that can own it.
   Register it in the trigger registry only after its ownership and trigger language are agreed.
2. Define systematic debugging in a narrow native runbook: reproduce/observe, inspect recent changes and
   scope, trace root cause, record a written hypothesis, make the smallest discriminating change, then
   verify. After three failed hypothesis-led attempts, require an architectural reconsideration or an
   explicit reason to continue. The numeric threshold is a proposed default to validate, not a settled rule.
3. Amend the existing completion/validation workflow rather than creating a new finish controller. A
   completion claim must cite a fresh command/check run after the relevant change, its outcome, and any
   unavailable/failed/waived validation with reason.
4. Define the planning evidence packet: selected alternative, sources consulted, applicable authority,
   compatibility constraints, conflicts, approved departures, effective project policy, and freshness
   markers. Cache scoped evidence for the plan and refresh it on an identified source, scope, or authority
   change rather than doing repeated corpus-wide retrieval.
5. Add proportional behavioural scenarios and a small real-work trial to test the route. The trial informs
   the default; it does not block the phase from including debugging and verification.

Likely owners: `.memory-seed/skills/index.md`, a new focused discovery/debugging skill only if an existing
owner cannot own the concern, `.memory-seed/skills/agent_collaboration.md`,
`.memory-seed/skills/local_compilation.md`, `.memory-seed/skills/end_of_turn.md`,
`.memory-seed/skills/session_logging.md`, Task Packet code/schema, and the live/seed twins where a shipped
runbook changes. Exact file additions remain an implementation design decision.

### Phase 2 — optional planning, test strategy, review, and behavioural evaluation

1. Add an optional implementation-plan path that turns approved discovery into ordered, testable work while
   preserving existing Task Packet and branch/integration authority.
2. Require a test/verification strategy per plan: tests where they are viable, other checks where they are
   more suitable, and explicit, reviewable exceptions instead of a blanket TDD rule.
3. Extend the existing review flow with an exact diff/range, declared acceptance criteria, review evidence,
   finding disposition, scoped re-review, and fresh final verification. Review feedback remains advice until
   evaluated against local rationale and applicable authority.
4. Build behavioural skill evaluation around observable scenarios, not phrase matching. It must test both
   correct routing and light-weight non-trigger cases, and report failures, token/context evidence where the
   runtime exposes it, and unavailable measurements honestly.

### Phase 3 — retain a strict external execution boundary

Keep the existing external boundary throughout:

- `dispatching-parallel-agents` remains for verified independent **read-only** work.
- `subagent-driven-development` remains for verified, approved same-session multi-task plans.
- Memory Seed continues to own project authority, risk/consent, Task Packets, worktree safety, integration,
  cleanup, durable records, and return-receipt verification.
- Do not copy `using-superpowers`, a generic worktree or branch-finishing workflow, or SDD's controller,
  workspace, ledger, briefs, reports, and reviews into the native registry.

## Dependencies and deliberate sequencing

1. Use the existing Superpowers integration proposal and skill as the external-boundary source of truth.
2. Reconcile the active topic-tree implementation with the agreed applicability model before encoding it in
   policy/packet selection. The current schema's axis branches are evidence of current state, not permission
   to invent another parallel metadata system.
3. Coordinate any ADR scope/representation work with the existing unassessed ADR-ledger plan. Until its
   review decides otherwise, use current accepted ADR heads as authority and avoid schema/migration claims.
4. Treat stale Reflection Board statements as documentation-reconciliation work. Preserve the closed launch
   ledger and its receipts; neither disabling, deleting, expiring, nor changing board retention is in scope.
5. Do not revise the Constitution unless the implementation finds a real conflict. A constitutional conflict
   stops for its formal amendment process.

## Open implementation decisions (not agreed facts)

- The exact native skill filenames, trigger-registry wording, and whether discovery/debugging are separate
  skills or tightly scoped additions to existing owners.
- The project-YAML policy schema, its defaults, its enforcement points, and how an explicit user acceptance
  is represented without allowing local settings to weaken shared policy.
- The durable scope/applicability representation that reuses the existing topic hierarchy while reconciling
  the current `area`/`activity` implementation; legacy untagged-record coverage and exact semantic-retrieval
  behaviour remain open.
- The evidence fingerprint, invalidation events, retention scope, and Task Packet rendering needed to make
  freshness cheap and inspectable.
- Whether the proposed three-failed-hypothesis reconsideration threshold is appropriate after scenarios and
  trials, and what counts as an independent failed hypothesis.
- The behavioural-evaluation corpus, success criteria, negative controls, and what runtime token/latency
  data is actually available. No metric is accepted merely because it looks complete.
- The exact reconciliation action for documents that still call the completed Reflection Board launch
  evaluation planned; this plan only records the discrepancy and preservation boundary.

## Acceptance scenarios and verification

| Scenario | Expected observable outcome |
| --- | --- |
| Routine, previously assessed edit | No heavyweight discovery loop; plan cites the existing decision and runs proportionate fresh verification. |
| Small but new consequential choice | Discovery inspects existing capabilities, compares realistic alternatives/costs, records the selection, and carries it into planning. |
| Planning against durable authority | Candidate selection includes Constitution, accepted ADR heads, and active unsuperseded session/individual decisions; it keeps compatible narrower constraints. |
| Constitutional contradiction | The route stops and asks for formal amendment/approval; warn/proceed is unavailable. |
| ADR versus individual-decision conflict | ADR conflict follows the shared stop/default policy; an individual pre-ADR conflict is visible and proceeds by default only with a durable departure record. |
| Repeated debugging failure | Each attempted fix has a reproduction and written hypothesis; the third failed independent hypothesis triggers architectural reassessment rather than a fourth blind patch. |
| Review finding | Reviewer receives exact range and criteria; recipient evaluates against rationale, records disposition, applies only accepted fixes, and reruns current verification. |
| Evidence freshness | A source/authority/scope change invalidates the affected plan evidence and causes bounded refresh; unchanged work reuses the scoped packet rather than repeatedly retrieving everything. |
| Reflection Board reuse discovery | Planning finds the real closed v1 launch ledger, compares its unique trust/receipt controls with external SDD's disposable ledger and reviews, records the trade-off, and leaves all board artefacts unchanged. |
| External delegation | Read-only independent work routes only to external dispatch; an approved multi-task plan may route to SDD. Both return to Memory Seed before integration/cleanup, and unavailable exposure uses the named local fallback. |

Run deterministic checks appropriate to each modified owner (unit/contract tests, packet validation,
documentation/link checks, and an ESR) plus behavioural scenarios. For every metric, test the instrument
with a negative control or other discriminating case before treating a clean result as evidence.

## Measurement plan

For a small, declared set of comparable tasks, capture baseline and post-adoption evidence separately:

- number and kind of discovered alternatives/constraints that changed the plan;
- decision or authority conflicts caught before versus during/after implementation;
- hypothesis-led debugging attempts and changes after architectural reassessment;
- verification failures, review findings, reopen/rework events, and their stated causes;
- evidence-packet size, refresh count, repeated retrieval avoided, and actual token/latency/cost only when
  the execution surface exposes them; otherwise record `unavailable` and why;
- time from task start to an accepted, verifiable plan and to completed verification, with task complexity
  recorded so unlike work is not treated as comparable.

The comparison should report limitations, selection bias, and uncertainty. It must not use board existence,
stars, anecdotes, or a completed-looking schema as proof of reduced cost or improved quality.

## Non-goals

- Implementing this proposal, changing workflow behaviour, or disabling the Reflection Board in this work.
- Replacing Memory Seed authority, worktree safety, session fusion, integration, cleanup, or durable memory.
- Making Superpowers, network access, or an upstream version a core runtime dependency.
- Rewriting history, changing the Constitution, deciding the ADR migration, or inventing an unverified topic
  coverage claim.

## Source trail

- [Existing Superpowers collaboration integration proposal](../2_Todo/superpowers-collaboration-integration-proposal.md)
- [Existing Superpowers integration skill](../../.memory-seed/skills/superpowers_integration.md)
- [Agent collaboration owner](../../.memory-seed/skills/agent_collaboration.md)
- [Current Constitution](../CONSTITUTION.md)
- [ADR scope proposal](adr-ledger-evolution-and-reasoning-semantics-plan.md)
- [Reflection Board workstream plan](../2_Todo/reflection-ledger-workstream-evolution-plan.md)
- [Official Superpowers repository and catalogue](https://github.com/obra/superpowers)
- [Official dispatching-parallel-agents skill](https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md)
- [Official subagent-driven-development skill](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md)
