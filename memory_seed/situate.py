"""Session orientation preflight (``memory-seed situate``).

Network-free, read-only. Reconciles the LOCAL authoritative facts an agent needs
to orient before work, so a session starts from ground truth instead of a stale
in-context snapshot:

- location: which checkout this actually is - the primary/root checkout or an
  agent-owned worktree - MEASURED from the caller's cwd via ``worktree_guard``.
  An agent can be told by a harness banner or a task packet that it is working in
  an isolated worktree when no such worktree was ever created; git then resolves
  every command up to the primary checkout, and the agent writes into shared
  state believing it is isolated. This section is the always-printed statement of
  ground truth that such a claim can be checked against.
- git: current branch, uncommitted count, and commits ahead of the integration
  ref's remote (unpushed local work) + the declared ``integration_mode``
- newest session entry: the most recent session-log heading, resolved through the
  same layout-aware reader the SessionStart hook uses (legacy-flat / per-user-day
  / month-dir), so orientation never re-derives "latest" and drifts from the hook
- worktrees: per-worktree posture (shared with ``esr``); stale sweep candidates
  are the merged-and-clean ones
- version: the LOCAL ``pyproject`` version and whether ``CHANGELOG.md`` carries a
  non-empty ``## Unreleased`` section - reported as neutral facts, not a verdict

The authoritative *published* version check (PyPI) remains outside this command:
release/version tasks invoke it from the orientation routine, while ordinary
startup stays network-free, fast, and offline-safe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import (
    CommitCadence,
    iter_session_documents,
    read_integration_mode,
    read_merge_trigger,
    resolve_runtime,
    session_target,
    worktree_guard,
)
from .esr import WorktreePosture, _git_lines, _integration_ref, _worktree_posture

_ENTRY_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+-\s*(.+?)\s*$", re.MULTILINE)
_PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_PYPROJECT_NAME_RE = re.compile(r'^name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

# Deterministic, tokenizer-independent routing boundary for startup context.
# The host agent applies the route; situate never invokes a model or network.
SESSION_CONTEXT_COMPRESSION_THRESHOLD_CHARS = 12_000


@dataclass(frozen=True)
class SessionContributor:
    path: str
    user: str
    entries: int


@dataclass
class SituateReport:
    checkout_classification: str | None = None
    checkout_path: str | None = None
    repo_root: str | None = None
    git_available: bool = False
    branch: str | None = None
    dirty: int | None = None
    ahead: int | None = None
    ahead_ref: str | None = None
    integration_mode: str = "local-merge"
    merge_trigger: str = "automatic"
    newest_session_path: str | None = None
    newest_session_date: str | None = None
    newest_session_user: str | None = None
    newest_entry: str | None = None
    newest_session_characters: int | None = None
    newest_session_bytes: int | None = None
    newest_session_entries: int | None = None
    newest_session_read_error: str | None = None
    compression_threshold_characters: int = SESSION_CONTEXT_COMPRESSION_THRESHOLD_CHARS
    context_route: str | None = None
    session_contributors: list[SessionContributor] = field(default_factory=list)
    worktrees_available: bool = False
    worktrees: list[WorktreePosture] = field(default_factory=list)
    local_version: str | None = None
    changelog_unreleased: bool | None = None
    is_memory_seed_repo: bool = False
    cadence: CommitCadence | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": {
                "classification": self.checkout_classification,
                "checkout": self.checkout_path,
                "repo_root": self.repo_root,
                "is_primary": self.checkout_classification == "root-checkout",
            },
            "git": {
                "available": self.git_available,
                "branch": self.branch,
                "dirty": self.dirty,
                "ahead": self.ahead,
                "ahead_ref": self.ahead_ref,
            },
            "integration_mode": self.integration_mode,
            "merge_trigger": self.merge_trigger,
            "newest_session": {
                "path": self.newest_session_path,
                "date": self.newest_session_date,
                "user": self.newest_session_user,
                "entry": self.newest_entry,
                "characters": self.newest_session_characters,
                "bytes": self.newest_session_bytes,
                "entries": self.newest_session_entries,
                "read_error": self.newest_session_read_error,
                "compression_threshold_characters": self.compression_threshold_characters,
                "context_route": self.context_route,
                "contributors": [
                    {"path": item.path, "user": item.user, "entries": item.entries}
                    for item in self.session_contributors
                ],
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
            "cadence": self.cadence.to_dict() if self.cadence is not None else None,
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


def _relative_session_path(path: Path, memory_dir: Path) -> str:
    try:
        return path.relative_to(memory_dir.parent).as_posix()
    except ValueError:
        return str(path)


def _entry_count(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    return len(_ENTRY_HEADING_RE.findall(text))


def _newest_session(
    memory_dir: Path,
    *,
    active_user: str | None,
) -> tuple[
    str | None,
    str | None,
    str | None,
    str | None,
    int | None,
    int | None,
    int | None,
    str | None,
    str | None,
    list[SessionContributor],
]:
    """Return latest applicable session measurements and co-contributor facts."""
    all_docs = list(iter_session_documents(memory_dir / "sessions"))
    docs = [doc for doc in all_docs if doc.user == active_user]
    if not docs:
        return (None, None, active_user, None, None, None, None, None, None, [])

    newest = max(docs, key=lambda d: (d.session_date, str(d.path)))
    entry: str | None = None
    characters: int | None = None
    byte_count: int | None = None
    entry_count: int | None = None
    read_error: str | None = None
    route: str | None = None
    try:
        raw = newest.path.read_bytes()
        byte_count = len(raw)
        text = raw.decode("utf-8")
        characters = len(text)
        matches = list(_ENTRY_HEADING_RE.finditer(text))
        entry_count = len(matches)
        if matches:
            ts, title = matches[-1].groups()
            entry = f"{ts} - {title}"
        route = (
            "direct"
            if characters <= SESSION_CONTEXT_COMPRESSION_THRESHOLD_CHARS
            else "summarize"
        )
    except UnicodeDecodeError:
        read_error = "invalid UTF-8"
    except OSError as exc:
        read_error = f"unreadable: {exc.__class__.__name__}"

    contributors: list[SessionContributor] = []
    if active_user is not None:
        for doc in all_docs:
            if doc.session_date != newest.session_date or doc.user in (None, active_user):
                continue
            contributors.append(
                SessionContributor(
                    path=_relative_session_path(doc.path, memory_dir),
                    user=doc.user,
                    entries=_entry_count(doc.path),
                )
            )
    contributors.sort(key=lambda item: (item.user, item.path))
    return (
        _relative_session_path(newest.path, memory_dir),
        newest.session_date,
        newest.user,
        entry,
        characters,
        byte_count,
        entry_count,
        read_error,
        route,
        contributors,
    )


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


def situate_report(cwd: str | Path = ".", *, explicit_user: str | None = None) -> SituateReport:
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    report = SituateReport()
    # Classify from the RAW cwd, never from ``root``. The two diverge only when
    # the runtime dir is ABSENT from a worktree checkout: ``resolve_runtime`` then
    # walks up past the worktree to the primary checkout, and classifying from
    # that root reports a correctly-isolated agent as sitting in the shared tree.
    # Measured: guard(cwd)=owned-worktree vs guard(root)=root-checkout. It does
    # NOT hide the phantom case (both say root-checkout there) - the cost is a
    # false alarm at a correct setup, and a section that cries wolf is one agents
    # learn to skip. Pinned by
    # ``test_location_is_classified_from_cwd_not_from_the_resolved_runtime_root``,
    # which fails if these arguments are swapped.
    guard = worktree_guard(cwd, write_intent=False)
    report.checkout_classification = guard.classification
    report.checkout_path = str(guard.worktree_path) if guard.worktree_path else None
    report.repo_root = str(guard.repo_root) if guard.repo_root else None
    report.cadence = guard.cadence
    report.integration_mode = read_integration_mode(root)
    report.merge_trigger = read_merge_trigger(root)
    (
        report.git_available,
        report.branch,
        report.dirty,
        report.ahead,
        report.ahead_ref,
    ) = _git_state(root)
    active_user = session_target(cwd, explicit_user=explicit_user, create=False).user
    (
        report.newest_session_path,
        report.newest_session_date,
        report.newest_session_user,
        report.newest_entry,
        report.newest_session_characters,
        report.newest_session_bytes,
        report.newest_session_entries,
        report.newest_session_read_error,
        report.context_route,
        report.session_contributors,
    ) = _newest_session(runtime.memory_dir, active_user=active_user)
    report.worktrees_available, report.worktrees = _worktree_posture(root)
    report.local_version, report.is_memory_seed_repo = _local_version(root)
    report.changelog_unreleased = _changelog_unreleased(root)
    return report


def format_situate_report(report: SituateReport) -> str:
    lines: list[str] = ["Situate — repo orientation (local facts; verify published version separately)", ""]

    # First, because it names the checkout every fact below describes.
    lines.append("## Location")
    classification = report.checkout_classification
    if classification in (None, "not-a-worktree"):
        lines.append("- checkout: not inside a git worktree.")
    elif classification == "root-checkout":
        lines.append(f"- checkout: {report.checkout_path}")
        lines.append("- this is the PRIMARY checkout - shared, NOT an isolated worktree.")
        lines.append("  Measured from this cwd, not declared. If a harness banner or task packet said")
        lines.append("  you are in a worktree, it is wrong: no worktree would resolve to this path.")
        lines.append("  Before non-trivial writes, create one - see `agent_collaboration.md`.")
    else:
        label = {
            "owned-worktree": "agent-owned worktree",
            "foreign-worktree": "worktree owned by ANOTHER agent",
            "unmanaged-worktree": "worktree outside every configured agent namespace",
        }.get(classification, classification)
        lines.append(f"- checkout: {report.checkout_path}  ({label})")
        lines.append(f"- repository root: {report.repo_root}")
        if classification != "owned-worktree":
            lines.append("  Writing here is a shared-control-plane hazard - check `agent_collaboration.md`.")
    lines.append("")

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

    lines.append("## Checkpoint cadence")
    if report.cadence is None or not report.cadence.available:
        lines.append(
            "Cadence measurements are unavailable: "
            f"{report.cadence.recommendation if report.cadence else 'no Git worktree.'}"
        )
    else:
        metrics = report.cadence
        lines.append(
            "- branch delta: "
            f"{metrics.entries} entries / {metrics.decisions} decisions / "
            f"{metrics.files} files / {metrics.churn} lines of churn"
        )
        for warning in metrics.warnings:
            lines.append(f"- {warning}")
        lines.append(f"- {metrics.recommendation}")
    lines.append("")

    lines.append("## Integration mode")
    if report.integration_mode == "pr":
        lines.append("pr — integrate via push + pull request (push authorized for that flow).")
    else:
        lines.append("local-merge — integrate via `session merge-branch` into local main; do NOT push without instruction.")
    if report.merge_trigger == "manual":
        lines.append("merge_trigger: manual — HOLD; do not land a branch on your own. The handoff (`session merge-branch` / `open-pr`) refuses without `--user-approved`, and the MCP integrate path declines; the user's go authorizes it.")
    else:
        lines.append("merge_trigger: automatic — may land at a stable, tested stopping point (local merge / open PR only; never pushes, never merges a PR).")
    lines.append("")

    lines.append("## Newest session entry")
    if not report.newest_session_path:
        lines.append("No session logs found.")
    else:
        lines.append(f"- {report.newest_session_path}")
        lines.append(f"  last entry: {report.newest_entry or '(no entries yet)'}")
        if report.newest_session_read_error:
            lines.append(f"  session context: unavailable ({report.newest_session_read_error})")
        else:
            lines.append(
                "  size: "
                f"{report.newest_session_characters} characters / "
                f"{report.newest_session_bytes} bytes / "
                f"{report.newest_session_entries} entries"
            )
            lines.append(
                "  context route: "
                f"{report.context_route} "
                f"(summarize when > {report.compression_threshold_characters} characters)"
            )
            if report.context_route == "direct":
                lines.append("  Read the entire file directly for current state.")
            elif report.context_route == "summarize":
                lines.append(
                    "  Follow `orientation.md`: use one read-only economy worker "
                    "to summarize the entire file."
                )
        lines.append("  Do not rely on memory_search for 'latest'; use it only for topical history.")
        if report.session_contributors:
            lines.append(f"  co-contributors on {report.newest_session_date}:")
            for contributor in report.session_contributors:
                noun = "entry" if contributor.entries == 1 else "entries"
                lines.append(f"  - {contributor.path} ({contributor.entries} {noun})")
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
