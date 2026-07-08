import json
import tempfile
import unittest
import unicodedata
from pathlib import Path

from memory_seed.text_files import (
    repair_text_encoding,
    read_json_file,
    read_text_file,
    scan_implicit_text_io,
    scan_text_encoding,
    write_json_file,
    write_text_file,
)


NON_ASCII_SAMPLE = (
    "Jean Nathan's memory - resume GBP EUR cafe naive Sao Paulo "
    "\u4e2d\u6587 \u0639\u0631\u0628\u0649 \U0001f680"
)


class TextFilesTests(unittest.TestCase):
    def test_text_file_round_trip_uses_utf8_without_bom_and_lf(self):
        with self.subTest("round trip"):
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "session.md"
                content = "title\r\n" + unicodedata.normalize("NFD", NON_ASCII_SAMPLE) + "\r\n"

                write_text_file(path, content)

                raw = path.read_bytes()
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r\n", raw)
                self.assertEqual(
                    read_text_file(path),
                    "title\n" + unicodedata.normalize("NFC", NON_ASCII_SAMPLE) + "\n",
                )

    def test_json_file_round_trip_preserves_readable_unicode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            data = {"message": NON_ASCII_SAMPLE}

            write_json_file(path, data)

            raw = path.read_bytes()
            self.assertNotIn(b"\\u", raw)
            self.assertEqual(json.loads(raw.decode("utf-8")), data)
            self.assertEqual(read_json_file(path), data)

    def test_encoding_scan_reports_invalid_utf8_bom_crlf_and_mojibake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "good.md").write_bytes(b"Memory Seed\n")
            (root / "invalid.md").write_bytes(b"\xff\xfe\x00broken")
            (root / "bom.md").write_bytes(b"\xef\xbb\xbfhello\n")
            (root / "crlf.md").write_bytes(b"one\r\ntwo\r\n")
            (root / "mojibake.md").write_bytes("Bad dash: \u00e2\u20ac\u201d\n".encode("utf-8"))

            issues = scan_text_encoding(root)

        by_file = {}
        for issue in issues:
            by_file.setdefault(issue.path.name, set()).add(issue.kind)
        self.assertEqual(by_file["invalid.md"], {"invalid-utf8"})
        self.assertEqual(by_file["bom.md"], {"utf8-bom"})
        self.assertEqual(by_file["crlf.md"], {"crlf"})
        self.assertEqual(by_file["mojibake.md"], {"likely-mojibake"})
        self.assertNotIn("good.md", by_file)

    def test_encoding_scan_excludes_nested_worktrees_archives_and_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            excluded = [
                root / ".claude" / "worktrees" / "worker" / "bad.md",
                root / ".memory-seed" / "archive" / "2.1" / "bad.md",
                root / ".memory-seed" / "backups" / "encoding" / "bad.md",
            ]
            for path in excluded:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"alpha\r\n")

            issues = scan_text_encoding(root)

        self.assertEqual(issues, [])

    def test_encoding_check_cli_json_reports_issue_paths(self):
        import contextlib
        import io

        from memory_seed.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.md").write_bytes(b"\xef\xbb\xbfalpha\r\n")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["encoding", "check", str(root), "--json"])

        self.assertEqual(code, 1)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual({issue["kind"] for issue in payload["issues"]}, {"utf8-bom", "crlf"})
        self.assertEqual({issue["path"] for issue in payload["issues"]}, {"bad.md"})

    def test_encoding_repair_dry_run_then_backs_up_and_normalizes_safe_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "docs" / "sample.md"
            source.parent.mkdir()
            original = (
                b"\xef\xbb\xbf"
                + ("title\r\n" + unicodedata.normalize("NFD", "caf\u00e9") + "\r\n").encode("utf-8")
            )
            source.write_bytes(original)

            preview = repair_text_encoding(root, dry_run=True, timestamp="20260708-150000")

            self.assertEqual([item.path for item in preview.planned], [source])
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(preview.backed_up, [])

            result = repair_text_encoding(root, timestamp="20260708-150000")

            backup = root / ".memory-seed" / "backups" / "encoding" / "20260708-150000" / "docs" / "sample.md"
            self.assertEqual([item.path for item in result.repaired], [source])
            self.assertEqual(result.backed_up, [backup])
            self.assertEqual(backup.read_bytes(), original)
            self.assertEqual(source.read_bytes(), "title\ncaf\u00e9\n".encode("utf-8"))
            self.assertIn(".memory-seed/backups/", (root / ".gitignore").read_text(encoding="utf-8"))

    def test_encoding_repair_blocks_invalid_utf8_and_likely_mojibake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = root / "invalid.md"
            mojibake = root / "mojibake.md"
            invalid.write_bytes(b"\xffbroken\r\n")
            mojibake.write_bytes("Bad dash: \u00e2\u20ac\u201d\r\n".encode("utf-8"))

            result = repair_text_encoding(root, timestamp="20260708-150000")

            self.assertEqual(result.repaired, [])
            self.assertEqual(
                {(issue.path.name, issue.kind) for issue in result.blocked},
                {("invalid.md", "invalid-utf8"), ("mojibake.md", "likely-mojibake")},
            )
            self.assertEqual(invalid.read_bytes(), b"\xffbroken\r\n")
            self.assertEqual(mojibake.read_bytes(), "Bad dash: \u00e2\u20ac\u201d\r\n".encode("utf-8"))
            self.assertFalse((root / ".memory-seed" / "backups").exists())

    def test_static_scan_flags_implicit_text_io_but_allows_binary_and_explicit_exceptions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "package"
            package.mkdir()
            (package / "bad.py").write_text(
                "\n".join(
                    [
                        "from pathlib import Path",
                        "Path('a.md').read_text()",
                        "Path('b.md').write_text('x')",
                        "open('c.md')",
                        "Path('d.bin').open('rb')",
                        "Path('e.md').read_text(encoding='utf-8')",
                        "Path('legacy.md').read_text()  # memory-seed: allow-implicit-text-io",
                        "webbrowser.open('https://example.com')",
                        "output_path = Path('output.md')",
                        "output_path.open('w')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_fixture.py").write_text("open('fixture.md')\n", encoding="utf-8")
            worktree_file = root / ".claude" / "worktrees" / "worker" / "bad.py"
            worktree_file.parent.mkdir(parents=True)
            worktree_file.write_text("open('worker.md')\n", encoding="utf-8")

            issues = scan_implicit_text_io(root)

        self.assertEqual(
            [(issue.path.name, issue.line) for issue in issues],
            [("bad.py", 2), ("bad.py", 3), ("bad.py", 4), ("bad.py", 10)],
        )
        self.assertTrue(all(issue.kind == "implicit-text-io" for issue in issues))

    def test_production_python_uses_explicit_text_encoding(self):
        issues = scan_implicit_text_io(Path("memory_seed"))

        self.assertEqual(
            issues,
            [],
            "\n".join(f"{issue.path}:{issue.line}: {issue.detail}" for issue in issues),
        )

    def test_encoding_repair_cli_json_dry_run_previews_without_writing(self):
        import contextlib
        import io

        from memory_seed.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bad.md"
            source.write_bytes(b"\xef\xbb\xbfalpha\r\n")
            before = source.read_bytes()
            stdout = io.StringIO()
            stderr = io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["encoding", "repair", str(root), "--dry-run", "--json"])

            payload = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(payload["planned_count"], 1)
            self.assertEqual(payload["repaired_count"], 0)
            self.assertEqual(payload["blocked_count"], 0)
