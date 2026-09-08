---
memory-system-version: 2.20
governing_adr: adr_worktree_convention
tags:
  - memory-seed
  - skill
  - agent-collaboration
---

# Agent Collaboration Skill

Use this skill for Git-first collaboration involving subagents, branch/worktree coordination, validator passes, merge-conflict handling, or multi-developer agent workflows.

## Principles

- Git-first collaboration: branches and worktrees isolate filesystem state; task packets isolate agent context; review and CI isolate integration risk.
- Follow the repository's existing branch naming convention first. If none exists, use `<agent>/<kind>/<topic>` (the agent segment is required — matches the worktree=session, branch=task model below), where `kind` is `feature|fix|refactor|test|docs`.
- Keep branches short-lived and focused on one coherent feature, fix, refactor, test change, or documentation change.
- Parallel code-writing agents use separate worktrees. Put plainly: parallel code-writing agents use separate worktrees. Read-only research, review, and validation agents may share the current tree.
- The orchestrator owns scope, sequencing, integration, final validation, and durable session logging for subagent work.
- Workers own bounded, non-overlapping file sets and report evidence instead of editing memory/session control files unless explicitly assigned.

## When To Use

Load this skill when the task involves any of:

- spawning or coordinating subagents
- assigning work across multiple humans using agents
- creating or reviewing feature branches
- using git worktrees to isolate parallel work
- preparing a worker or validator handoff
- resolving merge conflicts caused by agent or multi-developer edits
- deciding whether work should happen inline, on a branch, in a worktree, or through a pull request

## Collaboration Modes

### Single-Agent Branch Work

- Use when one agent implements one scoped change.
- Work on a branch unless the user explicitly asks to work directly on the current branch.
- Keep commits reviewable and run the smallest relevant validation before handoff.

### Orchestrated Subagents

- Use when splitting work reduces risk, wall-clock time, or context load.
- Orchestrator prepares Task Packet entries for each worker.
- Each code-writing worker gets a separate worktree unless the task is strictly sequential.
- Validators review from the integration branch or final diff, not from a worker's unmerged assumptions.

#### Continuous monitoring contract

Every dispatched planner, implementer, researcher, validator, and plan reviewer remains an active orchestration
gate until it reaches a terminal result. The orchestrator owns that gate and must:

1. record the dispatched agent and the outcome or verdict that will close the gate;
2. wait or poll through the collaboration surface at reasonable intervals instead of relying on the human to
   notice completion;
3. surface a meaningful blocker or requested decision promptly;
4. read and act on the terminal report before sequencing dependent work; and
5. close or supersede the gate explicitly in the plan ledger or handoff record.

A status update to the human does not close a running gate. Planning and plan-review agents follow the same
rule as implementation agents: once launched, they are monitored through `APPROVE`, `REVISE`, `BLOCKED`, or
another declared terminal contract. Prefer bounded waits and event cursors where the collaboration surface
supports them; avoid busy polling, but never leave completion discovery to the human.

### Multi-Developer Agent Work

- Use per-developer branches and per-user session targets where configured.
- Prefer pull requests, protected integration branches, CI, and merge queues when the hosting provider supports them.
- Treat GitHub, GitLab, and similar PR systems as optional integration layers; the portable contract is Git branch, worktree, validation, and handoff evidence.

## Worker Context Contract

A worker starts as a **clean session** and loads its **Task Packet + at most one domain persona +
objective-triggered skills**. Nothing else. It does not inherit the primary agent's conversation or broad
primary-agent orientation.

`agent-rules.md` "Operating Mode Start" is written for the **primary** agent, which has to establish
current project state for itself. A worker does not: the orchestrator already holds that state and
distilled it into the packet. So a worker **skips** primary orientation and latest-session loading
(steps 4–5), the whole skill registry (step 6), project-wide index/policy/Constitution/ADR loading
(steps 7–9), and load-all-active-personas (step 10). Its packet names the one persona, triggered skills,
and any policy, Constitution, or ADR context its objective actually requires.

It **still runs** `base_sha` verification, the packet's `preflight`, and the worktree guard. The
exemption is about *context volume*, never about safety rails — a worker that skips the guard is not
slim, it is unsafe.

Two reasons this is a contract and not an optimisation:

- **Waste.** Four persona operating systems and a whole-project index are irrelevant to "edit these two
  files and run these checks".
- **Coordination risk.** A worker steeped in whole-project context is likelier to act outside its
  `allowed_files` or re-derive a safeguard the packet already fixed — it starts *reasoning about the
  project* instead of executing a bounded objective.

Two packet fields carry it:

- **`persona:`** — the single domain persona to load, or `none`. Not a role/orchestration label:
  "orchestrator/worker/reviewer" and "developer/copywriter" are different axes, and conflating them is
  what this contract exists to avoid. `role:` already carries the orchestration axis.
- **`context_load:`** — `packet` (the contract above) or `full` (run Operating Mode Start as a primary
  would). Default to `packet` for a bounded objective. Use `full` only when the objective genuinely
  needs project-wide state, e.g. "reconcile the roadmap against the corpus".

Set `context_load: full` deliberately, not defensively. If a worker truly needs whole-project state,
the packet is probably under-specified.

## Task Packet

Every worker packet should include:

```yaml
owner: "<human-or-agent-slug>"
agent_type: "codex|claude|gemini|cursor|other"
role: "worker|validator|researcher"
persona: "<one domain persona slug, or 'none'>"
context_load: "packet|full"
base_branch: "<branch to start from>"
base_sha: "<commit hash the worker must verify before editing>"
working_branch: "<branch to write to, or read-only>"
worktree_namespace: ".codex/worktrees|.claude/worktrees|.gemini/worktrees|.cursor/worktrees|custom"
worktree: "<path or 'current tree for read-only work'>"
expected_pwd: "<worktree path or repository root>"
objective: "<one concrete outcome>"
integration_artifact: "pr|merge-request|patch|branch|handoff"
capability_tier: "economy|standard|frontier"
shared_file_policy: "orchestrator_only"
dependency_tier: "none|isolated|dependency-changing"
dependency_setup: "<none|per-worktree env command|orchestrator-coordinated>"
dependency_definition_policy: "orchestrator_only"
dependency_shared_cache_policy: "<shared read-only cache path, or 'none'>"
conflict_owner: "<orchestrator|worker|human>"
allowed_files:
  - "<paths or globs the worker may edit>"
forbidden_files:
  - "<paths or globs the worker must not edit>"
preflight:
  - "memory-seed worktree guard --agent <agent_type> --write-intent"
  - "pwd"
  - "git rev-parse --show-toplevel"
  - "git rev-parse HEAD"
  - "git status --short"
baseline_validation:
  - "<smallest command that proves the starting surface>"
baseline_result: "pass|known-failure|not-run"
baseline_failure_owner: "<human|orchestrator|existing-issue|none>"
creation_preflight:
  repository_context: "top-level|submodule"
  placement_ignored: true
  setup_detected:
    - "<recommended command; never automatically authorized>"
validation:
  - "<commands or checks to run>"
handoff_output:
  - "status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED"
  - "summary"
  - "files changed"
  - "commit range and hashes"
  - "tests run and result"
  - "known risks or conflicts"
conflict_escalation:
  - "<conditions requiring orchestrator or human review>"
review_loop:
  current_iteration: 0
  max_iterations: 2
  escalation: "<human-or-orchestrator>"
```

Keep packets narrow. Do not hand a worker the whole repository history when a path list, current plan, and a few relevant files are enough. Use capability tiers, never vendor or model names — providers change; roles and capability requirements are durable.

### Clean-session, high-signal packet convention

The frontier-authored artifact is the **semantic dispatch**: a minimal
`memory-seed/task-dispatch` v1 object that states the objective, grounded project frame, execution
contract, exact Retrieval Profile identity plus bounded overrides, budget, and memory-update policy.
Frontier judgment chooses meaning and scope; it does not hand-author the expanded packet. Deterministic
tooling combines that dispatch with the immutable profile version, measured runtime binding, and
pinned corpus revision to reconstruct the complete `memory-seed/task-packet` v1 artifact.

This compiler boundary is local and non-expansive. It adds no packet registry, worker dispatch,
worktree creation, authority, provider lookup, pricing lookup, or network access. Profiles and Markdown
remain readable project-local inputs; Evidence Packs and compiled Task Packets are derived and ephemeral.

```yaml
schema: memory-seed/task-dispatch
version: 1
objective: "<one concrete outcome>"
project_context:
  project_type_and_purpose: "<what this project is for>"
  relevant_subsystem: "<the surface this task touches>"
  task_fit: "<why this objective belongs in that surface>"
  downstream_use: "<who or what consumes the result>"
  non_goals:
    - "<explicitly excluded work>"
execution:
  role: worker
  persona: none
  capability_tier: "economy|balanced|frontier"
  write_intent: "read-only|writing"
  allowed_files: []
  forbidden_files: []
  validation: []
  output_contract: []
retrieval:
  profile: "<exact project-local profile ID>"
  profile_version: "<positive integer>"
  overrides: "<bounded v2 selector/filter overrides>"
budget:
  supplemental_input_tokens: "<reserved task-scoped reads>"
  output_tokens: "<output/reasoning reserve>"
  over_soft_cap: fail
  over_soft_cap_reason: null
memory_update_policy: orchestrator
```

The compiled packet is the worker's `context_load: packet` context. Give it a source-grounded
**100–250-token project frame** rather than a broad startup dump. Every worker-visible document counts
toward input: the serialized packet itself, fixed instructions, tool/schema descriptions, materialized
evidence, and any later supplemental fetch. Tool availability never grants additional write, merge,
integration, network, or memory authority.

Task Dispatch `allowed_files` and `forbidden_files` are execution/edit boundaries. They do not filter
Retrieval Specification memory reads, and a path in `forbidden_files` may still be materialized as
task-scoped evidence. Reading evidence never grants permission to edit its source.

#### Orchestrator evidence flow

Before dispatch, the orchestrator:

1. Authors the smallest semantic dispatch that preserves the ability to decide.
2. Measures the existing runtime binding; the compiler validates it and never creates a worktree.
3. Compiles through the exact immutable profile version and Retrieval Specification v2 resolver.
4. Verifies the Evidence Pack before materializing exact ADR current views, decision slices,
   Constitution clauses, sessions, or Markdown ranges.
5. Passes the complete compiled packet to the worker. Evidence Pack v2 keeps one semantic `id`, canonical
   `source`, inclusive range, digest, selection reason, corpus revision, and fingerprints.

Materialized sources are worker input already and **must not be fetched again**. A canonical `source` is
provenance and a supplemental-gap route, not permission to duplicate included content. The handoff reports
repeated fetches as a packet-procedure failure. Excerpts stay disabled in compiled manifests so each
evidence slice appears exactly once, under `materialized_evidence`.

#### Budget and supplemental retrieval

The resolver's `token_estimate` is **evidence-only**; it is not total model input and never replaces the
compiler ledger. Keep three ledgers distinct:

- `input_ledger`: serialized packet input, fixed instructions, tool/schema input, supplemental-input
  reserve, total input, output/reasoning reserve, and the total context envelope;
- output/reasoning reserve: a capacity plan, not consumed input and not provider-reported output; and
- `cost_ledger`: caller-supplied price arithmetic only, explicitly unavailable when prices were not
  supplied.

Do not collapse input, output, and cost into one token or money figure. The input ledger is the
**compiler-accounted caller-supplied envelope**, not actual provider input; hidden platform/system/tool
overhead is unavailable unless the runtime exposes it. Actual provider input/usage, latency, and cost are
**post-run evidence**, recorded only when the provider or execution surface exposes them;
otherwise report each as unavailable with the reason. Never infer actual usage from the resolver estimate,
budget reserve, or price ceiling.

Workers may use the same read tools for a task-scoped gap. They record the missing question, sources
consulted, tool call, and token estimate in their handoff. For every supplemental fetch, debit its estimated
token cost — including fetched evidence content — from the compiler-accounted caller envelope and confirm it was not
already materialized. The resolver `token_estimate` remains only the evidence-content component.
Return `NEEDS_CONTEXT` only when the gap exceeds the budget, objective, or authority — not merely because
additional context might be useful.

#### Memory update policy

Every compiled worker packet materializes the complete active `.memory-seed/agent-rules.md` as baseline
governance. It remains distinct from task-scoped retrieval evidence: it establishes the non-deferrable
worker safety and authority contract without eagerly loading orientation, the skill registry, policy,
unrelated skills, or unrelated authority. The compiler fingerprints and token-accounts this baseline, so
a source change is visible in both the packet identity and context ledger.

`memory_update_policy: orchestrator` is the default: the orchestrator owns durable session logging and
integrates worker evidence. `worker_checkpoint` is allowed only for consequential work with multiple
checkpoints where delaying a first-hand rationale risks losing it. A checkpoint worker — and any worker
whose exact session-log path is writable — also receives the complete active
`.memory-seed/skills/session_logging.md` plus guarded branch-local append mechanics. It must use
`memory_session_append` or the checkout-local `python -X utf8 -m memory_seed.cli session append` path;
the sanctioned writer owns the clock, so direct Markdown session edits and explicit timestamps are
forbidden unless the dispatch grants a narrowly scoped repair/backfill exception. Duration alone never
changes context, authority, or memory ownership; `context_load: full` is reserved for project-wide
reconciliation or deliberate promotion to an orchestrator role.

Under `worker_checkpoint`, the worker may write only its first-hand decisions, evidence, tests, risks, and
explicitly delegated files. Prior entries, policy, index, ADRs, and other shared control-plane files remain
forbidden unless separately assigned. The orchestrator reviews and integrates branch-local memory through
the normal guarded process.

## Optional Superpowers Delegation

Superpowers is an **optional orchestration capability**, never a Memory Seed core dependency. Use the
project's `superpowers_integration.md` skill when an active platform exposes the verified official
`dispatching-parallel-agents` and `subagent-driven-development` skills. Do not infer availability from a
cache directory, a package manifest, or a stale plugin version: the required skills must be callable in
the active client and within the adapter's supported version range.

- **Independent read-only diagnosis:** delegate to Superpowers parallel dispatch when domains are known
  to be independent. There is no Task Packet write entitlement; each investigator still verifies its tree
  before citations are trusted.
- **Multi-task same-session implementation:** delegate the task execution and internal review loop to
  Superpowers SDD only after the Scope and Plan Gates pass.
- **Parallel code-writing:** keep Memory Seed Fan-Out. Separate worktrees, Task Packets, ownership, and
  sequential integration remain necessary.
- **Worktree creation, branch landing, durable memory, and cleanup:** never delegate. Memory Seed owns
  these controls regardless of which task workflow ran.

Every SDD worker and reviewer receives the Worker Context Contract safety envelope: `persona`,
`context_load`, `base_sha`, the packet preflight (including `worktree guard`), `allowed_files`, and
`forbidden_files`. Superpowers owns its task brief and review procedure inside that envelope; it does not
replace the safety rails.

Before SDD starts, verify `.superpowers/sdd/` is git-ignored and clean. It is plan-scoped disposable
scratch, never a Git worktree, a staged artifact, or authoritative Memory Seed history. At completion,
capture only the validated return receipt (plan, completed ranges, final review, deferred findings, and
residual risk) in the orchestrator's durable handoff.

## Fan-Out Recipe: Explore / Plan / Implement / Validate

An optional Level 2/3 pattern for medium-to-large separable work — migrations, feature slices, broad test expansion, refactors with clear module boundaries. Not default behavior: the Scope Gate must state why direct (Level 0/1) work is insufficient. Avoid it for small fixes, tightly-coupled refactors where one coherent design matters more than speed, or work dominated by shared/control-plane files.

Gates, in order:

1. **Scope Gate.** Objective, non-goals, acceptance criteria, base branch/SHA, expected integration artifact, high-risk/shared files, and an explicit call on whether parallel implementation is justified (default: no, unless file ownership is clearly separable and the wall-clock reduction justifies the integration overhead).
2. **Exploration Gate.** Read-only agents, each given one narrow question, returning evidence — recommendations labeled as such, not stated as fact. Explorers may share the current tree since they never write, but that exemption covers write-collision safety only, not staleness: explorers still run the preflight commands and confirm their tree matches the intended base before their reads or citations are trusted.
3. **Plan Gate.** A single orchestrator reconciles explorer conflicts, chooses the architecture, assigns file ownership and interfaces, defines validation commands, and names the conflict owner. Use the strongest available capability tier here — same as review, not lighter. A weak plan poisons every downstream worker; review only catches what is already built.
4. **Worker Identity Gate.** Before a worker touches any file, it reports the packet's `preflight` output; the orchestrator verifies `memory-seed worktree guard --agent <agent_type> --write-intent` passes, then verifies the intended worktree and `base_sha` before the worker proceeds.
5. **Worktree Gate.** Parallel code-writing workers get separate worktrees, each with a bounded task packet. Workers never touch shared memory/session/control-plane files unless explicitly assigned — those stay orchestrator-owned per `shared_file_policy`.
6. **Pre-Review Validation Gate.** Each worker commits its own work and reports changed files, checks run, failures, skipped checks and why, and known risks *before* review. No uncommitted worker state gets integrated.
7. **Integration Gate.** The orchestrator merges worker branches one at a time into an integration branch, inspects the diff after each merge, resolves conflicts only via the named owner, and reruns targeted validation. No octopus merges for code. When branch-local session entries or diagram sidecars exist, integrate that branch with `memory-seed session merge-branch --branch <branch>` — it dry-runs the fuse, performs the `--no-ff` merge, applies the fuse, and commits in one gated step, then attempts to remove only the clean registered worktree for that source branch. Cleanup is Git-only, preserves the branch, and reports rather than force-deletes a dirty, locked, or partially removed checkout. The lower-level `session fuse` dry-run/`--apply` pair remains available for manually inspected merges. Do not fall back to a plain `git merge` for session paths: `.memory-seed/sessions/**` carries a `-merge` attribute, so concurrent session edits conflict wholesale by design (see **Session Files Do Not Line-Merge** below).
8. **Bounded Review-to-Rework Loop.** For Memory Seed Fan-Out, an independent validator (same strong tier as planning) reviews the integrated diff against the plan. Findings route back to the Worktree Gate for revision, tracked by `review_loop.current_iteration` and capped at `max_iterations` (default 2) — then automation stops and produces a human decision summary. The loop must not restart exploration or planning automatically. Superpowers SDD uses its own finite, scoped review circuit breaker; at its cap, it returns a recorded adjudication to this orchestrator rather than silently continuing.
9. **Final Handoff Gate.** The orchestrator (never the workers) writes the integration artifact and the handoff session entry: base SHA, worker branches/worktrees, validation evidence, review result, unresolved risks. Workers' reported commit hashes belong in the handoff entry's records. Set the entry's optional `branch:` field (see `session_logging.md`) from the Task Packet's `working_branch` — a durable record-time label, not a worktree path.

Capability tier guidance: exploration economy/standard; planning **frontier**; implementation standard; integration frontier or a senior orchestrator; review **frontier**. Planning and review both warrant the top tier — a weak plan is more expensive to catch later than a weak review.

## Branch And Worktree Defaults

- Read `.memory-seed/project.yaml` `integration_mode` before integration. Unset/`local-merge` keeps the existing local flow: from the integration/base checkout run `session integrate` or `session merge-branch`, never push. `pr` means from the task branch run `session integrate` or `session open-pr`; the declared mode authorizes only that normal non-force push and PR. A Task Packet's `integration_artifact` is a per-task override; force and destructive operations stay gated.
- Read `merge_trigger` too (fail-open `automatic`). Under `automatic` the agent may land a branch at a stable, tested stopping point. Under `manual` the agent **holds**: `session merge-branch`, `session open-pr` and the lower-level `session fuse --apply` all refuse without `--user-approved`, and MCP `memory_session_integrate` declines — so a raw `git merge` plus a fuse cannot route around the gate either. `--user-approved` represents the *user's* explicit go-ahead — **never supply it on your own initiative**; run it only when the user has said to land the branch. A `--dry-run` is never gated, so previewing the fuse plan under `manual` is always fine.
- Start from the current integration branch, normally `main`, unless the user or repository names another base.
- Update from the base branch before starting long-running work.
- Name branches by repository convention first; otherwise use `<agent>/<kind>/<topic>` (agent segment required).
- Use separate worktrees for parallel code-writing agents to prevent uncommitted file collisions.
- Worktree = session, branch = task: a worktree is a durable per-agent session environment, not a per-task one. Writing agents use their own namespace by default: Codex in `.codex/worktrees/<session>`, Claude in `.claude/worktrees/<session>`, Gemini in `.gemini/worktrees/<session>`, and Cursor in `.cursor/worktrees/<session>`. Configured third-party agents need an explicit namespace in `.memory-seed/project.yaml` before routine write work.
- Before editing in a branch/worktree workflow, run `memory-seed worktree guard --agent <agent> --write-intent`. A foreign namespace is a shared-control-plane STOP hazard; move to the correct worktree unless the user explicitly approves a different path.
- **Worktree identity is measured, never declared — including right after you create one.** A harness banner, a task packet, or an existing `…/worktrees/<session>` directory can each assert a worktree that was never created, and a `git worktree add` can half-fail and leave a bare directory behind. In every one of those cases git resolves upward to the primary checkout, so writes land in shared state while the agent believes it is isolated. After any create-or-enter, verify before the first write: `memory-seed worktree guard --agent <agent> --write-intent` (expect `owned-worktree` and `Safe to write: yes`), or by hand `git rev-parse --show-toplevel` (must return the worktree itself, not the repo root) and `git rev-parse --git-dir` (must point into `.git/worktrees/<name>`). Trusting the create is the same error as trusting the banner, one step later.
- **The tool you run is measured too, not just the tree.** A worktree's `.venv` is usually empty — `uv run --no-sync` never syncs it, and a fresh worktree has none at all — so the project's console scripts do not exist there and the shell resolves the bare name through PATH to a *globally installed, older* build. It runs, it prints, and none of its output is about your checkout: reads report errors for code your tree does not contain, and writes regenerate committed files from code that is not in your diff, producing a regression attributable to nothing in the change. Invoke the checkout's own code instead (for a Python package, `python -m <package>.cli <command>` from the checkout root, which resolves from cwd), or install the project into the worktree venv. `memory-seed` itself refuses to run when the package that loaded is outside the checkout you are standing in, and names the working invocation; most other tools fail silently.
- Root checkout is for read-only inspection, mainline integration, and approved cleanup. Routine feature edits should use an agent-owned task worktree; root writes require an explicit guard override (`--allow-root-write`) and should be recorded in the handoff.
- Do not create a worktree inside a tracked directory unless the worktree directory is ignored.
- **Pass `--branch` explicitly whenever sessions may share a working tree.** `session append` auto-captures `branch:` from git HEAD, and two sessions in one working tree have a genuinely identical HEAD — a session's own branch is never passed to the CLI, so no check or heuristic can recover it. Standing convention: the harness (or an orchestrator appending on a worker's behalf) passes `--branch <name>` on every append, taken from the Task Packet's `working_branch`; use `--no-branch` when the session has no branch worth recording. Worktree-isolated agents may rely on auto-capture, but passing the flag is never wrong. Field semantics live in `session_logging.md`.
- A branch is a **workstream, not a single commit**: keep follow-on fixes, evolutions, and adjacent tweaks of the same goal on the SAME branch — the tell is an `evolves`/`related` lifecycle edge to the entry you just wrote, or the same files/area. Open a new branch only for a genuinely new, independent goal; avoid BOTH stacking unrelated work in one branch AND spawning a fresh branch per commit. Merge the batched workstream at a stable, tested stopping point, never after every commit.

## Branch Finish Contract

Before a branch can land, the orchestrator must:

1. Verify the owned task worktree is clean and record `merge-base(<base>, HEAD)`.
2. Run branch-head validation appropriate to the risk tier.
3. Require Superpowers' final whole-branch review result when SDD ran; otherwise use the Memory Seed
   Fan-Out validator result.
4. Preview session-memory fusion and surface every blocker.
5. Present only integration choices allowed by `integration_mode` and `merge_trigger`.
6. On a live user go-ahead, integrate through `session merge-branch`, `session integrate`, or
   `session open-pr` as the configured mode permits — never a raw merge workaround.
7. Validate the **integrated tree**, not just the branch head.
8. Only after integrated validation passes, run the existing fail-closed cleanup classifier. Branch
   deletion remains a separate decision.
9. Append the handoff record with branch, worktree, merge commit, validation, review result, and
   retained risks.

Under `merge_trigger: manual`, step 5 is a hold. A dry-run is always allowed; a failed integrated-tree
validation leaves the branch and worktree intact.

## Branch History Preservation

Use this when the user expects Git history to show discrete feature branches and merges, or when
multiple writing agents work on different features at the same time.

- A worktree only isolates the working directory; it does not by itself create a visible branch in
  the Git graph. Visible topology requires commits on a task branch plus an integration merge commit.
- A distinct **workstream** (a feature, a proposal implementation, or an unrelated fix/refactor/docs
  effort) uses its own task branch; a follow-on that fixes or evolves the workstream already in progress
  stays on that same branch and lands in the same merge. Use direct `main` work only when the user
  explicitly chooses it for that task.
- Parallel writing agents get one task branch and one worktree each. Read-only researchers,
  reviewers, and validators may share the current tree because they do not write commits.
- Integrate completed task branches one at a time with `git merge --no-ff <branch>` when the desired
  outcome is a visible branch-and-merge graph. Avoid squash, rebase, or fast-forward integration when
  preserving branch shape matters. When the branch carries session entries or diagram sidecars,
  prefer `memory-seed session merge-branch --branch <branch>`, which performs the same `--no-ff`
  merge and fuses the session memory in one step.
- Do not delete task branches before the final handoff if the user wants the branch labels visible in
  local tools. If branches are later deleted, merge commits still preserve topology, but branch labels
  disappear.
- Before feature work starts, run `memory-seed branch status` when available. Treat warnings as a
  prompt to create or switch to a task branch, not as a hard block.
- To promote branch-local memory, run `memory-seed session merge-branch --branch <branch>` from the
  integration tree: it dry-runs the fuse, merges with `--no-ff`, applies the fuse, and commits —
  failing closed (fuse issues abort before the merge starts; non-session conflicts leave the merge
  in progress for the named conflict owner). The merge commit is stamped automatically with one
  `Memory-Entry: <entry_id>` trailer per fused entry (below git's prepared merge message), so
  `link commits` and trailer scans resolve fused entries to their integration point with no manual
  step. For a manually inspected merge, the lower-level
  `session fuse --branch <branch>` dry-run remains available; its `--apply` requires an in-progress
  `git merge --no-ff --no-commit <branch>`.
- Final handoff records the base SHA, task branch, worktree path, merge method (`--no-ff` when used),
  merge commit if available, validation, and unresolved risks.

## Session Files Do Not Line-Merge

Do not reason about session-file integration as though git's default three-way merge applied to it.
It does not, by design.

- `.gitattributes` marks `.memory-seed/sessions/**` with `-merge`. Every entry shares line-identical
  `topics:`/`related_entries:` scaffolding, so a line-based merge anchors on those shared lines and
  splices one entry's body into another while stranding a YAML fence - silent corruption rather than
  a conflict. The `-merge` attribute makes concurrent edits to the same session file conflict
  **wholesale** instead.
- Consequently `memory-seed session merge-branch` / `memory_session_integrate` (or the lower-level
  `session fuse --apply`) is the **only** correct integration path for a branch carrying session
  entries. Those tools rebuild the file from parsed entry records and reset branch-touched session
  files to base content before fusing, so the `-merge` conflict never has to be hand-resolved.
- Hand-resolving a whole-file session conflict, or picking "ours"/"theirs", drops one side's entries.
  If you are staring at such a conflict, abort and re-integrate through the tool.

**Link sidecars fuse like diagram sidecars, fixed 2026-07-20.** `.memory-seed/sessions/links/**` is in
the `-merge` domain, and the fuse rebuilds every branch-touched session-tree path from parsed records
rather than trusting git's line merge. Link sidecars are now a third recognized kind alongside session
entries and diagram sidecars: a branch-side link sidecar block for a newly authored or branch-accepted
entry fuses through `session merge-branch` / `memory_session_integrate` and survives the merge commit,
same as a diagram sidecar. A defense-in-depth guard also refuses to silently reset any session-tree path
no classifier recognizes, so the *next* unrecognized sidecar kind fails loudly instead of repeating this
bug.

**Still append-only.** Modifying the text of an *existing* (already-on-base) sidecar block on a branch -
same `entry_id`, changed content - is refused before any merge starts, exactly like editing a published
session entry. That is the append-only invariant, not a merge-tool gap. Do stub -> live classification
(`memory-seed link audit` and its sidecar writes) on the trunk, not on a task branch, for that reason.

## Reflection Board v1 collaboration

A declared Reflection Board is temporary coordination for one workstream. The only supported authored
format is `memory-seed/reflection-workstream-ledger` v1 at
`.memory-seed/reflections/active/<workstream_id>/ledger.md`. Planner, implementer, reviewer, and
orchestrator append sequentially; separate workstreams have separate ledgers. There is no participant
fragment writer, reflection fuse, or prototype compatibility reader.

Follow these gates in order:

1. Verify the worktree, task scope, clean committed state, and integration/merge policy. Before creating
   the ledger's base, the maintainer previews `memory-seed reflection trust init` on the resolved
   integration/default branch and explicitly applies it with `--apply`. Only the public anchor is
   committed; the matching private Ed25519 key stays in the Git common directory. Later trust cannot
   retrofit an older ledger base. No key rotation/replacement or recovery command exists.
2. On the owned workstream branch, preview `reflection ledger init`, then apply it. Use the returned
   `workstream_id`; initialization mints its own identity. Seven-day retention is the usable public
   default. Although the schema accepts 14/30, public retention-extension authoring is planned and
   those requests fail without the unavailable admitted host preflight.
3. Use `reflection ledger append <workstream_id>` for conclusion, reasoning, source, and role.
   A planner opens a root with `--relationship no_related_thread --no-related-thread`. Later records
   name `--chain-id` and `--parent`; the current phase owner records its transition. Planner advances
   plan to implement; implementer advances to review; reviewer explicitly selects
   `--to-phase implement` or `--to-phase orchestrate`; orchestrator synthesizes before close.
   Independent validation, where required, cannot be replaced by a role label.
4. Inspect `reflection ledger view <workstream_id>`, `reflection ledger check <workstream_id>`,
   and `reflection board view`. They read trusted committed history and expose malformed candidates.
   Every mutation defaults to preview; inspect its result before `--apply`. For init/append/close,
   echo `head` as `--expected-head` and, for append/close, `pre_ledger_digest` as
   `--expected-ledger-digest`. Apply remeasures authority; stale state requires a fresh judgment.
5. Integrate through the project's existing guarded workflow, preserving the live source ref and exact
   two-parent target/source merge. For local mode, run `reflection ledger rebind <workstream_id>
   --source <source-branch> --reason <reason>` on the integration branch, preview then apply.
   For PR mode, finish all source preparation against the current target, run
   `reflection ledger prepare <workstream_id>` on the source (preview then apply), and only then
   perform the separately authorized PR integration. On the target, preview/apply
   `reflection ledger finalize <workstream_id> --source <source-branch> --reason <reason>`.
   Prepare is CLI-only; rebind/finalize have MCP parity. Reflection performs no network action, push,
   PR creation, or source-ref deletion. Rebind adds exact integration evidence without rewriting records.
6. On the effective integration owner, prepare and commit ordinary session receipts, preview/apply
   `reflection ledger close <workstream_id> --chain-id <chain_id> --receipts <JSON-array>`,
   then finalize the new close-record and closure-outcome receipts in a new ordinary entry. Follow
   `session_logging.md`; `closed_receipts_pending` is unfinished closeout, not expiry eligibility.
7. Follow `end_of_turn.md` for elapsed `reflection ledger expire` preview/apply and verification.
   Defer branch/worktree cleanup until required rebind evidence and receipt closeout are complete.

The live/Seed prepare-commit-msg hooks call the shared admission facade before Memory-Entry stamping.
Manual staged reserved paths, aliases, or invented Reflection trailers are refused. Seeded hooks require
a current package whose interpreter can import the facade; repair the installation if it cannot load.
Do not bypass the hook. Only sanctioned kernel commits, one-time trust bootstrap, and exact integration
carriers are admitted.

Recovery is evidence-led: inspect status and diagnostics, preserve concurrent content, reload view/check,
and preview again. PR finalize claims its single-use handoff after preview validation and before CAS;
a failure after that claim consumes it. Re-preparation requires an eligible final source state; the same
tip cannot be prepared twice, and prepare refuses an already-integrated ledger. No automatic post-merge
recovery exists: escalate that state without deleting the claim or fabricating merge evidence.

Trust assumes an uncompromised host account, clock, and private key. The pure-Python Ed25519 signer is
not constant-time or hardware-backed. A legacy pre-proof close remains readable but non-expirable;
missing immutable-base trust blocks new close. Expiry is not cryptographic erasure: historical and
unreachable Git objects may remain until Git garbage collection.

## MCP Control Surface

When the Memory Seed MCP server is available, use it as the read-oriented coordination surface before
falling back to shell commands:

- `memory_branch_status` replaces the read-only CLI posture check for agents that can call MCP. Use
  it before distinct feature work, before assigning branch/worktree packets, and before explaining
  why a task should move off `main`.
- `memory_worktree_guard` mirrors `memory-seed worktree guard` as a read-only structured pre-write
  check. Use it before file edits when MCP is available; treat `safe_to_write: false` or
  `severity: block` as a blocker until the worker moves to the correct namespace or the user grants
  an explicit root-write override.
- `memory_session_fuse_preview` replaces the dry-run CLI preview for agents that can call MCP. Use it
  before promoting a task branch that may contain branch-local session entries or diagram sidecars.
  Treat `ok: false` or any `issues` as a merge blocker until the orchestrator or user resolves them.
- `memory_session_integrate` applies a branch merge+fuse autonomously — the MCP counterpart to
  `memory-seed session merge-branch`. It runs the fuse gate, performs the `--no-ff` merge, fuses
  branch-local session memory in chronological order, and commits, with no in-progress-merge
  precondition. It fails closed: a non-session conflict aborts the merge and restores a clean tree
  (retry by hand, or let the named conflict owner resolve it), and `integration_mode: pr` is declined
  (that path pushes and opens a PR) with the `memory-seed session integrate --branch <branch>` command
  handed back instead. `memory_session_fuse_preview` above stays the read-only dry-run for inspecting
  the plan first; its returned `merge_checkpoint_command`/`apply_command` remain operator guidance for
  a manually inspected merge applied through `session fuse --apply`.
- A previewed diagram sidecar is valid only when its parent entry already exists on the base/main tree
  or the parent branch entry is accepted for promotion in the same preview. Orphan or malformed
  sidecars must block promotion.

If MCP tools are unavailable, run `memory-seed branch status` and
`memory-seed session merge-branch --branch <branch> --dry-run` directly from the integration tree
and report the same fields: warnings/issues, planned entries, planned sidecars, source removals,
and the command that would perform the merge.

## Dependency Strategy

Worktrees isolate source edits. Local environments isolate runtime state. Shared caches reduce disk
cost. Dependency definition files are orchestrator-owned shared files.

### Dependency Tiers

Every task packet declares a `dependency_tier`:

- `none` — read-only work; no environment setup required.
- `isolated` — normal writing work; each worktree gets its own local environment (e.g. `.venv`,
  `node_modules`), never one live environment shared with another parallel writer.
- `dependency-changing` — the worker may change dependency definitions or lockfiles. Treat this as a
  coordination event: the orchestrator decides whether to merge it first, merge it last, or pause and
  rebase other worker branches before trusting their validation.

### Shared Dependency Files

Dependency definition files and lockfiles are orchestrator-owned shared files, same tier as the
control-plane files below: `pyproject.toml`, `requirements*.txt`, `uv.lock`, `package.json`,
`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`. Workers on `none` or `isolated` tiers must not
edit these files; only a `dependency-changing` worker may, and only within its assigned scope.

### Shared Caches

A read-only shared package/download cache (e.g. pip/uv/npm cache directories) may be shared across
worktrees to reduce disk cost. Never share one live installed environment or virtualenv across
parallel writing worktrees — that reintroduces the mutable-shared-state risk worktrees exist to
prevent.

### Tmux As Optional Control Room

Tmux (or any terminal multiplexer) is an optional operator convenience for watching multiple
worktrees at once. It is not part of the portable contract: Git branch, worktree, task packets,
validation records, and handoff evidence remain the contract regardless of which terminal tooling the
orchestrator uses.

## Conflict Escalation

Workers may resolve conflicts in files they clearly own for the task.

Shared/control-plane conflicts are the Shared / control-plane STOP category in
`risk_signaling.md`: do not let a worker resolve them unless the packet explicitly assigns that
write and names the conflict owner.

Escalate to the orchestrator or human for:

- shared control-plane files such as `AGENTS.md`, `.memory-seed/agent-rules.md`, `.memory-seed/policy.md`, or skill registry files
- dependency definition files and lockfiles (see Dependency Strategy) unless the worker's packet declares `dependency_tier: dependency-changing`
- session or memory files unless the worker was assigned that exact write
- seed templates under `memory_seed/seed/`
- generated artifacts where the source of truth is unclear
- binary files
- conflicts involving user-owned or foreign content
- conflicts where both sides changed behavior, not just nearby formatting

When a conflict is resolved, the handoff must state which side won, why, and what validation was rerun. Repeated mechanical conflicts may use Git's recorded-resolution tooling when the repository owner enables it, but never treat recorded resolution as approval.

## Memory And Session Policy

- For subagent work, the orchestrator owns durable session logging and summarizes worker results.
- Workers should return handoff evidence instead of writing session logs unless the orchestrator explicitly delegates memory updates.
- If a worker branch does write session memory, each new entry must carry `branch: <task-branch>`
  (`memory-seed session append` captures it automatically from git).
  Existing entries are immutable. Branch diagram sidecars may be fused only when the parent entry is
  already on the base/main tree or is accepted for promotion in the same fuse.
- In multi-developer workflows, use per-user session targets when configured so human contributors avoid same-file session conflicts.
- Do not rewrite old session entries to resolve conflicts. Append a new clarification entry when needed.

## Integration Checklist

- Branch is based on the intended integration branch.
- Worker edited only allowed files.
- Forbidden files are untouched or explicitly approved.
- Validation commands ran and results are recorded.
- Merge conflicts are resolved by the right owner.
- Session/memory updates are appended by the orchestrator or the responsible human.
- Final integration branch or PR diff receives a validator pass before merge.

## Output

Return a concise handoff with:

- branch and worktree used
- files changed
- validation run
- conflicts encountered and resolution owner
- risks, follow-ups, or integration blockers
