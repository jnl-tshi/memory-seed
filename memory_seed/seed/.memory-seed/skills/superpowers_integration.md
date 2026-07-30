---
memory-system-version: 2.19
tags:
  - memory-seed
  - skill
  - superpowers-integration
  - agent-collaboration
---

# Optional Superpowers Integration

Use this optional skill when a task may delegate independent read-only investigation or approved,
multi-task same-session implementation to the official Superpowers workflows.

## Boundary

Memory Seed remains authoritative for project memory, worktree identity, task branches, risk and consent,
integration mode, session fusion, durable handoff, and cleanup. Superpowers is a disposable execution
layer. It must never become required for the Memory Seed core, bootstrap, doctor, session storage, or
retrieval to work.

Only delegate to an active client exposure of the official Superpowers skills:

- `dispatching-parallel-agents` for independent **read-only** diagnosis;
- `subagent-driven-development` (SDD) for an approved multi-task implementation plan.

The supported release range is `>=6.2.0,<7.0.0`. Do not infer availability or version from a cache folder,
a manifest left by another client, or a globally installed executable. The active client must expose the
skill, and the orchestrator records the observed release in the Task Packet. A major-version change is
blocked until the interoperability baseline is rerun.

If either condition fails, state the named fallback and use Memory Seed's normal direct, sequential, or
Fan-Out workflow. Do not silently skip the work and do not download, update, or install dependencies as
part of task dispatch.

## Route

```text
read-only + independent known domains
    -> Superpowers parallel dispatch

approved multi-task plan + same-session execution + verified boundary
    -> Superpowers SDD

writing + separable file ownership
    -> Memory Seed Fan-Out

unknown root cause, coupled writes, shared control-plane, or unresolved architecture
    -> sequential exploration or planning
```

Do not use SDD for a mechanical edit, one small task, exploratory debugging, or work dominated by shared
control-plane files.

## Mandatory Memory Seed Safety Envelope

Before any delegated worker or reviewer acts, the orchestrator supplies a bounded packet containing:

```yaml
persona: "<one domain persona or none>"
context_load: "packet"
base_sha: "<verified commit>"
working_branch: "<Memory Seed task branch>"
expected_pwd: "<owned worktree path>"
preflight:
  - "memory-seed worktree guard --agent <agent_type> --write-intent"
  - "git rev-parse HEAD"
allowed_files: []
forbidden_files: []
baseline_validation: []
baseline_result: "pass|known-failure|not-run"
superpowers_release: ">=6.2.0,<7.0.0 observed: <actual release>"
```

Every delegated worker reports the preflight and verifies `base_sha` before touching files. `persona` and
`context_load` preserve the Worker Context Contract; they do not require a worker to reload the whole
project. Superpowers owns its task brief, task status, and review loop inside this envelope.

## Read-Only Parallel Dispatch

1. Establish that domains are independent and contain no writes, shared mutable state, or unresolved
   common cause.
2. Give one agent one domain, evidence requirements, expected output, and the intended base.
3. Require a tree/base check before trusting a citation.
4. Reconcile results in Memory Seed, then decide whether further work is sequential, Fan-Out, or SDD.

No worker receives write permission solely because the dispatcher is available.

## SDD Handoff

Before invoking SDD:

1. Confirm an approved implementation plan with multiple tasks requiring judgment.
2. Verify the Memory Seed owned session worktree, task branch, base SHA, and smallest relevant baseline.
3. Confirm `.superpowers/sdd/` is git-ignored. It is plan-scoped scratch, not a second Git worktree.
   Do not stage it, copy it into `.memory-seed/`, or treat it as durable project memory.
4. Attach the safety envelope and any conflict-owner/file-boundary instructions to every dispatch.
5. Invoke SDD. Let its scoped task review and finite circuit breaker run; do not layer Memory Seed's
   two-iteration Fan-Out reviewer on top of it.

At SDD completion, stop before `finishing-a-development-branch`. Return control to Memory Seed with:

```yaml
plan: "<canonical plan path>"
completed_ranges: []
final_review: "approved|approved-with-findings|blocked"
deferred_findings: []
residual_risks: []
```

The orchestrator verifies this receipt against Git, appends the durable session record, then follows the
Memory Seed Branch Finish Contract. Under `merge_trigger: manual`, branch landing remains held for a live
user go-ahead.

## Non-Negotiable Exclusions

- Do not use Superpowers `using-git-worktrees` to replace Memory Seed worktree ownership.
- Do not use Superpowers `finishing-a-development-branch` to merge, clean up, delete branches, or bypass
  session fusion.
- Do not make `.superpowers/` artifacts authoritative, tracked, or required for later retrieval.
- Do not replace Memory Seed's current direct workflow when the optional capability is unavailable.
