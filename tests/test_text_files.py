import json
import unittest
import unicodedata
from pathlib import Path

from memory_seed.text_files import (
    read_json_file,
    read_text_file,
    write_json_file,
    write_text_file,
)


NON_ASCII_SAMPLE = "Jean Nathan's memory - resume GBP EUR cafe naive Sao Paulo 中文 عربى 🚀"


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
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            data = {"message": NON_ASCII_SAMPLE}

            write_json_file(path, data)

            raw = path.read_bytes()
            self.assertNotIn(b"\\u", raw)
            self.assertEqual(json.loads(raw.decode("utf-8")), data)
            self.assertEqual(read_json_file(path), data)
