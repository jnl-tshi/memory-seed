"""`links graph-diff` - the graph-level assertion that has caught silent
sidecar corruption twice (807 edges vanished with `links check` reading OK;
then a +3 edge resurrection) but until now only lived in throwaway campaign
scripts. `effective_graph_snapshot` / `diff_graph_snapshots` promote it to a
standing tool: snapshot the effective evolves/refines graph, later compare
and fail loudly on an entry-level `evolves` edge-set change.
"""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.cli import main as cli_main
from memory_seed.core import MEMORY_DIR_NAME, check_session_links
from memory_seed.retrieval import diff_graph_snapshots, effective_graph_snapshot


class GraphDiffTestBase(unittest.TestCase):
    def setUp(self):
        self.cwd = Path(tempfile.mkdtemp(prefix="mseed-graphdiff-"))
        self.addCleanup(lambda: shutil.rmtree(self.cwd, ignore_errors=True))
        (self.cwd / MEMORY_DIR_NAME / "sessions").mkdir(parents=True, exist_ok=True)

    def _entry(self, entry_id, ts, *, body="### Decision\n\n- D: a call.\n- R: a reason.\n"):
        path = self.cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-13.md"
        block = f"## {ts} - entry {entry_id}\n\n```yaml\nentry_id: {entry_id}\n```\n\n{body}\n"
        path.write_text((path.read_text(encoding="utf-8") if path.exists() else "") + block, encoding="utf-8")

    def _sidecar(self, name, lines):
        d = self.cwd / MEMORY_DIR_NAME / "sessions" / "links"
        d.mkdir(parents=True, exist_ok=True)
        path = d / "2026-06-13.md"
        path.write_text(
            (path.read_text(encoding="utf-8") if path.exists() else "") + "\n".join(lines) + "\n",
            encoding="utf-8",
        )

    def _run_cli(self, *args, cwd=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(cwd or self.cwd)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli_main(list(args))
        finally:
            os.chdir(previous)
        return exit_code, stdout.getvalue(), stderr.getvalue()


class SnapshotShapeTests(GraphDiffTestBase):
    def test_snapshot_shape_and_aggregates(self):
        old, new = "mse_aaaaaaaaaaaaaaaa", "mse_bbbbbbbbbbbbbbbb"
        self._entry(old, "2026-06-13 09:00")
        self._entry(new, "2026-06-13 10:00")
        self._sidecar("edge", [
            "## 2026-06-13 10:05 - typed edge", "", "```yaml",
            f"entry_id: {new}", "evolves:", f"  - d1 -> {old} (refines)", "```", "",
        ])
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

        snapshot = effective_graph_snapshot(self.cwd)

        self.assertEqual(
            set(snapshot),
            {"schema_version", "corpus_revision", "generated_at", "aggregates", "evolves", "refines_successors"},
        )
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(
            snapshot["aggregates"],
            {"evolves_refs": 1, "nodes_with_successors": 1, "nodes_refined": 1},
        )
        self.assertEqual(snapshot["evolves"], {new: [old]})
        self.assertEqual(snapshot["refines_successors"], {f"{old}:d1": [f"{new}:d1"]})
        # generated_at and corpus_revision are present (a bare temp dir has no
        # git repo, so corpus_revision is None - still a valid, present key).
        self.assertIn("generated_at", snapshot)
        self.assertIsNone(snapshot["corpus_revision"])

    def test_empty_corpus_snapshot(self):
        snapshot = effective_graph_snapshot(self.cwd)
        self.assertEqual(
            snapshot["aggregates"],
            {"evolves_refs": 0, "nodes_with_successors": 0, "nodes_refined": 0},
        )
        self.assertEqual(snapshot["evolves"], {})
        self.assertEqual(snapshot["refines_successors"], {})


class NoOpDiffTests(GraphDiffTestBase):
    def test_unchanged_corpus_diffs_clean(self):
        old, new = "mse_cccccccccccccccc", "mse_dddddddddddddddd"
        self._entry(old, "2026-06-13 09:00")
        self._entry(new, "2026-06-13 10:00")
        self._sidecar("edge", [
            "## 2026-06-13 10:05 - typed edge", "", "```yaml",
            f"entry_id: {new}", "evolves:", f"  - {old} (builds-on)", "```", "",
        ])

        before = effective_graph_snapshot(self.cwd)
        after = effective_graph_snapshot(self.cwd)
        diff = diff_graph_snapshots(before, after)
        self.assertEqual(diff["verdict"], "unchanged")
        self.assertEqual(diff["evolves_added"], {})
        self.assertEqual(diff["evolves_removed"], {})

    def test_cli_snapshot_then_against_unchanged_exits_zero(self):
        old, new = "mse_eeeeeeeeeeeeeeee", "mse_ffffffffffffffff"
        self._entry(old, "2026-06-13 09:00")
        self._entry(new, "2026-06-13 10:00")
        self._sidecar("edge", [
            "## 2026-06-13 10:05 - typed edge", "", "```yaml",
            f"entry_id: {new}", "evolves:", f"  - {old} (builds-on)", "```", "",
        ])
        baseline = self.cwd / "baseline.json"
        code, out, err = self._run_cli("links", "graph-diff", "--snapshot", str(baseline))
        self.assertEqual(code, 0, err)
        self.assertTrue(baseline.is_file())
        payload = json.loads(baseline.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], 1)

        code, out, err = self._run_cli("links", "graph-diff", "--against", str(baseline))
        self.assertEqual(code, 0, err)
        self.assertIn("unchanged", out.lower())


class ChangedDiffTests(GraphDiffTestBase):
    def test_edge_added_between_snapshot_and_diff_fails_and_names_it(self):
        old, new = "mse_1111111111111111", "mse_2222222222222222"
        self._entry(old, "2026-06-13 09:00")
        self._entry(new, "2026-06-13 10:00")
        baseline = self.cwd / "baseline.json"
        code, out, err = self._run_cli("links", "graph-diff", "--snapshot", str(baseline))
        self.assertEqual(code, 0, err)

        # A bulk write adds a new evolves edge after the snapshot was taken.
        self._sidecar("edge", [
            "## 2026-06-13 10:05 - new edge", "", "```yaml",
            f"entry_id: {new}", "evolves:", f"  - {old} (builds-on)", "```", "",
        ])

        code, out, err = self._run_cli("links", "graph-diff", "--against", str(baseline))
        self.assertEqual(code, 1)
        self.assertIn("CHANGED", err)
        self.assertIn(new, err)
        self.assertIn(old, err)

        # Same assertion directly against the dict payload.
        before = json.loads(baseline.read_text(encoding="utf-8"))
        after = effective_graph_snapshot(self.cwd)
        diff = diff_graph_snapshots(before, after)
        self.assertEqual(diff["verdict"], "changed")
        self.assertEqual(diff["evolves_added"], {new: [old]})
        self.assertEqual(diff["evolves_removed"], {})
        self.assertNotEqual(diff["aggregate_deltas"]["evolves_refs"]["delta"], 0)

    def test_edge_removed_is_also_flagged(self):
        # Untyped on purpose: an entry-level-only edge with no decision_edges
        # twin, so a bare retract removes it outright (a typed edge's surviving
        # decision_edges projection would otherwise keep it - see
        # RetractAndRetypeIsInformationalTests, the behaviour this asymmetry
        # exists to support).
        old, new = "mse_3333333333333333", "mse_4444444444444444"
        self._entry(old, "2026-06-13 09:00")
        self._entry(new, "2026-06-13 10:00")
        self._sidecar("edge", [
            "## 2026-06-13 10:05 - edge", "", "```yaml",
            f"entry_id: {new}", "evolves:", f"  - {old}", "```", "",
        ])
        before = effective_graph_snapshot(self.cwd)

        self._sidecar("retract", [
            "## 2026-06-13 11:00 - retracted, not replaced", "", "```yaml",
            f"entry_id: {new}", "retracts:", f"  - evolves {old}", "```", "",
        ])
        after = effective_graph_snapshot(self.cwd)
        diff = diff_graph_snapshots(before, after)
        self.assertEqual(diff["verdict"], "changed")
        self.assertEqual(diff["evolves_removed"], {new: [old]})


class RetractAndRetypeIsInformationalTests(GraphDiffTestBase):
    def test_retract_and_retype_keeps_edge_set_and_reports_typing_delta(self):
        # The exact shape of the reverted 2026-08-09 backfill: one block
        # retracts the untyped edge and re-authors it typed. The effective
        # `evolves` edge set must NOT change (verdict unchanged / exit 0);
        # the refines-successor delta is reported as informational context.
        old, new = "mse_5555555555555555", "mse_6666666666666666"
        self._entry(old, "2026-06-13 09:00")
        self._entry(new, "2026-06-13 10:00")
        self._sidecar("original", [
            "## 2026-06-13 10:05 - original untyped edge", "", "```yaml",
            f"entry_id: {new}", "evolves:", f"  - d1 -> {old}", "```", "",
        ])
        baseline = self.cwd / "baseline.json"
        code, out, err = self._run_cli("links", "graph-diff", "--snapshot", str(baseline))
        self.assertEqual(code, 0, err)

        self._sidecar("backfill", [
            "## 2026-06-13 11:00 - evolution type backfilled", "", "```yaml",
            f"entry_id: {new}", "source: derived",
            "retracts:", f"  - evolves d1 -> {old}",
            "evolves:", f"  - d1 -> {old} (refines)", "```", "",
        ])
        self.assertTrue(check_session_links(cwd=self.cwd).ok)

        code, out, err = self._run_cli("links", "graph-diff", "--against", str(baseline), "--json")
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["verdict"], "unchanged")
        self.assertEqual(payload["evolves_added"], {})
        self.assertEqual(payload["evolves_removed"], {})
        self.assertTrue(
            payload["refines_successors_added"] or payload["refines_successors_removed"],
            "the retype must be visible as an informational refines delta",
        )


class BaselineFailureTests(GraphDiffTestBase):
    def test_missing_baseline_file_exits_two(self):
        code, out, err = self._run_cli(
            "links", "graph-diff", "--against", str(self.cwd / "nope.json")
        )
        self.assertEqual(code, 2)
        self.assertTrue(err)

    def test_malformed_json_baseline_exits_two(self):
        bad = self.cwd / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        code, out, err = self._run_cli("links", "graph-diff", "--against", str(bad))
        self.assertEqual(code, 2)
        self.assertTrue(err)

    def test_schema_version_mismatch_exits_two(self):
        old_schema = self.cwd / "old-schema.json"
        old_schema.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
        code, out, err = self._run_cli("links", "graph-diff", "--against", str(old_schema))
        self.assertEqual(code, 2)
        self.assertIn("schema_version", err)

    def test_both_flags_or_neither_is_a_usage_error(self):
        code, out, err = self._run_cli("links", "graph-diff")
        self.assertEqual(code, 2)
        baseline = self.cwd / "baseline.json"
        code, out, err = self._run_cli("links", "graph-diff", "--snapshot", str(baseline))
        self.assertEqual(code, 0, err)
        code, out, err = self._run_cli(
            "links", "graph-diff", "--snapshot", str(baseline), "--against", str(baseline)
        )
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
