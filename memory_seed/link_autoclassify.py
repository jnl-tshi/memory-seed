"""Automatic lifecycle-link classification: turn validated swarm verdicts into live edges.

Adopted 2026-09-25 (JNL, Constitution §4 `link-corrections` v2.x). Machine-classified edges are
written as live, retractable links without a human approval step, under these rules:

* Every edge comes from a mechanically validated verdict (`link batch-collect`: exact quote
  grounding, ordinal existence, chain-position legality). Nothing un-validated is written.
* Structure-changing labels - ``replaces`` and ``refines`` - are written only when two independent
  runs agree on the label and both ordinals. A single-run or disagreeing structural verdict falls
  back to the weaker label both runs support (``builds-on`` / ``related``) or is left pending.
* ``builds-on`` and ``related`` are written from one validated verdict.
* Each edge records ``source: derived``, the classifier runs, its confidence and its grounding
  quote. Retrieval scales a machine ``replaces`` by that confidence; a later human
  ``link verify`` record raises it to full weight.
* Machine edges never move an ADR head; an edge onto an ADR member only enters the review queue.
* A source entry whose every candidate was judged ``none`` by the available runs records
  ``edge_status: not_applicable`` so its stub reads as examined rather than unexamined.

The write is guarded: the effective graph is snapshotted before and after, and the change is
rolled back when ``links check`` reports an error.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

STRUCTURAL = {"replaces", "refines"}
WEAK = {"builds-on", "related"}
POSITIVE = STRUCTURAL | WEAK
# The strength order used to fall back when runs disagree: a verdict may only be weakened.
_STRENGTH = {"none": 0, "related": 1, "builds-on": 2, "refines": 3, "replaces": 3}
AUTO_HEADING_LABEL = "Automatic lifecycle classification"


@dataclass
class AutoEdge:
    source_entry_id: str
    source_date: str
    kind: str  # replaces | evolves | related_entries
    ref: str  # the authored ref token, e.g. "d1 -> mse_x:d2 (refines)"
    verdict: str
    confidence: float | None
    agreement: str  # two-run | single-run
    quote: str
    why: str


@dataclass
class AutoLinkPlan:
    run_ids: list[str]
    edges: list[AutoEdge] = field(default_factory=list)
    not_applicable: dict[str, str] = field(default_factory=dict)  # entry_id -> session_date
    pending: list[dict[str, Any]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_ids": self.run_ids,
            "edges": [edge.__dict__ for edge in self.edges],
            "not_applicable": sorted(self.not_applicable),
            "pending": self.pending,
            "counts": self.counts,
        }


_STUB_ENTRY_RE = re.compile(r"entry_id (\S+) still requires lifecycle classification")


def open_stub_entry_ids(cwd: str | Path) -> list[str]:
    """Entries whose `classify_pending` stub has no later classification or `edge_status`."""
    from .core import check_session_links

    ids: list[str] = []
    for issue in check_session_links(cwd).issues:
        if issue.kind != "sidecar-unclassified-stub":
            continue
        match = _STUB_ENTRY_RE.search(issue.detail)
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def _decisionless_open_stubs(cwd: str | Path) -> list[tuple[str, str]]:
    """Open-stub entries whose body has no decision records, with their session dates."""
    from .core import entry_body_decisions
    from .retrieval import load_corpus

    open_ids = set(open_stub_entry_ids(cwd))
    if not open_ids:
        return []
    found: list[tuple[str, str]] = []
    for chunk in load_corpus(cwd, granularity="entry"):
        entry_id = getattr(chunk, "entry_id", None)
        if entry_id in open_ids and not entry_body_decisions(chunk.text):
            found.append((entry_id, str(chunk.session_date)))
    return found


def _load_run(run_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    rows = {}
    for line in (run_dir / "analytics.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["pair_id"]] = row
    pairs = {pair["pair_id"]: pair for batch in plan.get("batches", []) for pair in batch.get("pairs", [])}
    return plan, rows, pairs


def _normalize_verdict(verdict: str | None) -> str:
    # A legacy untyped `evolves` cannot be written (every effective evolves edge carries a type),
    # so it can only ever support the weaker `related`.
    if verdict == "evolves":
        return "related"
    return verdict or "none"


def _decision_count(side: dict[str, Any]) -> int:
    return len(side.get("decisions") or [])


def _ref(pair: dict[str, Any], verdict: str, source_decision: str | None, candidate_decision: str | None) -> tuple[str, str]:
    """Build the canonical authored ref: ordinals only on 2+-decision ends."""
    source = pair["source"]
    candidate = pair["candidate"]
    prefix = f"{source_decision} -> " if source_decision and _decision_count(source) >= 2 else ""
    target = candidate["entry_id"]
    if candidate_decision and _decision_count(candidate) >= 2:
        target = f"{target}:{candidate_decision}"
    if verdict == "replaces":
        return "replaces", f"{prefix}{target}"
    if verdict in {"refines", "builds-on"}:
        return "evolves", f"{prefix}{target} ({verdict})"
    return "related_entries", f"{prefix}{target}"


def plan_auto_links(run_a: str | Path, run_b: str | Path | None = None) -> AutoLinkPlan:
    """Decide which validated verdicts become live edges under the two-run rule."""
    run_a = Path(run_a)
    plan_a, rows_a, pairs = _load_run(run_a)
    rows_b: dict[str, dict[str, Any]] = {}
    run_ids = [str(plan_a.get("run_id"))]
    if run_b is not None:
        plan_b, rows_b, pairs_b = _load_run(Path(run_b))
        if set(pairs_b) != set(pairs):
            raise ValueError("the two runs must judge the same candidate pairs (build both from one plan)")
        run_ids.append(str(plan_b.get("run_id")) + "#2" if plan_b.get("run_id") == plan_a.get("run_id") else str(plan_b.get("run_id")))

    result = AutoLinkPlan(run_ids=run_ids)
    counts = {"pairs": len(pairs), "written": 0, "fallback": 0, "pending": 0, "none": 0}
    positive_sources: set[str] = set()
    judged_sources: dict[str, str] = {}

    for pair_id, pair in pairs.items():
        source_id = pair["source"]["entry_id"]
        source_date = str(pair["source"].get("session_date") or "")
        row_a = rows_a.get(pair_id, {})
        row_b = rows_b.get(pair_id, {}) if run_b is not None else None
        valid_a = row_a.get("status") == "validated"
        valid_b = row_b is not None and row_b.get("status") == "validated"
        if not valid_a and not valid_b:
            counts["pending"] += 1
            result.pending.append({"pair_id": pair_id, "reason": "no validated verdict"})
            continue
        judged_sources.setdefault(source_id, source_date)
        verdict_a = _normalize_verdict(row_a.get("verdict")) if valid_a else None
        verdict_b = _normalize_verdict(row_b.get("verdict")) if valid_b else None

        chosen: str | None
        chosen_row: dict[str, Any]
        agreement = "single-run"
        if verdict_a is not None and verdict_b is not None:
            same_ordinals = (
                row_a.get("source_decision") == row_b.get("source_decision")
                and row_a.get("candidate_decision") == row_b.get("candidate_decision")
            )
            if verdict_a == verdict_b and same_ordinals:
                chosen, chosen_row, agreement = verdict_a, row_a, "two-run"
            else:
                # Weaken to the strongest label BOTH runs support, never below what the weaker says.
                weaker = verdict_a if _STRENGTH[verdict_a] <= _STRENGTH[verdict_b] else verdict_b
                chosen_row = row_a if weaker == verdict_a else row_b
                chosen = weaker if weaker in WEAK or weaker == "none" else "related"
                if chosen != "none":
                    counts["fallback"] += 1
        else:
            chosen_row = row_a if verdict_a is not None else row_b  # type: ignore[assignment]
            chosen = verdict_a if verdict_a is not None else verdict_b
            if chosen in STRUCTURAL:
                # A structural label needs a second, agreeing run.
                if run_b is None:
                    chosen = "related"
                    counts["fallback"] += 1
                else:
                    counts["pending"] += 1
                    result.pending.append({"pair_id": pair_id, "reason": "structural verdict from one run only"})
                    continue

        if chosen is None or chosen == "none":
            counts["none"] += 1
            continue
        positive_sources.add(source_id)
        confidences = [
            row.get("confidence") for row in (row_a if valid_a else None, row_b if valid_b else None)
            if row is not None and isinstance(row.get("confidence"), (int, float))
        ]
        confidence = min(confidences) if confidences else None
        kind, ref = _ref(pair, chosen, chosen_row.get("source_decision"), chosen_row.get("candidate_decision"))
        result.edges.append(
            AutoEdge(
                source_entry_id=source_id,
                source_date=source_date,
                kind=kind,
                ref=ref,
                verdict=chosen,
                confidence=confidence,
                agreement=agreement,
                quote=str(chosen_row.get("quote") or ""),
                why=str(chosen_row.get("why") or ""),
            )
        )
        counts["written"] += 1

    for source_id, source_date in judged_sources.items():
        if source_id not in positive_sources:
            result.not_applicable[source_id] = source_date
    result.counts = counts
    return result


def _yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_auto_block(
    entry_id: str,
    edges: list[AutoEdge],
    *,
    heading_ts: str,
    run_ids: list[str],
    not_applicable: bool = False,
) -> str:
    lines = [f"## {heading_ts} - {AUTO_HEADING_LABEL}", "", "```yaml", f"entry_id: {entry_id}", "source: derived"]
    lines.append(f"classified_by: {_yaml_quote('link-swarm ' + ' + '.join(run_ids))}")
    if not_applicable:
        lines.append("edge_status: not_applicable")
    for kind in ("replaces", "evolves", "related_entries"):
        refs = [edge.ref for edge in edges if edge.kind == kind]
        if refs:
            lines.append(f"{kind}:")
            lines.extend(f"  - {ref}" for ref in refs)
    scored = [edge for edge in edges if edge.confidence is not None]
    if scored:
        lines.append("edge_confidence:")
        for edge in scored:
            lines.append(f"  - ref: {_yaml_quote(edge.ref)}")
            lines.append(f"    confidence: {edge.confidence:.2f}")
            lines.append(f"    agreement: {edge.agreement}")
    if edges:
        lines.append("edge_evidence:")
        for edge in edges:
            lines.append(f"  - ref: {_yaml_quote(edge.ref)}")
            lines.append(f"    quote: {_yaml_quote(edge.quote)}")
            lines.append(f"    why: {_yaml_quote(edge.why)}")
    lines += ["```", ""]
    return "\n".join(lines)


def _sidecar_path(sessions_dir: Path, session_date: str) -> Path:
    return sessions_dir / "links" / session_date[:7] / f"{session_date}.md"


def apply_auto_links(
    cwd: str | Path,
    run_a: str | Path,
    run_b: str | Path | None = None,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Write the planned edges as live link-sidecar blocks, guarded by links check."""
    from .core import MEMORY_DIR_NAME, check_session_links, resolve_runtime
    from .retrieval import diff_graph_snapshots, effective_graph_snapshot

    root = resolve_runtime(cwd).workspace_root
    sessions_dir = root / MEMORY_DIR_NAME / "sessions"
    plan = plan_auto_links(run_a, run_b)
    heading_ts = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")

    by_source: dict[str, list[AutoEdge]] = {}
    dates: dict[str, str] = {}
    for edge in plan.edges:
        by_source.setdefault(edge.source_entry_id, []).append(edge)
        dates[edge.source_entry_id] = edge.source_date
    for entry_id, session_date in plan.not_applicable.items():
        by_source.setdefault(entry_id, [])
        dates[entry_id] = session_date
    # An open stub on an entry with no decision records can never carry a decision-level
    # lifecycle edge (the planner excludes it as `missing_decision`), so record it as
    # examined rather than leaving it pending forever.
    for entry_id, session_date in _decisionless_open_stubs(root):
        if entry_id not in by_source:
            by_source[entry_id] = []
            dates[entry_id] = session_date
            plan.not_applicable[entry_id] = session_date

    blocks: dict[Path, list[str]] = {}
    for entry_id in sorted(by_source):
        session_date = dates[entry_id]
        if len(session_date) != 10:
            plan.pending.append({"entry_id": entry_id, "reason": "source session date unknown"})
            continue
        block = render_auto_block(
            entry_id,
            by_source[entry_id],
            heading_ts=heading_ts,
            run_ids=plan.run_ids,
            not_applicable=not by_source[entry_id],
        )
        blocks.setdefault(_sidecar_path(sessions_dir, session_date), []).append(block)

    payload = plan.to_dict()
    payload["files"] = sorted(str(path.relative_to(root)) for path in blocks)
    payload["dry_run"] = dry_run
    if dry_run or not blocks:
        payload["written"] = False
        return payload

    before = effective_graph_snapshot(root)
    originals: dict[Path, str | None] = {}
    try:
        for path, rendered in blocks.items():
            originals[path] = path.read_text(encoding="utf-8") if path.exists() else None
            path.parent.mkdir(parents=True, exist_ok=True)
            existing = originals[path] or ""
            if existing and not existing.endswith("\n"):
                existing += "\n"
            separator = "\n" if existing else ""
            path.write_text(existing + separator + "\n".join(rendered), encoding="utf-8", newline="\n")
        check = check_session_links(root)
        errors = [issue for issue in check.issues if getattr(issue, "severity", "error") == "error"]
        if errors:
            raise ValueError(
                "links check failed after the automatic write; rolled back: "
                + "; ".join(f"{issue.kind}: {issue.detail}" for issue in errors[:5])
            )
    except Exception:
        for path, text in originals.items():
            if text is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(text, encoding="utf-8", newline="\n")
        raise
    after = effective_graph_snapshot(root)
    payload["written"] = True
    payload["graph_delta"] = diff_graph_snapshots(before, after)
    return payload


def verify_link(
    cwd: str | Path,
    source_entry_id: str,
    ref: str,
    *,
    verified_by: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Append a human verification record that raises one live edge to full weight."""
    from .core import MEMORY_DIR_NAME, check_session_links, resolve_runtime
    from .retrieval import entry_link_sidecars, load_corpus

    root = resolve_runtime(cwd).workspace_root
    sessions_dir = root / MEMORY_DIR_NAME / "sessions"
    corpus = {chunk.entry_id: chunk for chunk in load_corpus(root, granularity="entry") if getattr(chunk, "entry_id", None)}
    chunk = corpus.get(source_entry_id)
    if chunk is None:
        raise LookupError(f"no entry {source_entry_id}")
    sidecar = entry_link_sidecars(root).get(source_entry_id, {})
    target = ref.split("->")[-1].strip().split(" ")[0]
    target_entry = target.split(":")[0]
    live_targets = set()
    for key in ("replaces", "evolves", "related_entries"):
        live_targets.update(sidecar.get(key, ()))
        live_targets.update(getattr(chunk, key, ()) or ())
    live_targets.update(edge[2] for edge in sidecar.get("decision_edges", ()) if len(edge) > 2)
    if target_entry not in {item.split(":")[0].split(" ")[0] for item in live_targets}:
        raise LookupError(f"{source_entry_id} has no live edge to {target_entry}")
    session_date = str(chunk.session_date)
    path = sessions_dir / "links" / session_date[:7] / f"{session_date}.md"
    heading_ts = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
    stamp = (now or datetime.now()).isoformat(timespec="seconds")
    block = "\n".join([
        f"## {heading_ts} - Human verification",
        "",
        "```yaml",
        f"entry_id: {source_entry_id}",
        "source: write-time",
        "verified:",
        f"  - ref: {_yaml_quote(ref)}",
        f"    by: {_yaml_quote(verified_by)}",
        f"    at: {_yaml_quote(stamp)}",
        "```",
        "",
    ])
    original = path.read_text(encoding="utf-8") if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = original or ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + ("\n" if existing else "") + block, encoding="utf-8", newline="\n")
    check = check_session_links(root)
    errors = [issue for issue in check.issues if getattr(issue, "severity", "error") == "error"]
    if errors:
        if original is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(original, encoding="utf-8", newline="\n")
        raise ValueError("links check failed after the verification write; rolled back: " + errors[0].detail)
    return {"entry_id": source_entry_id, "ref": ref, "verified_by": verified_by, "file": str(path.relative_to(root))}
