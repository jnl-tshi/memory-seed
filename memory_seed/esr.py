"""End-of-session-routine mechanical preflight (``memory-seed esr``).

One read-only pass over every deterministic end-of-turn check, so the routine
costs one command instead of a dozen exploratory calls, and a skipped step is
impossible to hide: every section prints even when clean. Judgment stays with
the agent - this reports, it never fixes.

Sections:
- integrity: ``links check`` (the only section that can fail the exit code)
- topics: controlled-vocabulary check
- link_gaps: ``link audit`` scoped to the session date (lifecycle sweep input)
- worktrees: per-worktree branch / commits-ahead-of-integration / dirty count
  (stale-sweep candidates are the merged-and-clean ones)
- seed_twins: live skill vs ``memory_seed/seed`` twin drift - only meaningful
  in the control-plane development repo itself, where the twins ship from;
  ordinary projects adapt their live skills freely and are never flagged.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from .core import check_session_links, read_integration_mode, resolve_runtime
from .topics import check_topics


@dataclass(frozen=True)
class WorktreePosture:
    path: str
    branch: str | None
    ahead: int | None
    dirty: int | None
    is_primary: bool

    @property
    def stale_candidate(self) -> bool:
        return not self.is_primary and self.ahead == 0 and self.dirty == 0


@dataclass
class EsrReport:
    session_date: str
    integration_mode: str = "local-merge"
    integrity_ok: bool = True
    integrity_issues: list[str] = field(default_factory=list)
    topics_ok: bool = True
    topics_issues: list[str] = field(default_factory=list)
    link_gaps: list[dict[str, Any]] = field(default_factory=list)
    open_link_stubs: int = 0
    worktrees: list[WorktreePosture] = field(default_factory=list)
    worktrees_available: bool = False
    seed_twins_checked: bool = False
    seed_twin_drift: list[str] = field(default_factory=list)
    docs_checked: bool = False
    docs_ok: bool = True
    docs_errors: list[str] = field(default_factory=list)
    docs_warning_count: int = 0
    # Semantic ranking degrades to lexical when the provider cannot load, and
    # `search_memory` reports that only inside a result payload nobody reads.
    # It went unnoticed here for an unknown stretch: memory-seed was installed
    # without its one declared dependency, so every search ranked lexically
    # while claiming a semantic provider. A preflight that prints even when
    # clean is the right home for "the thing you believe is on is off".
    semantic_available: bool = True
    semantic_provider: str | None = None
    semantic_unavailable_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_date": self.session_date,
            "integration_mode": self.integration_mode,
            "integrity": {"ok": self.integrity_ok, "issues": self.integrity_issues},
            "topics": {"ok": self.topics_ok, "issues": self.topics_issues},
            "link_gaps": self.link_gaps,
            "open_link_stubs": self.open_link_stubs,
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
            "seed_twins": {"checked": self.seed_twins_checked, "drift": self.seed_twin_drift},
            "docs": {
                "checked": self.docs_checked,
                "ok": self.docs_ok,
                "errors": self.docs_errors,
                "warning_count": self.docs_warning_count,
            },
            "semantic": {
                "available": self.semantic_available,
                "provider": self.semantic_provider,
                "unavailable_reason": self.semantic_unavailable_reason,
            },
        }


def _git_lines(root: Path, *args: str, timeout: int = 30) -> list[str] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.splitlines()


def _integration_ref(root: Path) -> str | None:
    for ref in ("main", "master"):
        if _git_lines(root, "rev-parse", "--verify", "--quiet", ref) is not None:
            return ref
    return None


def _worktree_posture(root: Path) -> tuple[bool, list[WorktreePosture]]:
    lines = _git_lines(root, "worktree", "list", "--porcelain")
    if lines is None:
        return False, []
    integration = _integration_ref(root)
    postures: list[WorktreePosture] = []
    current: dict[str, Any] = {}

    def flush(is_primary: bool) -> None:
        if not current.get("path"):
            return
        wt_path = Path(current["path"])
        branch = current.get("branch")
        ahead: int | None = None
        dirty: int | None = None
        if integration and branch and branch != integration:
            ahead_lines = _git_lines(root, "log", "--oneline", f"{integration}..{branch}")
            ahead = len(ahead_lines) if ahead_lines is not None else None
        elif branch == integration:
            ahead = 0
        status_lines = _git_lines(wt_path, "status", "--short")
        dirty = len([line for line in status_lines if line.strip()]) if status_lines is not None else None
        postures.append(
            WorktreePosture(
                path=str(wt_path),
                branch=branch,
                ahead=ahead,
                dirty=dirty,
                is_primary=is_primary,
            )
        )

    first = True
    for raw in lines:
        line = raw.rstrip()
        if not line:
            flush(is_primary=first and not postures)
            first = False
            current = {}
            continue
        if line.startswith("worktree "):
            current = {"path": line[len("worktree "):].strip()}
        elif line.startswith("branch "):
            ref = line[len("branch "):].strip()
            current["branch"] = ref.rsplit("/", 1)[-1] if "/" in ref else ref
        elif line == "detached":
            current["branch"] = None
    flush(is_primary=not postures)
    return True, postures


def _seed_twin_drift(root: Path) -> tuple[bool, list[str]]:
    """Live-vs-seed skill drift, control-plane dev repo only.

    The seed twins live inside the memory_seed package source; a project that
    merely INSTALLED memory-seed has no ``memory_seed/seed`` directory at its
    root, and its live skills legitimately diverge (project adaptations) - so
    the check is skipped entirely outside the dev repo.
    """
    seed_skills = root / "memory_seed" / "seed" / ".memory-seed" / "skills"
    live_skills = root / ".memory-seed" / "skills"
    if not seed_skills.is_dir() or not live_skills.is_dir():
        return False, []
    drift: list[str] = []
    for seed_file in sorted(seed_skills.glob("*.md")):
        # The skills registry legitimately diverges: the live index also
        # registers project-local persona skills that never ship with the
        # seed. Only the skill BODIES are twinned.
        if seed_file.name == "index.md":
            continue
        live_file = live_skills / seed_file.name
        if not live_file.exists():
            drift.append(f"{seed_file.name}: seed twin exists, live skill missing")
            continue
        try:
            if seed_file.read_text(encoding="utf-8") != live_file.read_text(encoding="utf-8"):
                drift.append(f"{seed_file.name}: live and seed twin differ")
        except (OSError, UnicodeDecodeError) as exc:
            drift.append(f"{seed_file.name}: unreadable ({exc})")
    return True, drift


def esr_report(cwd: str | Path = ".", *, session_date: str | None = None) -> EsrReport:
    from .retrieval import audit_link_gaps

    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root
    day = session_date or date.today().isoformat()
    report = EsrReport(session_date=day)
    report.integration_mode = read_integration_mode(root)

    links = check_session_links(cwd=cwd)
    report.integrity_ok = links.ok
    report.integrity_issues = [
        f"{issue.file}: {issue.kind}: {issue.detail}"
        for issue in links.issues
        if issue.severity == "error"
    ]
    report.open_link_stubs = sum(
        issue.kind == "sidecar-unclassified-stub" for issue in links.issues
    )

    topics = check_topics(cwd=cwd)
    report.topics_ok = topics.ok
    report.topics_issues = [
        f"{issue.severity}: {issue.kind}: {issue.detail}" + (f" ({issue.source})" if issue.source else "")
        for issue in topics.issues
    ]

    for gap in audit_link_gaps(cwd=cwd, session_date=day, top_k=3):
        report.link_gaps.append(
            {
                "entry_id": gap.entry_id,
                "title": gap.title,
                "candidates": [
                    {
                        "entry_id": cand.entry_id,
                        "title": cand.title,
                        "shared_files": list(cand.shared_files),
                        "shared_topics": list(cand.shared_topics),
                        "shared_title_terms": list(cand.shared_title_terms),
                        "already_related": cand.already_related,
                    }
                    for cand in gap.candidates
                ],
            }
        )

    report.worktrees_available, report.worktrees = _worktree_posture(root)
    report.seed_twins_checked, report.seed_twin_drift = _seed_twin_drift(root)

    from .docs_check import check_docs

    docs = check_docs(root)
    report.docs_checked = docs.files_checked > 0
    report.docs_ok = docs.ok
    report.docs_errors = [f"{i.file}: {i.kind}: {i.detail}" for i in docs.errors]
    report.docs_warning_count = len(docs.warnings)

    # Probe the embedding provider the way search does, so the preflight
    # reports the ranking the NEXT search will actually get. Imported here
    # rather than at module scope: esr must stay importable in a lightweight
    # install where the provider's dependency is absent - which is exactly the
    # situation this check exists to report.
    from .retrieval import resolve_semantic_provider

    provider, name, reason = resolve_semantic_provider("preflight")
    report.semantic_available = provider is not None
    report.semantic_provider = name
    report.semantic_unavailable_reason = reason
    return report


def format_esr_report(report: EsrReport) -> str:
    lines: list[str] = [f"ESR preflight — session {report.session_date}", ""]

    lines.append("## Semantic ranking")
    if report.semantic_available:
        lines.append(f"OK — {report.semantic_provider}")
    else:
        # Named as a degradation, not an error: search still answers, it just
        # answers lexically. The distinction matters because this is not a
        # failure anyone will notice from the results themselves.
        lines.append(f"DEGRADED — ranking is lexical only ({report.semantic_provider})")
        lines.append(f"- reason: {report.semantic_unavailable_reason}")
        lines.append("- a full install restores it: python -m pip install memory-seed")
    lines.append("")

    lines.append("## Integrity (links check)")
    if report.integrity_ok:
        lines.append("OK")
    else:
        lines.extend(f"- {issue}" for issue in report.integrity_issues)
    lines.append("")

    lines.append("## Topics")
    if report.topics_ok:
        lines.append("OK")
    else:
        lines.extend(f"- {issue}" for issue in report.topics_issues)
    lines.append("")

    lines.append("## Lifecycle link gaps (today's entries)")
    lines.append(f"Open classification stubs: {report.open_link_stubs}.")
    if not report.link_gaps:
        lines.append("None — no unlinked structural neighbours.")
    else:
        for gap in report.link_gaps:
            lines.append(f"- {gap['entry_id']}  {gap['title']}")
            for cand in gap["candidates"]:
                evidence = []
                # Title terms lead - see the matching comment in cli.py. Read
                # with `.get` because an ESR payload written before this field
                # existed must still render rather than KeyError on replay.
                if cand.get("shared_title_terms"):
                    evidence.append(f"terms: {', '.join(cand['shared_title_terms'])}")
                if cand["shared_files"]:
                    evidence.append(f"files: {', '.join(cand['shared_files'])}")
                if cand["shared_topics"]:
                    evidence.append(f"topics: {', '.join(cand['shared_topics'])}")
                if cand["already_related"]:
                    evidence.append("already related — consider a lifecycle upgrade")
                lines.append(f"    -> {cand['entry_id']}  {cand['title']}")
                if evidence:
                    lines.append(f"       {' | '.join(evidence)}")
    lines.append("")

    lines.append("## Integration mode")
    if report.integration_mode == "pr":
        lines.append("pr — integrate via push + pull request (declared push authorization for that flow).")
    else:
        lines.append("local-merge — integrate via `session merge-branch` into local main; no push.")
    lines.append("")

    lines.append("## Worktrees")
    if not report.worktrees_available:
        lines.append("Not a git repository (or git unavailable) — nothing to sweep.")
    elif len(report.worktrees) <= 1:
        lines.append("Only the primary checkout — nothing to sweep.")
    else:
        for wt in report.worktrees:
            if wt.is_primary:
                lines.append(f"- {wt.path}  [{wt.branch or 'detached'}]  primary")
                continue
            ahead = "?" if wt.ahead is None else wt.ahead
            dirty = "?" if wt.dirty is None else wt.dirty
            marker = "  STALE CANDIDATE (merged + clean)" if wt.stale_candidate else ""
            lines.append(f"- {wt.path}  [{wt.branch or 'detached'}]  ahead: {ahead}  dirty: {dirty}{marker}")
    lines.append("")

    lines.append("## Docs lifecycle")
    if not report.docs_checked:
        lines.append("No docs/ directory — skipped.")
    elif report.docs_ok:
        suffix = f" ({report.docs_warning_count} warning(s) — incomplete, not broken)" if report.docs_warning_count else ""
        lines.append(f"OK — links, lifecycle pointers, and spec bindings agree with the lanes{suffix}.")
    else:
        lines.extend(f"- {item}" for item in report.docs_errors)
    lines.append("")

    lines.append("## Seed twins")
    if not report.seed_twins_checked:
        lines.append("Not the control-plane dev repo — skipped.")
    elif not report.seed_twin_drift:
        lines.append("OK — live skills match their seed twins.")
    else:
        lines.extend(f"- {item}" for item in report.seed_twin_drift)

    return "\n".join(lines)
