# Task: support comments in settings files

Operators want to annotate their settings files with comments explaining why values were chosen.
`settings.json` is plain JSON, which does not allow comments.

Decide how `strutil` should support commented settings and implement your choice. Constraints:

- The library must stay stdlib-only (see the runtime policy).
- Existing plain `settings.json` files must keep working unchanged.
- `load_settings()`'s signature and return shape must not break existing callers.

Possible directions the team has floated, without a preference: strip comment lines before JSON
parsing; move to a TOML settings file via `tomllib` with JSON kept as a fallback; or something
better you see that fits the constraints.

`python run_checks.py` must pass when you are done, extended with at least two checks that exercise
a commented settings file.
