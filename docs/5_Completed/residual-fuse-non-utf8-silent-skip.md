> Status: COMPLETED 2026-07-13. `_git_show_text` now distinguishes missing blobs from UTF-8
> decode failures, and `session fuse` blocks branch-delta session/diagram files with an explicit
> `could not decode <path> as UTF-8` issue instead of silently omitting them. Base-side decode
> failures remain non-blocking for already-present/parent lookup degradation.

# Residual: `session fuse` silently skips a non-UTF-8 branch file

**Source:** review residual from the session-fuse encoding/scoping fix (session entry `mse_azn6bejpd9xpmh3f`, merge commit `c522379`, 2026-07-10). Flagged by both the advisor and the independent review subagent; consciously deferred as out of scope for that change.
**Severity:** low. Guarded by the repo's UTF-8 write policy (`write_text_file` always writes UTF-8) and separately surfaced by `memory-seed encoding check` / `doctor`.

## Problem

`_git_show_text` (`memory_seed/core.py`) now decodes git output as strict UTF-8 and catches `UnicodeDecodeError`, returning `None` on failure. Its callers `_entry_records_from_ref` / `_sidecar_records_from_ref` treat `None` as "unreadable" and `continue` **without appending an issue**:

```python
text = _git_show_text(root, ref, rel_path)
if text is None:
    continue
```

So a genuinely non-UTF-8 branch session/diagram file is silently dropped from the fuse plan, and `session fuse` reports success while omitting that entry. For a tool whose whole job is careful validated promotion, a dropped branch entry being invisible is mildly against its ethos.

This is the pre-existing "unreadable → skip" behavior (the `None`-on-`OSError`/missing-file path predates the encoding fix); the fix merely added `UnicodeDecodeError` to the same silent bucket.

## Why it was deferred

Surfacing the decode failure as a fuse *issue* cleanly requires distinguishing "file absent at ref" (`git show` returncode ≠ 0 → `None`) from "file present but undecodable" (`UnicodeDecodeError` → `None`) inside `_git_show_text`, then threading that signal up through helpers that are shared by **both** the base-side and branch-side enumeration (base-side decode failures should not necessarily block). That is more surface than the encoding/scoping fix warranted.

## Proposed fix (when picked up)

- Give `_git_show_text` a way to distinguish decode-failure from missing-file (e.g. a sentinel/enum or a second return value).
- In `session_fuse`, when a **branch-delta** file (one of `changed_paths`) fails to decode, append an explicit issue (`"could not decode <path> as UTF-8"`) so the fuse blocks rather than silently omitting an entry. Base-side decode failures can stay non-blocking (already-present/parent lookups degrade gracefully).
- Add a regression test: a branch session file with invalid UTF-8 bytes → fuse blocks with a decode issue, not a silent success.

## References

- `memory_seed/core.py`: `_git_show_text`, `_entry_records_from_ref`, `_sidecar_records_from_ref`, `session_fuse`.
- Session log: `.memory-seed/sessions/2026-07/2026-07-10.md`, entry `mse_azn6bejpd9xpmh3f` ("Known residual").
