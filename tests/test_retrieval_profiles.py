import copy
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from memory_seed.retrieval import (
    RetrievalSpecResolutionError,
    _evidence_pack_fingerprint,
    resolve_retrieval_spec,
    validate_evidence_pack,
)
from memory_seed.retrieval_profiles import (
    RetrievalProfileValidationError,
    _read_profile_yaml,
    load_retrieval_profile,
    normalize_retrieval_profile,
)
from memory_seed.retrieval_spec import (
    RetrievalSpecValidationError,
    normalize_retrieval_spec_v2,
)


class RetrievalProfileTests(unittest.TestCase):
    def make_project(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-retrieval-profile-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / ".memory-seed" / "sessions").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "docs" / "CONSTITUTION.md").write_text("# Constitution\n", encoding="utf-8")
        self.write_entry(root, "mse_entry0001", "### Decision\n\n- D: Keep exact retrieval.\n- R: IDs are stable.\n")
        return root

    def write_entry(self, root, entry_id, body, *, topics=()):
        topic_lines = "topics:\n" + "".join(f"  - {topic}\n" for topic in topics) if topics else ""
        (root / ".memory-seed" / "sessions" / "2026-08-01.md").write_text(
            "## 2026-08-01 09:00 - Test entry\n\n```yaml\n"
            f"entry_id: {entry_id}\nuser_initials: JN\nagent_type: codex\n"
            "project_path: .\nsubproject_path: null\n" + topic_lines + "```\n\n" + body,
            encoding="utf-8",
        )

    def write_adr(self, root, adr_id="adr_pinned"):
        path = root / ".memory-seed" / "decisions" / f"{adr_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\nformat: memory-seed-adr/2\nschema_version: 2\n"
            f"adr_id: {adr_id}\ntitle: Pinned\ncreated_at: 2026-08-01T09:00:00Z\n"
            "user_initials: JN\nagent_type: codex\nsource: write-time\n---\n\n"
            "# Pinned\n\n## Current view\n\nStatus: **Accepted**\n\n"
            "## Event ledger\n\n### accepted — 2026-08-01T09:00:00Z\n",
            encoding="utf-8",
        )
        return path

    def write_profile(self, root, profile_id, body, version=1):
        path = root / ".memory-seed" / "retrieval-profiles" / profile_id / f"v{version}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    @staticmethod
    def profile(profile_id, spec, *, extends="[]", version=1):
        return (
            "schema: memory-seed/retrieval-profile\nversion: 1\n"
            f"id: {profile_id}\nprofile_version: {version}\nextends: {extends}\nspec:\n{spec}"
        )

    def test_v2_schema_is_strict_and_rejects_hyphen_decision_ids(self):
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
            "selectors": {"pinned": [{"kind": "decision", "id": "mse_entry0001-d1", "reason": "needed"}]},
        }
        with self.assertRaisesRegex(RetrievalSpecValidationError, "canonical '<entry-id>:dN'"):
            normalize_retrieval_spec_v2(spec)
        spec["selectors"]["pinned"][0]["id"] = "mse_entry0001:d1"
        spec["selectors"]["pinned"][0]["kind"] = "session"
        with self.assertRaisesRegex(RetrievalSpecValidationError, "must be 'adr' or 'decision'"):
            normalize_retrieval_spec_v2(spec)
        spec["selectors"]["pinned"][0]["kind"] = "decision"
        spec["selectors"]["pinned"][0]["unknown"] = True
        with self.assertRaises(RetrievalSpecValidationError):
            normalize_retrieval_spec_v2(spec)

    def test_profile_schema_exact_lookup_composition_and_list_operations(self):
        root = self.make_project()
        self.write_profile(root, "base", self.profile("base", "  filters:\n    topics:\n      - alpha\n  required:\n    related_decisions:\n      depth: 2\n"))
        self.write_profile(root, "child", self.profile("child", "  filters:\n    topics:\n      append:\n        - beta\n      remove:\n        - alpha\n", extends="\n  - id: base\n    profile_version: 1"))
        resolved = load_retrieval_profile("child", 1, root, overrides={"filters": {"paths": ["docs/CONSTITUTION.md"]}})
        self.assertEqual(resolved["filters"], {"topics": ["beta"], "paths": ["docs/CONSTITUTION.md"]})
        self.assertEqual(resolved["required"]["related_decisions"]["depth"], 2)
        with self.assertRaises(RetrievalProfileValidationError):
            load_retrieval_profile("../child", 1, root)
        self.write_profile(root, "mismatch", self.profile("other", "  limits:\n    max_entries: 2\n"))
        with self.assertRaisesRegex(RetrievalProfileValidationError, "exact path"):
            load_retrieval_profile("mismatch", 1, root)

    def test_profile_parser_is_dependency_free_and_accepts_documented_forms(self):
        root = self.make_project()
        self.write_profile(
            root,
            "base",
            self.profile("base", "  filters:\n    topics:\n      - alpha\n"),
        )
        self.write_profile(
            root,
            "child",
            self.profile(
                "child",
                "  filters:\n    topics: {append: [], remove: []}\n"
                "  output:\n    include_resolution_trace: true\n",
                extends="\n  - id: base\n    profile_version: 1",
            ),
        )
        with patch.dict(sys.modules, {"yaml": None}):
            resolved = load_retrieval_profile("child", 1, root)
        self.assertEqual(resolved["filters"]["topics"], ["alpha"])
        self.assertTrue(resolved["output"]["include_resolution_trace"])
        parsed = _read_profile_yaml(
            "root:\n  children:\n    - name: one\n      enabled: true\n    - name: two\n      value: null\n",
            path="fixture.yaml",
        )
        self.assertEqual(parsed["root"]["children"][1], {"name": "two", "value": None})

    def test_profile_cycles_duplicates_and_downgrades_fail_closed(self):
        root = self.make_project()
        self.write_profile(root, "a", self.profile("a", "  limits:\n    max_entries: 30\n", extends="\n  - id: b\n    profile_version: 1"))
        self.write_profile(root, "b", self.profile("b", "  limits:\n    max_entries: 30\n", extends="\n  - id: a\n    profile_version: 1"))
        with self.assertRaisesRegex(RetrievalProfileValidationError, "a:v1 -> b:v1 -> a:v1"):
            load_retrieval_profile("a", 1, root)

        self.write_profile(root, "parent", self.profile("parent", "  required:\n    related_decisions:\n      depth: 3\n"))
        self.write_profile(root, "weak", self.profile("weak", "  required:\n    related_decisions:\n      depth: 2\n", extends="\n  - id: parent\n    profile_version: 1"))
        with self.assertRaisesRegex(RetrievalProfileValidationError, "cannot reduce"):
            load_retrieval_profile("weak", 1, root)
        with self.assertRaises(RetrievalProfileValidationError):
            normalize_retrieval_profile({"schema": "memory-seed/retrieval-profile"})

    def test_core_profiles_have_the_published_bounds(self):
        root = Path(__file__).resolve().parents[1]
        expected = {
            "implementation": (2, 8, 30, 12000),
            "bug-investigation": (3, 20, 40, 16000),
            "research": (2, 15, 50, 20000),
            "adr-review": (5, 10, 50, 20000),
            "refactoring": (3, 10, 40, 16000),
            "architecture": (4, 15, 50, 20000),
        }
        for profile_id, values in expected.items():
            with self.subTest(profile=profile_id):
                spec = load_retrieval_profile(profile_id, 1, root)
                self.assertEqual(
                    (spec["required"]["related_decisions"]["depth"], spec["optional"]["sessions"]["neighbouring_entries"], spec["limits"]["max_entries"], spec["limits"]["max_tokens"]),
                    values,
                )

    def test_pinned_adr_and_decision_are_exact_deduplicated_and_ordered(self):
        root = self.make_project()
        self.write_adr(root)
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
            "filters": {"paths": [".memory-seed/decisions/adr_pinned.md"]},
            "selectors": {"pinned": [
                {"kind": "adr", "id": "adr_pinned", "reason": "architecture mandate"},
                {"kind": "decision", "id": "mse_entry0001:d1", "reason": "implementation constraint"},
            ]},
        }
        pack = resolve_retrieval_spec(spec, root)
        self.assertEqual(pack["resolver_version"], 3)
        self.assertEqual(
            {item["id"] for item in pack["evidence"][:2]},
            {"adr_pinned", "mse_entry0001:d1"},
        )
        self.assertEqual(len([item for item in pack["evidence"] if item["id"] == "adr_pinned"]), 1)
        adr = next(item for item in pack["evidence"] if item["id"] == "adr_pinned")
        self.assertIn("Current view", "\n".join((root / adr["source"]).read_text(encoding="utf-8").splitlines()[adr["line_range"][0] - 1:adr["line_range"][1]]))
        self.assertNotIn("Event ledger", "\n".join((root / adr["source"]).read_text(encoding="utf-8").splitlines()[adr["line_range"][0] - 1:adr["line_range"][1]]))
        self.assertEqual(adr["model_selection_reasons"], ["architecture mandate"])
        self.assertTrue(validate_evidence_pack(pack, root)["valid"])

    def test_v2_profile_candidate_and_pin_deduplicate_to_colon_decision_id(self):
        root = self.make_project()
        self.write_entry(
            root,
            "mse_entry0001",
            "### Decision\n\n- D: Keep exact retrieval.\n- R: IDs are stable.\n",
            topics=("focus",),
        )
        self.write_profile(
            root,
            "dedup",
            self.profile(
                "dedup",
                "  filters:\n    topics:\n      - focus\n"
                "  selectors:\n    pinned:\n      - kind: decision\n"
                "        id: mse_entry0001:d1\n"
                "        reason: exact instruction\n",
            ),
        )
        pack = resolve_retrieval_spec(load_retrieval_profile("dedup", 1, root), root)
        decisions = [item for item in pack["evidence"] if item["kind"] == "decision"]
        self.assertEqual([item["id"] for item in decisions], ["mse_entry0001:d1"])
        self.assertIn("selectors.pinned", decisions[0]["selected_by"])
        self.assertIn("required.related_decisions", decisions[0]["selected_by"])

    def test_optional_missing_and_tampered_v2_packs_fail_correctly(self):
        root = self.make_project()
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
            "selectors": {"pinned": [{"kind": "decision", "id": "mse_missing:d1", "reason": "optional", "required": False}]},
        }
        spec["selectors"]["pinned"].append({"kind": "decision", "id": "mse_entry0001:d1", "reason": "required"})
        pack = resolve_retrieval_spec(spec, root)
        self.assertIn("mse_missing:d1", [warning["detail"] for warning in pack["warnings"]])
        tampered = copy.deepcopy(pack)
        next(
            item for item in tampered["evidence"] if "selectors.pinned" in item["selected_by"]
        )["model_selection_reasons"] = ["invented"]
        tampered["fingerprint"] = _evidence_pack_fingerprint(tampered)
        with self.assertRaises(RetrievalSpecResolutionError) as tampered_error:
            validate_evidence_pack(tampered, root)
        self.assertEqual(tampered_error.exception.code, "invalid_pack")
        session = root / ".memory-seed" / "sessions" / "2026-08-01.md"
        session.write_text(session.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        with self.assertRaises(RetrievalSpecResolutionError) as stale_error:
            validate_evidence_pack(pack, root)
        self.assertEqual(stale_error.exception.code, "stale_pack")

        required_missing = copy.deepcopy(spec)
        required_missing["selectors"]["pinned"] = [{"kind": "decision", "id": "mse_missing:d1", "reason": "required"}]
        with self.assertRaises(RetrievalSpecResolutionError) as required_error:
            resolve_retrieval_spec(required_missing, root)
        self.assertEqual(required_error.exception.code, "missing_required")


if __name__ == "__main__":
    unittest.main()
