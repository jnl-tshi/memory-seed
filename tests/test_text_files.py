import json
import tempfile
import unittest
import unicodedata
from pathlib import Path

from memory_seed.text_files import (
    read_json_file,
    read_text_file,
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
