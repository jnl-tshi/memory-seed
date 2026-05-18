# HTML Dashboard Waste

This file records the discarded HTML/dashboard direction for review before removal from the repository.

## Removed From Live Implementation

- `memory-seed dashboard` CLI command.
- `generate_dashboard` core function.
- Dashboard-specific constants and result type.
- HTML rendering helpers that generated `.AGENTS/dashboard/index.html`.
- Dashboard tests for generation, dry-run behavior, and seed-file exclusion.
- README references to the dashboard command.

## Reason

The user clarified that Memory Seed should not pursue an HTML frontend/dashboard because it clutters the project's purpose. Future work should stay Markdown-first and optimize orchestration around local memory files.

## Replacement Direction

- Explore Semble MCP/design MCP for projects using Semble when it improves token efficiency.
- Optimize around Markdown memory files rather than function names or source-symbol indexes.
- Consider a future CLI compact trigger that consolidates session facts into durable facts in `context.md`, `index.md`, and `style.md`.
