---
memory-system-version: 2.22
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

This section is Claude-specific because it governs assistant turn shape. Vendor-neutral constraints —
**Orientation** (verify state against live sources, never a worktree snapshot) and **Merge And Branch
Safety** (prove the changeset landed; never check out over uncommitted edits) — live in
`.memory-seed/policy.md`, which every agent reads and which `update` never replaces.
