"""Session orientation preflight (``memory-seed situate``).

Network-free, read-only. Reconciles the LOCAL authoritative facts an agent needs
to orient before work, so a session starts from ground truth instead of a stale
in-context snapshot:

- git: current branch, uncommitted count, and commits ahead of the integration
  ref's remote (unpushed local work) + the declared ``integration_mode``
- newest session entry: the most recent session-log heading, resolved through the
  same layout-aware reader the SessionStart hook uses (legacy-flat / per-user-day
  / month-dir), so orientation never re-derives "latest" and drifts from the hook
- worktrees: per-worktree posture (shared with ``esr``); stale sweep candidates
  are the merged-and-clean ones
- version: the LOCAL ``pyproject`` version and whether ``CHANGELOG.md`` carries a
  non-empty ``## Unreleased`` section - reported as neutral facts, not a verdict

The authoritative *published* version check (PyPI) deliberately lives in the
orientation routine (``.memory-seed/skills/orientation.md``) and the per-agent
command shims, NOT here: this keeps the CLI network-free (fast, offline-safe,
trivially testable, like ``esr``). "Verify, don't assume" is satisfied by the
routine reading ground truth; it does not require the CLI to fetch it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import iter_session_documents, read_integration_mode, resolve_runtime
from .esr import WorktreePosture, _git_lines, _integration_ref, _worktree_posture

_ENTRY_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+-\s*(.+?)\s*$", re.MULTILINE)
_PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_PYPROJECT_NAME_RE = re.compile(r'^name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


@dataclass
class SituateReport:
    git_available: bool = False
    branch: str | None = None
    dirty: int | None = None
    ahead: int | None = None
    ahead_ref: str | None = None
    integration_mode: str = "local-merge"
    newest_session_path: str | None = None
    newest_session_date: str | None = None
    newest_entry: str | None = None
    worktrees_available: bool = False
    worktrees: list[WorktreePosture] = field(default_factory=list)
    local_version: str | None = None
    changelog_unreleased: bool | None = None
    is_memory_seed_repo: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "git": {
                "available": self.git_available,
                "branch": self.branch,
                "dirty": self.dirty,
                "ahead": self.ahead,
                "ahead_ref": self.ahead_ref,
            },
            "integration_mode": self.integration_mode,
            "newest_session": {
                "path": self.newest_session_path,
                "date": self.newest_session_date,
                "entry": self.newest_entry,
            },
            "worktrees": {
                "available": self.worktrees_available,
                "entries": [
                    {
                        "path": w.path,
                        "branch": w.branch,
                        "ahead": w.ahead,
                        "dirty": w.dirty,
                        "is_primary": w.is_primary,
                        "stale_candidate": w.stale_candidate,
                    }
                    for w in self.worktrees
                ],
            },
            "version": {
                "local": self.local_version,
                "changelog_unreleased": self.changelog_unreleased,
                "is_memory_seed_repo": self.is_memory_seed_repo,
            },
        }


def _git_state(root: Path) -> tuple[bool, str | None, int | None, int | None, str | None]:
    """(available, branch, dirty, ahead, ahead_ref). available=False when not a git repo."""
    branch_lines = _git_lines(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch_lines is None:
        return False, None, None, None, None
    branch = branch_lines[0].strip() if branch_lines and branch_lines[0].strip() else None
    status_lines = _git_lines(root, "status", "--short")
    dirty = len([line for line in status_lines if line.strip()]) if status_lines is not None else None
    ahead: int | None = None
    ahead_ref: str | None = None
    integration = _integration_ref(root)
    if integration:
        remote = f"origin/{integration}"
        if _git_lines(root, "rev-parse", "--verify", "--quiet", remote) is not None:
            ahead_ref = remote
        else:
            ahead_ref = integration
        counts = _git_lines(root, "rev-list", "--count", f"{ahead_ref}..HEAD")
        if counts and counts[0].strip().isdigit():
            ahead = int(counts[0].strip())
    return True, branch, dirty, ahead, ahead_ref


def _newest_session(memory_dir: Path) -> tuple[str | None, str | None, str | None]:
    """(path, date, last-entry-heading) for the newest session document, or all None."""
    docs = list(iter_session_documents(memory_dir / "sessions"))
    if not docs:
        return None, None, None
    # Newest by session date, then by path so the pick is deterministic on ties.
    newest = max(docs, key=lambda d: (d.session_date, str(d.path)))
    entry: str | None = None
    try:
        text = Path(newest.path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""
    matches = list(_ENTRY_HEADING_RE.finditer(text))
    if matches:
        ts, title = matches[-1].groups()
        entry = f"{ts} - {title}"
    try:
        rel = Path(newest.path).relative_to(memory_dir.parent).as_posix()
    except ValueError:
        rel = str(newest.path)
    return rel, newest.session_date, entry


def _local_version(root: Path) -> tuple[str | None, bool]:
    """(pyproject version, is_memory_seed_repo). Both degrade to (None, False)."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return None, False
    try:
        text = pyproject.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, False
    version_match = _PYPROJECT_VERSION_RE.search(text)
    name_match = _PYPROJECT_NAME_RE.search(text)
    version = version_match.group(1) if version_match else None
    is_seed_repo = bool(name_match and name_match.group(1) == "memory-seed")
    return version, is_seed_repo


def _changelog_unreleased(root: Path) -> bool | None:
    """True/False if CHANGELOG has a non-empty ``## Unreleased`` section; None if no CHANGELOG."""
    changelog = root / "CHANGELOG.md"
    if not changelog.is_file():
        return None
    try:
        text = changelog.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "## unreleased":
            for follow in lines[i + 1:]:
                stripped = follow.strip()
                if stripped.startswith("## "):
                    return False  # next heading reached with nothing between
                if stripped:
                    return True
            return False
    return False


def situate_report(cwd: str | Path = ".") -> SituateReport:
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    report = SituateReport()
    report.integration_mode = read_integration_mode(root)
    (
        report.git_available,
        report.branch,
        report.dirty,
        report.ahead,
        report.ahead_ref,
    ) = _git_state(root)
    report.newest_session_path, report.newest_session_date, report.newest_entry = _newest_session(
        runtime.memory_dir
    )
    report.worktrees_available, report.worktrees = _worktree_posture(root)
    report.local_version, report.is_memory_seed_repo = _local_version(root)
    report.changelog_unreleased = _changelog_unreleased(root)
    return report


def format_situate_report(report: SituateReport) -> str:
    lines: list[str] = ["Situate — repo orientation (local facts; verify published version separately)", ""]

    lines.append("## Git")
    if not report.git_available:
        lines.append("Not a git repository (or git unavailable).")
    else:
        dirty = "?" if report.dirty is None else report.dirty
        state = "clean" if report.dirty == 0 else f"{dirty} uncommitted"
        lines.append(f"- branch: {report.branch or 'detached'}  ({state})")
        if report.ahead is not None and report.ahead_ref:
            lines.append(f"- {report.ahead} commit(s) ahead of {report.ahead_ref}")
    lines.append("")

    lines.append("## Integration mode")
    if report.integration_mode == "pr":
        lines.append("pr — integrate via push + pull request (push authorized for that flow).")
    else:
        lines.append("local-merge — integrate via `session merge-branch` into local main; do NOT push without instruction.")
    lines.append("")

    lines.append("## Newest session entry")
    if not report.newest_session_path:
        lines.append("No session logs found.")
    else:
        lines.append(f"- {report.newest_session_path}")
        lines.append(f"  last entry: {report.newest_entry or '(no entries yet)'}")
        lines.append("  Read this file directly for current state — do not rely on memory_search for 'latest'.")
    lines.append("")

    lines.append("## Version")
    if report.local_version:
        lines.append(f"- local (pyproject): {report.local_version}")
    else:
        lines.append("- local (pyproject): not found")
    if report.changelog_unreleased is True:
        lines.append("- CHANGELOG has a non-empty `## Unreleased` section (unreleased work present).")
    elif report.changelog_unreleased is False:
        lines.append("- CHANGELOG `## Unreleased` is empty/absent.")
    lines.append("- Verify the PUBLISHED version from the source of truth (never assume): "
                 "`curl -s https://pypi.org/pypi/memory-seed/json | python -c \"import sys,json;print(json.load(sys.stdin)['info']['version'])\"`"
                 + (" — this IS the memory-seed source repo, so local > published means an unreleased tranche." if report.is_memory_seed_repo else "."))
    lines.append("")

    lines.append("## Worktrees")
    if not report.worktrees_available:
        lines.append("Not a git repository (or git unavailable).")
    elif len(report.worktrees) <= 1:
        lines.append("Only the primary checkout.")
    else:
        for wt in report.worktrees:
            if wt.is_primary:
                lines.append(f"- {wt.path}  [{wt.branch or 'detached'}]  primary")
                continue
            ahead = "?" if wt.ahead is None else wt.ahead
            dirty = "?" if wt.dirty is None else wt.dirty
            marker = "  STALE CANDIDATE (merged + clean)" if wt.stale_candidate else ""
            lines.append(f"- {wt.path}  [{wt.branch or 'detached'}]  ahead: {ahead}  dirty: {dirty}{marker}")

    return "\n".join(lines)
