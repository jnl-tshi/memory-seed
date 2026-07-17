"""`memory-seed docs index` - generated lane tables for `docs/`.

The read surface of the document-lifecycle system: each lane's `README.md`
gains an auto-maintained table of that lane's documents rendered from their
YAML frontmatter, and the front door gains a counts roll-up - so a human reads
one file per lane instead of scanning frontmatter, and the counts can never
silently drift from the tree again.

**The generator only ever writes between its markers.** Lane READMEs carry
hand-written prose (a lane's purpose, reclassification notes, allowlists) that
a regeneration must never destroy, so the contract is explicit:

    <!-- docs-index:begin -->   ...generated table...   <!-- docs-index:end -->

Markers present -> only the region between them is replaced. Markers absent ->
the block is appended at the end of the file (non-destructive). No README ->
one is created holding just a heading and the block. Everything outside the
markers is untouchable, byte for byte.

The output is deterministic for the same tree, which makes `--check` a real
gate: regenerate in memory, compare, and report stale without writing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BEGIN = "<!-- docs-index:begin -->"
END = "<!-- docs-index:end -->"

# Flow lanes get a table; type lanes too. Order fixes the front-door roll-up.
LANES = (
    "1_Inbox",
    "2_Todo",
    "3_Spec",
    "4_Reference",
    "5_Completed",
    "6_Rejected",
    "7_Superseded",
    "8_Deferred",
)

_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


@dataclass
class DocsIndexResult:
    written: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.written or self.stale)


def _frontmatter(path: Path) -> dict[str, str]:
    from .core import _parse_frontmatter_scalars
    from .docs_check import _FRONTMATTER

    try:
        match = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}
    return _parse_frontmatter_scalars(match.group(1)) if match else {}


def _lane_docs(lane_dir: Path) -> list[Path]:
    # Sort by an explicit name key, NOT by the Path objects themselves: Path
    # ordering is case-insensitive on Windows and case-sensitive on Linux, so a
    # lane with mixed-case filenames would generate a different table order per
    # platform and break `--check` across a Windows author / Linux CI split.
    # (casefold(), name) is a stable, platform-independent total order.
    return sorted(
        (p for p in lane_dir.glob("*.md") if p.name != "README.md"),
        key=lambda p: (p.name.casefold(), p.name),
    )


def _cell(value: str | None, limit: int = 96) -> str:
    if not value:
        return "—"
    text = " ".join(value.split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|")


def _lane_table(lane: str, docs: list[Path]) -> str:
    if not docs:
        return f"{BEGIN}\n_(no documents in this lane)_\n{END}"

    rows: list[tuple[str, str, str, str]] = []
    for doc in docs:
        front = _frontmatter(doc)
        rows.append(
            (
                doc.name,
                front.get("priority", ""),
                front.get("blocked_by", ""),
                front.get("next_action") or front.get("superseded_by") or front.get("status", ""),
            )
        )
    if lane == "2_Todo":
        rows.sort(key=lambda r: (_PRIORITY_ORDER.get(r[1], 9), r[0].lower()))

    lines = [
        BEGIN,
        f"| Document | Priority | Blocked by | Next action / pointer |",
        "|---|---|---|---|",
    ]
    for name, priority, blocked, pointer in rows:
        lines.append(
            f"| [{_cell(name)}]({name.replace(' ', '%20')}) | {_cell(priority, 8)} "
            f"| {_cell(blocked, 60)} | {_cell(pointer)} |"
        )
    lines.append(END)
    return "\n".join(lines)


def _front_door_block(docs_root: Path) -> str:
    counts: list[str] = []
    total_open: list[tuple[str, str, str]] = []
    for lane in LANES:
        lane_dir = docs_root / lane
        if not lane_dir.is_dir():
            continue
        docs = _lane_docs(lane_dir)
        counts.append(f"{lane} {len(docs)}")
        if lane == "2_Todo":
            for doc in docs:
                front = _frontmatter(doc)
                if front.get("priority") in ("P0", "P1"):
                    total_open.append(
                        (front["priority"], doc.name, front.get("next_action", ""))
                    )
    lines = [
        BEGIN,
        "Counts (Markdown files directly in each lane, lane `README.md` excluded): "
        + " · ".join(counts),
    ]
    if total_open:
        total_open.sort()
        lines.append("")
        lines.append("Top open items (P0/P1 in `2_Todo/`):")
        for priority, name, action in total_open:
            lines.append(f"- **{priority}** [{name}](2_Todo/{name.replace(' ', '%20')}) — {_cell(action, 140)}")
    lines.append(END)
    return "\n".join(lines)


def _splice(existing: str, block: str) -> str:
    """Replace the marker region, or append the block; never touch anything
    outside the markers."""
    if BEGIN in existing and END in existing:
        head, rest = existing.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        return head + block + tail
    suffix = "" if existing.endswith("\n") else "\n"
    return existing + suffix + "\n" + block + "\n"


def apply_docs_index(cwd: str | Path = ".", *, check: bool = False) -> DocsIndexResult:
    """Regenerate every lane table and the front-door roll-up.

    ``check=True`` writes nothing: files whose regenerated content differs are
    reported ``stale`` (the CI/esr gate the lifecycle plan's "stale generated
    index" rule asks for).
    """
    from .text_files import read_text_file, write_text_file

    root = Path(cwd).resolve()
    docs_root = root / "docs"
    result = DocsIndexResult()
    if not docs_root.is_dir():
        return result

    targets: list[tuple[Path, str]] = []
    for lane in LANES:
        lane_dir = docs_root / lane
        if not lane_dir.is_dir():
            continue
        targets.append((lane_dir / "README.md", _lane_table(lane, _lane_docs(lane_dir))))
    targets.append((docs_root / "README.md", _front_door_block(docs_root)))

    for readme, block in targets:
        existing = read_text_file(readme) if readme.exists() else f"# {readme.parent.name}\n"
        updated = _splice(existing, block)
        if updated == existing:
            continue
        rel = readme.relative_to(root).as_posix()
        if check:
            result.stale.append(rel)
        else:
            write_text_file(readme, updated)
            result.written.append(rel)
    return result


def format_docs_index(result: DocsIndexResult, *, check: bool) -> str:
    if check:
        if not result.stale:
            return "Docs index is current."
        return "Stale generated index (run `memory-seed docs index`):\n" + "\n".join(
            f"  - {path}" for path in result.stale
        )
    if not result.written:
        return "Docs index already current; nothing written."
    return "Regenerated:\n" + "\n".join(f"  - {path}" for path in result.written)
