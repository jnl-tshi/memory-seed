import shutil
import tempfile
import unittest
import pytest
from pathlib import Path

from _git_helpers import run_git
from memory_seed.core import (
    MEMORY_DIR_NAME,
    check_session_links,
    session_fuse,
    session_merge_branch,
    session_open_pr,
    session_prepare_pr_branch,
)


class SessionFuseAndMergeTests(unittest.TestCase):
    NO_MERGE_ATTR = ".memory-seed/sessions/** -merge\n"

    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _git(self, cwd, *args):
        return run_git(cwd, *args, check=True)

    def _init_git_project(self, cwd):
        self._git(cwd, "init", "-q")
        self._git(cwd, "config", "user.name", "Test User")
        self._git(cwd, "config", "user.email", "test@example.com")
        self._git(cwd, "config", "commit.gpgsign", "false")
        self._git(cwd, "branch", "-M", "main")

    def _commit_all(self, cwd, message):
        self._git(cwd, "add", "-A")
        self._git(cwd, "commit", "-q", "-m", message)

    def _write_grouped_session(self, cwd, date, entry_id, *, branch, title="Entry", time="09:00", body="- Body."):
        path = cwd / MEMORY_DIR_NAME / "sessions" / date[:7] / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log",
                    "  - memory-seed",
                    f"session_date: {date}",
                    "---",
                    "",
                    f"## {date} {time} - {title}",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "user_initials: JN",
                    "agent_type: codex",
                    f"branch: {branch}",
                    "```",
                    "",
                    body,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def _write_legacy_session(self, cwd, date, entry_id, *, branch, title="Entry", time="09:00"):
        path = cwd / MEMORY_DIR_NAME / "sessions" / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log",
                    "  - memory-seed",
                    f"session_date: {date}",
                    "---",
                    "",
                    f"## {date} {time} - {title}",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "user_initials: JN",
                    "agent_type: codex",
                    f"branch: {branch}",
                    "```",
                    "",
                    "- Branch body.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def _write_legacy_diagram(self, cwd, date, entry_id, title="Entry"):
        path = cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "---",
                    "tags:",
                    "  - session-log-diagrams",
                    f"diagram_date: {date}",
                    "---",
                    "",
                    f"## {date} 09:00 - {title}",
                    "",
                    "```yaml",
                    f"entry_id: {entry_id}",
                    "```",
                    "",
                    "```mermaid",
                    "graph TD",
                    "  A[Branch] --> B[Main]",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def _link_sidecar_text(self, date, blocks):
        """Build link-sidecar file text, mirroring `_grouped_session_text`.

        Each block is ``(time, title, entry_id, extra_yaml_lines)`` where
        ``extra_yaml_lines`` is a list of raw lines placed inside the fenced
        yaml block after ``entry_id:`` (e.g. ``["supersedes:", "  - mse_..."]``
        or ``["classify_pending: true"]``).
        """
        lines = [
            "---",
            "tags:",
            "  - session-log-links",
            f"link_date: {date}",
            "---",
            "",
        ]
        for time, title, entry_id, extra_yaml_lines in blocks:
            lines += [
                f"## {date} {time} - {title}",
                "",
                "```yaml",
                f"entry_id: {entry_id}",
            ] + list(extra_yaml_lines) + [
                "```",
                "",
            ]
        return "\n".join(lines)

    def _grouped_session_text(self, date, entries):
        lines = [
            "---",
            "tags:",
            "  - session-log",
            "  - memory-seed",
            f"session_date: {date}",
            "---",
            "",
        ]
        for time, title, entry_id, branch in entries:
            lines += [
                f"## {date} {time} - {title}",
                "",
                "```yaml",
                f"entry_id: {entry_id}",
                "user_initials: JN",
                "agent_type: codex",
                f"branch: {branch}",
                "```",
                "",
                f"- Body for {title}.",
                "",
            ]
        return "\n".join(lines)

    def _concurrent_session_branches(self, cwd, *, gitattributes=None):
        """Base and branch both append to one dated file after a shared
        ancestor - the shape that produced the 2026-07-19 corruption. Returns
        the target path, with `main` checked out and `feature-merge` ready."""
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Later main entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-merge")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        if gitattributes is not None:
            (cwd / ".gitattributes").write_text(gitattributes, encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")
        self._git(cwd, "switch", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "main appends 10:00")
        return target

    def _false_anchor_branches(self, cwd, *, gitattributes=None):
        """The 2026-07-19 corruption shape: two entries whose `topics:` /
        `related_entries:` scaffolding is byte-identical, appended concurrently.
        Those shared lines are what git anchors on."""
        def entry(time, title, eid):
            return (
                f"## 2026-07-19 {time} - {title}\n\n"
                f"```yaml\nentry_id: mse_{eid}\n"
                "topics:\n  - memory-trace\n  - ui-design\n"
                "related_entries:\n  - mse_zzzzzzzzzzzzzzzz\n```\n\n"
                f"### Decision\n\n- D: {title}\n- R: {title}\n\n"
            )

        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-19.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        base = entry("09:00", "Base", "a" * 16)
        target.write_text(base, encoding="utf-8")
        if gitattributes is not None:
            (cwd / ".gitattributes").write_text(gitattributes, encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target.write_text(base + entry("11:33", "BranchOne", "c" * 16), encoding="utf-8")
        self._commit_all(cwd, "branch appends 11:33")
        self._git(cwd, "switch", "main")
        target.write_text(base + entry("12:02", "MainOne", "b" * 16), encoding="utf-8")
        self._commit_all(cwd, "main appends 12:02")
        return target

    @pytest.mark.integration
    def test_session_fuse_dry_run_reports_branch_only_entries_without_writing(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertEqual(result.issues, [])
        self.assertEqual(
            result.planned_entries,
            ["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
        )
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md").exists())

    @pytest.mark.integration
    def test_session_fuse_treats_h2_heading_in_body_as_content_not_an_entry(self):
        # Regression for the divergent entry-grammar incident: `session append`
        # accepted a body containing an `## Summary` heading, but the fuse path
        # (via the old broad `^##` boundary regex) split it into a phantom
        # ID-less entry and blocked the merge. One strict timestamped grammar
        # now governs both, so the heading is body content.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_grouped_session(
            cwd,
            "2026-07-11",
            "mse_1111111111111111",
            branch="feature-fuse",
            body="- Body.\n\n## Summary\n\nAn h2 heading inside the body, not a new entry.",
        )
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        # Exactly one planned entry; no phantom ID-less record, no blocking issue.
        self.assertEqual(result.issues, [])
        self.assertEqual(len(result.planned_entries), 1)
        self.assertIn("mse_1111111111111111", result.planned_entries[0])

    @pytest.mark.integration
    def test_session_fuse_apply_requires_in_progress_merge(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse", apply=True)

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("in-progress git merge", result.issues[0])

    @pytest.mark.integration
    def test_session_fuse_apply_normalizes_paths_and_imports_sidecars(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        self._write_legacy_diagram(cwd, "2026-07-11", "mse_1111111111111111")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")
        self._git(cwd, "merge", "--no-ff", "--no-commit", "feature-fuse")

        result = session_fuse(cwd=cwd, branch="feature-fuse", apply=True)

        self.assertTrue(result.changed)
        self.assertEqual(result.issues, [])
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-07-11.md").exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / "2026-07-11.md").exists())
        grouped = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md"
        grouped_diagram = cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / "2026-07" / "2026-07-11.md"
        self.assertIn("entry_id: mse_1111111111111111", grouped.read_text(encoding="utf-8"))
        self.assertIn("branch: feature-fuse", grouped.read_text(encoding="utf-8"))
        self.assertIn("```mermaid", grouped_diagram.read_text(encoding="utf-8"))
        self.assertTrue(check_session_links(cwd=cwd).ok)

    @pytest.mark.integration
    def test_session_fuse_apply_separates_entries_with_one_blank_line(self):
        # Regression: the chronological rewriter used to join rstripped entries
        # with a single "\n", butting each "## " heading against the previous
        # entry's last line and wrecking the log's readability on every fuse.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-10.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            self._grouped_session_text("2026-07-10", [("09:00", "Base", "mse_aaaaaaaaaaaaaaaa", "main")]),
            encoding="utf-8",
        )
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        target.write_text(
            self._grouped_session_text(
                "2026-07-10",
                [
                    ("09:00", "Base", "mse_aaaaaaaaaaaaaaaa", "main"),
                    ("10:00", "Branch entry", "mse_bbbbbbbbbbbbbbbb", "feature-fuse"),
                ],
            ),
            encoding="utf-8",
        )
        self._commit_all(cwd, "branch appends")
        self._git(cwd, "switch", "main")
        self._git(cwd, "merge", "--no-ff", "--no-commit", "feature-fuse")

        result = session_fuse(cwd=cwd, branch="feature-fuse", apply=True)

        self.assertEqual(result.issues, [])
        text = target.read_text(encoding="utf-8")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("## ") and index > 0:
                self.assertEqual(
                    lines[index - 1].strip(), "",
                    f"heading at line {index + 1} has no blank line before it: {lines[index - 1]!r}",
                )
        # Exactly one blank line between entries, never a run of them.
        self.assertIn("\n\n## 2026-07-10 10:00", text)
        self.assertNotIn("\n\n\n", text)

    @pytest.mark.integration
    def test_session_fuse_allows_sidecar_for_existing_base_entry(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_diagram(cwd, "2026-07-10", "mse_0123456789abcdef")
        self._commit_all(cwd, "add sidecar")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertEqual(result.issues, [])
        self.assertEqual(
            result.planned_sidecars,
            ["mse_0123456789abcdef 2026-07-10 09:00 -> .memory-seed/sessions/diagrams/2026-07/2026-07-10.md"],
        )

    @pytest.mark.integration
    def test_session_fuse_blocks_orphan_sidecar(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_diagram(cwd, "2026-07-11", "mse_1111111111111111")
        self._commit_all(cwd, "orphan sidecar")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("without a parent entry", result.issues[0])

    @pytest.mark.integration
    def test_session_fuse_blocks_sidecar_without_entry_id(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        sidecar = self._write_legacy_diagram(cwd, "2026-07-10", "mse_0123456789abcdef")
        sidecar.write_text(sidecar.read_text(encoding="utf-8").replace("entry_id: mse_0123456789abcdef\n", ""), encoding="utf-8")
        self._commit_all(cwd, "malformed sidecar")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("diagram sidecar block", result.issues[0])
        self.assertIn("has no entry_id", result.issues[0])

    @pytest.mark.integration
    def test_session_fuse_blocks_session_entry_without_entry_id(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        session = self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        session.write_text(session.read_text(encoding="utf-8").replace("entry_id: mse_1111111111111111\n", ""), encoding="utf-8")
        self._commit_all(cwd, "malformed session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("session entry", result.issues[0])
        self.assertIn("has no entry_id", result.issues[0])

    @pytest.mark.integration
    def test_session_fuse_ignores_unchanged_base_entries_without_entry_id(self):
        # Regression: fuse must scope branch-side validation to the branch's changed files, not the
        # whole corpus. A legacy pre-schema entry with no entry_id sitting unchanged on the base tree
        # (e.g. migrated from .AGENTS/) previously blocked every fuse on this repo.
        cwd = self.make_project()
        legacy = cwd / MEMORY_DIR_NAME / "sessions" / "2026-05" / "2026-05-17.md"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(
            "---\ntags:\n  - session-log\nsession_date: 2026-05-17\n---\n\n"
            "## 2026-05-17 09:00 - Legacy entry\n\nNo YAML block and no entry_id.\n",
            encoding="utf-8",
        )
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-fuse")
        self._commit_all(cwd, "feature session")  # legacy file untouched on the branch
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        # The unchanged legacy no-entry_id file is outside the branch diff, so it must not block...
        self.assertEqual(result.issues, [])
        # ...and the genuine branch entry is still planned.
        self.assertEqual(
            result.planned_entries,
            ["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
        )

    @pytest.mark.integration
    def test_session_fuse_reads_non_ascii_branch_entry(self):
        # Regression for the Windows cp1252 crash: git show of a non-ASCII session file must decode
        # as UTF-8. Applies the fuse and asserts the exact non-ASCII body round-trips byte-for-byte -
        # a cp1252 read would either crash or mojibake it, so this guards decoding, not just "no crash".
        non_ascii_body = "- Decision — kept the “fuse” contract \U0001f9e0 café."
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_grouped_session(
            cwd,
            "2026-07-11",
            "mse_2222222222222222",
            branch="feature-fuse",
            body=non_ascii_body,
        )
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")
        self._git(cwd, "merge", "--no-ff", "--no-commit", "feature-fuse")

        result = session_fuse(cwd=cwd, branch="feature-fuse", apply=True)

        self.assertEqual(result.issues, [])
        self.assertTrue(result.changed)
        grouped = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md"
        self.assertIn(non_ascii_body, grouped.read_text(encoding="utf-8"))

    @pytest.mark.integration
    def test_session_fuse_blocks_non_utf8_branch_session_file(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        bad = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07-11.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"## 2026-07-11 09:00 - Bad bytes\n\n```yaml\nentry_id: mse_badbadbadbadbad\nbranch: feature-fuse\n```\n\n\xff\n")
        self._commit_all(cwd, "invalid utf8 session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertEqual(result.planned_entries, [])
        self.assertTrue(result.issues)
        self.assertIn("could not decode .memory-seed/sessions/2026-07-11.md as UTF-8", result.issues)

    @pytest.mark.integration
    def test_session_fuse_blocks_when_diff_fails(self):
        # Regression: a git diff failure (e.g. unrelated histories / no merge-base) must surface an
        # issue, not collapse to an empty change set that silently filters out every branch entry
        # and reports success importing nothing.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "--orphan", "feature-orphan")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-orphan")
        self._commit_all(cwd, "orphan session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-orphan")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("could not compute changed session files", result.issues[0])

    @pytest.mark.integration
    def test_session_fuse_blocks_branch_field_mismatch(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_legacy_session(cwd, "2026-07-11", "mse_1111111111111111", branch="main")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("expected feature-fuse", result.issues[0])

    @pytest.mark.integration
    def test_session_fuse_blocks_existing_entry_edits(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main", body="- Original.")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-fuse")
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main", body="- Edited.")
        self._commit_all(cwd, "edit existing")
        self._git(cwd, "switch", "main")

        result = session_fuse(cwd=cwd, branch="feature-fuse")

        self.assertFalse(result.changed)
        self.assertTrue(result.issues)
        self.assertIn("existing entry_id modified", result.issues[0])

    @pytest.mark.integration
    def test_session_merge_branch_commits_clean_merge_end_to_end(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-merge")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        self.assertFalse(result.merge_in_progress)
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())
        parents = self._git(cwd, "log", "--merges", "-1", "--format=%P").stdout.split()
        self.assertEqual(len(parents), 2)
        grouped = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md"
        self.assertIn("entry_id: mse_1111111111111111", grouped.read_text(encoding="utf-8"))
        # Working tree fully committed: nothing staged or dirty afterwards.
        self.assertEqual(self._git(cwd, "status", "--short").stdout.strip(), "")

    @pytest.mark.integration
    def test_session_merge_branch_leaves_non_session_conflicts_in_progress(self):
        cwd = self.make_project()
        (cwd / "notes.txt").write_text("base\n", encoding="utf-8")
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        (cwd / "notes.txt").write_text("branch change\n", encoding="utf-8")
        self._commit_all(cwd, "branch edit")
        self._git(cwd, "switch", "main")
        (cwd / "notes.txt").write_text("main change\n", encoding="utf-8")
        self._commit_all(cwd, "main edit")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(result.merge_in_progress)
        self.assertEqual(result.conflicts, ["notes.txt"])
        # The merge must be left in progress for manual resolution, not aborted.
        self.assertTrue((cwd / ".git" / "MERGE_HEAD").exists())

    @pytest.mark.integration
    def test_session_merge_branch_fixes_out_of_order_landing(self):
        # The bug this command exists for: both sides append to the same dated
        # file after a shared ancestor, and a raw git merge would land the
        # branch's earlier-timestamped entry after base's later one (or leave
        # conflict markers). The wrapper must produce a chronological file.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Later main entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-merge")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")
        self._git(cwd, "switch", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "main appends 10:00")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("<<<<<<<", text)
        pos_a = text.find("## 2026-07-12 09:00")
        pos_c = text.find("## 2026-07-12 09:30")
        pos_b = text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_a < pos_c < pos_b, f"order wrong: a={pos_a} c={pos_c} b={pos_b}")
        # The committed tree matches the working tree (fuse result was staged).
        committed = self._git(cwd, "show", "HEAD:.memory-seed/sessions/2026-07/2026-07-12.md").stdout
        self.assertEqual(committed, text)

    @pytest.mark.integration
    def test_session_merge_branch_still_fuses_under_the_no_merge_attribute(self):
        # The guard must not break the sanctioned path. `-merge` makes git
        # conflict on the session file, but session_merge_branch resets
        # branch-touched session paths to base and rebuilds from parsed records,
        # so a session-only conflict is expected input, not a failure.
        cwd = self.make_project()
        target = self._concurrent_session_branches(cwd, gitattributes=self.NO_MERGE_ATTR)

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("<<<<<<<", text)
        pos_a = text.find("## 2026-07-12 09:00")
        pos_c = text.find("## 2026-07-12 09:30")
        pos_b = text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_a < pos_c < pos_b, f"order wrong: a={pos_a} c={pos_c} b={pos_b}")
        committed = self._git(cwd, "show", "HEAD:.memory-seed/sessions/2026-07/2026-07-12.md").stdout
        self.assertEqual(committed, text)

    @pytest.mark.integration
    def test_the_no_merge_attribute_stops_git_line_merging_session_files(self):
        # The other half: a raw `git merge` - the bypass that caused the
        # corruption - must now fail loudly instead of silently splicing
        # entries. Without the attribute git merges these cleanly by position;
        # with it, the file conflicts and demands the structural merge.
        import subprocess

        cwd = self.make_project()
        self._concurrent_session_branches(cwd, gitattributes=self.NO_MERGE_ATTR)

        merged = subprocess.run(
            ["git", "-C", str(cwd), "merge", "--no-ff", "--no-commit", "feature-merge"],
            capture_output=True, text=True,
        )

        self.assertNotEqual(merged.returncode, 0, "a raw line-merge of session files must not succeed")
        conflicted = self._git(cwd, "diff", "--name-only", "--diff-filter=U").stdout.split()
        self.assertIn(".memory-seed/sessions/2026-07/2026-07-12.md", conflicted)

    @pytest.mark.integration
    def test_without_the_attribute_git_interleaves_the_conflict_dangerously(self):
        # Control, and the actual mechanism behind the 2026-07-19 corruption.
        # Git does not merge these silently - it does something worse: it
        # anchors on the byte-identical topics:/related_entries: scaffolding,
        # treats those lines as AGREED content outside the markers, and splits
        # one logical conflict into two interleaved regions. The result has
        # fewer closing fences than entries, so stripping the markers and
        # re-splitting on '##' headings - the obvious hand-resolution, and the
        # one that caused the incident - strands a fence and splices bodies.
        import subprocess

        cwd = self.make_project()
        target = self._false_anchor_branches(cwd)

        subprocess.run(
            ["git", "-C", str(cwd), "merge", "--no-ff", "--no-commit", "feature-merge"],
            capture_output=True, text=True,
        )
        text = target.read_text(encoding="utf-8")

        self.assertGreater(text.count("<<<<<<<"), 1, "the danger is interleaving: >1 conflict region")
        # The shared scaffolding escaped the markers entirely, so the two
        # entries now share a single metadata fence between them.
        both_headings = text.count("## 2026-07-19 11:33") and text.count("## 2026-07-19 12:02")
        self.assertTrue(both_headings, "both entries are present...")
        stripped = "\n".join(
            ln for ln in text.splitlines()
            if not ln.startswith(("<<<<<<<", "=======", ">>>>>>>"))
        )
        from memory_seed.core import check_entry_metadata_fences
        self.assertTrue(
            check_entry_metadata_fences(stripped),
            "...and naive marker-stripping yields the unclosed fence links check now catches",
        )

    @pytest.mark.integration
    def test_the_attribute_keeps_the_conflicted_file_structurally_intact(self):
        # With the guard, the same merge conflicts as a UNIT: git writes no
        # markers into the file at all, so no entry is ever left half-formed.
        # The structural merge is then the only way forward.
        import subprocess

        from memory_seed.core import check_entry_metadata_fences

        cwd = self.make_project()
        target = self._false_anchor_branches(cwd, gitattributes=self.NO_MERGE_ATTR)

        merged = subprocess.run(
            ["git", "-C", str(cwd), "merge", "--no-ff", "--no-commit", "feature-merge"],
            capture_output=True, text=True,
        )
        text = target.read_text(encoding="utf-8")

        self.assertNotEqual(merged.returncode, 0)
        self.assertEqual(text.count("<<<<<<<"), 0, "no markers spliced into the file")
        self.assertFalse(check_entry_metadata_fences(text), "every entry left well formed")

    @pytest.mark.integration
    def test_session_merge_branch_fails_closed_before_merge_on_modified_entry(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main", body="- Original.")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main", body="- Edited.")
        self._commit_all(cwd, "edit existing")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(result.issues)
        self.assertIn("existing entry_id modified", result.issues[0])
        # Blocked at the fuse dry-run gate: the git merge must never have started.
        self.assertFalse(result.merge_in_progress)
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())

    @pytest.mark.integration
    def test_session_merge_branch_refuses_dirty_working_tree_naming_paths(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-merge")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")
        (cwd / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(result.issues)
        self.assertIn("working tree is not clean", result.issues[0])
        self.assertIn("uncommitted.txt", result.issues[0])
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())

    @pytest.mark.integration
    def test_session_merge_branch_stamps_memory_entry_trailers(self):
        # Approved trailer plan (2026-07-11): the merge commit carries one
        # Memory-Entry trailer per fused entry, below git's prepared merge
        # message, and find_trailer_commits resolves each entry to it. The
        # wider lowercase ids other agents emit (e.g. 20-hex codex ids) are
        # stamped too; base entries are never claimed.
        from memory_seed.core import find_trailer_commits

        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            ("09:00", "Branch entry one", "mse_1111111111111111", "feature-merge"),
            ("10:00", "Branch entry two", "mse_3ca332874c2bce263fd2", "feature-merge"),
        ]
        target.write_text(self._grouped_session_text("2026-07-12", entries), encoding="utf-8")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        self.assertEqual(
            result.stamped_entries,
            ["mse_1111111111111111", "mse_3ca332874c2bce263fd2"],
        )
        message = self._git(cwd, "log", "-1", "--format=%B").stdout
        # Git's prepared message is preserved above the trailer block.
        self.assertTrue(message.startswith("Merge branch 'feature-merge'"))
        self.assertIn("Memory-Entry: mse_1111111111111111", message)
        self.assertIn("Memory-Entry: mse_3ca332874c2bce263fd2", message)
        # The base entry was never part of the fuse and is never claimed.
        self.assertNotIn("mse_0123456789abcdef", message)
        merge_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        for entry_id in ("mse_1111111111111111", "mse_3ca332874c2bce263fd2"):
            hits = find_trailer_commits(cwd, entry_id)
            self.assertIsNotNone(hits)
            self.assertIn(merge_sha, [hit.split()[0] for hit in hits])

    @pytest.mark.integration
    def test_session_merge_branch_stamps_no_trailers_without_fuse_imports(self):
        # A merge whose branch touched no session files fuses nothing and must
        # leave git's prepared merge message untouched.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        (cwd / "notes.txt").write_text("base\n", encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        (cwd / "notes.txt").write_text("branch change\n", encoding="utf-8")
        self._commit_all(cwd, "branch edit")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        self.assertEqual(result.stamped_entries, [])
        message = self._git(cwd, "log", "-1", "--format=%B").stdout
        self.assertNotIn("Memory-Entry:", message)

    @pytest.mark.integration
    def test_session_merge_branch_never_stamps_malformed_entry_ids(self):
        # A malformed id must not poison the trailer channel: the entry still
        # fuses, but no Memory-Entry line is written for it.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            ("09:00", "Good entry", "mse_1111111111111111", "feature-merge"),
            ("10:00", "Weird id entry", "mse_UPPER!!invalid", "feature-merge"),
        ]
        target.write_text(self._grouped_session_text("2026-07-12", entries), encoding="utf-8")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertTrue(result.committed)
        self.assertEqual(result.stamped_entries, ["mse_1111111111111111"])
        message = self._git(cwd, "log", "-1", "--format=%B").stdout
        self.assertIn("Memory-Entry: mse_1111111111111111", message)
        self.assertNotIn("mse_UPPER!!invalid", message)

    @pytest.mark.integration
    def test_session_merge_branch_dry_run_reports_plan_without_merging(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-merge")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge", dry_run=True)

        self.assertFalse(result.committed)
        self.assertEqual(result.issues, [])
        self.assertEqual(
            result.planned_entries,
            ["mse_1111111111111111 2026-07-11 09:00 -> .memory-seed/sessions/2026-07/2026-07-11.md"],
        )
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())
        self.assertFalse((cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-11.md").exists())
        self.assertEqual(self._git(cwd, "log", "--merges", "-1", "--format=%P").stdout.strip(), "")

    def test_is_recognized_session_tree_path_covers_session_diagram_and_link(self):
        # The guard's recognizer set must equal the fuse's handled set, or the
        # guard eats the fix (link paths) or fails to eat the next gap.
        from memory_seed.core import _is_recognized_session_tree_path

        self.assertTrue(_is_recognized_session_tree_path(".memory-seed/sessions/2026-07/2026-07-10.md"))
        self.assertTrue(_is_recognized_session_tree_path(".memory-seed/sessions/diagrams/2026-07/2026-07-10.md"))
        self.assertTrue(_is_recognized_session_tree_path(".memory-seed/sessions/links/2026-07/2026-07-10.md"))
        self.assertFalse(_is_recognized_session_tree_path(".memory-seed/sessions/decisions/2026-07-10.md"))
        self.assertFalse(_is_recognized_session_tree_path("notes.txt"))

    @pytest.mark.integration
    def test_session_merge_branch_imports_link_sidecar_added_on_branch(self):
        # P1 regression: a branch-side link sidecar block appended to a file
        # that already exists on base used to be reset to base content and
        # silently dropped, because the fuse recognized session and diagram
        # paths but not `sessions/links/**`. This is the exact shape of the
        # 2026-07-19 loss - a shared dated sidecar file, one side appends.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-10.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "First", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("09:30", "Second", "mse_bbbbbbbbbbbbbbbb", "main")
        target.write_text(self._grouped_session_text("2026-07-10", [entry_a, entry_b]), encoding="utf-8")
        link_target = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-07" / "2026-07-10.md"
        link_target.parent.mkdir(parents=True, exist_ok=True)
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-10",
                [("09:15", "Note A", "mse_aaaaaaaaaaaaaaaa", ["related_entries:", "  - mse_zzzzzzzzzzzzzzzz"])],
            ),
            encoding="utf-8",
        )
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-10",
                [
                    ("09:15", "Note A", "mse_aaaaaaaaaaaaaaaa", ["related_entries:", "  - mse_zzzzzzzzzzzzzzzz"]),
                    ("09:45", "Note B", "mse_bbbbbbbbbbbbbbbb", ["supersedes:", "  - mse_aaaaaaaaaaaaaaaa"]),
                ],
            ),
            encoding="utf-8",
        )
        self._commit_all(cwd, "branch link sidecar")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        self.assertIn(
            "mse_bbbbbbbbbbbbbbbb 2026-07-10 09:45 -> .memory-seed/sessions/links/2026-07/2026-07-10.md",
            result.planned_link_sidecars,
        )
        text = link_target.read_text(encoding="utf-8")
        self.assertIn("entry_id: mse_aaaaaaaaaaaaaaaa", text)
        self.assertIn("entry_id: mse_bbbbbbbbbbbbbbbb", text)
        self.assertIn("supersedes:", text)
        # The regression proof: the merge COMMIT carries the change, not just
        # the working tree - `git diff base..merge` for this exact bug used
        # to be completely empty despite the merge reporting success.
        committed_text = self._git(cwd, "show", "HEAD:.memory-seed/sessions/links/2026-07/2026-07-10.md").stdout
        self.assertEqual(committed_text, text)
        diff_stat = self._git(cwd, "diff", "--stat", "HEAD~1", "HEAD", "--", ".memory-seed/sessions/links").stdout
        self.assertTrue(diff_stat.strip(), "merge commit must carry the link-sidecar change, not contribute nothing")

    def test_second_link_sidecar_block_for_same_entry_imports_as_new_declaration(self):
        # Block identity is (entry_id, timestamp), not entry_id alone. An entry
        # that already carries a block gains a SECOND dated block when a later
        # audit records a new edge - the append-only-compatible correction
        # path. Keying by entry_id alone made the first block the only block
        # forever: by cycle 5 of the judgment programme eight validated edges
        # were withheld on exactly this shape.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-10.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "First", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("09:30", "Second", "mse_bbbbbbbbbbbbbbbb", "main")
        target.write_text(self._grouped_session_text("2026-07-10", [entry_a, entry_b]), encoding="utf-8")
        link_target = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-07" / "2026-07-10.md"
        link_target.parent.mkdir(parents=True, exist_ok=True)
        first_block = ("09:45", "Second", "mse_bbbbbbbbbbbbbbbb", ["related_entries:", "  - mse_aaaaaaaaaaaaaaaa"])
        link_target.write_text(self._link_sidecar_text("2026-07-10", [first_block]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        second_block = ("21:00", "Second", "mse_bbbbbbbbbbbbbbbb", ["evolves:", "  - mse_aaaaaaaaaaaaaaaa"])
        link_target.write_text(
            self._link_sidecar_text("2026-07-10", [first_block, second_block]), encoding="utf-8"
        )
        self._commit_all(cwd, "second declaration for the same entry")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.committed)
        text = link_target.read_text(encoding="utf-8")
        self.assertEqual(text.count("entry_id: mse_bbbbbbbbbbbbbbbb"), 2, "both dated blocks must survive")
        self.assertIn("## 2026-07-10 09:45", text)
        self.assertIn("## 2026-07-10 21:00", text)
        self.assertIn("evolves:", text)
        self.assertIn("related_entries:", text)

    def test_modified_existing_link_sidecar_block_is_still_refused(self):
        # The composite key narrows the immutability guard, it does not remove
        # it: the SAME (entry_id, timestamp) block with different text is still
        # an in-place modification and still blocks the merge.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-10.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "First", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("09:30", "Second", "mse_bbbbbbbbbbbbbbbb", "main")
        target.write_text(self._grouped_session_text("2026-07-10", [entry_a, entry_b]), encoding="utf-8")
        link_target = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-07" / "2026-07-10.md"
        link_target.parent.mkdir(parents=True, exist_ok=True)
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-10",
                [("09:45", "Second", "mse_bbbbbbbbbbbbbbbb", ["related_entries:", "  - mse_aaaaaaaaaaaaaaaa"])],
            ),
            encoding="utf-8",
        )
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-10",
                [("09:45", "Second", "mse_bbbbbbbbbbbbbbbb", ["evolves:", "  - mse_aaaaaaaaaaaaaaaa"])],
            ),
            encoding="utf-8",
        )
        self._commit_all(cwd, "in-place edit of the published block")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(any("existing link sidecar modified" in issue for issue in result.issues))

    def test_duplicate_same_timestamp_link_sidecar_blocks_are_refused(self):
        # Two blocks for one entry at the SAME heading timestamp have the same
        # identity - that is authoring damage, not a second declaration.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-10.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "First", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("09:30", "Second", "mse_bbbbbbbbbbbbbbbb", "main")
        target.write_text(self._grouped_session_text("2026-07-10", [entry_a, entry_b]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        link_target = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-07" / "2026-07-10.md"
        link_target.parent.mkdir(parents=True, exist_ok=True)
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-10",
                [
                    ("09:45", "Second", "mse_bbbbbbbbbbbbbbbb", ["related_entries:", "  - mse_aaaaaaaaaaaaaaaa"]),
                    ("09:45", "Second", "mse_bbbbbbbbbbbbbbbb", ["evolves:", "  - mse_aaaaaaaaaaaaaaaa"]),
                ],
            ),
            encoding="utf-8",
        )
        self._commit_all(cwd, "duplicate identity blocks")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(any("duplicate link sidecar blocks" in issue for issue in result.issues))

    @pytest.mark.integration
    def test_session_merge_branch_fuses_link_sidecar_edited_on_both_sides(self):
        # Two-sided edit is the case the `-merge` guard forces into a real git
        # conflict. Before this fix that conflict was misclassified as
        # non-session (the classifier recognized session/diagram paths but not
        # links/) and the merge aborted loudly. It must now fuse like any
        # other session-tree conflict, not abort.
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "First", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("09:15", "Second", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Third", "mse_cccccccccccccccc", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b, entry_c]), encoding="utf-8")
        link_target = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-07" / "2026-07-12.md"
        link_target.parent.mkdir(parents=True, exist_ok=True)
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-12",
                [("09:05", "Note A", "mse_aaaaaaaaaaaaaaaa", ["related_entries:", "  - mse_zzzzzzzzzzzzzzzz"])],
            ),
            encoding="utf-8",
        )
        (cwd / ".gitattributes").write_text(self.NO_MERGE_ATTR, encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-12",
                [
                    ("09:05", "Note A", "mse_aaaaaaaaaaaaaaaa", ["related_entries:", "  - mse_zzzzzzzzzzzzzzzz"]),
                    ("09:20", "Note B", "mse_bbbbbbbbbbbbbbbb", ["evolves:", "  - mse_aaaaaaaaaaaaaaaa"]),
                ],
            ),
            encoding="utf-8",
        )
        self._commit_all(cwd, "branch link sidecar")
        self._git(cwd, "switch", "main")
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-12",
                [
                    ("09:05", "Note A", "mse_aaaaaaaaaaaaaaaa", ["related_entries:", "  - mse_zzzzzzzzzzzzzzzz"]),
                    ("09:35", "Note C", "mse_cccccccccccccccc", ["supersedes:", "  - mse_bbbbbbbbbbbbbbbb"]),
                ],
            ),
            encoding="utf-8",
        )
        self._commit_all(cwd, "main link sidecar")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertEqual(result.issues, [])
        self.assertFalse(result.conflicts)
        self.assertTrue(result.committed)
        text = link_target.read_text(encoding="utf-8")
        self.assertIn("entry_id: mse_aaaaaaaaaaaaaaaa", text)
        self.assertIn("entry_id: mse_bbbbbbbbbbbbbbbb", text)
        self.assertIn("entry_id: mse_cccccccccccccccc", text)

    @pytest.mark.integration
    def test_session_merge_branch_refuses_link_sidecar_modified_on_branch(self):
        # The sanctioned stub -> live classification workflow runs on trunk
        # (lifecycle-edge-linking-sidecars.md). Modifying an EXISTING sidecar
        # block's text on a branch (same entry_id, changed text) must fail
        # loudly before any merge starts, not corrupt or silently pick a side.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_aaaaaaaaaaaaaaaa", branch="main")
        link_target = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-07" / "2026-07-10.md"
        link_target.parent.mkdir(parents=True, exist_ok=True)
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-10",
                [("09:15", "Stub", "mse_aaaaaaaaaaaaaaaa", ["classify_pending: true"])],
            ),
            encoding="utf-8",
        )
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        link_target.write_text(
            self._link_sidecar_text(
                "2026-07-10",
                [("09:15", "Stub", "mse_aaaaaaaaaaaaaaaa", ["supersedes:", "  - mse_zzzzzzzzzzzzzzzz"])],
            ),
            encoding="utf-8",
        )
        self._commit_all(cwd, "branch classifies stub")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertFalse(result.merge_in_progress)
        self.assertTrue(result.issues)
        self.assertIn("existing link sidecar modified", result.issues[0])
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())

    @pytest.mark.integration
    def test_session_merge_branch_refuses_to_reset_an_unrecognized_sessions_path(self):
        # Defense in depth (added alongside the link-sidecar fix): a future
        # sidecar kind under .memory-seed/sessions that no classifier
        # recognizes yet must fail loudly rather than being silently reset to
        # base content the way link sidecars silently were before this fix.
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_aaaaaaaaaaaaaaaa", branch="main")
        unknown = cwd / MEMORY_DIR_NAME / "sessions" / "decisions" / "2026-07-10.md"
        unknown.parent.mkdir(parents=True, exist_ok=True)
        unknown.write_text("base content\n", encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-merge")
        unknown.write_text("branch content\n", encoding="utf-8")
        self._commit_all(cwd, "branch edits unknown sidecar")
        self._git(cwd, "switch", "main")

        result = session_merge_branch(cwd=cwd, branch="feature-merge")

        self.assertFalse(result.committed)
        self.assertTrue(result.merge_in_progress)
        self.assertTrue(result.issues)
        self.assertIn("not recognized by any session/diagram/link classifier", result.issues[0])
        self.assertTrue((cwd / ".git" / "MERGE_HEAD").exists())

    @pytest.mark.integration
    def test_session_prepare_pr_branch_commits_chronological_merge_on_task_branch(self):
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Later main entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")
        self._git(cwd, "switch", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "main appends 10:00")
        self._git(cwd, "switch", "feature-pr")

        result = session_prepare_pr_branch(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertEqual(result.issues, [])
        self.assertEqual(result.conflicts, [])
        self.assertTrue(result.ready)
        self.assertTrue(result.changed)
        self.assertIsNotNone(result.prep_commit)
        text = target.read_text(encoding="utf-8")
        pos_a = text.find("## 2026-07-12 09:00")
        pos_c = text.find("## 2026-07-12 09:30")
        pos_b = text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_a < pos_c < pos_b, f"order wrong: a={pos_a} c={pos_c} b={pos_b}")
        self.assertNotIn("<<<<<<<", text)
        message = self._git(cwd, "log", "-1", "--format=%B").stdout
        self.assertTrue(message.startswith("Merge branch 'main' into feature-pr"))
        self.assertIn("Memory-Entry: mse_cccccccccccccccc", message)

    @pytest.mark.integration
    def test_session_prepare_pr_branch_refuses_dirty_tree_naming_paths(self):
        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        (cwd / "dirty.txt").write_text("dirty\n", encoding="utf-8")

        result = session_prepare_pr_branch(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertFalse(result.ready)
        self.assertTrue(result.issues)
        self.assertIn("working tree is not clean", result.issues[0])
        self.assertIn("dirty.txt", result.issues[0])
        self.assertFalse((cwd / ".git" / "MERGE_HEAD").exists())

    @pytest.mark.integration
    def test_session_prepare_pr_branch_prefers_origin_main_when_local_main_is_stale(self):
        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Origin main entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        base_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        self._git(cwd, "switch", "-c", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")
        self._git(cwd, "switch", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "main appends 10:00")
        origin_main_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        # Deliberately stale local main while origin/main stays newer.
        self._git(cwd, "switch", "feature-pr")
        self._git(cwd, "update-ref", "refs/heads/main", base_sha)
        self._git(cwd, "update-ref", "refs/remotes/origin/main", origin_main_sha)
        self._git(cwd, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

        result = session_prepare_pr_branch(cwd=cwd, branch="feature-pr")

        self.assertEqual(result.issues, [])
        self.assertTrue(result.ready)
        text = target.read_text(encoding="utf-8")
        self.assertIn("mse_bbbbbbbbbbbbbbbb", text)
        pos_c = text.find("## 2026-07-12 09:30")
        pos_b = text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_c < pos_b, f"origin/main was not used: c={pos_c} b={pos_b}")

    @pytest.mark.integration
    def test_session_prepare_pr_branch_leaves_non_session_conflicts_in_progress(self):
        cwd = self.make_project()
        (cwd / "notes.txt").write_text("base\n", encoding="utf-8")
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        (cwd / "notes.txt").write_text("branch change\n", encoding="utf-8")
        self._commit_all(cwd, "branch edit")
        self._git(cwd, "switch", "main")
        (cwd / "notes.txt").write_text("main change\n", encoding="utf-8")
        self._commit_all(cwd, "main edit")
        self._git(cwd, "switch", "feature-pr")

        result = session_prepare_pr_branch(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertFalse(result.ready)
        self.assertTrue(result.merge_in_progress)
        self.assertEqual(result.conflicts, ["notes.txt"])
        self.assertTrue((cwd / ".git" / "MERGE_HEAD").exists())

    @pytest.mark.integration
    def test_session_open_pr_dry_run_returns_pr_body_plan(self):
        import unittest.mock

        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-pr")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "remote", "add", "origin", "https://example.com/owner/repo.git")

        def fake_gh(_root, args):
            if tuple(args) == ("--version",):
                return 0, "gh version 2.0.0", ""
            if tuple(args) == ("auth", "status"):
                return 0, "", ""
            self.fail(f"unexpected gh call: {args!r}")

        with unittest.mock.patch("memory_seed.core._gh_text", side_effect=fake_gh):
            result = session_open_pr(cwd=cwd, branch="feature-pr", base_branch="main", dry_run=True)

        self.assertEqual(result.issues, [])
        self.assertFalse(result.opened)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.pr_title, "Integrate feature-pr into main")
        self.assertIsNotNone(result.pr_body)
        self.assertIn("memory-seed session prepare-pr --branch feature-pr --base-branch main", result.pr_body)
        self.assertIn("mse_1111111111111111", result.pr_body)
        self.assertFalse(result.pushed)
        self.assertFalse(result.pr_created)
        self.assertEqual(self._git(cwd, "status", "--short").stdout.strip(), "")

    @pytest.mark.integration
    def test_session_open_pr_refreshes_remote_base_before_preparing_and_pushing(self):
        import subprocess
        import unittest.mock

        cwd = self.make_project()
        target = cwd / MEMORY_DIR_NAME / "sessions" / "2026-07" / "2026-07-12.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        entry_a = ("09:00", "Base entry", "mse_aaaaaaaaaaaaaaaa", "main")
        entry_b = ("10:00", "Fresh remote entry", "mse_bbbbbbbbbbbbbbbb", "main")
        entry_c = ("09:30", "Branch entry", "mse_cccccccccccccccc", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a]), encoding="utf-8")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        base_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()

        remote = self.make_project() / "origin.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True, text=True)
        self._git(cwd, "remote", "add", "origin", str(remote))
        self._git(cwd, "update-ref", "refs/remotes/origin/main", base_sha)

        self._git(cwd, "switch", "-q", "-c", "feature-pr")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_c]), encoding="utf-8")
        self._commit_all(cwd, "branch appends 09:30")

        self._git(cwd, "switch", "-q", "main")
        target.write_text(self._grouped_session_text("2026-07-12", [entry_a, entry_b]), encoding="utf-8")
        self._commit_all(cwd, "fresh remote main")
        fresh_remote_sha = self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        self._git(cwd, "switch", "-q", "feature-pr")
        self._git(cwd, "update-ref", "refs/heads/main", base_sha)

        from memory_seed import core as core_module

        original_git_text = core_module._git_text
        git_commands = []

        def fake_git(root, args):
            git_commands.append(tuple(args))
            if tuple(args) == (
                "fetch",
                "--no-tags",
                "origin",
                "refs/heads/main:refs/remotes/origin/main",
            ):
                self._git(cwd, "update-ref", "refs/remotes/origin/main", fresh_remote_sha)
                return 0, ""
            if tuple(args) == ("push", "--set-upstream", "origin", "feature-pr"):
                return 0, ""
            return original_git_text(root, args)

        def fake_gh(_root, args):
            if tuple(args) == ("--version",):
                return 0, "gh version 2.0.0", ""
            if tuple(args) == ("auth", "status"):
                return 0, "", ""
            if tuple(args[:2]) == ("pr", "create"):
                return 0, "https://example.test/owner/repo/pull/1", ""
            self.fail(f"unexpected gh call: {args!r}")

        with unittest.mock.patch("memory_seed.core._git_text", side_effect=fake_git), unittest.mock.patch(
            "memory_seed.core._gh_text", side_effect=fake_gh
        ):
            result = session_open_pr(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertTrue(result.opened)
        self.assertTrue(result.pushed)
        self.assertTrue(result.pr_created)
        self.assertEqual(result.issues, [])
        pushed_text = target.read_text(encoding="utf-8")
        pos_c = pushed_text.find("## 2026-07-12 09:30")
        pos_b = pushed_text.find("## 2026-07-12 10:00")
        self.assertTrue(0 <= pos_c < pos_b, "fresh origin/main was not prepared before push")
        self.assertIn(("fetch", "--no-tags", "origin", "refs/heads/main:refs/remotes/origin/main"), git_commands)
        self.assertIn(("push", "--set-upstream", "origin", "feature-pr"), git_commands)
        self.assertFalse(any("--force" in args or "-f" in args for args in git_commands))

    @pytest.mark.integration
    def test_session_open_pr_refuses_failed_base_refresh_before_branch_modification(self):
        import unittest.mock

        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-q", "-c", "feature-pr")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-pr")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "remote", "add", "origin", str(cwd / "missing-origin.git"))
        before = self._git(cwd, "rev-parse", "HEAD").stdout.strip()

        def fake_gh(_root, args):
            if tuple(args) == ("--version",):
                return 0, "gh version 2.0.0", ""
            if tuple(args) == ("auth", "status"):
                return 0, "", ""
            self.fail(f"unexpected gh call: {args!r}")

        with unittest.mock.patch("memory_seed.core._gh_text", side_effect=fake_gh):
            result = session_open_pr(cwd=cwd, branch="feature-pr", base_branch="main")

        self.assertFalse(result.opened)
        self.assertFalse(result.pushed)
        self.assertTrue(result.issues)
        self.assertIn("could not refresh origin/main", result.issues[0])
        self.assertEqual(before, self._git(cwd, "rev-parse", "HEAD").stdout.strip())
        self.assertEqual(self._git(cwd, "status", "--short").stdout.strip(), "")

    @pytest.mark.integration
    def test_session_open_pr_refuses_unauthenticated_gh_before_modifying_branch(self):
        import unittest.mock

        cwd = self.make_project()
        self._write_grouped_session(cwd, "2026-07-10", "mse_0123456789abcdef", branch="main")
        self._init_git_project(cwd)
        self._commit_all(cwd, "base")
        self._git(cwd, "switch", "-c", "feature-pr")
        self._write_grouped_session(cwd, "2026-07-11", "mse_1111111111111111", branch="feature-pr")
        self._commit_all(cwd, "feature session")
        self._git(cwd, "remote", "add", "origin", "https://example.com/owner/repo.git")
        before = self._git(cwd, "rev-parse", "HEAD").stdout.strip()

        def fake_gh(_root, args):
            if tuple(args) == ("--version",):
                return 0, "gh version 2.0.0", ""
            if tuple(args) == ("auth", "status"):
                return 1, "", "not logged in"
            self.fail(f"unexpected gh call: {args!r}")

        with unittest.mock.patch("memory_seed.core._gh_text", side_effect=fake_gh):
            result = session_open_pr(cwd=cwd, branch="feature-pr", base_branch="main", dry_run=False)

        self.assertFalse(result.opened)
        self.assertTrue(result.issues)
        self.assertIn("gh is not authenticated", result.issues[0])
        self.assertEqual(before, self._git(cwd, "rev-parse", "HEAD").stdout.strip())
        self.assertEqual(self._git(cwd, "status", "--short").stdout.strip(), "")
