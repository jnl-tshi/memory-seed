---
tags:
  - memory-seed
  - runtime-policy
---

# Runtime Policy

## Scope

Behavioral constraints only.

## Global Behavior

- Keep changes minimal and scoped to the task at hand.
- Preserve the existing public function signatures in `strutil/` unless the task requires changing them.
- Run `python run_checks.py` before treating a change as complete.

## Safety

- Do not write secrets or credentials into any file.
- Do not add third-party dependencies; the library is stdlib-only by design.
- Prefer targeted verification over broad rewrites.
