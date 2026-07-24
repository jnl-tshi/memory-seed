import shutil
import tempfile
import unittest
import pytest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
    check_session_links,
)


class LinksCheckTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _per_user_session(self, cwd, date, user, *, fm_user=None, fm_date=None,
                          schema="2", hash_id=None, entries=("ms-aaaaaaaa",), extra_fm=""):
        d = cwd / MEMORY_DIR_NAME / "sessions" / date
        d.mkdir(parents=True, exist_ok=True)
        fm = ["---", f"schema_version: {schema}", f"session_date: {fm_date or date}"]
        if hash_id is not None:
            fm.append(f"hash_id: {hash_id}")
        fm += [f"user: {fm_user or user}", "created_at: 2026-06-13T00:00:00Z"]
        if extra_fm:
            fm.append(extra_fm)
        fm.append("---")
        body = []
        for eid in entries:
            body += ["", f"## {date} 09:00 - entry", "", "```yaml", f"entry_id: {eid}", "```", "", "- note"]
        (d / f"{user}.md").write_text("\n".join(fm + body) + "\n", encoding="utf-8")

    def _flat_session(self, cwd, filename, *entry_specs):
        """Write a flat session file from (heading, entry_id, replaces) specs."""
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for heading, entry_id, replaces in entry_specs:
            lines += [f"## {heading}", "", "```yaml", f"entry_id: {entry_id}"]
            if replaces:
                lines.append("replaces:")
                lines.extend(f"  - {ref}" for ref in replaces)
            lines += ["```", "", "- note", ""]
        (sessions / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _link_sidecar(
        self,
        cwd,
        file_date,
        source_entry,
        *,
        replaces=(),
        evolves=(),
        classify_pending=False,
        heading_time="10:00",
    ):
        """Write a link sidecar block keyed to ``source_entry`` under
        sessions/links/<month>/<file_date>.md."""
        d = cwd / MEMORY_DIR_NAME / "sessions" / "links" / file_date[:7]
        d.mkdir(parents=True, exist_ok=True)
        lines = [f"## {file_date} {heading_time} - edge", "", "```yaml", f"entry_id: {source_entry}"]
        if classify_pending:
            lines.append("classify_pending: true")
        for key, refs in (("replaces", replaces), ("evolves", evolves)):
            if refs:
                lines.append(f"{key}:")
                lines.extend(f"  - {ref}" for ref in refs)
        lines += ["```", ""]
        (d / f"{file_date}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _flat_session_raw(self, cwd, filename, text):
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / filename).write_text(text, encoding="utf-8")

    def _entry_yaml(self, heading, entry_id, *yaml_lines):
        lines = [f"## {heading}", "", "```yaml", f"entry_id: {entry_id}", *yaml_lines, "```", "", "- note", ""]
        return "\n".join(lines)

    def _flat_session_with_commits(self, cwd, *hashes):
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        lines = ["## 2026-06-13 09:00 - entry", "", "```yaml", "entry_id: mse_0123456789abcdef", "commits:"]
        lines.extend(f"  - {h}" for h in hashes)
        lines += ["```", "", "- note", ""]
        (sessions / "2026-06-13.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _git_repo_with_commit(self, cwd, message="initial"):
        import subprocess

        subprocess.run(["git", "-C", str(cwd), "init", "-q"], check=True, capture_output=True)
        (cwd / "README.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "-C", str(cwd), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            [
                "git", "-C", str(cwd),
                "-c", "user.name=test", "-c", "user.email=test@example.com",
                "-c", "commit.gpgsign=false",
                "commit", "-q", "-m", message,
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "-C", str(cwd), "branch", "-M", "main"], check=True, capture_output=True)
        head = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        return head

    def test_links_check_flags_malformed_entry_format(self):
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        good = "## 2026-06-01 09:00 - Good\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n### Decision\n\n- D: x\n- R: y\n"
        (sessions / "2026-06-01.md").write_text(good, encoding="utf-8")
        self.assertTrue(check_session_links(cwd=cwd).ok)

        bad = "## 2026-06-02 09:00 - Bad\n\n```yaml\nentry_id: ms-bbbbbbbb\n```\n\nD: bare label\nR: reason\n"
        (sessions / "2026-06-02.md").write_text(bad, encoding="utf-8")
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        fmt_issues = [i for i in result.issues if i.kind == "malformed-entry-format"]
        self.assertTrue(fmt_issues)
        self.assertTrue(any("ms-bbbbbbbb" in i.detail for i in fmt_issues))

    def test_links_check_flags_an_unclosed_metadata_fence(self):
        # The exact shape a bad three-way merge left in the corpus: git anchored
        # on the line-identical `topics:`/`related_entries:` run every entry
        # shares, spliced the first entry's body away and stranded its fence.
        # links check PASSED that file - the ids still regexed out of raw text -
        # and only the fuse's stricter parser objected. This pins the gap.
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        corrupted = (
            "## 2026-06-03 11:33 - Stranded by a merge\n\n"
            "```yaml\n"
            "entry_id: ms-cccccccc\n"
            "topics:\n  - memory-trace\n"
            "## 2026-06-03 12:02 - The entry that swallowed it\n\n"
            "```yaml\nentry_id: ms-dddddddd\n```\n\n"
            "### Decision\n\n- D: x\n- R: y\n"
        )
        (sessions / "2026-06-03.md").write_text(corrupted, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        self.assertFalse(result.ok)
        fence_issues = [i for i in result.issues if i.kind == "malformed-entry-yaml"]
        self.assertTrue(fence_issues, "an unclosed metadata fence must be an error")
        self.assertTrue(any("ms-cccccccc" in i.detail for i in fence_issues))
        # The intact entry that followed it is not collateral.
        self.assertFalse(any("ms-dddddddd" in i.detail for i in fence_issues))

    def test_a_yaml_example_in_the_body_is_not_an_unclosed_fence(self):
        # The discriminating case. Entries legitimately quote YAML in their
        # prose, so a fence-balance count across the whole block would flag
        # well-formed history. The check anchors to the FIRST opener after the
        # heading and asks only whether that one closes.
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        with_example = (
            "## 2026-06-04 09:00 - Quotes YAML in its body\n\n"
            "```yaml\nentry_id: ms-eeeeeeee\n```\n\n"
            "### Decision\n\n- D: Documented the shape.\n- R: Future readers need it.\n\n"
            "```yaml\ntopics:\n  - example\n```\n"
        )
        (sessions / "2026-06-04.md").write_text(with_example, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        self.assertFalse([i for i in result.issues if i.kind == "malformed-entry-yaml"])

    def test_a_legacy_entry_with_no_metadata_block_is_left_alone(self):
        # The corpus's first two days predate the metadata convention (15 such
        # entries). Append-only forbids retrofitting published history, so their
        # absence of a fence must stay silent rather than red the whole check.
        from memory_seed.core import check_session_links

        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        legacy = "## 2026-05-19 20:35 - Before metadata existed\n\n- Just a note.\n"
        (sessions / "2026-05-19.md").write_text(legacy, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        self.assertFalse([i for i in result.issues if i.kind == "malformed-entry-yaml"])

    def test_links_check_clean_per_user_repo_is_ok(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", hash_id="msm_" + "a" * 32, entries=("ms-11111111",))
        self._per_user_session(cwd, "2026-06-13", "amina", hash_id="msm_" + "b" * 32, entries=("ms-22222222",))

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])
        self.assertEqual(result.files_checked, 2)

    def test_links_check_detects_duplicate_entry_id(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", hash_id="msm_" + "a" * 32, entries=("ms-deadbeef",))
        self._per_user_session(cwd, "2026-06-13", "amina", hash_id="msm_" + "b" * 32, entries=("ms-deadbeef",))

        result = check_session_links(cwd=cwd)

        self.assertFalse(result.ok)
        self.assertTrue(any(i.kind == "duplicate-entry-id" and "ms-deadbeef" in i.detail for i in result.issues))

    def test_links_check_detects_frontmatter_user_and_date_mismatch(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", fm_user="bob", fm_date="2026-06-14",
                               hash_id="msm_" + "a" * 32, entries=("ms-33333333",))

        kinds = {i.kind for i in check_session_links(cwd=cwd).issues}

        self.assertIn("user-mismatch", kinds)
        self.assertIn("date-mismatch", kinds)

    def test_links_check_detects_bad_schema_and_missing_hash(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", schema="9", hash_id=None, entries=("ms-44444444",))

        kinds = {i.kind for i in check_session_links(cwd=cwd).issues}

        self.assertIn("unsupported-schema-version", kinds)
        self.assertIn("missing-hash-id", kinds)

    def test_links_check_detects_duplicate_hash_id(self):
        cwd = self.make_project()
        self._per_user_session(cwd, "2026-06-13", "jean", hash_id="msm_" + "c" * 32, entries=("ms-55555555",))
        self._per_user_session(cwd, "2026-06-14", "jean", hash_id="msm_" + "c" * 32, entries=("ms-66666666",))

        kinds = {i.kind for i in check_session_links(cwd=cwd).issues}

        self.assertIn("duplicate-hash-id", kinds)

    def test_links_check_detects_dangling_related_refs(self):
        cwd = self.make_project()
        self._per_user_session(
            cwd, "2026-06-13", "jean", hash_id="msm_" + "a" * 32, entries=("ms-77777777",),
            extra_fm="related_entries:\n  - ms-99999999\nrelated_memories:\n  - msm_" + "f" * 32,
        )

        kinds = {i.kind for i in check_session_links(cwd=cwd).issues}

        self.assertIn("dangling-related-entry", kinds)
        self.assertIn("dangling-related-memory", kinds)

    def test_links_check_resolves_valid_related_refs(self):
        cwd = self.make_project()
        # jean references amina's entry + file hash, both of which exist.
        self._per_user_session(cwd, "2026-06-13", "amina", hash_id="msm_" + "b" * 32, entries=("ms-88888888",))
        self._per_user_session(
            cwd, "2026-06-13", "jean", hash_id="msm_" + "a" * 32, entries=("ms-77777777",),
            extra_fm="related_entries:\n  - ms-88888888\nrelated_memories:\n  - msm_" + "b" * 32,
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_validates_entry_level_related_entries_for_old_and_new_ids(self):
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-13"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "jean.md").write_text(
            "\n".join(
                [
                    "---",
                    "schema_version: 2",
                    "session_date: 2026-06-13",
                    "hash_id: msm_" + "a" * 32,
                    "user: jean",
                    "created_at: 2026-06-13T00:00:00Z",
                    "---",
                    "",
                    "## 2026-06-13 09:00 - first",
                    "",
                    "```yaml",
                    "entry_id: mse_0123456789abcdef",
                    "related_entries:",
                    "  - ms-88888888",
                    "```",
                    "",
                    "- note",
                    "",
                    "## 2026-06-13 10:00 - second",
                    "",
                    "```yaml",
                    "entry_id: ms-88888888",
                    "related_entries:",
                    "  - mse_ffffffffffffffff",
                    "```",
                    "",
                    "- note",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual(
            [issue.kind for issue in issues],
            ["dangling-related-entry"],
            [issue.__dict__ for issue in issues],
        )
        self.assertIn("mse_ffffffffffffffff", issues[0].detail)

    def test_links_check_validates_entry_level_related_entries_in_legacy_flat_files(self):
        # Regression test: entry-level related_entries used to only be scanned
        # for per-user-day files, silently skipping legacy-flat sessions/*.md
        # (this repo's own layout) - a dangling ref there passed with ok=True.
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-13.md").write_text(
            "\n".join(
                [
                    "---",
                    "tags: [session-log]",
                    "session_date: 2026-06-13",
                    "---",
                    "",
                    "## 2026-06-13 09:00 - flat entry",
                    "",
                    "```yaml",
                    "entry_id: mse_0123456789abcdef",
                    "user_initials: JN",
                    "related_entries:",
                    "  - mse_ffffffffffffffff",
                    "```",
                    "",
                    "- note",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual(
            [issue.kind for issue in issues],
            ["dangling-related-entry"],
            [issue.__dict__ for issue in issues],
        )
        self.assertIn("mse_ffffffffffffffff", issues[0].detail)

    def test_links_check_resolves_valid_related_entries_in_legacy_flat_files(self):
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-13.md").write_text(
            "\n".join(
                [
                    "## 2026-06-13 09:00 - first",
                    "",
                    "```yaml",
                    "entry_id: mse_0123456789abcdef",
                    "```",
                    "",
                    "## 2026-06-13 10:00 - second",
                    "",
                    "```yaml",
                    "entry_id: mse_ffffffffffffffff",
                    "related_entries:",
                    "  - mse_0123456789abcdef",
                    "```",
                    "",
                    "- note",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_accepts_backward_replaces(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - original", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - replacement", "mse_ffffffffffffffff", ("mse_0123456789abcdef",)),
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_flags_dangling_replaces(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - only", "mse_0123456789abcdef", ("mse_zzzzzzzzzzzzzzzz",)),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["dangling-replaces"], [i.__dict__ for i in issues])
        self.assertIn("mse_zzzzzzzzzzzzzzzz", issues[0].detail)

    def test_links_check_flags_postdating_replaces(self):
        # Forward-only guard: an earlier entry may not replace a later one.
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - earlier", "mse_0123456789abcdef", ("mse_ffffffffffffffff",)),
            ("2026-06-13 10:00 - later", "mse_ffffffffffffffff", ()),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["replaces-postdates"], [i.__dict__ for i in issues])
        self.assertIn("mse_ffffffffffffffff", issues[0].detail)

    def test_links_check_flags_self_replaces(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - self", "mse_0123456789abcdef", ("mse_0123456789abcdef",)),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["self-replaces"], [i.__dict__ for i in issues])

    def test_links_check_guards_non_crockford_entry_yaml_refs(self):
        # Regression: real corpus ids include o/u/i/l (outside the strict
        # Crockford charset), e.g. codex-authored entries. A ref to one used to
        # be silently skipped by the extractor - bypassing the dangling and
        # forward-only guards while the graph still drew the edge.
        loose = "mse_37fpcovvuniqzlxk"  # contains o, u, i, l
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - earlier", "mse_0123456789abcdef", (loose,)),
            (f"2026-06-13 10:00 - later", loose, ()),
        )

        issues = check_session_links(cwd=cwd).issues

        # The earlier entry replaces the LATER loose-id entry: the forward-only
        # guard must now see and reject it instead of silently passing.
        self.assertEqual([i.kind for i in issues], ["replaces-postdates"], [i.__dict__ for i in issues])
        self.assertIn(loose, issues[0].detail)

    def test_links_check_flags_dangling_ref_to_non_crockford_id(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - only", "mse_0123456789abcdef", ("mse_gonevvuniqzlxkoo",)),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["dangling-replaces"], [i.__dict__ for i in issues])

    def test_links_check_accepts_backward_replaces_in_sidecar(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - original", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - replacement", "mse_ffffffffffffffff", ()),
        )
        self._link_sidecar(cwd, "2026-06-13", "mse_ffffffffffffffff", replaces=("mse_0123456789abcdef",))

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_reports_unclassified_sidecar_stub_as_warning(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 10:00 - pending classification", "mse_ffffffffffffffff", ()),
        )
        self._link_sidecar(
            cwd,
            "2026-06-13",
            "mse_ffffffffffffffff",
            classify_pending=True,
        )
        diagram = cwd / MEMORY_DIR_NAME / "sessions" / "diagrams" / "2026-06" / "2026-06-13.md"
        diagram.parent.mkdir(parents=True)
        diagram.write_text(
            "\n".join(
                [
                    "## 2026-06-13 10:00 - unrelated diagram metadata",
                    "",
                    "```yaml",
                    "entry_id: mse_ffffffffffffffff",
                    "classify_pending: true",
                    "```",
                    "",
                    "```mermaid",
                    "flowchart TD",
                    "  A --> B",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = check_session_links(cwd=cwd)

        pending = [issue for issue in result.issues if issue.kind == "sidecar-unclassified-stub"]
        self.assertTrue(result.ok)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].severity, "warning")
        self.assertIn("/sessions/links/", pending[0].file)

        import contextlib
        import io
        import os

        from memory_seed.cli import main as cli_main

        stdout = io.StringIO()
        stderr = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(cwd)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli_main(["links", "check"])
        finally:
            os.chdir(previous)
        self.assertEqual(exit_code, 0)
        self.assertIn("[warning] [sidecar-unclassified-stub]", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_links_check_accepts_backward_evolves_in_sidecar(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - base", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - refinement", "mse_ffffffffffffffff", ()),
        )
        self._link_sidecar(cwd, "2026-06-13", "mse_ffffffffffffffff", evolves=("mse_0123456789abcdef",))

        self.assertTrue(check_session_links(cwd=cwd).ok)

    def test_links_check_flags_dangling_replaces_in_sidecar(self):
        cwd = self.make_project()
        self._flat_session(cwd, "2026-06-13.md", ("2026-06-13 10:00 - only", "mse_ffffffffffffffff", ()))
        self._link_sidecar(cwd, "2026-06-13", "mse_ffffffffffffffff", replaces=("mse_zzzzzzzzzzzzzzzz",))

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["dangling-replaces"], [i.__dict__ for i in issues])

    def test_links_check_flags_postdating_replaces_in_sidecar(self):
        # Forward-only guard covers sidecar edges too, attributed to the SOURCE
        # entry's timestamp: an earlier entry may not replace a later one.
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - earlier", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - later", "mse_ffffffffffffffff", ()),
        )
        self._link_sidecar(cwd, "2026-06-13", "mse_0123456789abcdef", replaces=("mse_ffffffffffffffff",))

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["replaces-postdates"], [i.__dict__ for i in issues])

    def test_links_check_flags_orphan_link_sidecar(self):
        cwd = self.make_project()
        self._flat_session(cwd, "2026-06-13.md", ("2026-06-13 09:00 - only", "mse_0123456789abcdef", ()))
        self._link_sidecar(cwd, "2026-06-13", "mse_ffffffffffffffff", replaces=("mse_0123456789abcdef",))

        kinds = [i.kind for i in check_session_links(cwd=cwd).issues]

        self.assertIn("orphan-link-sidecar", kinds)

    def test_links_check_flags_link_sidecar_date_mismatch(self):
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - original", "mse_0123456789abcdef", ()),
            ("2026-06-13 10:00 - replacement", "mse_ffffffffffffffff", ()),
        )
        # Source entry logged 2026-06-13, block filed under 2026-06-14.
        self._link_sidecar(cwd, "2026-06-14", "mse_ffffffffffffffff", replaces=("mse_0123456789abcdef",))

        kinds = [i.kind for i in check_session_links(cwd=cwd).issues]

        self.assertIn("link-sidecar-date-mismatch", kinds)

    def test_links_check_flags_malformed_link_sidecar(self):
        cwd = self.make_project()
        self._flat_session(cwd, "2026-06-13.md", ("2026-06-13 09:00 - only", "mse_0123456789abcdef", ()))
        links = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-06"
        links.mkdir(parents=True, exist_ok=True)
        (links / "not-a-date.md").write_text("## whatever\n", encoding="utf-8")

        kinds = [i.kind for i in check_session_links(cwd=cwd).issues]

        self.assertIn("malformed-link-sidecar", kinds)

    def test_link_show_reflects_sidecar_edges(self):
        """`link show` must union late-authored link-sidecar edges into the
        effective graph (computed inverse included), matching what
        retrieval/MCP/Trace read - not just the raw entry-YAML edges."""
        import contextlib
        import io
        import os
        import sys as _sys
        from unittest import mock as _mock

        from memory_seed.cli import main as cli_main

        cwd = self.make_project()
        base = "mse_0123456789abcdef"
        refinement = "mse_ffffffffffffffff"
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - base", base, ()),
            ("2026-06-13 10:00 - refinement", refinement, ()),
        )
        # Recorded ONLY in a link sidecar (not in either entry's YAML).
        self._link_sidecar(cwd, "2026-06-13", refinement, evolves=(base,))

        def run(entry_id):
            buffer = io.StringIO()
            prev = os.getcwd()
            os.chdir(cwd)  # the link handler resolves cwd from Path(".")
            try:
                with _mock.patch.object(_sys, "argv", ["memory-seed", "link", "show", entry_id]), \
                        contextlib.redirect_stdout(buffer):
                    code = cli_main()
            finally:
                os.chdir(prev)
            return code, buffer.getvalue()

        code_ref, out_ref = run(refinement)
        code_base, out_base = run(base)

        self.assertEqual(code_ref, 0, out_ref)
        self.assertEqual(code_base, 0, out_base)
        # The sidecar evolves edge is visible from both ends of the graph.
        self.assertIn(f"evolves (1): {base}", out_ref)
        self.assertIn(f"evolved_by (1): {refinement}", out_base)

    def test_links_check_accepts_backward_evolves(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - original", "mse_0123456789abcdef")
            + self._entry_yaml(
                "2026-06-13 10:00 - refinement", "mse_ffffffffffffffff", "evolves:", "  - mse_0123456789abcdef"
            ),
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_flags_dangling_evolves(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - only", "mse_0123456789abcdef", "evolves:", "  - mse_zzzzzzzzzzzzzzzz"),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["dangling-evolves"], [i.__dict__ for i in issues])
        self.assertIn("mse_zzzzzzzzzzzzzzzz", issues[0].detail)

    def test_links_check_flags_postdating_evolves(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - earlier", "mse_0123456789abcdef", "evolves:", "  - mse_ffffffffffffffff")
            + self._entry_yaml("2026-06-13 10:00 - later", "mse_ffffffffffffffff"),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["evolves-postdates"], [i.__dict__ for i in issues])

    def test_links_check_flags_self_evolves(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - self", "mse_0123456789abcdef", "evolves:", "  - mse_0123456789abcdef"),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["self-evolves"], [i.__dict__ for i in issues])

    def test_links_check_flags_evolves_cycle_between_same_minute_entries(self):
        # Same-minute entries defeat the postdates ordering, so the DFS cycle
        # guard has to catch a mutual evolves pair - within the evolves kind
        # only, never mixed with replaces edges.
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - a", "mse_aaaaaaaaaaaaaaaa", "evolves:", "  - mse_bbbbbbbbbbbbbbbb")
            + self._entry_yaml("2026-06-13 09:00 - b", "mse_bbbbbbbbbbbbbbbb", "evolves:", "  - mse_aaaaaaaaaaaaaaaa"),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertIn("evolves-cycle", [i.kind for i in issues], [i.__dict__ for i in issues])
        cycle_issue = next(i for i in issues if i.kind == "evolves-cycle")
        self.assertIn("evolution cycle", cycle_issue.detail)

    def test_links_check_flags_authored_inverse_fields(self):
        # Append-only enforcement: the computed inverses live only in the
        # derived read layer; a stored key is a named integrity error, not a
        # silently ignored no-op.
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml("2026-06-13 09:00 - a", "mse_0123456789abcdef", "evolved_by:", "  - mse_ffffffffffffffff")
            + self._entry_yaml("2026-06-13 10:00 - b", "mse_ffffffffffffffff", "replaced_by:", "  - mse_0123456789abcdef"),
        )

        issues = check_session_links(cwd=cwd).issues

        kinds = [i.kind for i in issues]
        self.assertEqual(kinds.count("authored-inverse-field"), 2, [i.__dict__ for i in issues])
        details = " ".join(i.detail for i in issues if i.kind == "authored-inverse-field")
        self.assertIn("evolved_by", details)
        self.assertIn("replaced_by", details)

    def test_links_check_accepts_valid_continuity_blocks(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml(
                "2026-06-13 09:00 - lineage", "mse_0123456789abcdef",
                "continuity:",
                "  - kind: rename",
                "    from: memory_seed/lense.py",
                "    to: memory_trace/lense.py",
                "  - kind: migration",
                "    from: .AGENTS/",
                "    to: .memory-seed/",
                "  - kind: removal",
                "    from: memory-seed lense command",
            ),
        )

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_flags_every_malformed_continuity_shape(self):
        cwd = self.make_project()
        self._flat_session_raw(
            cwd,
            "2026-06-13.md",
            self._entry_yaml(
                "2026-06-13 09:00 - lineage", "mse_0123456789abcdef",
                "continuity:",
                "  - kind: refactor",           # unknown kind
                "    from: a",
                "  - kind: rename",             # rename without to
                "    from: b",
                "  - kind: removal",            # removal with to
                "    from: c",
                "    to: d",
                "  - kind: migration",          # missing from
                "    to: e",
            ),
        )

        issues = check_session_links(cwd=cwd).issues

        kinds = [i.kind for i in issues]
        self.assertEqual(kinds.count("malformed-continuity"), 4, [i.__dict__ for i in issues])
        details = " ".join(i.detail for i in issues)
        self.assertIn("refactor", details)
        self.assertIn("has no to", details)
        self.assertIn("must not have to", details)
        self.assertIn("has no from", details)

    def test_links_check_flags_malformed_commit_hash_without_git(self):
        # Format validation applies even outside a git repo; existence is skipped.
        cwd = self.make_project()
        self._flat_session_with_commits(cwd, "abc123")

        issues = check_session_links(cwd=cwd).issues

        self.assertEqual([i.kind for i in issues], ["malformed-commit-hash"], [i.__dict__ for i in issues])
        self.assertIn("abc123", issues[0].detail)

    def test_links_check_skips_commit_existence_without_git(self):
        cwd = self.make_project()
        self._flat_session_with_commits(cwd, "a" * 40)

        result = check_session_links(cwd=cwd)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_validates_commit_existence_in_git_repo(self):
        cwd = self.make_project()
        head = self._git_repo_with_commit(cwd)
        self._flat_session_with_commits(cwd, head, "f" * 40)

        issues = check_session_links(cwd=cwd).issues

        # The real HEAD passes; the fabricated hash is flagged.
        self.assertEqual([i.kind for i in issues], ["unknown-commit"], [i.__dict__ for i in issues])
        self.assertIn("f" * 40, issues[0].detail)

    @pytest.mark.integration
    def test_links_check_skips_commit_existence_in_shallow_clone(self):
        import subprocess

        cwd = self.make_project()
        self._git_repo_with_commit(cwd)
        # A shallow clone (what CI checkouts default to) genuinely lacks
        # historical commits: "no such commit" is indistinguishable from
        # "outside the fetched window", so unknown-commit must not fire.
        shallow = Path(tempfile.mkdtemp(prefix="mseed-shallow-"))
        self.addCleanup(lambda: shutil.rmtree(shallow, ignore_errors=True))
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1",
             cwd.as_uri().replace("file:///", "file:///"), str(shallow / "clone")],
            check=True, capture_output=True, timeout=60,
        )
        clone = shallow / "clone"
        self._flat_session_with_commits(clone, "f" * 40)

        result = check_session_links(cwd=clone)

        self.assertTrue(result.ok, [i.__dict__ for i in result.issues])

    def test_links_check_flags_replaces_cycle_between_same_minute_entries(self):
        # Same-minute entries slip past the postdates comparison; the DFS
        # cycle guard is what catches a mutual supersession there.
        cwd = self.make_project()
        self._flat_session(
            cwd,
            "2026-06-13.md",
            ("2026-06-13 09:00 - first", "mse_0123456789abcdef", ("mse_ffffffffffffffff",)),
            ("2026-06-13 09:00 - second", "mse_ffffffffffffffff", ("mse_0123456789abcdef",)),
        )

        issues = check_session_links(cwd=cwd).issues

        self.assertIn("replaces-cycle", [i.kind for i in issues], [i.__dict__ for i in issues])
        cycle_issue = next(i for i in issues if i.kind == "replaces-cycle")
        self.assertIn("mse_0123456789abcdef", cycle_issue.detail)
        self.assertIn("mse_ffffffffffffffff", cycle_issue.detail)

    def test_decision_density_advisory_warns_but_never_errors(self):
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        three = (
            "## 2026-06-01 09:00 - Batched\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Decisions\n\n"
            "#### D1 - one\n\n- D: a\n- R: r\n\n"
            "#### D2 - two\n\n- D: b\n- R: r\n\n"
            "#### D3 - three\n\n- D: c\n- R: r\n"
        )
        (sessions / "2026-06-01.md").write_text(three, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        # A well-formed entry can still be worth splitting: advise, never fail.
        self.assertTrue(result.ok)
        self.assertEqual([i.severity for i in result.issues], ["warning"])
        self.assertEqual(result.issues[0].kind, "entry-decision-density")
        self.assertIn("3 decisions", result.issues[0].detail)

    def test_decision_density_advisory_is_quiet_below_the_threshold(self):
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        two = (
            "## 2026-06-01 09:00 - One deliberation\n\n```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Decisions\n\n"
            "#### D1 - one\n\n- D: a\n- R: r\n\n"
            "#### D2 - two\n\n- D: b\n- R: r\n"
        )
        (sessions / "2026-06-01.md").write_text(two, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        # Two decisions settled together is the sanctioned multi-decision shape.
        self.assertTrue(result.ok)
        self.assertEqual(result.issues, [])

    def test_future_timestamp_advisory_warns_but_never_errors(self):
        cwd = self.make_project()
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        future = (
            "## 2126-01-01 09:00 - Stamped a century ahead\n\n"
            "```yaml\nentry_id: ms-aaaaaaaa\n```\n\n"
            "### Decision\n\n- D: a\n- R: r\n"
        )
        (sessions / "2126-01-01.md").write_text(future, encoding="utf-8")

        result = check_session_links(cwd=cwd)

        # A drifted stamp is a smell, never an integrity failure: historical
        # corpora may contain known drifted-but-published entries and
        # append-only forbids restamping them.
        self.assertTrue(result.ok)
        self.assertEqual([i.severity for i in result.issues], ["warning"])
        self.assertEqual(result.issues[0].kind, "entry-future-timestamp")
        self.assertIn("ms-aaaaaaaa", result.issues[0].detail)
        self.assertIn("2126-01-01 09:00", result.issues[0].detail)

    # --- Ref grammar: the two silent corruptions, and decision-level refs ---

    def _decision_corpus(self, cwd):
        """Two entries: an older one carrying D1/D2, a newer one to refer from."""
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "2026-06-01.md").write_text(
            "## 2026-06-01 09:00 - Older\n\n```yaml\nentry_id: mse_aaaaaaaaaaaaaaaa\n```\n\n"
            "### Decisions\n\n#### D1 - first\n\n- D: a\n- R: b\n\n#### D2 - second\n\n- D: c\n- R: d\n",
            encoding="utf-8",
        )
        (sessions / "2026-06-02.md").write_text(
            "## 2026-06-02 09:00 - Newer\n\n```yaml\nentry_id: mse_bbbbbbbbbbbbbbbb\n```\n\n"
            "### Decision\n\n- D: x\n- R: y\n",
            encoding="utf-8",
        )

    def test_suffixed_ref_is_an_error_not_a_silent_truncation(self):
        # The 2026-07-21 defect: a section-anchor ref matched only on its
        # entry-id prefix, so the file LOOKED decision-level, behaved
        # entry-level, and links check reported nothing at all.
        cwd = self.make_project()
        self._decision_corpus(cwd)
        self._link_sidecar(
            cwd, "2026-06-02", "mse_bbbbbbbbbbbbbbbb",
            evolves=["mse_aaaaaaaaaaaaaaaa#decision"],
        )
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        self.assertIn("malformed-link-ref", [i.kind for i in result.issues])

    def test_indented_comment_in_an_edge_list_creates_no_phantom_edge(self):
        # Worse than truncation: an INDENTED comment had its ids extracted as
        # real edges, inventing an edge nobody authored. The id below exists
        # nowhere, so if it were still extracted it would surface as dangling.
        cwd = self.make_project()
        self._decision_corpus(cwd)
        d = cwd / MEMORY_DIR_NAME / "sessions" / "links" / "2026-06"
        d.mkdir(parents=True, exist_ok=True)
        (d / "2026-06-02.md").write_text(
            "## 2026-06-02 10:00 - edge\n\n```yaml\nentry_id: mse_bbbbbbbbbbbbbbbb\nevolves:\n"
            "  - mse_aaaaaaaaaaaaaaaa\n  # candidate: mse_zzzzzzzzzzzzzzzz\n```\n",
            encoding="utf-8",
        )
        result = check_session_links(cwd=cwd)
        self.assertTrue(result.ok, [i.detail for i in result.issues if i.severity == "error"])
        self.assertNotIn("mse_zzzzzzzzzzzzzzzz", " ".join(i.detail for i in result.issues))

    def test_decision_ref_resolves_against_the_targets_real_ordinals(self):
        cwd = self.make_project()
        self._decision_corpus(cwd)
        self._link_sidecar(
            cwd, "2026-06-02", "mse_bbbbbbbbbbbbbbbb",
            evolves=["mse_aaaaaaaaaaaaaaaa:d2"],
        )
        self.assertTrue(check_session_links(cwd=cwd).ok)

    def test_decision_ref_to_a_missing_ordinal_is_dangling(self):
        cwd = self.make_project()
        self._decision_corpus(cwd)
        self._link_sidecar(
            cwd, "2026-06-02", "mse_bbbbbbbbbbbbbbbb",
            evolves=["mse_aaaaaaaaaaaaaaaa:d9"],
        )
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        self.assertIn("dangling-decision-ref", [i.kind for i in result.issues])

    # The same two corruptions, but in an entry's OWN ```yaml frontmatter and
    # per-user file frontmatter - the paths that kept scraping the region text
    # after the sidecar path was migrated, until _entry_level_ref_ids replaced
    # them. Sidecar coverage is above; these pin the entry side.

    def test_indented_comment_in_entry_frontmatter_creates_no_phantom_edge(self):
        cwd = self.make_project()
        self._decision_corpus(cwd)
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        # Newer entry evolves the older (forward-only, valid); the indented
        # candidate comment names an id that exists nowhere. A phantom
        # extraction would surface it as dangling-evolves.
        (sessions / "2026-06-02.md").write_text(
            "## 2026-06-02 09:00 - Newer\n\n```yaml\nentry_id: mse_bbbbbbbbbbbbbbbb\nevolves:\n"
            "  - mse_aaaaaaaaaaaaaaaa\n  # candidate: mse_zzzzzzzzzzzzzzzz\n```\n\n"
            "### Decision\n\n- D: x\n- R: y\n",
            encoding="utf-8",
        )
        result = check_session_links(cwd=cwd)
        self.assertTrue(result.ok, [i.detail for i in result.issues if i.severity == "error"])
        self.assertNotIn("mse_zzzzzzzzzzzzzzzz", " ".join(i.detail for i in result.issues))

    def test_decision_ref_in_entry_frontmatter_is_valid_write_time_grammar(self):
        # `:dN` in an entry's own replaces/evolves lists is the write-time
        # grammar (JNL's 2026-07-24 direction). A ref to an existing ordinal on
        # an older multi-decision entry validates clean - no misplaced flag, no
        # truncation to an entry-level edge.
        cwd = self.make_project()
        self._decision_corpus(cwd)
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        (sessions / "2026-06-02.md").write_text(
            "## 2026-06-02 09:00 - Newer\n\n```yaml\nentry_id: mse_bbbbbbbbbbbbbbbb\nevolves:\n"
            "  - mse_aaaaaaaaaaaaaaaa:d2\n```\n\n### Decision\n\n- D: x\n- R: y\n",
            encoding="utf-8",
        )
        result = check_session_links(cwd=cwd)
        self.assertTrue(result.ok, [i.detail for i in result.issues if i.severity == "error"])
        self.assertNotIn("misplaced-decision-ref", [i.kind for i in result.issues])

    def test_entry_frontmatter_decision_ref_to_missing_ordinal_is_dangling(self):
        cwd = self.make_project()
        self._decision_corpus(cwd)
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        (sessions / "2026-06-02.md").write_text(
            "## 2026-06-02 09:00 - Newer\n\n```yaml\nentry_id: mse_bbbbbbbbbbbbbbbb\nevolves:\n"
            "  - mse_aaaaaaaaaaaaaaaa:d9\n```\n\n### Decision\n\n- D: x\n- R: y\n",
            encoding="utf-8",
        )
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        self.assertIn("dangling-decision-ref", [i.kind for i in result.issues])

    def test_entry_frontmatter_decision_ref_in_related_entries_is_still_misplaced(self):
        # related_entries stays entry-level everywhere; the write-time grammar
        # covers only the lifecycle lists.
        cwd = self.make_project()
        self._decision_corpus(cwd)
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        (sessions / "2026-06-02.md").write_text(
            "## 2026-06-02 09:00 - Newer\n\n```yaml\nentry_id: mse_bbbbbbbbbbbbbbbb\nrelated_entries:\n"
            "  - mse_aaaaaaaaaaaaaaaa:d2\n```\n\n### Decision\n\n- D: x\n- R: y\n",
            encoding="utf-8",
        )
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        self.assertIn("misplaced-decision-ref", [i.kind for i in result.issues])
        self.assertEqual(
            1, sum(1 for i in result.issues if i.kind == "misplaced-decision-ref")
        )

    def test_entry_frontmatter_decision_ref_postdating_is_rejected(self):
        # Forward-only holds for entry-yaml decision refs exactly as for
        # sidecar ones: the OLDER entry referencing a NEWER entry's decision is
        # decision-ref-postdates.
        cwd = self.make_project()
        self._decision_corpus(cwd)
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        (sessions / "2026-05-31.md").write_text(
            "## 2026-05-31 09:00 - Oldest\n\n```yaml\nentry_id: mse_cccccccccccccccc\nevolves:\n"
            "  - mse_aaaaaaaaaaaaaaaa:d2\n```\n\n### Decision\n\n- D: x\n- R: y\n",
            encoding="utf-8",
        )
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        self.assertIn("decision-ref-postdates", [i.kind for i in result.issues])

    def test_registered_nonstandard_id_ref_is_not_newly_flagged(self):
        # _ENTRY_ID_RE accepts any \\S+ as an entry_id, so an entry can carry a
        # non-standard id that the stricter ref grammar would reject. The old
        # scrape silently ignored a ref to such an id; the migration must too, or
        # a registered entry becomes un-referenceable and a clean corpus breaks.
        # (Real minted ids all match the strict grammar - this guards the general
        # case the retrieval parity fixture exercises with `ms-bootstrap`.)
        cwd = self.make_project()
        self._decision_corpus(cwd)
        sessions = cwd / MEMORY_DIR_NAME / "sessions"
        (sessions / "2026-05-31.md").write_text(
            "## 2026-05-31 08:00 - Oddly named\n\n```yaml\nentry_id: ms-oddname\n```\n\n"
            "### Decision\n\n- D: a\n- R: b\n",
            encoding="utf-8",
        )
        (sessions / "2026-06-02.md").write_text(
            "## 2026-06-02 09:00 - Newer\n\n```yaml\nentry_id: mse_bbbbbbbbbbbbbbbb\nrelated_entries:\n"
            "  - ms-oddname\n```\n\n### Decision\n\n- D: x\n- R: y\n",
            encoding="utf-8",
        )
        result = check_session_links(cwd=cwd)
        self.assertTrue(result.ok, [i.detail for i in result.issues if i.severity == "error"])

    def test_singular_decision_entry_is_addressable_as_d1(self):
        # The convention that makes the scheme total rather than partial:
        # single-decision entries are the corpus majority.
        cwd = self.make_project()
        self._decision_corpus(cwd)
        (cwd / MEMORY_DIR_NAME / "sessions" / "2026-06-03.md").write_text(
            "## 2026-06-03 09:00 - Newest\n\n```yaml\nentry_id: mse_cccccccccccccccc\n```\n\n"
            "### Decision\n\n- D: x\n- R: y\n",
            encoding="utf-8",
        )
        self._link_sidecar(
            cwd, "2026-06-03", "mse_cccccccccccccccc",
            evolves=["mse_bbbbbbbbbbbbbbbb:d1"],
        )
        self.assertTrue(check_session_links(cwd=cwd).ok)

        # The negative half is what makes this test discriminate. Without it it
        # passes against the OLD code too, which truncated `:d1` to a valid
        # entry id and never looked at the ordinal at all. A singular entry has
        # d1 and nothing else, so d2 must be rejected.
        self._link_sidecar(
            cwd, "2026-06-03", "mse_cccccccccccccccc",
            evolves=["mse_bbbbbbbbbbbbbbbb:d2"], heading_time="11:00",
        )
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        self.assertIn("dangling-decision-ref", [i.kind for i in result.issues])

    def test_intra_entry_decision_ref_is_rejected(self):
        # Decisions of one entry are contemporaneous, so there is no order to
        # record and the forward-only guard would have nothing to check.
        cwd = self.make_project()
        self._decision_corpus(cwd)
        self._link_sidecar(
            cwd, "2026-06-01", "mse_aaaaaaaaaaaaaaaa",
            evolves=["mse_aaaaaaaaaaaaaaaa:d1"],
        )
        result = check_session_links(cwd=cwd)
        self.assertFalse(result.ok)
        self.assertIn("intra-entry-decision-ref", [i.kind for i in result.issues])
