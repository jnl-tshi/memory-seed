---
memory-system-version: 2.16
tags:
  - memory-seed
  - skill
  - history-retrieval
---

# History Retrieval And Conflict Resolution Skill

Use this skill when prior decisions, reason, unresolved risks, architecture, policy, bootstrap behavior, release history, or "why was this done" matters.

## Recency vs. Topical Retrieval

Pick the retrieval method by question type. They are not interchangeable.

- Current state / "what is the latest": read the newest dated `.memory-seed/sessions/*.md` files directly by filename date, newest first. Do not use `memory_search` for latest-state questions because semantic and lexical ranking optimize for topical similarity, not recency.
- Topical / "why was X decided" / "what do we know about Y": use `memory_search`, then fetch consequential results with `memory_get_chunk`.

## When To Search

Call `memory_search` before relying on the visible conversation alone when the task asks about or depends on:

- a past design decision, architecture choice, policy change, bootstrap choice, release, migration, or unresolved risk
- why a file, workflow, or memory structure behaves a certain way
- whether a current request conflicts with older session history
- sub-project boundaries, inherited policy, or prior agent handoff context

Skip MCP history lookup for small, obvious edits where current source files and the active `index.md` / `policy.md` are enough.

## Tool Mechanics

The MCP server exposes two tools:

- `memory_search`: ranks session-memory entries or sections.
- `memory_get_chunk`: fetches the full text for one returned `chunk_id`.

Default search payload:

```json
{
  "query": "short natural-language description of what you need to know",
  "cwd": ".",
  "top_k": 5,
  "granularity": "entry"
}
```

Use `cwd` as the project or sub-project path you are operating in. The runtime resolver uses the nearest `.memory-seed/` directory from that path.

Use `granularity: "entry"` by default. It returns one coherent chunk for each `##` session entry, and `chunk_id` is normally the entry YAML `entry_id`, such as `ms-db2d715c`.

Use `granularity: "section"` only when entries are long, multi-topic, or the task needs narrower targeting. Section chunk ids append a heading path to the parent entry id, such as `ms-db2d715c#decisions/d1-use-draft-for-compact-decision-records`.

Useful optional search fields:

```json
{
  "semantic_enabled": true,
  "recency_enabled": true,
  "recency_floor": 0.15
}
```

Recency is anchored to the current date read from the system clock at call time. There is no date-override field; the tool never trusts a caller-supplied "today".

Search results include `chunk_id`, `entry_id`, `source`, `line_range`, `heading_path`, `excerpt`, matched fields, score fields, entry metadata, and `granularity`. Treat excerpts as previews only.

Fetch any result that may affect implementation, policy, bootstrap behavior, release behavior, or memory structure:

```json
{
  "chunk_id": "ms-db2d715c",
  "cwd": "."
}
```

Use the fetched chunk text, not just the excerpt, when making or evaluating a consequential decision.

## Fallback

If MCP tools are unavailable, read recent and relevant `.memory-seed/sessions/YYYY-MM-DD.md` and `.memory-seed/sessions/YYYY-MM-DD/<user>.md` files directly. Start with the last two session documents, then search older dated files by keyword if needed.

## Authority And Conflict Resolution

Current files are the active authority: `.memory-seed/index.md`, `.memory-seed/policy.md`, active `.memory-seed/skills/*.md`, and source/config files for implementation truth. Session history is evidence and reason, not automatic authority.

When history conflicts with current authority files, resolve by timeline only when all clear supersession criteria are met:

- the superseding source is a newer dated session entry or current authority file
- it states an explicit decision boundary
- it names the affected files, behavior, policy, or design area
- no later reversal or unresolved disagreement is found

If the conflict remains ambiguous or unresolved, ask the user before changing durable design, policy, bootstrap behavior, memory structure, release behavior, or similarly consequential workflow.
