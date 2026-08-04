import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "context-derivation" / "generate_fixtures.py"
SPEC = importlib.util.spec_from_file_location("context_fixture_builder", SCRIPT)
assert SPEC and SPEC.loader
fixture_builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fixture_builder
SPEC.loader.exec_module(fixture_builder)

from memory_seed.adr import adr_membership, check_adrs, parse_adr
from memory_seed.core import check_session_links


class ContextDerivationFixtureTests(unittest.TestCase):
    def test_manifest_has_exact_real_and_adversarial_mix(self):
        _manifest, gold, tasks = fixture_builder.load_definitions()

        self.assertEqual(12, len(tasks))
        self.assertEqual([f"CTX-{number:02d}" for number in range(1, 13)], [task["task_id"] for task in tasks])
        self.assertEqual(6, sum(task["fixture"] == "real-current" for task in tasks))
        self.assertEqual(6, sum(task["fixture"] != "real-current" for task in tasks))
        self.assertEqual(6, len({task["fixture"] for task in tasks if task["fixture"] != "real-current"}))
        self.assertEqual("APPROVED", gold["approval_status"])
        self.assertTrue(fixture_builder.scored_execution_approved())

    def test_frozen_real_sources_are_verified(self):
        source = fixture_builder.load_json(fixture_builder.SOURCE_DIR / "real-current.json")
        for item in [*source["adr_sources"], *source["session_sources"]]:
            path, text = fixture_builder._read_verified_source(item)
            self.assertTrue(path.is_file())
            self.assertTrue(text)

        tampered = dict(source["adr_sources"][0], sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "frozen source drift"):
            fixture_builder._read_verified_source(tampered)

    def test_rebuild_is_byte_deterministic_and_adrs_validate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = fixture_builder.build_all(root / "first" / "fixtures")
            second = fixture_builder.build_all(root / "second" / "fixtures")

            self.assertEqual(
                {item.fixture_id: fixture_builder.tree_fingerprint(item.path) for item in first},
                {item.fixture_id: fixture_builder.tree_fingerprint(item.path) for item in second},
            )
            for item in first:
                ok, issues = check_adrs(item.path)
                if item.fixture_id == "adversarial-missing-evidence":
                    self.assertFalse(ok)
                    self.assertEqual(1, len(issues), issues)
                    self.assertIn("supporting decision references missing entry mse_ctxmissingbenchmark", issues[0])
                else:
                    self.assertTrue(ok, f"{item.fixture_id}: {issues}")
                link_result = check_session_links(item.path)
                self.assertTrue(link_result.ok, f"{item.fixture_id}: {link_result.issues}")
                fixture_manifest = json.loads((item.path / "FIXTURE_MANIFEST.json").read_text(encoding="utf-8"))
                self.assertFalse(fixture_manifest["gold_included"])
                self.assertEqual(
                    fixture_manifest["content_fingerprint"],
                    fixture_builder.tree_fingerprint(item.path, exclude_manifest=True),
                )

    def test_generated_tasks_resolve_to_built_fixtures_without_context_answers(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "generated" / "fixtures"
            built = fixture_builder.build_all(output)
            built_by_id = {item.fixture_id: item.path.resolve() for item in built}
            generated = json.loads((output.parent / "tasks.json").read_text(encoding="utf-8"))

            self.assertEqual(12, len(generated["tasks"]))
            for task in generated["tasks"]:
                self.assertNotIn("included_refs", task)
                actual = (fixture_builder.EXPERIMENT_ROOT / task["fixture"]).resolve()
                source_id = next(
                    source["fixture"]
                    for source in fixture_builder.load_json(fixture_builder.MANIFEST_PATH)["tasks"]
                    if source["task_id"] == task["task_id"]
                )
                self.assertEqual(built_by_id[source_id], actual)

    def test_gold_is_never_copied_into_fixture_or_run_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fixtures"
            built = fixture_builder.build_all(output)
            for item in built:
                fixture_builder.assert_gold_isolated(item.path)
                run_dir = Path(temporary) / "runs" / item.fixture_id
                shutil.copytree(item.path, run_dir)
                fixture_builder.assert_gold_isolated(run_dir)
                self.assertFalse(any("gold" in path.name.lower() for path in run_dir.rglob("*")))

    def test_related_only_reference_is_not_adr_lineage(self):
        _manifest, gold, _tasks = fixture_builder.load_definitions()
        row = next(item for item in gold["tasks"] if item["task_id"] == "CTX-11")
        self.assertEqual([], row["required_lineage_edges"])
        self.assertEqual("related", row["required_related_edges"][0]["type"])

        with tempfile.TemporaryDirectory() as temporary:
            built = {item.fixture_id: item for item in fixture_builder.build_all(Path(temporary) / "fixtures")}
            record = parse_adr(
                built["adversarial-related-only"].path
                / ".memory-seed"
                / "decisions"
                / "adr_related_encryption.md"
            )
            self.assertIn("mse_ctxrelhead:d1", adr_membership(record))
            self.assertNotIn("mse_ctxrelcontext:d1", adr_membership(record))

    def test_missing_supporting_evidence_is_declared_but_not_materialized(self):
        _manifest, gold, _tasks = fixture_builder.load_definitions()
        row = next(item for item in gold["tasks"] if item["task_id"] == "CTX-12")
        self.assertEqual(["mse_ctxmissingbenchmark:d1"], row["required_missing_refs"])

        with tempfile.TemporaryDirectory() as temporary:
            built = {item.fixture_id: item for item in fixture_builder.build_all(Path(temporary) / "fixtures")}
            fixture = built["adversarial-missing-evidence"].path
            record = parse_adr(
                fixture / ".memory-seed" / "decisions" / "adr_missing_compaction.md"
            )
            declared_support = {
                ref
                for event in record.events
                if event.kind == "revision-proposed"
                for ref in event.supporting_decisions
            }
            self.assertIn("mse_ctxmissingbenchmark:d1", declared_support)
            session_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (fixture / ".memory-seed" / "sessions").rglob("*.md")
            )
            self.assertNotIn("mse_ctxmissingbenchmark", session_text)


if __name__ == "__main__":
    unittest.main()
