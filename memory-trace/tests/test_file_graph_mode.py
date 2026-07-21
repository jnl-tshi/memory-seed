"""File graph mode: /api/v1/graph/projection?path=<file> seeds the graph with
the exact entry membership set for that file, not a neighborhood expansion.

The real signal is subtle: this project's convention logs a session entry on
main *after* merging a feature branch, not on the branch itself and not in
the same commit as the feature's own files. So an entry's own authoring
commit (whichever commit first added its `entry_id:` line) almost always
touches only the session file - the real file changes sit on that commit's
PARENT (see _file_entry_index's docstring). These fixtures mirror that
pattern exactly: a merge commit carrying real files, immediately followed by
a separate commit that logs the entry - not a single combined commit.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_trace.service import TraceCache, create_app


def _entry(title, entry_id, body, *, branch=None, agent="claude"):
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
    if branch:
        lines.append(f"branch: {branch}")
    lines += ["```", "", body, ""]
    return "\n".join(lines)


class FileGraphModeTests(unittest.TestCase):
    """Corpus: two merged feature branches, each editing its own extra file,
    with the session entry logged on main in a separate commit right after
    each merge - exactly this project's real workflow.

    main   A -------- M1 -- L1 -------- M2 -- L2
                     /                /
    feature-a       B    feature-b   C

    L1 (logs mse_a) lands right after M1 (merges feature-a, which touched
    src/alpha.py). L2 (logs mse_b) lands right after M2 (feature-b,
    src/beta.py). Neither merge carries a Memory-Entry trailer and neither
    entry records the feature branch in its own `branch:` field (mse_a/mse_b
    are logged with branch: main, matching real practice) - the only signal
    available is the authoring commit's parent.
    """

    @classmethod
    def setUpClass(cls):
        cls.cwd = Path(tempfile.mkdtemp(prefix="memory-seed-file-mode-test-"))
        cls.cache_root = Path(tempfile.mkdtemp(prefix="memory-seed-file-mode-cache-"))
        sessions = cls.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        cls.session_file = sessions / "2026-06-01.md"
        src = cls.cwd / "src"
        src.mkdir(parents=True, exist_ok=True)

        def git(*args):
            subprocess.run(["git", "-C", str(cls.cwd), *args], check=True, capture_output=True)

        preamble = "---\ntags:\n  - session-log\n---\n\n"
        base = preamble + _entry("2026-06-01 09:00 - Main work", "mse_main", "On the trunk.", branch="main")

        git("init", "-b", "main")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        cls.session_file.write_text(base, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "A: base entry")

        git("checkout", "-b", "feature-a")
        (src / "alpha.py").write_text("alpha = 1\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "B: alpha.py, no session entry on the branch")

        git("checkout", "main")
        git("merge", "--no-ff", "feature-a", "-m", "Merge feature-a")

        with_a = base + _entry("2026-06-01 10:00 - Alpha work", "mse_a", "Logged after merge.", branch="main")
        cls.session_file.write_text(with_a, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "L1: log the alpha entry on main")

        git("checkout", "-b", "feature-b")
        (src / "beta.py").write_text("beta = 2\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "C: beta.py, no session entry on the branch")

        git("checkout", "main")
        git("merge", "--no-ff", "feature-b", "-m", "Merge feature-b")

        with_b = with_a + _entry("2026-06-01 11:00 - Beta work", "mse_b", "Logged after merge.", branch="main")
        cls.session_file.write_text(with_b, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "L2: log the beta entry on main")

        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(cls.cache_root)}):
            cls.app = create_app(cls.cwd, rebuild_cache=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cwd, ignore_errors=True)
        shutil.rmtree(cls.cache_root, ignore_errors=True)

    def client(self):
        from fastapi.testclient import TestClient

        return TestClient(self.app)

    def graph(self, **params):
        return self.client().get("/api/v1/graph/projection", params=params).json()

    def test_file_scoped_graph_resolves_to_the_entry_that_touched_it(self):
        result = self.graph(path="src/alpha.py")
        node_ids = [node["source"]["entry_id"] for node in result["nodes"]]
        self.assertEqual(node_ids, ["mse_a"])

    def test_a_different_file_resolves_to_its_own_entry_not_the_others(self):
        result = self.graph(path="src/beta.py")
        node_ids = [node["source"]["entry_id"] for node in result["nodes"]]
        self.assertEqual(node_ids, ["mse_b"])

    def test_the_shared_session_file_does_not_leak_into_an_unrelated_file_query(self):
        # Both branches touch the session file, but a query for one branch's
        # own source file must not pull in the other branch's entry.
        result = self.graph(path="src/alpha.py")
        node_ids = {node["source"]["entry_id"] for node in result["nodes"]}
        self.assertNotIn("mse_b", node_ids)

    def test_unknown_path_returns_an_empty_graph_not_the_overview(self):
        result = self.graph(path="src/does-not-exist.py")
        self.assertEqual(result["nodes"], [])

    def test_no_path_falls_back_to_the_normal_overview(self):
        # Sanity check that adding `path` support did not change default
        # (no-path) behavior: the overview still returns every entry.
        result = self.graph()
        node_ids = {node["source"]["entry_id"] for node in result["nodes"]}
        self.assertEqual(node_ids, {"mse_main", "mse_a", "mse_b"})

    def test_file_index_is_available_off_the_cache_directly(self):
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        index = cache.file_entry_index()
        self.assertEqual(index.get("src/alpha.py"), ["mse_a"])
        self.assertEqual(index.get("src/beta.py"), ["mse_b"])

    def test_an_entrys_own_branch_field_of_main_is_not_the_signal_used(self):
        # Both mse_a and mse_b record branch: main (they were logged on main
        # after merging) - proves the index isn't just grouping by that field,
        # since if it were, alpha.py and beta.py would both resolve to both
        # entries instead of staying distinct.
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        index = cache.file_entry_index()
        self.assertNotEqual(index.get("src/alpha.py"), index.get("src/beta.py"))


class FileGraphModeDirectToMainTests(unittest.TestCase):
    """An entry logged immediately after a plain (non-merge) commit that
    touched real files, with no feature branch involved at all - the other
    real shape this project's history contains."""

    @classmethod
    def setUpClass(cls):
        cls.cwd = Path(tempfile.mkdtemp(prefix="memory-seed-file-mode-direct-test-"))
        cls.cache_root = Path(tempfile.mkdtemp(prefix="memory-seed-file-mode-direct-cache-"))
        sessions = cls.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        cls.session_file = sessions / "2026-06-01.md"
        src = cls.cwd / "src"
        src.mkdir(parents=True, exist_ok=True)

        def git(*args):
            subprocess.run(["git", "-C", str(cls.cwd), *args], check=True, capture_output=True)

        preamble = "---\ntags:\n  - session-log\n---\n\n"
        base = preamble + _entry("2026-06-01 09:00 - Main work", "mse_main", "On the trunk.", branch="main")

        git("init", "-b", "main")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        cls.session_file.write_text(base, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "A: base entry")

        (src / "delta.py").write_text("delta = 4\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "B: delta.py committed straight to main")

        with_delta = base + _entry("2026-06-01 10:00 - Delta work", "mse_delta", "Logged right after.", branch="main")
        cls.session_file.write_text(with_delta, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "C: log the delta entry")

        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(cls.cache_root)}):
            cls.app = create_app(cls.cwd, rebuild_cache=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cwd, ignore_errors=True)
        shutil.rmtree(cls.cache_root, ignore_errors=True)

    def test_file_mode_resolves_a_plain_commit_with_no_merge_involved(self):
        from fastapi.testclient import TestClient

        result = TestClient(self.app).get("/api/v1/graph/projection", params={"path": "src/delta.py"}).json()
        node_ids = [node["source"]["entry_id"] for node in result["nodes"]]
        self.assertEqual(node_ids, ["mse_delta"])
