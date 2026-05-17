from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
SEED_ROOT = PACKAGE_ROOT / "seed"
VERSION = "1.2"
BACKUP_IGNORE_ENTRY = ".AGENTS/backups/"


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
            shutil.copy2(destination, backup_path)
            backed_up.append(backup_relative.as_posix())

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(seed_file.source, destination)
        created.append(seed_file.destination)

    return InitResult(
        changed=True,
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


def _read_memory_system_version(path: Path) -> str | None:
    match = re.search(
        r"^memory-system-version:\s*([^\s]+)\s*$",
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        return None
    return match.group(1)


def _ensure_backup_gitignore(target_root: Path) -> None:
    gitignore = target_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
    else:
        content = ""

    lines = content.splitlines()
    if BACKUP_IGNORE_ENTRY in lines:
        return

    prefix = content
    if prefix and not prefix.endswith(("\n", "\r\n")):
        prefix += "\n"
    gitignore.write_text(prefix + BACKUP_IGNORE_ENTRY + "\n", encoding="utf-8")
