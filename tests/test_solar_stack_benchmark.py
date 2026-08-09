"""Offline contract and negative-control tests for Solar Stack Benchmark 001."""
from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "experiments" / "stack-benchmark" / "solar-filaments-001"
spec = importlib.util.spec_from_file_location("solar_harness", HERE / "harness.py")
harness = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(harness)


class SolarHarnessTests(unittest.TestCase):
    def test_eight_arms_and_strict_tool_separation(self):
        config = harness.load_json(HERE / "benchmark.json")
        self.assertEqual(list(harness.ARM_TOOLS), config["arms"])
        self.assertEqual([], harness.ARM_TOOLS["baseline"])
        self.assertEqual(["graphify"], harness.ARM_TOOLS["graphify"])
        self.assertEqual(["semble"], harness.ARM_TOOLS["semble"])
        self.assertEqual(["memory-seed", "graphify"], harness.ARM_TOOLS["memory-seed-graphify"])
        self.assertEqual(["memory-seed", "semble"], harness.ARM_TOOLS["memory-seed-semble"])

    def test_freeze_fails_closed(self):
        issues = harness.freeze_issues(harness.load_json(HERE / "benchmark.json"))
        self.assertIn("benchmark status is not FROZEN", issues)
        self.assertIn("Kaggle rules are not accepted", issues)
        self.assertTrue(any("claude_model" in issue for issue in issues))
        for schema in (HERE / "schemas").glob("*.json"):
            self.assertIsInstance(json.loads(schema.read_text(encoding="utf-8")), dict)

    def test_union_prevents_double_count_and_gpu_wait_does_not_change_agent_time(self):
        active = [
            {"type": "interval", "class": "agent_active", "start": "2026-08-08T10:00:00Z", "end": "2026-08-08T10:10:00Z"},
            {"type": "interval", "class": "agent_active", "start": "2026-08-08T10:05:00Z", "end": "2026-08-08T10:15:00Z"},
        ]
        short = active + [{"type": "interval", "class": "compute_wait", "start": "2026-08-08T10:15:00Z", "end": "2026-08-08T10:20:00Z"}]
        long = active + [{"type": "interval", "class": "compute_wait", "start": "2026-08-08T10:15:00Z", "end": "2026-08-08T11:20:00Z"}]
        self.assertEqual(900, harness.derive_clocks(short)["agent_active_seconds"])
        self.assertEqual(harness.derive_clocks(short)["agent_active_seconds"], harness.derive_clocks(long)["agent_active_seconds"])
        self.assertNotEqual(harness.derive_clocks(short)["compute_wait_seconds"], harness.derive_clocks(long)["compute_wait_seconds"])

    def test_conflicting_classification_is_rejected(self):
        events = [
            {"type": "interval", "interval_id": "x", "class": "agent_active", "start": "2026-08-08T10:00:00Z", "end": "2026-08-08T10:01:00Z"},
            {"type": "interval", "interval_id": "x", "class": "compute_wait", "start": "2026-08-08T10:00:00Z", "end": "2026-08-08T10:01:00Z"},
        ]
        with self.assertRaisesRegex(ValueError, "merges agent-active"):
            harness.derive_clocks(events)

    def test_submission_negative_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            valid = root / "valid.csv"
            with valid.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle); writer.writerow(["filament_id", "segmentation_rle"]); writer.writerow(["img1_1", "abc123"])
            self.assertEqual([], harness.validate_submission(valid, {"img1"}))
            invalid = root / "invalid.csv"
            invalid.write_text("filament_id,segmentation_rle\nimg1_1,\nimg1_1,x\n", encoding="utf-8")
            issues = harness.validate_submission(invalid, {"img1", "img2"})
            self.assertTrue(any("unique" in issue for issue in issues))
            self.assertTrue(any("non-empty" in issue for issue in issues))
            self.assertTrue(any("omits" in issue for issue in issues))

    def test_colab_result_checks_identity_hashes_and_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            job = Path(temp); (job / "result").mkdir(); (job / "payload").mkdir()
            spec = {"job_id": "j1", "expected_artifacts": ["metrics.json"]}
            (job / "job.json").write_text(json.dumps(spec), encoding="utf-8")
            artifact = job / "payload" / "metrics.json"; artifact.write_text("{}", encoding="utf-8")
            result = {"job_id": "j1", "config_sha256": harness.sha256(job / "job.json"), "compute_seconds": 12, "exit_code": 0, "artifacts": [{"path": "metrics.json", "sha256": harness.sha256(artifact)}]}
            (job / "result" / "result.json").write_text(json.dumps(result), encoding="utf-8")
            self.assertEqual([], harness.validate_job(job))
            (job / "result" / "stderr.log").write_text("KAGGLE_KEY=do-not-store", encoding="utf-8")
            self.assertTrue(any("credential" in issue for issue in harness.validate_job(job)))

    def test_report_keeps_raw_metrics_and_marginal_pairs(self):
        runs = []
        for arm, score in (("baseline", .1), ("memory-seed", .2), ("graphify", .3), ("memory-seed-graphify", .4)):
            runs.append({"arm": arm, "metrics": {"best_validation_dice": score}, "clocks": {"agent_active_seconds": 10}, "issues": []})
        with tempfile.TemporaryDirectory() as temp:
            original = harness.ROOT
            try:
                harness.ROOT = Path(temp)
                report = harness.report({"runs": runs})
            finally: harness.ROOT = original
        self.assertEqual(runs, report["raw_runs"])
        pair = next(row for row in report["comparisons"] if row["treatment"] == "memory-seed-graphify" and row["control"] == "graphify")
        self.assertAlmostEqual(.1, pair["deltas"]["best_validation_dice"])

    def test_generation_creates_all_canonical_arm_contracts_deterministically(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir(); (source / ".git").mkdir()
            (source / "train.py").write_text("print('train')\n", encoding="utf-8")
            config = harness.load_json(HERE / "benchmark.json")
            config["status"] = "FROZEN"; config["competition"]["rules_accepted"] = True
            for field in harness.FREEZE_FIELDS: config["freeze"][field] = config["freeze"].get(field) or "pinned"
            benchmark = root / "benchmark.json"; benchmark.write_text(json.dumps(config), encoding="utf-8")
            old_benchmark, old_generated = harness.BENCHMARK, harness.GENERATED
            try:
                harness.BENCHMARK, harness.GENERATED = benchmark, root / "generated"
                harness.generate(source)
                first = harness.fingerprint_tree(harness.GENERATED)
                harness.generate(source)
                second = harness.fingerprint_tree(harness.GENERATED)
            finally:
                harness.BENCHMARK, harness.GENERATED = old_benchmark, old_generated
            self.assertEqual(first, second)
            for arm in config["arms"]:
                workspace = root / "generated" / "arms" / arm / "workspace"
                self.assertTrue((root / "generated" / "arms" / arm / "ARM_MANIFEST.json").is_file())
                for relative in harness.REQUIRED_RUN_PATHS: self.assertTrue((workspace / relative).exists())


if __name__ == "__main__": unittest.main()
