from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
SEED_ROOT = PACKAGE_ROOT / "seed"
VERSION = "1.4"
BACKUP_IGNORE_ENTRY = ".AGENTS/backups/"

SESSION_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class SeedFile:
    source: Path
    destination: str


@dataclass
class InitResult:
    changed: bool
    planned: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    backed_up: list[str] = field(default_factory=list)


@dataclass
class DoctorResult:
    ok: bool
    missing: list[str] = field(default_factory=list)
    version_mismatches: list[dict[str, str]] = field(default_factory=list)


@dataclass
class CompactResult:
    sessions_scanned: list[str]
    headings: dict[str, list[str]]
    full_text: str
    date_range: tuple[str, str] | None


SEED_FILES = [
    SeedFile(SEED_ROOT / "AGENTS.md", "AGENTS.md"),
    SeedFile(SEED_ROOT / "CLAUDE.md", "CLAUDE.md"),
    SeedFile(SEED_ROOT / "GEMINI.md", "GEMINI.md"),
    SeedFile(SEED_ROOT / ".AGENTS" / "agent-rules.md", ".AGENTS/agent-rules.md"),
    SeedFile(
        SEED_ROOT / ".AGENTS" / "project-bootstrap.md",
        ".AGENTS/project-bootstrap.md",
    ),
]


def get_version() -> str:
    return VERSION


def init_project(cwd: str | Path = ".", dry_run: bool = False, force: bool = False) -> InitResult:
    target_root = Path(cwd).resolve()
    planned = [seed_file.destination for seed_file in SEED_FILES]
    existing = [
        seed_file.destination
        for seed_file in SEED_FILES
        if (target_root / seed_file.destination).exists()
    ]

    if dry_run:
        return InitResult(changed=False, planned=planned)

    if existing and not force:
        raise FileExistsError(
            "Refusing to overwrite existing files: " + ", ".join(existing)
        )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    created: list[str] = []
    backed_up: list[str] = []

    for seed_file in SEED_FILES:
        destination = target_root / seed_file.destination

        if destination.exists() and force:
            _ensure_backup_gitignore(target_root)
            backup_relative = Path(".AGENTS") / "backups" / timestamp / seed_file.destination
            backup_path = target_root / backup_relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            _copy_text_file(destination, backup_path)
            backed_up.append(backup_relative.as_posix())

        destination.parent.mkdir(parents=True, exist_ok=True)
        _copy_text_file(seed_file.source, destination)
        created.append(seed_file.destination)

    return InitResult(
        changed=True,
        planned=planned,
        created=created,
        backed_up=backed_up,
    )


def update_project(cwd: str | Path = ".", dry_run: bool = False) -> InitResult:
    target_root = Path(cwd).resolve()
    planned = [seed_file.destination for seed_file in SEED_FILES]

    if dry_run:
        return InitResult(changed=False, planned=planned)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    created: list[str] = []
    backed_up: list[str] = []

    for seed_file in SEED_FILES:
        destination = target_root / seed_file.destination
        if destination.exists() and _read_memory_system_version(destination) == VERSION:
            continue

        if destination.exists():
            _ensure_backup_gitignore(target_root)
            backup_relative = Path(".AGENTS") / "backups" / timestamp / seed_file.destination
            backup_path = target_root / backup_relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            _copy_text_file(destination, backup_path)
            backed_up.append(backup_relative.as_posix())

        destination.parent.mkdir(parents=True, exist_ok=True)
        _copy_text_file(seed_file.source, destination)
        created.append(seed_file.destination)

    return InitResult(
        changed=bool(created or backed_up),
        planned=planned,
        created=created,
        backed_up=backed_up,
    )


def doctor(cwd: str | Path = ".") -> DoctorResult:
    target_root = Path(cwd).resolve()
    missing: list[str] = []
    version_mismatches: list[dict[str, str]] = []

    for seed_file in SEED_FILES:
        candidate = target_root / seed_file.destination
        if not candidate.exists():
            missing.append(seed_file.destination)
            continue

        actual = _read_memory_system_version(candidate)
        if actual != VERSION:
            version_mismatches.append(
                {
                    "file": seed_file.destination,
                    "expected": VERSION,
                    "actual": actual or "missing",
                }
            )

    return DoctorResult(
        ok=not missing and not version_mismatches,
        missing=missing,
        version_mismatches=version_mismatches,
    )


def compact_sessions(
    cwd: str | Path = ".",
    days: int = 7,
    scan_all: bool = False,
) -> CompactResult:
    target_root = Path(cwd).resolve()
    sessions_dir = target_root / ".AGENTS" / "sessions"

    if not sessions_dir.is_dir():
        return CompactResult(
            sessions_scanned=[],
            headings={},
            full_text="",
            date_range=None,
        )

    today = datetime.now().date()
    cutoff = None if scan_all else today - timedelta(days=days)

    dated_files: list[tuple[str, Path]] = []
    for path in sorted(sessions_dir.iterdir()):
        m = SESSION_DATE_RE.match(path.name)
        if not m:
            continue
        date_str = m.group(1)
        if cutoff is not None:
            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if file_date < cutoff:
                continue
        dated_files.append((date_str, path))

    if not dated_files:
        return CompactResult(
            sessions_scanned=[],
            headings={},
            full_text="",
            date_range=None,
        )

    headings: dict[str, list[str]] = {}
    full_parts: list[str] = []

    for date_str, path in dated_files:
        content = path.read_text(encoding="utf-8")
        headings[date_str] = HEADING_RE.findall(content)
        full_parts.append(content)

    return CompactResult(
        sessions_scanned=[f.name for _, f in dated_files],
        headings=headings,
        full_text="\n".join(full_parts),
        date_range=(dated_files[0][0], dated_files[-1][0]),
    )


def _read_memory_system_version(path: Path) -> str | None:
    match = re.search(
        r"^memory-system-version:\s*([^\s]+)\s*$",
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        return None
    return match.group(1)


def _copy_text_file(source: Path, destination: Path) -> None:
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _ensure_backup_gitignore(target_root: Path) -> None:
    _ensure_gitignore_entry(target_root, BACKUP_IGNORE_ENTRY)


def _ensure_gitignore_entry(target_root: Path, entry: str) -> None:
    gitignore = target_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
    else:
        content = ""

    lines = content.splitlines()
    if entry in lines:
        return

    prefix = content
    if prefix and not prefix.endswith(("\n", "\r\n")):
        prefix += "\n"
    gitignore.write_text(prefix + entry + "\n", encoding="utf-8")
