"""Qualification tests for the Codex decision-edge fixture preparer."""

from __future__ import annotations

import json
import inspect
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[2]
sys.path.insert(0, str(PACKAGE_ROOT))

import common  # noqa: E402
import prepare  # noqa: E402

EXPECTED_TASK_SHA256 = "1d3410a92b96e89edda32506fa6418df970ba26bb4f733a845cf874e672beb35"


class PrepareStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="codex-decision-edge-v2-test-")
        cls.output_root = Path(cls.temporary.name) / "qualified-artifacts"
        cls.result = prepare.prepare_study(
            cls.output_root,
            seed=20260816,
            run_id="unit-qualification",
            repo_root=REPO_ROOT,
            blocks=1,
        )
        cls.public = json.loads((cls.output_root / "public-manifest.json").read_text(encoding="utf-8"))
        cls.sealed_path = cls.output_root / "sealed" / "condition-map.json"
        cls.sealed = json.loads(cls.sealed_path.read_text(encoding="utf-8"))
        cls.delta = json.loads(
            (cls.output_root / "sealed" / "treatment-deltas.json").read_text(encoding="utf-8")
        )
        cls.fixtures = {
            subject_id: Path(record["fixture_path"])
            for subject_id, record in cls.sealed["subjects"].items()
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_parent_relation_and_sample_shape(self) -> None:
        relationship = common.verify_source_relationship(REPO_ROOT)
        self.assertEqual(common.SOURCE_REVISION, relationship["withheld_parent"])
        self.assertEqual(3, self.result["fixture_count"])
        self.assertEqual(1, len(self.public["blocks"]))
        for block in self.public["blocks"]:
            subject_ids = block["subject_ids"]
            self.assertEqual(3, len(subject_ids))
            self.assertCountEqual(subject_ids, block["execution_order"])
            arms = [self.sealed["subjects"][subject_id]["arm"] for subject_id in subject_ids]
            self.assertCountEqual(common.ARMS, arms)

    def test_scored_default_is_eight_blocks_and_qualification_range_is_strict(self) -> None:
        parameter = inspect.signature(prepare.prepare_study).parameters["blocks"]
        self.assertEqual(common.BLOCK_COUNT, parameter.default)
        self.assertEqual(8, common.BLOCK_COUNT)
        for invalid in (0, 9, True, 1.5):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "blocks must be an integer"):
                    prepare.prepare_study(
                        Path(self.temporary.name) / f"invalid-{invalid}",
                        seed=1,
                        run_id="invalid-block-count",
                        repo_root=REPO_ROOT,
                        blocks=invalid,
                    )

    def test_sanitation_manifest_and_exact_comment_removal(self) -> None:
        fixture = next(iter(self.fixtures.values()))
        manifest = json.loads((fixture / "fixture-transformation.json").read_text(encoding="utf-8"))
        by_path = {item["path"]: item for item in manifest["transformations"]}
        deleted = by_path[common.REMOVED_DOCUMENT.as_posix()]
        comment = by_path[common.COMMENT_PATH.as_posix()]
        self.assertEqual("delete-file", deleted["action"])
        self.assertIsNone(deleted["transformed_sha256"])
        self.assertTrue(deleted["removed_lines"])
        self.assertFalse((fixture / common.REMOVED_DOCUMENT).exists())
        self.assertEqual("remove-exact-comment", comment["action"])
        self.assertEqual(5, len(comment["removed_lines"]))
        self.assertEqual(
            [
                common.sha256_bytes(line)
                for line in common.ANSWER_BEARING_COMMENT.splitlines(keepends=True)
            ],
            [record["sha256"] for record in comment["removed_lines"]],
        )
        transformed = fixture / common.COMMENT_PATH
        self.assertEqual(comment["transformed_sha256"], common.sha256_file(transformed))
        self.assertNotIn(common.ANSWER_BEARING_COMMENT, transformed.read_bytes())

    def test_project_agent_configs_are_removed_and_local_contract_is_explicit(self) -> None:
        for fixture in self.fixtures.values():
            common.assert_no_active_project_agent_config(fixture)
            for surface in common.PROJECT_AGENT_CONFIG_SURFACES:
                self.assertFalse((fixture / surface).exists(), surface.as_posix())
            contract = (fixture / common.CODEX_CONTRACT_PATH).read_text(encoding="utf-8")
            normalized_contract = " ".join(contract.split())
            self.assertIn("project-level agent configuration surfaces are removed", contract)
            self.assertIn("cannot programmatically disable", contract)
            self.assertIn("user-level tool inventory or connectors", normalized_contract)
            self.assertIn("external or cross-fixture tool use is an exclusion", normalized_contract)
            manifest = json.loads(
                (fixture / "fixture-transformation.json").read_text(encoding="utf-8")
            )
            actions = {item["path"]: item["action"] for item in manifest["transformations"]}
            deleted = [
                item
                for item in manifest["transformations"]
                if item["action"] == "delete-project-agent-surface-file"
            ]
            self.assertTrue(deleted)
            self.assertTrue(all(item["original_sha256"] for item in deleted))
            self.assertTrue(all(item["transformed_sha256"] is None for item in deleted))
            self.assertIn(".mcp.json", actions)
            self.assertIn(".codex/config.toml", actions)
            self.assertIn(".claude/launch.json", actions)
            self.assertIn(".github/mcp.json", actions)
            self.assertIn(".github/hooks/memory-seed.json", actions)
            self.assertIn(".github/copilot-instructions.md", actions)
            audit = manifest["agent_surface_audit"]
            self.assertEqual(
                {surface.as_posix() for surface in common.PROJECT_AGENT_CONFIG_SURFACES},
                set(audit["declared_removed_surfaces"]),
            )
            inert = {
                item["path"]: item["classification"]
                for item in audit["remaining_inert_source_or_template_matches"]
            }
            self.assertEqual(common.INERT_SOURCE_AGENT_NAME_MATCHES, inert)
            self.assertTrue(all((fixture / path).is_file() for path in inert))
            self.assertEqual(
                "add-fixture-local-agent-contract",
                actions[common.CODEX_CONTRACT_PATH.as_posix()],
            )

    def test_unknown_project_agent_config_files_fail_structurally(self) -> None:
        fixture = next(iter(self.fixtures.values()))
        adversaries = (
            (
                fixture / ".codex" / "rogue.toml",
                "[mcp_servers.bad]\ncommand='python'\n",
                fixture / ".codex",
            ),
            (fixture / ".vscode" / "anything.xyz", "opaque\n", fixture / ".vscode"),
            (fixture / ".github" / "mcp.json", "{}\n", fixture / ".github" / "mcp.json"),
            (
                fixture / ".github" / "hooks" / "unknown.xyz",
                "opaque\n",
                fixture / ".github" / "hooks",
            ),
        )
        for path, content, surface in adversaries:
            with self.subTest(path=path.relative_to(fixture).as_posix()):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
                try:
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "active project agent configuration survived isolation",
                    ):
                        common.assert_no_active_project_agent_config(fixture)
                finally:
                    if surface.is_dir():
                        shutil.rmtree(surface)
                    else:
                        surface.unlink(missing_ok=True)
        common.assert_no_active_project_agent_config(fixture)
        self.assertEqual(b"", common.run(["git", "status", "--porcelain"], cwd=fixture).stdout)

    def test_arm_session_counts_and_context_exposure(self) -> None:
        historical_counts: list[int] = []
        context_bytes: list[bytes] = []
        for subject_id, fixture in self.fixtures.items():
            record = self.sealed["subjects"][subject_id]
            arm = record["arm"]
            count = len(common.dated_session_documents(fixture))
            context = (fixture / "EXPERIMENT_CONTEXT.md").read_text(encoding="utf-8")
            context_bytes.append((fixture / "EXPERIMENT_CONTEXT.md").read_bytes())
            if arm == "historical-available":
                historical_counts.append(count)
                self.assertNotIn(common.DECISIVE_PHRASE, context)
            elif arm == "no-dated-memory":
                self.assertEqual(0, count)
                self.assertNotIn(common.DECISIVE_PHRASE, context)
                common.assert_no_decisive_phrase(fixture)
            else:
                self.assertEqual(0, count)
                self.assertIn(common.DECISIVE_PHRASE, context)
                self.assertIn(f"{common.RELEVANT_ENTRY_ID}:d2", context)
        self.assertTrue(historical_counts)
        self.assertTrue(all(count > 0 for count in historical_counts))
        self.assertEqual(1, len({len(payload) for payload in context_bytes}))
        self.assertEqual(1, len({len(payload.decode("utf-8").split()) for payload in context_bytes}))
        self.assertEqual(0, self.sealed["context_balance"]["byte_difference"])
        self.assertEqual(0, self.sealed["context_balance"]["whitespace_token_difference"])
        neutral = prepare.NEUTRAL_CONTEXT_BODY.lower()
        for forbidden in (
            common.RELEVANT_ENTRY_ID,
            "decision",
            "supersedes",
            "rationale",
            "edge",
        ):
            self.assertNotIn(forbidden, neutral)

    def test_task_is_byte_identical_everywhere(self) -> None:
        expected = common.TASK_PATH.read_bytes()
        self.assertEqual(EXPECTED_TASK_SHA256, common.sha256_bytes(expected))
        for fixture in self.fixtures.values():
            self.assertEqual(expected, (fixture / "TASK.md").read_bytes())

    def test_mapping_is_sealed_and_public_manifest_has_no_conditions(self) -> None:
        serialized_public = json.dumps(self.public, sort_keys=True)
        for arm in common.ARMS:
            self.assertNotIn(arm, serialized_public)
        subjects_root = (self.output_root / "subjects").resolve()
        self.assertNotEqual(subjects_root, self.sealed_path.parent.resolve())
        self.assertFalse(subjects_root in self.sealed_path.resolve().parents)
        for subject_id, fixture in self.fixtures.items():
            self.assertRegex(subject_id, r"^subject-[0-9a-f]{16}$")
            self.assertEqual(subject_id, fixture.name)
            self.assertFalse((fixture / "sealed").exists())

    def test_objects_are_isolated_and_fixtures_start_pristine(self) -> None:
        for fixture in self.fixtures.values():
            common.assert_object_isolation(fixture)
            status = common.run(["git", "status", "--porcelain"], cwd=fixture).stdout
            self.assertEqual(b"", status)
            withheld = common.run(
                ["git", "cat-file", "-e", f"{common.WITHHELD_REVISION}^{{commit}}"],
                cwd=fixture,
                check=False,
            )
            self.assertNotEqual(0, withheld.returncode)

    def test_neutral_file_mutation_is_detected(self) -> None:
        paths = list(self.fixtures.values())
        allowed = self.delta["allowed_treatment_paths"]
        common.assert_cross_arm_equality(paths, allowed_treatment_paths=allowed)
        target = paths[-1] / ".memory-seed" / "sessions" / ".gitkeep"
        original = target.read_bytes()
        try:
            target.write_bytes(original + b"unexpected control mutation\n")
            with self.assertRaisesRegex(RuntimeError, "unexpected cross-arm difference"):
                common.assert_cross_arm_equality(paths, allowed_treatment_paths=allowed)
        finally:
            target.write_bytes(original)
        unexpected = paths[-1] / ".memory-seed" / "sessions" / "unexpected-control.txt"
        try:
            unexpected.write_text("unexpected\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unexpected cross-arm difference"):
                common.assert_cross_arm_equality(paths, allowed_treatment_paths=allowed)
        finally:
            unexpected.unlink(missing_ok=True)
        common.assert_cross_arm_equality(paths, allowed_treatment_paths=allowed)

    def test_treatment_delta_manifest_names_only_baseline_paths(self) -> None:
        allowed = set(self.delta["allowed_treatment_paths"])
        self.assertIn("EXPERIMENT_CONTEXT.md", allowed)
        baseline = set(self.delta["baseline_session_markdown_sha256"])
        self.assertEqual({"EXPERIMENT_CONTEXT.md", *baseline}, allowed)
        self.assertNotIn(".memory-seed/sessions/.gitkeep", allowed)
        for subject_id, record in self.delta["subjects"].items():
            arm = self.sealed["subjects"][subject_id]["arm"]
            removed = set(record["removed_session_markdown_paths"])
            retained = set(record["retained_session_markdown_paths"])
            if arm == "historical-available":
                self.assertEqual(set(), removed)
                self.assertEqual(baseline, retained)
            else:
                self.assertEqual(baseline, removed)
                self.assertEqual(set(), retained)

    def test_candidate_validation_command_has_qualified_missing_module_boundary(self) -> None:
        fixture = next(iter(self.fixtures.values()))
        module = fixture / "memory-trace" / "tests" / "test_trail_decision_edges.py"
        self.assertFalse(module.exists())
        command = [sys.executable, "-m", "unittest", "memory-trace/tests/test_trail_decision_edges.py"]
        pristine = common.run(command, cwd=fixture, check=False)
        output = (pristine.stdout + pristine.stderr).decode("utf-8", errors="replace")
        self.assertNotEqual(0, pristine.returncode)
        self.assertIn("test_trail_decision_edges", output)
        self.assertTrue("Failed to import" in output or "No module named" in output)
        module.write_text(
            "import unittest\n\n"
            "class CommandSurfaceQualification(unittest.TestCase):\n"
            "    def test_surface(self):\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
            newline="\n",
        )
        try:
            qualified = common.run(command, cwd=fixture, check=False)
            self.assertEqual(
                0,
                qualified.returncode,
                (qualified.stdout + qualified.stderr).decode("utf-8", errors="replace"),
            )
        finally:
            module.unlink(missing_ok=True)
        self.assertEqual(b"", common.run(["git", "status", "--porcelain"], cwd=fixture).stdout)

    def test_withheld_object_contamination_control_fails(self) -> None:
        source_fixture = next(iter(self.fixtures.values()))
        contaminated = Path(self.temporary.name) / "contaminated-object-control"
        contaminated.mkdir()
        shutil.copytree(source_fixture / ".git", contaminated / ".git")
        withheld_commit_bytes = common.run(
            ["git", "cat-file", "commit", common.WITHHELD_REVISION],
            cwd=REPO_ROOT,
        ).stdout
        imported = common.run(
            ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
            cwd=contaminated,
            input_bytes=withheld_commit_bytes,
        ).stdout.decode("ascii").strip()
        self.assertEqual(common.WITHHELD_REVISION, imported)
        with self.assertRaisesRegex(RuntimeError, "historical object unexpectedly resolves"):
            common.assert_object_isolation(contaminated)

    def test_existing_output_root_is_refused(self) -> None:
        with self.assertRaises(FileExistsError):
            prepare.prepare_study(
                self.output_root,
                seed=1,
                run_id="must-refuse",
                repo_root=REPO_ROOT,
            )

    def test_artifact_hash_index_matches(self) -> None:
        index = json.loads((self.output_root / "artifact-sha256.json").read_text(encoding="utf-8"))
        for relative, expected in index["files"].items():
            self.assertEqual(expected, common.sha256_file(self.output_root / relative))


if __name__ == "__main__":
    unittest.main()
