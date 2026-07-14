"""Tests for the on-device worktree switcher.

The UI can re-point the Trail at any git worktree of the repo. These tests run
against a non-git temp corpus, so git worktree enumeration returns nothing and
the service falls back to exposing just the launch checkout - which is exactly
the contract the frontend relies on (there is always at least one entry, the
default). Path validation (only git-reported worktrees are served) is covered
by the unknown-path 404.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_trace.service import create_app, list_worktrees


def _entry(title, entry_id, body, *, agent="codex", topics=None):
    lines = [
        f"## {title}",
        "",
        "```yaml",
        f"entry_id: {entry_id}",
        "user_initials: JN",
        f"agent_type: {agent}",
        "project_path: .",
        "subproject_path: null",
    ]
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {topic}" for topic in topics)
    lines += ["```", "", body, ""]
    return "\n".join(lines)


class WorktreeSwitchingTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="memory-seed-worktree-test-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="memory-seed-worktree-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        sessions = self.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            + _entry("2026-06-01 09:00 - Bootstrap", "mse_boot", "Built #cache support.", topics=["cache"]),
            encoding="utf-8",
        )
        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            self.app = create_app(self.cwd, rebuild_cache=True)

    def client(self):
        from fastapi.testclient import TestClient

        return TestClient(self.app)

    def test_list_worktrees_returns_empty_outside_a_git_repo(self):
        # The temp corpus is not a git repo, so enumeration returns nothing and
        # the endpoint falls back to the single launch checkout.
        self.assertEqual(list_worktrees(self.cwd), [])

    def test_worktrees_endpoint_always_exposes_the_launch_checkout_as_default(self):
        payload = self.client().get("/api/worktrees").json()
        self.assertEqual(len(payload["worktrees"]), 1)
        only = payload["worktrees"][0]
        self.assertTrue(only["is_default"])
        self.assertTrue(only["is_primary"])
        self.assertEqual(Path(only["id"]).resolve(), self.cwd.resolve())
        self.assertEqual(Path(payload["default"]).resolve(), self.cwd.resolve())

    def test_default_and_launch_path_worktree_serve_identical_data(self):
        client = self.client()
        default = client.get("/api/graph", params={"granularity": "entry"}).json()
        explicit = client.get("/api/graph", params={"granularity": "entry", "worktree": str(self.cwd)}).json()
        self.assertEqual(default["nodes"], explicit["nodes"])

    def test_unknown_worktree_path_is_rejected(self):
        client = self.client()
        bogus = str(self.cwd / "not" / "a" / "worktree")
        for path in ("/api/graph", "/api/runtime", "/api/facets"):
            self.assertEqual(client.get(path, params={"worktree": bogus}).status_code, 404, path)

    def test_legacy_endpoints_ignore_absent_worktree_param(self):
        client = self.client()
        for path in ("/api/runtime", "/api/facets", "/api/graph", "/api/search", "/api/timeline"):
            self.assertEqual(client.get(path).status_code, 200, path)


if __name__ == "__main__":
    unittest.main()
