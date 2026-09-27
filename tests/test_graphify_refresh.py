"""Project-scoped, warning-only Graphify merge refresh tests."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_seed import graphify_refresh as subject
from memory_seed.core import session_merge_branch


def git(root: Path, *args: str) -> None:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise AssertionError(completed.stderr)


class GraphifyRefreshTests(unittest.TestCase):
    def test_scope_covers_visible_project_code_and_documents(self):
        self.assertTrue(subject.selected("docs/2_Todo/plan.md"))
        for path in ("README.md", "experiments/pilot/README.md", "business/brief.md",
                     "demo/src/app.tsx", "memory_seed/core.py", "tests/test_core.py",
                     "pyproject.toml"):
            with self.subTest(path=path):
                self.assertTrue(subject.selected(path))
        for path in (
            ".memory-seed/sessions/2026-09/2026-09-25.md",
            ".memory-seed/decisions/adr.md",
            "demo/.memory-seed/index.md",
            "experiments/.cache/result.md",
            "graphify-out/GRAPH_REPORT.md",
            "experiments/results.json",
            "experiments/results.jsonl",
            "experiments/results.csv",
            "package-lock.json",
            "docs/image.png",
        ):
            with self.subTest(path=path):
                self.assertFalse(subject.selected(path))

    def test_disabled_project_is_inert(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual("disabled", subject.refresh_after_merge(root).status)
            self.assertEqual("disabled", subject.status(root).status)

    def test_missing_interpreter_warns_without_marking_fresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".memory-seed").mkdir()
            (root / ".memory-seed" / "project.yaml").write_text(
                "graphify_merge_refresh: true\n", encoding="utf-8"
            )
            git(root, "init", "-q")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "initial")
            with patch.object(subject, "_graphify_python", return_value=None):
                result = subject.refresh_after_merge(root)
            self.assertEqual("stale", result.status)
            self.assertIn("unavailable", result.warning or "")
            self.assertFalse((root / "graphify-out" / subject.STATE_NAME).exists())

    def test_query_refuses_stale_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".memory-seed").mkdir()
            (root / ".memory-seed" / "project.yaml").write_text(
                "graphify_merge_refresh: true\n", encoding="utf-8"
            )
            git(root, "init", "-q")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "initial")
            with patch.object(subject.Path, "cwd", return_value=root), patch.object(subject.shutil, "which", side_effect=AssertionError("query must not launch Graphify")):
                self.assertEqual(1, subject.main(["query", "Why?"]))

    def test_refresh_command_returns_after_success_without_query_question(self):
        with patch.object(subject.Path, "cwd", return_value=Path(".")), patch.object(
            subject, "refresh_after_merge", return_value=subject.RefreshResult("fresh", head="a" * 40)
        ), patch.object(subject.shutil, "which", side_effect=AssertionError("refresh must not query")):
            self.assertEqual(0, subject.main(["refresh"]))

    def test_committed_merge_surfaces_refresh_warning_without_rollback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".memory-seed" / "sessions").mkdir(parents=True)
            (root / ".memory-seed" / "project.yaml").write_text(
                "graphify_merge_refresh: true\n", encoding="utf-8"
            )
            git(root, "init", "-q")
            # merge-branch commits the merge itself; CI runners have no global identity.
            git(root, "config", "user.name", "Test")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "branch", "-M", "main")
            git(root, "add", ".")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base")
            git(root, "switch", "-qc", "feature")
            (root / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "feature")
            git(root, "switch", "-q", "main")
            with patch.object(subject, "refresh_after_merge", return_value=subject.RefreshResult("stale", warning="index unavailable")):
                result = session_merge_branch(root, branch="feature")
            self.assertTrue(result.committed, result.issues)
            self.assertEqual("stale", result.graphify_refresh_status)
            self.assertEqual(["index unavailable"], result.post_merge_warnings)
            self.assertEqual("main", subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip())

    def test_full_and_git_diff_incremental_refresh_with_stock_graphify(self):
        with tempfile.TemporaryDirectory(prefix="memory-seed-graphify-test-") as temporary:
            root = Path(temporary)
            if subject._graphify_python(root) is None:
                self.skipTest("optional Graphify installation unavailable")
            (root / ".memory-seed").mkdir()
            (root / ".memory-seed" / "project.yaml").write_text(
                "graphify_merge_refresh: true\n", encoding="utf-8"
            )
            (root / ".graphifyignore").write_text(
                (Path(__file__).resolve().parents[1] / "memory_seed" / "seed" / ".graphifyignore").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            docs = root / "docs"
            docs.mkdir()
            (root / "experiments").mkdir()
            (root / "experiments" / "notes.md").write_text("# Experiment notes\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "feature.py").write_text("def feature():\n    return 1\n", encoding="utf-8")
            (root / ".private").mkdir()
            (root / ".private" / "secret.md").write_text("# Excluded\n", encoding="utf-8")
            alpha = docs / "alpha.md"
            beta = docs / "beta.md"
            alpha.write_text("# Alpha\n\n[Beta](./beta.md)\n", encoding="utf-8")
            beta.write_text("# Beta\n", encoding="utf-8")
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial")

            first = subject.refresh_after_merge(root)
            self.assertEqual("fresh", first.status, first.warning)
            self.assertEqual("fresh", subject.status(root).status)
            graph = root / "graphify-out" / "graph.json"
            before = json.loads(graph.read_text(encoding="utf-8"))
            beta_nodes = [n for n in before["nodes"] if n.get("source_file") == "docs/beta.md"]
            self.assertTrue(beta_nodes)
            sources = {n.get("source_file") for n in before["nodes"]}
            self.assertIn("experiments/notes.md", sources)
            self.assertIn("src/feature.py", sources)
            self.assertNotIn(".private/secret.md", sources)

            alpha.write_text("# Alpha revised\n\n[Beta](./beta.md)\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "edit")
            self.assertEqual("stale", subject.status(root).status)
            second = subject.refresh_after_merge(root)
            self.assertEqual("fresh", second.status, second.warning)
            after = json.loads(graph.read_text(encoding="utf-8"))
            self.assertEqual(beta_nodes, [n for n in after["nodes"] if n.get("source_file") == "docs/beta.md"])
            links = after.get("links", after.get("edges", []))
            self.assertTrue(any(e.get("relation") == "references" and e.get("source_file") == "docs/alpha.md" for e in links))

            # Code changes are now part of the incremental selected diff.
            (root / "src" / "feature.py").write_text("def feature():\n    return 2\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "code-edit")
            code_edit = subject.refresh_after_merge(root)
            self.assertEqual("fresh", code_edit.status, code_edit.warning)
            self.assertIn("src/feature.py", {n.get("source_file") for n in json.loads(graph.read_text(encoding="utf-8"))["nodes"]})

            # A scope change rebuilds and removes now-excluded source nodes.
            with (root / ".graphifyignore").open("a", encoding="utf-8") as scope:
                scope.write("/experiments/\n")
            git(root, "add", ".")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "scope-change")
            scoped = subject.refresh_after_merge(root)
            self.assertEqual("fresh", scoped.status, scoped.warning)
            self.assertNotIn("experiments/notes.md", {n.get("source_file") for n in json.loads(graph.read_text(encoding="utf-8"))["nodes"]})

            # An unrelated merge moves HEAD but needs no Graphify extraction.
            (root / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "unrelated")
            with patch.object(subject, "_graphify_python", side_effect=AssertionError("must not run")):
                self.assertEqual("fresh", subject.refresh_after_merge(root).status)
            self.assertEqual("fresh", subject.status(root).status)

            beta.rename(docs / "gamma.md")
            alpha.write_text("# Alpha revised\n\n[Gamma](./gamma.md)\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "rename")
            renamed = subject.refresh_after_merge(root)
            self.assertEqual("fresh", renamed.status, renamed.warning)
            sources = {n.get("source_file") for n in json.loads(graph.read_text(encoding="utf-8"))["nodes"]}
            self.assertIn("docs/gamma.md", sources)
            self.assertNotIn("docs/beta.md", sources)

            alpha.unlink()
            git(root, "add", "-A")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "delete")
            deleted = subject.refresh_after_merge(root)
            self.assertEqual("fresh", deleted.status, deleted.warning)
            sources = {n.get("source_file") for n in json.loads(graph.read_text(encoding="utf-8"))["nodes"]}
            self.assertNotIn("docs/alpha.md", sources)

            previous_digest = subject._sha256(graph)
            (docs / "gamma.md").write_text("# Gamma changed\n", encoding="utf-8")
            self.assertEqual("stale", subject.status(root).status)
            git(root, "add", ".")
            git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fail-refresh")
            with patch.object(subject, "_graphify_python", return_value=None):
                failed = subject.refresh_after_merge(root)
            self.assertEqual("stale", failed.status)
            self.assertEqual(previous_digest, subject._sha256(graph))
            self.assertEqual("stale", subject.status(root).status)


if __name__ == "__main__":
    unittest.main()
