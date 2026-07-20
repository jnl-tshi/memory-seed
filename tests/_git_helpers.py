"""Shared git subprocess helper for tests that spin up real repos.

One implementation for the actual subprocess call. The four test files that used to hand-roll
this (test_git_hooks.py, test_mcp_session_integrate.py, test_worktree_gc.py,
test_session_fuse_and_merge.py) disagreed on `check` (raise vs. inspect returncode) and whether
to bound the call with a `timeout` - real behavioral differences, not incidental drift. Each
caller keeps its own historical default by passing it explicitly, so sharing this implementation
changes no existing test's behavior. See docs/2_Todo/test-suite-protection-value-audit.md Phase 2b.
"""

import subprocess


def run_git(cwd, *args, check=False, timeout=None):
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=check,
        timeout=timeout,
    )
