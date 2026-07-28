"""Tests for browsing to and opening an external project from within Trace.

Pointing Trace at a folder is a two-step flow: /api/v1/browse lets the client
walk the server's filesystem to find a candidate (a cheap "does it have a
.memory-seed/ at all" hint only), and /api/v1/projects is the actual gate -
it runs the real `doctor()` check and only registers the folder as a
switchable worktree entry if it is correctly initialised. These tests run
against a non-git temp corpus, matching test_worktree_switching.py's setup.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_seed.core import init_project
from memory_trace.service import create_app


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


class ProjectOpenTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="memory-seed-open-test-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="memory-seed-open-cache-"))
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

    def make_dir(self, *parts):
        path = self.cwd.parent / "-".join(parts)
        path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def make_valid_project(self, *parts):
        # init_project() alone leaves doctor() failing: index.md/policy.md are
        # BOOTSTRAP_GENERATED_FILES, authored during a project's first real
        # bootstrap rather than copied by init - see doctor()'s bootstrap_missing
        # check in memory_seed/core.py. Placeholder content is enough to make
        # this a correctly-initialised project for doctor()'s purposes, which is
        # all validate_project_init() itself checks.
        path = self.make_dir(*parts)
        init_project(cwd=path)
        (path / ".memory-seed" / "index.md").write_text("# Index\n", encoding="utf-8")
        (path / ".memory-seed" / "policy.md").write_text("# Policy\n", encoding="utf-8")
        return path

    # --- browse -------------------------------------------------------

    def test_browse_flags_which_subdirectories_have_a_memory_seed(self):
        base = self.make_dir("browse-base")
        (base / "with-seed" / ".memory-seed").mkdir(parents=True)
        (base / "without-seed").mkdir()
        (base / ".hidden").mkdir()

        payload = self.client().get("/api/v1/browse", params={"path": str(base)}).json()

        names = {entry["name"]: entry["has_memory_seed"] for entry in payload["entries"]}
        self.assertEqual(names, {"with-seed": True, "without-seed": False})
        self.assertNotIn(".hidden", names)
        self.assertEqual(Path(payload["path"]).resolve(), base.resolve())
        self.assertEqual(Path(payload["parent"]).resolve(), base.parent.resolve())

    def test_browse_defaults_to_home_when_no_path_given(self):
        payload = self.client().get("/api/v1/browse").json()
        self.assertEqual(Path(payload["path"]).resolve(), Path.home().resolve())

    def test_browse_rejects_a_path_that_is_not_a_directory(self):
        not_a_dir = self.cwd / ".memory-seed" / "sessions" / "2026-06-01.md"
        response = self.client().get("/api/v1/browse", params={"path": str(not_a_dir)})
        self.assertEqual(response.status_code, 400)

    # --- open -----------------------------------------------------------

    def test_opening_an_uninitialised_folder_is_refused_with_reasons(self):
        bare = self.make_dir("bare-folder")

        response = self.client().post("/api/v1/projects", params={"path": str(bare)})

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(payload["ok"])
        self.assertIsNone(payload["worktree"])
        self.assertTrue(payload["issues"])
        # Refused, so it must not appear as a switchable worktree.
        worktrees = self.client().get("/api/v1/worktrees").json()["worktrees"]
        self.assertEqual(len(worktrees), 1)

    def test_opening_a_correctly_initialised_project_registers_and_serves_it(self):
        other = self.make_valid_project("other-project")

        response = self.client().post("/api/v1/projects", params={"path": str(other)})
        payload = response.json()

        self.assertTrue(payload["ok"], payload.get("issues"))
        self.assertEqual(Path(payload["worktree"]["path"]).resolve(), other.resolve())
        self.assertFalse(payload["worktree"]["is_default"])

        client = self.client()
        worktrees = client.get("/api/v1/worktrees").json()["worktrees"]
        self.assertEqual(len(worktrees), 2)

        # The registered path now resolves through the normal worktree-scoped
        # surface - the same lazy-build/cache path a git worktree uses.
        facets = client.get("/api/v1/facets", params={"worktree": str(other)})
        self.assertEqual(facets.status_code, 200)

    def test_opening_the_same_project_twice_does_not_duplicate_the_entry(self):
        other = self.make_valid_project("reopened-project")
        client = self.client()

        client.post("/api/v1/projects", params={"path": str(other)})
        client.post("/api/v1/projects", params={"path": str(other)})

        worktrees = client.get("/api/v1/worktrees").json()["worktrees"]
        self.assertEqual(len(worktrees), 2)


if __name__ == "__main__":
    unittest.main()
