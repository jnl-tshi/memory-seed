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
- Keep the memory core plain Markdown and predictable for file-reading agents.
- Preserve compatibility for legacy `.AGENTS/` projects in code unless intentionally removing a legacy path.

## Orientation

- Before answering "what state is the project in?", verify against live sources, not worktree snapshots: run `git fetch --all --prune`, check `git log --oneline -5 origin/main`, and confirm the published version from the PyPI JSON API (`https://pypi.org/pypi/memory-seed/json`; `pip index versions memory-seed` is experimental and often unavailable).
- Never state a current version from a local worktree checkout. A worktree can be pinned to an old commit and will report stale state confidently.

## Merge And Branch Safety

- After every merge, verify the full changeset landed: run `git diff --stat <branch>..HEAD` and confirm it is empty, and explicitly check that sidecar and metadata files are present, not just session-log entries.
- Never `git checkout` a branch while uncommitted edits exist — stash or commit first.
- Prefer `session merge-branch` over a raw `git merge` for branches carrying session entries: it dry-runs the fuse, preserves chronology, and stamps `Memory-Entry:` trailers. A raw line-merge of a session file is what the fuse exists to prevent.

## Safety

- Do not write secrets, tokens, credentials, private keys, or unnecessary personal data into memory files.
- Treat memory files as potentially publishable unless the user explicitly says otherwise.
- Ask before destructive operations, broad rewrites, release actions, or changes that affect published package behavior.
- Preserve user changes and unrelated worktree changes.
- Prefer dry-run, preview, or targeted verification when available.
- Prefer local deterministic behavior over hosted or vendor-specific assumptions.
- Correct a published lifecycle edge (downgrade or remove) through an append-only `retracts:` block in a NEW sidecar block — never by editing the published block in place. `session merge-branch` refuses in-place edits to existing link sidecars (Invariant #2); do not bypass it. Machine-suggested edges (a link swarm) only suggest — the mechanical validator and a human approval gate every write.
- General precedence rule across sidecar families (Constitution v1.6, 2026-07-26): a `derived` block may never *implicitly* override a `write-time` block on recency alone — it may only fill a gap. An explicit override requires a human-reviewed `retracts:` naming the block it supersedes. Provenance is recorded as **first-hand vs reconstructed** (who observed the fact directly), not human-vs-machine — every YAML topic/edge in this corpus is agent-chosen, so that axis was never the real distinction.
- Before trusting a subagent's file reads, citations, or "this doesn't exist" claims for this repository, verify `pwd` and `git rev-parse HEAD` against the intended base commit — a pinned or frozen worktree can silently diverge from the live tree.

## File Ownership

- `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` route tools into the shared runtime.
- `.memory-seed/agent-rules.md` owns operating-mode rules.
- `.memory-seed/project-bootstrap.md` owns bootstrap and repair procedures.
- `.memory-seed/index.md` owns topology, active state, inheritance rules, and skill pointers.
- `.memory-seed/policy.md` owns behavioral constraints.
- `.memory-seed/skills/*.md` owns task-specific execution runbooks.
- `.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md` owns chronological work history.
- `.memory-seed/archive/` owns archived prior control-plane states.
- `.memory-seed/hooks/*.py` owns lifecycle hook scripts (e.g. `session-log-check.py`).
- `memory_seed/seed/` owns reusable files copied by `memory-seed init`.

## Security And Privacy

- Minimize sensitive detail in durable memory.
- Redact account identifiers, private local paths, client names, tokens, credentials, and raw proprietary material unless the user explicitly asks to preserve them.
- Public, production, networked, or user-data projects require explicit security review before release-impacting changes.
- Private local knowledge projects require privacy and backup awareness, not unnecessary production process.
- If risk is unclear, protect secrets, credentials, personal data, and destructive operations by default.

## Python And Release Policy

- Use tests before behavior changes.
- Keep CLI output explicit about what writes and what does not write.
- Publishing should be triggered by GitHub Release creation, not direct workflow dispatch.
- Package version and git tag must match for release work.
- Archive prior control-plane snapshots under `.memory-seed/archive/<version>/` before replacing reusable versioned artifacts.

## Sub-Projects

- A nested `.memory-seed/` runtime scopes work under its containing folder.
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
