"""Git adapter checks for reference-only progressive provenance."""

from __future__ import annotations

import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.provenance_git import (
    derive_commit_bindings,
    parse_memory_implements,
    project_binding,
    resolve_attribution,
    verify_binding_git,
)


DECISION_A = "mse_abcd1234:d1"
DECISION_B = "mse_dcba4321:d1"
AUTHORSHIP = {"provenance": "first-hand", "actor": {"kind": "agent", "id": "codex"}}


class ProvenanceEngineTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="memory-seed-provenance-git-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        self.git(root, "init", "-q")
        self.git(root, "config", "user.name", "Test")
        self.git(root, "config", "user.email", "test@example.invalid")
        return root

    def git(self, cwd: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
        )
        return completed.stdout.strip()

    def commit(self, cwd: Path, path: str, text: str, message: str) -> str:
        destination = cwd / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        self.git(cwd, "add", "-A")
        self.git(cwd, "commit", "-q", "-m", message)
        return self.git(cwd, "rev-parse", "HEAD")

    def test_resolution_uses_explicit_then_exact_f_path_then_unique_only(self):
        result = resolve_attribution(
            ["memory_seed/provenance_git.py", "memory_seed/provenance.py"],
            [
                {"decision_ref": DECISION_A, "files": ["memory_seed/provenance_git.py"]},
                {"decision_ref": DECISION_B, "files": ["memory_seed/provenance_git.py"]},
            ],
        )
        self.assertEqual(result["automatic"], [])
        self.assertEqual(result["shared"], [{"file": "memory_seed/provenance_git.py", "decision_refs": [DECISION_A, DECISION_B]}])
        self.assertEqual(result["unmatched"], ["memory_seed/provenance.py"])

        explicit = resolve_attribution(
            ["memory_seed/provenance_git.py"],
            [
                {"decision_ref": DECISION_A, "files": ["memory_seed/provenance_git.py"]},
                {"decision_ref": DECISION_B, "files": ["memory_seed/provenance_git.py"]},
            ],
            memory_implements=[DECISION_A],
        )
        self.assertEqual(explicit["automatic"], [{"file": "memory_seed/provenance_git.py", "decision_ref": DECISION_A}])
        self.assertEqual(explicit["shared"], [])
        self.assertEqual(parse_memory_implements("work\n\nMemory-Implements: " + DECISION_A + ", " + DECISION_B), [DECISION_A, DECISION_B])

    def test_derivation_verification_and_bounded_projection_keep_only_references(self):
        repo = self.make_repo()
        self.commit(repo, "pkg/example.py", "one\ntwo\nthree\n", "initial")
        head = self.commit(
            repo,
            "pkg/example.py",
            "one\nTWO\nthree\nfour\n",
            "implement\n\nMemory-Implements: " + DECISION_A,
        )
        result = derive_commit_bindings(
            repo,
            head,
            [{"decision_ref": DECISION_A, "files": ["pkg/example.py"]}],
            authorship=AUTHORSHIP,
        )
        self.assertEqual(result["mode"], "derived")
        binding = result["bindings"][0]
        self.assertNotIn("patch", binding)
        self.assertTrue(binding["hunks"][0]["patch_bytes"]["digest"].startswith("sha256:"))
        self.assertEqual(verify_binding_git(binding, repo)["evidence_state"], "available")

        projection = project_binding(binding, repo, before=1, after=1, reason="why")
        self.assertTrue(projection["code_available"])
        self.assertEqual(projection["reason"], "why")
        self.assertEqual(projection["context"], {"before": 1, "after": 1})
        self.assertTrue(any(line["text"] == "TWO" for line in projection["hunks"][0]["after"]["lines"]))
        with self.assertRaises(ValueError):
            project_binding(binding, repo, before=21)

        tampered = copy.deepcopy(binding)
        tampered["hunks"][0]["patch_bytes"]["digest"] = "sha256:" + "0" * 64
        self.assertFalse(verify_binding_git(tampered, repo)["verified"])

    def test_git_unavailable_projection_has_explicit_no_code_state(self):
        repo = self.make_repo()
        head = self.commit(repo, "example.py", "one\n", "implement\n\nMemory-Implements: " + DECISION_A)
        binding = derive_commit_bindings(
            repo, head, [{"decision_ref": DECISION_A, "files": ["example.py"]}], authorship=AUTHORSHIP
        )["bindings"][0]
        nowhere = Path(tempfile.mkdtemp(prefix="memory-seed-no-git-"))
        self.addCleanup(lambda: shutil.rmtree(nowhere, ignore_errors=True))
        projection = project_binding(binding, nowhere)
        self.assertFalse(projection["code_available"])
        self.assertEqual(projection["verification"]["evidence_state"], "git-unavailable")

    def test_merge_is_integration_only_and_never_derives_combined_hunks(self):
        repo = self.make_repo()
        self.commit(repo, "base.txt", "base\n", "initial")
        self.git(repo, "switch", "-q", "-c", "topic")
        self.commit(repo, "topic.txt", "topic\n", "topic")
        self.git(repo, "switch", "-q", "master")
        self.commit(repo, "main.txt", "main\n", "main")
        self.git(repo, "merge", "--no-ff", "-q", "topic", "-m", "integration")
        merge = self.git(repo, "rev-parse", "HEAD")
        result = derive_commit_bindings(
            repo, merge, [{"decision_ref": DECISION_A, "files": ["topic.txt"]}], authorship=AUTHORSHIP
        )
        self.assertEqual(result["mode"], "integration-only")
        self.assertEqual(result["bindings"], [])


if __name__ == "__main__":
    unittest.main()
