# Task: add a slug validator

`strutil` needs a new public function `is_valid_slug(value: str) -> bool` that returns True only for
strings already in canonical slug form (what `slugify` would produce unchanged).

There are two viable implementations and the team has no standing preference — pick whichever you
judge better for this codebase and implement it:

1. Reuse the existing regex machinery in `strutil/text.py` (a full-match pattern).
2. A character-scan loop with explicit rules (no regex).

Requirements:

- Export it from the package like the other helpers.
- Extend `run_checks.py` with at least three checks covering valid and invalid inputs.
- `python run_checks.py` must pass when you are done.
