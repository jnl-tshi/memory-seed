import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from memory_seed.retrieval import (
    RetrievalSpecResolutionError,
    _evidence_pack_fingerprint,
    preview_retrieval_spec,
    resolve_retrieval_spec,
    validate_evidence_pack,
)
from memory_seed.retrieval_adapters import (
    preview_retrieval_input,
    resolve_retrieval_input_pack,
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
    retrieval_spec_fingerprint,
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

    def write_entry(self, root, entry_id, body, *, topics=(), filename="2026-08-01.md"):
        topic_lines = "topics:\n" + "".join(f"  - {topic}\n" for topic in topics) if topics else ""
        (root / ".memory-seed" / "sessions" / filename).write_text(
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
            "schema: memory-seed/retrieval-profile\nschema_version: 1\n"
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

    def test_multiple_parent_partial_specs_preserve_earlier_parent_clauses(self):
        root = self.make_project()
        self.write_profile(
            root,
            "first",
            self.profile(
                "first",
                "  filters:\n    topics:\n      - first-topic\n"
                "  required:\n    related_decisions:\n      depth: 3\n",
            ),
        )
        self.write_profile(
            root,
            "second",
            self.profile("second", "  limits:\n    max_entries: 30\n"),
        )
        self.write_profile(
            root,
            "child",
            self.profile(
                "child",
                "  optional:\n    sessions:\n      neighbouring_entries: 5\n",
                extends="\n  - id: first\n    profile_version: 1\n  - id: second\n    profile_version: 1",
            ),
        )
        resolved = load_retrieval_profile("child", 1, root)
        self.assertEqual(resolved["filters"]["topics"], ["first-topic"])
        self.assertEqual(resolved["required"]["related_decisions"]["depth"], 3)
        self.assertEqual(resolved["limits"]["max_entries"], 30)

    def test_multiple_parent_raw_list_operations_compose_in_order(self):
        root = self.make_project()
        self.write_profile(
            root,
            "first",
            self.profile(
                "first",
                "  filters:\n    topics:\n      append:\n        - alpha\n      remove: []\n",
            ),
        )
        self.write_profile(
            root,
            "second",
            self.profile(
                "second",
                "  filters:\n    topics:\n      append:\n        - beta\n      remove: []\n",
            ),
        )
        self.write_profile(
            root,
            "literal",
            self.profile("literal", "  filters:\n    paths:\n      - docs/old.md\n"),
        )
        self.write_profile(
            root,
            "child",
            self.profile(
                "child",
                "  filters:\n    topics:\n      append:\n        - child\n      remove:\n        - alpha\n"
                "    paths:\n      append:\n        - docs/new.md\n      remove:\n        - docs/old.md\n",
                extends=(
                    "\n  - id: first\n    profile_version: 1"
                    "\n  - id: second\n    profile_version: 1"
                    "\n  - id: literal\n    profile_version: 1"
                ),
            ),
        )
        resolved = load_retrieval_profile(
            "child",
            1,
            root,
            overrides={"filters": {"topics": {"append": ["dispatch"], "remove": ["beta"]}}},
        )
        self.assertEqual(resolved["filters"]["topics"], ["child", "dispatch"])
        self.assertEqual(resolved["filters"]["paths"], ["docs/new.md"])

    def test_required_pins_cannot_be_removed_by_child_or_dispatch_override(self):
        root = self.make_project()
        self.write_profile(
            root,
            "parent",
            self.profile(
                "parent",
                "  selectors:\n    pinned:\n      - kind: decision\n"
                "        id: mse_entry0001:d1\n"
                "        reason: inherited requirement\n",
            ),
        )
        self.write_profile(
            root,
            "child",
            self.profile(
                "child",
                "  selectors:\n    pinned: []\n",
                extends="\n  - id: parent\n    profile_version: 1",
            ),
        )
        with self.assertRaisesRegex(RetrievalProfileValidationError, "cannot remove required pinned"):
            load_retrieval_profile("child", 1, root)
        with self.assertRaisesRegex(RetrievalProfileValidationError, "cannot remove required pinned"):
            load_retrieval_profile(
                "parent",
                1,
                root,
                overrides={"selectors": {"pinned": []}},
            )

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

    def test_runtime_local_profile_and_adr_reads_reject_symlink_escapes(self):
        root = self.make_project()
        outside = Path(tempfile.mkdtemp(prefix="memory-seed-retrieval-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        external_profiles = outside / "profiles"
        external_profiles.mkdir()
        (external_profiles / "v1.yaml").write_text(
            self.profile("escape", "  limits:\n    max_entries: 2\n"),
            encoding="utf-8",
        )
        profile_link = root / ".memory-seed" / "retrieval-profiles" / "escape"
        profile_link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(external_profiles, profile_link, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable on this platform: {exc}")
        with self.assertRaisesRegex(RetrievalProfileValidationError, "outside the active runtime"):
            load_retrieval_profile("escape", 1, root)

        external_session = outside / "external.md"
        external_session.write_text("# externally linked session\n", encoding="utf-8")
        session_link = root / ".memory-seed" / "sessions" / "external.md"
        os.symlink(external_session, session_link)
        plain_spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
        }
        with self.assertRaises(RetrievalSpecResolutionError) as escaped_session:
            resolve_retrieval_spec(plain_spec, root)
        self.assertEqual(escaped_session.exception.code, "forbidden_path")
        session_link.unlink()

        external_adr = self.write_adr(outside, "adr_escape")
        adr_link = root / ".memory-seed" / "decisions" / "adr_escape.md"
        adr_link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(external_adr, adr_link)
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
            "selectors": {"pinned": [{"kind": "adr", "id": "adr_escape", "reason": "escape"}]},
        }
        with self.assertRaises(RetrievalSpecResolutionError) as escaped:
            resolve_retrieval_spec(spec, root)
        self.assertEqual(escaped.exception.code, "forbidden_path")

    def test_public_retrieval_paths_fail_closed_before_guarded_topic_read(self):
        """Exercise preview/resolve and both adapters without relying on symlink support."""
        root = self.make_project()
        topic_path = root / ".memory-seed" / "topics.yaml"
        topic_path.write_text("topics: {}\n", encoding="utf-8")
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
        }
        from memory_seed import retrieval as retrieval_module

        real_guard = retrieval_module._runtime_scoped_candidate_path

        def reject_topic(root_path, candidate, *, stage, details=None):
            if Path(candidate).resolve() == topic_path.resolve():
                raise RetrievalSpecResolutionError(
                    "forbidden_path", "mocked external topic source", stage=stage
                )
            return real_guard(root_path, candidate, stage=stage, details=details)

        public_calls = (
            ("preview_retrieval_spec", lambda: preview_retrieval_spec(spec, root)),
            ("resolve_retrieval_spec", lambda: resolve_retrieval_spec(spec, root)),
            ("preview_retrieval_input", lambda: preview_retrieval_input(spec=spec, cwd=root)),
            ("resolve_retrieval_input_pack", lambda: resolve_retrieval_input_pack(spec=spec, cwd=root)),
        )
        with patch("memory_seed.retrieval._runtime_scoped_candidate_path", side_effect=reject_topic), patch(
            "memory_seed.retrieval.extract_memory_chunks"
        ) as extract:
            # subTest's label must stay a plain string, not the callable itself - pytest-xdist
            # reports a subtest result by serializing its parameters back from the worker
            # process to the controller, and a bare function/lambda can't be pickled for that
            # trip (execnet.gateway_base.DumpError: can't serialize <class 'function'>). The
            # test passed either way; only the cross-process report of *which* subtest broke.
            for name, call in public_calls:
                with self.subTest(call=name), self.assertRaises(RetrievalSpecResolutionError) as raised:
                    call()
                self.assertEqual(raised.exception.code, "forbidden_path")
            extract.assert_not_called()

    def test_decision_only_pins_ignore_unrelated_malformed_adrs(self):
        root = self.make_project()
        bad = root / ".memory-seed" / "decisions" / "bad.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("# not an ADR\n", encoding="utf-8")
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
            "selectors": {"pinned": [{"kind": "decision", "id": "mse_entry0001:d1", "reason": "exact"}]},
        }
        self.assertTrue(validate_evidence_pack(resolve_retrieval_spec(spec, root), root)["valid"])

    def test_v2_rejects_non_entry_typed_decision_ids(self):
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
            "selectors": {"pinned": [{"kind": "decision", "id": "not-an-entry:d1", "reason": "invalid"}]},
        }
        with self.assertRaisesRegex(RetrievalSpecValidationError, "canonical '<entry-id>:dN'"):
            normalize_retrieval_spec_v2(spec)

    def test_optional_missing_and_tampered_v2_packs_fail_correctly(self):
        root = self.make_project()
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
            "selectors": {"pinned": [{"kind": "decision", "id": "mse_missing1:d1", "reason": "optional", "required": False}]},
        }
        spec["selectors"]["pinned"].append({"kind": "decision", "id": "mse_entry0001:d1", "reason": "required"})
        pack = resolve_retrieval_spec(spec, root)
        self.assertIn("mse_missing1:d1", [warning["detail"] for warning in pack["warnings"]])
        tampered = copy.deepcopy(pack)
        next(
            item for item in tampered["evidence"] if "selectors.pinned" in item["selected_by"]
        )["model_selection_reasons"] = ["invented"]
        tampered["fingerprint"] = _evidence_pack_fingerprint(tampered)
        with self.assertRaises(RetrievalSpecResolutionError) as tampered_error:
            validate_evidence_pack(tampered, root)
        self.assertEqual(tampered_error.exception.code, "invalid_pack")
        deleted_pin = copy.deepcopy(pack)
        deleted_pin["evidence"] = [
            item for item in deleted_pin["evidence"] if item["id"] != "mse_entry0001:d1"
        ]
        deleted_pin["fingerprint"] = _evidence_pack_fingerprint(deleted_pin)
        with self.assertRaises(RetrievalSpecResolutionError) as deleted_error:
            validate_evidence_pack(deleted_pin, root)
        self.assertEqual(deleted_error.exception.code, "invalid_pack")
        session = root / ".memory-seed" / "sessions" / "2026-08-01.md"
        session.write_text(session.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        with self.assertRaises(RetrievalSpecResolutionError) as stale_error:
            validate_evidence_pack(pack, root)
        self.assertEqual(stale_error.exception.code, "stale_pack")

        required_missing = copy.deepcopy(spec)
        required_missing["selectors"]["pinned"] = [{"kind": "decision", "id": "mse_missing1:d1", "reason": "required"}]
        with self.assertRaises(RetrievalSpecResolutionError) as required_error:
            resolve_retrieval_spec(required_missing, root)
        self.assertEqual(required_error.exception.code, "missing_required")

    def test_required_pin_defaults_true_for_recomputed_pack_membership(self):
        root = self.make_project()
        self.write_entry(
            root,
            "mse_entry0002",
            "### Decision\n\n- D: Optional evidence remains optional.\n",
            filename="2026-08-02.md",
        )
        spec = {
            "schema": "memory-seed/retrieval-spec",
            "version": 2,
            "required": {"constitution": True, "related_decisions": {"depth": 1}, "evidence": {"mode": "latest"}},
            "selectors": {"pinned": [
                {"kind": "decision", "id": "mse_entry0001:d1", "reason": "implicit required"},
                {"kind": "decision", "id": "mse_entry0002:d1", "reason": "optional", "required": False},
            ]},
        }
        pack = resolve_retrieval_spec(spec, root)

        retained_required = copy.deepcopy(pack)
        retained_required["effective_spec"]["selectors"]["pinned"][0].pop("required", None)
        retained_required["effective_spec_fingerprint"] = retrieval_spec_fingerprint(
            retained_required["effective_spec"]
        )
        retained_required["fingerprint"] = _evidence_pack_fingerprint(retained_required)
        self.assertTrue(validate_evidence_pack(retained_required, root)["valid"])

        deleted_required = copy.deepcopy(pack)
        deleted_required["effective_spec"]["selectors"]["pinned"][0].pop("required", None)
        deleted_required["effective_spec_fingerprint"] = retrieval_spec_fingerprint(
            deleted_required["effective_spec"]
        )
        deleted_required["evidence"] = [
            item for item in deleted_required["evidence"] if item["id"] != "mse_entry0001:d1"
        ]
        deleted_required["fingerprint"] = _evidence_pack_fingerprint(deleted_required)
        with self.assertRaises(RetrievalSpecResolutionError) as required_error:
            validate_evidence_pack(deleted_required, root)
        self.assertEqual(required_error.exception.code, "invalid_pack")

        deleted_optional = copy.deepcopy(pack)
        deleted_optional["evidence"] = [
            item for item in deleted_optional["evidence"] if item["id"] != "mse_entry0002:d1"
        ]
        deleted_optional["fingerprint"] = _evidence_pack_fingerprint(deleted_optional)
        self.assertTrue(validate_evidence_pack(deleted_optional, root)["valid"])


if __name__ == "__main__":
    unittest.main()
