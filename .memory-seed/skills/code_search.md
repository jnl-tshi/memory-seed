---
memory-system-version: 2.13
tags:
  - memory-seed
  - skill
  - code-search
---

# Code Search Skill

Use this skill when exploring source code, library behavior, symbols, call paths, or repository structure in a software project.

## Procedure

1. Prefer `semble search` for natural-language or symbol queries.
2. Use `semble find-related <file> <line> .` when a known location needs surrounding related code.
3. Use literal search only for exhaustive string confirmation.
4. Read full files only when returned chunks lack enough context.
5. Record important paths in `.memory-seed/index.md` only when they are durable topology.

## Commands

```bash
semble search "authentication flow" .
semble search "getUserById" .
semble find-related src/auth.py 42 .
```

If `semble` is not on `PATH`, use:

```bash
uvx --from "semble[mcp]" semble search "query" .
```

## Output

- Relevant files and symbols.
- Why they matter to the task.
- Any uncertainty that requires full-file inspection.
