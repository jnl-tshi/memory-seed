---
tags:
  - memory-seed
  - runtime-index
---

# Runtime Index

## Purpose

`strutil` is a small Python utility library: string helpers plus a JSON-backed settings loader.
This runtime is the project's local memory.

## Runtime Boundary

- Active runtime: this directory's `.memory-seed/`.
- This project is standalone. It has no parent runtime and inherits nothing.

## Inheritance

- No parent runtime. Policy, skills, active state, and sessions are all local.

## Active State

- Project type: small Python utility library.
- Current priority: incoming maintenance and enhancement tasks, handled one at a time.
- No open risks recorded.

## Topology

- `strutil/` — the package (`text.py` string helpers, `config.py` settings loader).
- `settings.json` — runtime settings consumed by `strutil.config`.
- `run_checks.py` — plain-assert check script; run with `python run_checks.py`.

## Session Memory

- Session files live under `.memory-seed/sessions/`.
