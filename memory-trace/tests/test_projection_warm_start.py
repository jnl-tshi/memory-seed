"""Derived-projection Phase 1 warm start (contract G4/G5/G7).

The existing cache tests use a NON-git corpus, so they only exercise the mtime
fallback. These use a real git repo and pin the warm-start path:

- a no-op ``ensure_current`` (clean tree, HEAD unmoved) does NOT rebuild and
  does NOT fall back to the whole-corpus mtime scan (G5);
- every genuine change rebuilds: an uncommitted edit (dirty tree), a new commit
  (HEAD moved), and a schema-version bump;
- without git it degrades to the mtime scan and still self-heals (G7);
- deleting the DB and rebuilding yields byte-identical reads (G2).
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_trace.service import PROJECTION_SCHEMA_VERSION, TraceCache


def _entry(dt, eid, body="work."):
    return f"## {dt} - {eid}\n\n```yaml\nentry_id: {eid}\n```\n\n{body}\n"


class ProjectionWarmStartTests(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mtrace-warm-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="mtrace-warm-cache-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache_root, ignore_errors=True))
        self.sessions = self.cwd / ".memory-seed" / "sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)
        self.env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@e.com",
            "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@e.com",
        }
        self.git("init", "-b", "main")
        self.write("2026-06-01.md", _entry("2026-06-01 09:00", "mse_a"))
        self.git("add", "-A")
        self.git("commit", "-m", "a")

    def git(self, *args):
        subprocess.run(
            ["git", "-C", str(self.cwd), *args],
            check=True, capture_output=True, text=True, env=self.env,
        )

    def write(self, name, content):
        (self.sessions / name).write_text(
            "---\ntags:\n  - session-log\n---\n\n" + content, encoding="utf-8"
        )

    def cache(self):
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        # These tests exercise the freshness CHECK directly; disable the memo
        # window so a change made right after a build is seen immediately. The
        # memoization itself is covered by its own test below.
        cache._FRESHNESS_TTL_SECONDS = 0
        return cache

    def test_no_op_ensure_current_does_not_rebuild(self):
        cache = self.cache()
        cache.rebuild()
        before = cache.status()["rebuilt_at"]
        cache.ensure_current()
        self.assertEqual(cache.status()["rebuilt_at"], before)

    def test_no_op_fast_path_never_scans_the_whole_corpus(self):
        cache = self.cache()
        cache.rebuild()
        # The mtime whole-corpus scan is the no-git fallback ONLY. With git, the
        # fast path must prove freshness without it - so calling it here fails.
        with mock.patch.object(
            TraceCache, "_metadata_matches", side_effect=AssertionError("scanned whole corpus")
        ):
            cache.ensure_current()  # must not raise

    def test_uncommitted_edit_triggers_rebuild(self):
        cache = self.cache()
        cache.rebuild()
        before = cache.status()["rebuilt_at"]
        self.write("2026-06-01.md", _entry("2026-06-01 09:00", "mse_a", "edited."))
        cache.ensure_current()
        self.assertGreater(cache.status()["rebuilt_at"], before)

    def test_new_commit_triggers_rebuild(self):
        cache = self.cache()
        cache.rebuild()
        before = cache.status()["rebuilt_at"]
        self.write("2026-06-02.md", _entry("2026-06-02 09:00", "mse_b"))
        self.git("add", "-A")
        self.git("commit", "-m", "b")
        cache.ensure_current()
        self.assertGreater(cache.status()["rebuilt_at"], before)

    def test_schema_version_bump_triggers_rebuild(self):
        cache = self.cache()
        cache.rebuild()
        before = cache.status()["rebuilt_at"]
        with mock.patch("memory_trace.service.PROJECTION_SCHEMA_VERSION", PROJECTION_SCHEMA_VERSION + 1):
            cache.ensure_current()
        self.assertGreater(cache.status()["rebuilt_at"], before)

    def test_no_git_degrades_to_mtime_scan(self):
        cache = self.cache()
        cache.rebuild()
        before = cache.status()["rebuilt_at"]
        with mock.patch("memory_trace.service._git_head", return_value=None):
            cache.ensure_current()  # unchanged -> mtime scan says current
            self.assertEqual(cache.status()["rebuilt_at"], before)
            self.write("2026-06-01.md", _entry("2026-06-01 09:00", "mse_a", "grown."))
            cache.ensure_current()  # changed -> mtime scan detects it
            self.assertGreater(cache.status()["rebuilt_at"], before)

    def test_freshness_verdict_is_memoized_within_the_ttl(self):
        # Within the TTL window a burst of reads must NOT re-run the freshness
        # check (git) - the fix for per-read git spawns making entry switching
        # laggy. rebuild() marks fresh; the following reads stay inside it.
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        cache._FRESHNESS_TTL_SECONDS = 60
        cache.rebuild()
        with mock.patch("memory_trace.service._git_head") as head:
            cache.ensure_current()
            cache.ensure_current()
            cache.ensure_current()
            head.assert_not_called()

    def test_chunks_are_memoized_and_invalidated_on_rebuild(self):
        # Deserializing chunks is the dominant read cost; the parsed list is
        # memoized until a rebuild, so repeated reads reuse it (same object),
        # and a change that rebuilds returns a fresh list reflecting it.
        cache = self.cache()
        cache.rebuild()
        first = cache.chunks(granularity="entry")
        self.assertIs(cache.chunks(granularity="entry"), first)  # memo hit
        self.write("2026-06-02.md", _entry("2026-06-02 09:00", "mse_new"))
        self.git("add", "-A")
        self.git("commit", "-m", "add")
        third = cache.chunks(granularity="entry")
        self.assertIsNot(third, first)  # rebuilt -> memo dropped -> fresh list
        self.assertIn("mse_new", {c.entry_id for c in third})

    def test_no_git_link_sidecar_change_triggers_rebuild(self):
        # The closed gap: link/diagram sidecars live under sessions/ but the
        # no-git mtime scan used to skip them (iter_session_documents ignores
        # links/ and diagrams/). They are now tracked, so a sidecar edit
        # invalidates the projection even without git.
        cache = self.cache()
        cache.rebuild()
        before = cache.status()["rebuilt_at"]
        with mock.patch("memory_trace.service._git_head", return_value=None):
            cache.ensure_current()
            self.assertEqual(cache.status()["rebuilt_at"], before)  # nothing changed
            links = self.sessions / "links" / "2026-06"
            links.mkdir(parents=True, exist_ok=True)
            (links / "2026-06-01.md").write_text(
                "---\ntags:\n  - session-log-links\nlink_date: 2026-06-01\n---\n\n"
                "## 2026-06-01 09:00 - a\n\n```yaml\nentry_id: mse_a\nrelated_entries:\n  - mse_a\n```\n",
                encoding="utf-8",
            )
            cache.ensure_current()  # no-git scan must now see the new sidecar file
            self.assertGreater(cache.status()["rebuilt_at"], before)

    def test_derived_bundle_is_memoized_and_invalidated_on_rebuild(self):
        from memory_trace.service import TraceService

        service = TraceService(self.cache())
        first = service._derived()
        self.assertIs(service._derived(), first)  # memo hit within a generation
        service.cache.rebuild()  # bumps the generation
        self.assertIsNot(service._derived(), first)  # invalidated -> fresh bundle

    def test_rebuild_from_markdown_is_byte_identical(self):
        # G2: the projection is disposable - a fresh rebuild from the same
        # Markdown yields identical reads. Two independent caches (separate
        # roots, same corpus) stand in for delete-then-rebuild without racing
        # Windows file locks on the read connections.
        first = self.cache()
        first.rebuild()
        second_root = Path(tempfile.mkdtemp(prefix="mtrace-warm-cache2-"))
        self.addCleanup(lambda: shutil.rmtree(second_root, ignore_errors=True))
        second = TraceCache(self.cwd, cache_root=second_root)
        second.rebuild()
        self.assertEqual(
            sorted((c.chunk_id, c.granularity) for c in second.chunks()),
            sorted((c.chunk_id, c.granularity) for c in first.chunks()),
        )
        self.assertEqual(second.entry_commits(), first.entry_commits())
        self.assertEqual(second.trailer_merges(), first.trailer_merges())


if __name__ == "__main__":
    unittest.main()
