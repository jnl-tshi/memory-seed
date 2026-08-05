import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "context-derivation" / "generate_fixtures.py"
SPEC = importlib.util.spec_from_file_location("context_constitution_fixture_builder", SCRIPT)
assert SPEC and SPEC.loader
fixture_builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fixture_builder
SPEC.loader.exec_module(fixture_builder)

from memory_seed.adr import adr_membership


class ConstitutionBindingFixtureTests(unittest.TestCase):
    def _sources_and_records(self):
        real = fixture_builder.load_json(fixture_builder.SOURCE_DIR / "real-current.json")
        adversarial = fixture_builder.load_json(fixture_builder.SOURCE_DIR / "adversarial.json")
        bindings = fixture_builder.load_json(fixture_builder.CONSTITUTION_BINDINGS_PATH)
        return real, adversarial, bindings, fixture_builder._source_adr_records(real, adversarial)

    def test_source_has_stable_section_digests_and_exact_adr_coverage(self):
        _real, _adversarial, bindings, records = self._sources_and_records()
        sections, normalized = fixture_builder.validate_constitution_bindings(bindings, records)

        self.assertEqual(5, len(sections))
        self.assertEqual(10, len(normalized))
        self.assertEqual(
            {(fixture_id, adr_id) for fixture_id, adrs in records.items() for adr_id in adrs},
            {(item["fixture_id"], item["adr_id"]) for item in normalized},
        )
        for section in sections:
            self.assertEqual(
                section["digest"], fixture_builder._sha256(section["text"].encode("utf-8"))
            )

    def test_generated_fixtures_include_bound_constitution_blocks_in_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary:
            built = fixture_builder.build_all(Path(temporary) / "fixtures")
            for item in built:
                document = json.loads((item.path / "CONSTITUTION_BINDINGS.json").read_text(encoding="utf-8"))
                constitution = (item.path / "CONSTITUTION.md").read_text(encoding="utf-8")
                fixture_manifest = json.loads((item.path / "FIXTURE_MANIFEST.json").read_text(encoding="utf-8"))

                self.assertEqual("context-fixture-adr-constitution-bindings.v1", document["schema"])
                self.assertEqual(item.fixture_id, document["fixture_id"])
                self.assertTrue(document["bindings"])
                self.assertEqual(
                    fixture_manifest["content_fingerprint"],
                    fixture_builder.tree_fingerprint(item.path, exclude_manifest=True),
                )
                for section in document["sections"]:
                    self.assertIn(f"constitution-ref: {section['ref']}", constitution)
                    self.assertIn(section["text"], constitution)

    def test_shared_decision_binds_two_adrs_to_different_governing_sections(self):
        _real, _adversarial, bindings, records = self._sources_and_records()
        _sections, normalized = fixture_builder.validate_constitution_bindings(bindings, records)
        matching = [
            item
            for item in normalized
            if item["fixture_id"] == "adversarial-shared-decision"
            and "mse_ctxshared:d1" in item["decision_refs"]
        ]

        self.assertEqual({"adr_shared_cache", "adr_shared_audit"}, {item["adr_id"] for item in matching})
        governing_refs = {
            item["adr_id"]: next(ref["ref"] for ref in item["constitution_refs"] if ref["role"] == "governing")
            for item in matching
        }
        self.assertNotEqual(governing_refs["adr_shared_cache"], governing_refs["adr_shared_audit"])

    def test_related_only_context_cannot_create_an_adr_constitution_binding(self):
        _real, _adversarial, bindings, records = self._sources_and_records()
        _sections, normalized = fixture_builder.validate_constitution_bindings(bindings, records)
        binding = next(
            item
            for item in normalized
            if item["fixture_id"] == "adversarial-related-only"
            and item["adr_id"] == "adr_related_encryption"
        )

        self.assertEqual(["mse_ctxrelhead:d1"], binding["decision_refs"])
        self.assertNotIn(
            "mse_ctxrelcontext:d1",
            adr_membership(records["adversarial-related-only"]["adr_related_encryption"]),
        )

    def test_missing_duplicate_and_stale_bindings_fail_closed(self):
        _real, _adversarial, bindings, records = self._sources_and_records()

        missing = copy.deepcopy(bindings)
        missing["bindings"].pop()
        with self.assertRaisesRegex(ValueError, "missing constitution bindings"):
            fixture_builder.validate_constitution_bindings(missing, records)

        duplicate = copy.deepcopy(bindings)
        duplicate["bindings"].append(copy.deepcopy(duplicate["bindings"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate constitution binding"):
            fixture_builder.validate_constitution_bindings(duplicate, records)

        stale_decision = copy.deepcopy(bindings)
        stale_decision["bindings"][7]["decision_refs"] = ["mse_ctxrelcontext:d1"]
        with self.assertRaisesRegex(ValueError, "stale ADR decision references"):
            fixture_builder.validate_constitution_bindings(stale_decision, records)

        stale_section = copy.deepcopy(bindings)
        stale_section["bindings"][0]["constitution_refs"][0]["ref"] = "constitution:v1#gone"
        with self.assertRaisesRegex(ValueError, "stale constitution section"):
            fixture_builder.validate_constitution_bindings(stale_section, records)


if __name__ == "__main__":
    unittest.main()
