from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any


CANONICAL_ENCODING = "utf-8"
CANONICAL_NEWLINE = "\n"


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")


def read_text_file(path: Path) -> str:
    return path.read_text(encoding=CANONICAL_ENCODING)


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        normalize_text(content),
        encoding=CANONICAL_ENCODING,
        newline=CANONICAL_NEWLINE,
    )


def append_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding=CANONICAL_ENCODING, newline=CANONICAL_NEWLINE) as file:
        file.write(normalize_text(content))


def read_json_file(path: Path) -> Any:
    return json.loads(read_text_file(path))


def write_json_file(path: Path, data: Any, *, indent: int = 2) -> None:
    text = json.dumps(data, indent=indent, ensure_ascii=False) + "\n"
    write_text_file(path, text)
