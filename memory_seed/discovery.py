"""Planning-time authority lookup and link carry-forward for Design Discovery.

Two read-only steps, both built on existing machinery:

``discovery_evidence``
    Resolve the ``design-discovery`` retrieval profile for a topic/area:
    related decisions, the ADRs that own the area (Current view), and the
    Constitution clauses that govern it (the shared clause cascade).  A free
    text ``query`` runs ``memory_search`` with ``preferred_keywords`` first and
    pins its decision hits, so the pack itself stays deterministic and
    fingerprinted.

``discovery_assess``
    Record the agent's (or user's) relation to each evidence item - the
    Discovery Record's authority answer - and turn it into the exact
    ``decisions[].links`` envelope, ``consulted`` list and ADR outcomes the
    plan-approval ``memory_session_append`` needs.  Verdicts may name only
    evidence in the pack (a closed candidate list), and graph distance never
    becomes a relation: only a verdict does.

Nothing here writes memory.  ``no-edge`` verdicts are authoring-time evidence
and are not persisted (``mse_a7zs346tqznzpexn``: no new store).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

DISCOVERY_PROFILE = ("design-discovery", 1)
RELATIONS = ("replaces", "refines", "builds-on", "related", "no-edge", "conflicts", "governed-by")
# The relation each evidence kind may take.  Links target session decisions;
# an ADR verdict links to the ADR's authoritative decision.  A Constitution
# clause governs - it is never a link target.
_KIND_RELATIONS = {
    "decision": {"replaces", "refines", "builds-on", "related", "no-edge", "conflicts"},
    "session": {"related", "no-edge", "conflicts"},
    "adr": {"replaces", "refines", "builds-on", "related", "no-edge", "conflicts"},
    "constitution": {"governed-by", "no-edge", "conflicts"},
    "markdown": {"no-edge", "conflicts"},
}
_WHY_REQUIRED = {"replaces", "refines", "builds-on", "conflicts", "governed-by"}
_DECISION_REF_RE = re.compile(r"^(mse_[0-9a-z]{8,32}|ms-[0-9a-f]{8}):(d[1-9][0-9]*)$")
_ORDINAL_RE = re.compile(r"^d[1-9][0-9]*$")


class DiscoveryError(ValueError):
    def __init__(self, message: str, *, issues: Sequence[str] = ()) -> None:
        self.issues = list(issues) or [message]
        super().__init__(message)


def _decision_ref(value: str) -> str:
    return value if ":" in value else f"{value}:d1"


def _decision_index(cwd: str | Path) -> dict[str, Any]:
    from .retrieval import load_corpus

    return {chunk.chunk_id: chunk for chunk in load_corpus(cwd, granularity="decision")}


def _search_pins(
    cwd: str | Path, query: str, keywords: Sequence[str], limit: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from .retrieval import search_memory

    result = search_memory(
        query,
        cwd,
        preferred_keywords=list(keywords),
        top_k=limit,
        granularity="decision",
    )
    pins: list[dict[str, Any]] = []
    hits: list[dict[str, Any]] = []
    for row in result.get("results", []):
        ref = _decision_ref(str(row.get("chunk_id", "")))
        if not _DECISION_REF_RE.match(ref) or any(pin["id"] == ref for pin in pins):
            continue
        pins.append(
            {
                "kind": "decision",
                "id": ref,
                "reason": f"memory_search hit for the discovery query (score {row.get('score')})",
                # Required so the hits sort first and survive the budget: they
                # are the most query-specific evidence the lookup has.
                "required": True,
            }
        )
        heading = row.get("heading_path") or []
        hits.append(
            {
                "ref": ref,
                "title": heading[-1] if heading else "",
                "score": row.get("score"),
                "matched_preferred_keywords": row.get("matched_preferred_keywords", []),
            }
        )
    return pins, hits


def discovery_evidence(
    cwd: str | Path = ".",
    *,
    topics: Sequence[str] = (),
    keywords: Sequence[str] = (),
    pins: Sequence[str] = (),
    paths: Sequence[str] = (),
    query: str | None = None,
    search_limit: int = 5,
    profile: tuple[str, int] = DISCOVERY_PROFILE,
) -> dict[str, Any]:
    """Resolve the authority and evidence a design in this area must answer to."""
    from .retrieval import RetrievalSpecResolutionError, resolve_retrieval_spec
    from .retrieval_profiles import load_retrieval_profile

    pinned: list[dict[str, Any]] = []
    for value in pins:
        value = value.strip()
        if value.startswith("adr_"):
            pinned.append({"kind": "adr", "id": value, "reason": "named by the discovery request", "required": True})
        else:
            ref = _decision_ref(value)
            if not _DECISION_REF_RE.match(ref):
                raise DiscoveryError(f"pin {value!r} is neither an ADR id nor '<entry-id>[:dN]'")
            pinned.append({"kind": "decision", "id": ref, "reason": "named by the discovery request", "required": True})
    search_hits: list[dict[str, Any]] = []
    if query:
        found, search_hits = _search_pins(cwd, query, keywords, search_limit)
        pinned.extend(pin for pin in found if all(pin["id"] != other["id"] for other in pinned))

    overrides: dict[str, Any] = {"filters": {"topics": list(topics), "paths": list(paths)}}
    if pinned:
        overrides["selectors"] = {"pinned": pinned}
    if keywords:
        overrides["constitution"] = {"keywords": list(keywords)}
    spec = load_retrieval_profile(profile[0], profile[1], cwd, overrides=overrides)
    request = {
        "topics": list(topics),
        "keywords": list(keywords),
        "pins": [pin["id"] for pin in pinned],
        "paths": list(paths),
        "query": query,
    }
    try:
        pack = resolve_retrieval_spec(spec, cwd, _timeout_ms=120_000)
    except RetrievalSpecResolutionError as exc:
        if exc.code != "missing_required" or exc.stage != "required_coverage":
            raise
        # Advisory by design: an area with no recorded history is a finding,
        # not an error - the Discovery Record says so and planning continues.
        return {
            "ok": True,
            "empty": True,
            "request": request,
            "search_hits": search_hits,
            "warnings": [
                {
                    "code": "no_prior_evidence",
                    "detail": "no decision matched these topics, paths or pins: "
                    + ", ".join(exc.details.get("clauses", [])),
                }
            ],
            "pack": None,
            "summary": {"adrs": [], "decisions": [], "constitution": []},
        }
    return {
        "ok": True,
        "empty": False,
        "request": request,
        "search_hits": search_hits,
        "warnings": pack["warnings"],
        "pack": pack,
        "summary": _summarize(pack, cwd),
    }


def _summarize(pack: Mapping[str, Any], cwd: str | Path) -> dict[str, list[dict[str, Any]]]:
    from .adr import parse_adr
    from .core import resolve_runtime

    root = resolve_runtime(cwd).workspace_root
    decisions = _decision_index(cwd)
    headings = (pack.get("constitution") or {}).get("clause_headings", {})
    summary: dict[str, list[dict[str, Any]]] = {"adrs": [], "decisions": [], "constitution": []}
    for item in pack["evidence"]:
        row = {
            "ref": item["id"],
            "graph_distance": item["graph_distance"],
            "selected_by": item["selected_by"],
            "reasons": item["reasons"],
        }
        if item["kind"] == "adr":
            try:
                record = parse_adr(root / item["source"])
                row.update(
                    title=record.title,
                    status=record.current_status,
                    head=record.authoritative_decision,
                    topics=list(record.topics),
                )
            except (OSError, ValueError):
                row["title"] = item["id"]
            summary["adrs"].append(row)
        elif item["kind"] == "constitution":
            row["title"] = _clause_title(item, cwd) if item["id"] in headings else item["id"]
            summary["constitution"].append(row)
        elif item["kind"] in {"decision", "session"}:
            chunk = decisions.get(item["id"])
            heading = list(getattr(chunk, "heading_path", ()) or ())
            row["title"] = heading[-1] if heading else item["id"]
            row["date"] = item.get("session_date")
            summary["decisions"].append(row)
    summary["adrs"].sort(key=lambda row: (row["graph_distance"] or 0, row["ref"]))
    summary["decisions"].sort(key=lambda row: (row["graph_distance"] or 0, row["ref"]))
    return summary


def _link_ref(target: str, decisions: Mapping[str, Any]) -> str:
    """``entry:dN`` as the append wants it: bare when the entry has one decision."""
    entry, _, ordinal = target.partition(":")
    siblings = sum(1 for key in decisions if key.split(":", 1)[0] == entry)
    return entry if ordinal and siblings <= 1 else target


def _clause_title(item: Mapping[str, Any], cwd: str | Path) -> str:
    """A clause's first prose line (its bold lead, usually), trimmed for a table."""
    from .core import resolve_runtime

    try:
        lines = (resolve_runtime(cwd).workspace_root / item["source"]).read_text(encoding="utf-8").splitlines()
    except OSError:
        return str(item["id"])
    start, end = item["line_range"]
    for line in lines[start - 1 : end]:
        text = line.strip()
        if text and not text.startswith("<!--"):
            text = re.sub(r"^[-*]\s+|\*\*", "", text)
            return text if len(text) <= 90 else text[:87].rstrip() + "..."
    return str(item["id"])


def _candidate_state(item: Mapping[str, Any], cwd: str | Path, decisions: Mapping[str, Any]) -> dict[str, Any]:
    """Authority, lifecycle status, recorded topics and link target of one item."""
    from .adr import parse_adr
    from .core import resolve_runtime

    kind = item["kind"]
    if kind == "adr":
        record = parse_adr(resolve_runtime(cwd).workspace_root / item["source"])
        return {
            "authority": "accepted_adr" if record.current_status == "accepted" else "session_evidence",
            "status": "active" if record.current_status == "accepted" else record.current_status,
            "topics": list(record.topics),
            "title": record.title,
            "link_target": record.authoritative_decision,
            "adr_id": record.adr_id,
        }
    if kind == "constitution":
        return {
            "authority": "constitution",
            "status": "active",
            "topics": [],
            "title": _clause_title(item, cwd),
            "link_target": None,
        }
    if kind in {"decision", "session"}:
        chunk = decisions.get(item["id"])
        topics = list(dict.fromkeys([*getattr(chunk, "topics", ()), *getattr(chunk, "inferred_topics", ())]))
        heading = list(getattr(chunk, "heading_path", ()) or ())
        return {
            "authority": "session_evidence",
            "status": "superseded" if getattr(chunk, "replaced_by", None) else "active",
            "topics": topics,
            "title": heading[-1] if heading else item["id"],
            "link_target": item["id"] if kind == "decision" else None,
        }
    return {"authority": "derived_projection", "status": "active", "topics": [], "title": item["id"], "link_target": None}


def _applicability(state: Mapping[str, Any], ref: str, task_topics: Sequence[str], cwd: str | Path) -> dict[str, Any]:
    """Reuse the planning assessment; unclassifiable input is reported, not fatal."""
    from .planning import PlanningCandidate, PlanningValidationError, assess_candidate
    from .topics import load_topic_index

    if state["authority"] == "constitution":
        return {"applicability": "applicable", "reason": "Governing Constitution clause selected for this area."}
    index = load_topic_index(cwd)
    resolution = index.resolution()
    try:
        assessment = assess_candidate(
            PlanningCandidate(
                reference=ref,
                decision=state["title"] or ref,
                authority=state["authority"],
                topics=tuple(topic for topic in state["topics"] if topic in resolution),
                status=state["status"] if state["status"] in {"active", "proposed", "superseded", "rejected", "withdrawn"} else "active",
            ),
            [topic for topic in task_topics if topic in resolution],
            index,
        )
    except PlanningValidationError as exc:
        return {"applicability": "unclassified", "reason": str(exc)}
    return {"applicability": assessment.applicability, "reason": assessment.reason}


def discovery_assess(
    cwd: str | Path = ".",
    *,
    pack: Mapping[str, Any],
    verdicts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate the authority answer and build the plan-approval link envelope.

    Each verdict is ``{ref, relation, why, applies_to}``: ``ref`` an evidence
    id from the pack; ``relation`` one of ``RELATIONS`` (allowed per kind);
    ``why`` one line, required for every lifecycle, conflict or governing
    relation; ``applies_to`` the planned decision ordinals (default ``["d1"]``).
    """
    from .adr import adr_review_context
    from .adr import lifecycle_targets as gate_lifecycle_targets
    from .core import existing_refines_targets, resolve_runtime
    from .retrieval import RetrievalSpecResolutionError, validate_evidence_pack

    try:
        validate_evidence_pack(pack, cwd)
    except RetrievalSpecResolutionError as exc:
        raise DiscoveryError(
            f"the evidence pack is no longer current ({exc.code}); re-run discovery evidence",
            issues=[exc.message],
        ) from exc
    in_pack = {item["id"]: item for item in pack["evidence"]}
    task_topics = list(pack["effective_spec"]["filters"]["topics"])
    decisions = _decision_index(cwd)
    runtime = resolve_runtime(cwd)
    refines_taken = existing_refines_targets(runtime.memory_dir / "sessions")

    issues: list[str] = []
    rows: list[dict[str, Any]] = []
    links: dict[str, dict[str, list[Any]]] = {}
    consulted: list[str] = []
    governing: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    refines_claimed: dict[str, str] = {}
    lifecycle_targets: list[str] = []
    for index, verdict in enumerate(verdicts):
        label = f"verdicts[{index}]"
        if not isinstance(verdict, Mapping):
            issues.append(f"{label} must be an object")
            continue
        unknown = set(verdict) - {"ref", "relation", "why", "applies_to"}
        if unknown:
            issues.append(f"{label} has unsupported field(s): {', '.join(sorted(unknown))}")
        ref = str(verdict.get("ref", "")).strip()
        relation = str(verdict.get("relation", "")).strip()
        why = " ".join(str(verdict.get("why") or "").split())
        applies_to = verdict.get("applies_to") or ["d1"]
        item = in_pack.get(ref)
        if item is None:
            issues.append(f"{label}.ref {ref!r} is not in the evidence pack; verdicts name only retrieved evidence")
            continue
        if relation not in RELATIONS:
            issues.append(f"{label}.relation must be one of {', '.join(RELATIONS)}")
            continue
        allowed = _KIND_RELATIONS.get(item["kind"], {"no-edge"})
        if relation not in allowed:
            issues.append(f"{label}: a {item['kind']} cannot be '{relation}' (allowed: {', '.join(sorted(allowed))})")
            continue
        if relation in _WHY_REQUIRED and not why:
            issues.append(f"{label}: '{relation}' needs a one-line 'why'")
            continue
        if not isinstance(applies_to, list) or not all(isinstance(value, str) and _ORDINAL_RE.match(value) for value in applies_to):
            issues.append(f"{label}.applies_to must be a list of planned decision ordinals like 'd1'")
            continue
        state = _candidate_state(item, cwd, decisions)
        target = state.get("link_target")
        if relation in {"replaces", "refines", "builds-on", "related"} and not target:
            issues.append(f"{label}: {ref} has no decision to link to (an ADR without an authoritative decision)")
            continue
        if relation == "refines":
            entry, _, ordinal = str(target).partition(":")
            holder = refines_taken.get((entry, ordinal or "d1"))
            if holder:
                issues.append(
                    f"{label}: {target} is already refined by {holder}; refine that successor or use builds-on"
                )
                continue
            if target in refines_claimed:
                issues.append(f"{label}: {target} is refined twice in this plan ({refines_claimed[target]} and {applies_to})")
                continue
            refines_claimed[str(target)] = ",".join(applies_to)
        # `consulted` ranks link suggestions by entry id, so it names the
        # session entry behind each decision (an ADR by its head); clauses and
        # documents are authority, not link candidates.
        if target:
            entry_id = str(target).split(":", 1)[0]
            if entry_id not in consulted:
                consulted.append(entry_id)
        # The append names a single-decision entry by its bare id.
        link_ref = _link_ref(str(target), decisions) if target else None
        for ordinal in applies_to:
            envelope = links.setdefault(ordinal, {"replaces": [], "evolves": [], "related_entries": []})
            if relation == "replaces":
                envelope["replaces"].append({"ref": link_ref, "why": why})
            elif relation in {"refines", "builds-on"}:
                envelope["evolves"].append({"ref": link_ref, "type": relation, "why": why})
            elif relation == "related":
                if link_ref not in envelope["related_entries"]:
                    envelope["related_entries"].append(link_ref)
        if relation in {"replaces", "refines", "builds-on"}:
            lifecycle_targets.append(str(target))
        if relation == "governed-by":
            governing.append({"ref": ref, "why": why})
        if relation == "conflicts":
            conflicts.append({"ref": ref, "why": why, "question": f"The design conflicts with {ref}: {why} - revise the design, or revise that authority?"})
        rows.append(
            {
                "ref": ref,
                "kind": item["kind"],
                "title": state["title"],
                "relation": relation,
                "why": why,
                "applies_to": applies_to,
                "link_target": target if relation in {"replaces", "refines", "builds-on", "related"} else None,
                **_applicability(state, ref, task_topics, cwd),
            }
        )
    if issues:
        raise DiscoveryError("the authority answer has problems", issues=issues)

    # ADR membership is surfaced now, at planning time, instead of by the
    # append's zero-write first call.  The receipt gate still runs then.
    # The same target computation the append's gate runs, so the outcomes
    # listed here are exactly the ones it will ask for.
    adr_outcomes: list[dict[str, Any]] = []
    gate_targets = gate_lifecycle_targets(cwd, [{"links": value} for value in links.values()])
    if gate_targets:
        for match in adr_review_context(cwd, gate_targets):
            adr_outcomes.append(
                {
                    "adr_id": match.get("adr_id"),
                    "title": match.get("title"),
                    "matched_decisions": list(match.get("matched_decisions", [])),
                    "needs": "an ADR outcome in decisions[].adrs: no-change {reason} or revise {decision, reason, impact}",
                }
            )
    for row in rows:
        row["adr_outcome_needed"] = any(
            row["link_target"] in outcome["matched_decisions"] for outcome in adr_outcomes
        ) if row["link_target"] else False

    envelope = {
        ordinal: {kind: values for kind, values in value.items() if values}
        for ordinal, value in sorted(links.items())
    }
    return {
        "ok": True,
        "pack_fingerprint": pack["fingerprint"],
        "authority_answer": rows,
        "authority_table": _authority_table(rows),
        "links": envelope,
        "decisions": [{"decision": ordinal, "links": value} for ordinal, value in envelope.items()],
        "consulted": consulted,
        "governing_clauses": governing,
        "conflicts": conflicts,
        "adr_outcomes_needed": adr_outcomes,
        "note": (
            "Pass `decisions` (add topics/origin and any ADR outcomes) and `consulted` to "
            "memory_session_append when the plan is approved. no-edge verdicts are not persisted."
        ),
    }


_AUTHORITY_ORDER = {"constitution": 0, "adr": 1, "decision": 2, "session": 2, "markdown": 3}


def _authority_table(rows: Sequence[Mapping[str, Any]]) -> str:
    """The Discovery Record's authority answer, in authority order."""
    ordered = sorted(rows, key=lambda row: (_AUTHORITY_ORDER.get(row["kind"], 9), row["ref"]))
    lines = [
        "| Ref | Kind | Title | Relation | Why | Applies | ADR outcome |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in ordered:
        title = str(row["title"]).replace("|", "/")
        why = str(row["why"]).replace("|", "/")
        lines.append(
            f"| `{row['ref']}` | {row['kind']} | {title} | {row['relation']} | {why} | "
            f"{row['applicability']} | {'needed' if row.get('adr_outcome_needed') else '-'} |"
        )
    return "\n".join(lines)
