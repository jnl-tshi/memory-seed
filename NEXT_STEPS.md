# Next Steps

These items need user judgement, account access, or real-client validation.

## MCP Client Validation

- Register Memory Seed in Claude Code or another MCP-capable client:

```powershell
claude mcp add memory-seed -s user -- uvx --from memory-seed memory-seed-mcp --stdio
```

- Ask the agent a question that should require historical project memory and confirm it calls `memory_search` before answering.
- Record any client-specific setup differences so the README can include confirmed examples.

## Launch Assets

- Capture a real terminal screenshot or short GIF showing `memory-seed init`, `memory-seed-mcp-validate`, and an agent memory lookup.
- Decide whether to publish a launch note focused on solo developers, teams standardizing agent memory, or both.

## Ranking Experiments

- Keep ranking behavior stable on `main`.
- Run ranking experiments on a separate branch and merge only if fixture tests show a clear improvement without degrading current text-ranking behavior.

## Optional Semantic Dependency

- Decide whether to add an optional package extra such as `memory-seed[semantic]` for Model2Vec-backed embeddings.
- Keep the default CLI and MCP path dependency-light unless the optional path shows clear value.

## Community Feedback

- Watch issue reports for agent compatibility gaps across Codex, Claude Code, Gemini CLI, and other MCP clients.
- Use the issue templates to separate bugs, feature requests, compatibility reports, and memory workflow improvements.
