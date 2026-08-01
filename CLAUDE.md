---
memory-system-version: 2.19
tags:
  - agent-entry
  - ai-memory
---

# Claude Instructions

The canonical agent instructions for this repository are in `AGENTS.md`.

Before planning, editing, reviewing, or running commands:

1. Open `AGENTS.md`.
2. Follow its nearest `.memory-seed/` runtime discovery and read order.
3. If tool-specific behavior is needed, adapt only the tooling, not the policy.

Do not treat this file as a replacement for `AGENTS.md`.

## Working Style

### Response Length

Keep individual assistant turns short. For multi-report or multi-artifact work, write each artifact
directly to a file with the Write tool and return only a one-line confirmation — never stream long
report bodies into the chat.

## Orientation

Before answering "what state is the project in?", verify against live sources, not worktree snapshots:
run `git fetch --all --prune`, check `git log --oneline -5 origin/main`, and confirm the published
version with `pip index versions memory-seed` (or the PyPI JSON API). Never state a current version
from a local worktree checkout.

## Merge & Branch Safety

After every merge, verify the full changeset landed: run `git diff --stat <branch>..HEAD` and confirm
it is empty, and explicitly check that sidecar/metadata files (not just session-log entries) are
present. Never `git checkout` a branch while uncommitted edits exist — stash or commit first.
