import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.docs_index import BEGIN, END, apply_docs_index, format_docs_index


class DocsIndexTests(unittest.TestCase):
    def make_docs(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-docsindex-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / "docs").mkdir()
        return root

    def write(self, root, rel, text):
        path = root / "docs" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_creates_readme_with_table_when_absent(self):
        root = self.make_docs()
        self.write(root, "2_Todo/a.md", "---\npriority: P1\nnext_action: build it\n---\n\n# A\n")

        result = apply_docs_index(root)

        text = (root / "docs" / "2_Todo" / "README.md").read_text(encoding="utf-8")
        self.assertIn(BEGIN, text)
        self.assertIn("[a.md](a.md) | P1", text)
        self.assertIn("build it", text)
        self.assertIn("docs/2_Todo/README.md", result.written)

    def test_hand_written_prose_outside_markers_survives_regeneration(self):
        root = self.make_docs()
        self.write(root, "2_Todo/a.md", "---\npriority: P1\nnext_action: x\n---\n\n# A\n")
        prose = "# Todo lane\n\nHand-written purpose paragraph that must survive.\n"
        self.write(root, "2_Todo/README.md", prose)

        apply_docs_index(root)
        first = (root / "docs" / "2_Todo" / "README.md").read_text(encoding="utf-8")
        # Regenerate after a change; the prose must still be there, once.
        self.write(root, "2_Todo/b.md", "---\npriority: P0\nnext_action: y\n---\n\n# B\n")
        apply_docs_index(root)
        second = (root / "docs" / "2_Todo" / "README.md").read_text(encoding="utf-8")

        for text in (first, second):
            self.assertIn("Hand-written purpose paragraph that must survive.", text)
        self.assertEqual(second.count(BEGIN), 1)
        self.assertEqual(second.count("Hand-written purpose"), 1)

    def test_todo_table_sorts_by_priority_then_name(self):
        root = self.make_docs()
        self.write(root, "2_Todo/zz.md", "---\npriority: P0\nnext_action: x\n---\n\n# Z\n")
        self.write(root, "2_Todo/aa.md", "---\npriority: P2\nnext_action: x\n---\n\n# A\n")

        apply_docs_index(root)

        text = (root / "docs" / "2_Todo" / "README.md").read_text(encoding="utf-8")
        self.assertLess(text.index("zz.md"), text.index("aa.md"))  # P0 outranks P2

    def test_lane_table_orders_case_insensitively_for_cross_platform_stability(self):
        # Path objects sort case-insensitively on Windows but case-sensitively on
        # Linux, so a lane with mixed-case filenames would generate a different
        # table order per platform and break `--check` on a Windows-author /
        # Linux-CI split. The generator must sort by a case-folded name key so
        # "Beta.md" lands BETWEEN alpha and gamma, not ASCII-first before both.
        root = self.make_docs()
        for name in ("alpha.md", "Beta.md", "gamma.md"):
            self.write(root, f"5_Completed/{name}", "---\ndate: 2026-07-17\n---\n\n# x\n")

        apply_docs_index(root)

        text = (root / "docs" / "5_Completed" / "README.md").read_text(encoding="utf-8")
        self.assertLess(text.index("alpha.md"), text.index("Beta.md"))
        self.assertLess(text.index("Beta.md"), text.index("gamma.md"))

    def test_apply_is_idempotent(self):
        root = self.make_docs()
        self.write(root, "2_Todo/a.md", "---\npriority: P1\nnext_action: x\n---\n\n# A\n")

        apply_docs_index(root)
        second = apply_docs_index(root)

        self.assertEqual(second.written, [])
        self.assertFalse(second.changed)
        self.assertIn("already current", format_docs_index(second, check=False))

    def test_check_reports_stale_without_writing(self):
        root = self.make_docs()
        self.write(root, "2_Todo/a.md", "---\npriority: P1\nnext_action: x\n---\n\n# A\n")
        apply_docs_index(root)
        # A new doc makes the generated table stale.
        self.write(root, "2_Todo/b.md", "---\npriority: P1\nnext_action: y\n---\n\n# B\n")
        before = (root / "docs" / "2_Todo" / "README.md").read_text(encoding="utf-8")

        result = apply_docs_index(root, check=True)

        self.assertIn("docs/2_Todo/README.md", result.stale)
        # check never writes.
        self.assertEqual(before, (root / "docs" / "2_Todo" / "README.md").read_text(encoding="utf-8"))
        self.assertIn("Stale generated index", format_docs_index(result, check=True))

    def test_front_door_counts_and_top_open_items(self):
        root = self.make_docs()
        self.write(root, "2_Todo/a.md", "---\npriority: P1\nnext_action: urgent thing\n---\n\n# A\n")
        self.write(root, "5_Completed/done.md", "# Done\n")
        self.write(root, "README.md", f"# Front door\n\n{BEGIN}\n{END}\n")

        apply_docs_index(root)

        text = (root / "docs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("2_Todo 1", text)
        self.assertIn("5_Completed 1", text)
        self.assertIn("urgent thing", text)  # P1 surfaces as a top open item
        self.assertIn("# Front door", text)  # prose intact

    def test_empty_lane_renders_placeholder_not_empty_table(self):
        root = self.make_docs()
        (root / "docs" / "6_Rejected").mkdir()

        apply_docs_index(root)

        text = (root / "docs" / "6_Rejected" / "README.md").read_text(encoding="utf-8")
        self.assertIn("no documents in this lane", text)

    def test_pipe_in_frontmatter_cannot_break_the_table(self):
        root = self.make_docs()
        self.write(
            root, "2_Todo/a.md", "---\npriority: P1\nnext_action: do x | then y\n---\n\n# A\n"
        )

        apply_docs_index(root)

        text = (root / "docs" / "2_Todo" / "README.md").read_text(encoding="utf-8")
        self.assertIn("do x \\| then y", text)


if __name__ == "__main__":
    unittest.main()
