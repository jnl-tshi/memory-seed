"""Commit-accurate merge representation in the Trail.

The Trail's fork/merge geometry is driven by ground truth where it exists:
``session merge-branch`` stamps ``Memory-Entry: <entry_id>`` trailers on merge
commits, and the lense recovers those in one first-parent pass. These tests
build a REAL git repo (the worktree-switching suite's temp-corpus pattern,
plus ``git init``) and pin:

- ``/api/graph`` gains ``merges`` (ordered trailer merge events) and
  ``branches`` (per-branch merge/fork/estimated), on the legacy surface only;
- a branch's fork is the merge commit's parents' merge-base;
- a branch whose NEWEST entry is unmerged is open (merge None, not estimated)
  even when older entries were merged - no fabricated merge;
- pre-trailer-era branches fall back to ``estimated: True``;
- ``chunk()`` reports ``merged_by`` distinctly from the authoring ``commit``;
- without git everything fails open (empty merges, estimated branches);
- the ``/api/v1/*`` contract does NOT expose the new keys (response_model
  strips them - pins the vanilla-only scope).
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_trace.lense import create_app


def _entry(title, entry_id, body, *, branch=None, agent="claude", topics=None):
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
    if topics:
        lines.append("topics:")
        lines.extend(f"  - {topic}" for topic in topics)
    lines += ["```", "", body, ""]
    return "\n".join(lines)


class TrailMergeAccuracyTests(unittest.TestCase):
    """Corpus: a real repo whose history exercises every branch state.

    main   A ---------- M ---- D ---------- M2      (M, M2 carry trailers)
                       /                   /
    feature-x         B          feature-y E

    Entries: mse_main (main), mse_old (legacy-branch, pre-trailer era),
    mse_feat1 (feature-x, merged by M), mse_feat2 (feature-x metadata but
    committed straight to main in D with no trailer - the branch's newest
    entry is unmerged, so feature-x is OPEN), mse_feat3 (feature-y, merged
    by M2 - feature-y is CLOSED).
    """

    @classmethod
    def setUpClass(cls):
        cls.cwd = Path(tempfile.mkdtemp(prefix="memory-seed-merge-test-"))
        cls.cache_root = Path(tempfile.mkdtemp(prefix="memory-seed-merge-cache-"))
        sessions = cls.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        cls.session_file = sessions / "2026-06-01.md"

        def git(*args):
            subprocess.run(["git", "-C", str(cls.cwd), *args], check=True, capture_output=True)

        preamble = "---\ntags:\n  - session-log\n---\n\n"
        base = preamble + _entry(
            "2026-06-01 09:00 - Legacy work", "mse_old", "Pre-trailer era.", branch="legacy-branch"
        ) + _entry("2026-06-01 10:00 - Main work", "mse_main", "On the trunk.", branch="main")

        git("init", "-b", "main")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        cls.session_file.write_text(base, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "A: base entries")

        git("checkout", "-b", "feature-x")
        with_feat1 = base + _entry(
            "2026-06-01 11:00 - Feature one", "mse_feat1", "Branch work.", branch="feature-x"
        )
        cls.session_file.write_text(with_feat1, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "B: feature-x entry")

        git("checkout", "main")
        git("merge", "--no-ff", "feature-x", "-m", "Merge feature-x\n\nMemory-Entry: mse_feat1")
        cls.merge1 = _rev_parse(cls.cwd, "HEAD")
        cls.commit_a = _rev_parse(cls.cwd, "HEAD~1")

        # mse_feat2 carries feature-x branch metadata but lands straight on
        # main with no trailer: the branch's newest entry is unmerged.
        with_feat2 = with_feat1 + _entry(
            "2026-06-01 12:00 - Feature one continues", "mse_feat2", "Unmerged tail.", branch="feature-x"
        )
        cls.session_file.write_text(with_feat2, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "D: unmerged feature-x tail")
        cls.commit_d = _rev_parse(cls.cwd, "HEAD")

        git("checkout", "-b", "feature-y")
        with_feat3 = with_feat2 + _entry(
            "2026-06-01 13:00 - Feature two", "mse_feat3", "Second branch.", branch="feature-y"
        )
        cls.session_file.write_text(with_feat3, encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "E: feature-y entry")

        git("checkout", "main")
        git("merge", "--no-ff", "feature-y", "-m", "Merge feature-y\n\nMemory-Entry: mse_feat3")
        cls.merge2 = _rev_parse(cls.cwd, "HEAD")

        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(cls.cache_root)}):
            cls.app = create_app(cls.cwd, rebuild_cache=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.cwd, ignore_errors=True)
        shutil.rmtree(cls.cache_root, ignore_errors=True)

    def client(self):
        from fastapi.testclient import TestClient

        return TestClient(self.app)

    def graph(self):
        return self.client().get("/api/graph", params={"granularity": "entry"}).json()

    def test_graph_lists_trailer_merge_events_with_their_entries(self):
        merges = self.graph()["merges"]
        self.assertEqual(len(merges), 2)
        by_sha = {event["sha"]: event for event in merges}
        self.assertEqual(by_sha[self.merge1]["entry_ids"], ["mse_feat1"])
        self.assertEqual(by_sha[self.merge2]["entry_ids"], ["mse_feat3"])
        for event in merges:
            self.assertEqual(
                sorted(event), ["date", "entry_ids", "sha", "short", "subject"]
            )
            self.assertTrue(event["date"])
            self.assertTrue(event["short"])

    def test_closed_branch_binds_merge_and_merge_base_fork(self):
        info = self.graph()["branches"]["feature-y"]
        self.assertFalse(info["estimated"])
        self.assertEqual(info["merge"]["sha"], self.merge2)
        # feature-y branched off D, so the merge commit's parents' merge-base
        # (the fork point) is D.
        self.assertEqual(info["fork"]["sha"], self.commit_d)

    def test_open_branch_dangles_instead_of_fabricating_a_merge(self):
        # feature-x's newest entry (mse_feat2) was never merged: the branch is
        # open (merge None) but NOT estimated - its history is still real, and
        # its earlier merge remains visible in the merges list.
        info = self.graph()["branches"]["feature-x"]
        self.assertFalse(info["estimated"])
        self.assertIsNone(info["merge"])
        self.assertEqual(info["fork"]["sha"], self.commit_a)

    def test_pre_trailer_branch_falls_back_to_estimated(self):
        info = self.graph()["branches"]["legacy-branch"]
        self.assertTrue(info["estimated"])
        self.assertIsNone(info["merge"])
        self.assertIsNone(info["fork"])

    def test_main_never_appears_as_a_branch(self):
        self.assertNotIn("main", self.graph()["branches"])

    def test_chunk_reports_merged_by_distinct_from_authoring_commit(self):
        client = self.client()
        merged = client.get("/api/chunks/mse_feat1").json()
        self.assertEqual(merged["merged_by"]["sha"], self.merge1)
        # Authoring commit (diff-derived) is the branch commit, not the merge.
        self.assertNotEqual(merged["commit"]["sha"], merged["merged_by"]["sha"])
        unmerged = client.get("/api/chunks/mse_feat2").json()
        self.assertIsNone(unmerged["merged_by"])

    def test_v1_contract_does_not_expose_the_new_keys(self):
        # Vanilla-only scope: the versioned surface stays untouched -
        # response_model validation strips the extra keys the shared service
        # now returns.
        client = self.client()
        v1_graph = client.get("/api/v1/graph", params={"granularity": "entry"})
        self.assertEqual(v1_graph.status_code, 200)
        self.assertNotIn("merges", v1_graph.json())
        self.assertNotIn("branches", v1_graph.json())
        v1_trail = client.get("/api/v1/trail")
        self.assertEqual(v1_trail.status_code, 200)
        self.assertNotIn("merges", v1_trail.json())
        v1_chunk = client.get("/api/v1/chunks/mse_feat1")
        self.assertEqual(v1_chunk.status_code, 200)
        self.assertNotIn("merged_by", v1_chunk.json())


class TrailMergeNoGitFallbackTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="memory-seed-merge-nogit-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="memory-seed-merge-nogit-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        sessions = self.cwd / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n"
            + _entry("2026-06-01 09:00 - Solo", "mse_solo", "No repo here.", branch="some-branch"),
            encoding="utf-8",
        )
        with mock.patch.dict(os.environ, {"MEMORY_SEED_LENSE_CACHE_ROOT": str(self.cache_root)}):
            self.app = create_app(self.cwd, rebuild_cache=True)

    def test_no_git_fails_open_to_estimated(self):
        from fastapi.testclient import TestClient

        payload = TestClient(self.app).get("/api/graph", params={"granularity": "entry"}).json()
        self.assertEqual(payload["merges"], [])
        self.assertEqual(
            payload["branches"], {"some-branch": {"merge": None, "fork": None, "estimated": True}}
        )


def _rev_parse(cwd: Path, ref: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", ref], check=True, capture_output=True, text=True
    )
    return proc.stdout.strip()


if __name__ == "__main__":
    unittest.main()
