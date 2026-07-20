import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.docs_check import check_docs, format_docs_check


class DocsCheckTests(unittest.TestCase):
    def make_docs(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-docscheck-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / "docs").mkdir()
        return root

    def write(self, root, rel, text):
        path = root / "docs" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def kinds(self, result):
        return {i.kind for i in result.issues}

    def test_clean_tree_is_ok(self):
        root = self.make_docs()
        self.write(root, "2_Todo/a.md", "---\npriority: P1\nnext_action: do it\n---\n\n# A\n")

        result = check_docs(root)

        self.assertTrue(result.ok)
        self.assertEqual(result.issues, ())
        self.assertIn("Docs lifecycle OK", format_docs_check(result))

    def test_broken_relative_link_is_an_error(self):
        root = self.make_docs()
        self.write(
            root,
            "2_Todo/a.md",
            "---\npriority: P1\nnext_action: x\n---\n\n[gone](../5_Completed/missing.md)\n",
        )

        result = check_docs(root)

        # This is the gate the 43-doc lane migration had to hand-roll.
        self.assertFalse(result.ok)
        self.assertIn("broken-link", self.kinds(result))

    def test_resolving_link_and_external_url_are_not_flagged(self):
        root = self.make_docs()
        self.write(root, "5_Completed/target.md", "# T\n")
        self.write(
            root,
            "2_Todo/a.md",
            "---\npriority: P1\nnext_action: x\n---\n\n"
            "[ok](../5_Completed/target.md) [web](https://example.com) [anchor](#s)\n",
        )

        self.assertTrue(check_docs(root).ok)

    def test_link_with_anchor_and_encoded_space_resolves(self):
        root = self.make_docs()
        self.write(root, "5_Completed/two words.md", "# T\n")
        self.write(
            root,
            "2_Todo/a.md",
            "---\npriority: P1\nnext_action: x\n---\n\n"
            "[ok](../5_Completed/two%20words.md#section)\n",
        )

        self.assertTrue(check_docs(root).ok)

    def test_missing_todo_yaml_warns_but_does_not_fail(self):
        root = self.make_docs()
        self.write(root, "2_Todo/a.md", "# A with no frontmatter\n")

        result = check_docs(root)

        # Backfilling secondary YAML is separate, still-open work: failing here
        # would keep the check red for a known-unfinished task.
        self.assertTrue(result.ok)
        self.assertIn("missing-todo-yaml", self.kinds(result))
        self.assertEqual(len(result.errors), 0)

    def test_superseded_without_pointer_warns(self):
        root = self.make_docs()
        self.write(root, "7_Superseded/old.md", "---\ntitle: old\n---\n\n# Old\n")

        result = check_docs(root)

        self.assertTrue(result.ok)
        self.assertIn("missing-superseded-by", self.kinds(result))

    def test_dangling_superseded_by_pointer_is_an_error(self):
        root = self.make_docs()
        self.write(
            root,
            "7_Superseded/old.md",
            "---\nsuperseded_by: 2_Todo/nonexistent.md\n---\n\n# Old\n",
        )

        result = check_docs(root)

        self.assertFalse(result.ok)
        self.assertIn("dangling-pointer", self.kinds(result))

    def test_resolving_superseded_by_pointer_is_clean(self):
        root = self.make_docs()
        self.write(root, "2_Todo/new.md", "---\npriority: P1\nnext_action: x\n---\n\n# New\n")
        self.write(root, "7_Superseded/old.md", "---\nsuperseded_by: 2_Todo/new.md\n---\n\n# Old\n")

        result = check_docs(root)

        self.assertTrue(result.ok)
        self.assertNotIn("dangling-pointer", self.kinds(result))

    def test_entry_id_pointer_is_not_treated_as_a_path(self):
        root = self.make_docs()
        self.write(root, "7_Superseded/old.md", "---\nsuperseded_by: mse_abc123\n---\n\n# Old\n")

        result = check_docs(root)

        # Entry-id pointers are links check's job, not a file path to resolve.
        self.assertTrue(result.ok)
        self.assertNotIn("dangling-pointer", self.kinds(result))

    def test_spec_binding_must_agree_with_its_subfolder(self):
        root = self.make_docs()
        self.write(root, "3_Spec/draft/c.md", "---\nspec_binding: live\n---\n\n# C\n")

        result = check_docs(root)

        # A draft claiming to be live is the folder-vs-field contradiction the
        # lane system exists to make impossible.
        self.assertFalse(result.ok)
        self.assertIn("spec-binding-mismatch", self.kinds(result))

    def test_spec_binding_agreeing_with_folder_is_clean(self):
        root = self.make_docs()
        self.write(root, "3_Spec/draft/c.md", "---\nspec_binding: draft\n---\n\n# C\n")
        self.write(root, "3_Spec/live.md", "---\nspec_binding: live\n---\n\n# L\n")

        self.assertTrue(check_docs(root).ok)

    def test_off_allowlist_nested_folder_is_flagged(self):
        root = self.make_docs()
        self.write(root, "2_Todo/scratch/x.md", "---\npriority: P1\nnext_action: x\n---\n\n# X\n")

        result = check_docs(root)

        self.assertIn("off-allowlist-folder", self.kinds(result))

    def test_allowlisted_nested_folder_is_not_flagged(self):
        root = self.make_docs()
        self.write(root, "5_Completed/agent-templates/dev.md", "# Dev\n")

        self.assertNotIn("off-allowlist-folder", self.kinds(check_docs(root)))

    def test_allowlisted_reference_design_group_is_not_flagged(self):
        root = self.make_docs()
        self.write(root, "4_Reference/trace-humanised-dashboard-references/README.md", "# References\n")

        self.assertNotIn("off-allowlist-folder", self.kinds(check_docs(root)))

    def test_lane_readme_is_not_a_lifecycle_document(self):
        root = self.make_docs()
        self.write(root, "2_Todo/README.md", "# Todo lane\n")

        # A lane index has no priority/next_action and must not be nagged for it.
        self.assertEqual(check_docs(root).issues, ())

    def test_missing_docs_dir_is_not_an_error(self):
        root = Path(tempfile.mkdtemp(prefix="memory-seed-docscheck-none-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        result = check_docs(root)

        self.assertTrue(result.ok)
        self.assertEqual(result.files_checked, 0)
        self.assertIn("No docs/", format_docs_check(result))

    def test_check_writes_nothing(self):
        root = self.make_docs()
        self.write(root, "2_Todo/a.md", "---\npriority: P1\nnext_action: x\n---\n\n# A\n")
        before = sorted(p.name for p in root.rglob("*"))

        check_docs(root)

        self.assertEqual(before, sorted(p.name for p in root.rglob("*")))


if __name__ == "__main__":
    unittest.main()
