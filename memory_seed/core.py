from __future__ import annotations

import json
import re
import hashlib
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
SEED_ROOT = PACKAGE_ROOT / "seed"
VERSION = "2.4"
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
    warnings: list[str] = field(default_factory=list)


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
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "hooks" / "memory-retrieval-check.py",
        ".memory-seed/hooks/memory-retrieval-check.py",
    ),
]

_CLAUDE_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py"
_CODEX_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --codex"
_CURSOR_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --cursor"
_GEMINI_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --gemini"

_CLAUDE_RETRIEVAL_COMMAND = "python3 .memory-seed/hooks/memory-retrieval-check.py"
_CODEX_RETRIEVAL_COMMAND = "python3 .memory-seed/hooks/memory-retrieval-check.py --codex"
_CURSOR_RETRIEVAL_COMMAND = "python3 .memory-seed/hooks/memory-retrieval-check.py --cursor"
_GEMINI_RETRIEVAL_COMMAND = "python3 .memory-seed/hooks/memory-retrieval-check.py --gemini"

_MCP_SERVER_COMMAND = "uvx"
_MCP_SERVER_ARGS = ["--from", "memory-seed", "memory-seed-mcp", "--stdio"]
_MCP_SERVER_KEY = "memory-seed"
_OWN_MCP_COMMANDS = {"uvx", "memory-seed-mcp"}

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
    """Upsert the session-log afterAgentResponse hook in .cursor/hooks.json."""
    return _merge_cursor_event_hook(
        target_root / ".cursor" / "hooks.json",
        "afterAgentResponse",
        _CURSOR_HOOK_COMMAND,
        "session-log-check.py",
    )


def _merge_gemini_hook(target_root: Path) -> bool:
    """Upsert the session-log Stop hook in .gemini/settings.json."""
    return _merge_grouped_hook(
        target_root / ".gemini" / "settings.json",
        "Stop",
        _GEMINI_HOOK_COMMAND,
        "session-log-check.py",
    )


def _merge_codex_hook(target_root: Path) -> bool:
    """Upsert the session-log Stop hook in .codex/hooks.json."""
    return _merge_grouped_hook(
        target_root / ".codex" / "hooks.json",
        "Stop",
        _CODEX_HOOK_COMMAND,
        "session-log-check.py",
    )


def _merge_claude_hook(target_root: Path) -> bool:
    """Upsert the session-log Stop hook in .claude/settings.json."""
    return _merge_grouped_hook(
        target_root / ".claude" / "settings.json",
        "Stop",
        _CLAUDE_HOOK_COMMAND,
        "session-log-check.py",
    )


def _merge_grouped_hook(config_path: Path, event: str, command: str, script_name: str) -> bool:
    """Upsert a command hook under hooks.<event> in matcher-group form.

    Used for Claude Code, Codex, and Gemini, which share the
    hooks.<event>[].hooks[].{type, command} shape.

    Identifies our entry by script_name (the stable filename). If an entry
    with that script is found with a different command, updates it in place.
    Returns True if the file was written, False if already current.
    """
    data: dict = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    for group in data.get("hooks", {}).get(event, []):
        for hook in group.get("hooks", []):
            if hook.get("command") == command:
                return False
            if script_name in (hook.get("command") or ""):
                hook["command"] = command
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")
                return True

    data.setdefault("hooks", {}).setdefault(event, []).append(
        {"hooks": [{"type": "command", "command": command}]}
    )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_cursor_event_hook(config_path: Path, event: str, command: str, script_name: str) -> bool:
    """Upsert a command hook under hooks.<event> in Cursor's flat list form.

    Identifies our entry by script_name. Updates in place if command changed.
    Returns True if the file was written, False if already current.
    """
    data: dict = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    data.setdefault("version", 1)
    for entry in data.get("hooks", {}).get(event, []):
        if entry.get("command") == command:
            return False
        if script_name in (entry.get("command") or ""):
            entry["command"] = command
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            return True

    data.setdefault("hooks", {}).setdefault(event, []).append({"command": command})

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_claude_retrieval_hook(target_root: Path) -> bool:
    return _merge_grouped_hook(
        target_root / ".claude" / "settings.json",
        "UserPromptSubmit",
        _CLAUDE_RETRIEVAL_COMMAND,
        "memory-retrieval-check.py",
    )


def _merge_codex_retrieval_hook(target_root: Path) -> bool:
    return _merge_grouped_hook(
        target_root / ".codex" / "hooks.json",
        "UserPromptSubmit",
        _CODEX_RETRIEVAL_COMMAND,
        "memory-retrieval-check.py",
    )


def _merge_gemini_retrieval_hook(target_root: Path) -> bool:
    return _merge_grouped_hook(
        target_root / ".gemini" / "settings.json",
        "UserPromptSubmit",
        _GEMINI_RETRIEVAL_COMMAND,
        "memory-retrieval-check.py",
    )


def _merge_cursor_retrieval_hook(target_root: Path) -> bool:
    return _merge_cursor_event_hook(
        target_root / ".cursor" / "hooks.json",
        "sessionStart",
        _CURSOR_RETRIEVAL_COMMAND,
        "memory-retrieval-check.py",
    )


def _merge_claude_mcp(target_root: Path) -> bool:
    """Upsert the memory-seed-mcp stdio server entry in the project-root .mcp.json.

    Claude Code discovers project-scope MCP servers from .mcp.json, not from
    .claude/settings.json (that key is silently ignored by Claude Code).
    _strip_claude_settings_mcp removes the legacy settings.json entry.
    """
    mcp_path = target_root / ".mcp.json"
    expected = {"command": _MCP_SERVER_COMMAND, "args": _MCP_SERVER_ARGS}

    data: dict = {}
    if mcp_path.exists():
        try:
            with open(mcp_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("mcpServers", {}).get(_MCP_SERVER_KEY, {})
    if existing == expected:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("mcpServers", {})[_MCP_SERVER_KEY] = expected

    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mcp_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _strip_claude_settings_mcp(target_root: Path) -> bool:
    """Remove the legacy memory-seed MCP entry from .claude/settings.json.

    Versions 2.2.0-2.3.0 wrote the server into .claude/settings.json > mcpServers,
    which Claude Code never reads. Now that the server lives in .mcp.json, drop the
    dead entry so it does not mislead. Only our own entry is removed; a foreign
    server under the same key is left untouched.
    """
    settings_path = target_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return False
    try:
        with open(settings_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or _MCP_SERVER_KEY not in servers:
        return False

    existing = servers.get(_MCP_SERVER_KEY, {})
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if not is_ours:
        return False  # foreign server under the same key; leave it alone

    del servers[_MCP_SERVER_KEY]
    if not servers:
        del data["mcpServers"]

    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_cursor_mcp(target_root: Path) -> bool:
    """Upsert the memory-seed-mcp stdio server entry in .cursor/mcp.json."""
    mcp_path = target_root / ".cursor" / "mcp.json"
    expected = {"command": _MCP_SERVER_COMMAND, "args": _MCP_SERVER_ARGS}

    data: dict = {}
    if mcp_path.exists():
        try:
            with open(mcp_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("mcpServers", {}).get(_MCP_SERVER_KEY, {})
    if existing == expected:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("mcpServers", {})[_MCP_SERVER_KEY] = expected

    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mcp_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_gemini_mcp(target_root: Path) -> bool:
    """Upsert the memory-seed-mcp stdio server entry in .gemini/settings.json."""
    settings_path = target_root / ".gemini" / "settings.json"
    expected = {"command": _MCP_SERVER_COMMAND, "args": _MCP_SERVER_ARGS}

    data: dict = {}
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("mcpServers", {}).get(_MCP_SERVER_KEY, {})
    if existing == expected:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("mcpServers", {})[_MCP_SERVER_KEY] = expected

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


# Header line for our entry in .codex/config.toml. Codex accepts both the bare
# and quoted single-segment table-key forms; we write the bare form.
_CODEX_MCP_HEADER_RE = re.compile(
    r'^\[mcp_servers\.(?:memory-seed|"memory-seed")\]\s*$'
)


def _codex_expected() -> dict:
    """The MCP table we want present under [mcp_servers.memory-seed]."""
    return {"command": _MCP_SERVER_COMMAND, "args": _MCP_SERVER_ARGS}


def _codex_standard_header_index(lines: list[str]) -> int | None:
    """Index of the standard ``[mcp_servers.memory-seed]`` header line, or None.

    The in-place stale-update path can only rewrite an entry written with this
    header form. Shared by _merge_codex_mcp (to decide whether it can migrate)
    and _codex_mcp_status (to decide stale-fixable vs stale-manual), so the two
    always agree on what counts as auto-fixable.
    """
    return next(
        (i for i, ln in enumerate(lines) if _CODEX_MCP_HEADER_RE.match(ln)),
        None,
    )


def _render_codex_mcp_block() -> str:
    """Render our fixed [mcp_servers.memory-seed] TOML table.

    args is a TOML array of strings, which is JSON-compatible, so json.dumps
    produces valid TOML for it.
    """
    return (
        f"[mcp_servers.{_MCP_SERVER_KEY}]\n"
        f'command = "{_MCP_SERVER_COMMAND}"\n'
        f"args = {json.dumps(_MCP_SERVER_ARGS)}\n"
    )


def _merge_codex_mcp(target_root: Path) -> bool:
    """Upsert the memory-seed-mcp stdio server in the project .codex/config.toml.

    Codex reads project-scoped MCP servers from .codex/config.toml under
    [mcp_servers.<name>] (trusted projects only). This is a zero-dependency text
    upsert: tomllib (stdlib, Python >=3.11) is used only to *inspect* current
    state; writes are line-based so existing content and comments are preserved.

    Returns True if the file was written, False if already current.

    Known limitation (in-place stale-entry update only): rewriting a present-but-
    outdated entry while preserving comments relies on finding the standard
    ``[mcp_servers.memory-seed]`` header line. Detection itself is robust (tomllib
    parses semantically), but if a user *hand-wrote* the entry in a form that has
    no such header line — dotted keys (``mcp_servers.memory-seed.command = ...``),
    an inline subtable under ``[mcp_servers]``, a fully inline
    ``mcp_servers = { ... }``, or a header with a trailing comment / leading
    indentation — and the entry is stale, this no-ops (returns False) rather than
    risk a duplicate-key / invalid-TOML write. The no-op is intentionally not
    silent: ``doctor`` classifies this case via _codex_mcp_status as a
    ``stale-manual`` warning telling the user to fix it by hand. Memory Seed only
    ever writes the standard header form, so this path is only reachable through
    manual edits.
    """
    config_path = target_root / ".codex" / "config.toml"
    block = _render_codex_mcp_block()

    text = ""
    parsed: dict = {}
    if config_path.exists():
        try:
            text = config_path.read_text(encoding="utf-8")
            parsed = tomllib.loads(text)
        except (tomllib.TOMLDecodeError, OSError):
            text = ""
            parsed = {}

    existing = parsed.get("mcp_servers", {}).get(_MCP_SERVER_KEY, {})
    if existing == _codex_expected():
        return False
    if existing:
        is_ours = (
            existing.get("command") in _OWN_MCP_COMMANDS
            or "memory-seed-mcp" in existing.get("args", [])
        )
        if not is_ours:
            return False  # a different server holds this key; don't overwrite

    if not existing:
        # Append our block, preserving everything above it.
        new_text = text
        if new_text and not new_text.endswith("\n"):
            new_text += "\n"
        if new_text:
            new_text += "\n"
        new_text += block
    else:
        # Stale entry: replace just our table's lines (header to next table/EOF).
        lines = text.splitlines(keepends=True)
        start = _codex_standard_header_index(lines)
        if start is None:
            # No standard header to anchor the rewrite. Don't risk a duplicate
            # key; leave it for the user. doctor() flags this as stale-manual.
            return False
        end = start + 1
        while end < len(lines) and not lines[end].lstrip().startswith("["):
            end += 1
        replacement = block if block.endswith("\n") else block + "\n"
        new_text = "".join(lines[:start]) + replacement + "".join(lines[end:])

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(new_text, encoding="utf-8")
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

    hook_merges = (
        (_merge_claude_hook, ".claude/settings.json"),
        (_merge_codex_hook, ".codex/hooks.json"),
        (_merge_cursor_hook, ".cursor/hooks.json"),
        (_merge_gemini_hook, ".gemini/settings.json"),
        (_merge_claude_retrieval_hook, ".claude/settings.json"),
        (_merge_codex_retrieval_hook, ".codex/hooks.json"),
        (_merge_cursor_retrieval_hook, ".cursor/hooks.json"),
        (_merge_gemini_retrieval_hook, ".gemini/settings.json"),
        (_merge_claude_mcp, ".mcp.json"),
        (_strip_claude_settings_mcp, ".claude/settings.json"),
        (_merge_cursor_mcp, ".cursor/mcp.json"),
        (_merge_gemini_mcp, ".gemini/settings.json"),
        (_merge_codex_mcp, ".codex/config.toml"),
    )
    for merge, destination in hook_merges:
        if merge(target_root) and destination not in created:
            created.append(destination)

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

        if destination.exists() and _version_at_least(
            _read_memory_system_version(destination), VERSION
        ):
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

    hook_merges = (
        (_merge_claude_hook, ".claude/settings.json"),
        (_merge_codex_hook, ".codex/hooks.json"),
        (_merge_cursor_hook, ".cursor/hooks.json"),
        (_merge_gemini_hook, ".gemini/settings.json"),
        (_merge_claude_retrieval_hook, ".claude/settings.json"),
        (_merge_codex_retrieval_hook, ".codex/hooks.json"),
        (_merge_cursor_retrieval_hook, ".cursor/hooks.json"),
        (_merge_gemini_retrieval_hook, ".gemini/settings.json"),
        (_merge_claude_mcp, ".mcp.json"),
        (_strip_claude_settings_mcp, ".claude/settings.json"),
        (_merge_cursor_mcp, ".cursor/mcp.json"),
        (_merge_gemini_mcp, ".gemini/settings.json"),
        (_merge_codex_mcp, ".codex/config.toml"),
    )
    for merge, destination in hook_merges:
        if merge(target_root) and destination not in created:
            created.append(destination)

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

    warnings: list[str] = []
    codex_status = _codex_mcp_status(target_root)
    if (target_root / ".codex" / "hooks.json").exists() and codex_status == "absent":
        warnings.append(
            "Codex hooks are installed but .codex/config.toml has no memory-seed MCP "
            "entry. Run `memory-seed update`, then trust this directory in Codex so it "
            "loads the project MCP server (memory_search / memory_get_chunk)."
        )
    elif codex_status == "stale-fixable":
        warnings.append(
            "Codex .codex/config.toml has an outdated memory-seed MCP entry. Run "
            "`memory-seed update` to migrate it to `uvx --from memory-seed "
            "memory-seed-mcp --stdio`."
        )
    elif codex_status == "stale-manual":
        warnings.append(
            "Codex .codex/config.toml has an outdated memory-seed MCP entry written in "
            "a non-standard TOML form that `memory-seed update` cannot safely auto-fix. "
            'Set it by hand to: command = "uvx", args = ["--from", "memory-seed", '
            '"memory-seed-mcp", "--stdio"].'
        )

    return DoctorResult(
        ok=control_plane_ok and bootstrap_complete,
        control_plane_ok=control_plane_ok,
        bootstrap_complete=bootstrap_complete,
        missing=missing,
        version_mismatches=version_mismatches,
        bootstrap_missing=bootstrap_missing,
        warnings=warnings,
    )


def _codex_mcp_status(target_root: Path) -> str:
    """Classify our memory-seed entry in .codex/config.toml.

    Returns one of:
      "absent"        - no entry (or no/unparseable file)
      "current"       - present and matches the expected uvx command + args
      "foreign"       - present but owned by a different server
      "stale-fixable" - ours but outdated, written with a standard header that
                        `memory-seed update` can auto-migrate
      "stale-manual"  - ours but outdated, written in a form with no standard
                        header line, so update no-ops and the user must edit it
    """
    config_path = target_root / ".codex" / "config.toml"
    if not config_path.exists():
        return "absent"
    try:
        text = config_path.read_text(encoding="utf-8")
        parsed = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, OSError):
        return "absent"

    existing = parsed.get("mcp_servers", {}).get(_MCP_SERVER_KEY, {})
    if not existing:
        return "absent"
    if existing == _codex_expected():
        return "current"
    is_ours = (
        existing.get("command") in _OWN_MCP_COMMANDS
        or "memory-seed-mcp" in existing.get("args", [])
    )
    if not is_ours:
        return "foreign"
    if _codex_standard_header_index(text.splitlines()) is not None:
        return "stale-fixable"
    return "stale-manual"


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


def _version_tuple(version: str | None) -> tuple[int, ...]:
    """Dotted version -> int tuple. Missing/unparseable -> (-1,) so it always
    compares older than any real version and is upgraded forward."""
    if not version:
        return (-1,)
    try:
        return tuple(int(part) for part in version.strip().split("."))
    except ValueError:
        return (-1,)


def _version_at_least(actual: str | None, minimum: str) -> bool:
    return _version_tuple(actual) >= _version_tuple(minimum)


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
