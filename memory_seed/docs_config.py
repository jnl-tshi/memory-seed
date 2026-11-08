"""Project-local configuration for the document lifecycle lanes.

The planning profile creates the generic layout.  Existing projects that
predate the setting keep working through a narrow numbered-layout fallback;
once ``project.yaml`` declares ``docs.lanes``, that ordered list is the sole
lane registry used by both ``docs check`` and ``docs index``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

SEED_DOC_LANES = ("inbox", "todo", "reference")
SEED_DOC_ALLOWLIST = frozenset({"todo/completed"})

LEGACY_DOC_LANES = (
    "1_Inbox",
    "2_Todo",
    "3_Spec",
    "4_Reference",
    "5_Completed",
    "6_Rejected",
    "7_Replaced",
    "7_Superseded",
    "8_Deferred",
)
LEGACY_DOC_ALLOWLIST = frozenset(
    {
        "5_Completed/agent-templates",
        "4_Reference/memory-trace-phase0-baseline",
        "4_Reference/archived",
        "4_Reference/trace-humanised-dashboard-references",
        "3_Spec/draft",
        "3_Spec/deprecated",
    }
)


@dataclass(frozen=True)
class DocsLayout:
    lanes: tuple[str, ...]
    allowlist: frozenset[str]


_GLOB_MAGIC = re.compile(r"[*?[]")


def docs_folder_is_allowlisted(folder: str, allowlist: frozenset[str]) -> bool:
    """Return whether *folder* is covered by a configured directory rule.

    Literal entries own their complete subtree.  Glob entries are matched
    against the folder and each of its ancestors, so a rule such as
    ``handbook/*`` allows the matched directory and everything below it.
    Matching always uses docs-root-relative POSIX paths.
    """

    normalised = _normalise_path(folder, lane=False)
    if normalised is None:
        return False
    path = PurePosixPath(normalised)
    for pattern in allowlist:
        if not _GLOB_MAGIC.search(pattern):
            if normalised == pattern or normalised.startswith(f"{pattern}/"):
                return True
            continue
        candidates = (path, *path.parents)
        if any(candidate.as_posix() != "." and candidate.match(pattern) for candidate in candidates):
            return True
    return False


def _normalise_path(value: str, *, lane: bool) -> str | None:
    value = value.strip().strip("'\"").replace("\\", "/")
    if value.startswith("/"):
        return None
    value = value.strip("/")
    if not value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    if lane and len(path.parts) != 1:
        return None
    return path.as_posix()


def _inline_items(value: str) -> list[str] | None:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    body = value[1:-1].strip()
    return [] if not body else [item.strip() for item in body.split(",")]


def _docs_block(text: str) -> list[str] | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^docs\s*:\s*(?:#.*)?$", line):
            block: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate and not candidate[0].isspace():
                    break
                block.append(candidate)
            return block
    return None


def _list_from_block(block: list[str], key: str, *, lane: bool) -> tuple[str, ...] | None:
    for index, line in enumerate(block):
        match = re.match(rf"^\s{{2}}{re.escape(key)}\s*:\s*(.*?)\s*$", line)
        if not match:
            continue
        raw_items = _inline_items(match.group(1))
        if raw_items is None:
            raw_items = []
            for candidate in block[index + 1 :]:
                item = re.match(r"^\s{4,}-\s*(.+?)\s*$", candidate)
                if item:
                    raw_items.append(item.group(1))
                    continue
                if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= 2:
                    break
        normalised: list[str] = []
        for item in raw_items:
            value = _normalise_path(item, lane=lane)
            if value and value not in normalised:
                normalised.append(value)
        return tuple(normalised)
    return None


def _implicit_layout(docs_root: Path) -> DocsLayout:
    existing = {path.name for path in docs_root.iterdir() if path.is_dir()} if docs_root.is_dir() else set()
    legacy_present = any(lane in existing for lane in LEGACY_DOC_LANES)
    generic_present = any(lane in existing for lane in SEED_DOC_LANES)
    if legacy_present and not generic_present:
        return DocsLayout(LEGACY_DOC_LANES, LEGACY_DOC_ALLOWLIST)
    if legacy_present:
        return DocsLayout(
            SEED_DOC_LANES + tuple(lane for lane in LEGACY_DOC_LANES if lane not in SEED_DOC_LANES),
            SEED_DOC_ALLOWLIST | LEGACY_DOC_ALLOWLIST,
        )
    return DocsLayout(SEED_DOC_LANES, SEED_DOC_ALLOWLIST)


def load_docs_layout(root: str | Path) -> DocsLayout:
    project_root = Path(root).resolve()
    implicit = _implicit_layout(project_root / "docs")
    config = project_root / ".memory-seed" / "project.yaml"
    try:
        block = _docs_block(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return implicit
    if block is None:
        return implicit

    lanes = _list_from_block(block, "lanes", lane=True)
    allowlist = _list_from_block(block, "allowlist", lane=False)
    if not lanes:
        return implicit
    return DocsLayout(lanes, frozenset(allowlist if allowlist is not None else ()))


def docs_lane_role(lane: str) -> str:
    role = re.sub(r"^\d+_", "", lane).casefold()
    return "replaced" if role == "superseded" else role
