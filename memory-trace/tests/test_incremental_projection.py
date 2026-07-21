"""Incremental projection reconciliation (the derived-projection plan's
"incremental ingest" fast-follow, gated on incremental == full-rebuild
equivalence - contract G2).

Real git repos throughout. The load-bearing assertions:

- a plain forward move (new commit / dirty edit) reconciles WITHOUT a full
  rebuild, reparsing only the changed documents;
- a new merge resolves only its own fork point, from one bulk pass;
- fork points persist in SQLite and survive a fresh process (memo cleared);
- the file-entry index is absent after ordinary startup, built lazily on the
  first File-mode request, shared across concurrent callers, and persisted;
- history rewrites and re-added entry ids fall back to full recomputation;
- after any mix of changes, every read surface is IDENTICAL to a clean full
  rebuild of the same corpus (the G2 equivalence gate).
"""

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import memory_trace.service as service_module
from memory_trace.service import TraceCache


def _entry(dt, eid, body="work."):
    return f"## {dt} - {eid}\n\n```yaml\nentry_id: {eid}\n```\n\n{body}\n"


class _RepoCase(unittest.TestCase):
    """A real git corpus with helpers for branches, merges and entries."""

    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mtrace-incr-"))
        self.cache_root = Path(tempfile.mkdtemp(prefix="mtrace-incr-cache-"))
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
        self.git("commit", "-m", "seed")
        service_module._FORK_POINT_MEMO.clear()
        self.addCleanup(service_module._FORK_POINT_MEMO.clear)

    def git(self, *args):
        subprocess.run(
            ["git", "-C", str(self.cwd), *args],
            check=True, capture_output=True, text=True, env=self.env,
        )

    def write(self, name, content):
        (self.sessions / name).write_text(
            "---\ntags:\n  - session-log\n---\n\n" + content, encoding="utf-8"
        )

    def append(self, name, content):
        with (self.sessions / name).open("a", encoding="utf-8") as handle:
            handle.write(content)

    def merge_feature(self, branch, file_name, entry_text, extra_file=None, trailer=None):
        """A feature branch carrying a session entry (and optionally another
        file), merged --no-ff into main with an optional Memory-Entry trailer."""
        self.git("checkout", "-b", branch)
        self.write(file_name, entry_text) if not (self.sessions / file_name).exists() else self.append(file_name, entry_text)
        if extra_file:
            (self.cwd / extra_file).write_text("payload\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", f"work on {branch}")
        self.git("checkout", "main")
        message = f"Merge branch '{branch}'"
        if trailer:
            message += f"\n\nMemory-Entry: {trailer}"
        self.git("merge", "--no-ff", "-m", message, branch)

    def cache(self):
        cache = TraceCache(self.cwd, cache_root=self.cache_root)
        cache._FRESHNESS_TTL_SECONDS = 0
        return cache


class IncrementalReconcileTests(_RepoCase):
    def test_new_commit_reconciles_without_full_rebuild(self):
        cache = self.cache()
        cache.rebuild()
        self.write("2026-06-02.md", _entry("2026-06-02 09:00", "mse_b"))
        self.git("add", "-A")
        self.git("commit", "-m", "add b")
        with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
            cache.ensure_current()
        self.assertIn("mse_b", {c.entry_id for c in cache.chunks(granularity="entry")})
        self.assertIn("mse_b", cache.entry_commits())
        self.assertIn("mse_b", cache.main_commit_entries())

    def test_changed_document_reparses_only_that_document(self):
        self.write("2026-06-03.md", _entry("2026-06-03 09:00", "mse_c"))
        self.git("add", "-A")
        self.git("commit", "-m", "add c")
        cache = self.cache()
        cache.rebuild()
        self.append("2026-06-03.md", _entry("2026-06-03 10:00", "mse_c2"))
        original = service_module.extract_memory_chunks
        seen_paths: list[object] = []

        def recording(cwd, *, granularity="entry", paths=None):
            seen_paths.append(paths)
            return original(cwd, granularity=granularity, paths=paths)

        with mock.patch.object(service_module, "extract_memory_chunks", recording):
            with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
                cache.ensure_current()
        self.assertTrue(seen_paths, "reconcile never reparsed anything")
        for paths in seen_paths:
            self.assertIsNotNone(paths, "reconcile fell back to a whole-corpus parse")
            self.assertEqual(
                [Path(p).name for p in paths], ["2026-06-03.md"],
                "reconcile reparsed more than the changed document",
            )
        self.assertIn("mse_c2", {c.entry_id for c in cache.chunks(granularity="entry")})

    def test_dirty_edit_and_its_commit_are_both_seen(self):
        cache = self.cache()
        cache.rebuild()
        self.append("2026-06-01.md", _entry("2026-06-01 11:00", "mse_dirty"))
        with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
            cache.ensure_current()
        self.assertIn("mse_dirty", {c.entry_id for c in cache.chunks(granularity="entry")})
        self.git("add", "-A")
        self.git("commit", "-m", "commit the dirty entry")
        with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
            cache.ensure_current()
        self.assertIn("mse_dirty", cache.entry_commits())

    def test_new_merge_resolves_only_its_own_fork_point(self):
        self.merge_feature("f/one", "2026-06-04.md", _entry("2026-06-04 09:00", "mse_m1"), trailer="mse_m1")
        cache = self.cache()
        cache.rebuild()
        self.assertEqual(len(cache.trailer_merges()), 1)
        self.merge_feature("f/two", "2026-06-05.md", _entry("2026-06-05 09:00", "mse_m2"), trailer="mse_m2")
        # Only the NEW merge may cost fork work, and never via per-merge git.
        with mock.patch.object(service_module, "_merge_fork_point", side_effect=AssertionError("per-merge subprocess")):
            with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
                cache.ensure_current()
        merges = cache.trailer_merges()
        self.assertEqual(len(merges), 2)
        for event in merges:
            self.assertIsNotNone(event["fork"], f"merge {event['short']} lost its fork point")

    def test_fork_points_survive_a_new_process(self):
        self.merge_feature("f/persist", "2026-06-06.md", _entry("2026-06-06 09:00", "mse_p"), trailer="mse_p")
        cache = self.cache()
        cache.rebuild()
        expected = [event["fork"] for event in cache.trailer_merges()]
        self.assertTrue(all(expected))
        # Fresh "process": empty memo, new instance. Touch history so the
        # reconcile path must re-emit trailer_merges - with bulk resolution
        # forbidden, the only source for the old fork is the persisted table.
        service_module._FORK_POINT_MEMO.clear()
        self.write("2026-06-07.md", _entry("2026-06-07 09:00", "mse_after"))
        self.git("add", "-A")
        self.git("commit", "-m", "later commit")
        fresh = self.cache()
        with mock.patch.object(service_module, "_merge_fork_point", side_effect=AssertionError("per-merge subprocess")):
            with mock.patch.object(service_module, "_bulk_fork_points", side_effect=AssertionError("bulk recompute ran")):
                fresh.ensure_current()
        self.assertEqual([event["fork"] for event in fresh.trailer_merges()], expected)

    def test_rewrite_triggers_full_rebuild_and_stays_correct(self):
        cache = self.cache()
        cache.rebuild()
        self.append("2026-06-01.md", _entry("2026-06-01 12:00", "mse_rw"))
        self.git("add", "-A")
        self.git("commit", "--amend", "-m", "seed amended")
        rebuilds: list[bool] = []
        original = cache._rebuild_locked

        def spying():
            rebuilds.append(True)
            return original()

        with mock.patch.object(cache, "_rebuild_locked", spying):
            cache.ensure_current()
        self.assertTrue(rebuilds, "amended history must fall back to a full rebuild")
        self.assertIn("mse_rw", {c.entry_id for c in cache.chunks(granularity="entry")})

    def test_deleted_session_file_removes_its_chunks(self):
        self.write("2026-06-08.md", _entry("2026-06-08 09:00", "mse_gone"))
        self.git("add", "-A")
        self.git("commit", "-m", "add doomed file")
        cache = self.cache()
        cache.rebuild()
        self.assertIn("mse_gone", {c.entry_id for c in cache.chunks(granularity="entry")})
        self.git("rm", str((self.sessions / "2026-06-08.md").relative_to(self.cwd)))
        self.git("commit", "-m", "remove doomed file")
        with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
            cache.ensure_current()
        self.assertNotIn("mse_gone", {c.entry_id for c in cache.chunks(granularity="entry")})

    def test_renamed_session_file_moves_its_chunks(self):
        self.write("2026-06-09.md", _entry("2026-06-09 09:00", "mse_move"))
        self.git("add", "-A")
        self.git("commit", "-m", "add movable file")
        cache = self.cache()
        cache.rebuild()
        self.git(
            "mv",
            str((self.sessions / "2026-06-09.md").relative_to(self.cwd)),
            str((self.sessions / "2026-06-10.md").relative_to(self.cwd)),
        )
        self.git("commit", "-m", "rename session file")
        with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
            cache.ensure_current()
        dates = {c.session_date.isoformat() for c in cache.chunks(granularity="entry") if c.entry_id == "mse_move"}
        self.assertEqual(dates, {"2026-06-10"})

    def test_readded_entry_id_keeps_oldest_attribution(self):
        self.write("2026-06-11.md", _entry("2026-06-11 09:00", "mse_re"))
        self.git("add", "-A")
        self.git("commit", "-m", "first add")
        cache = self.cache()
        cache.rebuild()
        first_sha = cache.entry_commits()["mse_re"]["sha"]
        self.git("rm", str((self.sessions / "2026-06-11.md").relative_to(self.cwd)))
        self.git("commit", "-m", "drop")
        self.write("2026-06-11.md", _entry("2026-06-11 09:00", "mse_re"))
        self.git("add", "-A")
        self.git("commit", "-m", "re-add")
        cache.ensure_current()
        self.assertEqual(cache.entry_commits()["mse_re"]["sha"], first_sha)


class LazyFileIndexTests(_RepoCase):
    def test_ordinary_startup_does_not_build_the_file_index(self):
        self.merge_feature(
            "f/files", "2026-06-12.md", _entry("2026-06-12 09:00", "mse_f"),
            extra_file="src_alpha.py", trailer="mse_f",
        )
        self.write("2026-06-12b.md", _entry("2026-06-12 10:00", "mse_flog"))
        self.git("add", "-A")
        self.git("commit", "-m", "log after merge")
        cache = self.cache()
        cache.rebuild()
        marker, rows = self._index_state(cache)
        self.assertIsNone(marker, "rebuild eagerly built the file index")
        self.assertEqual(rows, 0)
        index = cache.file_entry_index()
        self.assertIn("src_alpha.py", index)
        marker, rows = self._index_state(cache)
        self.assertIsNotNone(marker, "first File-mode request must persist the index")
        self.assertGreater(rows, 0)

    @staticmethod
    def _index_state(cache):
        # Close the connection explicitly: sqlite3's context manager only ends
        # the transaction, and a lingering open handle on Windows would deny
        # the very atomic swap this test goes on to require.
        conn = sqlite3.connect(cache.db_path)
        try:
            marker = conn.execute("select 1 from meta where key='file_index_watermark'").fetchone()
            rows = conn.execute("select count(*) from file_entries").fetchone()[0]
        finally:
            conn.close()
        return marker, rows

    def test_persisted_file_index_serves_a_fresh_process_without_harvest(self):
        self.merge_feature(
            "f/files2", "2026-06-13.md", _entry("2026-06-13 09:00", "mse_g"),
            extra_file="src_beta.py", trailer="mse_g",
        )
        cache = self.cache()
        cache.rebuild()
        first = cache.file_entry_index()
        service_module._FORK_POINT_MEMO.clear()
        fresh = self.cache()
        with mock.patch.object(service_module, "_changed_paths_bulk", side_effect=AssertionError("re-harvested")):
            with mock.patch.object(service_module, "_commit_graph", side_effect=AssertionError("re-harvested")):
                self.assertEqual(fresh.file_entry_index(), first)

    def test_concurrent_first_requests_share_one_build(self):
        self.merge_feature(
            "f/files3", "2026-06-14.md", _entry("2026-06-14 09:00", "mse_h"),
            extra_file="src_gamma.py", trailer="mse_h",
        )
        cache = self.cache()
        cache.rebuild()
        calls: list[bool] = []
        original = service_module._changed_paths_bulk

        def counting(root, rev):
            calls.append(True)
            return original(root, rev)

        results: list[dict] = []
        with mock.patch.object(service_module, "_changed_paths_bulk", counting):
            threads = [
                threading.Thread(target=lambda: results.append(cache.file_entry_index()))
                for _ in range(4)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(len(calls), 1, "concurrent first requests raced separate builds")
        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result, results[0])

    def test_no_git_corpus_returns_empty_index(self):
        plain = Path(tempfile.mkdtemp(prefix="mtrace-nogit-"))
        self.addCleanup(lambda: shutil.rmtree(plain, ignore_errors=True))
        sessions = plain / ".memory-seed" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "2026-06-01.md").write_text(
            "---\ntags:\n  - session-log\n---\n\n" + _entry("2026-06-01 09:00", "mse_x"),
            encoding="utf-8",
        )
        cache = TraceCache(plain, cache_root=self.cache_root)
        cache._FRESHNESS_TTL_SECONDS = 0
        cache.rebuild()
        self.assertEqual(cache.file_entry_index(), {})


class EquivalenceTests(_RepoCase):
    """The G2 gate: after incremental reconciliation, every read surface is
    identical to a clean full rebuild of the same corpus."""

    def _full_rebuild_reference(self):
        reference_root = Path(tempfile.mkdtemp(prefix="mtrace-ref-cache-"))
        self.addCleanup(lambda: shutil.rmtree(reference_root, ignore_errors=True))
        reference = TraceCache(self.cwd, cache_root=reference_root)
        reference._FRESHNESS_TTL_SECONDS = 0
        reference.rebuild()
        return reference

    def _chunk_key(self, cache):
        return sorted(
            (c.chunk_id, c.granularity, c.entry_id or "", json.dumps(service_module._chunk_to_storage(c), sort_keys=True))
            for c in cache.chunks()
        )

    def test_incremental_reads_match_a_clean_full_rebuild(self):
        cache = self.cache()
        cache.rebuild()
        # A representative mix: plain commit, trailer merge carrying real
        # files, post-merge log entry, dirty append.
        self.write("2026-06-20.md", _entry("2026-06-20 09:00", "mse_e1"))
        self.git("add", "-A")
        self.git("commit", "-m", "plain commit")
        with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
            cache.ensure_current()
        self.merge_feature(
            "f/equiv", "2026-06-21.md", _entry("2026-06-21 09:00", "mse_e2"),
            extra_file="src_equiv.py", trailer="mse_e2",
        )
        self.write("2026-06-22.md", _entry("2026-06-22 09:00", "mse_e3"))
        self.git("add", "-A")
        self.git("commit", "-m", "log after merge")
        with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
            cache.ensure_current()
        self.append("2026-06-22.md", _entry("2026-06-22 10:00", "mse_e4"))
        with mock.patch.object(cache, "_rebuild_locked", side_effect=AssertionError("full rebuild ran")):
            cache.ensure_current()

        reference = self._full_rebuild_reference()
        self.assertEqual(self._chunk_key(cache), self._chunk_key(reference))
        self.assertEqual(cache.entry_commits(), reference.entry_commits())
        self.assertEqual(cache.main_commit_entries(), reference.main_commit_entries())
        self.assertEqual(cache.trailer_merges(), reference.trailer_merges())
        self.assertEqual(cache.file_entry_index(), reference.file_entry_index())


class BulkSubprocessBudgetTests(_RepoCase):
    """"No git work per historical item": the subprocess count of a full
    rebuild must stay flat as merge history grows."""

    def _count_rebuild_subprocesses(self):
        cache = self.cache()
        if cache.db_path.exists():
            cache.db_path.unlink()
        service_module._FORK_POINT_MEMO.clear()
        count = 0
        original = subprocess.run

        def counting(*args, **kwargs):
            nonlocal count
            count += 1
            return original(*args, **kwargs)

        with mock.patch.object(service_module.subprocess, "run", counting):
            cache.rebuild()
        return count

    def test_rebuild_subprocesses_do_not_grow_with_merge_count(self):
        for index in range(3):
            self.merge_feature(
                f"f/budget{index}", f"2026-06-{15 + index}.md",
                _entry(f"2026-06-{15 + index} 09:00", f"mse_b{index}"),
                trailer=f"mse_b{index}",
            )
        few = self._count_rebuild_subprocesses()
        for index in range(3, 9):
            self.merge_feature(
                f"f/budget{index}", f"2026-06-{15 + index}.md",
                _entry(f"2026-06-{15 + index} 09:00", f"mse_b{index}"),
                trailer=f"mse_b{index}",
            )
        many = self._count_rebuild_subprocesses()
        self.assertEqual(
            few, many,
            f"rebuild subprocess count grew with history ({few} -> {many}): per-item git work is back",
        )


if __name__ == "__main__":
    unittest.main()
