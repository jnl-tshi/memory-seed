from __future__ import annotations

import json
import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
SEED_ROOT = PACKAGE_ROOT / "seed"
VERSION = "2.0"
MEMORY_DIR_NAME = ".memory-seed"
LEGACY_MEMORY_DIR_NAME = ".AGENTS"
BACKUP_IGNORE_ENTRY = ".memory-seed/backups/"

SESSION_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class SeedFile:
    source: Path
    destination: str


@dataclass(frozen=True)
class Runtime:
    workspace_root: Path
    memory_dir: Path
    legacy: bool = False


@dataclass
class InitResult:
    changed: bool
    planned: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    backed_up: list[str] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)


@dataclass
class DoctorResult:
    ok: bool
    control_plane_ok: bool = False
    bootstrap_complete: bool = False
    missing: list[str] = field(default_factory=list)
    version_mismatches: list[dict[str, str]] = field(default_factory=list)
    bootstrap_missing: list[str] = field(default_factory=list)


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
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "agent-rules.md",
        ".memory-seed/agent-rules.md",
    ),
    SeedFile(SEED_ROOT / MEMORY_DIR_NAME / "archive" / ".gitkeep", ".memory-seed/archive/.gitkeep"),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "project-bootstrap.md",
        ".memory-seed/project-bootstrap.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "security_triage.md",
        ".memory-seed/skills/security_triage.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "code_search.md",
        ".memory-seed/skills/code_search.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "index.md",
        ".memory-seed/skills/index.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "data_architecture.md",
        ".memory-seed/skills/data_architecture.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "local_compilation.md",
        ".memory-seed/skills/local_compilation.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "memory_consolidation.md",
        ".memory-seed/skills/memory_consolidation.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "memory_doctor.md",
        ".memory-seed/skills/memory_doctor.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "release_publishing.md",
        ".memory-seed/skills/release_publishing.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "sessions" / ".gitkeep",
        ".memory-seed/sessions/.gitkeep",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "hooks" / "session-log-check.py",
        ".memory-seed/hooks/session-log-check.py",
    ),
]

_CLAUDE_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py"
_CODEX_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --codex"
_CURSOR_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --cursor"
_GEMINI_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --gemini"

BOOTSTRAP_GENERATED_FILES = [
    ".memory-seed/index.md",
    ".memory-seed/policy.md",
]


def get_version() -> str:
    return VERSION


def generate_session_entry_id(
    *,
    timestamp: str,
    title: str,
    user_initials: str,
    agent_type: str,
    project_path: str,
    subproject_path: str | None,
) -> str:
    metadata = "\n".join(
        (
            timestamp.strip(),
            title.strip(),
            user_initials.strip(),
            agent_type.strip(),
            project_path.strip(),
            "" if subproject_path is None else subproject_path.strip(),
        )
    )
    return f"ms-{hashlib.sha1(metadata.encode('utf-8')).hexdigest()[:8]}"


def resolve_runtime(cwd: str | Path = ".") -> Runtime:
    start = Path(cwd).resolve()
    if start.exists() and start.is_file():
        start = start.parent

    for candidate in (start, *start.parents):
        memory_dir = candidate / MEMORY_DIR_NAME
        if memory_dir.is_dir():
            return Runtime(
                workspace_root=candidate,
                memory_dir=memory_dir.resolve(),
                legacy=False,
            )

    for candidate in (start, *start.parents):
        memory_dir = candidate / LEGACY_MEMORY_DIR_NAME
        if memory_dir.is_dir():
            return Runtime(
                workspace_root=candidate,
                memory_dir=memory_dir.resolve(),
                legacy=True,
            )

    return Runtime(
        workspace_root=start,
        memory_dir=start / MEMORY_DIR_NAME,
        legacy=False,
    )


def _merge_cursor_hook(target_root: Path) -> bool:
    """Add the session-log afterAgentResponse hook to .cursor/hooks.json."""
    hooks_path = target_root / ".cursor" / "hooks.json"

    data: dict = {}
    if hooks_path.exists():
        try:
            with open(hooks_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    data.setdefault("version", 1)
    for entry in data.get("hooks", {}).get("afterAgentResponse", []):
        if entry.get("command") == _CURSOR_HOOK_COMMAND:
            return False

    data.setdefault("hooks", {}).setdefault("afterAgentResponse", []).append(
        {"command": _CURSOR_HOOK_COMMAND}
    )

    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    with open(hooks_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_gemini_hook(target_root: Path) -> bool:
    """Add the session-log Stop hook to .gemini/settings.json."""
    settings_path = target_root / ".gemini" / "settings.json"

    data: dict = {}
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    for group in data.get("hooks", {}).get("Stop", []):
        for hook in group.get("hooks", []):
            if hook.get("command") == _GEMINI_HOOK_COMMAND:
                return False

    data.setdefault("hooks", {}).setdefault("Stop", []).append(
        {"hooks": [{"type": "command", "command": _GEMINI_HOOK_COMMAND}]}
    )

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_codex_hook(target_root: Path) -> bool:
    """Add the session-log Stop hook to .codex/hooks.json, merging with existing content.

    Returns True if the file was created or modified, False if the hook was already present.
    """
    hooks_path = target_root / ".codex" / "hooks.json"

    data: dict = {}
    if hooks_path.exists():
        try:
            with open(hooks_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    for group in data.get("hooks", {}).get("Stop", []):
        for hook in group.get("hooks", []):
            if hook.get("command") == _CODEX_HOOK_COMMAND:
                return False

    data.setdefault("hooks", {}).setdefault("Stop", []).append(
        {"hooks": [{"type": "command", "command": _CODEX_HOOK_COMMAND}]}
    )

    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    with open(hooks_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_claude_hook(target_root: Path) -> bool:
    """Add the session-log Stop hook to .claude/settings.json, merging with existing content.

    Returns True if the file was created or modified, False if the hook was already present.
    """
    settings_path = target_root / ".claude" / "settings.json"

    data: dict = {}
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    for group in data.get("hooks", {}).get("Stop", []):
        for hook in group.get("hooks", []):
            if hook.get("command") == _CLAUDE_HOOK_COMMAND:
                return False

    data.setdefault("hooks", {}).setdefault("Stop", []).append(
        {"hooks": [{"type": "command", "command": _CLAUDE_HOOK_COMMAND}]}
    )

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


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
            backup_relative = Path(MEMORY_DIR_NAME) / "backups" / timestamp / seed_file.destination
            backup_path = target_root / backup_relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            _copy_text_file(destination, backup_path)
            backed_up.append(backup_relative.as_posix())

        destination.parent.mkdir(parents=True, exist_ok=True)
        _copy_text_file(seed_file.source, destination)
        created.append(seed_file.destination)

    if _merge_claude_hook(target_root):
        created.append(".claude/settings.json")
    if _merge_codex_hook(target_root):
        created.append(".codex/hooks.json")
    if _merge_cursor_hook(target_root):
        created.append(".cursor/hooks.json")
    if _merge_gemini_hook(target_root):
        created.append(".gemini/settings.json")

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
    archived: list[str] = []

    for seed_file in SEED_FILES:
        destination = target_root / seed_file.destination
        if _is_runtime_local_file(seed_file.destination) and destination.exists():
            continue

        if destination.exists() and _read_memory_system_version(destination) == VERSION:
            continue

        if destination.exists():
            _ensure_backup_gitignore(target_root)
            backup_relative = Path(MEMORY_DIR_NAME) / "backups" / timestamp / seed_file.destination
            backup_path = target_root / backup_relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            _copy_text_file(destination, backup_path)
            backed_up.append(backup_relative.as_posix())
            archive_relative = _archive_replaced_control_plane_file(
                target_root,
                destination,
                seed_file.destination,
                timestamp,
            )
            if archive_relative:
                archived.append(archive_relative)

        destination.parent.mkdir(parents=True, exist_ok=True)
        _copy_text_file(seed_file.source, destination)
        created.append(seed_file.destination)

    if _merge_claude_hook(target_root):
        created.append(".claude/settings.json")
    if _merge_codex_hook(target_root):
        created.append(".codex/hooks.json")
    if _merge_cursor_hook(target_root):
        created.append(".cursor/hooks.json")
    if _merge_gemini_hook(target_root):
        created.append(".gemini/settings.json")

    return InitResult(
        changed=bool(created or backed_up or archived),
        planned=planned,
        created=created,
        backed_up=backed_up,
        archived=archived,
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

        if not candidate.suffix == ".md":
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

    bootstrap_missing = [
        path
        for path in BOOTSTRAP_GENERATED_FILES
        if not (target_root / path).exists()
    ]

    control_plane_ok = not missing and not version_mismatches
    bootstrap_complete = not bootstrap_missing

    return DoctorResult(
        ok=control_plane_ok and bootstrap_complete,
        control_plane_ok=control_plane_ok,
        bootstrap_complete=bootstrap_complete,
        missing=missing,
        version_mismatches=version_mismatches,
        bootstrap_missing=bootstrap_missing,
    )


def compact_sessions(
    cwd: str | Path = ".",
    days: int = 7,
    scan_all: bool = False,
) -> CompactResult:
    target_root = Path(cwd).resolve()
    sessions_dir = resolve_runtime(target_root).memory_dir / "sessions"

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


def _is_runtime_local_file(destination: str) -> bool:
    reusable_runtime_files = {
        f"{MEMORY_DIR_NAME}/agent-rules.md",
        f"{MEMORY_DIR_NAME}/project-bootstrap.md",
    }
    return (
        destination.startswith(f"{MEMORY_DIR_NAME}/")
        and destination not in reusable_runtime_files
    )


def _archive_replaced_control_plane_file(
    target_root: Path,
    source: Path,
    destination: str,
    timestamp: str,
) -> str | None:
    if _is_runtime_local_file(destination):
        return None

    old_version = _read_memory_system_version(source)
    archive_folder = old_version or f"unknown-{timestamp}"
    archive_relative = Path(MEMORY_DIR_NAME) / "archive" / archive_folder / destination
    archive_path = target_root / archive_relative
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    _copy_text_file(source, archive_path)
    return archive_relative.as_posix()


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
