import json
import tempfile
import unittest
from pathlib import Path

from hosted.capture.corpus import build_manifest, evaluate_negative_controls, write_manifest


ROOT = Path(__file__).resolve().parents[1]


class P02CorpusTests(unittest.TestCase):
    def test_manifest_freezes_exact_partitions_and_hashes(self):
        manifest = build_manifest(ROOT)
        self.assertEqual(manifest["counts"]["formal_records"], 103)
        self.assertEqual(manifest["counts"]["typed_decisions"], 100)
        self.assertEqual(manifest["counts"]["development"], 80)
        self.assertEqual(manifest["counts"]["heldout_descriptive"], 15)
        self.assertEqual(manifest["counts"]["audit_only"], 13)
        self.assertEqual(len(manifest["source_artifacts"]), 3)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["source_artifacts"]))
        self.assertEqual(len(manifest["manifest_sha256"]), 64)

    def test_manifest_write_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            write_manifest(ROOT, first)
            write_manifest(ROOT, second)
            self.assertEqual((first / "corpus.jsonl").read_bytes(), (second / "corpus.jsonl").read_bytes())
            self.assertEqual((first / "manifest.json").read_bytes(), (second / "manifest.json").read_bytes())

    def test_negative_controls_measure_accepted_precision(self):
        result = evaluate_negative_controls(ROOT / "hosted" / "evaluation" / "negative_controls.jsonl")
        self.assertGreaterEqual(result["accepted_precision"], 0.90)
        self.assertEqual(result["false_accepts"], [])


if __name__ == "__main__":
    unittest.main()
