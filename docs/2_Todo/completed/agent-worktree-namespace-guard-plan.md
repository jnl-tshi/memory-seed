# Agent Worktree Namespace Guard Plan

Status: Implemented 2026-07-13
Priority: P1 - immediate multi-agent safety hardening
Source: 2026-07-12 user direction after reviewing how to keep Codex out of Claude worktrees and Claude out of Codex worktrees.
Scope: Add vendor-neutral guardrails so writing agents work from their own namespace under an agent-owned worktree folder, while root checkout inspection and integration remain possible by explicit policy.
Non-goals: Do not move, rename, delete, or repair existing worktrees automatically; do not build a hosted orchestrator; do not spawn agents; do not rewrite existing session entries; do not add a durable `worktree:` session field.
Dependencies: `.memory-seed/skills/agent_collaboration.md`, `.memory-seed/skills/risk_signaling.md`, the `branch:` session field, `memory-seed branch status`, branch-session fuse / `session merge-branch`, agent-selection config, and seed/live skill parity.
Acceptance criteria:
- `memory-seed worktree guard --agent codex --write-intent` passes from `.codex/worktrees/<task>` and fails from `.claude/worktrees/<task>`.
- `memory-seed worktree guard --agent claude --write-intent` passes from `.claude/worktrees/<task>` and fails from `.codex/worktrees/<task>`.
- Root checkout read-only inspection passes; root write intent fails or requires an explicit `--allow-root-write` override.
- Unknown or unmanaged worktree paths produce a clear warning with the expected namespace and a suggested next action.
- The same guard result is available through a read-only MCP tool so LLMs do not have to scrape terminal prose.
- `agent_collaboration.md` and its seed twin require the guard before file edits in branch/worktree workflows.
- Tests cover Windows path normalization, paths with spaces, case-insensitive namespace matching, root checkout policy, foreign namespace blocking, JSON output, and MCP schema behavior.

## Problem

The repository now supports parallel agent work through branches, worktrees, branch-local session
entries, fuse/merge promotion, and visible branch topology. That solves branch history and session
integration, but it does not yet prevent a writing agent from starting inside another agent's
worktree namespace.

The practical risk is simple:

- Codex can accidentally work inside `.claude/worktrees/...`.
- Claude can accidentally work inside `.codex/worktrees/...`.
- The root checkout can be used for feature edits when it should usually be reserved for inspection,
  integration, and explicit mainline cleanup.
- A branch/worktree may be clean and technically valid while still belonging to the wrong agent
  namespace.

This is a coordination issue, not a Git capability issue. Git worktrees isolate file state, but only
the surrounding Memory Seed workflow can say which agent is supposed to write where.

## Decision

Add an explicit agent-worktree namespace guard as the next layer on top of the existing branch and
session-fuse workflow.

The rule should be:

- Codex writes in `.codex/worktrees/<task>` by default.
- Claude writes in `.claude/worktrees/<task>` by default.
- Gemini writes in `.gemini/worktrees/<task>` by default when it is used as a writing agent.
- Cursor writes in `.cursor/worktrees/<task>` by default when it is used as a writing agent.
- Other configured agents get an explicit namespace in project config before write work starts.
- The root checkout is allowed for read-only inspection, mainline integration, and user-approved
  cleanup, but routine feature edits should happen in an agent-owned task worktree.

This preserves the existing durable-memory decision that session entries may carry a `branch:` field
but should not carry a `worktree:` field. A worktree path is local machine state. It belongs in
handoff evidence and guard output, not in long-lived session schema.

## Proposed CLI Surface

Add a new command group:

```text
memory-seed worktree guard --agent <agent> [--write-intent] [--allow-root-write] [--json]
memory-seed worktree status [--agent <agent>] [--json]
```

`guard` is the pre-write check. It should classify the current path and return a non-zero status
when a writing agent is in a foreign namespace or an unapproved root checkout.

`status` is the human/LLM-friendly readout. It can show the current checkout role, namespace owner,
branch, HEAD, dirty state, expected namespace, and suggested next action.

Expected classifications:

| Classification | Meaning | Write intent behavior |
| --- | --- | --- |
| `owned-worktree` | Current path is under the calling agent's namespace. | Pass. |
| `foreign-worktree` | Current path is under another agent's namespace. | Fail closed. |
| `root-checkout` | Current path is the repository root checkout. | Pass for read-only, fail unless `--allow-root-write`. |
| `unmanaged-worktree` | Current path is a Git worktree outside a configured namespace. | Warn or fail for write intent, depending on project policy. |
| `not-a-worktree` | Current path is not inside the target repository's Git worktree set. | Fail for write intent. |

The guard should never create branches, create worktrees, delete anything, or switch branches. It
only reports whether the current location is appropriate for the requested agent and intent.

## Proposed MCP Surface

Add a read-only MCP tool:

```text
memory_worktree_guard(agent_type, write_intent=false, cwd=null)
```

Return structured fields:

```yaml
ok: true|false
severity: ok|warning|block
agent_type: codex
classification: owned-worktree|foreign-worktree|root-checkout|unmanaged-worktree|not-a-worktree
safe_to_write: true|false
current_branch: <branch-or-null>
head: <sha-or-null>
worktree_path: <path>
repo_root: <path>
expected_namespace: .codex/worktrees
actual_namespace_owner: codex|claude|gemini|cursor|null
recommended_next_action: <short action>
```

This mirrors the existing principle that MCP should help agents reason safely without giving it
write authority for merges, fuses, branch creation, or deletion.

## Project Configuration

Defaults can be built in for known agents, with optional project overrides in
`.memory-seed/project.yaml`:

```yaml
worktrees:
  root_write_policy: explicit-override
  unmanaged_write_policy: warn
  namespaces:
    codex: .codex/worktrees
    claude: .claude/worktrees
    gemini: .gemini/worktrees
    cursor: .cursor/worktrees
```

If the config block is absent, Memory Seed should use the known-agent defaults. Existing projects
must not be broken by the absence of this block.

## Control-Plane And Skill Updates

Update the live and seed collaboration guidance:

- Add the guard to `agent_collaboration.md` under Branch And Worktree Defaults and Worker Identity
  Gate.
- Add `agent_type`, `worktree_namespace`, and a guard preflight line to the Task Packet example.
- Keep `agent-rules.md` short: it should only point agents to `agent_collaboration.md` before
  branch/worktree edits.
- Cross-reference `risk_signaling.md`: writing from a foreign namespace is a shared/control-plane
  STOP-style coordination hazard unless the user explicitly overrides it.
- Add `.codex/worktrees/`, `.claude/worktrees/`, `.gemini/worktrees/`, and `.cursor/worktrees/` to
  `.gitignore` without ignoring the tracked agent configuration files themselves.

The guard belongs in `agent_collaboration.md`, not a new skill. It extends the existing branch,
worktree, task-packet, and merge-handoff workflow.

## Implementation Order

1. Add a pure path classifier in `memory_seed/core.py`.
2. Add `memory-seed worktree guard` and `memory-seed worktree status`.
3. Extend `memory-seed branch status` to include the namespace posture or point to the new command.
4. Add the read-only MCP wrapper.
5. Update live and seed `agent_collaboration.md`, plus minimal `agent-rules.md` pointer text if
   needed.
6. Update docs and `.gitignore`.
7. Add tests for classifier, CLI, MCP, and seed/live parity.

## Open Questions For Implementation

- Should `unmanaged_write_policy` default to `warn` or `block`? Recommendation: `warn` for legacy
  compatibility, with `block` available for team repositories.
- Should `worktree status` suggest exact `git worktree add` commands? Recommendation: include
  suggested commands in text output only, but do not execute them.
- Should root write override require a CLI flag only, or also a durable project config toggle?
  Recommendation: require `--allow-root-write` per invocation so root writes stay conscious.
- How should non-Codex agents pass identity? Recommendation: explicit `--agent`/MCP argument first,
  optional environment detection later.

## Done Means

The next time a Codex, Claude, Gemini, Cursor, or configured third-party agent starts write work, it
can call one guard and get an unambiguous answer: stay here, move to your own worktree, or ask the
user for an explicit root-write override.
