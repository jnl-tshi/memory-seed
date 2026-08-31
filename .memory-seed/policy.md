---
memory-system-version: 2.0
tags:
  - memory-seed
  - runtime-policy
  - memory-seed-project
---

# Memory Seed Runtime Policy

## Scope

This file contains behavioral constraints only. Functional runbooks belong in `.memory-seed/skills/`, active state belongs in `.memory-seed/index.md`, and chronological history belongs in `.memory-seed/sessions/`.

## Global Behavior

- Read `AGENTS.md`, `.memory-seed/agent-rules.md`, `.memory-seed/index.md`, and `.memory-seed/policy.md` before changing this repository.
- Apply nearest-runtime discovery for all work.
- Do not preload skills. Load `.memory-seed/skills/*.md` only when the task calls for that runbook.
- Keep root routing files thin and vendor-neutral.
- Keep the memory core plain Markdown and predictable for file-reading agents. (ADR [`adr_markdown_substrate`](decisions/adr_markdown_substrate.md))
- Preserve compatibility for legacy `.AGENTS/` projects in code unless intentionally removing a legacy path. (ADR [`adr_legacy_agents_compat`](decisions/adr_legacy_agents_compat.md))

## Orientation

- Before answering "what state is the project in?", verify the local checkout and newest session
  first. Fetch remotes only when the question depends on remote state and network use is authorized;
  confirm published package state from PyPI when release state matters.
- Never state a current version from a local worktree checkout. A worktree can be pinned to an old commit and will report stale state confidently.

## Merge And Branch Safety

- After every merge, verify the full changeset landed: run `git diff --stat <branch>..HEAD` and confirm it is empty, and explicitly check that sidecar and metadata files are present, not just session-log entries.
- Never `git checkout` a branch while uncommitted edits exist — stash or commit first.
- Prefer `session merge-branch` over a raw `git merge` for branches carrying session entries: it dry-runs the fuse, preserves chronology, and stamps `Memory-Entry:` trailers. A raw line-merge of a session file is what the fuse exists to prevent.
- Land a format change BEFORE any data that uses it, as its own merge. The fuse validates a branch's records with the parser in the CHECKED-OUT tree, not the branch's, so a branch that both adds a format (an ADR event kind, a sidecar field) and writes records in it is unmergeable — the new form is invisible to the old parser and the records read as corrupt rather than as newer. Split it: merge the parser change first (it touches no data, so there is nothing to fuse), then merge the data.

## Safety

- Do not write secrets, tokens, credentials, private keys, or unnecessary personal data into memory files.
- Treat memory files as potentially publishable unless the user explicitly says otherwise.
- Ask before destructive operations, broad rewrites, release actions, or changes that affect published package behavior.
- Preserve user changes and unrelated worktree changes.
- Prefer dry-run, preview, or targeted verification when available.
- Prefer local deterministic behavior over hosted or vendor-specific assumptions.
- Correct a published lifecycle edge (downgrade or remove) through an append-only `retracts:` block in a NEW sidecar block — never by editing the published block in place. `session merge-branch` refuses in-place edits to existing link sidecars (Invariant #2); do not bypass it. Machine-suggested edges (a link swarm) only suggest — the mechanical validator and a human approval gate every write. (ADR [`adr_link_retraction`](decisions/adr_link_retraction.md))
- General precedence rule across sidecar families: a `derived` block may never *implicitly* override a `write-time` block on recency alone — it may only fill a gap. An explicit override requires a human-reviewed `retracts:` naming the block it supersedes. (ADR [`adr_derived_precedence`](decisions/adr_derived_precedence.md))
- Before trusting a subagent's file reads, citations, or "this doesn't exist" claims for this repository, verify `pwd` and `git rev-parse HEAD` against the intended base commit — a pinned or frozen worktree can silently diverge from the live tree.

## File Ownership

- `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` route tools into the shared runtime; `AGENTS.md`'s orientation-chain completion requirement is governed by (ADR [`adr_orientation_completion_gate`](decisions/adr_orientation_completion_gate.md)).
- `.memory-seed/agent-rules.md` owns operating-mode rules.
- `.memory-seed/project-bootstrap.md` owns bootstrap and repair procedures.
- The ratified Constitution declared by the index governs lower control-plane files.
- `.memory-seed/index.md` owns topology, active state, inheritance rules, authority routing, and skill pointers. (ADR [`adr_control_file_authority`](decisions/adr_control_file_authority.md))
- `.memory-seed/policy.md` owns concise executable behavioral constraints; ADRs own their rationale and evolution.
- `.memory-seed/decisions/*.md` owns append-only durable concern decisions and their current accepted heads.
- `.memory-seed/skills/*.md` owns task-specific execution runbooks.
- `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md` owns chronological work history.
- `.memory-seed/archive/` owns archived prior control-plane states.
- `.memory-seed/hooks/*.py` owns lifecycle hook scripts (e.g. `session-log-check.py`, whose logging
  trigger is governed by (ADR [`adr_session_log_trigger_enforcement`](decisions/adr_session_log_trigger_enforcement.md))).
- `memory_seed/seed/` owns reusable files copied by `memory-seed init`.

## Security And Privacy

- Minimize sensitive detail in durable memory.
- Redact account identifiers, private local paths, client names, tokens, credentials, and raw proprietary material unless the user explicitly asks to preserve them.
- Public, production, networked, or user-data projects require explicit security review before release-impacting changes.
- Private local knowledge projects require privacy and backup awareness, not unnecessary production process.
- If risk is unclear, protect secrets, credentials, personal data, and destructive operations by default.

## Python And Release Policy

- Use tests before behavior changes.
- `python -m pytest` from the repo root runs BOTH suites - `tests/` and `memory-trace/tests/` - because `pythonpath = ["memory-trace"]` in `pyproject.toml` makes the Trace package importable. Do not gate on `pytest tests` alone: that is what let three Trace failures sit on `main` from 2026-07-28 until a push finally ran CI's Verify job.
- To reproduce CI's Trace step exactly: `python -m unittest discover -s memory-trace/tests -p "test_*.py"`.
- Read the suite's own exit code, never a pipeline's - `pytest ... | tail` reports tail's status, which has hidden a failing suite behind a chained `&&`.
- Keep CLI output explicit about what writes and what does not write.
- Publishing should be triggered by GitHub Release creation, not direct workflow dispatch. (ADR [`adr_release_topology`](decisions/adr_release_topology.md))
- Package version and git tag must match for release work.
- Archive prior control-plane snapshots under `.memory-seed/archive/<version>/` before replacing reusable versioned artifacts. (ADR [`adr_archive_before_replace`](decisions/adr_archive_before_replace.md))

## Sub-Projects

- A nested `.memory-seed/` runtime scopes work under its containing folder. (ADR [`adr_subproject_scoping`](decisions/adr_subproject_scoping.md))
- Sub-project active state is local by default.
- Sub-project skills inherit parent skills by default and use local skill files only for overrides or genuinely local runbooks.
- Parent policy is inherited by default unless a sub-project index explicitly disables it.
- Do not read parent active state unless the sub-project index explicitly links to it.

## End Of Turn

- Append a concise note to the active grouped session target (`.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md` by default) **before the current turn ends** — not deferred, not batched.
- Do not fabricate decision rationale; mark rationale as inferred or not recorded when it is not explicitly known.
- Update `.memory-seed/index.md` only when topology, active state, inheritance, or skill pointers changed.
- Update `.memory-seed/policy.md` only when durable behavioral constraints changed.
- Update `.memory-seed/skills/*.md` only when a reusable runbook changed.
- Run the smallest relevant verification before reporting completion.
