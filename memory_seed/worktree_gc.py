"""Worktree cleanup classification - the dry-run half of the safe executor.

Track E Phase 1. Classifies every registered worktree and shows the evidence
for each verdict. **Classification only: this module never removes anything.**

The design rule that matters: *never assume merge status implies a clean
worktree*. A branch being merged says nothing about whether its worktree holds
uncommitted work, and this repo lives on OneDrive, where a locked `.git/index`
mid-operation is routine rather than exceptional. So a worktree is `removable`
only when **every** safety question answers yes at once, and anything unknown
degrades to a state that refuses removal rather than one that permits it.

Branch deletion is deliberately out of scope: a worktree and its branch are
independent lifecycle objects, and conflating them is how "clean up my
worktrees" quietly deletes unmerged work.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

WorktreeState = Literal[
    "root",  # the primary worktree - never removable
    "active",  # the worktree this process is running in
    "dirty",  # uncommitted or untracked changes present
    "unmerged",  # branch has commits not in the integration branch
    "locked",  # git-locked, or prunable/unreachable
    "foreign",  # outside this agent's namespace, or in no known namespace
    "removable",  # clean, merged, registered, unlocked, own namespace
    "unknown",  # a safety question could not be answered - fails closed
]

# Ordered by precedence: the first matching state wins, so a dirty *and*
# unmerged worktree reports `dirty`. Deliberately reported as one state with
# full evidence rather than a set, so the reason a removal was refused is
# unambiguous.
_REMOVABLE_STATES: frozenset[str] = frozenset({"removable"})


@dataclass(frozen=True)
class WorktreeClassification:
    path: str
    state: WorktreeState
    branch: str | None
    head: str | None
    namespace_owner: str | None
    removable: bool
    evidence: tuple[str, ...]
    recommendation: str


@dataclass(frozen=True)
class WorktreeGcReport:
    integration_branch: str
    classifications: tuple[WorktreeClassification, ...]

    @property
    def removable(self) -> tuple[WorktreeClassification, ...]:
        return tuple(item for item in self.classifications if item.removable)

    def to_dict(self) -> dict:
        return {
            "integration_branch": self.integration_branch,
            "worktrees": [
                {
                    "path": item.path,
                    "state": item.state,
                    "branch": item.branch,
                    "head": item.head,
                    "namespace_owner": item.namespace_owner,
                    "removable": item.removable,
                    "evidence": list(item.evidence),
                    "recommendation": item.recommendation,
                }
                for item in self.classifications
            ],
        }


def _is_dirty(path: Path) -> bool | None:
    """True/False, or None when git could not answer - which the caller must
    treat as `unknown`, never as clean."""
    from .core import _git_text

    code, out = _git_text(path, ("status", "--porcelain"))
    if code != 0:
        return None
    return bool(out.strip())


def _is_merged(root: Path, branch: str, integration_branch: str) -> bool | None:
    from .core import _git_text

    code, out = _git_text(
        root, ("branch", "--merged", integration_branch, "--format=%(refname:short)")
    )
    if code != 0:
        return None
    return branch in {line.strip() for line in out.splitlines() if line.strip()}


def classify_worktrees(
    cwd: str | Path = ".",
    *,
    agent_type: str | None = None,
    integration_branch: str = "main",
) -> WorktreeGcReport:
    """Classify every registered worktree. Read-only; removes nothing.

    ``agent_type`` scopes the ``foreign`` verdict: a worktree in another agent's
    namespace is never this agent's to remove. With no ``agent_type`` the
    namespace owner is still reported, but only unowned paths are foreign.
    """
    from .core import (
        DEFAULT_WORKTREE_NAMESPACES,
        _git_text,
        _namespace_owner,
        _parse_worktree_list,
    )

    root = Path(cwd).resolve()
    code, porcelain = _git_text(root, ("worktree", "list", "--porcelain"))
    if code != 0 or not porcelain.strip():
        return WorktreeGcReport(integration_branch=integration_branch, classifications=())

    namespaces = dict(DEFAULT_WORKTREE_NAMESPACES)
    here = root
    items = _parse_worktree_list(porcelain)
    if not items:
        return WorktreeGcReport(integration_branch=integration_branch, classifications=())

    # git always lists the *main* worktree first. Do not use `rev-parse
    # --show-toplevel`: inside a linked worktree it returns that worktree's own
    # path, which would both misclassify it as root and resolve every namespace
    # against the wrong base.
    try:
        repo_root = Path(items[0].get("path", "")).resolve()
    except (OSError, ValueError):
        return WorktreeGcReport(integration_branch=integration_branch, classifications=())
    classifications: list[WorktreeClassification] = []

    for index, item in enumerate(items):
        raw_path = item.get("path", "")
        try:
            path = Path(raw_path).resolve()
        except (OSError, ValueError):
            classifications.append(
                WorktreeClassification(
                    path=raw_path,
                    state="unknown",
                    branch=None,
                    head=None,
                    namespace_owner=None,
                    removable=False,
                    evidence=("worktree path could not be resolved",),
                    recommendation="Inspect manually; refusing to classify an unresolvable path.",
                )
            )
            continue

        branch_ref = item.get("branch")
        branch = branch_ref.replace("refs/heads/", "") if branch_ref else None
        head = item.get("HEAD")
        owner = _namespace_owner(repo_root, path, namespaces)
        evidence: list[str] = []

        # The first entry git reports is always the primary worktree.
        if index == 0:
            evidence.append("primary worktree of the repository")
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="root",
                    branch=branch,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation="Never removable: this is the repository root.",
                )
            )
            continue

        if "locked" in item or "prunable" in item:
            reason = item.get("locked") or item.get("prunable") or "reported by git"
            evidence.append(f"git reports locked/prunable: {reason or 'no reason given'}")
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="locked",
                    branch=branch,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation=(
                        "Run `git worktree unlock` or `git worktree prune` deliberately. "
                        "Never delete the directory by hand."
                    ),
                )
            )
            continue

        if path == here:
            evidence.append("this process is running inside it")
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="active",
                    branch=branch,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation="Not removable while it is the active worktree.",
                )
            )
            continue

        if owner is None or (agent_type is not None and owner != agent_type):
            evidence.append(
                f"namespace owner is {owner or 'none'}"
                + (f", not {agent_type}" if agent_type else " (outside any known namespace)")
            )
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="foreign",
                    branch=branch,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation="Not this agent's worktree to remove; leave it to its owner.",
                )
            )
            continue

        dirty = _is_dirty(path)
        if dirty is None:
            evidence.append("git status could not be read - cleanliness unknown")
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="unknown",
                    branch=branch,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation=(
                        "Refusing removal: an unreadable worktree may still hold work. "
                        "Inspect it manually."
                    ),
                )
            )
            continue
        if dirty:
            evidence.append("uncommitted or untracked changes present")
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="dirty",
                    branch=branch,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation="Commit, stash, or discard the changes first.",
                )
            )
            continue
        evidence.append("working tree is clean")

        if branch is None:
            evidence.append("detached HEAD - no branch to check merge status against")
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="unknown",
                    branch=None,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation=(
                        "Refusing removal: a detached HEAD may hold unreachable commits."
                    ),
                )
            )
            continue

        merged = _is_merged(repo_root, branch, integration_branch)
        if merged is None:
            evidence.append(f"could not determine whether {branch} is merged")
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="unknown",
                    branch=branch,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation="Refusing removal: merge status is unknown.",
                )
            )
            continue
        if not merged:
            evidence.append(f"{branch} has commits not in {integration_branch}")
            classifications.append(
                WorktreeClassification(
                    path=str(path),
                    state="unmerged",
                    branch=branch,
                    head=head,
                    namespace_owner=owner,
                    removable=False,
                    evidence=tuple(evidence),
                    recommendation=f"Merge or explicitly abandon {branch} first.",
                )
            )
            continue

        evidence.append(f"{branch} is merged into {integration_branch}")
        evidence.append("registered with git and unlocked")
        classifications.append(
            WorktreeClassification(
                path=str(path),
                state="removable",
                branch=branch,
                head=head,
                namespace_owner=owner,
                removable=True,
                evidence=tuple(evidence),
                recommendation=(
                    f"Safe to remove with `git worktree remove {path}`. "
                    "Branch deletion is a separate, approval-gated step."
                ),
            )
        )

    return WorktreeGcReport(
        integration_branch=integration_branch, classifications=tuple(classifications)
    )


@dataclass(frozen=True)
class WorktreeRemoval:
    path: str
    branch: str | None
    removed: bool
    attempts: int
    detail: str


@dataclass(frozen=True)
class WorktreeGcApplyResult:
    removed: tuple[WorktreeRemoval, ...]
    refused: tuple[WorktreeRemoval, ...]
    skipped_non_removable: tuple[WorktreeClassification, ...]

    def to_dict(self) -> dict:
        def _r(x: WorktreeRemoval) -> dict:
            return {
                "path": x.path,
                "branch": x.branch,
                "removed": x.removed,
                "attempts": x.attempts,
                "detail": x.detail,
            }

        return {
            "removed": [_r(x) for x in self.removed],
            "refused": [_r(x) for x in self.refused],
            "skipped_non_removable": [x.path for x in self.skipped_non_removable],
        }


def _remove_one_worktree(
    repo_root: Path,
    path: str,
    *,
    max_attempts: int,
    remover: "Callable[[Path, str], tuple[int, str]] | None" = None,
) -> tuple[bool, int, str]:
    """Remove one worktree with git, retrying a locked path a bounded number of
    times. Returns (removed, attempts, detail).

    ``remover`` is injectable so the retry/failure path can be tested without a
    real OS lock (which cannot be summoned on demand). It defaults to
    ``git worktree remove`` and is the *only* removal mechanism — there is no
    raw-filesystem fallback, by design: the plan forbids raw recursive deletion,
    and an escape hatch is how that rule gets bypassed later.
    """
    from .core import _git_text

    def _default(root: Path, target: str) -> tuple[int, str]:
        return _git_text(root, ("worktree", "remove", target))

    run = remover or _default
    detail = ""
    for attempt in range(1, max_attempts + 1):
        code, out = run(repo_root, path)
        if code == 0:
            return True, attempt, "removed"
        detail = out or "git worktree remove failed"
        # A lock is the retryable case; anything else is a hard failure now.
        if "locked" not in detail.lower() and "denied" not in detail.lower():
            break
    return False, attempt, detail


def apply_worktree_gc(
    cwd: str | Path = ".",
    *,
    agent_type: str | None = None,
    integration_branch: str = "main",
    max_attempts: int = 3,
    remover: "Callable[[Path, str], tuple[int, str]] | None" = None,
) -> WorktreeGcApplyResult:
    """Remove the worktrees a fresh classification calls ``removable``.

    **Destructive.** It reclassifies immediately before acting — a stale
    ``removable`` verdict is never trusted for a delete — and removes only what
    that live pass still calls removable, through git, with bounded retry on a
    lock and no raw-filesystem fallback. Branch deletion is deliberately out of
    scope: a worktree and its branch are independent objects.
    """
    from .core import _git_text

    root = Path(cwd).resolve()
    code, top = _git_text(root, ("rev-parse", "--show-toplevel"))
    repo_root = Path(top).resolve() if code == 0 and top else root

    # Re-derive the truth now, at apply time. Do not accept a caller's report.
    report = classify_worktrees(
        root, agent_type=agent_type, integration_branch=integration_branch
    )
    removed: list[WorktreeRemoval] = []
    refused: list[WorktreeRemoval] = []
    for item in report.classifications:
        if not item.removable:
            continue
        ok, attempts, detail = _remove_one_worktree(
            repo_root, item.path, max_attempts=max_attempts, remover=remover
        )
        record = WorktreeRemoval(
            path=item.path, branch=item.branch, removed=ok, attempts=attempts, detail=detail
        )
        (removed if ok else refused).append(record)

    return WorktreeGcApplyResult(
        removed=tuple(removed),
        refused=tuple(refused),
        skipped_non_removable=tuple(i for i in report.classifications if not i.removable),
    )


def format_worktree_gc_apply(result: WorktreeGcApplyResult) -> str:
    lines: list[str] = []
    for x in result.removed:
        lines.append(f"REMOVED  {x.path}  (branch {x.branch or '-'}; {x.attempts} attempt(s))")
    for x in result.refused:
        lines.append(f"REFUSED  {x.path}: {x.detail}")
        lines.append(
            "  → left intact. Resolve the lock or condition and re-run; "
            "never delete the directory by hand."
        )
    if not result.removed and not result.refused:
        lines.append("No removable worktree to act on.")
    else:
        lines.append(
            f"{len(result.removed)} removed, {len(result.refused)} refused. "
            "Branch deletion is separate and was not touched."
        )
    return "\n".join(lines)


def format_worktree_gc_report(report: WorktreeGcReport) -> str:
    """Human surface. Shows the evidence for every verdict, per the plan's
    "show the evidence for every classification"."""
    if not report.classifications:
        return "No worktrees found (not a git repository, or git could not be read)."
    lines = [f"Worktree classification (integration branch: {report.integration_branch})", ""]
    for item in report.classifications:
        lines.append(f"{item.state.upper()}  {item.path}")
        lines.append(f"  branch: {item.branch or '(detached)'}")
        for reason in item.evidence:
            lines.append(f"  - {reason}")
        lines.append(f"  → {item.recommendation}")
        lines.append("")
    removable = report.removable
    if removable:
        lines.append(f"{len(removable)} worktree(s) classified removable. This is a dry run;")
        lines.append("nothing has been removed. Removal is a separate, deliberate step.")
    else:
        lines.append("No worktree is currently removable.")
    return "\n".join(lines)
