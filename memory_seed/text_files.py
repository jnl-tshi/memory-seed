from __future__ import annotations

import ast
import json
import os
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
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
REPAIR_BLOCKING_ISSUES = {"invalid-utf8", "likely-mojibake"}
IMPLICIT_TEXT_IO_ALLOW_MARKER = "memory-seed: allow-implicit-text-io"
STATIC_SCAN_EXCLUDED_PARTS = SCAN_EXCLUDED_PARTS | {"tests"}


@dataclass(frozen=True)
class TextEncodingIssue:
    path: Path
    kind: str
    detail: str
    line: int | None = None


@dataclass(frozen=True)
class TextRepairItem:
    path: Path
    issue_kinds: tuple[str, ...]


@dataclass
class TextRepairResult:
    planned: list[TextRepairItem]
    repaired: list[TextRepairItem]
    backed_up: list[Path]
    blocked: list[TextEncodingIssue]


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
    if not unicodedata.is_normalized("NFC", text):
        issues.append(
            TextEncodingIssue(
                path=path,
                kind="non-nfc",
                detail="Text is not normalized to Unicode NFC.",
            )
        )
    return issues


def scan_implicit_text_io(root: Path) -> list[TextEncodingIssue]:
    issues: list[TextEncodingIssue] = []
    root = Path(root)
    candidates = [root] if root.is_file() else sorted(root.rglob("*.py"))
    for path in candidates:
        if path.suffix.lower() != ".py":
            continue
        try:
            relative = path.relative_to(root if root.is_dir() else root.parent)
        except ValueError:
            relative = path
        if set(relative.parts) & STATIC_SCAN_EXCLUDED_PARTS or _is_excluded_scan_path(relative):
            continue
        try:
            source = path.read_text(encoding=CANONICAL_ENCODING)
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        lines = source.splitlines()
        path_names = _path_variable_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            operation = _implicit_text_io_operation(node, path_names)
            if operation is None or _call_has_explicit_encoding(node):
                continue
            if operation == "open" and _call_uses_binary_mode(node):
                continue
            source_line = lines[node.lineno - 1] if 0 < node.lineno <= len(lines) else ""
            if IMPLICIT_TEXT_IO_ALLOW_MARKER in source_line:
                continue
            issues.append(
                TextEncodingIssue(
                    path=path,
                    kind="implicit-text-io",
                    detail=f"{operation}() uses text mode without an explicit encoding.",
                    line=node.lineno,
                )
            )
    return sorted(issues, key=lambda issue: (issue.path.as_posix(), issue.line or 0))


def repair_text_encoding(
    root: Path,
    *,
    dry_run: bool = False,
    timestamp: str | None = None,
) -> TextRepairResult:
    root = Path(root).resolve()
    issues_by_path: dict[Path, list[TextEncodingIssue]] = {}
    for issue in scan_text_encoding(root):
        issues_by_path.setdefault(issue.path, []).append(issue)

    planned: list[TextRepairItem] = []
    blocked: list[TextEncodingIssue] = []
    normalized_by_path: dict[Path, bytes] = {}
    for path in iter_project_text_files(root):
        path_issues = issues_by_path.get(path, [])
        blocking = [issue for issue in path_issues if issue.kind in REPAIR_BLOCKING_ISSUES]
        if blocking:
            blocked.extend(blocking)
            continue
        try:
            raw = path.read_bytes()
            normalized = _normalized_utf8_bytes(raw)
        except (OSError, UnicodeDecodeError):
            continue
        if normalized == raw:
            continue
        kinds = tuple(sorted({issue.kind for issue in path_issues} or {"normalization"}))
        item = TextRepairItem(path=path, issue_kinds=kinds)
        planned.append(item)
        normalized_by_path[path] = normalized

    if dry_run:
        return TextRepairResult(planned=planned, repaired=[], backed_up=[], blocked=blocked)

    project_root, backup_root = _encoding_backup_paths(root, timestamp=timestamp)
    repaired: list[TextRepairItem] = []
    backed_up: list[Path] = []
    for item in planned:
        relative = _relative_for_backup(item.path, project_root)
        backup_path = backup_root / relative
        _atomic_write_bytes(backup_path, item.path.read_bytes())
        _atomic_write_bytes(item.path, normalized_by_path[item.path])
        repaired.append(item)
        backed_up.append(backup_path)
    if backed_up:
        _ensure_backup_gitignore(project_root)

    return TextRepairResult(
        planned=planned,
        repaired=repaired,
        backed_up=backed_up,
        blocked=blocked,
    )


def encoding_issue_to_dict(
    issue: TextEncodingIssue,
    *,
    root: Path | None = None,
) -> dict[str, str | int]:
    path = issue.path
    if root is not None:
        try:
            path_text = path.relative_to(root).as_posix()
        except ValueError:
            path_text = path.as_posix()
    else:
        path_text = path.as_posix()
    data: dict[str, str | int] = {
        "path": path_text,
        "kind": issue.kind,
        "detail": issue.detail,
    }
    if issue.line is not None:
        data["line"] = issue.line
    return data


def _is_text_file(path: Path) -> bool:
    return path.name in TEXT_FILE_NAMES or path.suffix.lower() in TEXT_FILE_SUFFIXES


def _is_excluded_scan_path(relative: Path) -> bool:
    path_parts = relative.parts
    parts = set(path_parts)
    if parts & SCAN_EXCLUDED_PARTS:
        return True
    if len(path_parts) >= 2 and path_parts[0:2] == (".claude", "worktrees"):
        return True
    for index, part in enumerate(path_parts[:-1]):
        if part == ".memory-seed" and path_parts[index + 1] in {"archive", "backups"}:
            return True
    return False


def _implicit_text_io_operation(node: ast.Call, path_names: set[str]) -> str | None:
    if isinstance(node.func, ast.Name) and node.func.id == "open":
        return "open"
    if not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr in {"read_text", "write_text"}:
        return node.func.attr
    if node.func.attr == "open" and (
        _is_path_constructor(node.func.value)
        or isinstance(node.func.value, ast.Name)
        and node.func.value.id in path_names
    ):
        return "open"
    return None


def _is_path_constructor(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id == "Path"
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "pathlib"
        and node.func.attr == "Path"
    )


def _path_variable_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_path_constructor(node.value):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if _is_path_annotation(node.annotation) or (
                node.value is not None and _is_path_constructor(node.value)
            ):
                names.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                if argument.annotation is not None and _is_path_annotation(argument.annotation):
                    names.add(argument.arg)
    return names


def _is_path_annotation(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "Path"
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "pathlib"
        and node.attr == "Path"
    )


def _call_has_explicit_encoding(node: ast.Call) -> bool:
    return any(keyword.arg == "encoding" for keyword in node.keywords)


def _call_uses_binary_mode(node: ast.Call) -> bool:
    mode_node: ast.AST | None = None
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode_node = keyword.value
            break
    if mode_node is None:
        if isinstance(node.func, ast.Name) and len(node.args) > 1:
            mode_node = node.args[1]
        elif isinstance(node.func, ast.Attribute) and node.args:
            mode_node = node.args[0]
    return (
        isinstance(mode_node, ast.Constant)
        and isinstance(mode_node.value, str)
        and "b" in mode_node.value
    )


def _normalized_utf8_bytes(raw: bytes) -> bytes:
    text = raw.decode(CANONICAL_ENCODING)
    if text.startswith("\ufeff"):
        text = text[1:]
    return normalize_text(text).encode(CANONICAL_ENCODING)


def _encoding_backup_paths(root: Path, *, timestamp: str | None) -> tuple[Path, Path]:
    start = root.parent if root.is_file() else root
    project_root = start
    for candidate in (start, *start.parents):
        if (candidate / ".memory-seed").is_dir():
            project_root = candidate
            break
    stamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = project_root / ".memory-seed" / "backups" / "encoding" / stamp
    return project_root, backup_root


def _relative_for_backup(path: Path, project_root: Path) -> Path:
    try:
        return path.relative_to(project_root)
    except ValueError:
        return Path(path.name)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _ensure_backup_gitignore(project_root: Path) -> None:
    gitignore = project_root / ".gitignore"
    try:
        existing = read_text_file(gitignore) if gitignore.exists() else ""
    except (OSError, UnicodeDecodeError):
        return
    entry = ".memory-seed/backups/"
    if entry in {line.strip() for line in existing.splitlines()}:
        return
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    write_text_file(gitignore, prefix + entry + "\n")
