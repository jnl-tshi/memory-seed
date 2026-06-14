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
VERSION = "2.8"
MEMORY_DIR_NAME = ".memory-seed"
LEGACY_MEMORY_DIR_NAME = ".AGENTS"
BACKUP_IGNORE_ENTRY = ".memory-seed/backups/"

# Entry-point "routing" files share their names with files other tools own
# (HyperFrames also uses AGENTS.md/CLAUDE.md). When one of these already exists
# and is NOT ours (no memory-system-version frontmatter), we inject a marker-
# delimited managed block that routes into .memory-seed/ instead of overwriting
# the host's content, then re-sync that block in place on later updates. Mirrors
# the JSON config merge philosophy (_merge_grouped_hook / _COPILOT_STARTUP_MARKER).
ROUTING_DESTINATIONS = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
}
_ROUTING_BLOCK_RE = re.compile(
    r"<!-- BEGIN memory-seed.*?<!-- END memory-seed -->", re.DOTALL
)
# The block carries no version stamp: a foreign file is host-owned and not
# version-tracked (doctor likewise skips it from version-mismatch), so the
# block is re-synced only when its *body* changes, never on a bare version bump.
_ROUTING_STANZA = (
    "<!-- BEGIN memory-seed (managed block — edits inside are overwritten on update) -->\n"
    "## Memory (Memory Seed runtime)\n"
    "\n"
    "This project has a Memory Seed runtime in `.memory-seed/`. Before substantive work, read in order:\n"
    "\n"
    "1. `.memory-seed/agent-rules.md` — operating contract (retrieval, session-log discipline, End Of Turn)\n"
    "2. `.memory-seed/index.md` — orientation, active state, inheritance\n"
    "3. `.memory-seed/policy.md` — constraints\n"
    "4. `.memory-seed/skills/index.md` — skill trigger registry\n"
    "\n"
    "Append a session entry to `.memory-seed/sessions/YYYY-MM-DD.md` after meaningful work.\n"
    "Instructions above this block remain authoritative for their own domain.\n"
    "<!-- END memory-seed -->"
)

SESSION_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class SeedFile:
    source: Path
    destination: str
    # Agent this file belongs to (e.g. "claude"). None = agent-agnostic, always
    # installed. Agent-tagged files are installed only when that agent is selected.
    agent: str | None = None


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
    SeedFile(SEED_ROOT / "CLAUDE.md", "CLAUDE.md", agent="claude"),
    SeedFile(SEED_ROOT / "GEMINI.md", "GEMINI.md", agent="gemini"),
    SeedFile(SEED_ROOT / ".github" / "copilot-instructions.md", ".github/copilot-instructions.md", agent="copilot"),
    SeedFile(SEED_ROOT / ".agents" / "README.md", ".agents/README.md"),
    SeedFile(SEED_ROOT / ".agents" / "developer.md", ".agents/developer.md"),
    SeedFile(SEED_ROOT / ".agents" / "content-creator.md", ".agents/content-creator.md"),
    SeedFile(SEED_ROOT / ".agents" / "researcher.md", ".agents/researcher.md"),
    SeedFile(SEED_ROOT / ".agents" / "sales-rep.md", ".agents/sales-rep.md"),
    SeedFile(SEED_ROOT / ".agents" / "solo-founder.md", ".agents/solo-founder.md"),
    SeedFile(SEED_ROOT / ".agents" / "copywriter.md", ".agents/copywriter.md"),
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
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "copywriter-conversion.md",
        ".memory-seed/skills/copywriter-conversion.md",
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
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "document_ingestion.md",
        ".memory-seed/skills/document_ingestion.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "office_document_editing.md",
        ".memory-seed/skills/office_document_editing.md",
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
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "hooks" / "session-start-context.py",
        ".memory-seed/hooks/session-start-context.py",
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

# SessionStart orientation hook: injects the newest session entries directly so
# agents do not lean on semantic search (which can bury the newest entry) to
# establish current state. Fires once per session, unlike the per-prompt reminder.
_CLAUDE_STARTUP_COMMAND = "python3 .memory-seed/hooks/session-start-context.py"
_CODEX_STARTUP_COMMAND = "python3 .memory-seed/hooks/session-start-context.py --codex"
_CURSOR_STARTUP_COMMAND = "python3 .memory-seed/hooks/session-start-context.py --cursor"
_GEMINI_STARTUP_COMMAND = "python3 .memory-seed/hooks/session-start-context.py --gemini"

_MCP_SERVER_COMMAND = "uvx"
_MCP_SERVER_ARGS = ["--from", "memory-seed", "memory-seed-mcp", "--stdio"]
_MCP_SERVER_KEY = "memory-seed"
_OWN_MCP_COMMANDS = {"uvx", "memory-seed-mcp"}

# GitHub Copilot CLI integration. Its MCP config is repo-local at .github/mcp.json
# with a distinct schema (type + tools). Its sessionStart hook cannot inject context
# from a command hook (stdout is consumed, not processed) — only a "prompt" hook can,
# so Copilot gets a static directive (it must glob the sessions dir itself) rather
# than running session-start-context.py.
# type "stdio" (over the also-valid "local") is the GitHub-documented preferred
# value for compatibility with VS Code and other MCP clients.
_COPILOT_MCP_EXPECTED = {
    "type": "stdio",
    "command": _MCP_SERVER_COMMAND,
    "args": _MCP_SERVER_ARGS,
    "tools": ["*"],
}
# VS Code (Copilot Chat / agent mode) reads MCP servers from .vscode/mcp.json under
# the "servers" key (NOT "mcpServers" like the CLI / Cursor configs).
_VSCODE_MCP_EXPECTED = {
    "type": "stdio",
    "command": _MCP_SERVER_COMMAND,
    "args": _MCP_SERVER_ARGS,
}
_COPILOT_STARTUP_MARKER = "memory-seed:"
_COPILOT_STARTUP_PROMPT = (
    "memory-seed: To establish current project state, read the most recent dated "
    "file in .memory-seed/sessions/ (newest YYYY-MM-DD.md) in full, then skim the "
    "prior one. Do NOT use memory_search/semantic search to find the most recent "
    "work - its ranking can bury the newest entry beneath older topically-similar "
    "ones. Use memory_search only for topical 'why was X decided / what do we know "
    "about Y' questions."
)

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
    """Upsert the session-log AfterAgent hook in .gemini/settings.json.

    Gemini's turn-end event is `AfterAgent` (it has no `Stop` event). Earlier
    versions wrote `Stop`, which never fired; _strip_gemini_dead_hooks removes it.
    """
    return _merge_grouped_hook(
        target_root / ".gemini" / "settings.json",
        "AfterAgent",
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
    # Gemini's prompt-submit event is `BeforeAgent` (fires after the user submits,
    # before planning). It has no `UserPromptSubmit` event; the old wiring was dead.
    return _merge_grouped_hook(
        target_root / ".gemini" / "settings.json",
        "BeforeAgent",
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


def _merge_claude_startup_hook(target_root: Path) -> bool:
    return _merge_grouped_hook(
        target_root / ".claude" / "settings.json",
        "SessionStart",
        _CLAUDE_STARTUP_COMMAND,
        "session-start-context.py",
    )


def _merge_codex_startup_hook(target_root: Path) -> bool:
    return _merge_grouped_hook(
        target_root / ".codex" / "hooks.json",
        "SessionStart",
        _CODEX_STARTUP_COMMAND,
        "session-start-context.py",
    )


def _merge_gemini_startup_hook(target_root: Path) -> bool:
    return _merge_grouped_hook(
        target_root / ".gemini" / "settings.json",
        "SessionStart",
        _GEMINI_STARTUP_COMMAND,
        "session-start-context.py",
    )


def _merge_cursor_startup_hook(target_root: Path) -> bool:
    return _merge_cursor_event_hook(
        target_root / ".cursor" / "hooks.json",
        "sessionStart",
        _CURSOR_STARTUP_COMMAND,
        "session-start-context.py",
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


def _strip_gemini_dead_hooks(target_root: Path) -> bool:
    """Remove our stale Stop / UserPromptSubmit hook entries from .gemini/settings.json.

    Gemini exposes no `Stop` or `UserPromptSubmit` event, so entries earlier versions
    wrote there never fired. The merge functions now write the correct events
    (`AfterAgent` / `BeforeAgent` / `SessionStart`); this strips the dead ones so
    `update` migrates existing projects. Only our own entries (identified by script
    filename) are removed; foreign hooks under those events are left untouched.
    """
    settings_path = target_root / ".gemini" / "settings.json"
    if not settings_path.exists():
        return False
    try:
        with open(settings_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False

    our_scripts = ("session-log-check.py", "memory-retrieval-check.py")

    def _group_is_ours(group: dict) -> bool:
        inner = group.get("hooks", []) if isinstance(group, dict) else []
        return any(
            any(s in (h.get("command") or "") for s in our_scripts) for h in inner
        )

    changed = False
    for event in ("Stop", "UserPromptSubmit"):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept = [g for g in groups if not _group_is_ours(g)]
        if len(kept) == len(groups):
            continue  # nothing of ours under this event
        changed = True
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]

    if not changed:
        return False

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


def _merge_copilot_mcp(target_root: Path) -> bool:
    """Upsert the memory-seed-mcp stdio server entry in repo-local .github/mcp.json.

    GitHub Copilot CLI auto-loads MCP servers from a workspace .github/mcp.json.
    Its schema differs from the other clients (type + tools fields), so it has its
    own expected dict. Only our own entry is touched; a foreign server under the
    same key is left alone.
    """
    mcp_path = target_root / ".github" / "mcp.json"

    data: dict = {}
    if mcp_path.exists():
        try:
            with open(mcp_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("mcpServers", {}).get(_MCP_SERVER_KEY, {})
    if existing == _COPILOT_MCP_EXPECTED:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("mcpServers", {})[_MCP_SERVER_KEY] = dict(_COPILOT_MCP_EXPECTED)

    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mcp_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_vscode_mcp(target_root: Path) -> bool:
    """Upsert the memory-seed-mcp stdio server entry in .vscode/mcp.json.

    VS Code (Copilot agent mode) uses the `servers` key, unlike the `mcpServers`
    key in .mcp.json / .cursor/mcp.json / .github/mcp.json. Only our own entry is
    touched; a foreign server under the same key is left alone.
    """
    mcp_path = target_root / ".vscode" / "mcp.json"

    data: dict = {}
    if mcp_path.exists():
        try:
            with open(mcp_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("servers", {}).get(_MCP_SERVER_KEY, {})
    if existing == _VSCODE_MCP_EXPECTED:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("servers", {})[_MCP_SERVER_KEY] = dict(_VSCODE_MCP_EXPECTED)

    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mcp_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return True


def _merge_copilot_startup_hook(target_root: Path) -> bool:
    """Upsert a sessionStart prompt hook in .github/hooks/memory-seed.json.

    Copilot command hooks cannot inject context at sessionStart (stdout is consumed,
    not processed); only a "prompt" hook injects text. So Copilot gets a static
    directive instead of running session-start-context.py. Our entry is identified
    by the _COPILOT_STARTUP_MARKER prefix and updated in place if the text changes.
    """
    config_path = target_root / ".github" / "hooks" / "memory-seed.json"

    data: dict = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    data.setdefault("version", 1)
    entries = data.setdefault("hooks", {}).setdefault("sessionStart", [])
    for entry in entries:
        if entry.get("type") == "prompt" and entry.get("prompt", "").startswith(
            _COPILOT_STARTUP_MARKER
        ):
            if entry.get("prompt") == _COPILOT_STARTUP_PROMPT:
                return False
            entry["prompt"] = _COPILOT_STARTUP_PROMPT
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            return True

    entries.append({"type": "prompt", "prompt": _COPILOT_STARTUP_PROMPT})

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
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


# ---- Agent registry & selection ------------------------------------------

KNOWN_AGENTS = ("claude", "codex", "cursor", "gemini", "copilot")

# Per-agent hook/MCP merge operations: (merge_fn, destination-for-reporting).
# init/update run only the operations for selected agents. Order within an agent
# is independent — each merge is idempotent and targets distinct keys/files.
_AGENT_MERGES: dict[str, tuple[tuple, ...]] = {
    "claude": (
        (_merge_claude_hook, ".claude/settings.json"),
        (_merge_claude_retrieval_hook, ".claude/settings.json"),
        (_merge_claude_startup_hook, ".claude/settings.json"),
        (_merge_claude_mcp, ".mcp.json"),
        (_strip_claude_settings_mcp, ".claude/settings.json"),
    ),
    "codex": (
        (_merge_codex_hook, ".codex/hooks.json"),
        (_merge_codex_retrieval_hook, ".codex/hooks.json"),
        (_merge_codex_startup_hook, ".codex/hooks.json"),
        (_merge_codex_mcp, ".codex/config.toml"),
    ),
    "cursor": (
        (_merge_cursor_hook, ".cursor/hooks.json"),
        (_merge_cursor_retrieval_hook, ".cursor/hooks.json"),
        (_merge_cursor_startup_hook, ".cursor/hooks.json"),
        (_merge_cursor_mcp, ".cursor/mcp.json"),
    ),
    "gemini": (
        (_merge_gemini_hook, ".gemini/settings.json"),
        (_merge_gemini_retrieval_hook, ".gemini/settings.json"),
        (_merge_gemini_startup_hook, ".gemini/settings.json"),
        (_merge_gemini_mcp, ".gemini/settings.json"),
        (_strip_gemini_dead_hooks, ".gemini/settings.json"),
    ),
    "copilot": (
        (_merge_copilot_mcp, ".github/mcp.json"),
        (_merge_copilot_startup_hook, ".github/hooks/memory-seed.json"),
        (_merge_vscode_mcp, ".vscode/mcp.json"),
    ),
}


def _agent_merges(selected: set[str]) -> list[tuple]:
    """Flatten merge ops for the selected agents, in deterministic KNOWN_AGENTS order."""
    ops: list[tuple] = []
    for agent in KNOWN_AGENTS:
        if agent in selected:
            ops.extend(_AGENT_MERGES[agent])
    return ops


# ---- Uninstall (for `agents remove`) -------------------------------------
# Strip-in-place is the default: remove only OUR entries (our hook scripts / MCP
# key) from a config file and leave any foreign content. Delete a config file only
# when nothing of value remains. Never delete a shared directory (.github, .vscode).

_OUR_HOOK_SCRIPTS = (
    "session-log-check.py",
    "memory-retrieval-check.py",
    "session-start-context.py",
)


def _command_is_ours(command: str | None) -> bool:
    c = command or ""
    return any(s in c for s in _OUR_HOOK_SCRIPTS)


def _load_json(path: Path) -> dict | None:
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _write_json_or_delete(path: Path, data: dict) -> None:
    """Write JSON, or delete the file if `data` is empty (it was wholly ours)."""
    if not data:
        try:
            path.unlink()
        except OSError:
            pass
        return
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _strip_grouped_hooks(config_path: Path) -> bool:
    """Remove our hook groups from a grouped-format config (Claude/Codex/Gemini)."""
    if not config_path.exists():
        return False
    data = _load_json(config_path)
    if data is None:
        return False
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event in list(hooks.keys()):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept = []
        for g in groups:
            inner = g.get("hooks", []) if isinstance(g, dict) else []
            if any(_command_is_ours(h.get("command")) for h in inner):
                changed = True
            else:
                kept.append(g)
        if len(kept) != len(groups):
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
    if not changed:
        return False
    if not hooks:
        del data["hooks"]
    _write_json_or_delete(config_path, data)
    return True


def _strip_cursor_hooks(config_path: Path) -> bool:
    """Remove our hook entries from Cursor's flat-list config."""
    if not config_path.exists():
        return False
    data = _load_json(config_path)
    if data is None:
        return False
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event in list(hooks.keys()):
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        kept = [
            e for e in entries
            if not (isinstance(e, dict) and _command_is_ours(e.get("command")))
        ]
        if len(kept) != len(entries):
            changed = True
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
    if not changed:
        return False
    if not hooks:
        data.pop("hooks", None)
    if set(data.keys()) <= {"version"}:
        data = {}
    _write_json_or_delete(config_path, data)
    return True


def _strip_mcp_entry(path: Path, container_key: str) -> bool:
    """Remove our memory-seed server from an MCP config's container (mcpServers/servers)."""
    if not path.exists():
        return False
    data = _load_json(path)
    if data is None:
        return False
    container = data.get(container_key)
    if not isinstance(container, dict) or _MCP_SERVER_KEY not in container:
        return False
    existing = container.get(_MCP_SERVER_KEY, {})
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if not is_ours:
        return False
    del container[_MCP_SERVER_KEY]
    if not container:
        del data[container_key]
    if set(data.keys()) <= {"version"}:
        data = {}
    _write_json_or_delete(path, data)
    return True


def _strip_copilot_startup(target_root: Path) -> bool:
    """Remove our sessionStart prompt hook from .github/hooks/memory-seed.json."""
    path = target_root / ".github" / "hooks" / "memory-seed.json"
    if not path.exists():
        return False
    data = _load_json(path)
    if data is None:
        return False
    hooks = data.get("hooks", {})
    entries = hooks.get("sessionStart")
    if not isinstance(entries, list):
        return False
    kept = [
        e for e in entries
        if not (
            isinstance(e, dict)
            and e.get("type") == "prompt"
            and (e.get("prompt") or "").startswith(_COPILOT_STARTUP_MARKER)
        )
    ]
    if len(kept) == len(entries):
        return False
    if kept:
        hooks["sessionStart"] = kept
    else:
        hooks.pop("sessionStart", None)
    if not hooks:
        data.pop("hooks", None)
    if set(data.keys()) <= {"version"}:
        data = {}
    _write_json_or_delete(path, data)
    return True


def _strip_codex_mcp(target_root: Path) -> bool:
    """Remove our [mcp_servers.memory-seed] block from .codex/config.toml."""
    path = target_root / ".codex" / "config.toml"
    if not path.exists():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return False
    idx = _codex_standard_header_index([ln.rstrip("\n") for ln in lines])
    if idx is None:
        return False
    end = idx + 1
    while end < len(lines) and not lines[end].lstrip().startswith("["):
        end += 1
    del lines[idx:end]
    new_text = "".join(lines)
    if new_text.strip():
        path.write_text(new_text, encoding="utf-8")
    else:
        try:
            path.unlink()
        except OSError:
            pass
    return True


def _uninstall_claude(root: Path) -> bool:
    a = _strip_grouped_hooks(root / ".claude" / "settings.json")
    b = _strip_mcp_entry(root / ".mcp.json", "mcpServers")
    return a or b


def _uninstall_codex(root: Path) -> bool:
    a = _strip_grouped_hooks(root / ".codex" / "hooks.json")
    b = _strip_codex_mcp(root)
    return a or b


def _uninstall_cursor(root: Path) -> bool:
    a = _strip_cursor_hooks(root / ".cursor" / "hooks.json")
    b = _strip_mcp_entry(root / ".cursor" / "mcp.json", "mcpServers")
    return a or b


def _uninstall_gemini(root: Path) -> bool:
    a = _strip_grouped_hooks(root / ".gemini" / "settings.json")
    b = _strip_mcp_entry(root / ".gemini" / "settings.json", "mcpServers")
    return a or b


def _uninstall_copilot(root: Path) -> bool:
    a = _strip_copilot_startup(root)
    b = _strip_mcp_entry(root / ".github" / "mcp.json", "mcpServers")
    c = _strip_mcp_entry(root / ".vscode" / "mcp.json", "servers")
    return a or b or c


_AGENT_UNINSTALLS = {
    "claude": _uninstall_claude,
    "codex": _uninstall_codex,
    "cursor": _uninstall_cursor,
    "gemini": _uninstall_gemini,
    "copilot": _uninstall_copilot,
}


def _routing_seedfiles(agent: str) -> list[SeedFile]:
    return [sf for sf in SEED_FILES if sf.agent == agent]


def _project_config_path(target_root: Path) -> Path:
    return target_root / MEMORY_DIR_NAME / "project.yaml"


def read_project_agents(target_root: Path) -> set[str] | None:
    """Return the configured agent set from .memory-seed/project.yaml, or None.

    None means "no usable config" (absent / empty / malformed / no `agents:`
    block); callers treat None as ALL agents, so legacy projects and the
    zero-config default are unchanged. Fail-open: never raises, never returns an
    empty set from a parse failure. Unknown keys (e.g. a future `users:` block)
    are ignored.
    """
    path = _project_config_path(target_root)
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    agents: set[str] = set()
    saw_agents_key = False
    in_block = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r"^agents\s*:", line):
            saw_agents_key = True
            inline = line.split(":", 1)[1].strip()
            if inline.startswith("[") and inline.endswith("]"):
                for tok in inline[1:-1].split(","):
                    tok = tok.strip().strip("'\"")
                    if tok in KNOWN_AGENTS:
                        agents.add(tok)
                in_block = False
            else:
                in_block = True
            continue
        if in_block:
            m = re.match(r"^\s*-\s*(.+)$", line)
            if m:
                tok = m.group(1).strip().strip("'\"")
                if tok in KNOWN_AGENTS:
                    agents.add(tok)
                continue
            if line and not line[0].isspace():
                in_block = False  # a new top-level key ends the block
    # Present-but-empty `agents:` is a real "zero agents" state, distinct from an
    # absent key (None = unconfigured = all agents).
    return agents if saw_agents_key else None


def selected_agents(target_root: Path) -> set[str]:
    """Active agent set: the configured subset, or ALL known agents if unconfigured."""
    configured = read_project_agents(target_root)
    return configured if configured is not None else set(KNOWN_AGENTS)


def write_project_agents(target_root: Path, agents: set[str]) -> None:
    """Persist the agent selection to .memory-seed/project.yaml.

    Replaces only the `agents:` block, preserving any other content (so a future
    `users:` block survives). Creates a minimal file if none exists.
    """
    path = _project_config_path(target_root)
    ordered = [a for a in KNOWN_AGENTS if a in agents]
    new_block = "\n".join(["agents:"] + [f"  - {a}" for a in ordered])

    text = ""
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""

    if re.search(r"^agents\s*:", text, flags=re.MULTILINE):
        lines = text.splitlines()
        out: list[str] = []
        i = 0
        while i < len(lines):
            if re.match(r"^agents\s*:", lines[i]):
                out.append(new_block)
                i += 1
                while i < len(lines) and re.match(r"^\s*-\s+", lines[i]):
                    i += 1
                continue
            out.append(lines[i])
            i += 1
        text = "\n".join(out)
    elif text.strip():
        text = (text if text.endswith("\n") else text + "\n") + new_block
    else:
        text = f"schema_version: 1\nproject_id: {target_root.name}\n" + new_block

    if not text.endswith("\n"):
        text += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _parse_agent_list(value: str) -> set[str]:
    """Parse a comma/space-separated agent list; raise ValueError on unknown slugs."""
    tokens = [t.strip().lower() for t in re.split(r"[,\s]+", value) if t.strip()]
    if not tokens or tokens == ["all"]:
        return set(KNOWN_AGENTS)
    unknown = [t for t in tokens if t not in KNOWN_AGENTS]
    if unknown:
        raise ValueError(
            f"Unknown agent(s): {', '.join(unknown)}. "
            f"Valid agents: {', '.join(KNOWN_AGENTS)}."
        )
    return set(tokens)


def resolve_agents(cli_value: str | None, *, isatty: bool, prompt_response: str | None = None) -> set[str]:
    """Resolve the agent set for `init`.

    Precedence: explicit `--agents` value > interactive prompt response (TTY only)
    > all agents (preserves the zero-arg / non-TTY default). Pure/testable: the CLI
    reads the prompt and passes the raw string as `prompt_response`.
    """
    if cli_value:
        return _parse_agent_list(cli_value)
    if isatty and prompt_response is not None and prompt_response.strip():
        return _parse_agent_list(prompt_response)
    return set(KNOWN_AGENTS)


def init_project(
    cwd: str | Path = ".",
    dry_run: bool = False,
    force: bool = False,
    agents: set[str] | None = None,
) -> InitResult:
    target_root = Path(cwd).resolve()
    selected = agents if agents is not None else set(KNOWN_AGENTS)
    seed_files = [sf for sf in SEED_FILES if sf.agent is None or sf.agent in selected]
    planned = [seed_file.destination for seed_file in seed_files]
    # Foreign entry-point routing files (a host's own AGENTS.md/CLAUDE.md, no
    # frontmatter) are merged into, not overwritten, so they don't block init.
    existing = [
        seed_file.destination
        for seed_file in seed_files
        if (target_root / seed_file.destination).exists()
        and not _is_foreign_routing_file(target_root, seed_file)
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

    for seed_file in seed_files:
        destination = target_root / seed_file.destination

        # Foreign routing file: inject/re-sync our managed block, never clobber
        # (holds even under --force — the point is non-destruction).
        merged = _maybe_merge_foreign_routing(target_root, seed_file)
        if merged is not None:
            if merged:
                created.append(seed_file.destination)
            continue

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

    for merge, destination in _agent_merges(selected):
        if merge(target_root) and destination not in created:
            created.append(destination)

    # Persist the selection only when it is a proper subset. The all-agents
    # default writes no project.yaml, so existing projects (and the file set
    # asserted by tests) stay byte-identical, and "all" stays dynamic.
    if selected != set(KNOWN_AGENTS):
        write_project_agents(target_root, selected)
        cfg = MEMORY_DIR_NAME + "/project.yaml"
        if cfg not in created:
            created.append(cfg)

    return InitResult(
        changed=True,
        planned=planned,
        created=created,
        backed_up=backed_up,
    )


def update_project(cwd: str | Path = ".", dry_run: bool = False) -> InitResult:
    target_root = Path(cwd).resolve()
    # Respect the persisted agent selection (ALL when no project.yaml), so update
    # never re-adds a deselected agent's files.
    selected = selected_agents(target_root)
    seed_files = [sf for sf in SEED_FILES if sf.agent is None or sf.agent in selected]
    planned = [seed_file.destination for seed_file in seed_files]

    if dry_run:
        return InitResult(changed=False, planned=planned)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    created: list[str] = []
    backed_up: list[str] = []
    archived: list[str] = []

    for seed_file in seed_files:
        destination = target_root / seed_file.destination
        if _is_runtime_local_file(seed_file.destination) and destination.exists():
            continue

        # Foreign routing file: inject/re-sync our managed block in place instead
        # of archiving + overwriting the host's content (the "second merge" on a
        # version bump replaces just the block when its text changed).
        merged = _maybe_merge_foreign_routing(target_root, seed_file)
        if merged is not None:
            if merged:
                created.append(seed_file.destination)
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

    for merge, destination in _agent_merges(selected):
        if merge(target_root) and destination not in created:
            created.append(destination)

    return InitResult(
        changed=bool(created or backed_up or archived),
        planned=planned,
        created=created,
        backed_up=backed_up,
        archived=archived,
    )


def add_agent(cwd: str | Path = ".", agent: str = "") -> dict:
    """Add an agent to an existing project: install its files + update project.yaml."""
    if agent not in KNOWN_AGENTS:
        raise ValueError(f"Unknown agent: {agent}. Valid: {', '.join(KNOWN_AGENTS)}.")
    target_root = Path(cwd).resolve()
    selected = selected_agents(target_root)
    if agent in selected:
        return {"changed": False, "message": f"Agent '{agent}' is already installed.", "created": [], "backed_up": []}

    created: list[str] = []
    for sf in _routing_seedfiles(agent):
        dest = target_root / sf.destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        _copy_text_file(sf.source, dest)
        created.append(sf.destination)
    for merge, destination in _AGENT_MERGES[agent]:
        if merge(target_root) and destination not in created:
            created.append(destination)

    write_project_agents(target_root, selected | {agent})
    return {"changed": True, "message": f"Added agent '{agent}'.", "created": created, "backed_up": []}


def remove_agent(cwd: str | Path = ".", agent: str = "") -> dict:
    """Remove an agent: strip our entries from its configs, delete its routing file.

    Strip-in-place — foreign content is preserved; config files are deleted only
    when nothing of value remains. Everything touched is backed up first. Never
    deletes shared directories.
    """
    if agent not in KNOWN_AGENTS:
        raise ValueError(f"Unknown agent: {agent}. Valid: {', '.join(KNOWN_AGENTS)}.")
    target_root = Path(cwd).resolve()
    selected = selected_agents(target_root)
    if agent not in selected:
        return {"changed": False, "message": f"Agent '{agent}' is not installed.", "removed": [], "backed_up": [], "warning": None}

    # Back up every file we may touch (config files + routing file) before changes.
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backed_up: list[str] = []
    rels = list(dict.fromkeys(
        [dest for (_fn, dest) in _AGENT_MERGES[agent]]
        + [sf.destination for sf in _routing_seedfiles(agent)]
    ))
    for rel in rels:
        p = target_root / rel
        if p.exists():
            _ensure_backup_gitignore(target_root)
            backup_rel = Path(MEMORY_DIR_NAME) / "backups" / timestamp / rel
            bp = target_root / backup_rel
            bp.parent.mkdir(parents=True, exist_ok=True)
            _copy_text_file(p, bp)
            backed_up.append(backup_rel.as_posix())

    removed: list[str] = []
    if _AGENT_UNINSTALLS[agent](target_root):
        removed.append(f"{agent} config entries")
    for sf in _routing_seedfiles(agent):
        dest = target_root / sf.destination
        if dest.exists():
            try:
                dest.unlink()
                removed.append(sf.destination)
            except OSError:
                pass

    new_selected = selected - {agent}
    write_project_agents(target_root, new_selected)
    warning = None
    if not new_selected:
        warning = (
            "No agents remain selected. The .memory-seed runtime and AGENTS.md are "
            "still installed; run `memory-seed agents add <agent>` to re-enable one."
        )
    return {"changed": True, "message": f"Removed agent '{agent}'.", "removed": removed, "backed_up": backed_up, "warning": warning}


def doctor(cwd: str | Path = ".") -> DoctorResult:
    target_root = Path(cwd).resolve()
    missing: list[str] = []
    version_mismatches: list[dict[str, str]] = []

    # Only check files for the project's selected agents (ALL when unconfigured),
    # so a deselected agent's intentionally-absent files are not flagged missing.
    selected = selected_agents(target_root)

    for seed_file in SEED_FILES:
        if seed_file.agent is not None and seed_file.agent not in selected:
            continue
        candidate = target_root / seed_file.destination
        if not candidate.exists():
            missing.append(seed_file.destination)
            continue

        if not candidate.suffix == ".md":
            continue
        if seed_file.destination.startswith(".agents/"):
            continue  # agent personas are project-local; not version-tracked control plane
        actual = _read_memory_system_version(candidate)
        if actual is None and seed_file.destination in ROUTING_DESTINATIONS:
            # Foreign host-owned routing file (e.g. HyperFrames AGENTS.md). We only
            # manage our injected block, not the file's version; the route-presence
            # check below flags it if our block is missing.
            continue
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
    codex_status = _codex_mcp_status(target_root) if "codex" in selected else "absent"
    if "codex" in selected and (target_root / ".codex" / "hooks.json").exists() and codex_status == "absent":
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

    # Orphan-skill check: every skill runbook must be registered in the trigger
    # registry, or agents will never load it. index.md references each skill as
    # `- skill: <filename>`; match that token (not a bare filename) so one skill
    # name being a substring of another (search.md vs code_search.md) can't mask an orphan.
    skills_dir = target_root / ".memory-seed" / "skills"
    registry_path = skills_dir / "index.md"
    if registry_path.exists():
        registry_text = registry_path.read_text(encoding="utf-8")
        for skill_path in sorted(skills_dir.glob("*.md")):
            if skill_path.name == "index.md":
                continue
            if f"skill: {skill_path.name}" not in registry_text:
                warnings.append(
                    f"Skill file .memory-seed/skills/{skill_path.name} is not registered "
                    "in skills/index.md (orphan skill). Add a trigger entry referencing it, "
                    "or remove the file."
                )

    # Route-presence check: if a .memory-seed/ runtime exists, the present entry-point
    # files must route into it (be ours, or a foreign file carrying our managed block).
    # A foreign entry-point file without the block leaves the runtime orphaned — no
    # agent is ever pointed at it (the demo HyperFrames AGENTS.md before 2.8).
    if (target_root / MEMORY_DIR_NAME).is_dir():
        for seed_file in SEED_FILES:
            if seed_file.destination not in ROUTING_DESTINATIONS:
                continue
            if seed_file.agent is not None and seed_file.agent not in selected:
                continue
            candidate = target_root / seed_file.destination
            if candidate.exists() and not _file_routes_into_runtime(candidate):
                warnings.append(
                    f"{seed_file.destination} does not route into the .memory-seed/ "
                    "runtime (foreign file, no memory-seed block). Run "
                    "`memory-seed update` to inject the routing block."
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
    ) or destination.startswith(".agents/")


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


def _is_foreign_routing_file(target_root: Path, seed_file: SeedFile) -> bool:
    """True if this is an entry-point routing file that already exists and is
    NOT ours (no memory-system-version frontmatter) — i.e. a host-owned file
    we must merge into rather than overwrite (the demo HyperFrames AGENTS.md)."""
    if seed_file.destination not in ROUTING_DESTINATIONS:
        return False
    destination = target_root / seed_file.destination
    return destination.exists() and _read_memory_system_version(destination) is None


def _file_routes_into_runtime(path: Path) -> bool:
    """True if an entry-point file routes into the .memory-seed/ runtime: it is
    either ours (carries our frontmatter) or a foreign file carrying our managed
    routing block. Used by doctor() to detect an orphaned runtime."""
    text = path.read_text(encoding="utf-8")
    if _read_memory_system_version(path) is not None:
        return True
    return _ROUTING_BLOCK_RE.search(text) is not None


def _merge_routing_stanza(path: Path, stanza: str = _ROUTING_STANZA) -> bool:
    """Inject or re-sync the memory-seed managed routing block in a foreign
    entry-point file, never touching the host's own content.

    - No marker present -> append the block at end of file.
    - Marker present -> replace the marked region in place, but only if the
      rendered block differs (content-equality gate, like _merge_grouped_hook),
      so a release bump with unchanged stanza text causes no churn.

    Returns True if the file was written, False if it was already current.
    """
    text = path.read_text(encoding="utf-8")
    match = _ROUTING_BLOCK_RE.search(text)
    if match:
        if match.group(0) == stanza:
            return False
        new_text = text[: match.start()] + stanza + text[match.end() :]
        path.write_text(new_text, encoding="utf-8")
        return True
    path.write_text(text.rstrip("\n") + "\n\n" + stanza + "\n", encoding="utf-8")
    return True


def _maybe_merge_foreign_routing(target_root: Path, seed_file: SeedFile) -> bool | None:
    """If this is a foreign (host-owned) entry-point routing file, inject/re-sync
    our managed routing block and return whether the file was written. Returns
    None when the file is not a foreign routing file, signalling the caller to
    fall back to normal full-file copy / version-gate handling."""
    if not _is_foreign_routing_file(target_root, seed_file):
        return None
    return _merge_routing_stanza(target_root / seed_file.destination)


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
