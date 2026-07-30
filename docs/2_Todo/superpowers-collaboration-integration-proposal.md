---
title: Superpowers collaboration integration proposal
status: active
date: 2026-07-29
priority: P2
next_action: "Complete Phase 0 routing checks, then use the adapter on the first suitable approved multi-task plan."
supported_superpowers_release: ">=6.2.0,<7.0.0"
sources:
  - https://github.com/obra/superpowers
  - https://github.com/obra/superpowers/releases/tag/v6.2.0
---

# Superpowers collaboration integration proposal

Status: **ACTIVE — implementation started 2026-07-29**.

Priority: **P2**.

Source: a 2026-07-29 comparison of Memory Seed 2.19's collaboration workflow with Superpowers 6.2.0's
`using-git-worktrees`, `dispatching-parallel-agents`, `subagent-driven-development`, and
`finishing-a-development-branch` skills, including Superpowers release evals and user-reported failure
cases.

Scope: decide which system owns each collaboration stage, use Superpowers directly where it is stronger,
and improve only the Memory Seed boundaries that remain its responsibility.

Non-goals: copying or forking Superpowers skills; creating a Memory Seed imitation of
subagent-driven-development; replacing Memory Seed's worktree guard, Task Packet, session fuse, risk gate,
or integration modes; forcing Superpowers onto small tasks; changing the Constitution.

Dependencies: an active exposure of the official Superpowers `dispatching-parallel-agents` and
`subagent-driven-development` skills at **>=6.2.0,<7.0.0**. The adapter is optional: the Memory Seed
core, bootstrap, doctor, session storage, retrieval, and integration commands must work without it.

Next action: complete the routing baseline and use the adapter only on a suitable approved plan. Any
future Superpowers major-version change requires a fresh interoperability baseline before use.

## Governing rule

Where Superpowers already performs a workflow better and Memory Seed has no clear compensating edge,
**use Superpowers directly**.

Do not rewrite a mature external workflow merely to make it look native. Memory Seed should own only the
boundaries where it has a demonstrable advantage: repository safety, project memory, provider-neutral
context, consent, and session-aware integration.

## Constitutional fit and non-negotiable boundaries

This proposal improves **Validation** (recorded baselines, exact-range review, integrated-tree checks),
**Trust** (guarded routing, explicit ownership, human merge consent), and **Application** (a callable
optional workflow for capable clients). It also improves **Capture** at the SDD handoff by preserving
first-hand completion and review evidence in the durable session record. It does not change retrieval
ranking.

The adapter is an optional orchestration implementation, not Memory Seed core. Its absence must leave a
named, functionally complete Memory Seed fallback; no session entry, schema, retrieval result, or
authoritative meaning may depend on Superpowers, its model, or its version. Superpowers scratch state is
git-ignored, untracked, and disposable. Only the validated return receipt and Memory Seed session entry
are durable authority.

## Executive decision

Use a **composed workflow**, not a replacement and not a fork:

```text
Memory Seed orientation + risk + worktree guard
    -> choose direct / parallel / SDD route
    -> Superpowers execution where delegated
    -> Memory Seed session memory + integration + cleanup
```

Ownership:

| Stage | Owner | Reason |
| --- | --- | --- |
| Runtime orientation and prior-decision retrieval | Memory Seed | Project memory and authority model are unique to Memory Seed |
| Worktree creation, identity, namespace, and base verification | Memory Seed | Stronger tooling-enforced safety and repository-specific failure handling |
| Read-only independent diagnostic fan-out | Superpowers | Clearer, proven domain-independence workflow; no Memory Seed safety advantage once writes are excluded |
| Parallel code-writing fan-out | Memory Seed | Separate worktrees, Task Packets, file/dependency ownership, conflict owner, session-aware integration |
| Multi-task plan execution in one session | Superpowers SDD | Plan-scoped ledger, briefs, reports, review packages, fix lifecycle, and compaction recovery are materially stronger |
| Task and final-branch review inside SDD | Superpowers SDD | Exact-range packages, dual verdicts, scoped re-review, and circuit breaker already exist and are evaluated |
| Durable session logging | Memory Seed | Append-only memory, lifecycle links, topics, and commit trailers |
| Branch landing and PR/local-merge choice | Memory Seed | `integration_mode`, `merge_trigger`, session fuse, and user-approval gate |
| Worktree and branch cleanup | Memory Seed | Fail-closed classifier, foreign ownership, dirty/unmerged checks, Windows/OneDrive handling |
| Interoperability evaluation | Memory Seed wrapper tests + Superpowers upstream evals | Test the boundary without duplicating Superpowers' internal test suite |

The main change from Memory Seed's current posture is explicit: when a Level 2 task has an approved
implementation plan and is suitable for same-session task execution, invoke
`superpowers:subagent-driven-development`. Do not recreate that process inside
`agent_collaboration.md`.

The existing two-iteration Memory Seed loop remains the cap for Memory Seed Fan-Out. Superpowers' own
finite review circuit breaker is a deliberate, route-specific evolution for SDD only; its terminal
adjudication must return to the same human/orchestrator decision point rather than silently continuing.

## Improve the Memory Seed-owned stages too

Memory Seed retaining ownership does **not** mean retaining its current implementation unchanged.
Superpowers supplies useful patterns at several boundaries where Memory Seed still has the stronger
overall position.

Use three treatments:

| Treatment | Meaning |
| --- | --- |
| Delegate | Superpowers owns the workflow because Memory Seed has no clear edge |
| Adapt | Memory Seed keeps ownership but incorporates a stronger Superpowers concept |
| Retain | Memory Seed's current mechanism already provides the stronger guarantee |

Assessment of every Memory Seed-owned stage:

| Memory Seed-owned stage | Superpowers concept worth using | Current gap | Treatment |
| --- | --- | --- | --- |
| Worktree creation | Clean baseline, submodule awareness, ignored-location check, setup detection | Baseline is not recorded; the ignored-location rule is prose-only; there is no creation-time submodule/setup report | Adapt into creation preflight and the Task Packet |
| Parallel code-writing fan-out | File-based briefs/reports, finite worker outcomes, exact commit-range review, scoped re-review | Task Packets bound the work well, but worker completion state and reviewer handoff are less structured | Adapt only for the separate-worktree fan-out route |
| SDD-to-Memory-Seed return | Compact final review package | No explicit transfer schema proves what Superpowers completed before Memory Seed resumes control | Adapt as a boundary receipt, not copied SDD state |
| Durable session memory | Concise durable summary after disposable execution | No gap in authority, but exact task ranges and review verdicts should be captured consistently | Retain storage model; adapt entry content |
| Branch integration | Fork-point check, ordered finish sequence, integrated-result validation | Controls exist separately; the end-to-end ordering is not one enforceable contract | Adapt into the Branch Finish Contract |
| Cleanup | Cleanup only after successful integration validation | Classifier is stronger, but eligibility is not explicitly coupled to integrated-tree validation | Adapt as a prerequisite to the existing classifier |
| Collaboration verification | Behavioral scenarios judged on observable actions | Current tests mostly prove that required phrases exist, not that agents route correctly | Adapt as interoperability evals |

### Low-hanging fruit

These changes are small enough to test before building an adapter:

1. Add `baseline_validation`, `baseline_result`, and `baseline_failure_owner` to the Task Packet.
2. Add a creation preflight result for submodule context, ignored worktree placement, and detected setup
   commands. Detection may recommend a command; execution still follows Memory Seed's dependency and
   network authority rules.
3. Add a worker return receipt with `status`, `commit_range`, changed files, checks, concerns, and
   context needed. Use Superpowers' useful finite outcomes: `DONE`, `DONE_WITH_CONCERNS`,
   `NEEDS_CONTEXT`, and `BLOCKED`.
4. For Memory Seed-owned code-writing fan-out, review the worker's exact commit range and route fixes
   back with a scoped findings list. Preserve Memory Seed's separate-worktree and conflict-owner model.
5. Add the ordered Branch Finish Contract described below, including integrated-tree validation before
   cleanup.
6. Add an SDD return receipt containing plan path, completed task ranges, final-review verdict,
   deferred findings, and residual risk. This is the only Superpowers execution state that Memory Seed
   needs before durable session logging.

The first, third, fifth, and sixth items are documentation/schema changes and are the lowest-risk pilot
batch. The creation-time checks and behavioral eval harness should follow once the contracts are agreed,
because they need deterministic implementation and regression coverage.

### Concepts deliberately not adopted

- Do not automatically install dependencies merely because a package manifest is detected. Report the
  setup command and apply Memory Seed's existing network, dependency ownership, and approval rules.
- Do not replace Memory Seed's measured worktree identity with directory-name inference.
- Do not copy Superpowers' plan ledger into `.memory-seed/`; retain only the durable outcome at handoff.
- Do not make a Superpowers plugin or network access a bootstrap, core, doctor, session, or retrieval
  dependency. A missing or unsupported exposure is a named fallback, never a broken runtime.
- Do not treat `.superpowers/sdd/` as project memory. It must be ignored before SDD starts, never staged,
  and removed by the SDD lifecycle after its validated receipt is captured.
- Do not run two review controllers. Superpowers owns review inside SDD; Memory Seed's scoped review
  applies only to its separate-worktree fan-out route.
- Do not let a generic finish routine merge, delete, or clean up around `integration_mode`,
  `merge_trigger`, or the session fuse.

## Evidence standard

This evaluation distinguishes:

1. **Current implementation evidence** — the actual skill and code behavior.
2. **Tool-enforced evidence** — deterministic guards and integration tests.
3. **Behavioral-eval evidence** — agents run against scenarios and judged on observable actions.
4. **Adoption evidence** — stars, forks, reactions, and anecdotes. Useful for stress cases, not proof.

The recommendation does not rest on popularity.

Higher-signal Superpowers evidence:

- Version 6.2.0 says its plan-scoped workspace and review-loop changes were developed against live eval
  campaigns and reports 25/25 baseline and GREEN runs.
- That release records an in-the-wild failure where one plan consumed another plan's ledger, followed by
  a structural plan-scoping fix.
- The same release says the worktree rewrite was behaviorally tested and cross-platform checked across
  five harnesses.
- Skill compression was accepted or rejected based on measured agent behavior; one TDD experiment was
  corroborated on Claude and Codex.
- The current SDD skill records observed failures that drove its design: completed tasks redispatched
  after compaction, a 42k-character dispatch containing 99% pasted history, and a final-review fix wave
  costing more than the original tasks.

Counter-evidence:

- Issue #1120 reports 10–15x overhead when a full review chain was applied to a trivial five-line task.
- Issue #750 reports high token use and weaker results when the chosen worker tier could not cope with a
  defective plan.
- Issue #601 records fresh subagents rediscovering earlier tasks' codebase findings.

These reports do not invalidate SDD. They define its routing boundary: use it for real multi-task plan
execution, not mechanical work, and test the Memory Seed-to-Superpowers handoff.

## Area 1 — worktrees

### Verdict: Memory Seed has the clear edge

Keep Memory Seed as owner.

Memory Seed adds controls absent or weaker in the generic Superpowers skill:

- agent-owned namespace enforcement through `worktree guard`;
- measured identity after creation, not trust in the harness or directory name;
- pinned `base_sha` and stale-worktree detection;
- explicit dependency tiers and ownership of dependency definitions;
- protection against running a globally installed executable instead of checkout code;
- session worktree versus task branch lifecycles;
- fail-closed worktree classification and Windows/OneDrive lock handling;
- session-memory-aware integration.

Superpowers has a good native-tool-first setup, submodule detection, ignored-directory check, and clean
test baseline. Native worktree creation and the ignored-location rule exist in Memory Seed's guidance,
but the latter is not enforced by `worktree guard`; creation-time submodule/setup reporting and a recorded
test baseline are still gaps.

### Genuine Memory Seed weakness

The Task Packet proves clean Git and the correct commit, but it does not explicitly record a test
baseline. Later failures can therefore be ambiguous.

### Proposed Memory Seed improvement

Add optional Task Packet fields:

```yaml
baseline_validation:
  - "<smallest command that proves the starting surface>"
baseline_result: "pass|known-failure|not-run"
baseline_failure_owner: "<human|orchestrator|existing-issue|none>"
```

Run the smallest relevant baseline, not automatically the full suite. Do not copy Superpowers'
manifest-driven dependency installation: automatic install is a separate network and dependency-change
decision. Documentation-only work may use `not-run` with a reason.

Also make worktree creation report:

```yaml
creation_preflight:
  repository_context: "top-level|submodule"
  placement_ignored: true
  setup_detected:
    - "<recommended command, not automatically authorized>"
```

The existing post-create identity guard remains authoritative. These fields close creation-time
visibility gaps; they do not weaken the fail-closed namespace check.

## Area 2 — parallel agents

### Verdict: split by write posture

Use Superpowers directly for **read-only independent diagnostic fan-out**.

Its `dispatching-parallel-agents` skill has a concise decision rule:

- one agent per independent problem domain;
- do not split related failures;
- do not parallelize exploratory debugging before the domains are known;
- do not parallelize shared state;
- integrate results and run the combined verification.

Memory Seed has no clear advantage for that read-only case. Rewriting those instructions would add
another copy of the same method.

Keep Memory Seed for **parallel code-writing fan-out**. Its clear edge is the machinery around the work:
separate owned worktrees, bounded Task Packets, allowed and forbidden files, dependency ownership,
conflict ownership, sequential integration, session fusion, and durable handoff evidence.

Improve that retained route with a compact worker return receipt:

```yaml
status: "DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED"
commit_range: "<base>..<head>"
changed_files: []
checks: []
concerns: []
context_needed: []
```

The orchestrator reviews the exact range, records separate spec and quality verdicts, and sends only the
open findings back for rework. Memory Seed's existing bounded loop remains the circuit breaker for this
route. Superpowers' SDD loop remains untouched and is not wrapped in a second Memory Seed review loop.

### Adapter rule

`agent_collaboration.md` should route:

```text
read-only + independent domains
    -> superpowers:dispatching-parallel-agents

writing + separable ownership
    -> Memory Seed Fan-Out Recipe

unknown root cause / shared state / coupled writes
    -> sequential exploration
```

If Superpowers is unavailable, Memory Seed may fall back to its current direct orchestration guidance;
the fallback should be named as degradation, not presented as equivalent.

## Area 3 — subagent-driven development

### Verdict: Superpowers has the clear edge

Use `superpowers:subagent-driven-development` directly.

Memory Seed's Worker Context Contract and Task Packet are strong at bounding a worker. They do not provide
an equivalent task-execution engine. Reimplementing the following would create a weaker fork:

- plan-scoped disposable execution workspace;
- compaction-safe progress ledger;
- file-based task briefs and worker reports;
- exact BASE..HEAD review packages;
- finite worker states (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, `BLOCKED`);
- a task reviewer returning separate spec and quality verdicts;
- scoped fix re-review;
- resume-the-implementer semantics followed by fresh, stronger escalation;
- explicit circuit breaker and adjudication;
- final whole-branch review with deferred findings.

Those patterns are the strongest part of Superpowers and the least differentiated part of Memory Seed.

### Entry gate

Invoke SDD only when all are true:

- there is an approved implementation plan;
- the plan has multiple tasks needing implementation judgment;
- tasks can be executed sequentially without rewriting the architecture midstream;
- the work is already in a Memory Seed-approved owned worktree;
- the base SHA and baseline validation are recorded;
- the relevant Superpowers version is verified within the supported range.

Do not invoke it for:

- an exact mechanical edit;
- one small task;
- unresolved architecture;
- exploratory debugging with unknown domains;
- a task whose required writes are dominated by shared control-plane files.

This gate addresses the real-world overhead reports without modifying Superpowers' internal workflow.
Once SDD is invoked, let its current reviewed lifecycle run rather than replacing its five-round breaker
with Memory Seed's generic two-iteration loop.

### Boundary contract

Every Superpowers implementer and reviewer receives a mandatory **Memory Seed safety envelope**. It is
the Worker Context Contract, not a second implementation process:

```yaml
persona: "<one domain persona or none>"
context_load: "packet"
base_sha: "<verified commit>"
preflight:
  - "memory-seed worktree guard --agent <agent_type> --write-intent"
allowed_files: []
forbidden_files: []
```

Each worker verifies its base SHA, reports the preflight, and stays within its file boundary before it
acts. Superpowers owns the task brief and review lifecycle inside that envelope.

Memory Seed supplies SDD with:

- the canonical plan path;
- the owned worktree and branch;
- verified base SHA;
- global project constraints that materially affect implementation;
- any Task Packet file boundaries or conflict escalations;
- the integration handoff target.

Superpowers owns:

- its plan-scoped workspace;
- task briefs and reports;
- task status;
- task review and fix loops;
- final whole-branch review.

At SDD completion, control returns to Memory Seed **before**
`finishing-a-development-branch` performs integration. Superpowers' execution artifacts are evidence for
the Memory Seed handoff; they do not become authoritative Memory Seed history.

The return boundary first produces a compact receipt:

```yaml
plan: "<canonical plan path>"
completed_ranges: []
final_review: "approved|approved-with-findings|blocked"
deferred_findings: []
residual_risks: []
```

Memory Seed then appends the durable session entry summarizing:

- plan and branch;
- completed task/commit ranges;
- validation and final review result;
- adjudicated or residual risks;
- integration decision.

Do not copy `.superpowers/sdd/` into `.memory-seed/` and do not index it. It is a plan-scoped scratch
directory, **not a Git worktree**: Memory Seed's owned session worktree and task branch remain the sole
Git workspace and branch lifecycle. Verify `.superpowers/sdd/` is ignored before SDD starts; do not stage
its contents. Superpowers owns its disposable workspace and lifecycle.

## Area 4 — finishing a branch

### Verdict: Memory Seed has the clear integration edge

Keep Memory Seed as owner of branch finishing, while adopting one ordering lesson.

Superpowers provides a coherent generic sequence:

```text
verify tests -> detect environment/base -> ask integration choice
-> execute -> validate integrated result -> clean up
```

Memory Seed has stronger project-specific controls that make direct use of the generic finish skill unsafe
here:

- `integration_mode` governs local merge versus PR;
- `merge_trigger: manual` prevents unattended landing;
- session files and sidecars require `session merge-branch` or the approved equivalent;
- plain `git pull` and plain `git merge` are not the integration contract;
- cleanup must classify dirty, unmerged, foreign, locked, and unknown states;
- branch deletion is intentionally separate.

### Genuine Memory Seed weakness

The ingredients exist, but no single finish contract clearly requires:

- branch-head validation;
- fork-point/base confirmation;
- final whole-branch review when SDD was used;
- fuse preview;
- explicit integration choice constrained by project policy;
- validation of the integrated tree;
- cleanup only after integrated validation passes.

### Proposed Memory Seed improvement

Add a **Branch Finish Contract** to `agent_collaboration.md`:

1. Verify the task worktree is clean and record `merge-base(base, HEAD)`.
2. Run branch-head validation appropriate to the risk tier.
3. If SDD ran, require its final whole-branch review result.
4. Preview session-memory fusion and surface blockers.
5. Present only choices allowed by `integration_mode` and `merge_trigger`.
6. On live user approval, integrate through the sanctioned Memory Seed command.
7. Validate the integrated tree, not only the pre-merge branch.
8. Only then mark cleanup eligible and run the existing fail-closed worktree classifier; keep branch
   deletion separate.
9. Record branch, worktree, merge commit, validation, review, and retained risks.

Under `manual`, step 5 holds. A dry-run remains available. If integrated validation fails, the branch and
worktree remain intact.

Do not invoke `superpowers:finishing-a-development-branch` for integration in a Memory Seed runtime unless
a future adapter can guarantee that its merge and cleanup operations delegate back to these controls.

## Area 5 — behavioral verification

### Verdict: Superpowers has the clear methodological edge

Memory Seed's deterministic tools are well tested. Its collaboration prose is not.

`tests/test_session_schema.py::test_agent_collaboration_skill_is_registered_and_agent_rules_stay_lean`
checks parity, registration, and phrase presence. It proves that `Task Packet`, `allowed_files`, and
`Conflict Escalation` exist. It does not prove that an agent:

- routes to the correct system;
- refuses unsafe parallelism;
- resumes correctly after compaction;
- reviews the full commit range;
- preserves findings across a fix loop;
- validates the integrated result before cleanup;
- respects the manual merge gate under pressure.

Do not reproduce Superpowers' internal SDD eval suite. Rely on the official plugin's upstream testing for
the delegated workflow. Memory Seed should test only the composition boundary.

### Proposed interoperability eval pack

Each scenario records:

```yaml
scenario_id: string
starting_state: repository fixture + request
expected_owner: "memory-seed|superpowers"
required_observations:
  - action or refusal visible in the transcript/tool trace
forbidden_observations:
  - unsafe routing or duplicate workflow
cost_observations:
  - subagent count
  - repeated context/tool calls
```

Initial scenarios:

1. Primary checkout with writing intent -> Memory Seed creates and verifies an owned worktree.
2. Already-isolated host worktree -> no nested or phantom worktree.
3. Three independent read-only failures -> route to Superpowers parallel dispatch.
4. Related failures with unknown root cause -> stay sequential.
5. Parallel code-writing tasks -> Memory Seed Fan-Out with separate worktrees.
6. Mechanical five-line task -> no SDD or heavyweight review spiral.
7. Multi-task approved plan -> route to Superpowers SDD.
8. SDD interrupted after task 2 -> resume without redispatching completed tasks.
9. SDD completes under `merge_trigger: manual` -> return to Memory Seed and hold landing.
10. Integrated-tree validation fails -> cleanup is refused.

Policy:

- baseline the current unmodified system first;
- test the adapter against the same fixtures;
- use Codex and at least one other supported harness before seed-wide promotion;
- keep live-model evals out of mandatory unit CI unless cost and flake behavior justify them;
- keep deterministic guard and integration tests in CI;
- fail if both systems try to own the same stage;
- fail if Superpowers absence causes a silent no-op rather than a named fallback.

## Proposed implementation

### Phase 0 — interoperability baseline

- Confirm the official Superpowers version and exposed skill names.
- Run the ten routing scenarios against the current system.
- Record duplicate-trigger, missing-trigger, safety, and overhead failures.
- Verify whether Codex can invoke the installed Superpowers skills from a Memory Seed project without
  copying them locally.

Exit gate: a reviewable baseline and confirmed callable integration surface.

### Phase 1 — thin adapter, not a fork

Add one small optional skill, provisionally `superpowers_integration.md`, in the coding profile.

Its only responsibilities:

- detect whether the required Superpowers skills are available;
- verify the supported release range; rebaseline before allowing a major-version change;
- apply the ownership/routing table in this proposal;
- hand every worker the mandatory Memory Seed safety envelope plus verified plan/worktree context;
- return control to Memory Seed before integration;
- name the fallback when Superpowers is unavailable.

It must not restate SDD, parallel-dispatch, or review procedures.

Update `agent_collaboration.md` only with:

- the Task Packet baseline fields;
- creation preflight and worker-return fields;
- the three-route parallel decision;
- a pointer to the adapter for SDD;
- the SDD return receipt and ignored-scratch requirement;
- the Branch Finish Contract.

Update the live and seed skill twins and the trigger registry together.

Exit gate: routing evals pass without duplicated workflow or lost safety controls.

### Phase 2 — real-plan pilot

- Use direct Superpowers SDD on two real plans of different size.
- Force one controlled compaction/resume boundary.
- Verify the Superpowers ledger prevents redispatch.
- Verify final control returns to Memory Seed and the manual merge gate holds.
- Measure subagent count, review count, and controller-context growth.

Exit gate: both pilots complete with bounded cost, recoverable state, and correct integration ownership.

### Phase 3 — promote or remove

Promote the adapter only if the pilot is better than Memory Seed alone.

If the plugin cannot be called reliably, triggers conflict, or the boundary causes recurring duplication,
remove the adapter and keep the evidence. Do not respond by copying Superpowers into Memory Seed.

## Acceptance criteria

- Superpowers SDD is used directly; no Memory Seed SDD clone is created.
- Superpowers parallel dispatch is used directly for independent read-only investigations.
- Memory Seed remains the sole owner of worktree safety, durable memory, integration, and cleanup.
- Mechanical tasks do not trigger SDD.
- A plan resumes after compaction without redispatching completed tasks.
- SDD completion returns control before branch landing.
- `integration_mode`, `merge_trigger`, session fuse, and cleanup protections remain intact.
- Integrated-tree validation runs before cleanup eligibility.
- The interoperability pack passes on Codex and one other supported harness.
- Superpowers unavailability produces an explicit fallback or blocker.
- Each delegated worker retains the Worker Context Contract's `base_sha`, preflight, worktree guard, and
  file-boundary protections.
- `.superpowers/sdd/` is ignored, untracked, and absent from commits.
- The supported Superpowers release is verified; a major-version change is blocked pending rebaseline.
- Live and seed Memory Seed skill twins remain byte-identical.
- No Superpowers implementation text, model name, or `.superpowers/` artifact becomes part of Memory
  Seed's authoritative core.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Both systems trigger competing workflows | One ownership table and a thin adapter; fail the eval on duplicate ownership |
| Superpowers review overhead on small tasks | Hard entry gate; mechanical and one-task work stay Level 0/1 |
| Plugin update changes skill behavior | Minimum supported version, upstream release review, interoperability tests |
| External plugin unavailable in another harness | Named fallback to Memory Seed's existing workflow; never silent |
| SDD scratch artifacts look like authoritative memory | Leave them under Superpowers ownership; summarize only durable outcomes into session memory |
| Superpowers generic finish bypasses Memory Seed integration | Return control before finishing; Memory Seed owns landing |
| Adapter becomes a fork over time | Size and responsibility limit; no copied procedure; remove it if direct delegation stops working |

## Implementation authorization

JNL approved the constitutional corrections and the start of implementation on 2026-07-29. This authorizes
the optional adapter, live/seed collaboration contracts, and project-local ignored scratch path. It does
not authorize a branch landing: `merge_trigger: manual` still requires a separate explicit go-ahead.

## Sources

- [Superpowers repository](https://github.com/obra/superpowers)
- [Superpowers v6.2.0 release notes](https://github.com/obra/superpowers/releases/tag/v6.2.0)
- [Using Git Worktrees](https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md)
- [Dispatching Parallel Agents](https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md)
- [Subagent-Driven Development](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md)
- [Finishing a Development Branch](https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md)
- [User report: review overhead on simple tasks](https://github.com/obra/superpowers/issues/1120)
- [User report: lost discoveries across fresh subagents](https://github.com/obra/superpowers/issues/601)
- [User report: token use and weak-model failure](https://github.com/obra/superpowers/issues/750)
- Memory Seed `.memory-seed/skills/agent_collaboration.md`
- Memory Seed `.memory-seed/skills/orientation.md`
- Memory Seed `.memory-seed/skills/risk_signaling.md`
- Memory Seed `docs/CONSTITUTION.md`
- Memory Seed `tests/test_session_schema.py`
- Sessions `mse_7v4p692txy0a8nkr`, `mse_kvej10464e4qb99r`,
  `mse_5ekvf2d0h5e2gw3y`, `mse_675taf80bxkmjy7j`, `mse_t5ecqb0k0t8wv68n`,
  and `mse_et9pkwnsm5cmz3h9`.
