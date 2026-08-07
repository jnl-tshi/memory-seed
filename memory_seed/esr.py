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
  (stale-sweep candidates are the merged-and-clean ones), plus physical agent
  worktree directories that Git no longer registers
- seed_twins: live skill vs ``memory_seed/seed`` twin drift - only meaningful
  in the control-plane development repo itself, where the twins ship from;
  ordinary projects adapt their live skills freely and are never flagged.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

SESSION_DATE_IN_PATH_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.md$")
DECISION_ORDINAL_RE = re.compile(r"d\d+")

from .core import check_session_links, read_integration_mode, read_merge_trigger, resolve_runtime
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


@dataclass(frozen=True)
class WorktreeResidue:
    path: str
    namespace: str
    git_file_present: bool


@dataclass
class EsrReport:
    session_date: str
    integration_mode: str = "local-merge"
    merge_trigger: str = "automatic"
    integrity_ok: bool = True
    integrity_issues: list[str] = field(default_factory=list)
    topics_ok: bool = True
    topics_issues: list[str] = field(default_factory=list)
    link_gaps: list[dict[str, Any]] = field(default_factory=list)
    open_link_stubs: int = 0
    # Backlog AGE, not just size. Both sweeps below find work every session but
    # only a deliberate campaign clears it, so a raw count reads as steady state
    # while the oldest item quietly rots - the link backlog cleared on
    # 2026-08-07 had been accumulating since 2026-07-21 and nothing said so.
    # Deliberately a count plus a date and NO verdict, for the same reason
    # `diagram_*` below is a count: the threshold at which a backlog earns a
    # campaign depends on cost and corpus state this report cannot see.
    oldest_open_link_stub: str | None = None
    topic_attribution_gaps: int = 0
    oldest_topic_attribution_gap: str | None = None
    # Vocabulary REQUESTS awaiting adjudication: `proposed_topic` values written
    # at decision granularity. They are never topics and cannot become one by
    # being used, so the only way they ever get considered is by being surfaced
    # here with the decision that asked as evidence.
    proposed_topics: list[str] = field(default_factory=list)
    worktrees: list[WorktreePosture] = field(default_factory=list)
    worktree_residues: list[WorktreeResidue] = field(default_factory=list)
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
    # Decision-diagram coverage. Deliberately a COUNT, not a verdict: a keyword
    # heuristic for "this entry needed a diagram" was prototyped against the
    # real corpus and flagged 35% of all entries - matching "worktree" in a
    # passing validation line, "topology" in a feature name. A check that fires
    # on one entry in three teaches its reader to skip it, and guessing the
    # judgement would contradict this module's own rule that judgment stays
    # with the agent. The bare fact is enough: the convention lapsed for five
    # days and 131 entries with nothing anywhere reporting it.
    diagrams_today: int = 0
    entries_today: int = 0
    last_diagram_date: str | None = None
    entries_since_last_diagram: int = 0
    # ADR diagram coverage IS mechanically determinable, unlike the per-entry
    # question: the denominator is the ADR corpus and every ADR owes an answer -
    # a diagram, or `diagram_status: not_applicable` recording that someone
    # looked and there was nothing structural to draw. Reported as a backlog
    # rather than enforced by `adrs check`, because landing the mechanism must
    # not turn 38 unanswered ADRs into a red gate on the commit that introduces
    # it. Tightening to a hard gate is the follow-up, once the corpus is answered.
    adrs_total: int = 0
    adrs_without_diagram_answer: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_date": self.session_date,
            "integration_mode": self.integration_mode,
            "merge_trigger": self.merge_trigger,
            "integrity": {"ok": self.integrity_ok, "issues": self.integrity_issues},
            "topics": {"ok": self.topics_ok, "issues": self.topics_issues},
            "link_gaps": self.link_gaps,
            "open_link_stubs": self.open_link_stubs,
            "oldest_open_link_stub": self.oldest_open_link_stub,
            "topic_attribution_gaps": self.topic_attribution_gaps,
            "proposed_topics": self.proposed_topics,
            "oldest_topic_attribution_gap": self.oldest_topic_attribution_gap,
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
                "residues": [
                    {
                        "path": residue.path,
                        "namespace": residue.namespace,
                        "git_file_present": residue.git_file_present,
                    }
                    for residue in self.worktree_residues
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
            "diagrams": {
                "today": self.diagrams_today,
                "entries_today": self.entries_today,
                "last_sidecar_date": self.last_diagram_date,
                "entries_since_last_sidecar": self.entries_since_last_diagram,
                "adrs_total": self.adrs_total,
                "adrs_without_diagram_answer": self.adrs_without_diagram_answer,
            },
        }


def _proposed_topic_requests(memory_dir: Path) -> list[str]:
    """``<slug> (requested by <entry_id>:<dN>)`` for every open vocabulary request.

    Read straight from the `proposed_topics:` key in topic sidecars rather than
    through a topic reader, deliberately: a request must never travel with the
    resolvable slugs, or something downstream will eventually treat it as one.
    """
    topics_dir = memory_dir / "sessions" / "topics"
    if not topics_dir.is_dir():
        return []
    requests: list[str] = []
    for path in sorted(topics_dir.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for block in re.finditer(r"```yaml\n(.*?)```", text, re.S):
            body = block.group(1)
            entry = re.search(r"entry_id:\s*(\S+)", body)
            region = re.search(r"^proposed_topics:\s*\n((?:[ \t]+\S.*\n)+)", body, re.M)
            if not (entry and region):
                continue
            axis = ""
            for line in region.group(1).splitlines():
                stripped = line.strip()
                if stripped.rstrip(":") in ("area", "activity") and stripped.endswith(":"):
                    axis = stripped.rstrip(":")
                    continue
                if not stripped.startswith("-"):
                    continue
                slug, _, ordinal = stripped[1:].strip().partition(":")
                who = f"{entry.group(1)}:{ordinal}" if ordinal else entry.group(1)
                requests.append(f"{slug} [{axis or 'axis not declared'}] (requested by {who})")
    return sorted(set(requests))


def _topic_attribution_gaps(cwd: str | Path) -> tuple[int, str | None]:
    """Decisions whose Area+Activity is not attributed AT DECISION GRANULARITY,
    where keying would actually add information.

    Not counted: a single-decision entry carrying entry-level Area+Activity.
    Its `dN` and its bare form denote the same thing, so keying it is the topic
    analogue of `redundant-decision-ref` - noise, not coverage. Counted: a
    multi-decision entry whose decisions can only inherit one shared list, and
    any decision with no Area+Activity from either source.

    Returns (count, oldest session date). Silent (0, None) on any failure - a
    reminder must never be able to fail the preflight it rides in.
    """
    try:
        from .retrieval import entry_topic_sidecars
        from .semantic_cache import extract_memory_chunks
        from .topics import load_topic_index

        index = load_topic_index(cwd)
        resolution = index.resolution()
        canon = lambda slug: resolution.get(slug, slug)  # noqa: E731
        both_axes = lambda slugs: {"area", "activity"} <= {  # noqa: E731
            index.axis_of(canon(slug)) for slug in slugs
        }

        keyed: dict[tuple[str, str], set[str]] = {}
        entry_level: dict[str, set[str]] = {}
        for entry_id, record in entry_topic_sidecars(cwd).items():
            for ordinal, slug in record.get("decision_topics", ()):
                target = keyed.setdefault((entry_id, ordinal), set()) if ordinal else entry_level.setdefault(entry_id, set())
                target.add(canon(slug))
            for slug in record.get("topics", ()):
                entry_level.setdefault(entry_id, set()).add(canon(slug))
        for chunk in extract_memory_chunks(cwd, granularity="entry"):
            if chunk.entry_id:
                for slug in (getattr(chunk, "topics", None) or ()):
                    entry_level.setdefault(chunk.entry_id, set()).add(canon(slug))

        decisions = [
            (chunk.session_date.isoformat(), chunk.entry_id, ordinal)
            for chunk in extract_memory_chunks(cwd, granularity="decision")
            if chunk.entry_id
            and DECISION_ORDINAL_RE.fullmatch(ordinal := (chunk.chunk_id or "").rsplit(":", 1)[-1])
        ]
        per_entry: dict[str, int] = {}
        for _date, entry_id, _ordinal in decisions:
            per_entry[entry_id] = per_entry.get(entry_id, 0) + 1

        gap_dates = []
        for session_date, entry_id, ordinal in decisions:
            if both_axes(keyed.get((entry_id, ordinal), set())):
                continue
            if both_axes(entry_level.get(entry_id, set())) and per_entry[entry_id] < 2:
                continue
            gap_dates.append(session_date)
        return len(gap_dates), min(gap_dates) if gap_dates else None
    except Exception:  # noqa: BLE001 - a reminder never fails the preflight
        return 0, None


def _entry_dates(memory_dir: Path) -> dict[str, str]:
    """``{entry_id: YYYY-MM-DD}`` for every session entry.

    Diagram sidecars are keyed by entry_id, so counting "today's entries that
    carry one" needs the reverse map. Skips the links/ and diagrams/ subtrees,
    which live under sessions/ but are not session logs.
    """
    import re

    dates: dict[str, str] = {}
    sessions = memory_dir / "sessions"
    if not sessions.is_dir():
        return dates
    for path in sorted(sessions.rglob("*.md")):
        if "links" in path.parts or "diagrams" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in re.finditer(r"^## (\d{4}-\d{2}-\d{2}) \d{2}:\d{2} - ", text, flags=re.M):
            nxt = text.find("\n## ", match.end())
            body = text[match.end(): nxt if nxt > 0 else len(text)]
            entry = re.search(r"entry_id:\s*(\S+)", body)
            if entry:
                dates[entry.group(1)] = match.group(1)
    return dates


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


def _normalised_path(path: Path) -> str:
    """Stable path identity using the host filesystem's case semantics."""
    return os.path.normcase(os.path.abspath(path))


def _worktree_storage_root(root: Path) -> Path:
    """Return the primary checkout root even when ESR runs in a worktree."""
    lines = _git_lines(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not lines:
        lines = _git_lines(root, "rev-parse", "--git-common-dir")
    if not lines:
        return root
    common_dir = Path(lines[0].strip())
    if not common_dir.is_absolute():
        common_dir = root / common_dir
    common_dir = common_dir.resolve(strict=False)
    return common_dir.parent if common_dir.name == ".git" else root


def _worktree_residues(root: Path, postures: list[WorktreePosture]) -> list[WorktreeResidue]:
    """Find physical agent worktree directories Git no longer registers.

    This is deliberately read-only and shallow. A residue candidate is not
    deletion authority: ESR surfaces the physical-vs-registered mismatch and
    the End Of Turn runbook owns the audit and consent gate.
    """
    storage_root = _worktree_storage_root(root)
    registered = {_normalised_path(Path(posture.path)) for posture in postures}
    residues: list[WorktreeResidue] = []
    for owner in ("claude", "codex", "gemini", "cursor"):
        namespace = storage_root / f".{owner}" / "worktrees"
        if not namespace.is_dir():
            continue
        try:
            children = sorted(namespace.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            continue
        for child in children:
            try:
                is_directory = child.is_dir()
            except OSError:
                continue
            if not is_directory or _normalised_path(child) in registered:
                continue
            residues.append(
                WorktreeResidue(
                    path=str(child.resolve(strict=False)),
                    namespace=f".{owner}/worktrees",
                    git_file_present=(child / ".git").is_file(),
                )
            )
    return residues


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
    report.merge_trigger = read_merge_trigger(root)

    links = check_session_links(cwd=cwd)
    report.integrity_ok = links.ok
    report.integrity_issues = [
        f"{issue.file}: {issue.kind}: {issue.detail}"
        for issue in links.issues
        if issue.severity == "error"
    ]
    stub_files = [
        issue.file for issue in links.issues if issue.kind == "sidecar-unclassified-stub"
    ]
    report.open_link_stubs = len(stub_files)
    # A link sidecar is filed under its SOURCE entry's session date, so the
    # filename IS the age of the work waiting - no entry lookup needed.
    stub_dates = sorted(
        match.group(1)
        for match in (SESSION_DATE_IN_PATH_RE.search(path) for path in stub_files)
        if match
    )
    report.oldest_open_link_stub = stub_dates[0] if stub_dates else None

    gaps, oldest_gap = _topic_attribution_gaps(cwd)
    report.topic_attribution_gaps = gaps
    report.oldest_topic_attribution_gap = oldest_gap
    report.proposed_topics = _proposed_topic_requests(runtime.memory_dir)

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
                        # The one ranking term a reader cannot verify by eye, so it
                        # travels with the evidence rather than staying implicit in
                        # the order. `None` when semantic ranking was unavailable.
                        "semantic_score": cand.semantic_score,
                        "already_related": cand.already_related,
                    }
                    for cand in gap.candidates
                ],
            }
        )

    report.worktrees_available, report.worktrees = _worktree_posture(root)
    if report.worktrees_available:
        report.worktree_residues = _worktree_residues(root, report.worktrees)
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

    # Diagram coverage: how many of today's entries carry a sidecar, and when
    # the last one anywhere was written. The second number is the one that
    # matters - a run of empty days is invisible from inside any single day.
    # Read through the sanctioned sidecar reader rather than re-parsing the
    # files here: it already owns both the month-grouped and legacy-flat
    # layouts, and a second hand-rolled parser is how the two drift apart.
    from .retrieval import entry_diagram_sidecars

    sidecars = entry_diagram_sidecars(cwd)
    report.last_diagram_date = max(
        (str(meta.get("heading_datetime", ""))[:10] for meta in sidecars.values() if meta),
        default=None,
    ) or None
    today_entries = {
        entry_id
        for entry_id, meta in _entry_dates(runtime.memory_dir).items()
        if meta == report.session_date
    }
    report.entries_today = len(today_entries)
    report.diagrams_today = sum(1 for entry_id in today_entries if entry_id in sidecars)
    # How far the practice has drifted, counted the only way that needs no
    # judgment: entries logged since the last diagram was written. NOT "entries
    # that owed one" - the heuristic for that was prototyped and rejected (see
    # the field comment). A date alone reads as recent at a glance; "42 entries
    # since" is the same fact with its weight attached.
    if report.last_diagram_date:
        report.entries_since_last_diagram = sum(
            1
            for entry_id, entry_date in _entry_dates(runtime.memory_dir).items()
            if entry_date > report.last_diagram_date and entry_id not in sidecars
        )

    from .core import known_adr_ids
    from .retrieval import adr_diagram_sidecars

    adr_ids = known_adr_ids(cwd)
    answered = set(adr_diagram_sidecars(cwd))
    report.adrs_total = len(adr_ids)
    report.adrs_without_diagram_answer = len(adr_ids - answered)
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

    lines.append("## Decision diagrams")
    if report.diagrams_today:
        lines.append(f"{report.diagrams_today} of today's {report.entries_today} entries carry a sidecar.")
    else:
        # No verdict on whether one was warranted - that judgement is the
        # agent's. The lapse this exists to surface is only visible as a RUN of
        # empty days, which no single day's view shows.
        lines.append(f"None of today's {report.entries_today} entries carry a sidecar.")
        if report.last_diagram_date:
            since = (
                f" ({report.entries_since_last_diagram} entries logged since)"
                if report.entries_since_last_diagram
                else ""
            )
            lines.append(f"- last sidecar anywhere: {report.last_diagram_date}{since}")
        else:
            lines.append("- no diagram sidecar exists in this project yet")
        lines.append(
            "- session_logging.md: when a positive trigger is present and no sidecar is written, "
            "state the reason under A: or Follow-up"
        )
    if report.adrs_without_diagram_answer:
        lines.append(
            f"- ADRs with no diagram answer: {report.adrs_without_diagram_answer} of {report.adrs_total} "
            "(a diagram, or `diagram_status: not_applicable` recording that there is no shape to draw)"
        )
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
    if report.topic_attribution_gaps:
        oldest = f", oldest {report.oldest_topic_attribution_gap}" if report.oldest_topic_attribution_gap else ""
        lines.append(
            f"Decisions without decision-keyed area+activity, corpus-wide: "
            f"{report.topic_attribution_gaps}{oldest} (topic_swarm.md backfills these)."
        )
    if report.proposed_topics:
        lines.append(f"Vocabulary requests awaiting adjudication: {len(report.proposed_topics)}.")
        lines.extend(f"- {request}" for request in report.proposed_topics)
        lines.append(
            "  Rule each: add to topics.yaml, or decline. A request never becomes a slug by being used."
        )
    lines.append("")

    lines.append("## Lifecycle link gaps (today's entries)")
    oldest = f", oldest {report.oldest_open_link_stub}" if report.oldest_open_link_stub else ""
    lines.append(f"Open classification stubs: {report.open_link_stubs}.")
    if report.open_link_stubs:
        lines.append(f"Corpus-wide, not just today{oldest} (link_swarm.md judges these at scale).")
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
    if report.merge_trigger == "manual":
        lines.append("merge_trigger: manual — HOLD; landing needs `--user-approved` (MCP integrate declines).")
    else:
        lines.append("merge_trigger: automatic — may land at a stable, tested stopping point (local merge / open PR only).")
    lines.append("")

    lines.append("## Worktrees")
    if not report.worktrees_available:
        lines.append("Not a git repository (or git unavailable) — nothing to sweep.")
    elif len(report.worktrees) <= 1 and not report.worktree_residues:
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
        if report.worktree_residues:
            lines.append("Unregistered physical directories — audit before removal:")
            for residue in report.worktree_residues:
                metadata = ".git pointer present" if residue.git_file_present else ".git pointer absent"
                lines.append(
                    f"- {residue.path}  [{residue.namespace}]  "
                    f"ORPHAN RESIDUE CANDIDATE ({metadata})"
                )
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
