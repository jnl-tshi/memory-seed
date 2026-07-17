from __future__ import annotations

import json
import os
import re
import hashlib
import secrets
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator, Literal, Sequence

from .text_files import (
    read_json_file,
    read_text_file,
    scan_implicit_text_io,
    scan_text_encoding,
    write_json_file,
    write_text_file,
)

PACKAGE_ROOT = Path(__file__).resolve().parent
SEED_ROOT = PACKAGE_ROOT / "seed"
VERSION = "2.19"
MEMORY_DIR_NAME = ".memory-seed"
LEGACY_MEMORY_DIR_NAME = ".AGENTS"
BACKUP_IGNORE_ENTRY = ".memory-seed/backups/"
LOCAL_CONFIG_IGNORE_ENTRY = ".memory-seed/local.yaml"
DEFAULT_WORKTREE_NAMESPACES = {
    "codex": ".codex/worktrees",
    "claude": ".claude/worktrees",
    "gemini": ".gemini/worktrees",
    "cursor": ".cursor/worktrees",
}
DEFAULT_ROOT_WRITE_POLICY = "explicit-override"
DEFAULT_UNMANAGED_WRITE_POLICY = "warn"

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
    "Append a session entry to the active grouped session target "
    "(`.memory-seed/sessions/YYYY-MM/YYYY-MM-DD.md` by default) after meaningful work.\n"
    "Instructions above this block remain authoritative for their own domain.\n"
    "<!-- END memory-seed -->"
)

SESSION_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
SESSION_DAY_DIR_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})$")
SESSION_MONTH_DIR_RE = re.compile(r"^(\d{4}-\d{2})$")
SESSION_USER_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_RESERVED_SESSION_STEMS = {"index", "readme", "policy"}
HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class SeedFile:
    source: Path
    destination: str
    # Agent this file belongs to (e.g. "claude"). None = agent-agnostic, always
    # installed. Agent-tagged files are installed only when that agent is selected.
    agent: str | None = None


@dataclass(frozen=True)
class BranchStatus:
    is_git_repo: bool
    branch: str | None
    is_integration_branch: bool
    dirty: bool
    upstream: str | None
    ahead: int | None
    behind: int | None
    worktree_count: int
    recent_merge_commit: str | None
    warnings: tuple[str, ...]
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "is_git_repo": self.is_git_repo,
            "branch": self.branch,
            "is_integration_branch": self.is_integration_branch,
            "dirty": self.dirty,
            "upstream": self.upstream,
            "ahead": self.ahead,
            "behind": self.behind,
            "worktree_count": self.worktree_count,
            "recent_merge_commit": self.recent_merge_commit,
            "warnings": list(self.warnings),
            "recommendation": self.recommendation,
            "worktree_guard_command": "memory-seed worktree guard --agent <agent> --write-intent",
        }


@dataclass(frozen=True)
class WorktreeGuardConfig:
    root_write_policy: str
    unmanaged_write_policy: str
    namespaces: dict[str, str]


@dataclass(frozen=True)
class WorktreeGuardStatus:
    ok: bool
    severity: str
    agent_type: str | None
    classification: str
    safe_to_write: bool
    write_intent: bool
    current_branch: str | None
    head: str | None
    dirty: bool | None
    worktree_path: str | None
    repo_root: str | None
    expected_namespace: str | None
    actual_namespace_owner: str | None
    root_write_policy: str
    unmanaged_write_policy: str
    recommended_next_action: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "severity": self.severity,
            "agent_type": self.agent_type,
            "classification": self.classification,
            "safe_to_write": self.safe_to_write,
            "write_intent": self.write_intent,
            "current_branch": self.current_branch,
            "head": self.head,
            "dirty": self.dirty,
            "worktree_path": self.worktree_path,
            "repo_root": self.repo_root,
            "expected_namespace": self.expected_namespace,
            "actual_namespace_owner": self.actual_namespace_owner,
            "root_write_policy": self.root_write_policy,
            "unmanaged_write_policy": self.unmanaged_write_policy,
            "recommended_next_action": self.recommended_next_action,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SkillProfile:
    description: str
    skills: tuple[str, ...]


@dataclass(frozen=True)
class SkillSelection:
    profiles: set[str]
    selected: set[str]
    ignored: set[str]
    explicit: bool


@dataclass(frozen=True)
class SkillStatus:
    core: list[str]
    installed_optional: list[str]
    selected_optional: list[str]
    ignored: list[str]
    available_optional: list[str]
    profiles: dict[str, list[str]]
    profile_descriptions: dict[str, str]
    descriptions: dict[str, str]

    def __getitem__(self, key: str):
        return getattr(self, key)


@dataclass(frozen=True)
class Runtime:
    workspace_root: Path
    memory_dir: Path
    legacy: bool = False


@dataclass(frozen=True)
class SessionDocument:
    path: Path
    session_date: str
    user: str | None
    layout: Literal["legacy-flat", "per-user-day", "month-flat", "month-user"]


@dataclass(frozen=True)
class SessionTarget:
    path: Path
    session_date: str
    user: str | None
    layout: Literal["legacy-flat", "per-user-day", "month-flat", "month-user"]


@dataclass(frozen=True)
class DiagramSidecarDocument:
    path: Path
    diagram_date: str | None
    layout: Literal["legacy-diagram", "month-diagram"]
    malformed_reason: str | None = None


@dataclass(frozen=True)
class LinkSidecarDocument:
    path: Path
    link_date: str | None
    layout: Literal["legacy-link", "month-link"]
    malformed_reason: str | None = None


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


@dataclass(frozen=True)
class GitHookStatus:
    is_git_repo: bool
    state: str
    message: str
    hook_path: str | None = None
    managed: bool = False
    current: bool = False
    repairable: bool = False


@dataclass
class CompactResult:
    sessions_scanned: list[str]
    headings: dict[str, list[str]]
    full_text: str
    date_range: tuple[str, str] | None


@dataclass(frozen=True)
class LinkIssue:
    file: str
    kind: str
    detail: str
    severity: Literal["error", "warning"] = "error"


@dataclass
class LinksCheckResult:
    ok: bool
    files_checked: int
    issues: list[LinkIssue] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectParticipant:
    slug: str
    initials: str
    display_name: str | None = None


@dataclass
class SessionLayoutMigrationResult:
    changed: bool
    planned: list[str] = field(default_factory=list)
    migrated: list[str] = field(default_factory=list)
    backed_up: list[Path] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _FlatSessionEntry:
    text: str
    entry_id: str | None
    user_initials: str | None


@dataclass(frozen=True)
class _SessionEntryRecord:
    text: str
    entry_id: str | None
    timestamp: str | None
    session_date: str
    branch: str | None
    source_path: str
    target_path: str
    user: str | None = None


@dataclass(frozen=True)
class _DiagramSidecarRecord:
    text: str
    entry_id: str | None
    timestamp: str | None
    diagram_date: str | None
    source_path: str
    target_path: str


@dataclass
class SessionFuseResult:
    changed: bool
    planned_entries: list[str] = field(default_factory=list)
    planned_sidecars: list[str] = field(default_factory=list)
    removed_sources: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@dataclass
class SessionMergeBranchResult:
    committed: bool
    merge_in_progress: bool = False
    conflicts: list[str] = field(default_factory=list)
    planned_entries: list[str] = field(default_factory=list)
    planned_sidecars: list[str] = field(default_factory=list)
    removed_sources: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    stamped_entries: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _SessionFusePlan:
    source_label: str
    source_commit: str
    base_commit: str
    changed_paths: tuple[str, ...]
    import_entries: tuple[_SessionEntryRecord, ...]
    import_sidecars: tuple[_DiagramSidecarRecord, ...]
    planned_entries: tuple[str, ...]
    planned_sidecars: tuple[str, ...]
    removed_sources: tuple[str, ...]


@dataclass
class SessionPreparePrBranchResult:
    ready: bool
    changed: bool = False
    merge_in_progress: bool = False
    base_branch: str | None = None
    source_branch: str | None = None
    planned_entries: list[str] = field(default_factory=list)
    planned_sidecars: list[str] = field(default_factory=list)
    removed_sources: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    stamped_entries: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    prep_commit: str | None = None
    branch_head: str | None = None
    issues: list[str] = field(default_factory=list)


@dataclass
class SessionOpenPrResult:
    opened: bool
    dry_run: bool = False
    base_branch: str | None = None
    source_branch: str | None = None
    remote_name: str | None = None
    remote_url: str | None = None
    pushed: bool = False
    pr_created: bool = False
    pr_title: str | None = None
    pr_body: str | None = None
    pr_url: str | None = None
    planned_entries: list[str] = field(default_factory=list)
    planned_sidecars: list[str] = field(default_factory=list)
    removed_sources: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    stamped_entries: list[str] = field(default_factory=list)
    prep_commit: str | None = field(default=None)
    branch_head: str | None = field(default=None)
    conflicts: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def iter_session_documents(sessions_dir: Path) -> Iterator[SessionDocument]:
    documents: list[SessionDocument] = []
    if not sessions_dir.is_dir():
        return iter(())

    for path in sessions_dir.iterdir():
        if path.is_file():
            match = SESSION_DATE_RE.match(path.name)
            if not match:
                continue
            date_str = match.group(1)
            if not _valid_session_date(date_str):
                continue
            documents.append(SessionDocument(path=path, session_date=date_str, user=None, layout="legacy-flat"))
            continue

        if not path.is_dir():
            continue
        day_match = SESSION_DAY_DIR_RE.match(path.name)
        if day_match:
            date_str = day_match.group(1)
            if not _valid_session_date(date_str):
                continue
            for child in path.iterdir():
                if not child.is_file() or child.suffix != ".md":
                    continue
                user = child.stem
                if user in _RESERVED_SESSION_STEMS or not SESSION_USER_SLUG_RE.match(user):
                    continue
                documents.append(SessionDocument(path=child, session_date=date_str, user=user, layout="per-user-day"))
            continue

        month_match = SESSION_MONTH_DIR_RE.match(path.name)
        if not month_match:
            continue
        month_str = month_match.group(1)
        for child in path.iterdir():
            if child.is_file():
                date_match = SESSION_DATE_RE.match(child.name)
                if not date_match:
                    continue
                date_str = date_match.group(1)
                if not _valid_session_date(date_str) or not date_str.startswith(month_str + "-"):
                    continue
                documents.append(SessionDocument(path=child, session_date=date_str, user=None, layout="month-flat"))
                continue
            if not child.is_dir():
                continue
            day_match = SESSION_DAY_DIR_RE.match(child.name)
            if not day_match:
                continue
            date_str = day_match.group(1)
            if not _valid_session_date(date_str) or not date_str.startswith(month_str + "-"):
                continue
            for user_file in child.iterdir():
                if not user_file.is_file() or user_file.suffix != ".md":
                    continue
                user = user_file.stem
                if user in _RESERVED_SESSION_STEMS or not SESSION_USER_SLUG_RE.match(user):
                    continue
                documents.append(SessionDocument(path=user_file, session_date=date_str, user=user, layout="month-user"))

    return iter(sorted(documents, key=lambda doc: (doc.session_date, doc.user or "", doc.path.as_posix())))


def iter_diagram_sidecar_documents(sessions_dir: Path) -> Iterator[DiagramSidecarDocument]:
    documents: list[DiagramSidecarDocument] = []
    diagrams_dir = sessions_dir / "diagrams"
    if not diagrams_dir.is_dir():
        return iter(())

    for path in diagrams_dir.iterdir():
        if path.is_file():
            date_match = SESSION_DATE_RE.match(path.name)
            if not date_match or not _valid_session_date(date_match.group(1)):
                documents.append(
                    DiagramSidecarDocument(
                        path=path,
                        diagram_date=None,
                        layout="legacy-diagram",
                        malformed_reason=f"filename '{path.name}' is not a YYYY-MM-DD.md date",
                    )
                )
                continue
            documents.append(DiagramSidecarDocument(path=path, diagram_date=date_match.group(1), layout="legacy-diagram"))
            continue

        if not path.is_dir():
            continue
        month_match = SESSION_MONTH_DIR_RE.match(path.name)
        if not month_match:
            continue
        month_str = month_match.group(1)
        for child in path.iterdir():
            if not child.is_file() or child.suffix != ".md":
                continue
            date_match = SESSION_DATE_RE.match(child.name)
            if not date_match or not _valid_session_date(date_match.group(1)):
                documents.append(
                    DiagramSidecarDocument(
                        path=child,
                        diagram_date=None,
                        layout="month-diagram",
                        malformed_reason=f"filename '{child.name}' is not a YYYY-MM-DD.md date",
                    )
                )
                continue
            date_str = date_match.group(1)
            if not date_str.startswith(month_str + "-"):
                documents.append(
                    DiagramSidecarDocument(
                        path=child,
                        diagram_date=date_str,
                        layout="month-diagram",
                        malformed_reason=f"date '{date_str}' does not match month folder '{month_str}'",
                    )
                )
                continue
            documents.append(DiagramSidecarDocument(path=child, diagram_date=date_str, layout="month-diagram"))

    return iter(sorted(documents, key=lambda doc: doc.path.as_posix()))


def iter_link_sidecar_documents(sessions_dir: Path) -> Iterator[LinkSidecarDocument]:
    """Lifecycle-edge link sidecars under ``sessions/links``, mirroring
    ``iter_diagram_sidecar_documents``. A link sidecar records
    ``supersedes``/``evolves``/``related_entries`` edges authored *after* an
    entry (append-only enrichment - the entry itself is never reopened). Same
    dated layouts: ``links/YYYY-MM/YYYY-MM-DD.md`` and legacy
    ``links/YYYY-MM-DD.md``. Returns an empty iterator when the dir is absent."""
    documents: list[LinkSidecarDocument] = []
    links_dir = sessions_dir / "links"
    if not links_dir.is_dir():
        return iter(())

    for path in links_dir.iterdir():
        if path.is_file():
            date_match = SESSION_DATE_RE.match(path.name)
            if not date_match or not _valid_session_date(date_match.group(1)):
                documents.append(
                    LinkSidecarDocument(
                        path=path,
                        link_date=None,
                        layout="legacy-link",
                        malformed_reason=f"filename '{path.name}' is not a YYYY-MM-DD.md date",
                    )
                )
                continue
            documents.append(LinkSidecarDocument(path=path, link_date=date_match.group(1), layout="legacy-link"))
            continue

        if not path.is_dir():
            continue
        month_match = SESSION_MONTH_DIR_RE.match(path.name)
        if not month_match:
            continue
        month_str = month_match.group(1)
        for child in path.iterdir():
            if not child.is_file() or child.suffix != ".md":
                continue
            date_match = SESSION_DATE_RE.match(child.name)
            if not date_match or not _valid_session_date(date_match.group(1)):
                documents.append(
                    LinkSidecarDocument(
                        path=child,
                        link_date=None,
                        layout="month-link",
                        malformed_reason=f"filename '{child.name}' is not a YYYY-MM-DD.md date",
                    )
                )
                continue
            date_str = date_match.group(1)
            if not date_str.startswith(month_str + "-"):
                documents.append(
                    LinkSidecarDocument(
                        path=child,
                        link_date=date_str,
                        layout="month-link",
                        malformed_reason=f"date '{date_str}' does not match month folder '{month_str}'",
                    )
                )
                continue
            documents.append(LinkSidecarDocument(path=child, link_date=date_str, layout="month-link"))

    return iter(sorted(documents, key=lambda doc: doc.path.as_posix()))


def _valid_session_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _validate_session_user(user: str) -> str:
    if not SESSION_USER_SLUG_RE.match(user):
        raise ValueError(
            "User slug must start with a lowercase letter or digit and contain "
            "only lowercase letters, digits, underscores, or hyphens (max 64 chars)."
        )
    if user in _RESERVED_SESSION_STEMS:
        raise ValueError(f"User slug is reserved: {user}")
    return user


def _local_config_path(target_root: Path) -> Path:
    return target_root / MEMORY_DIR_NAME / "local.yaml"


def read_local_user(target_root: Path) -> str | None:
    path = _local_config_path(target_root)
    if not path.exists():
        return None
    try:
        for line in read_text_file(path).splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not stripped.startswith("user:"):
                continue
            user = stripped.split(":", 1)[1].strip()
            if user.startswith(("'", '"')) and user.endswith(("'", '"')) and len(user) >= 2:
                user = user[1:-1]
            return _validate_session_user(user)
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return None


def write_local_user(target_root: Path, user: str) -> None:
    user = _validate_session_user(user)
    memory_dir = target_root / MEMORY_DIR_NAME
    memory_dir.mkdir(parents=True, exist_ok=True)
    write_text_file(_local_config_path(target_root), f"user: {user}\n")
    _ensure_gitignore_entry(target_root, LOCAL_CONFIG_IGNORE_ENTRY)


def clear_local_user(target_root: Path) -> bool:
    path = _local_config_path(target_root)
    if not path.exists():
        return False
    path.unlink()
    return True


def resolve_active_user(cwd: Path | str = ".", explicit_user: str | None = None) -> str | None:
    if explicit_user:
        return _validate_session_user(explicit_user)

    env_user = os.environ.get("MEMORY_SEED_USER")
    if env_user:
        return _validate_session_user(env_user)

    runtime = resolve_runtime(cwd)
    if runtime.legacy:
        return None
    return read_local_user(runtime.workspace_root)


def session_path(sessions_dir: Path, date_str: str, user: str) -> Path:
    if not _valid_session_date(date_str):
        raise ValueError(f"Invalid session date: {date_str}")
    user = _validate_session_user(user)
    return sessions_dir / date_str[:7] / date_str / f"{user}.md"


def _session_flat_path(sessions_dir: Path, date_str: str) -> Path:
    if not _valid_session_date(date_str):
        raise ValueError(f"Invalid session date: {date_str}")
    return sessions_dir / date_str[:7] / f"{date_str}.md"


_ENTRY_ID_RE = re.compile(r"^entry_id:\s*(\S+)\s*$", re.MULTILINE)
_FILE_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)
_LEGACY_ENTRY_ID_RE = r"ms-[0-9a-f]{8}"
_V2_ENTRY_ID_RE = r"mse_[0-9a-hjkmnp-tv-z]{16}"
_RELATED_ENTRY_REF_RE = re.compile(rf"(?:{_LEGACY_ENTRY_ID_RE}|{_V2_ENTRY_ID_RE})")
# Memory-Entry trailer stamping accepts both id generations plus the wider
# lowercase ids observed from other agents (e.g. 20-hex-char codex ids);
# anything else is never stamped, so a malformed id cannot poison the trailer
# channel that find_trailer_commits greps.
_TRAILER_ENTRY_ID_RE = re.compile(r"(?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32})")
_RELATED_MEMORY_REF_RE = re.compile(r"msm_[0-9a-zA-Z]+")
_FENCED_YAML_RE = re.compile(r"^```ya?ml\s*\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
# An entry heading with a parseable timestamp, followed immediately by its
# fenced yaml block. Used to attribute supersedes refs to a source entry and
# timestamp for the forward-only guard; blocks whose heading doesn't match
# still get the plain dangling-ref scan via _FENCED_YAML_RE.
_ENTRY_TS_YAML_RE = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+-[^\n]*\n\s*```ya?ml\s*\n(.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)
_COMMIT_TOKEN_RE = re.compile(r"-\s*['\"]?([0-9a-fA-F]+)['\"]?")
_FULL_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SUPPORTED_SCHEMA_VERSIONS = {"1", "2"}
_CROCKFORD_BASE32_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"


def _parse_frontmatter_scalars(block: str) -> dict[str, str]:
    """Parse the top-level ``key: value`` scalars of a frontmatter block.

    Stdlib-only (no YAML dependency): reads unindented ``key: value`` lines and
    strips matching surrounding quotes. List keys (e.g. related_entries) are
    ignored here; references inside them are scanned separately by regex.
    """
    scalars: dict[str, str] = {}
    for line in block.splitlines():
        if not line or line[0] in " \t#-":
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
            value = value[1:-1]
        if key and value:
            scalars[key] = value
    return scalars


def _frontmatter_list_region(block: str, list_key: str) -> str:
    """Return the indented region following ``<list_key>:`` within a frontmatter
    block (the list items), or "" if the key is absent."""
    lines = block.splitlines()
    out: list[str] = []
    collecting = False
    for line in lines:
        if collecting:
            if line[:1] in (" ", "\t"):
                out.append(line)
                continue
            break
        if line.strip().rstrip().rstrip(":") == list_key and line.strip().endswith(":"):
            collecting = True
    return "\n".join(out)


def _parse_continuity_items(region: str) -> list[dict[str, str]]:
    """Parse the indented ``continuity:`` list region into item mappings.

    Stdlib-only, shared by the validator here and the chunk extractor in
    ``semantic_cache`` so both read the identical shape. Each ``- `` starts a
    new item; ``key: value`` lines fill the current item. Malformed lines are
    kept out of items rather than guessed at - the validator reports the
    resulting missing keys."""
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in region.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if current is not None:
                items.append(current)
            current = {}
            stripped = stripped[2:].strip()
            if not stripped:
                continue
        if current is None:
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = value.strip().strip("'\"")
    if current is not None:
        items.append(current)
    return items


_CONTINUITY_KINDS = {"rename", "migration", "removal"}
_AUTHORED_INVERSE_RE = re.compile(r"^(superseded_by|evolved_by)\s*:", re.MULTILINE)


def _fenced_yaml_blocks(text: str) -> Iterator[str]:
    for match in _FENCED_YAML_RE.finditer(text):
        yield match.group(1)


def _commit_exists(root: Path, sha: str) -> bool | None:
    """Whether ``sha`` names a commit in the repository at ``root``.

    Returns ``None`` when git itself is unavailable or unresponsive - callers
    skip the existence check in that case rather than failing (matching the
    no-``.git``-directory behavior).
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{sha}^{{commit}}"],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.returncode == 0


def find_trailer_commits(root: Path, entry_id: str) -> list[str] | None:
    """Commits (``<sha> <subject>`` lines) whose message carries a
    ``Memory-Entry: <entry_id>`` trailer, across all refs.

    The trailer is the write-path half of commit<->entry linking: the
    ``commits:`` field on an entry can only be backfilled while that entry is
    still the newest one, so the trailer provides coverage for commits made
    after the window closed. Returns ``None`` (not an error) when ``root`` is
    not a git repository or git is unavailable - the package works outside git.
    """
    if not (root / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "--all", f"--grep=Memory-Entry: {entry_id}", "--format=%H %s"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return None
    if proc.returncode != 0:
        return None
    return [line for line in proc.stdout.splitlines() if line.strip()]


def commit_reference_ids(root: Path, entry_id: str, commits_field: Sequence[str] = ()) -> set[str]:
    """Full commit SHAs that link commits to this entry, from both sources:
    the entry's own ``commits:`` field and any commit carrying a
    ``Memory-Entry: <entry_id>`` trailer. Union, deduped by SHA - a commit that
    is both listed and trailered counts once. Outside a git repo the trailer
    scan is skipped, so this returns the field-only set (never fails).

    This is a caller-side signal deliberately kept out of ``build_related_entry_graph``:
    the graph reader stays pure (no subprocess) so frequent readers like
    ``memory_search`` never shell out to git. See docs/3_Spec/graph-edge-contract.md.
    """
    ids: set[str] = {sha for sha in commits_field if _FULL_COMMIT_SHA_RE.match(sha)}
    trailer = find_trailer_commits(root, entry_id)
    if trailer:
        for line in trailer:
            sha = line.split(maxsplit=1)[0].strip()
            if sha:
                ids.add(sha)
    return ids


def _git_text(root: Path, args: Sequence[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return 1, ""
    return proc.returncode, proc.stdout.strip()


def branch_status(cwd: str | Path = ".") -> BranchStatus:
    """Read-only Git branch posture check for feature-branch guardrails."""
    root = Path(cwd).resolve()
    code, top = _git_text(root, ("rev-parse", "--show-toplevel"))
    if code != 0 or not top:
        return BranchStatus(
            is_git_repo=False,
            branch=None,
            is_integration_branch=False,
            dirty=False,
            upstream=None,
            ahead=None,
            behind=None,
            worktree_count=0,
            recent_merge_commit=None,
            warnings=("Not a Git repository.",),
            recommendation="Not a Git repository; branch-history guidance is unavailable.",
        )

    repo = Path(top)
    _, branch = _git_text(repo, ("branch", "--show-current"))
    branch = branch or None
    is_integration = branch in {"main", "master"}

    _, status_out = _git_text(repo, ("status", "--short"))
    dirty = bool(status_out.strip())

    upstream = None
    ahead = behind = None
    code, upstream_out = _git_text(repo, ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"))
    if code == 0 and upstream_out:
        upstream = upstream_out
        code, counts = _git_text(repo, ("rev-list", "--left-right", "--count", "HEAD...@{u}"))
        if code == 0:
            parts = counts.split()
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                ahead, behind = int(parts[0]), int(parts[1])

    code, worktrees = _git_text(repo, ("worktree", "list", "--porcelain"))
    worktree_count = 0
    if code == 0 and worktrees:
        worktree_count = sum(1 for line in worktrees.splitlines() if line.startswith("worktree "))

    code, merge_commit = _git_text(repo, ("log", "--merges", "-n", "1", "--format=%H"))
    if code != 0 or not merge_commit:
        merge_commit = None

    warnings: list[str] = []
    if is_integration and dirty:
        warnings.append(
            "Current integration branch has uncommitted changes; use a task branch/worktree for distinct feature work."
        )
    elif is_integration:
        warnings.append("On integration branch; create a task branch before distinct feature/proposal work.")
    if merge_commit is None:
        warnings.append("No recent merge commit found; fast-forward or direct commits produce a linear graph.")

    if not branch:
        recommendation = "Detached HEAD; create or switch to a task branch before writing feature work."
    elif is_integration:
        recommendation = (
            "For distinct feature/proposal work, create a task branch and integrate with "
            "git merge --no-ff to preserve visible branch topology."
        )
    else:
        recommendation = (
            f"Task branch '{branch}' detected; integrate into the base branch with "
            "git merge --no-ff when the work is complete."
        )

    return BranchStatus(
        is_git_repo=True,
        branch=branch,
        is_integration_branch=is_integration,
        dirty=dirty,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        worktree_count=worktree_count,
        recent_merge_commit=merge_commit,
        warnings=tuple(warnings),
        recommendation=recommendation,
    )


def _casefold_parts(path: Path) -> tuple[str, ...]:
    return tuple(part.casefold() for part in path.resolve().parts)


def _is_relative_to_casefold(child: Path, parent: Path) -> bool:
    child_parts = _casefold_parts(child)
    parent_parts = _casefold_parts(parent)
    return len(child_parts) >= len(parent_parts) and child_parts[: len(parent_parts)] == parent_parts


def _parse_worktree_list(porcelain: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in porcelain.splitlines():
        if raw.startswith("worktree "):
            if current:
                items.append(current)
            current = {"path": raw[len("worktree "):].strip()}
            continue
        if current is None or " " not in raw:
            continue
        key, value = raw.split(" ", 1)
        current[key] = value.strip()
    if current:
        items.append(current)
    return items


def _namespace_owner(repo_root: Path, worktree_path: Path, namespaces: dict[str, str]) -> str | None:
    for owner, namespace in sorted(namespaces.items()):
        namespace_root = repo_root / namespace
        if _is_relative_to_casefold(worktree_path, namespace_root):
            return owner
    return None


def _worktree_guard_config_for(root: Path) -> WorktreeGuardConfig:
    namespaces = dict(DEFAULT_WORKTREE_NAMESPACES)
    root_write_policy = DEFAULT_ROOT_WRITE_POLICY
    unmanaged_write_policy = DEFAULT_UNMANAGED_WRITE_POLICY
    path = _project_config_path(root)
    if not path.exists():
        return WorktreeGuardConfig(root_write_policy, unmanaged_write_policy, namespaces)
    try:
        text = read_text_file(path)
    except OSError:
        return WorktreeGuardConfig(root_write_policy, unmanaged_write_policy, namespaces)

    block = _extract_yaml_block(text, "worktrees")
    if block is None:
        return WorktreeGuardConfig(root_write_policy, unmanaged_write_policy, namespaces)

    in_namespaces = False
    for raw in block.splitlines()[1:]:
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key_match = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", line)
        if not key_match:
            continue
        key = key_match.group(1)
        value = key_match.group(2).strip().strip("'\"")
        if indent == 2 and key == "namespaces":
            in_namespaces = True
            continue
        if indent == 2 and key in {"root_write_policy", "unmanaged_write_policy"}:
            in_namespaces = False
            if key == "root_write_policy" and value:
                root_write_policy = value
            elif key == "unmanaged_write_policy" and value:
                unmanaged_write_policy = value
            continue
        if indent >= 4 and in_namespaces and value:
            namespaces[key.lower()] = value.replace("\\", "/").strip("/")
    return WorktreeGuardConfig(root_write_policy, unmanaged_write_policy, namespaces)


def worktree_guard(
    cwd: str | Path = ".",
    *,
    agent_type: str | None = None,
    write_intent: bool = False,
    allow_root_write: bool = False,
) -> WorktreeGuardStatus:
    """Classify whether the current Git worktree belongs to the calling agent.

    This is deliberately read-only. It never creates, moves, deletes, or switches
    worktrees; callers use the structured result to decide whether writing is
    appropriate.
    """
    root = Path(cwd).resolve()
    code, top = _git_text(root, ("rev-parse", "--show-toplevel"))
    normalized_agent = agent_type.strip().lower() if agent_type else None
    config = _worktree_guard_config_for(resolve_runtime(root).workspace_root)
    expected_namespace = config.namespaces.get(normalized_agent or "") if normalized_agent else None
    if code != 0 or not top:
        ok = not write_intent
        return WorktreeGuardStatus(
            ok=ok,
            severity="block" if write_intent else "warning",
            agent_type=normalized_agent,
            classification="not-a-worktree",
            safe_to_write=False,
            write_intent=write_intent,
            current_branch=None,
            head=None,
            dirty=None,
            worktree_path=None,
            repo_root=None,
            expected_namespace=expected_namespace,
            actual_namespace_owner=None,
            root_write_policy=config.root_write_policy,
            unmanaged_write_policy=config.unmanaged_write_policy,
            recommended_next_action=(
                "Move into the repository worktree assigned to this agent before editing."
                if write_intent
                else "Git worktree posture is unavailable from this path."
            ),
            warnings=("Current path is not inside a Git worktree.",),
        )

    worktree_path = Path(top).resolve()
    code, worktree_out = _git_text(worktree_path, ("worktree", "list", "--porcelain"))
    worktrees = _parse_worktree_list(worktree_out) if code == 0 else []
    repo_root = Path(worktrees[0]["path"]).resolve() if worktrees else worktree_path
    _, branch = _git_text(worktree_path, ("branch", "--show-current"))
    _, head = _git_text(worktree_path, ("rev-parse", "HEAD"))
    _, status_out = _git_text(worktree_path, ("status", "--short"))
    dirty = bool(status_out.strip())

    actual_owner = _namespace_owner(repo_root, worktree_path, config.namespaces)
    if _casefold_parts(worktree_path) == _casefold_parts(repo_root):
        classification = "root-checkout"
    elif actual_owner and (normalized_agent is None or actual_owner == normalized_agent):
        classification = "owned-worktree"
    elif actual_owner:
        classification = "foreign-worktree"
    else:
        classification = "unmanaged-worktree"

    warnings: list[str] = []
    safe_to_write = True
    severity = "ok"
    if classification == "owned-worktree":
        recommendation = "Current worktree matches the agent namespace; writing is allowed."
    elif classification == "foreign-worktree":
        safe_to_write = False
        severity = "block"
        warnings.append(
            f"Current worktree belongs to '{actual_owner}', not '{normalized_agent or 'unknown'}'."
        )
        recommendation = f"Move to {expected_namespace or 'the configured namespace'} for this agent before editing."
    elif classification == "root-checkout":
        if write_intent and not allow_root_write:
            safe_to_write = False
            severity = "block"
            warnings.append("Root checkout write intent requires --allow-root-write.")
            recommendation = "Use an agent-owned task worktree, or rerun with --allow-root-write for approved root cleanup."
        else:
            severity = "warning" if write_intent else "ok"
            recommendation = (
                "Root checkout is acceptable for read-only inspection and explicit integration work."
                if not write_intent
                else "Root write override was provided; keep this to approved integration or cleanup work."
            )
    elif classification == "unmanaged-worktree":
        policy = config.unmanaged_write_policy.lower()
        if write_intent and policy == "block":
            safe_to_write = False
            severity = "block"
            recommendation = f"Move this task into {expected_namespace or 'a configured agent namespace'} before editing."
        else:
            severity = "warning"
            recommendation = (
                f"Unmanaged worktree; expected namespace is {expected_namespace or 'not configured for this agent'}."
            )
        warnings.append("Current Git worktree is outside every configured agent namespace.")
    else:
        safe_to_write = False
        severity = "block"
        recommendation = "Move into a configured worktree before editing."

    ok = safe_to_write if write_intent else severity != "block"
    return WorktreeGuardStatus(
        ok=ok,
        severity=severity,
        agent_type=normalized_agent,
        classification=classification,
        safe_to_write=safe_to_write,
        write_intent=write_intent,
        current_branch=branch or None,
        head=head or None,
        dirty=dirty,
        worktree_path=worktree_path.as_posix(),
        repo_root=repo_root.as_posix(),
        expected_namespace=expected_namespace,
        actual_namespace_owner=actual_owner,
        root_write_policy=config.root_write_policy,
        unmanaged_write_policy=config.unmanaged_write_policy,
        recommended_next_action=recommendation,
        warnings=tuple(warnings),
    )


# --- Entry DRAFT-body format lint (deterministic, shared by session append +
# links check). Purely STRUCTURAL: it never judges whether a turn should be one
# decision or several (that is authoring judgement) - only that the chosen shape
# is well formed. High precision (6/348 real-corpus entries flag), so it is safe
# to gate a write on. See session_logging.md for the authored templates.
# THE entry-boundary grammar - defined once, used by append, integrity/format
# checks, reorder, and the branch-fuse flows alike. An entry heading is a
# timestamped `## YYYY-MM-DD HH:MM - title` line and nothing else: a plain `##`
# heading inside an entry body is body content, not a boundary. (This module
# once carried a second, broader `^##` definition of the same name further
# down; the two grammars disagreed, so `session append` accepted a body that
# `session merge-branch` then split into a phantom ID-less entry.)
_ENTRY_HEADING_RE = re.compile(
    r"^##\s+\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s+-\s*.*$", re.MULTILINE
)
_BARE_DRAFT_RE = re.compile(r"^(D|R|A|F|T)\d*\s*:")         # column-0 label with no '- '
_BULLET_DRAFT_RE = re.compile(r"^-\s+(D|R|A|F|T)\d*\s*:")   # '- D:' list item
_INLINE_NUMBERED_DECISION_RE = re.compile(r"^-\s+D\d+\s*:")  # '- D1:' inline (should be '#### Dn')
_ENTRY_SECTION_RE = re.compile(r"^#{2,4}\s+(Summary|Decision|Decisions|Implementation|Validation|Follow-up)", re.I)
_SINGULAR_DECISION_HEADING_RE = re.compile(r"^###\s+Decision\s*$")
_NUMBERED_DECISION_HEADING_RE = re.compile(r"^####\s+D\d+\s*[-–]")  # '#### D1 - name'
# Indent-aware: a nested '  - R:' under a '- D1:' is still a reason present.
_ANY_D_LABEL_RE = re.compile(r"^\s*-?\s*D\d*\s*:")
_ANY_R_LABEL_RE = re.compile(r"^\s*-?\s*R\d*\s*:")


def entry_body_format_issues(body: str) -> list[str]:
    """Return DRAFT-format problems in one entry BODY (text after the ```yaml
    block), or [] when well formed. Flags: bare ``D:``/``R:`` labels that are not
    ``- `` list items; DRAFT prose with no ``### Decision``/``### Summary``
    heading; multiple decisions crammed under a singular ``### Decision`` via
    inline ``- Dn:`` (should be ``### Decisions`` + ``#### Dn - name``); and a
    decision (``D:``) with no reason (``R:`` is mandatory). Entries with no DRAFT
    labels at all (e.g. a plain ``### Summary`` note) are never flagged - the lint
    only rejects malformed DRAFT usage, it does not force DRAFT on every entry."""
    lines = body.splitlines()
    issues: list[str] = []
    bare = [ln for ln in lines if _BARE_DRAFT_RE.match(ln)]
    bulleted = [ln for ln in lines if _BULLET_DRAFT_RE.match(ln)]
    inline_numbered = any(_INLINE_NUMBERED_DECISION_RE.match(ln) for ln in lines)
    has_section = any(_ENTRY_SECTION_RE.match(ln) for ln in lines)
    singular_decision = any(_SINGULAR_DECISION_HEADING_RE.match(ln) for ln in lines)
    if bare:
        labels = ", ".join(sorted({ln.split(":", 1)[0].strip() for ln in bare}))
        issues.append(f"DRAFT labels ({labels}) are not list items - prefix each with '- ' under a section heading")
    if bare and not has_section:
        issues.append("DRAFT prose has no '### Decision'/'### Decisions'/'### Summary' section heading")
    # Only the singular-heading case is a genuine error: a lone '### Decision'
    # holding several inline '- Dn:' bullets conflates decisions and drops the
    # per-decision structure. A well-formed '### Decisions' block with '- D1:' +
    # nested '- R:' renders fine and is left alone (avoid condemning a readable
    # historical style over pedantic '#### Dn' conformance).
    if inline_numbered and singular_decision:
        issues.append("multiple decisions under a singular '### Decision' - use '### Decisions' + '#### Dn - name' subsections")
    if (bare or bulleted) and any(_ANY_D_LABEL_RE.match(ln) for ln in lines) and not any(_ANY_R_LABEL_RE.match(ln) for ln in lines):
        issues.append("a decision (D:) has no reason (R:) - R is mandatory")
    return issues


def _walk_entry_bodies(
    text: str, inspect: Callable[[str], list[str]]
) -> list[tuple[str, str]]:
    """Apply ``inspect`` to every entry body in a session file's ``text``,
    returning ``(entry_id, finding)`` pairs. Shared by the format check and its
    advisory twin so both see exactly the same body boundaries."""
    lines = text.splitlines()
    heads = [i for i, ln in enumerate(lines) if _ENTRY_HEADING_RE.match(ln)]
    out: list[tuple[str, str]] = []
    for k, start in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        block = lines[start:end]
        entry_id = next(
            (m.group(1) for ln in block if (m := re.match(r"\s*entry_id:\s*(\S+)", ln))),
            "?",
        )
        fences = [i for i, ln in enumerate(block) if ln.strip() == "```"]
        body = "\n".join(block[fences[1] + 1:] if len(fences) >= 2 else block[1:])
        for finding in inspect(body):
            out.append((entry_id, finding))
    return out


# A decision count at or above this is a *smell*, not an error: the corpus norm
# is ~1.0-1.5 decisions per entry across both agents and every recent day, so an
# entry carrying three or more usually means several milestones were batched at
# merge time instead of appended as they happened.
DECISION_DENSITY_ADVISORY_THRESHOLD = 3


def entry_body_decision_count(body: str) -> int:
    """Count the durable decisions an entry body records.

    Counts ``#### Dn - name`` subsections (the multi-decision shape) and falls
    back to ``- D:`` / ``- Dn:`` bullets, so both the current and the older
    readable styles are measured the same way.
    """
    lines = body.splitlines()
    numbered = [ln for ln in lines if _NUMBERED_DECISION_HEADING_RE.match(ln)]
    if numbered:
        return len(numbered)
    return len([ln for ln in lines if _ANY_D_LABEL_RE.match(ln)])


def entry_body_advisories(body: str) -> list[str]:
    """Return non-blocking *advisories* about one entry body.

    Deliberately separate from ``entry_body_format_issues``: that function is a
    write-time gate — ``session append`` refuses a body it rejects — and these
    are judgement calls that must never block a write or fail a check. An entry
    can be perfectly well formed and still be worth splitting.
    """
    advisories: list[str] = []
    count = entry_body_decision_count(body)
    if count >= DECISION_DENSITY_ADVISORY_THRESHOLD:
        advisories.append(
            f"{count} decisions in one entry - if they were made at different times "
            "(work happened between them), append each at its milestone instead of "
            "batching them at merge; see session_logging.md 'When to append'"
        )
    return advisories


def check_entry_advisories(text: str) -> list[tuple[str, str]]:
    """``check_entry_format``'s advisory twin: (entry_id, advisory) pairs over a
    session file's text. Reported as warnings, never errors."""
    return _walk_entry_bodies(text, entry_body_advisories)


def check_entry_format(text: str) -> list[tuple[str, str]]:
    """Run ``entry_body_format_issues`` over every entry in a session-file's
    ``text``, returning ``(entry_id, issue)`` pairs. Shared by ``links check``
    (audit over the corpus) and available for any surface that has raw text; the
    write-time gate in ``session append`` calls ``entry_body_format_issues`` on
    the single body it is about to write."""
    return _walk_entry_bodies(text, entry_body_format_issues)


def check_session_links(cwd: str | Path = ".") -> LinksCheckResult:
    """Validate session-memory integrity across both legacy-flat and per-user
    layouts (multi-user Phase 3). Detects duplicate entry/file IDs, dangling
    ``related_entries``/``related_memories``/``supersedes`` references,
    supersession forward-only violations (a ``supersedes`` ref whose target
    postdates the referencing entry, including self-references and cycles),
    malformed or unknown ``commits:`` hashes (existence checked only when a
    ``.git`` directory is present and git responds), per-user-file
    frontmatter problems (filename/frontmatter user or date mismatch, missing
    or malformed ``hash_id``, unsupported ``schema_version``, invalid user
    slug), and decision-diagram sidecar problems under
    ``sessions/diagrams/YYYY-MM-DD.md`` and
    ``sessions/diagrams/YYYY-MM/YYYY-MM-DD.md`` (``orphan-diagram``,
    ``diagram-date-mismatch``, ``malformed-diagram``; sidecars are always
    optional). Lifecycle-edge link sidecars under ``sessions/links/…`` are
    validated the same way (``orphan-link-sidecar``,
    ``link-sidecar-date-mismatch``, ``malformed-link-sidecar``), and their
    ``supersedes``/``evolves``/``related_entries`` edges join the entry-YAML
    edges in the dangling and forward-only checks. An unresolved
    ``classify_pending: true`` link block emits the non-blocking
    ``sidecar-unclassified-stub`` warning.

    Each issue names the source file and the offending value. Warnings,
    including ``sidecar-unclassified-stub``, remain in ``issues`` but do not
    make ``ok=False``; only error-severity issues fail the CLI gate.
    """
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    sessions_dir = runtime.memory_dir / "sessions"

    issues: list[LinkIssue] = []
    entry_id_files: dict[str, list[str]] = {}
    hash_id_files: dict[str, list[str]] = {}
    related_entry_refs: list[tuple[str, str]] = []
    related_memory_refs: list[tuple[str, str]] = []
    supersedes_refs: list[tuple[str, str]] = []
    evolves_refs: list[tuple[str, str]] = []
    commit_refs: list[tuple[str, str]] = []
    # (rel_path, source_entry_id, ref) for refs attributable to a source entry.
    supersedes_edges: list[tuple[str, str, str]] = []
    evolves_edges: list[tuple[str, str, str]] = []
    entry_timestamps: dict[str, str] = {}
    files_checked = 0

    for doc in iter_session_documents(sessions_dir):
        files_checked += 1
        try:
            rel = doc.path.relative_to(root).as_posix()
        except ValueError:
            rel = doc.path.as_posix()
        try:
            text = doc.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(LinkIssue(rel, "unreadable", str(exc)))
            continue

        for entry_id in _ENTRY_ID_RE.findall(text):
            entry_id_files.setdefault(entry_id, []).append(rel)

        # DRAFT-body format lint: a malformed decision record (bare labels, no
        # section heading, wrong multi-decision shape, D: without R:) is an
        # integrity error so it surfaces in `esr` and blocks a bad commit once CI
        # runs links check. Structural only; see entry_body_format_issues.
        for entry_id, issue in check_entry_format(text):
            issues.append(LinkIssue(rel, "malformed-entry-format", f"{entry_id}: {issue}"))

        # Advisory, never an error: a well-formed entry can still be worth
        # splitting. Batching milestones is a judgement call, so this prompts
        # and never blocks a commit.
        for entry_id, advisory in check_entry_advisories(text):
            issues.append(
                LinkIssue(rel, "entry-decision-density", f"{entry_id}: {advisory}", "warning")
            )

        # Entry-level related_entries/supersedes live inside each entry's fenced
        # ```yaml block, the same shape in both layouts - scan them regardless
        # of layout, unlike the per-user *file*-frontmatter checks below.
        # Refs extract with the wider _TRAILER_ENTRY_ID_RE, not the strict
        # Crockford _RELATED_ENTRY_REF_RE: real corpus ids include o/u/i/l
        # (codex-authored entries), and a ref the extractor skips silently
        # bypasses the dangling and forward-only guards while the graph still
        # draws it. known_entries accepts any id shape (_ENTRY_ID_RE), so a
        # wider-matched bad token surfaces as dangling instead of vanishing.
        for yaml_block in _fenced_yaml_blocks(text):
            for ref in _TRAILER_ENTRY_ID_RE.findall(_frontmatter_list_region(yaml_block, "related_entries")):
                related_entry_refs.append((rel, ref))
            for ref in _TRAILER_ENTRY_ID_RE.findall(_frontmatter_list_region(yaml_block, "supersedes")):
                supersedes_refs.append((rel, ref))
            for ref in _TRAILER_ENTRY_ID_RE.findall(_frontmatter_list_region(yaml_block, "evolves")):
                evolves_refs.append((rel, ref))
            for token in _COMMIT_TOKEN_RE.findall(_frontmatter_list_region(yaml_block, "commits")):
                commit_refs.append((rel, token))
            # Append-only enforcement: the computed inverses exist only in the
            # derived read layer and must never be written into stored YAML.
            inverse_match = _AUTHORED_INVERSE_RE.search(yaml_block)
            if inverse_match:
                issues.append(
                    LinkIssue(
                        rel,
                        "authored-inverse-field",
                        f"stored '{inverse_match.group(1)}:' key found; the inverse is read-time only "
                        "and must never be written into an entry",
                    )
                )
            # Structural continuity validation (artifact lineage, D6): kind is
            # closed-vocabulary, from is required, to is required for
            # rename/migration and forbidden for removal.
            continuity_region = _frontmatter_list_region(yaml_block, "continuity")
            if continuity_region.strip():
                for item in _parse_continuity_items(continuity_region):
                    kind = item.get("kind", "")
                    from_value = item.get("from", "")
                    to_value = item.get("to", "")
                    if kind not in _CONTINUITY_KINDS:
                        issues.append(
                            LinkIssue(
                                rel,
                                "malformed-continuity",
                                f"continuity kind '{kind or '(missing)'}' is not rename|migration|removal",
                            )
                        )
                        continue
                    if not from_value:
                        issues.append(
                            LinkIssue(rel, "malformed-continuity", f"continuity {kind} item has no from")
                        )
                        continue
                    if kind == "removal" and to_value:
                        issues.append(
                            LinkIssue(
                                rel,
                                "malformed-continuity",
                                f"continuity removal '{from_value}' must not have to "
                                "(a removal with a successor is a rename or a supersession)",
                            )
                        )
                    elif kind != "removal" and not to_value:
                        issues.append(
                            LinkIssue(rel, "malformed-continuity", f"continuity {kind} '{from_value}' has no to")
                        )

        # Second, heading-anchored pass: attribute each supersedes/evolves ref
        # to its source entry and heading timestamp for the forward-only guard.
        for heading_ts, yaml_block in _ENTRY_TS_YAML_RE.findall(text):
            id_match = _ENTRY_ID_RE.search(yaml_block)
            source_id = id_match.group(1) if id_match else None
            if source_id:
                entry_timestamps.setdefault(source_id, heading_ts)
            for ref in _TRAILER_ENTRY_ID_RE.findall(_frontmatter_list_region(yaml_block, "supersedes")):
                if source_id:
                    supersedes_edges.append((rel, source_id, ref))
            for ref in _TRAILER_ENTRY_ID_RE.findall(_frontmatter_list_region(yaml_block, "evolves")):
                if source_id:
                    evolves_edges.append((rel, source_id, ref))

        if doc.layout not in {"per-user-day", "month-user"}:
            continue

        if doc.user is not None and (
            not SESSION_USER_SLUG_RE.match(doc.user) or doc.user in _RESERVED_SESSION_STEMS
        ):
            issues.append(LinkIssue(rel, "invalid-user-slug", f"filename slug '{doc.user}'"))

        match = _FILE_FRONTMATTER_RE.match(text)
        if not match:
            issues.append(
                LinkIssue(rel, "missing-frontmatter", "per-user file has no leading --- frontmatter block")
            )
            continue
        block = match.group(1)
        scalars = _parse_frontmatter_scalars(block)

        fm_user = scalars.get("user")
        if fm_user is not None and fm_user != doc.user:
            issues.append(LinkIssue(rel, "user-mismatch", f"frontmatter user '{fm_user}' != filename user '{doc.user}'"))
        fm_date = scalars.get("session_date")
        if fm_date is not None and fm_date != doc.session_date:
            issues.append(LinkIssue(rel, "date-mismatch", f"frontmatter session_date '{fm_date}' != directory date '{doc.session_date}'"))
        schema_version = scalars.get("schema_version")
        if schema_version is not None and schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
            issues.append(LinkIssue(rel, "unsupported-schema-version", f"schema_version '{schema_version}'"))
        hash_id = scalars.get("hash_id")
        if not hash_id:
            issues.append(LinkIssue(rel, "missing-hash-id", "per-user file frontmatter has no hash_id"))
        else:
            if not hash_id.startswith("msm_"):
                issues.append(LinkIssue(rel, "malformed-hash-id", f"hash_id '{hash_id}' lacks the msm_ prefix"))
            hash_id_files.setdefault(hash_id, []).append(rel)

        for ref in _TRAILER_ENTRY_ID_RE.findall(_frontmatter_list_region(block, "related_entries")):
            related_entry_refs.append((rel, ref))
        for ref in _RELATED_MEMORY_REF_RE.findall(_frontmatter_list_region(block, "related_memories")):
            related_memory_refs.append((rel, ref))

    for entry_id, files in sorted(entry_id_files.items()):
        if len(files) > 1:
            where = ", ".join(sorted(set(files)))
            issues.append(LinkIssue(files[0], "duplicate-entry-id", f"entry_id {entry_id} appears {len(files)}x ({where})"))
    for hash_id, files in sorted(hash_id_files.items()):
        if len(set(files)) > 1:
            issues.append(LinkIssue(sorted(files)[0], "duplicate-hash-id", f"hash_id {hash_id} in {', '.join(sorted(set(files)))}"))

    known_entries = set(entry_id_files)
    known_hashes = set(hash_id_files)

    # Decision-diagram sidecars: old flat and new month-grouped sidecar files.
    # Optional throughout - an entry without a sidecar is never an issue.
    for diagram_doc in iter_diagram_sidecar_documents(sessions_dir):
        files_checked += 1
        diagram_path = diagram_doc.path
        try:
            rel = diagram_path.relative_to(root).as_posix()
        except ValueError:
            rel = diagram_path.as_posix()
        if diagram_doc.malformed_reason:
            issues.append(LinkIssue(rel, "malformed-diagram", diagram_doc.malformed_reason))
            continue
        file_date = diagram_doc.diagram_date or ""
        try:
            text = diagram_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(LinkIssue(rel, "unreadable", str(exc)))
            continue
        blocks = list(_ENTRY_TS_YAML_RE.finditer(text))
        if not blocks:
            issues.append(
                LinkIssue(rel, "malformed-diagram", "no '## <timestamp> - <title>' + ```yaml entry_id block found")
            )
            continue
        for index, block in enumerate(blocks):
            heading_ts, yaml_block = block.groups()
            entry_id_match = _ENTRY_ID_RE.search(yaml_block)
            if not entry_id_match:
                issues.append(LinkIssue(rel, "malformed-diagram", f"diagram block at '{heading_ts}' has no entry_id"))
                continue
            entry_id = entry_id_match.group(1)
            if entry_id not in known_entries:
                issues.append(LinkIssue(rel, "orphan-diagram", f"entry_id -> {entry_id} (no such entry_id)"))
            entry_date = entry_timestamps.get(entry_id, "")[:10]
            if entry_date and entry_date != file_date:
                issues.append(
                    LinkIssue(
                        rel,
                        "diagram-date-mismatch",
                        f"entry_id {entry_id} was logged on {entry_date}, but diagram is filed under {file_date}",
                    )
                )
            section_end = blocks[index + 1].start() if index + 1 < len(blocks) else len(text)
            section_text = text[block.end():section_end]
            fence_lines = [line.strip() for line in section_text.splitlines() if line.strip().startswith("```")]
            mermaid_opens = sum(1 for line in fence_lines if line.startswith("```mermaid"))
            if mermaid_opens == 0:
                issues.append(LinkIssue(rel, "malformed-diagram", f"diagram block for {entry_id} has no ```mermaid block"))
            elif len(fence_lines) % 2 != 0:
                issues.append(LinkIssue(rel, "malformed-diagram", f"diagram block for {entry_id} has an unbalanced code fence"))

    # Lifecycle-edge link sidecars (sessions/links/...): supersedes/evolves/
    # related edges authored after an entry, keyed to the SOURCE (newer) entry.
    # Optional throughout. Edges fold into the SAME dangling + forward-only
    # checks as entry-YAML edges, attributed to the source ENTRY's heading
    # timestamp (not the sidecar's authoring time), so "B supersedes A" is legal
    # iff A predates B no matter when the sidecar was written. Dangling checks
    # run inline here because the supersedes/evolves dangling passes above have
    # already executed; the forward-only guard runs last and sees these edges.
    for link_doc in iter_link_sidecar_documents(sessions_dir):
        files_checked += 1
        link_path = link_doc.path
        try:
            rel = link_path.relative_to(root).as_posix()
        except ValueError:
            rel = link_path.as_posix()
        if link_doc.malformed_reason:
            issues.append(LinkIssue(rel, "malformed-link-sidecar", link_doc.malformed_reason))
            continue
        file_date = link_doc.link_date or ""
        try:
            text = link_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(LinkIssue(rel, "unreadable", str(exc)))
            continue
        blocks = list(_ENTRY_TS_YAML_RE.finditer(text))
        if not blocks:
            issues.append(
                LinkIssue(rel, "malformed-link-sidecar", "no '## <timestamp> - <title>' + ```yaml entry_id block found")
            )
            continue
        for block in blocks:
            heading_ts, yaml_block = block.groups()
            entry_id_match = _ENTRY_ID_RE.search(yaml_block)
            if not entry_id_match:
                issues.append(LinkIssue(rel, "malformed-link-sidecar", f"link block at '{heading_ts}' has no entry_id"))
                continue
            entry_id = entry_id_match.group(1)
            scalars = _parse_frontmatter_scalars(yaml_block)
            if scalars.get("classify_pending", "").lower() == "true":
                issues.append(
                    LinkIssue(
                        rel,
                        "sidecar-unclassified-stub",
                        f"entry_id {entry_id} still requires lifecycle classification",
                        severity="warning",
                    )
                )
            if entry_id not in known_entries:
                issues.append(LinkIssue(rel, "orphan-link-sidecar", f"entry_id -> {entry_id} (no such entry_id)"))
            entry_date = entry_timestamps.get(entry_id, "")[:10]
            if entry_date and entry_date != file_date:
                issues.append(
                    LinkIssue(
                        rel,
                        "link-sidecar-date-mismatch",
                        f"entry_id {entry_id} was logged on {entry_date}, but link sidecar is filed under {file_date}",
                    )
                )
            # Wider _TRAILER_ENTRY_ID_RE, matching the sidecar reader: real
            # corpus ids include non-Crockford letters (o/u/i/l) the strict
            # ref regex would silently skip - here a bad ref must surface as
            # dangling, never vanish.
            for kind, edge_list in (("supersedes", supersedes_edges), ("evolves", evolves_edges)):
                for ref in _TRAILER_ENTRY_ID_RE.findall(_frontmatter_list_region(yaml_block, kind)):
                    if ref not in known_entries:
                        issues.append(LinkIssue(rel, f"dangling-{kind}", f"{kind} -> {ref} (no such entry_id)"))
                    else:
                        edge_list.append((rel, entry_id, ref))
            for ref in _TRAILER_ENTRY_ID_RE.findall(_frontmatter_list_region(yaml_block, "related_entries")):
                if ref not in known_entries:
                    issues.append(LinkIssue(rel, "dangling-related-entry", f"related_entries -> {ref} (no such entry_id)"))

    for rel, ref in related_entry_refs:
        if ref not in known_entries:
            issues.append(LinkIssue(rel, "dangling-related-entry", f"related_entries -> {ref} (no such entry_id)"))
    for rel, ref in related_memory_refs:
        if ref not in known_hashes:
            issues.append(LinkIssue(rel, "dangling-related-memory", f"related_memories -> {ref} (no such hash_id)"))
    for rel, ref in supersedes_refs:
        if ref not in known_entries:
            issues.append(LinkIssue(rel, "dangling-supersedes", f"supersedes -> {ref} (no such entry_id)"))
    for rel, ref in evolves_refs:
        if ref not in known_entries:
            issues.append(LinkIssue(rel, "dangling-evolves", f"evolves -> {ref} (no such entry_id)"))

    # commits: entries store full 40-character SHAs (validation stays
    # unambiguous; display may shorten). Existence is checked only when a .git
    # directory is present at the runtime root AND git itself answers - the
    # package works outside git repos, so absence skips, never fails.
    if commit_refs:
        git_present = (root / ".git").exists()
        # A shallow clone (CI checkouts default to depth 1) genuinely lacks
        # historical commits, so "no such commit" cannot be distinguished from
        # "outside the fetched window". Absence of evidence is not evidence of
        # absence there - skip unknown-commit validation rather than raise
        # false integrity errors. Malformed-hash checks still run.
        if git_present:
            code, shallow = _git_text(root, ("rev-parse", "--is-shallow-repository"))
            if code == 0 and shallow.strip() == "true":
                git_present = False
        commit_known: dict[str, bool | None] = {}
        for rel_path, token in commit_refs:
            if not _FULL_COMMIT_SHA_RE.match(token):
                issues.append(
                    LinkIssue(rel_path, "malformed-commit-hash", f"commits -> {token} (full 40-character lowercase SHA required)")
                )
                continue
            if not git_present:
                continue
            if token not in commit_known:
                commit_known[token] = _commit_exists(root, token)
            if commit_known[token] is False:
                issues.append(LinkIssue(rel_path, "unknown-commit", f"commits -> {token} (no such commit in this repository)"))

    # Forward-only guard: supersedes/evolves may only point at entries that
    # already existed when the referencing entry was written. Acyclicity of
    # each lifecycle graph depends on this holding, so violations are errors,
    # not warnings. Refs without a resolvable source or target timestamp fall
    # through to the dangling check above rather than failing here. The two
    # edge kinds are guarded independently - an evolves + supersedes pair
    # between the same two entries is legal, and cycles are checked within
    # each kind, never across kinds.
    def _forward_only_guard(
        edges: list[tuple[str, str, str]],
        field: str,
        self_message: str,
        cycle_noun: str,
    ) -> None:
        adjacency: dict[str, set[str]] = {}
        edge_file: dict[str, str] = {}
        for rel_path, source_id, ref in edges:
            edge_file.setdefault(source_id, rel_path)
            if ref == source_id:
                issues.append(LinkIssue(rel_path, f"self-{field}", f"{field} -> {ref} ({self_message})"))
                continue
            source_ts = entry_timestamps.get(source_id)
            target_ts = entry_timestamps.get(ref)
            if source_ts and target_ts and target_ts > source_ts:
                issues.append(
                    LinkIssue(
                        rel_path,
                        f"{field}-postdates",
                        f"{field} -> {ref} ({target_ts}) postdates the referencing entry {source_id} ({source_ts})",
                    )
                )
            if ref in known_entries:
                adjacency.setdefault(source_id, set()).add(ref)

        # Cycle guard: the postdates check leaves same-minute entries
        # unordered, so a cycle is still constructible there; a DFS closes
        # that residual hole.
        state: dict[str, int] = {}  # absent=unvisited, 1=in-stack, 2=done
        for start in sorted(adjacency):
            if state.get(start):
                continue
            stack: list[tuple[str, Iterator[str]]] = [(start, iter(sorted(adjacency.get(start, ()))))]
            state[start] = 1
            path = [start]
            while stack:
                node, neighbours = stack[-1]
                advanced = False
                for neighbour in neighbours:
                    if state.get(neighbour) == 1:
                        cycle = " -> ".join(path[path.index(neighbour):] + [neighbour])
                        issues.append(
                            LinkIssue(edge_file.get(neighbour, ""), f"{field}-cycle", f"{cycle_noun} cycle: {cycle}")
                        )
                        continue
                    if state.get(neighbour) == 2:
                        continue
                    state[neighbour] = 1
                    path.append(neighbour)
                    stack.append((neighbour, iter(sorted(adjacency.get(neighbour, ())))))
                    advanced = True
                    break
                if not advanced:
                    state[node] = 2
                    path.pop()
                    stack.pop()

    _forward_only_guard(supersedes_edges, "supersedes", "entry supersedes itself", "supersession")
    _forward_only_guard(evolves_edges, "evolves", "entry evolves itself", "evolution")

    return LinksCheckResult(
        ok=not any(issue.severity == "error" for issue in issues),
        files_checked=files_checked,
        issues=issues,
    )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_per_user_session_file(path: Path, date_str: str, user: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    hash_id = "msm_" + secrets.token_hex(16)
    write_text_file(
        path,
        "\n".join(
            [
                "---",
                "schema_version: 2",
                f"session_date: {date_str}",
                f"hash_id: {hash_id}",
                f"user: {user}",
                f"created_at: {_utc_timestamp()}",
                "---",
                "",
            ]
        ),
    )


def session_target(
    cwd: Path | str = ".",
    date_str: str | None = None,
    explicit_user: str | None = None,
    create: bool = False,
) -> SessionTarget:
    runtime = resolve_runtime(cwd)
    if runtime.legacy:
        sessions_dir = runtime.memory_dir / "sessions"
    else:
        sessions_dir = runtime.workspace_root / MEMORY_DIR_NAME / "sessions"
    date_value = date_str or datetime.now().strftime("%Y-%m-%d")
    if not _valid_session_date(date_value):
        raise ValueError(f"Invalid session date: {date_value}")

    user = resolve_active_user(cwd, explicit_user=explicit_user)
    if user is not None and explicit_user is None:
        # A configured user alone isn't enough to fragment the log: per-user
        # files exist to avoid concurrent-author merge conflicts, which isn't a
        # concern until there is a second participant to conflict with. An
        # explicit --user override bypasses this (a deliberate one-shot choice,
        # e.g. testing migration by hand).
        if len(read_project_participants(runtime.workspace_root)) < 2:
            user = None
    if user is None:
        path = _session_flat_path(sessions_dir, date_value)
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
        return SessionTarget(path=path, session_date=date_value, user=None, layout="month-flat")

    path = session_path(sessions_dir, date_value, user)
    if create:
        _ensure_per_user_session_file(path, date_value, user)
    return SessionTarget(path=path, session_date=date_value, user=user, layout="month-user")


_USER_INITIALS_RE = re.compile(r"^user_initials:\s*(\S+)\s*$", re.MULTILINE)
_REORDER_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+-\s*(.*)$")
_APPEND_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def _known_entry_ids_and_timestamps(sessions_dir: Path) -> tuple[set[str], dict[str, str]]:
    """All entry ids in the corpus, plus id -> heading timestamp where the
    entry block is heading-anchored (refs to un-anchored ids skip the
    forward-only check, matching links check)."""
    known: set[str] = set()
    timestamps: dict[str, str] = {}
    for doc in iter_session_documents(sessions_dir):
        try:
            text = read_text_file(doc.path)
        except (OSError, UnicodeDecodeError):
            continue
        known.update(_ENTRY_ID_RE.findall(text))
        for heading_ts, yaml_block in _ENTRY_TS_YAML_RE.findall(text):
            id_match = _ENTRY_ID_RE.search(yaml_block)
            if id_match:
                timestamps.setdefault(id_match.group(1), heading_ts)
    return known, timestamps


@dataclass(frozen=True)
class SessionAppendResult:
    ok: bool
    path: Path | None = None
    entry_id: str | None = None
    timestamp: str | None = None
    issues: tuple[str, ...] = ()
    written: bool = False


def session_append_entry(
    cwd: Path | str = ".",
    *,
    title: str,
    body: str,
    user_initials: str,
    agent_type: str,
    agent_name: str | None = None,
    topics: Sequence[str] = (),
    related_entries: Sequence[str] = (),
    supersedes: Sequence[str] = (),
    evolves: Sequence[str] = (),
    project_path: str = ".",
    subproject_path: str | None = None,
    branch: str | None = None,
    auto_branch: bool = True,
    timestamp: str | None = None,
    explicit_user: str | None = None,
) -> SessionAppendResult:
    """Append a session entry with every structural guarantee enforced.

    The tool owns structure, the agent owns voice: target resolution, heading
    timestamp, canonical entry id, YAML shape, ref/topic validation, and
    chronological append are handled here; ``title``, ``topics``, lifecycle
    classification, and the D/R/A/F/T ``body`` prose arrive verbatim and are
    never reworded.

    Guards (all reported together; nothing is written when any fails):
    - timestamp defaults to now and must not sort before the file's last
      entry - when the previous heading claims a FUTURE time relative to the
      clock, this errors loudly rather than silently propagating drift; the
      agent fixes it consciously (``--timestamp`` or ``session reorder``).
    - every ``related_entries``/``supersedes``/``evolves`` ref must exist
      (kills fabricated ids) and must not postdate this entry (forward-only,
      same rule links check enforces after the fact).
    - topics must resolve in the controlled vocabulary; aliases are stored as
      their canonical slug.
    - the generated id colliding with an existing one means identical
      metadata - almost certainly a double-append - and errors.
    - ``branch`` is captured from git automatically unless supplied or
      ``auto_branch=False`` (omitted when detached or not a repository).
    """
    issues: list[str] = []
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    if not _APPEND_TS_RE.match(ts):
        return SessionAppendResult(ok=False, issues=(f"invalid timestamp '{ts}' (expected 'YYYY-MM-DD HH:MM')",))
    date_part = ts[:10]
    if not _valid_session_date(date_part):
        return SessionAppendResult(ok=False, issues=(f"invalid session date '{date_part}'",))

    target = session_target(cwd, date_str=date_part, explicit_user=explicit_user, create=False)
    runtime = resolve_runtime(cwd)
    sessions_dir = runtime.memory_dir / "sessions"

    if target.path.exists():
        text = read_text_file(target.path)
        heading_times = [
            match.group(1)
            for match in (_REORDER_HEADING_RE.match(m.group(0)) for m in _ENTRY_HEADING_RE.finditer(text))
            if match
        ]
        if heading_times and heading_times[-1] > ts:
            issues.append(
                f"chronology conflict: the file's last entry claims {heading_times[-1]} but this entry "
                f"would be stamped {ts}. Fix consciously: pass --timestamp, correct the clock drift at "
                "its source, or repair prior order with 'session reorder'. Refusing to append out of order."
            )

    known, entry_ts = _known_entry_ids_and_timestamps(sessions_dir)
    for kind, refs in (("related_entries", related_entries), ("supersedes", supersedes), ("evolves", evolves)):
        for ref in refs:
            if ref not in known:
                issues.append(f"{kind} -> {ref}: no such entry_id (refs must never be invented)")
            elif ref in entry_ts and entry_ts[ref] > ts:
                issues.append(f"{kind} -> {ref}: target is newer ({entry_ts[ref]}) than this entry ({ts}); edges point backward in time")

    canonical_topics: list[str] = []
    if topics:
        from .topics import load_topic_index

        index = load_topic_index(cwd)
        resolution = index.resolution()
        if not resolution:
            issues.append("topics given but no controlled vocabulary exists (.memory-seed/topics.yaml)")
        else:
            for topic in topics:
                slug = resolution.get(topic)
                if slug is None:
                    issues.append(f"unknown topic '{topic}' (not a canonical slug or alias in topics.yaml)")
                elif slug not in canonical_topics:
                    canonical_topics.append(slug)

    entry_id = generate_session_entry_id(
        timestamp=ts,
        title=title,
        user_initials=user_initials,
        agent_type=agent_type,
        project_path=project_path,
        subproject_path=subproject_path,
    )
    if entry_id in known:
        issues.append(
            f"generated id {entry_id} already exists - identical metadata (timestamp/title/initials/agent/paths); "
            "this looks like a double-append"
        )

    resolved_branch = branch
    if resolved_branch is None and auto_branch:
        lines = _git_capture(runtime.workspace_root, "rev-parse", "--abbrev-ref", "HEAD")
        if lines and lines[0].strip() and lines[0].strip() != "HEAD":
            resolved_branch = lines[0].strip()

    # Write-time DRAFT-format gate: the tool owns structure, so it refuses to
    # write a malformed decision record (bare labels, missing R:, wrong
    # multi-decision shape). The message names the fix; see session_logging.md.
    for issue in entry_body_format_issues(body):
        issues.append(f"body format: {issue}")

    if issues:
        return SessionAppendResult(ok=False, path=target.path, timestamp=ts, issues=tuple(issues))

    yaml_lines = [
        f"entry_id: {entry_id}",
        f"user_initials: {user_initials}",
        f"agent_type: {agent_type}",
        f"agent_name: {agent_name if agent_name else 'null'}",
        f"project_path: {project_path}",
        f"subproject_path: {subproject_path if subproject_path else 'null'}",
    ]
    if resolved_branch:
        yaml_lines.append(f"branch: {resolved_branch}")
    for key, values in (
        ("topics", canonical_topics),
        ("related_entries", list(related_entries)),
        ("supersedes", list(supersedes)),
        ("evolves", list(evolves)),
    ):
        if values:
            yaml_lines.append(f"{key}:")
            yaml_lines.extend(f"  - {value}" for value in values)

    block = "\n".join(
        [f"## {ts} - {title}", "", "```yaml", *yaml_lines, "```", "", body.strip(), ""]
    )
    target = session_target(cwd, date_str=date_part, explicit_user=explicit_user, create=True)
    existing = read_text_file(target.path) if target.path.exists() else ""
    if existing.strip():
        new_text = existing.rstrip("\n") + "\n\n" + block
    else:
        new_text = existing + block
    write_text_file(target.path, new_text)
    return SessionAppendResult(ok=True, path=target.path, entry_id=entry_id, timestamp=ts, written=True)


def _git_capture(root: Path, *args: str) -> list[str] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.splitlines()


@dataclass(frozen=True)
class SessionReorderResult:
    path: Path
    ok: bool
    changed: bool
    applied: bool
    order_before: tuple[str, ...] = ()
    order_after: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()


def session_reorder(
    cwd: Path | str = ".",
    *,
    date_str: str,
    explicit_user: str | None = None,
    apply: bool = False,
) -> SessionReorderResult:
    """Restore chronological order in one day's session file - a pure block
    permutation, never a content edit.

    Entries are `## YYYY-MM-DD HH:MM - title` blocks; the file's bytes are
    split into preamble + entry spans and the spans are stably re-sorted by
    heading timestamp (ties keep their original relative order). Every
    entry's bytes - ids, refs, body - are untouched: order is presentation,
    content is history, so this stays inside the append-only contract. The
    function refuses (ok=False) rather than guess when any `## ` heading
    does not parse as a timestamped entry or the file does not end with a
    newline (both would make a byte-exact permutation ambiguous). Dry-run by
    default; ``apply=True`` writes. Intended for repairing misordered logs
    that block ``session merge-branch``'s chronology gate - run
    ``links check`` after applying.
    """
    target = session_target(cwd, date_str=date_str, explicit_user=explicit_user, create=False)
    path = target.path
    if not path.exists():
        return SessionReorderResult(path=path, ok=False, changed=False, applied=False, issues=(f"no session file for {date_str}",))
    text = read_text_file(path)
    matches = list(_ENTRY_HEADING_RE.finditer(text))
    if not matches:
        return SessionReorderResult(path=path, ok=True, changed=False, applied=False, issues=("no entries found",))

    issues: list[str] = []
    blocks: list[tuple[str, int, str]] = []  # (timestamp, original_index, bytes)
    for index, match in enumerate(matches):
        heading = match.group(0)
        parsed = _REORDER_HEADING_RE.match(heading)
        if not parsed:
            issues.append(f"heading is not a timestamped entry: {heading!r}")
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start():end]
        if not block.endswith("\n"):
            issues.append(f"entry at {parsed.group(1)} does not end with a newline; permutation would not be byte-exact")
        blocks.append((parsed.group(1), index, block))
    if issues:
        return SessionReorderResult(path=path, ok=False, changed=False, applied=False, issues=tuple(issues))

    preamble = text[: matches[0].start()]
    ordered = sorted(blocks, key=lambda item: (item[0], item[1]))
    order_before = tuple(f"{ts} - {_REORDER_HEADING_RE.match(block.splitlines()[0]).group(2)}" for ts, _i, block in blocks)
    order_after = tuple(f"{ts} - {_REORDER_HEADING_RE.match(block.splitlines()[0]).group(2)}" for ts, _i, block in ordered)
    changed = [item[1] for item in ordered] != [item[1] for item in blocks]
    if not changed:
        return SessionReorderResult(path=path, ok=True, changed=False, applied=False, order_before=order_before, order_after=order_after)

    new_text = preamble + "".join(block for _ts, _i, block in ordered)
    # Byte-exact permutation guarantee: same content, only order differs.
    if sorted(new_text) != sorted(text):
        return SessionReorderResult(
            path=path, ok=False, changed=True, applied=False,
            order_before=order_before, order_after=order_after,
            issues=("internal error: permutation would alter file bytes; refusing",),
        )
    if apply:
        write_text_file(path, new_text)
    return SessionReorderResult(
        path=path, ok=True, changed=True, applied=apply,
        order_before=order_before, order_after=order_after,
    )


def _flat_session_entries(text: str) -> list[_FlatSessionEntry]:
    matches = list(_ENTRY_HEADING_RE.finditer(text))
    entries: list[_FlatSessionEntry] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entry_text = text[match.start():end].rstrip() + "\n"
        entry_id_match = _ENTRY_ID_RE.search(entry_text)
        initials_match = _USER_INITIALS_RE.search(entry_text)
        entries.append(
            _FlatSessionEntry(
                text=entry_text,
                entry_id=entry_id_match.group(1) if entry_id_match else None,
                user_initials=initials_match.group(1) if initials_match else None,
            )
        )
    return entries


def _participant_slug_by_initials(target_root: Path) -> tuple[dict[str, str], list[str]]:
    mapping: dict[str, str] = {}
    issues: list[str] = []
    for participant in read_project_participants(target_root):
        key = participant.initials.strip()
        if not key:
            continue
        if key in mapping and mapping[key] != participant.slug:
            issues.append(f"duplicate participant initials {key}: {mapping[key]}, {participant.slug}")
        else:
            mapping[key] = participant.slug
    return mapping, issues


def _append_session_entries(path: Path, entries: list[_FlatSessionEntry]) -> None:
    existing = read_text_file(path) if path.exists() else ""
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    body = "\n".join(entry.text.rstrip() for entry in entries).rstrip() + "\n"
    write_text_file(path, prefix + body)


def migrate_session_layout(cwd: str | Path = ".", dry_run: bool = False) -> SessionLayoutMigrationResult:
    """Migrate legacy flat session files into per-day/per-user files.

    The migration is deliberately conservative: every legacy entry must carry a
    ``user_initials`` value that maps to a ``participants:`` entry in
    ``.memory-seed/project.yaml``. Existing per-user files are appended to only
    when none of the incoming entry IDs already exist there. On apply, each
    migrated flat source is backed up and then removed so permanent dual-read
    compatibility does not create duplicate entry IDs.
    """
    runtime = resolve_runtime(cwd)
    target_root = runtime.workspace_root
    sessions_dir = runtime.memory_dir / "sessions"
    initials_to_slug, participant_issues = _participant_slug_by_initials(target_root)

    grouped: dict[Path, list[_FlatSessionEntry]] = {}
    source_docs: list[SessionDocument] = []
    issues: list[str] = list(participant_issues)

    for doc in iter_session_documents(sessions_dir):
        if doc.layout != "legacy-flat":
            continue
        try:
            text = doc.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(f"{doc.path.name}: unreadable ({exc})")
            continue
        entries = _flat_session_entries(text)
        if not entries:
            continue
        source_docs.append(doc)
        for entry in entries:
            if not entry.user_initials:
                issues.append(f"{doc.path.name}: entry has no user_initials")
                continue
            slug = initials_to_slug.get(entry.user_initials)
            if slug is None:
                issues.append(f"{doc.path.name}: no participant slug for user_initials {entry.user_initials}")
                continue
            target = session_path(sessions_dir, doc.session_date, slug)
            grouped.setdefault(target, []).append(entry)

    if issues:
        return SessionLayoutMigrationResult(changed=False, issues=issues)

    planned = sorted(
        {
            f"{doc.session_date}.md -> {target.relative_to(sessions_dir).as_posix()}"
            for doc in source_docs
            for target in grouped
            if target.parent.name == doc.session_date
        }
    )
    if not grouped:
        return SessionLayoutMigrationResult(changed=False, planned=planned)

    for target, entries in grouped.items():
        if not target.exists():
            continue
        existing = target.read_text(encoding="utf-8")
        existing_ids = set(_ENTRY_ID_RE.findall(existing))
        incoming_ids = {entry.entry_id for entry in entries if entry.entry_id}
        duplicates = sorted(existing_ids & incoming_ids)
        if duplicates:
            issues.append(
                f"{target.relative_to(sessions_dir).as_posix()}: existing entry_id(s) block safe merge: "
                + ", ".join(duplicates)
            )
    if issues:
        return SessionLayoutMigrationResult(changed=False, planned=planned, issues=issues)

    if dry_run:
        return SessionLayoutMigrationResult(changed=False, planned=planned)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backed_up: list[Path] = []
    migrated: list[str] = []

    for target, entries in sorted(grouped.items(), key=lambda item: item[0].relative_to(sessions_dir).as_posix()):
        user = target.stem
        date_str = target.parent.name
        _ensure_per_user_session_file(target, date_str, user)
        _append_session_entries(target, entries)
        migrated.append(target.relative_to(sessions_dir).as_posix())

    for doc in source_docs:
        backup_relative = Path(MEMORY_DIR_NAME) / "backups" / timestamp / "sessions" / doc.path.name
        backup_path = target_root / backup_relative
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        _copy_text_file(doc.path, backup_path)
        doc.path.unlink()
        backed_up.append(backup_relative)

    return SessionLayoutMigrationResult(
        changed=bool(migrated or backed_up),
        planned=planned,
        migrated=migrated,
        backed_up=backed_up,
    )


def _backup_session_source(target_root: Path, sessions_dir: Path, source: Path, timestamp: str) -> Path:
    source_rel = source.relative_to(sessions_dir)
    backup_relative = Path(MEMORY_DIR_NAME) / "backups" / timestamp / "sessions" / source_rel
    backup_path = target_root / backup_relative
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    _copy_text_file(source, backup_path)
    return backup_relative


def _source_entries_for_append(path: Path) -> list[_FlatSessionEntry]:
    return _flat_session_entries(path.read_text(encoding="utf-8"))


def _hash_id_from_file_frontmatter(text: str) -> str | None:
    match = _FILE_FRONTMATTER_RE.match(text)
    if not match:
        return None
    return _parse_frontmatter_scalars(match.group(1)).get("hash_id")


_SESSION_ENTRY_HEADING_TS_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+-")


def _session_doc_from_relative_path(rel_path: str) -> tuple[str, str | None, str] | None:
    path = Path(rel_path)
    parts = path.parts
    if len(parts) < 3 or parts[0] != MEMORY_DIR_NAME or parts[1] != "sessions":
        return None
    rest = parts[2:]
    if not rest or rest[0] == "diagrams":
        return None
    if len(rest) == 1:
        match = SESSION_DATE_RE.match(rest[0])
        if not match or not _valid_session_date(match.group(1)):
            return None
        return match.group(1), None, "legacy-flat"
    if len(rest) == 2:
        day_match = SESSION_DAY_DIR_RE.match(rest[0])
        if day_match and rest[1].endswith(".md"):
            date_str = day_match.group(1)
            user = Path(rest[1]).stem
            if _valid_session_date(date_str) and SESSION_USER_SLUG_RE.match(user) and user not in _RESERVED_SESSION_STEMS:
                return date_str, user, "per-user-day"
        month_match = SESSION_MONTH_DIR_RE.match(rest[0])
        date_match = SESSION_DATE_RE.match(rest[1])
        if month_match and date_match:
            month_str = month_match.group(1)
            date_str = date_match.group(1)
            if _valid_session_date(date_str) and date_str.startswith(month_str + "-"):
                return date_str, None, "month-flat"
    if len(rest) == 3:
        month_match = SESSION_MONTH_DIR_RE.match(rest[0])
        day_match = SESSION_DAY_DIR_RE.match(rest[1])
        if month_match and day_match and rest[2].endswith(".md"):
            month_str = month_match.group(1)
            date_str = day_match.group(1)
            user = Path(rest[2]).stem
            if (
                _valid_session_date(date_str)
                and date_str.startswith(month_str + "-")
                and SESSION_USER_SLUG_RE.match(user)
                and user not in _RESERVED_SESSION_STEMS
            ):
                return date_str, user, "month-user"
    return None


def _diagram_doc_from_relative_path(rel_path: str) -> tuple[str | None, str] | None:
    path = Path(rel_path)
    parts = path.parts
    if len(parts) < 4 or parts[0] != MEMORY_DIR_NAME or parts[1] != "sessions" or parts[2] != "diagrams":
        return None
    rest = parts[3:]
    if len(rest) == 1:
        match = SESSION_DATE_RE.match(rest[0])
        if match and _valid_session_date(match.group(1)):
            return match.group(1), "legacy-diagram"
        return None, "legacy-diagram"
    if len(rest) == 2:
        month_match = SESSION_MONTH_DIR_RE.match(rest[0])
        date_match = SESSION_DATE_RE.match(rest[1])
        if month_match and date_match:
            month_str = month_match.group(1)
            date_str = date_match.group(1)
            if _valid_session_date(date_str) and date_str.startswith(month_str + "-"):
                return date_str, "month-diagram"
        return None, "month-diagram"
    return None


def _session_target_relative_path(date_str: str, user: str | None = None) -> str:
    if user:
        return (Path(MEMORY_DIR_NAME) / "sessions" / date_str[:7] / date_str / f"{user}.md").as_posix()
    return (Path(MEMORY_DIR_NAME) / "sessions" / date_str[:7] / f"{date_str}.md").as_posix()


def _diagram_target_relative_path(date_str: str) -> str:
    return (Path(MEMORY_DIR_NAME) / "sessions" / "diagrams" / date_str[:7] / f"{date_str}.md").as_posix()


def _split_entry_records(text: str, *, source_path: str, session_date: str, user: str | None) -> list[_SessionEntryRecord]:
    matches = list(_ENTRY_HEADING_RE.finditer(text))
    records: list[_SessionEntryRecord] = []
    target_path = _session_target_relative_path(session_date, user)
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entry_text = text[match.start():end].rstrip() + "\n"
        heading_line = match.group(0)
        timestamp_match = _SESSION_ENTRY_HEADING_TS_RE.match(heading_line)
        timestamp = timestamp_match.group(1) if timestamp_match else None
        yaml_match = _FENCED_YAML_RE.search(entry_text)
        yaml_block = yaml_match.group(1) if yaml_match else ""
        entry_id_match = _ENTRY_ID_RE.search(yaml_block)
        scalars = _parse_frontmatter_scalars(yaml_block)
        records.append(
            _SessionEntryRecord(
                text=entry_text,
                entry_id=entry_id_match.group(1) if entry_id_match else None,
                timestamp=timestamp,
                session_date=session_date,
                branch=scalars.get("branch"),
                source_path=source_path,
                target_path=target_path,
                user=user,
            )
        )
    return records


def _session_file_prefix(text: str, date_str: str, *, user: str | None = None) -> str:
    first_heading = _ENTRY_HEADING_RE.search(text)
    if first_heading:
        prefix = text[:first_heading.start()].rstrip()
        if prefix:
            return prefix + "\n\n"
    if user:
        return ""
    return (
        "---\n"
        "tags:\n"
        "  - session-log\n"
        "  - memory-seed\n"
        f"session_date: {date_str}\n"
        "---\n\n"
    )


def _diagram_file_prefix(text: str, date_str: str) -> str:
    first_heading = _ENTRY_HEADING_RE.search(text)
    if first_heading:
        prefix = text[:first_heading.start()].rstrip()
        if prefix:
            return prefix + "\n\n"
    return (
        "---\n"
        "tags:\n"
        "  - session-log-diagrams\n"
        f"diagram_date: {date_str}\n"
        "---\n\n"
    )


def _split_diagram_records(text: str, *, source_path: str, diagram_date: str | None) -> list[_DiagramSidecarRecord]:
    blocks = list(_ENTRY_TS_YAML_RE.finditer(text))
    records: list[_DiagramSidecarRecord] = []
    for index, block in enumerate(blocks):
        section_end = blocks[index + 1].start() if index + 1 < len(blocks) else len(text)
        block_text = text[block.start():section_end].rstrip() + "\n"
        timestamp, yaml_block = block.groups()
        entry_id_match = _ENTRY_ID_RE.search(yaml_block)
        target_date = diagram_date or timestamp[:10]
        records.append(
            _DiagramSidecarRecord(
                text=block_text,
                entry_id=entry_id_match.group(1) if entry_id_match else None,
                timestamp=timestamp,
                diagram_date=diagram_date,
                source_path=source_path,
                target_path=_diagram_target_relative_path(target_date),
            )
        )
    return records


def _git_lines(root: Path, args: Sequence[str]) -> tuple[int, list[str]]:
    code, text = _git_text(root, args)
    if code != 0 or not text:
        return code, []
    return code, [line for line in text.splitlines() if line.strip()]


_GIT_SHOW_DECODE_ERROR = object()


def _git_show_text(root: Path, ref: str, rel_path: str) -> str | None | object:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "show", f"{ref}:{rel_path}"],
            capture_output=True,
            text=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return _GIT_SHOW_DECODE_ERROR


def _git_ref_paths(root: Path, ref: str) -> list[str]:
    code, lines = _git_lines(root, ("ls-tree", "-r", "--name-only", ref, "--", f"{MEMORY_DIR_NAME}/sessions"))
    if code != 0:
        return []
    return lines


def _changed_session_paths(root: Path, base: str, branch: str) -> set[str] | None:
    """Session/diagram file paths changed on ``branch`` relative to its merge-base with ``base``.

    Uses a three-dot diff (``base...branch`` == merge-base(base, branch)..branch) so only the
    branch's own additions are in scope. Two-dot would also surface base's post-divergence session
    appends - which matters here because every integration merge appends to the same dated files.
    Scoping the branch-side record walk to this set keeps fuse from validating unchanged base-tree
    files (e.g. legacy pre-schema logs that carry no entry_id) that were never part of the branch.

    Returns ``None`` when the diff command itself fails (e.g. no merge-base / unrelated histories),
    distinct from a legitimate empty diff (empty set). Callers must treat ``None`` as an error rather
    than "nothing changed", or a git failure would silently filter out every branch record and make
    the fuse report success while importing nothing.
    """
    code, lines = _git_lines(
        root,
        ("diff", "--name-only", f"{base}...{branch}", "--", f"{MEMORY_DIR_NAME}/sessions"),
    )
    if code != 0:
        return None
    return set(lines)


def _entry_records_from_ref(
    root: Path,
    ref: str,
    *,
    only_paths: set[str] | None = None,
    decode_issues: list[str] | None = None,
) -> list[_SessionEntryRecord]:
    records: list[_SessionEntryRecord] = []
    for rel_path in _git_ref_paths(root, ref):
        if only_paths is not None and rel_path not in only_paths:
            continue
        doc = _session_doc_from_relative_path(rel_path)
        if doc is None:
            continue
        date_str, user, _layout = doc
        text = _git_show_text(root, ref, rel_path)
        if text is _GIT_SHOW_DECODE_ERROR:
            if decode_issues is not None:
                decode_issues.append(f"could not decode {rel_path} as UTF-8")
            continue
        if text is None:
            continue
        records.extend(_split_entry_records(text, source_path=rel_path, session_date=date_str, user=user))
    return records


def _entries_from_ref(root: Path, ref: str) -> dict[str, _SessionEntryRecord]:
    entries: dict[str, _SessionEntryRecord] = {}
    for record in _entry_records_from_ref(root, ref):
        if record.entry_id and record.entry_id not in entries:
            entries[record.entry_id] = record
    return entries


def _sidecar_records_from_ref(
    root: Path,
    ref: str,
    *,
    only_paths: set[str] | None = None,
    decode_issues: list[str] | None = None,
) -> list[_DiagramSidecarRecord]:
    records: list[_DiagramSidecarRecord] = []
    for rel_path in _git_ref_paths(root, ref):
        if only_paths is not None and rel_path not in only_paths:
            continue
        doc = _diagram_doc_from_relative_path(rel_path)
        if doc is None:
            continue
        diagram_date, _layout = doc
        text = _git_show_text(root, ref, rel_path)
        if text is _GIT_SHOW_DECODE_ERROR:
            if decode_issues is not None:
                decode_issues.append(f"could not decode {rel_path} as UTF-8")
            continue
        if text is None:
            continue
        records.extend(_split_diagram_records(text, source_path=rel_path, diagram_date=diagram_date))
    return records


def _sidecars_from_ref(root: Path, ref: str) -> dict[str, _DiagramSidecarRecord]:
    sidecars: dict[str, _DiagramSidecarRecord] = {}
    for record in _sidecar_records_from_ref(root, ref):
        if record.entry_id and record.entry_id not in sidecars:
            sidecars[record.entry_id] = record
    return sidecars


def _working_tree_entries(root: Path, rel_path: str, *, date_str: str, user: str | None) -> list[_SessionEntryRecord]:
    path = root / rel_path
    if not path.exists():
        return []
    text = read_text_file(path)
    return _split_entry_records(text, source_path=rel_path, session_date=date_str, user=user)


def _working_tree_sidecars(root: Path, rel_path: str, *, diagram_date: str) -> list[_DiagramSidecarRecord]:
    path = root / rel_path
    if not path.exists():
        return []
    text = read_text_file(path)
    return _split_diagram_records(text, source_path=rel_path, diagram_date=diagram_date)


def _records_are_chronological(records: Sequence[_SessionEntryRecord | _DiagramSidecarRecord]) -> bool:
    timestamps = [record.timestamp for record in records]
    if any(timestamp is None for timestamp in timestamps):
        return False
    return list(timestamps) == sorted(timestamps)


def _write_chronological_session_file(path: Path, date_str: str, records: Sequence[_SessionEntryRecord], *, user: str | None = None) -> None:
    existing_text = read_text_file(path) if path.exists() else ""
    prefix = _session_file_prefix(existing_text, date_str, user=user)
    ordered = sorted(records, key=lambda record: (record.timestamp or "", record.entry_id or ""))
    # Records are rstripped, so a double newline leaves exactly one blank line
    # between entries - the same separation a hand-appended log has. A single
    # "\n" here butts each heading against the previous entry's last line.
    body = "\n\n".join(record.text.rstrip() for record in ordered).rstrip()
    write_text_file(path, prefix + body + "\n")


def _write_chronological_diagram_file(path: Path, date_str: str, records: Sequence[_DiagramSidecarRecord]) -> None:
    existing_text = read_text_file(path) if path.exists() else ""
    prefix = _diagram_file_prefix(existing_text, date_str)
    ordered = sorted(records, key=lambda record: (record.timestamp or "", record.entry_id or ""))
    # Same blank-line separation contract as the session-file writer above.
    body = "\n\n".join(record.text.rstrip() for record in ordered).rstrip()
    write_text_file(path, prefix + body + "\n")


def _git_dir(root: Path) -> Path | None:
    code, git_dir = _git_text(root, ("rev-parse", "--git-dir"))
    if code != 0 or not git_dir:
        return None
    path = Path(git_dir)
    if not path.is_absolute():
        path = root / path
    return path


def _stamp_memory_entry_trailers(root: Path, planned_entries: Sequence[str]) -> list[str]:
    """Append ``Memory-Entry: <entry_id>`` trailers to the prepared MERGE_MSG.

    Takes the fuse's planned-entry lines (``"<entry_id> <timestamp> -> <path>"``),
    keeps the first occurrence of each well-formed id (no cap - a partial list
    would make ``find_trailer_commits`` silently miss entries), and appends one
    trailer line per id below the existing message content. Returns the stamped
    ids; returns ``[]`` without raising on any failure so trailer stamping can
    never abort a merge.
    """
    stamped: list[str] = []
    for planned in planned_entries:
        entry_id = planned.split(" ", 1)[0]
        if entry_id and entry_id not in stamped and _TRAILER_ENTRY_ID_RE.fullmatch(entry_id):
            stamped.append(entry_id)
    if not stamped:
        return []
    git_dir = _git_dir(root)
    if git_dir is None:
        return []
    merge_msg = git_dir / "MERGE_MSG"
    try:
        message = merge_msg.read_text(encoding="utf-8") if merge_msg.exists() else ""
    except (OSError, UnicodeDecodeError):
        return []
    if not message.strip():
        return []
    # Dedupe against Memory-Entry trailers already in the message (a hook may
    # have stamped some) so none is written twice.
    already = {
        line.strip()[len("Memory-Entry:"):].strip()
        for line in message.splitlines()
        if line.strip().startswith("Memory-Entry:")
    }
    missing = [entry_id for entry_id in stamped if entry_id not in already]
    if not missing:
        return stamped
    trailer_block = "".join(f"Memory-Entry: {entry_id}\n" for entry_id in missing)
    body = message.rstrip("\n")
    last_line = body.rsplit("\n", 1)[-1] if body else ""
    # Append CONTIGUOUSLY to an existing trailer block: a blank line splits it,
    # and git's trailer parser (and Memory Trace's merge geometry) reads only the
    # final contiguous block, silently dropping every earlier Memory-Entry.
    # Blank-line-separate only when the message ends in prose.
    joiner = "\n" if re.match(r"[A-Za-z][A-Za-z0-9-]*: ", last_line) else "\n\n"
    try:
        merge_msg.write_text(body + joiner + trailer_block, encoding="utf-8")
    except OSError:
        return []
    return stamped


def _merge_head_commits(root: Path) -> list[str]:
    git_dir = _git_dir(root)
    if git_dir is None:
        return []
    merge_head = git_dir / "MERGE_HEAD"
    if not merge_head.exists():
        return []
    try:
        return [line.strip() for line in merge_head.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError):
        return []


def _resolve_commit(root: Path, ref: str) -> str | None:
    code, commit = _git_text(root, ("rev-parse", f"{ref}^{{commit}}"))
    return commit if code == 0 and commit else None


def _current_branch_name(root: Path) -> str | None:
    code, branch = _git_text(root, ("branch", "--show-current"))
    return branch if code == 0 and branch else None


def _git_dirty_paths(root: Path) -> list[str] | None:
    code, status_out = _git_text(root, ("status", "--short"))
    if code != 0:
        return None
    return [line.strip() for line in status_out.splitlines() if line.strip()]


def _format_dirty_paths_issue(dirty_paths: Sequence[str]) -> str:
    listing = "; ".join(dirty_paths[:10])
    if len(dirty_paths) > 10:
        listing += f"; ... ({len(dirty_paths) - 10} more)"
    return f"working tree is not clean; commit or stash these paths first: {listing}"


def _resolve_pr_base_branch(
    root: Path,
    explicit_base_branch: str | None,
    *,
    source_branch: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    def _candidate(display: str, ref: str) -> tuple[str, str, str] | None:
        commit = _resolve_commit(root, ref)
        if commit is None:
            return None
        return (display, ref, commit)

    if explicit_base_branch:
        display = explicit_base_branch.removeprefix("origin/")
        refs = (explicit_base_branch,) if explicit_base_branch.startswith("origin/") else (f"origin/{display}", explicit_base_branch)
        for ref in refs:
            candidate = _candidate(display, ref)
            if candidate is not None:
                return candidate[0], candidate[1], candidate[2], None
        return None, None, None, f"base branch does not resolve to a commit: {explicit_base_branch}"

    ordered: list[tuple[str, str, str]] = []
    by_display: dict[str, tuple[str, str, str]] = {}
    for display in ("main", "master"):
        for ref in (f"origin/{display}", display):
            candidate = _candidate(display, ref)
            if candidate is None:
                continue
            if display not in by_display:
                by_display[display] = candidate
                ordered.append(candidate)
            break

    code, remote_head = _git_text(root, ("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"))
    if code == 0 and remote_head:
        display = remote_head.rsplit("/", 1)[-1]
        if display not in by_display:
            candidate = _candidate(display, f"origin/{display}") or _candidate(display, display)
            if candidate is not None:
                by_display[display] = candidate
                ordered.append(candidate)

    ordered = [item for item in ordered if item[0] != source_branch]
    if not ordered:
        return None, None, None, "could not infer a PR base branch; pass --base-branch explicitly"
    if len(ordered) > 1:
        names = ", ".join(item[0] for item in ordered)
        return None, None, None, f"ambiguous PR base branch ({names}); pass --base-branch explicitly"
    return ordered[0][0], ordered[0][1], ordered[0][2], None


def _refresh_pr_base_branch(root: Path, *, remote_name: str, base_branch: str) -> str | None:
    """Refresh the remote-tracking base used by a real PR preparation.

    Preparing against a stale ``origin/main`` only makes the later host merge
    *appear* clean. Fetch the selected branch into its normal tracking ref
    before the task branch is changed; a non-fast-forward remote rewrite fails
    closed because this refspec deliberately does not force it.
    """
    refspec = f"refs/heads/{base_branch}:refs/remotes/{remote_name}/{base_branch}"
    code, output = _git_text(root, ("fetch", "--no-tags", remote_name, refspec))
    if code == 0:
        return None
    detail = f": {output}" if output else ""
    return (
        f"could not refresh {remote_name}/{base_branch} before branch preparation; "
        f"the task branch was not modified{detail}"
    )


def _plan_session_fuse(
    root: Path,
    *,
    source_ref: str,
    base_ref: str,
    source_label: str,
) -> tuple[_SessionFusePlan | None, list[str]]:
    source_commit = _resolve_commit(root, source_ref)
    if source_commit is None:
        return None, [f"source ref does not resolve to a commit: {source_ref}"]
    base_commit = _resolve_commit(root, base_ref)
    if base_commit is None:
        return None, [f"base ref does not resolve to a commit: {base_ref}"]

    changed_paths = _changed_session_paths(root, base_commit, source_commit)
    if changed_paths is None:
        return None, [f"could not compute changed session files for source {source_label} against base {base_ref}"]

    issues: list[str] = []
    base_paths = set(_git_ref_paths(root, base_commit))
    base_entry_records = _entry_records_from_ref(root, base_commit)
    source_entry_records = _entry_records_from_ref(
        root,
        source_commit,
        only_paths=changed_paths,
        decode_issues=issues,
    )
    base_sidecar_records = _sidecar_records_from_ref(root, base_commit)
    source_sidecar_records = _sidecar_records_from_ref(
        root,
        source_commit,
        only_paths=changed_paths,
        decode_issues=issues,
    )

    base_entries: dict[str, _SessionEntryRecord] = {}
    source_entries: dict[str, _SessionEntryRecord] = {}
    base_sidecars: dict[str, _DiagramSidecarRecord] = {}
    source_sidecars: dict[str, _DiagramSidecarRecord] = {}

    import_entries: list[_SessionEntryRecord] = []
    imported_ids: set[str] = set()
    import_sidecars: list[_DiagramSidecarRecord] = []

    seen_source_entries: set[str] = set()
    duplicate_source_entries: set[str] = set()
    for record in base_entry_records:
        if record.entry_id and record.entry_id not in base_entries:
            base_entries[record.entry_id] = record
    for record in source_entry_records:
        if not record.entry_id:
            issues.append(f"{record.source_path}: session entry at {record.timestamp or '(unknown time)'} has no entry_id")
            continue
        if record.entry_id in seen_source_entries:
            duplicate_source_entries.add(record.entry_id)
            continue
        seen_source_entries.add(record.entry_id)
        source_entries[record.entry_id] = record
    for entry_id in sorted(duplicate_source_entries):
        issues.append(f"source {source_label}: duplicate session entry_id blocks safe fuse: {entry_id}")

    seen_source_sidecars: set[str] = set()
    duplicate_source_sidecars: set[str] = set()
    for record in base_sidecar_records:
        if record.entry_id and record.entry_id not in base_sidecars:
            base_sidecars[record.entry_id] = record
    for record in source_sidecar_records:
        if not record.entry_id:
            issues.append(f"{record.source_path}: diagram sidecar block at {record.timestamp or '(unknown time)'} has no entry_id")
            continue
        if record.entry_id in seen_source_sidecars:
            duplicate_source_sidecars.add(record.entry_id)
            continue
        seen_source_sidecars.add(record.entry_id)
        source_sidecars[record.entry_id] = record
    for entry_id in sorted(duplicate_source_sidecars):
        issues.append(f"source {source_label}: duplicate diagram sidecar blocks safe fuse: {entry_id}")

    for entry_id, source_entry in sorted(source_entries.items(), key=lambda item: (item[1].timestamp or "", item[0])):
        base_entry = base_entries.get(entry_id)
        if base_entry is not None:
            if base_entry.text != source_entry.text:
                issues.append(f"{source_entry.source_path}: existing entry_id modified on source: {entry_id}")
            continue
        if not source_entry.timestamp:
            issues.append(f"{source_entry.source_path}: entry_id {entry_id} has no parseable timestamp heading")
            continue
        if source_entry.timestamp[:10] != source_entry.session_date:
            issues.append(
                f"{source_entry.source_path}: entry_id {entry_id} heading date {source_entry.timestamp[:10]} "
                f"does not match session date {source_entry.session_date}"
            )
            continue
        if source_entry.branch != source_label:
            issues.append(
                f"{source_entry.source_path}: entry_id {entry_id} has branch {source_entry.branch or '(missing)'}; expected {source_label}"
            )
            continue
        if source_entry.branch in {"main", "master"}:
            issues.append(f"{source_entry.source_path}: entry_id {entry_id} records integration branch {source_entry.branch}")
            continue
        import_entries.append(source_entry)
        imported_ids.add(entry_id)

    for entry_id, source_sidecar in sorted(source_sidecars.items(), key=lambda item: (item[1].timestamp or "", item[0])):
        base_sidecar = base_sidecars.get(entry_id)
        if base_sidecar is not None:
            if base_sidecar.text != source_sidecar.text:
                issues.append(f"{source_sidecar.source_path}: existing diagram sidecar modified for entry_id {entry_id}")
            continue
        parent_entry = source_entries.get(entry_id) if entry_id in imported_ids else base_entries.get(entry_id)
        if parent_entry is None:
            issues.append(
                f"{source_sidecar.source_path}: diagram sidecar references entry_id {entry_id} "
                "without a parent entry on the base branch or accepted for this fuse"
            )
            continue
        if parent_entry.timestamp is None:
            issues.append(f"{source_sidecar.source_path}: parent entry_id {entry_id} has no parseable timestamp")
            continue
        if source_sidecar.timestamp is None:
            issues.append(f"{source_sidecar.source_path}: diagram sidecar for entry_id {entry_id} has no parseable timestamp")
            continue
        if source_sidecar.diagram_date and source_sidecar.diagram_date != parent_entry.timestamp[:10]:
            issues.append(
                f"{source_sidecar.source_path}: diagram date {source_sidecar.diagram_date} does not match "
                f"entry date {parent_entry.timestamp[:10]} for {entry_id}"
            )
            continue
        import_sidecars.append(source_sidecar)

    if issues:
        return None, issues

    planned_entries: list[str] = []
    planned_sidecars: list[str] = []
    removed_sources: list[str] = []

    for entry in import_entries:
        planned_entries.append(f"{entry.entry_id} {entry.timestamp} -> {entry.target_path}")
        if entry.source_path != entry.target_path and entry.source_path not in base_paths:
            if entry.source_path not in removed_sources:
                removed_sources.append(entry.source_path)

    for sidecar in import_sidecars:
        planned_sidecars.append(f"{sidecar.entry_id} {sidecar.timestamp} -> {sidecar.target_path}")
        if sidecar.source_path != sidecar.target_path and sidecar.source_path not in base_paths:
            if sidecar.source_path not in removed_sources:
                removed_sources.append(sidecar.source_path)

    return _SessionFusePlan(
        source_label=source_label,
        source_commit=source_commit,
        base_commit=base_commit,
        changed_paths=tuple(sorted(changed_paths)),
        import_entries=tuple(import_entries),
        import_sidecars=tuple(import_sidecars),
        planned_entries=tuple(planned_entries),
        planned_sidecars=tuple(planned_sidecars),
        removed_sources=tuple(removed_sources),
    ), []


def _apply_session_fuse_plan(root: Path, plan: _SessionFusePlan) -> SessionFuseResult:
    planned_entries = list(plan.planned_entries)
    planned_sidecars = list(plan.planned_sidecars)
    removed_sources = list(plan.removed_sources)
    already_present: list[str] = []

    entries_by_target: dict[str, list[_SessionEntryRecord]] = {}
    for entry in plan.import_entries:
        entries_by_target.setdefault(entry.target_path, []).append(entry)

    sidecars_by_target: dict[str, list[_DiagramSidecarRecord]] = {}
    for sidecar in plan.import_sidecars:
        sidecars_by_target.setdefault(sidecar.target_path, []).append(sidecar)

    session_writes: list[tuple[Path, str, str | None, list[_SessionEntryRecord]]] = []
    diagram_writes: list[tuple[Path, str, list[_DiagramSidecarRecord]]] = []

    for target_rel, incoming in entries_by_target.items():
        target_path = root / target_rel
        date_str = incoming[0].session_date
        user = incoming[0].user
        existing = _working_tree_entries(root, target_rel, date_str=date_str, user=user)
        if not _records_are_chronological(existing):
            return SessionFuseResult(changed=False, issues=[f"{target_rel}: existing entries are not chronological"])
        by_id = {record.entry_id: record for record in existing if record.entry_id}
        writable_records = list(existing)
        for record in incoming:
            current = by_id.get(record.entry_id)
            if current is not None:
                if current.text == record.text:
                    already_present.append(record.entry_id or "")
                    continue
                return SessionFuseResult(changed=False, issues=[f"{target_rel}: entry_id {record.entry_id} already exists with different text"])
            writable_records.append(record)
        writable_records = sorted(writable_records, key=lambda item: (item.timestamp or "", item.entry_id or ""))
        if not _records_are_chronological(writable_records):
            return SessionFuseResult(changed=False, issues=[f"{target_rel}: imported entries are not chronological"])
        session_writes.append((target_path, date_str, user, writable_records))

    for target_rel, incoming in sidecars_by_target.items():
        target_path = root / target_rel
        date_str = incoming[0].target_path.rsplit("/", 1)[-1].removesuffix(".md")
        existing = _working_tree_sidecars(root, target_rel, diagram_date=date_str)
        if not _records_are_chronological(existing):
            return SessionFuseResult(changed=False, issues=[f"{target_rel}: existing diagram blocks are not chronological"])
        by_id = {record.entry_id: record for record in existing if record.entry_id}
        writable_records = list(existing)
        for record in incoming:
            current = by_id.get(record.entry_id)
            if current is not None:
                if current.text == record.text:
                    already_present.append(record.entry_id or "")
                    continue
                return SessionFuseResult(changed=False, issues=[f"{target_rel}: diagram for entry_id {record.entry_id} already exists with different text"])
            writable_records.append(record)
        writable_records = sorted(writable_records, key=lambda item: (item.timestamp or "", item.entry_id or ""))
        if not _records_are_chronological(writable_records):
            return SessionFuseResult(changed=False, issues=[f"{target_rel}: imported diagram blocks are not chronological"])
        diagram_writes.append((target_path, date_str, writable_records))

    for target_path, date_str, user, writable_records in session_writes:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if user and not target_path.exists():
            _ensure_per_user_session_file(target_path, date_str, user)
        _write_chronological_session_file(target_path, date_str, writable_records, user=user)

    for target_path, date_str, writable_records in diagram_writes:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _write_chronological_diagram_file(target_path, date_str, writable_records)

    for source_rel in removed_sources:
        source_path = root / source_rel
        if source_path.exists() and source_path.is_file():
            source_path.unlink()

    return SessionFuseResult(
        changed=bool(planned_entries or planned_sidecars or removed_sources),
        planned_entries=planned_entries,
        planned_sidecars=planned_sidecars,
        removed_sources=removed_sources,
        already_present=already_present,
    )


def session_fuse(
    cwd: str | Path = ".",
    *,
    branch: str,
    base: str = "HEAD",
    apply: bool = False,
) -> SessionFuseResult:
    """Fuse branch-local session entries into the current working tree.

    The command is intentionally Memory Seed-aware instead of relying on Git's
    line-oriented merge drivers: branch-only entries must carry ``branch:
    <branch>``, existing entries are immutable, target paths normalize to the
    current month-grouped layout, and apply mode is guarded by an in-progress
    Git merge.
    """
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    if not (root / ".git").exists():
        return SessionFuseResult(changed=False, issues=["session fuse requires a Git repository"])
    if branch in {"main", "master"}:
        return SessionFuseResult(changed=False, issues=["source branch must not be main or master"])

    branch_commit = _resolve_commit(root, branch)
    if branch_commit is None:
        return SessionFuseResult(changed=False, issues=[f"source branch does not resolve to a commit: {branch}"])
    base_commit = _resolve_commit(root, base)
    if base_commit is None:
        return SessionFuseResult(changed=False, issues=[f"base ref does not resolve to a commit: {base}"])

    if apply:
        merge_heads = _merge_head_commits(root)
        if not merge_heads:
            return SessionFuseResult(changed=False, issues=["--apply requires an in-progress git merge"])
        if branch_commit not in merge_heads:
            return SessionFuseResult(
                changed=False,
                issues=[f"--apply source branch {branch} ({branch_commit}) is not listed in MERGE_HEAD"],
            )

    plan, issues = _plan_session_fuse(root, source_ref=branch, base_ref=base, source_label=branch)
    if issues:
        return SessionFuseResult(changed=False, issues=issues)
    assert plan is not None
    if not apply:
        return SessionFuseResult(
            changed=False,
            planned_entries=list(plan.planned_entries),
            planned_sidecars=list(plan.planned_sidecars),
            removed_sources=list(plan.removed_sources),
        )
    return _apply_session_fuse_plan(root, plan)


def session_merge_branch(
    cwd: str | Path = ".",
    *,
    branch: str,
    dry_run: bool = False,
) -> SessionMergeBranchResult:
    """Merge a task branch and fuse its branch-local session memory in one step.

    Wraps the documented integration dance (fuse dry-run, ``git merge --no-ff
    --no-commit``, ``session fuse --apply``, commit) into a single command so
    orchestrators cannot skip the fuse step and let a raw line-merge land
    session entries out of chronological order. Fails closed: any fuse issue
    aborts before the merge starts, and any non-session conflict leaves the
    merge in progress for manual resolution instead of guessing.
    """
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    if not (root / ".git").exists():
        return SessionMergeBranchResult(committed=False, issues=["session merge-branch requires a Git repository"])
    if branch in {"main", "master"}:
        return SessionMergeBranchResult(committed=False, issues=["source branch must not be main or master"])

    branch_commit = _resolve_commit(root, branch)
    if branch_commit is None:
        return SessionMergeBranchResult(committed=False, issues=[f"source branch does not resolve to a commit: {branch}"])
    base_commit = _resolve_commit(root, "HEAD")
    if base_commit is None:
        return SessionMergeBranchResult(committed=False, issues=["HEAD does not resolve to a commit"])

    if _merge_head_commits(root):
        return SessionMergeBranchResult(
            committed=False,
            merge_in_progress=True,
            issues=["a git merge is already in progress; finish or abort it before session merge-branch"],
        )
    code, status_out = _git_text(root, ("status", "--short"))
    if code != 0:
        return SessionMergeBranchResult(committed=False, issues=["could not read git status"])
    dirty_paths = [line.strip() for line in status_out.splitlines() if line.strip()]
    if dirty_paths:
        listing = "; ".join(dirty_paths[:10])
        if len(dirty_paths) > 10:
            listing += f"; ... ({len(dirty_paths) - 10} more)"
        return SessionMergeBranchResult(
            committed=False,
            issues=[f"working tree is not clean; commit or stash these paths first: {listing}"],
        )

    # Fuse dry-run gate: any session-memory problem (modified existing entry,
    # missing entry_id/branch provenance, duplicate ids, ...) aborts before the
    # git merge ever starts, so a fail-closed result has no merge state to clean.
    preview = session_fuse(root, branch=branch, base="HEAD", apply=False)
    if preview.issues:
        return SessionMergeBranchResult(committed=False, issues=list(preview.issues))

    result = SessionMergeBranchResult(
        committed=False,
        planned_entries=list(preview.planned_entries),
        planned_sidecars=list(preview.planned_sidecars),
        removed_sources=list(preview.removed_sources),
        already_present=list(preview.already_present),
    )
    if dry_run:
        return result

    merge_code, merge_out = _git_text(root, ("merge", "--no-ff", "--no-commit", branch))
    # Exit code 1 is ambiguous (conflict vs. real failure); the presence of
    # MERGE_HEAD is the reliable signal that a merge actually started.
    if not _merge_head_commits(root):
        if merge_code != 0:
            result.issues.append(f"git merge failed without starting a merge: {merge_out or '(no output)'}")
        # rc 0 with no MERGE_HEAD: branch is already merged into HEAD.
        return result

    code, conflicted = _git_lines(root, ("diff", "--name-only", "--diff-filter=U"))
    if code != 0:
        result.merge_in_progress = True
        result.issues.append("could not enumerate conflicted paths; merge left in progress")
        return result
    non_session = [
        path
        for path in conflicted
        if _session_doc_from_relative_path(path) is None and _diagram_doc_from_relative_path(path) is None
    ]
    if non_session:
        result.merge_in_progress = True
        result.conflicts = non_session
        return result

    # Reset every branch-touched session path that also exists on base back to
    # base's committed content. This guarantees the fuse apply below never sees
    # conflict markers, and it undoes any silent git auto-merge that landed
    # entries by physical position instead of timestamp without a conflict.
    changed_paths = _changed_session_paths(root, base_commit, branch_commit)
    if changed_paths is None:
        result.merge_in_progress = True
        result.issues.append(f"could not compute changed session files for branch {branch}; merge left in progress")
        return result
    base_paths = set(_git_ref_paths(root, base_commit))
    for rel_path in sorted(changed_paths & base_paths):
        code, _ = _git_text(root, ("checkout", base_commit, "--", rel_path))
        if code != 0:
            result.merge_in_progress = True
            result.issues.append(f"could not reset {rel_path} to base content; merge left in progress")
            return result

    applied = session_fuse(root, branch=branch, base=base_commit, apply=True)
    if applied.issues:
        result.merge_in_progress = True
        result.issues.extend(applied.issues)
        return result
    result.planned_entries = list(applied.planned_entries)
    result.planned_sidecars = list(applied.planned_sidecars)
    result.removed_sources = list(applied.removed_sources)
    result.already_present = list(applied.already_present)

    # The clean-tree precondition makes this sweep safe: the only changes under
    # sessions/ at this point are the merge itself plus fuse's writes/removals.
    code, _ = _git_text(root, ("add", "-A", "--", f"{MEMORY_DIR_NAME}/sessions"))
    if code != 0:
        result.merge_in_progress = True
        result.issues.append("could not stage fused session files; merge left in progress")
        return result

    code, remaining = _git_lines(root, ("diff", "--name-only", "--diff-filter=U"))
    if code != 0 or remaining:
        result.merge_in_progress = True
        listing = ", ".join(remaining) if remaining else "(unknown)"
        result.issues.append(f"unmerged paths remain after fuse; merge left in progress: {listing}")
        return result

    # Memory-Entry trailer stamping (approved plan, 2026-07-11): one trailer
    # per entry this fuse imports, appended below git's prepared merge message
    # so find_trailer_commits resolves each fused entry to this merge commit.
    # planned_entries is diffed against the base commit, so entries that
    # reached base earlier are never claimed; already_present only records
    # working-tree placement by git's own auto-merge and does not exclude.
    # Best-effort: a stamping failure must not abort an otherwise-clean merge.
    result.stamped_entries = _stamp_memory_entry_trailers(root, result.planned_entries)

    code, commit_out = _git_text(root, ("commit", "--no-edit"))
    if code != 0:
        result.merge_in_progress = bool(_merge_head_commits(root))
        result.issues.append(f"git commit failed: {commit_out or '(no output)'}")
        return result

    result.committed = True
    return result


def session_prepare_pr_branch(
    cwd: str | Path = ".",
    *,
    branch: str,
    base_branch: str | None = None,
    dry_run: bool = False,
) -> SessionPreparePrBranchResult:
    """Prepare a task branch for host-side PR merge by replaying chronology locally.

    The current worktree must already be on ``branch``. The command merges the
    target base branch into the task branch, resets any branch-touched session
    files back to base content, reapplies the branch's own session entries in
    chronological order, and commits the merge. This makes the later host merge
    trivially clean without teaching GitHub how to reorder append-only logs.
    """
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    if not (root / ".git").exists():
        return SessionPreparePrBranchResult(ready=False, issues=["session prepare-pr requires a Git repository"])
    if branch in {"main", "master"}:
        return SessionPreparePrBranchResult(ready=False, issues=["source branch must not be main or master"])

    current_branch = _current_branch_name(root)
    if not current_branch:
        return SessionPreparePrBranchResult(ready=False, issues=["detached HEAD; switch to the task branch before preparing a PR"])
    if current_branch != branch:
        return SessionPreparePrBranchResult(
            ready=False,
            issues=[f"current branch is {current_branch}; switch to {branch} before preparing a PR"],
            source_branch=current_branch,
        )

    dirty_paths = _git_dirty_paths(root)
    if dirty_paths is None:
        return SessionPreparePrBranchResult(ready=False, issues=["could not read git status"], source_branch=branch)
    if dirty_paths:
        return SessionPreparePrBranchResult(
            ready=False,
            source_branch=branch,
            issues=[_format_dirty_paths_issue(dirty_paths)],
        )

    if _merge_head_commits(root):
        return SessionPreparePrBranchResult(
            ready=False,
            merge_in_progress=True,
            source_branch=branch,
            issues=["a git merge is already in progress; finish or abort it before session prepare-pr"],
        )

    resolved_base_branch, base_ref, _base_commit, base_issue = _resolve_pr_base_branch(
        root,
        base_branch,
        source_branch=branch,
    )
    if base_issue:
        return SessionPreparePrBranchResult(ready=False, source_branch=branch, issues=[base_issue])
    assert resolved_base_branch is not None and base_ref is not None
    if resolved_base_branch == branch:
        return SessionPreparePrBranchResult(
            ready=False,
            base_branch=resolved_base_branch,
            source_branch=branch,
            issues=["source branch and PR base branch must differ"],
        )

    plan, issues = _plan_session_fuse(root, source_ref=branch, base_ref=base_ref, source_label=branch)
    if issues:
        return SessionPreparePrBranchResult(
            ready=False,
            base_branch=resolved_base_branch,
            source_branch=branch,
            issues=issues,
        )
    assert plan is not None

    result = SessionPreparePrBranchResult(
        ready=False,
        base_branch=resolved_base_branch,
        source_branch=branch,
        planned_entries=list(plan.planned_entries),
        planned_sidecars=list(plan.planned_sidecars),
        removed_sources=list(plan.removed_sources),
    )
    if dry_run:
        result.ready = True
        result.branch_head = plan.source_commit
        return result

    merge_code, merge_out = _git_text(root, ("merge", "--no-ff", "--no-commit", base_ref))
    if not _merge_head_commits(root):
        if merge_code != 0:
            result.issues.append(f"git merge failed without starting a merge: {merge_out or '(no output)'}")
            return result
        # Already up to date with base: nothing to rewrite or commit.
        result.ready = True
        result.changed = False
        result.branch_head = _resolve_commit(root, "HEAD")
        return result

    code, conflicted = _git_lines(root, ("diff", "--name-only", "--diff-filter=U"))
    if code != 0:
        result.merge_in_progress = True
        result.issues.append("could not enumerate conflicted paths; merge left in progress")
        return result
    non_session = [
        path
        for path in conflicted
        if _session_doc_from_relative_path(path) is None and _diagram_doc_from_relative_path(path) is None
    ]
    if non_session:
        result.merge_in_progress = True
        result.conflicts = non_session
        return result

    base_paths = set(_git_ref_paths(root, plan.base_commit))
    for rel_path in sorted(set(plan.changed_paths) & base_paths):
        code, _ = _git_text(root, ("checkout", plan.base_commit, "--", rel_path))
        if code != 0:
            result.merge_in_progress = True
            result.issues.append(f"could not reset {rel_path} to base content; merge left in progress")
            return result

    applied = _apply_session_fuse_plan(root, plan)
    if applied.issues:
        result.merge_in_progress = True
        result.issues.extend(applied.issues)
        return result
    result.planned_entries = list(applied.planned_entries)
    result.planned_sidecars = list(applied.planned_sidecars)
    result.removed_sources = list(applied.removed_sources)
    result.already_present = list(applied.already_present)

    code, _ = _git_text(root, ("add", "-A", "--", f"{MEMORY_DIR_NAME}/sessions"))
    if code != 0:
        result.merge_in_progress = True
        result.issues.append("could not stage prepared session files; merge left in progress")
        return result

    code, remaining = _git_lines(root, ("diff", "--name-only", "--diff-filter=U"))
    if code != 0 or remaining:
        result.merge_in_progress = True
        listing = ", ".join(remaining) if remaining else "(unknown)"
        result.issues.append(f"unmerged paths remain after branch prep; merge left in progress: {listing}")
        return result

    result.stamped_entries = _stamp_memory_entry_trailers(root, result.planned_entries)

    code, commit_out = _git_text(root, ("commit", "--no-edit"))
    if code != 0:
        result.merge_in_progress = bool(_merge_head_commits(root))
        result.issues.append(f"git commit failed: {commit_out or '(no output)'}")
        return result

    result.ready = True
    result.changed = True
    result.prep_commit = _resolve_commit(root, "HEAD")
    result.branch_head = result.prep_commit
    return result


def _gh_text(root: Path, args: Sequence[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            cwd=str(root),
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return 1, "", ""
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _gh_json(root: Path, args: Sequence[str]) -> tuple[int, object | None]:
    code, out, _err = _gh_text(root, args)
    if code != 0 or not out:
        return code, None
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, None


def _format_pr_body(
    *,
    source_branch: str,
    base_branch: str,
    planned_entries: Sequence[str],
    planned_sidecars: Sequence[str],
    removed_sources: Sequence[str],
    changed: bool,
) -> str:
    lines = [
        "## Summary",
        "",
        f"- Prepared `{source_branch}` for host-side merge into `{base_branch}`.",
        (
            "- Branch-side session chronology preparation ran and rewrote branch-local session files as needed."
            if changed else
            "- Branch-side session chronology preparation found nothing to rewrite."
        ),
        "",
        "## Session entries",
        "",
    ]
    if planned_entries:
        lines.extend(f"- `{planned}`" for planned in planned_entries)
    else:
        lines.append("- None.")
    lines.extend(["", "## Diagram sidecars", ""])
    if planned_sidecars:
        lines.extend(f"- `{planned}`" for planned in planned_sidecars)
    else:
        lines.append("- None.")
    lines.extend(["", "## Source path removals", ""])
    if removed_sources:
        lines.extend(f"- `{source}`" for source in removed_sources)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- `memory-seed session prepare-pr --branch {source_branch} --base-branch {base_branch}` passed.",
        ]
    )
    return "\n".join(lines)


def session_open_pr(
    cwd: str | Path = ".",
    *,
    branch: str,
    base_branch: str | None = None,
    remote_name: str = "origin",
    dry_run: bool = False,
) -> SessionOpenPrResult:
    """Prepare a branch, push it normally, and open a PR with `gh`.

    A declared `integration_mode: pr` authorizes this normal non-force path
    only. Missing origin/gh/auth or a failed fresh-base fetch fail closed before
    the branch is modified.
    """
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    if not (root / ".git").exists():
        return SessionOpenPrResult(opened=False, dry_run=dry_run, issues=["session open-pr requires a Git repository"])

    dirty_paths = _git_dirty_paths(root)
    if dirty_paths is None:
        return SessionOpenPrResult(opened=False, dry_run=dry_run, source_branch=branch, issues=["could not read git status"])
    if dirty_paths:
        return SessionOpenPrResult(
            opened=False,
            dry_run=dry_run,
            source_branch=branch,
            issues=[_format_dirty_paths_issue(dirty_paths)],
        )

    remote_url_code, remote_url = _git_text(root, ("remote", "get-url", remote_name))
    if remote_url_code != 0 or not remote_url:
        return SessionOpenPrResult(
            opened=False,
            dry_run=dry_run,
            source_branch=branch,
            remote_name=remote_name,
            issues=[f"missing remote '{remote_name}'; use local-merge or add that remote first"],
        )

    code, _out, _err = _gh_text(root, ("--version",))
    if code != 0:
        return SessionOpenPrResult(
            opened=False,
            dry_run=dry_run,
            source_branch=branch,
            remote_name=remote_name,
            remote_url=remote_url,
            issues=["gh is not available; use local-merge or install/authenticate gh first"],
        )
    code, _out, _err = _gh_text(root, ("auth", "status"))
    if code != 0:
        return SessionOpenPrResult(
            opened=False,
            dry_run=dry_run,
            source_branch=branch,
            remote_name=remote_name,
            remote_url=remote_url,
            issues=["gh is not authenticated; use local-merge or authenticate gh first"],
        )

    resolved_base_branch, _base_ref, _base_commit, base_issue = _resolve_pr_base_branch(
        root,
        base_branch,
        source_branch=branch,
    )
    if base_issue:
        return SessionOpenPrResult(
            opened=False,
            dry_run=dry_run,
            source_branch=branch,
            remote_name=remote_name,
            remote_url=remote_url,
            issues=[base_issue],
        )
    assert resolved_base_branch is not None
    if not dry_run:
        refresh_issue = _refresh_pr_base_branch(
            root,
            remote_name=remote_name,
            base_branch=resolved_base_branch,
        )
        if refresh_issue:
            return SessionOpenPrResult(
                opened=False,
                base_branch=resolved_base_branch,
                source_branch=branch,
                remote_name=remote_name,
                remote_url=remote_url,
                issues=[refresh_issue],
            )

    prepared = session_prepare_pr_branch(root, branch=branch, base_branch=base_branch, dry_run=dry_run)
    result = SessionOpenPrResult(
        opened=False,
        dry_run=dry_run,
        base_branch=prepared.base_branch,
        source_branch=prepared.source_branch or branch,
        remote_name=remote_name,
        remote_url=remote_url,
        planned_entries=list(prepared.planned_entries),
        planned_sidecars=list(prepared.planned_sidecars),
        removed_sources=list(prepared.removed_sources),
        already_present=list(prepared.already_present),
        stamped_entries=list(prepared.stamped_entries),
        prep_commit=prepared.prep_commit,
        branch_head=prepared.branch_head,
        conflicts=list(prepared.conflicts),
        issues=list(prepared.issues),
    )
    if result.issues or result.conflicts or not prepared.ready:
        return result

    assert result.base_branch is not None
    result.pr_title = f"Integrate {result.source_branch} into {result.base_branch}"
    result.pr_body = _format_pr_body(
        source_branch=result.source_branch or branch,
        base_branch=result.base_branch,
        planned_entries=result.planned_entries,
        planned_sidecars=result.planned_sidecars,
        removed_sources=result.removed_sources,
        changed=prepared.changed,
    )
    if dry_run:
        return result

    code, push_out = _git_text(root, ("push", "--set-upstream", remote_name, branch))
    if code != 0:
        result.issues.append(push_out or f"git push to {remote_name} failed")
        return result
    result.pushed = True
    result.branch_head = _resolve_commit(root, "HEAD")

    code, pr_out, pr_err = _gh_text(
        root,
        (
            "pr",
            "create",
            "--base",
            result.base_branch,
            "--head",
            branch,
            "--title",
            result.pr_title,
            "--body",
            result.pr_body,
        ),
    )
    if code != 0:
        result.issues.append(pr_err or pr_out or "gh pr create failed")
        return result
    result.pr_created = True
    result.pr_url = pr_out.splitlines()[-1].strip() if pr_out else None
    result.opened = True
    return result


def migrate_session_month_layout(cwd: str | Path = ".", dry_run: bool = False) -> SessionLayoutMigrationResult:
    """Migrate old flat/day session paths into the month-grouped layout.

    This is separate from ``migrate sessions-layout``: it preserves whether a
    source was flat or per-user and only changes the filesystem grouping. It is
    explicit, idempotent, backs up sources before removal, and blocks unsafe
    target merges with duplicate ``entry_id`` or per-user ``hash_id`` values.
    """
    runtime = resolve_runtime(cwd)
    target_root = runtime.workspace_root
    sessions_dir = runtime.memory_dir / "sessions"
    if not sessions_dir.is_dir():
        return SessionLayoutMigrationResult(changed=False)

    participant_slugs = {participant.slug for participant in read_project_participants(target_root)}
    sources: list[tuple[Path, Path, str]] = []
    issues: list[str] = []

    for doc in iter_session_documents(sessions_dir):
        if doc.layout == "legacy-flat":
            target = _session_flat_path(sessions_dir, doc.session_date)
        elif doc.layout == "per-user-day" and doc.user is not None:
            if participant_slugs and doc.user not in participant_slugs:
                issues.append(f"{doc.path.relative_to(sessions_dir).as_posix()}: unknown user '{doc.user}'")
                continue
            target = session_path(sessions_dir, doc.session_date, doc.user)
        else:
            continue
        if doc.path == target:
            continue
        sources.append((doc.path, target, "session"))

    for diagram_doc in iter_diagram_sidecar_documents(sessions_dir):
        if diagram_doc.layout != "legacy-diagram":
            if diagram_doc.malformed_reason:
                issues.append(f"{diagram_doc.path.relative_to(sessions_dir).as_posix()}: {diagram_doc.malformed_reason}")
            continue
        if diagram_doc.malformed_reason or not diagram_doc.diagram_date:
            issues.append(f"{diagram_doc.path.relative_to(sessions_dir).as_posix()}: {diagram_doc.malformed_reason}")
            continue
        target = sessions_dir / "diagrams" / diagram_doc.diagram_date[:7] / f"{diagram_doc.diagram_date}.md"
        if diagram_doc.path != target:
            sources.append((diagram_doc.path, target, "diagram"))

    planned = sorted(
        f"{source.relative_to(sessions_dir).as_posix()} -> {target.relative_to(sessions_dir).as_posix()}"
        for source, target, _ in sources
    )
    if issues:
        return SessionLayoutMigrationResult(changed=False, planned=planned, issues=issues)
    if not sources:
        return SessionLayoutMigrationResult(changed=False, planned=planned)

    for source, target, kind in sources:
        try:
            source_text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(f"{source.relative_to(sessions_dir).as_posix()}: unreadable ({exc})")
            continue
        if not target.exists():
            continue
        try:
            target_text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(f"{target.relative_to(sessions_dir).as_posix()}: unreadable ({exc})")
            continue
        source_ids = set(_ENTRY_ID_RE.findall(source_text))
        target_ids = set(_ENTRY_ID_RE.findall(target_text))
        duplicates = sorted(source_ids & target_ids)
        if duplicates:
            issues.append(
                f"{target.relative_to(sessions_dir).as_posix()}: duplicate entry_id(s) block safe merge: "
                + ", ".join(duplicates)
            )
        if kind == "session":
            source_hash = _hash_id_from_file_frontmatter(source_text)
            target_hash = _hash_id_from_file_frontmatter(target_text)
            if source_hash and target_hash and source_hash == target_hash:
                issues.append(
                    f"{target.relative_to(sessions_dir).as_posix()}: duplicate hash_id blocks safe merge: {source_hash}"
                )
        if kind == "session" and target.exists() and not _flat_session_entries(source_text):
            issues.append(f"{source.relative_to(sessions_dir).as_posix()}: no session entry headings to append")

    if issues:
        return SessionLayoutMigrationResult(changed=False, planned=planned, issues=issues)
    if dry_run:
        return SessionLayoutMigrationResult(changed=False, planned=planned)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backed_up: list[Path] = []
    migrated: list[str] = []

    for source, _, _ in sources:
        backed_up.append(_backup_session_source(target_root, sessions_dir, source, timestamp))

    for source, target, kind in sorted(sources, key=lambda item: item[1].relative_to(sessions_dir).as_posix()):
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if kind == "session":
                _append_session_entries(target, _source_entries_for_append(source))
            else:
                existing = target.read_text(encoding="utf-8")
                addition = source.read_text(encoding="utf-8").rstrip()
                separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
                write_text_file(target, existing + separator + addition + "\n")
        else:
            _copy_text_file(source, target)
        source.unlink()
        migrated.append(target.relative_to(sessions_dir).as_posix())

    return SessionLayoutMigrationResult(
        changed=bool(migrated or backed_up),
        planned=planned,
        migrated=migrated,
        backed_up=backed_up,
    )


SEED_FILES = [
    SeedFile(SEED_ROOT / "AGENTS.md", "AGENTS.md"),
    SeedFile(SEED_ROOT / "CLAUDE.md", "CLAUDE.md", agent="claude"),
    SeedFile(SEED_ROOT / "GEMINI.md", "GEMINI.md", agent="gemini"),
    SeedFile(SEED_ROOT / ".github" / "copilot-instructions.md", ".github/copilot-instructions.md", agent="copilot"),
    # End-of-session routine command shortcuts (the routine itself lives in
    # agent-rules.md). Seeded only for agents with a verified repo-level custom-
    # command mechanism: Claude (.claude/commands/*.md) and Gemini
    # (.gemini/commands/*.toml). Codex/Cursor invoke the routine via agent-rules.md.
    SeedFile(SEED_ROOT / ".claude" / "commands" / "esr.md", ".claude/commands/esr.md", agent="claude"),
    SeedFile(SEED_ROOT / ".gemini" / "commands" / "esr.toml", ".gemini/commands/esr.toml", agent="gemini"),
    # Start-of-session orientation command shortcuts (routine in
    # .memory-seed/skills/orientation.md; Codex/Cursor invoke it via agent-rules.md).
    SeedFile(SEED_ROOT / ".claude" / "commands" / "situate.md", ".claude/commands/situate.md", agent="claude"),
    SeedFile(SEED_ROOT / ".gemini" / "commands" / "situate.toml", ".gemini/commands/situate.toml", agent="gemini"),
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
    # Deploy-once project-local topic vocabulary (destination is runtime-local
    # under .memory-seed/, so update never overwrites project curation).
    SeedFile(SEED_ROOT / MEMORY_DIR_NAME / "topics.yaml", ".memory-seed/topics.yaml"),
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
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "agent_collaboration.md",
        ".memory-seed/skills/agent_collaboration.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "history_retrieval.md",
        ".memory-seed/skills/history_retrieval.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "session_logging.md",
        ".memory-seed/skills/session_logging.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "compact_mermaid_diagrams.md",
        ".memory-seed/skills/compact_mermaid_diagrams.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "orientation.md",
        ".memory-seed/skills/orientation.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "end_of_turn.md",
        ".memory-seed/skills/end_of_turn.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "memory_hygiene.md",
        ".memory-seed/skills/memory_hygiene.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "risk_signaling.md",
        ".memory-seed/skills/risk_signaling.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "skill_architecture.md",
        ".memory-seed/skills/skill_architecture.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "proposal_lifecycle.md",
        ".memory-seed/skills/proposal_lifecycle.md",
    ),
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "subproject_runtime.md",
        ".memory-seed/skills/subproject_runtime.md",
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
        SEED_ROOT / MEMORY_DIR_NAME / "skills" / "docx_render_windows.md",
        ".memory-seed/skills/docx_render_windows.md",
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
    SeedFile(
        SEED_ROOT / MEMORY_DIR_NAME / "hooks" / "prepare-commit-msg.py",
        ".memory-seed/hooks/prepare-commit-msg.py",
    ),
]

# Shim written into .git/hooks/ so git runs the repo-tracked trailer stamper.
# Non-Windows installs use this portable shell delegator; Windows installs use
# an absolute-Python wrapper from _git_prepare_commit_msg_shim().
_GIT_PREPARE_COMMIT_MSG_SHIM = """#!/bin/sh
# Installed by memory-seed (hooks install): stamps Memory-Entry trailers for
# staged session entries. Delegates to the repo-tracked script; never blocks.
root="$(git rev-parse --show-toplevel)" || exit 0
script="$root/.memory-seed/hooks/prepare-commit-msg.py"
[ -f "$script" ] || exit 0
if command -v python3 >/dev/null 2>&1; then
  python3 "$script" "$@" || exit 0
else
  python "$script" "$@" || exit 0
fi
exit 0
"""


def _git_prepare_commit_msg_shim() -> str:
    if os.name != "nt":
        return _GIT_PREPARE_COMMIT_MSG_SHIM
    # Git for Windows normally runs shell hooks, but some locked-down Windows
    # sessions fail before the shell script starts. An absolute-Python shebang
    # avoids sh/env and delegates to the repo-tracked standalone script.
    return f"""#!{sys.executable}
# Installed by memory-seed (hooks install): stamps Memory-Entry trailers for
# staged session entries. Delegates to the repo-tracked script; never blocks.
import runpy
import subprocess
import sys
from pathlib import Path


def main():
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
    except Exception:
        return 0
    if proc.returncode != 0:
        return 0
    root = proc.stdout.strip()
    if not root:
        return 0
    script = Path(root) / ".memory-seed" / "hooks" / "prepare-commit-msg.py"
    if not script.is_file():
        return 0
    old_argv = sys.argv[:]
    try:
        sys.argv = [str(script), *sys.argv[1:]]
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit:
        return 0
    except Exception:
        return 0
    finally:
        sys.argv = old_argv
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""


def _git_common_hooks_dir(root: Path) -> Path | None:
    git_dir_lines = _git_capture(root, "rev-parse", "--git-common-dir")
    if not git_dir_lines:
        return None
    git_dir = Path(git_dir_lines[0].strip())
    if not git_dir.is_absolute():
        git_dir = root / git_dir
    return git_dir / "hooks"


def git_hook_status(cwd: Path | str = ".") -> GitHookStatus:
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    hooks_dir = _git_common_hooks_dir(root)
    if hooks_dir is None:
        return GitHookStatus(
            is_git_repo=False,
            state="no-git",
            message="No git repository found.",
        )

    hook_path = hooks_dir / "prepare-commit-msg"
    hook_path_str = hook_path.as_posix()
    if not hook_path.exists():
        return GitHookStatus(
            is_git_repo=True,
            state="missing",
            message="Memory-Entry trailer hook is missing. Run `memory-seed hooks repair`.",
            hook_path=hook_path_str,
            repairable=True,
        )

    existing = read_text_file(hook_path)
    if "Installed by memory-seed" not in existing:
        return GitHookStatus(
            is_git_repo=True,
            state="foreign",
            message=(
                "A foreign prepare-commit-msg hook is installed; Memory Seed will not overwrite it. "
                "Merge the Memory Seed hook manually if commit trailers are required."
            ),
            hook_path=hook_path_str,
        )

    shim = _git_prepare_commit_msg_shim()
    if existing != shim:
        return GitHookStatus(
            is_git_repo=True,
            state="stale-managed",
            message="Memory Seed prepare-commit-msg hook is stale. Run `memory-seed hooks repair`.",
            hook_path=hook_path_str,
            managed=True,
            repairable=True,
        )

    if os.name == "nt":
        first_line = existing.splitlines()[0] if existing.splitlines() else ""
        if first_line.startswith("#!") and not Path(first_line[2:]).exists():
            return GitHookStatus(
                is_git_repo=True,
                state="broken-python",
                message=(
                    "Memory Seed prepare-commit-msg hook points at a missing Python executable. "
                    "Run `memory-seed hooks repair`."
                ),
                hook_path=hook_path_str,
                managed=True,
                repairable=True,
            )

    script = root / MEMORY_DIR_NAME / "hooks" / "prepare-commit-msg.py"
    if not script.is_file():
        return GitHookStatus(
            is_git_repo=True,
            state="script-missing",
            message=(
                "Memory Seed git hook is installed, but .memory-seed/hooks/prepare-commit-msg.py "
                "is missing. Run `memory-seed update`."
            ),
            hook_path=hook_path_str,
            managed=True,
        )

    return GitHookStatus(
        is_git_repo=True,
        state="current",
        message="Memory Seed prepare-commit-msg hook is current.",
        hook_path=hook_path_str,
        managed=True,
        current=True,
    )


def install_git_hooks(cwd: Path | str = ".") -> list[str]:
    """Write the prepare-commit-msg shim into .git/hooks (idempotent).

    Returns the list of actions taken; empty when there is no git repository.
    An existing hook that memory-seed did not write is left untouched and
    reported instead of overwritten.
    """
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    # --git-common-dir, not --git-dir: in a linked worktree git resolves hooks
    # from the COMMON dir - installing there covers every linked worktree.
    hooks_dir = _git_common_hooks_dir(root)
    if hooks_dir is None:
        return []
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "prepare-commit-msg"
    shim = _git_prepare_commit_msg_shim()
    if hook_path.exists():
        existing = read_text_file(hook_path)
        if "Installed by memory-seed" in existing:
            if existing == shim:
                return [f"prepare-commit-msg: already installed ({hook_path})"]
            try:
                write_text_file(hook_path, shim)
            except OSError as exc:
                return [f"prepare-commit-msg: NOT refreshed - could not write {hook_path}: {exc}"]
            return [f"prepare-commit-msg: refreshed ({hook_path})"]
        return [
            f"prepare-commit-msg: NOT installed - a hook that memory-seed did not write "
            f"already exists at {hook_path}; merge the shim manually"
        ]
    try:
        write_text_file(hook_path, shim)
    except OSError as exc:
        return [f"prepare-commit-msg: NOT installed - could not write {hook_path}: {exc}"]
    try:
        hook_path.chmod(0o755)
    except OSError:
        pass
    return [f"prepare-commit-msg: installed ({hook_path})"]

CORE_SKILL_NAMES = (
    "session_logging.md",
    "history_retrieval.md",
    "orientation.md",
    "end_of_turn.md",
    "memory_hygiene.md",
    "risk_signaling.md",
    "memory_doctor.md",
    "memory_consolidation.md",
    "subproject_runtime.md",
)

SKILL_PROFILES: dict[str, SkillProfile] = {
    "coding": SkillProfile(
        "Source exploration, local validation, and durable data-structure work.",
        ("code_search.md", "local_compilation.md", "data_architecture.md"),
    ),
    "security": SkillProfile(
        "Security-sensitive review, secret handling, and permission-risk triage.",
        ("security_triage.md",),
    ),
    "collaboration": SkillProfile(
        "Multi-agent, worktree, branch, and handoff coordination.",
        ("agent_collaboration.md",),
    ),
    "planning": SkillProfile(
        "Proposal inbox, todo, completed, and reference lifecycle management.",
        ("proposal_lifecycle.md",),
    ),
    "release": SkillProfile(
        "Package publishing, tags, changelog, and release verification.",
        ("release_publishing.md",),
    ),
    "documents": SkillProfile(
        "Document ingestion, Office editing, and Windows DOCX render QA.",
        ("document_ingestion.md", "office_document_editing.md", "docx_render_windows.md"),
    ),
    "marketing": SkillProfile(
        "Conversion copy, launch copy, CTAs, and product-positioning text.",
        ("copywriter-conversion.md",),
    ),
    "diagramming": SkillProfile(
        "Compact Mermaid layout plus Mermaid-first D2 selection guidance.",
        ("compact_mermaid_diagrams.md",),
    ),
    "governance": SkillProfile(
        "Skill architecture, trigger registry, profile, and seed/live parity maintenance.",
        ("skill_architecture.md",),
    ),
}

OPTIONAL_SKILL_NAMES = tuple(
    sorted({skill for profile in SKILL_PROFILES.values() for skill in profile.skills})
)

SKILL_DESCRIPTIONS = {
    "agent_collaboration.md": "Coordinate branch, worktree, and multi-agent handoff workflows.",
    "code_search.md": "Use precise repository search and symbol lookup before broad reads.",
    "compact_mermaid_diagrams.md": "Produce compact Mermaid diagrams and decide when D2 is justified.",
    "copywriter-conversion.md": "Write conversion-focused product and launch copy.",
    "data_architecture.md": "Handle durable schema, cache, ranking, and retrieval-contract changes.",
    "docx_render_windows.md": "Render DOCX pages to images for Windows visual QA.",
    "document_ingestion.md": "Convert binary documents into readable Markdown/text.",
    "local_compilation.md": "Validate local build, test, package, and CLI behavior.",
    "office_document_editing.md": "Create or edit Office documents programmatically.",
    "proposal_lifecycle.md": "Move proposal docs through inbox, todo, completed, and reference states.",
    "release_publishing.md": "Prepare and verify package releases.",
    "security_triage.md": "Triage security, privacy, and destructive-operation risks.",
    "skill_architecture.md": "Design and maintain skill/profile boundaries and trigger registry entries.",
}

PROPOSAL_LIFECYCLE_ARTIFACTS = (
    "docs/inbox/.gitkeep",
    "docs/todo/.gitkeep",
    "docs/todo/completed/.gitkeep",
    "docs/reference/.gitkeep",
)

_CLAUDE_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py"
_CODEX_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --codex"
_CURSOR_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --cursor"
_GEMINI_HOOK_COMMAND = "python3 .memory-seed/hooks/session-log-check.py --gemini"

_CLAUDE_RETRIEVAL_COMMAND = "python3 .memory-seed/hooks/memory-retrieval-check.py"
_CODEX_RETRIEVAL_COMMAND = "python3 .memory-seed/hooks/memory-retrieval-check.py --codex"
_CURSOR_RETRIEVAL_COMMAND = "python3 .memory-seed/hooks/memory-retrieval-check.py --cursor"
_GEMINI_RETRIEVAL_COMMAND = "python3 .memory-seed/hooks/memory-retrieval-check.py --gemini"

# SessionStart orientation hook: routes agents through AGENTS.md and injects the
# five newest session entries directly so agents do not lean on semantic search
# (which can bury the newest entry) to establish current state. Fires once per
# session, unlike the per-prompt reminder.
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
    "memory-seed: Before any work, locate the nearest applicable AGENTS.md by "
    "walking upward from the current directory, read it first, and follow every "
    "instruction and routing path it defines. Then read the five newest applicable "
    "entries directly from the latest .memory-seed/sessions/ files to establish "
    "current project context. Do NOT use memory_search/semantic search to find the "
    "most recent work - use it only for topical 'why was X decided / what do we "
    "know about Y' questions."
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
    digest = hashlib.sha256(metadata.encode("utf-8")).digest()[:10]
    return f"mse_{_base32_crockford(digest)}"


def _base32_crockford(data: bytes) -> str:
    value = int.from_bytes(data, "big")
    chars: list[str] = []
    total_chars = (len(data) * 8 + 4) // 5
    for shift in range((total_chars - 1) * 5, -1, -5):
        chars.append(_CROCKFORD_BASE32_ALPHABET[(value >> shift) & 0b11111])
    return "".join(chars)


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
            data = read_json_file(config_path)
        except (json.JSONDecodeError, OSError):
            data = {}

    for group in data.get("hooks", {}).get(event, []):
        for hook in group.get("hooks", []):
            if hook.get("command") == command:
                return False
            if script_name in (hook.get("command") or ""):
                hook["command"] = command
                write_json_file(config_path, data)
                return True

    data.setdefault("hooks", {}).setdefault(event, []).append(
        {"hooks": [{"type": "command", "command": command}]}
    )

    write_json_file(config_path, data)

    return True


def _merge_cursor_event_hook(config_path: Path, event: str, command: str, script_name: str) -> bool:
    """Upsert a command hook under hooks.<event> in Cursor's flat list form.

    Identifies our entry by script_name. Updates in place if command changed.
    Returns True if the file was written, False if already current.
    """
    data: dict = {}
    if config_path.exists():
        try:
            data = read_json_file(config_path)
        except (json.JSONDecodeError, OSError):
            data = {}

    data.setdefault("version", 1)
    for entry in data.get("hooks", {}).get(event, []):
        if entry.get("command") == command:
            return False
        if script_name in (entry.get("command") or ""):
            entry["command"] = command
            write_json_file(config_path, data)
            return True

    data.setdefault("hooks", {}).setdefault(event, []).append({"command": command})

    write_json_file(config_path, data)

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
            data = read_json_file(mcp_path)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("mcpServers", {}).get(_MCP_SERVER_KEY, {})
    if existing == expected:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("mcpServers", {})[_MCP_SERVER_KEY] = expected

    write_json_file(mcp_path, data)

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
        data = read_json_file(settings_path)
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

    write_json_file(settings_path, data)

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
        data = read_json_file(settings_path)
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

    write_json_file(settings_path, data)
    return True


def _merge_cursor_mcp(target_root: Path) -> bool:
    """Upsert the memory-seed-mcp stdio server entry in .cursor/mcp.json."""
    mcp_path = target_root / ".cursor" / "mcp.json"
    expected = {"command": _MCP_SERVER_COMMAND, "args": _MCP_SERVER_ARGS}

    data: dict = {}
    if mcp_path.exists():
        try:
            data = read_json_file(mcp_path)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("mcpServers", {}).get(_MCP_SERVER_KEY, {})
    if existing == expected:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("mcpServers", {})[_MCP_SERVER_KEY] = expected

    write_json_file(mcp_path, data)

    return True


def _merge_gemini_mcp(target_root: Path) -> bool:
    """Upsert the memory-seed-mcp stdio server entry in .gemini/settings.json."""
    settings_path = target_root / ".gemini" / "settings.json"
    expected = {"command": _MCP_SERVER_COMMAND, "args": _MCP_SERVER_ARGS}

    data: dict = {}
    if settings_path.exists():
        try:
            data = read_json_file(settings_path)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("mcpServers", {}).get(_MCP_SERVER_KEY, {})
    if existing == expected:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("mcpServers", {})[_MCP_SERVER_KEY] = expected

    write_json_file(settings_path, data)

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
            data = read_json_file(mcp_path)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("mcpServers", {}).get(_MCP_SERVER_KEY, {})
    if existing == _COPILOT_MCP_EXPECTED:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("mcpServers", {})[_MCP_SERVER_KEY] = dict(_COPILOT_MCP_EXPECTED)

    write_json_file(mcp_path, data)

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
            data = read_json_file(mcp_path)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = data.get("servers", {}).get(_MCP_SERVER_KEY, {})
    if existing == _VSCODE_MCP_EXPECTED:
        return False
    is_ours = existing.get("command") in _OWN_MCP_COMMANDS or "memory-seed-mcp" in existing.get("args", [])
    if existing and not is_ours:
        return False  # a different server is using this key; don't overwrite

    data.setdefault("servers", {})[_MCP_SERVER_KEY] = dict(_VSCODE_MCP_EXPECTED)

    write_json_file(mcp_path, data)

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
            data = read_json_file(config_path)
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
            write_json_file(config_path, data)
            return True

    entries.append({"type": "prompt", "prompt": _COPILOT_STARTUP_PROMPT})

    write_json_file(config_path, data)

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

    write_text_file(config_path, new_text)
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
        data = read_json_file(path)
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
    write_json_file(path, data)


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
        lines = read_text_file(path).splitlines(keepends=True)
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
        write_text_file(path, new_text)
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
            if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_-]*\s*:", line):
                in_block = False
                continue
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


def read_project_participants(target_root: Path) -> list[ProjectParticipant]:
    """Return participant registry entries from .memory-seed/project.yaml.

    Fail-open like the agent-selection parser: absent, unreadable, malformed, or
    invalid participant entries return an empty list instead of breaking init,
    update, doctor, or migration dry-runs.
    """
    path = _project_config_path(target_root)
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    participants: list[ProjectParticipant] = []
    in_participants = False
    current: dict[str, str] | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            current = None
            return
        slug = current.get("slug", "").strip()
        initials = current.get("initials", "").strip()
        display_name = current.get("display_name", "").strip() or None
        if SESSION_USER_SLUG_RE.match(slug) and initials:
            participants.append(ProjectParticipant(slug=slug, initials=initials, display_name=display_name))
        current = None

    for raw in lines:
        line = raw.rstrip()
        if re.match(r"^participants\s*:", line):
            in_participants = True
            current = None
            continue
        if not in_participants:
            continue
        if line and not line[0].isspace():
            flush()
            break
        item_match = re.match(r"^\s*-\s*slug\s*:\s*(.+)$", line)
        if item_match:
            flush()
            current = {"slug": item_match.group(1).strip().strip("'\"")}
            continue
        field_match = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$", line)
        if field_match and current is not None:
            current[field_match.group(1)] = field_match.group(2).strip().strip("'\"")
    else:
        flush()

    return participants


INTEGRATION_MODES = ("local-merge", "pr")
DEFAULT_INTEGRATION_MODE = "local-merge"


def read_integration_mode(target_root: Path) -> str:
    """Return the project's declared integration mode from .memory-seed/project.yaml.

    ``integration_mode:`` is a single top-level scalar governing how branch work
    lands (configurable-integration-mode-plan.md):

    - ``local-merge`` (default): branch work merges into local ``main`` via
      ``memory-seed session merge-branch``; nothing is pushed.
    - ``pr``: branch work integrates through the hosting provider - the branch is
      prepared, pushed, and a PR is opened; the host performs the merge.

    Fail-open to ``local-merge``: an absent file/key, an unreadable file, or an
    unrecognised value all yield the default, so legacy and unconfigured projects
    behave exactly as before. A declared ``pr`` mode is the durable authorization
    for the normal push->PR flow; force-push and other destructive git operations
    stay gated regardless of mode.
    """
    path = _project_config_path(target_root)
    if not path.exists():
        return DEFAULT_INTEGRATION_MODE
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return DEFAULT_INTEGRATION_MODE
    for raw in lines:
        match = re.match(r"^integration_mode\s*:\s*(.+)$", raw.rstrip())
        if match:
            value = match.group(1).strip().strip("'\"")
            return value if value in INTEGRATION_MODES else DEFAULT_INTEGRATION_MODE
    return DEFAULT_INTEGRATION_MODE


def read_declared_integration_mode(target_root: Path) -> str | None:
    path = _project_config_path(target_root)
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read existing {path}; integration mode was not changed") from exc
    for raw in lines:
        match = re.match(r"^integration_mode\s*:\s*(.+)$", raw.rstrip())
        if not match:
            continue
        value = match.group(1).strip().strip("'\"")
        return value if value in INTEGRATION_MODES else None
    return None


def _replace_top_level_scalar(text: str, key: str, value: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    replaced = False
    for line in lines:
        if re.match(rf"^{re.escape(key)}\s*:", line):
            out.append(f"{key}: {value}")
            replaced = True
            continue
        out.append(line)
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}: {value}")
    return "\n".join(out).rstrip() + "\n"


def write_integration_mode(target_root: Path, mode: str) -> None:
    if mode not in INTEGRATION_MODES:
        raise ValueError(f"Unknown integration mode: {mode}. Valid modes: {', '.join(INTEGRATION_MODES)}.")
    path = _project_config_path(target_root)
    text = ""
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"cannot read existing {path}; integration mode was not changed") from exc
    if not text.strip():
        text = f"schema_version: 1\nproject_id: {target_root.name}\n"
    text = _replace_top_level_scalar(text, "integration_mode", mode)
    write_text_file(path, text)


def suggest_integration_mode(target_root: Path) -> tuple[str, str]:
    """Heuristic init-time suggestion for the first integration_mode value.

    Fail open to ``local-merge`` whenever GitHub/provider signals are absent,
    unreadable, unauthenticated, or not obviously team-oriented. This suggestion
    never mutates an existing project by itself; callers must still confirm.
    """
    if not (target_root / ".git").exists():
        return DEFAULT_INTEGRATION_MODE, "no git repository detected"
    code, remote_url = _git_text(target_root, ("remote", "get-url", "origin"))
    if code != 0 or not remote_url:
        return DEFAULT_INTEGRATION_MODE, "no origin remote detected"
    code, _out, _err = _gh_text(target_root, ("--version",))
    if code != 0:
        return DEFAULT_INTEGRATION_MODE, "gh is unavailable"
    code, _out, _err = _gh_text(target_root, ("auth", "status"))
    if code != 0:
        return DEFAULT_INTEGRATION_MODE, "gh is unauthenticated"
    code, repo_payload = _gh_json(
        target_root,
        ("repo", "view", "--json", "nameWithOwner,defaultBranchRef,branchProtectionRules"),
    )
    repo_name = None
    if isinstance(repo_payload, dict):
        repo_name = repo_payload.get("nameWithOwner")
        if repo_payload.get("branchProtectionRules"):
            default_branch = (
                repo_payload.get("defaultBranchRef", {}).get("name")
                if isinstance(repo_payload.get("defaultBranchRef"), dict) else None
            )
            branch_note = f" on {default_branch}" if default_branch else ""
            return "pr", f"GitHub reports branch protection{branch_note}"
    code, pr_payload = _gh_json(target_root, ("pr", "list", "--limit", "1", "--json", "number"))
    if isinstance(pr_payload, list) and pr_payload:
            return "pr", "existing pull requests were found"
    if isinstance(repo_name, str) and repo_name:
        code, collaborator_payload = _gh_json(
            target_root,
            ("api", f"repos/{repo_name}/collaborators?per_page=2"),
        )
        if isinstance(collaborator_payload, list) and len(collaborator_payload) > 1:
            return "pr", "GitHub reports more than one collaborator"
    return DEFAULT_INTEGRATION_MODE, "no team PR signals were detected"


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
    write_text_file(path, text)


def _parse_agent_list(value: str) -> set[str]:
    """Parse a comma/space-separated agent list; raise ValueError on unknown slugs."""
    tokens = [t.strip().lower() for t in re.split(r"[,\s]+", value) if t.strip()]
    if not tokens or tokens == ["all"]:
        return set(KNOWN_AGENTS)
    if "none" in tokens:
        if tokens == ["none"]:
            return set()
        raise ValueError("Agent selection 'none' cannot be combined with agent names.")
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
    > all agents (preserves the zero-arg / non-TTY default). `none` is an explicit
    opt-out to the zero-agent state. Pure/testable: the CLI reads the prompt and
    passes the raw string as `prompt_response`.
    """
    if cli_value:
        return _parse_agent_list(cli_value)
    if isatty and prompt_response is not None and prompt_response.strip():
        return _parse_agent_list(prompt_response)
    return set(KNOWN_AGENTS)


def _skill_seed_file_map() -> dict[str, SeedFile]:
    prefix = f"{MEMORY_DIR_NAME}/skills/"
    return {
        Path(seed_file.destination).name: seed_file
        for seed_file in SEED_FILES
        if seed_file.destination.startswith(prefix) and Path(seed_file.destination).name != "index.md"
    }


def _normalise_skill_name(value: str) -> str:
    token = value.strip().replace("\\", "/")
    if not token:
        raise ValueError("Skill name cannot be empty.")
    token = token.rsplit("/", 1)[-1]
    if not token.endswith(".md"):
        token += ".md"
    valid = set(CORE_SKILL_NAMES) | set(OPTIONAL_SKILL_NAMES)
    if token not in valid:
        raise ValueError(
            f"Unknown skill: {value}. Valid skills: {', '.join(sorted(valid))}."
        )
    return token


def _normalise_profile_names(values: set[str] | Sequence[str] | None) -> set[str]:
    if not values:
        return set()
    profiles = {value.strip().lower() for value in values if value.strip()}
    unknown = sorted(profiles - set(SKILL_PROFILES))
    if unknown:
        raise ValueError(
            f"Unknown skill profile(s): {', '.join(unknown)}. "
            f"Valid profiles: {', '.join(sorted(SKILL_PROFILES))}."
        )
    return profiles


def _skills_from_profiles(profiles: set[str]) -> set[str]:
    selected: set[str] = set()
    for profile in profiles:
        selected.update(SKILL_PROFILES[profile].skills)
    return selected


def _resolve_requested_optional_skills(
    *,
    skill_profiles: set[str] | Sequence[str] | None = None,
    skills: set[str] | Sequence[str] | None = None,
    exclude_skills: set[str] | Sequence[str] | None = None,
    all_skills: bool = False,
) -> tuple[set[str], set[str], set[str]]:
    profiles = _normalise_profile_names(skill_profiles)
    selected = set(OPTIONAL_SKILL_NAMES) if all_skills else _skills_from_profiles(profiles)
    for skill in skills or ():
        selected.add(_normalise_skill_name(skill))
    for skill in exclude_skills or ():
        selected.discard(_normalise_skill_name(skill))
    selected &= set(OPTIONAL_SKILL_NAMES)
    ignored = set(OPTIONAL_SKILL_NAMES) - selected
    return profiles, selected, ignored


def _read_top_level_list(text: str, key: str, valid: set[str] | None = None) -> tuple[bool, set[str]]:
    values: set[str] = set()
    saw_key = False
    in_block = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(rf"^\s*{re.escape(key)}\s*:", line):
            saw_key = True
            inline = line.split(":", 1)[1].strip()
            if inline.startswith("[") and inline.endswith("]"):
                for tok in inline[1:-1].split(","):
                    value = tok.strip().strip("'\"")
                    if value and (valid is None or value in valid):
                        values.add(value)
                in_block = False
            else:
                in_block = True
            continue
        if in_block:
            if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_-]*\s*:", line):
                in_block = False
                continue
            m = re.match(r"^\s*-\s*(.+)$", line)
            if m:
                value = m.group(1).strip().strip("'\"")
                if value and (valid is None or value in valid):
                    values.add(value)
                continue
            if line and not line[0].isspace():
                in_block = False
    return saw_key, values


def _extract_yaml_block(text: str, key: str) -> str | None:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}\s*:", line):
            end = idx + 1
            while end < len(lines):
                candidate = lines[end]
                if candidate and not candidate[0].isspace():
                    break
                end += 1
            return "\n".join(lines[idx:end])
    return None


def read_project_skill_selection(target_root: Path) -> SkillSelection:
    path = _project_config_path(target_root)
    text = ""
    if path.exists():
        try:
            text = read_text_file(path)
        except OSError:
            text = ""

    skills_block = _extract_yaml_block(text, "skills") if text else None
    if skills_block is not None:
        _saw_profiles, profiles = _read_top_level_list(skills_block, "profiles", set(SKILL_PROFILES))
        _saw_selected, selected = _read_top_level_list(skills_block, "selected", set(OPTIONAL_SKILL_NAMES))
        _saw_ignored, ignored = _read_top_level_list(skills_block, "ignored", set(OPTIONAL_SKILL_NAMES))
        selected.update(_skills_from_profiles(profiles))
        ignored = (set(OPTIONAL_SKILL_NAMES) - selected) if not ignored else ignored
        ignored -= selected
        return SkillSelection(profiles=profiles, selected=selected, ignored=ignored, explicit=True)

    installed = _installed_optional_skills(target_root)
    return SkillSelection(
        profiles=set(),
        selected=installed,
        ignored=set(OPTIONAL_SKILL_NAMES) - installed,
        explicit=False,
    )


def _replace_top_level_block(text: str, key: str, block: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    replaced = False
    while i < len(lines):
        if re.match(rf"^{re.escape(key)}\s*:", lines[i]):
            out.extend(block.splitlines())
            replaced = True
            i += 1
            while i < len(lines):
                candidate = lines[i]
                if candidate and not candidate[0].isspace():
                    break
                i += 1
            continue
        out.append(lines[i])
        i += 1
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.extend(block.splitlines())
    return "\n".join(out).rstrip() + "\n"


def _write_project_skills(
    target_root: Path,
    *,
    profiles: set[str],
    selected: set[str],
    ignored: set[str] | None = None,
) -> None:
    path = _project_config_path(target_root)
    ignored = (set(OPTIONAL_SKILL_NAMES) - selected) if ignored is None else set(ignored)
    ignored -= selected
    block_lines = ["skills:", "  profiles:"]
    block_lines.extend(f"    - {profile}" for profile in sorted(profiles))
    block_lines.append("  selected:")
    block_lines.extend(f"    - {skill}" for skill in sorted(selected))
    block_lines.append("  ignored:")
    block_lines.extend(f"    - {skill}" for skill in sorted(ignored))
    block = "\n".join(block_lines)

    text = ""
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""
    if not text.strip():
        text = f"schema_version: 1\nproject_id: {target_root.name}\n"
    text = _replace_top_level_block(text, "skills", block)
    write_text_file(path, text)


def _installed_optional_skills(target_root: Path) -> set[str]:
    skills_dir = target_root / MEMORY_DIR_NAME / "skills"
    return {
        skill
        for skill in OPTIONAL_SKILL_NAMES
        if (skills_dir / skill).exists()
    }


def _selected_seed_files(
    target_root: Path,
    selected_agents_set: set[str],
    selected_optional: set[str],
) -> list[SeedFile]:
    wanted_skills = set(CORE_SKILL_NAMES) | set(selected_optional) | {"index.md"}
    selected: list[SeedFile] = []
    for seed_file in SEED_FILES:
        if seed_file.agent is not None and seed_file.agent not in selected_agents_set:
            continue
        if seed_file.destination.startswith(f"{MEMORY_DIR_NAME}/skills/"):
            if Path(seed_file.destination).name not in wanted_skills:
                continue
        selected.append(seed_file)
    return selected


def _registry_blocks_from_seed() -> tuple[list[str], dict[str, list[str]], list[str]]:
    registry_path = SEED_ROOT / MEMORY_DIR_NAME / "skills" / "index.md"
    lines = read_text_file(registry_path).splitlines()
    header: list[str] = []
    footer: list[str] = []
    blocks: dict[str, list[str]] = {}
    i = 0
    while i < len(lines):
        if lines[i].strip() == "skills:":
            header = lines[: i + 1]
            i += 1
            break
        i += 1
    while i < len(lines):
        match = re.match(r"^\s*-\s*skill:\s*(\S+)\s*$", lines[i])
        if not match:
            footer = lines[i:]
            break
        skill = match.group(1)
        block = [lines[i]]
        i += 1
        while i < len(lines) and not re.match(r"^\s*-\s*skill:\s*(\S+)\s*$", lines[i]):
            if lines[i].startswith("```"):
                footer = lines[i:]
                i = len(lines)
                break
            block.append(lines[i])
            i += 1
        blocks[skill] = block
    return header, blocks, footer


def _rewrite_skill_registry(target_root: Path, installed_skills: set[str]) -> None:
    header, blocks, footer = _registry_blocks_from_seed()
    ordered = [
        Path(seed_file.destination).name
        for seed_file in SEED_FILES
        if seed_file.destination.startswith(f"{MEMORY_DIR_NAME}/skills/")
        and Path(seed_file.destination).name in installed_skills
    ]
    lines = list(header)
    for skill in ordered:
        block = blocks.get(skill)
        if block:
            lines.extend(block)
    lines.extend(footer)
    registry = target_root / MEMORY_DIR_NAME / "skills" / "index.md"
    write_text_file(registry, "\n".join(lines).rstrip() + "\n")


def _create_skill_artifacts(target_root: Path, selected_optional: set[str]) -> list[str]:
    created: list[str] = []
    if "proposal_lifecycle.md" not in selected_optional:
        return created
    for rel in PROPOSAL_LIFECYCLE_ARTIFACTS:
        path = target_root / rel
        if not path.exists():
            write_text_file(path, "")
            created.append(rel)
    return created


def _remove_empty_skill_artifacts(target_root: Path, skill: str) -> list[str]:
    removed: list[str] = []
    if skill != "proposal_lifecycle.md":
        return removed
    for rel in PROPOSAL_LIFECYCLE_ARTIFACTS:
        path = target_root / rel
        if path.exists() and path.is_file() and path.stat().st_size == 0:
            path.unlink()
            removed.append(rel)
    return removed


def init_project(
    cwd: str | Path = ".",
    dry_run: bool = False,
    force: bool = False,
    agents: set[str] | None = None,
    skill_profiles: set[str] | Sequence[str] | None = None,
    skills: set[str] | Sequence[str] | None = None,
    exclude_skills: set[str] | Sequence[str] | None = None,
    all_skills: bool = False,
) -> InitResult:
    target_root = Path(cwd).resolve()
    selected = agents if agents is not None else set(KNOWN_AGENTS)
    profiles, selected_optional, ignored_optional = _resolve_requested_optional_skills(
        skill_profiles=skill_profiles,
        skills=skills,
        exclude_skills=exclude_skills,
        all_skills=all_skills,
    )
    seed_files = _selected_seed_files(target_root, selected, selected_optional)
    planned = [seed_file.destination for seed_file in seed_files]
    if "proposal_lifecycle.md" in selected_optional:
        planned.extend(PROPOSAL_LIFECYCLE_ARTIFACTS)
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

    if selected != set(KNOWN_AGENTS):
        write_project_agents(target_root, selected)
        cfg = MEMORY_DIR_NAME + "/project.yaml"
        if cfg not in created:
            created.append(cfg)
    _write_project_skills(
        target_root,
        profiles=profiles,
        selected=selected_optional,
        ignored=ignored_optional,
    )
    cfg = MEMORY_DIR_NAME + "/project.yaml"
    if cfg not in created:
        created.append(cfg)

    _rewrite_skill_registry(target_root, set(CORE_SKILL_NAMES) | selected_optional)
    for artifact in _create_skill_artifacts(target_root, selected_optional):
        if artifact not in created:
            created.append(artifact)

    # Default-on at init (user decision, cheap-tooling P3): a fresh project
    # gets the Memory-Entry trailer stamper immediately; existing checkouts
    # opt in explicitly via `memory-seed hooks install`. No-op without git.
    for action in install_git_hooks(target_root):
        created.append(f"git-hook: {action}")

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
    skill_selection = read_project_skill_selection(target_root)
    seed_files = _selected_seed_files(target_root, selected, skill_selection.selected)
    planned = [seed_file.destination for seed_file in seed_files]
    if "proposal_lifecycle.md" in skill_selection.selected:
        planned.extend(PROPOSAL_LIFECYCLE_ARTIFACTS)

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

    _rewrite_skill_registry(target_root, set(CORE_SKILL_NAMES) | skill_selection.selected)
    for artifact in _create_skill_artifacts(target_root, skill_selection.selected):
        if artifact not in created:
            created.append(artifact)

    # Commit trailers are core provenance. Refresh only Memory Seed-managed
    # hooks (or install when absent); foreign hooks remain untouched.
    for action in install_git_hooks(target_root):
        if ": installed" in action or ": refreshed" in action:
            created.append(f"git-hook: {action}")

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


def skill_status(cwd: str | Path = ".") -> SkillStatus:
    target_root = Path(cwd).resolve()
    selection = read_project_skill_selection(target_root)
    installed = _installed_optional_skills(target_root)
    return SkillStatus(
        core=sorted(CORE_SKILL_NAMES),
        installed_optional=sorted(installed),
        selected_optional=sorted(selection.selected),
        ignored=sorted(set(OPTIONAL_SKILL_NAMES) - installed),
        available_optional=sorted(OPTIONAL_SKILL_NAMES),
        profiles={name: list(profile.skills) for name, profile in sorted(SKILL_PROFILES.items())},
        profile_descriptions={name: profile.description for name, profile in sorted(SKILL_PROFILES.items())},
        descriptions={skill: SKILL_DESCRIPTIONS[skill] for skill in sorted(SKILL_DESCRIPTIONS)},
    )


def add_skill(cwd: str | Path = ".", name: str = "") -> dict:
    target_root = Path(cwd).resolve()
    profile_name = name.strip().lower()
    selection = read_project_skill_selection(target_root)
    profiles = set(selection.profiles)
    if profile_name in SKILL_PROFILES:
        profiles.add(profile_name)
        to_add = set(SKILL_PROFILES[profile_name].skills)
    else:
        try:
            skill = _normalise_skill_name(name)
        except ValueError as exc:
            valid = sorted(set(SKILL_PROFILES) | set(OPTIONAL_SKILL_NAMES))
            raise ValueError(
                f"Unknown skill or profile: {name}. Valid options: {', '.join(valid)}."
            ) from exc
        if skill in CORE_SKILL_NAMES:
            return {"changed": False, "message": f"Core skill '{skill}' is always installed.", "created": []}
        to_add = {skill}

    seed_map = _skill_seed_file_map()
    created: list[str] = []
    for skill in sorted(to_add):
        seed_file = seed_map[skill]
        destination = target_root / seed_file.destination
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            _copy_text_file(seed_file.source, destination)
            created.append(seed_file.destination)

    selected_optional = selection.selected | to_add
    ignored = set(OPTIONAL_SKILL_NAMES) - selected_optional
    _write_project_skills(target_root, profiles=profiles, selected=selected_optional, ignored=ignored)
    _rewrite_skill_registry(target_root, set(CORE_SKILL_NAMES) | selected_optional)
    for artifact in _create_skill_artifacts(target_root, selected_optional):
        created.append(artifact)

    changed = bool(created) or bool(to_add - selection.selected) or profiles != selection.profiles
    label = profile_name if profile_name in SKILL_PROFILES else next(iter(to_add))
    return {"changed": changed, "message": f"Added skill/profile '{label}'.", "created": created}


def remove_skill(cwd: str | Path = ".", skill: str = "") -> dict:
    target_root = Path(cwd).resolve()
    skill_name = _normalise_skill_name(skill)
    if skill_name in CORE_SKILL_NAMES:
        raise ValueError(f"Cannot remove core skill: {skill_name}.")
    if skill_name not in OPTIONAL_SKILL_NAMES:
        raise ValueError(f"Unknown optional skill: {skill_name}.")

    selection = read_project_skill_selection(target_root)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backed_up: list[str] = []
    removed: list[str] = []

    paths_to_backup = [
        target_root / MEMORY_DIR_NAME / "skills" / skill_name,
        target_root / MEMORY_DIR_NAME / "skills" / "index.md",
    ]
    for path in paths_to_backup:
        if path.exists():
            _ensure_backup_gitignore(target_root)
            rel = path.relative_to(target_root)
            backup_relative = Path(MEMORY_DIR_NAME) / "backups" / timestamp / rel
            backup_path = target_root / backup_relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            _copy_text_file(path, backup_path)
            backed_up.append(backup_relative.as_posix())

    skill_path = target_root / MEMORY_DIR_NAME / "skills" / skill_name
    if skill_path.exists():
        skill_path.unlink()
        removed.append(f"{MEMORY_DIR_NAME}/skills/{skill_name}")

    selected_optional = set(selection.selected)
    selected_optional.discard(skill_name)
    profiles = {
        profile
        for profile in selection.profiles
        if skill_name not in SKILL_PROFILES[profile].skills
    }
    ignored = set(OPTIONAL_SKILL_NAMES) - selected_optional
    _write_project_skills(target_root, profiles=profiles, selected=selected_optional, ignored=ignored)
    _rewrite_skill_registry(target_root, set(CORE_SKILL_NAMES) | selected_optional)
    for artifact in _remove_empty_skill_artifacts(target_root, skill_name):
        removed.append(artifact)

    return {
        "changed": bool(removed) or skill_name in selection.selected,
        "message": f"Removed skill '{skill_name}'.",
        "removed": removed,
        "backed_up": backed_up,
    }


def doctor(cwd: str | Path = ".") -> DoctorResult:
    target_root = Path(cwd).resolve()
    missing: list[str] = []
    version_mismatches: list[dict[str, str]] = []

    # Only check files for the project's selected agents (ALL when unconfigured),
    # so a deselected agent's intentionally-absent files are not flagged missing.
    selected = selected_agents(target_root)
    skill_selection = read_project_skill_selection(target_root)
    seed_files = _selected_seed_files(target_root, selected, skill_selection.selected)

    for seed_file in seed_files:
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

    hook_status = git_hook_status(target_root)
    if hook_status.is_git_repo and hook_status.state != "current":
        warnings.append(f"Git hook status: {hook_status.message}")

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

    # Local-user / participant-registry consistency (non-fatal). Only checked
    # when a local user is actually configured — an unconfigured user is not a
    # problem doctor should nag about (the SessionStart hook offers identity
    # setup once, separately). A configured user with no matching participants:
    # entry means user_initials can't be resolved for multi-user tooling
    # (migrate sessions-layout, links check) even though session_target()
    # still works.
    local_user = read_local_user(target_root)
    if local_user is not None:
        participant_slugs = {p.slug for p in read_project_participants(target_root)}
        if local_user not in participant_slugs:
            warnings.append(
                f"Local user '{local_user}' (.memory-seed/local.yaml) has no matching "
                "entry in .memory-seed/project.yaml's participants: list. Add one with "
                f"slug: {local_user} so multi-user tooling can resolve initials for it."
            )

    # Session integrity summary (non-fatal). The full report — with each
    # offending file and value, and a CI-usable non-zero exit — is
    # `memory-seed links check`; doctor only surfaces the count.
    links = check_session_links(target_root)
    link_errors = [issue for issue in links.issues if issue.severity == "error"]
    if link_errors:
        warnings.append(
            f"Session memory has {len(link_errors)} integrity issue(s) "
            "(duplicate/dangling IDs or per-user frontmatter problems). Run "
            "`memory-seed links check` for the full report."
        )

    encoding_issues = scan_text_encoding(target_root) + scan_implicit_text_io(target_root)
    if encoding_issues:
        warnings.append(
            f"Project text has {len(encoding_issues)} encoding issue(s) "
            "(UTF-8/LF/NFC drift, likely mojibake, or implicit Python text I/O). Run "
            "`memory-seed encoding check` for the full report."
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

    dated_files: list[tuple[str, str, str, Path]] = []
    for doc in iter_session_documents(sessions_dir):
        date_str = doc.session_date
        if cutoff is not None:
            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if file_date < cutoff:
                continue
        display_path = doc.path.relative_to(sessions_dir).as_posix()
        heading_key = date_str if doc.layout == "legacy-flat" else display_path
        dated_files.append((date_str, display_path, heading_key, doc.path))

    if not dated_files:
        return CompactResult(
            sessions_scanned=[],
            headings={},
            full_text="",
            date_range=None,
        )

    headings: dict[str, list[str]] = {}
    full_parts: list[str] = []

    for date_str, display_path, heading_key, path in dated_files:
        content = path.read_text(encoding="utf-8")
        headings[heading_key] = HEADING_RE.findall(content)
        full_parts.append(content)

    return CompactResult(
        sessions_scanned=[display_path for _, display_path, _, _ in dated_files],
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
        (
            destination.startswith(f"{MEMORY_DIR_NAME}/")
            and destination not in reusable_runtime_files
        )
        or destination.startswith(".agents/")
        # The Gemini command is TOML and cannot carry a memory-system-version
        # marker for update gating, so it is deploy-once (the routine it points
        # to, in agent-rules.md, updates normally). The Claude command is .md
        # with frontmatter, so it stays version-tracked and refreshes on update.
        or destination.startswith(".gemini/commands/")
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
    text = read_text_file(path)
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
        write_text_file(path, new_text)
        return True
    write_text_file(path, text.rstrip("\n") + "\n\n" + stanza + "\n")
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
    write_text_file(destination, read_text_file(source))


def _ensure_backup_gitignore(target_root: Path) -> None:
    _ensure_gitignore_entry(target_root, BACKUP_IGNORE_ENTRY)


def _ensure_gitignore_entry(target_root: Path, entry: str) -> None:
    gitignore = target_root / ".gitignore"
    if gitignore.exists():
        content = read_text_file(gitignore)
    else:
        content = ""

    lines = content.splitlines()
    if entry in lines:
        return

    prefix = content
    if prefix and not prefix.endswith(("\n", "\r\n")):
        prefix += "\n"
    write_text_file(gitignore, prefix + entry + "\n")
