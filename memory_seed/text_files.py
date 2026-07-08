from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CANONICAL_ENCODING = "utf-8"
CANONICAL_NEWLINE = "\n"

TEXT_FILE_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILE_NAMES = {
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
}
SCAN_EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
MOJIBAKE_MARKERS = (
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\u00f0\u0178",
    "\u00ef\u00bb\u00bf",
    "\ufffd",
)


@dataclass(frozen=True)
class TextEncodingIssue:
    path: Path
    kind: str
    detail: str


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


def iter_project_text_files(root: Path) -> list[Path]:
    root = Path(root)
    if root.is_file():
        return [root] if _is_text_file(root) else []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            relative = path
        if _is_excluded_scan_path(relative):
            continue
        if _is_text_file(path):
            files.append(path)
    return sorted(files)


def scan_text_encoding(root: Path) -> list[TextEncodingIssue]:
    issues: list[TextEncodingIssue] = []
    for path in iter_project_text_files(root):
        issues.extend(scan_text_file_encoding(path))
    return issues


def scan_text_file_encoding(path: Path) -> list[TextEncodingIssue]:
    raw = path.read_bytes()
    issues: list[TextEncodingIssue] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        issues.append(TextEncodingIssue(path=path, kind="utf8-bom", detail="File starts with a UTF-8 BOM."))
    if b"\r\n" in raw:
        issues.append(TextEncodingIssue(path=path, kind="crlf", detail="File contains CRLF line endings."))
    try:
        text = raw.decode(CANONICAL_ENCODING)
    except UnicodeDecodeError as exc:
        issues.append(TextEncodingIssue(path=path, kind="invalid-utf8", detail=str(exc)))
        return issues
    marker = next((candidate for candidate in MOJIBAKE_MARKERS if candidate in text), None)
    if marker:
        issues.append(
            TextEncodingIssue(
                path=path,
                kind="likely-mojibake",
                detail=f"Text contains likely mojibake marker {marker!r}.",
            )
        )
    return issues


def encoding_issue_to_dict(issue: TextEncodingIssue, *, root: Path | None = None) -> dict[str, str]:
    path = issue.path
    if root is not None:
        try:
            path_text = path.relative_to(root).as_posix()
        except ValueError:
            path_text = path.as_posix()
    else:
        path_text = path.as_posix()
    return {"path": path_text, "kind": issue.kind, "detail": issue.detail}


def _is_text_file(path: Path) -> bool:
    return path.name in TEXT_FILE_NAMES or path.suffix.lower() in TEXT_FILE_SUFFIXES


def _is_excluded_scan_path(relative: Path) -> bool:
    parts = set(relative.parts)
    if parts & SCAN_EXCLUDED_PARTS:
        return True
    return ".memory-seed" in parts and "backups" in parts
