import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.core import (
    MEMORY_DIR_NAME,
    compact_sessions,
    generate_session_entry_id,
    iter_session_documents,
    resolve_runtime,
)


class CoreMiscTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

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

    def _make_sessions(self, cwd, entries):
        sessions_dir = cwd / MEMORY_DIR_NAME / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in entries.items():
            path = sessions_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_entry_body_format_issues_flags_malformed_draft(self):
        from memory_seed.core import entry_body_format_issues as fmt

        # Well-formed shapes produce no issues.
        self.assertEqual(fmt("### Decision\n\n- D: chose X\n- R: because Y"), [])
        self.assertEqual(fmt("### Summary\n\n- a plain note, no DRAFT"), [])  # DRAFT not forced
        self.assertEqual(
            fmt("### Decisions\n\n#### D1 - a\n\n- D: x\n- R: y\n\n#### D2 - b\n\n- D: z\n- R: w"), []
        )
        # Nested '- R:' under an inline '- D1:' under '### Decisions' is a valid,
        # readable style - must NOT false-positive as 'D without R'.
        self.assertEqual(fmt("### Decisions\n\n- D1: a\n  - R: reason\n  - F: file"), [])

        # Bare labels (no '- ') and no heading.
        bare = fmt("D: chose X\nR: because Y")
        self.assertTrue(any("not list items" in i for i in bare))
        self.assertTrue(any("no '### Decision'" in i for i in bare))
        # Several decisions crammed under a singular '### Decision'.
        self.assertTrue(
            any("singular '### Decision'" in i for i in fmt("### Decision\n\n- D1: a\n- R: y\n- D2: b\n- R: z"))
        )
        # A decision with no reason.
        self.assertTrue(any("no reason (R:)" in i for i in fmt("### Decision\n\n- D: only a decision")))

    def test_decision_count_reads_both_entry_styles(self):
        from memory_seed.core import entry_body_decision_count

        headings = "#### D1 - a\n\n- D: x\n- R: y\n\n#### D2 - b\n\n- D: z\n- R: y\n"
        bullets = "### Decision\n\n- D: only one\n- R: y\n"

        # '#### Dn' subsections win; older '- D:' bullets are the fallback, so
        # the count is not inflated by counting both in the same entry.
        self.assertEqual(entry_body_decision_count(headings), 2)
        self.assertEqual(entry_body_decision_count(bullets), 1)
        self.assertEqual(entry_body_decision_count("### Summary\n\n- just a note\n"), 0)

    def test_entry_body_decisions_extracts_ordinal_name_and_bounded_text(self):
        from memory_seed.core import entry_body_decisions

        body = (
            "### Decisions\n\n"
            "#### D1 - First name\n\n- D: alpha\n- R: because\n\n"
            "#### D2 - Second name\n\n- D: beta\n- R: reasons\n\n"
            "### Validation\n\n- checked\n"
        )
        ds = entry_body_decisions(body)
        self.assertEqual([d.ordinal for d in ds], ["d1", "d2"])
        self.assertEqual([d.name for d in ds], ["First name", "Second name"])
        self.assertIn("beta", ds[1].text)
        # The trailing ### Validation is a new section, not part of d2.
        self.assertNotIn("checked", ds[1].text)

    def test_entry_body_decisions_singular_is_d1_with_no_name(self):
        from memory_seed.core import entry_body_decisions

        ds = entry_body_decisions("### Decision\n\n- D: only one\n- R: because\n")
        self.assertEqual(len(ds), 1)
        self.assertEqual(ds[0].ordinal, "d1")
        self.assertEqual(ds[0].name, "")
        self.assertIn("only one", ds[0].text)

    def test_entry_body_decisions_empty_without_a_decision_section(self):
        from memory_seed.core import entry_body_decisions

        self.assertEqual(entry_body_decisions("Just prose, no decision heading.\n"), [])

    def test_the_body_lint_sees_past_a_code_fence_in_the_body(self):
        # Regression: the body used to be split on fences[1], but the metadata
        # opener is '```yaml' and never equals a bare '```', so fences[1] was
        # really the opening fence of a code block in the BODY - everything
        # before it was discarded and the DRAFT lint audited only the tail. Any
        # entry quoting code was therefore exempt from the format check. This
        # entry's violation sits ahead of its code block, so it is only visible
        # if the body is anchored to the metadata closer.
        from memory_seed.core import check_entry_format

        text = (
            "## 2026-06-05 09:00 - Quotes code after a bad DRAFT body\n\n"
            "```yaml\nentry_id: ms-ffffffff\n```\n\n"
            "### Decision\n\n- D: A decision with no reason.\n\n"
            "```\nsome illustrative snippet\n```\n"
        )

        findings = check_entry_format(text)

        self.assertTrue(
            any("R is mandatory" in issue for _, issue in findings),
            "a code fence in the body must not hide the DRAFT lint from the body above it",
        )

    def test_cli_session_entry_id_reproduces_canonical_id(self):
        import contextlib
        import io
        import sys as _sys
        from unittest import mock as _mock

        from memory_seed.cli import main as cli_main

        argv = [
            "memory-seed", "session", "entry-id",
            "--timestamp", "2026-07-12 12:15",
            "--title", "Fuse Codex branches and align Trace packaging docs",
            "--user-initials", "JNL",
            "--agent-type", "codex",
        ]
        buffer = io.StringIO()
        with _mock.patch.object(_sys, "argv", argv), contextlib.redirect_stdout(buffer):
            exit_code = cli_main()

        self.assertEqual(exit_code, 0)
        # Deterministic: this metadata tuple reproduces a real corpus id.
        self.assertEqual(buffer.getvalue().strip(), "mse_kq3ba0cy9nkpqkm0")

    def test_find_trailer_commits_scans_memory_entry_trailer(self):
        from memory_seed.core import find_trailer_commits

        cwd = self.make_project()
        head = self._git_repo_with_commit(cwd, message="fix thing\n\nMemory-Entry: mse_0123456789abcdef")

        hits = find_trailer_commits(cwd, "mse_0123456789abcdef")
        misses = find_trailer_commits(cwd, "mse_ffffffffffffffff")

        self.assertEqual(len(hits), 1, hits)
        self.assertTrue(hits[0].startswith(head))
        self.assertEqual(misses, [])

    def test_find_trailer_commits_returns_none_outside_git(self):
        from memory_seed.core import find_trailer_commits

        cwd = self.make_project()

        self.assertIsNone(find_trailer_commits(cwd, "mse_0123456789abcdef"))

    def test_commit_reference_ids_unions_field_and_trailer_deduped(self):
        from memory_seed.core import commit_reference_ids

        cwd = self.make_project()
        head = self._git_repo_with_commit(
            cwd, message="do thing\n\nMemory-Entry: mse_0123456789abcdef"
        )
        # The field lists the trailered HEAD (dedup case) plus one other SHA.
        ids = commit_reference_ids(cwd, "mse_0123456789abcdef", (head, "b" * 40))

        # HEAD appears in both the field and the trailer scan but counts once.
        self.assertEqual(ids, {head, "b" * 40})

    def test_commit_reference_ids_field_only_outside_git(self):
        from memory_seed.core import commit_reference_ids

        cwd = self.make_project()  # no .git
        ids = commit_reference_ids(cwd, "mse_0123456789abcdef", ("a" * 40, "notasha"))

        # Trailer scan skips (no git); only the well-formed field SHA survives.
        self.assertEqual(ids, {"a" * 40})

    def test_session_entry_id_uses_80_bit_mse_format_and_is_metadata_deterministic(self):
        first = generate_session_entry_id(
            timestamp="2026-05-26 18:54",
            title="Bootstrap-generated memory and semantic MCP",
            user_initials="JN",
            agent_type="codex",
            project_path=".",
            subproject_path=None,
        )
        second = generate_session_entry_id(
            timestamp="2026-05-26 18:54",
            title="Bootstrap-generated memory and semantic MCP",
            user_initials="JN",
            agent_type="codex",
            project_path=".",
            subproject_path=None,
        )

        self.assertEqual(first, second)
        self.assertRegex(first, r"^mse_[0-9a-hjkmnp-tv-z]{16}$")
        self.assertEqual(len(first), len("mse_") + 16)

    def test_resolve_runtime_prefers_nearest_memory_seed(self):
        cwd = self.make_project()
        root_runtime = cwd / MEMORY_DIR_NAME
        subproject = cwd / "apps" / "mobile"
        sub_runtime = subproject / MEMORY_DIR_NAME
        root_runtime.mkdir(parents=True)
        sub_runtime.mkdir(parents=True)
        nested = subproject / "src"
        nested.mkdir()

        resolved = resolve_runtime(nested)

        self.assertEqual(resolved.workspace_root, subproject.resolve())
        self.assertEqual(resolved.memory_dir, sub_runtime.resolve())
        self.assertFalse(resolved.legacy)

    def test_resolve_runtime_falls_back_to_legacy_agents(self):
        cwd = self.make_project()
        legacy = cwd / ".AGENTS"
        legacy.mkdir()
        nested = cwd / "packages" / "core"
        nested.mkdir(parents=True)

        resolved = resolve_runtime(nested)

        self.assertEqual(resolved.workspace_root, cwd.resolve())
        self.assertEqual(resolved.memory_dir, legacy.resolve())
        self.assertTrue(resolved.legacy)

    def test_iter_session_documents_discovers_legacy_and_per_user_sessions(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2026-06-20.md": "## Legacy\n",
            "2026-06-21/jean.md": "## Jean\n",
            "2026-06-21/amina.md": "## Amina\n",
            "2026-06/2026-06-22.md": "## Month flat\n",
            "2026-06/2026-06-23/jean.md": "## Month Jean\n",
            "2026-07/2026-06-24.md": "## Month mismatch\n",
            "2026-07/2026-06-24/jean.md": "## Month user mismatch\n",
            "2026-06-21/README.md": "## Not a user\n",
            "2026-06-21/Bad_User.md": "## Invalid slug\n",
            "not-a-date/theo.md": "## Invalid date\n",
            "2026-06-22.md/readme.md": "## Invalid layout\n",
        })

        docs = list(iter_session_documents(cwd / MEMORY_DIR_NAME / "sessions"))

        self.assertEqual(
            [(doc.session_date, doc.user, doc.layout, doc.path.name) for doc in docs],
            [
                ("2026-06-20", None, "legacy-flat", "2026-06-20.md"),
                ("2026-06-21", "amina", "per-user-day", "amina.md"),
                ("2026-06-21", "jean", "per-user-day", "jean.md"),
                ("2026-06-22", None, "month-flat", "2026-06-22.md"),
                ("2026-06-23", "jean", "month-user", "jean.md"),
            ],
        )

    def test_compact_returns_headings_from_recent_sessions(self):
        cwd = self.make_project()
        today = __import__("datetime").date.today().isoformat()
        self._make_sessions(cwd, {
            f"{today}.md": "## First heading\n\nSome text.\n\n## Second heading\n\nMore text.\n",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, [f"{today}.md"])
        self.assertEqual(result.headings[today], ["First heading", "Second heading"])
        self.assertIn("Some text.", result.full_text)
        self.assertEqual(result.date_range, (today, today))

    def test_compact_respects_day_filter(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2020-01-01.md": "## Old entry\n\nOld text.\n",
            "2099-12-31.md": "## Future entry\n\nFuture text.\n",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, ["2099-12-31.md"])
        self.assertNotIn("Old text.", result.full_text)

    def test_compact_all_includes_every_session(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2020-01-01.md": "## Old entry\n",
            "2099-12-31.md": "## Future entry\n",
        })

        result = compact_sessions(cwd=cwd, scan_all=True)

        self.assertEqual(len(result.sessions_scanned), 2)
        self.assertIn("2020-01-01.md", result.sessions_scanned)
        self.assertIn("2099-12-31.md", result.sessions_scanned)

    def test_compact_all_includes_legacy_and_per_user_sessions(self):
        cwd = self.make_project()
        self._make_sessions(cwd, {
            "2026-06-20.md": "## Legacy entry\n\nLegacy text.\n",
            "2026-06-21/jean.md": "## Jean entry\n\nJean text.\n",
        })

        result = compact_sessions(cwd=cwd, scan_all=True)

        self.assertEqual(result.sessions_scanned, ["2026-06-20.md", "2026-06-21/jean.md"])
        self.assertEqual(result.headings["2026-06-20"], ["Legacy entry"])
        self.assertEqual(result.headings["2026-06-21/jean.md"], ["Jean entry"])
        self.assertIn("Legacy text.", result.full_text)
        self.assertIn("Jean text.", result.full_text)
        self.assertEqual(result.date_range, ("2026-06-20", "2026-06-21"))

    def test_compact_empty_sessions_returns_empty_result(self):
        cwd = self.make_project()

        result = compact_sessions(cwd=cwd)

        self.assertEqual(result.sessions_scanned, [])
        self.assertEqual(result.headings, {})
        self.assertEqual(result.full_text, "")
        self.assertIsNone(result.date_range)

    def test_compact_ignores_non_date_filenames(self):
        cwd = self.make_project()
        today = __import__("datetime").date.today().isoformat()
        self._make_sessions(cwd, {
            f"{today}.md": "## Valid\n",
            "notes.md": "## Should be ignored\n",
            "readme.txt": "not a session",
        })

        result = compact_sessions(cwd=cwd, days=7)

        self.assertEqual(result.sessions_scanned, [f"{today}.md"])
        self.assertNotIn("Should be ignored", result.full_text)

    def test_merge_routing_stanza_resyncs_on_body_change_only(self):
        # The no-churn guarantee: the block is rewritten only when its body
        # differs, not on a bare version bump (the block carries no version).
        from memory_seed.core import _merge_routing_stanza

        cwd = self.make_project()
        f = cwd / "HOST.md"
        f.write_text("# Host\n\nhost content\n", encoding="utf-8")

        self.assertTrue(_merge_routing_stanza(f))            # injected
        self.assertFalse(_merge_routing_stanza(f))           # identical -> no write
        # A different stanza body forces an in-place re-sync.
        changed = "<!-- BEGIN memory-seed -->\nnew body\n<!-- END memory-seed -->"
        self.assertTrue(_merge_routing_stanza(f, changed))
        self.assertFalse(_merge_routing_stanza(f, changed))
        self.assertIn("host content", f.read_text(encoding="utf-8"))
