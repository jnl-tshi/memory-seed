from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).with_name("freeze_exposure.py")
SPEC = importlib.util.spec_from_file_location("freeze_exposure", MODULE_PATH)
assert SPEC and SPEC.loader
snapshot = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = snapshot
SPEC.loader.exec_module(snapshot)


def meta(rollout: str, session: str, parent: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(rollout_id=rollout, session_id=session, parent_thread_id=parent)


class ExposureRootTests(unittest.TestCase):
    def test_resolves_nested_parent_and_continuation_to_one_root(self) -> None:
        rows = [meta("r1", "root"), meta("r2", "root"), meta("r3", "child", "root"),
                meta("r4", "grandchild", "child")]
        result = snapshot.resolve_roots(rows)
        self.assertEqual(result["root"], ("resolved", "root"))
        self.assertEqual(result["child"], ("resolved", "root"))
        self.assertEqual(result["grandchild"], ("resolved", "root"))

    def test_missing_parent_cannot_be_claimed_as_fresh_root(self) -> None:
        result = snapshot.resolve_roots([meta("r1", "child", "absent")])
        self.assertEqual(result["child"], ("missing_parent", None))

    def test_ambiguous_continuation_and_descendant_remain_unresolved(self) -> None:
        rows = [meta("r1", "one"), meta("r2", "two"),
                meta("r3", "child", "one"), meta("r4", "child", "two"),
                meta("r5", "grandchild", "child")]
        result = snapshot.resolve_roots(rows)
        self.assertEqual(result["child"], ("ambiguous_parent", None))
        self.assertEqual(result["grandchild"], ("ancestor_unresolved", None))

    def test_cycle_is_not_a_root(self) -> None:
        result = snapshot.resolve_roots([meta("r1", "one", "two"), meta("r2", "two", "one")])
        self.assertEqual(result["one"], ("cycle", None))
        self.assertEqual(result["two"], ("cycle", None))

    def test_private_destination_rejects_repository_and_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo = base / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            with self.assertRaisesRegex(ValueError, "outside a Git checkout"):
                snapshot.validate_output_path(repo / "manifest.json")
            private = base / "private"
            private.mkdir()
            target = private / "manifest.json"
            self.assertEqual(snapshot.validate_output_path(target), target)
            target.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                snapshot.validate_output_path(target)

    def test_only_new_post_freeze_roots_are_prospectively_eligible(self) -> None:
        baseline = {
            "schema_version": 2, "created_at_utc": "2026-10-02T00:00:00+00:00",
            "rollouts": [{"root_session_id": "old", "lineage_status": "resolved",
                          "session_started_at_utc": "2026-10-01T00:00:00+00:00"}],
        }
        current = {
            "schema_version": 2, "created_at_utc": "2026-10-02T00:03:00+00:00",
            "rollouts": [
                {"root_session_id": "old", "lineage_status": "resolved",
                 "session_started_at_utc": "2026-10-01T00:00:00+00:00"},
                {"root_session_id": "new", "lineage_status": "resolved",
                 "session_started_at_utc": "2026-10-02T00:01:00+00:00"},
                {"root_session_id": "late-archive", "lineage_status": "resolved",
                 "session_started_at_utc": "2026-10-01T23:59:00+00:00"},
            ],
        }
        self.assertEqual(snapshot.prospective_roots(baseline, current), {"new"})

    def test_unresolved_current_population_blocks_freshness_claim(self) -> None:
        baseline = {"schema_version": 2, "created_at_utc": "2026-10-02T00:00:00+00:00",
                    "rollouts": []}
        current = {"schema_version": 2, "created_at_utc": "2026-10-02T00:03:00+00:00", "rollouts": [
            {"root_session_id": "new", "lineage_status": "resolved",
             "session_started_at_utc": "2026-10-02T00:01:00+00:00"},
            {"root_session_id": None, "lineage_status": "missing_parent",
             "session_started_at_utc": "2026-10-02T00:02:00+00:00"},
        ]}
        with self.assertRaisesRegex(ValueError, "unresolved"):
            snapshot.prospective_roots(baseline, current)

    def test_future_dated_root_is_not_prospectively_eligible(self) -> None:
        baseline = {"schema_version": 2, "created_at_utc": "2026-10-02T00:00:00+00:00",
                    "rollouts": []}
        current = {"schema_version": 2, "created_at_utc": "2026-10-02T00:03:00+00:00",
                   "rollouts": [{"root_session_id": "future", "lineage_status": "resolved",
                                 "session_started_at_utc": "2026-10-03T00:00:00+00:00"}]}
        self.assertEqual(snapshot.prospective_roots(baseline, current), set())

    def test_old_schema_cannot_claim_prospective_freshness(self) -> None:
        with self.assertRaisesRegex(ValueError, "timestamped baseline"):
            snapshot.prospective_roots({"schema_version": 1}, {"schema_version": 2})


if __name__ == "__main__":
    unittest.main()
