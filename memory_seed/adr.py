from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .core import (
    _entry_decision_ordinals,
    _known_entry_ids_and_timestamps,
    _walk_entry_bodies,
    entry_body_decisions,
    iter_session_documents,
    read_text_file,
    resolve_runtime,
    write_text_file,
)
from .topics import load_topic_index


ADR_ID_RE = re.compile(r"^adr_[a-z0-9][a-z0-9_-]{0,79}$")
EVENT_ID_RE = re.compile(r"^adre_[a-z0-9][a-z0-9_]{0,63}$")
ADR_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?$"
)
DECISION_REF_RE = re.compile(r"^(mse_[a-z0-9]+|ms-[a-z0-9]+):d([1-9][0-9]*)$")
ENTRY_ID_RE = re.compile(r"^(mse_[a-z0-9]+|ms-[a-z0-9]+)$")
LINK_ASSERTION_RE = re.compile(
    r"^link:(?P<source>(?:mse_[a-z0-9]+|ms-[a-z0-9]+):d[1-9][0-9]*):"
    r"(?P<kind>evolves|replaces):(?P<target>(?:mse_[a-z0-9]+|ms-[a-z0-9]+):d[1-9][0-9]*)$"
)
EVENT_TYPES = {
    "revision-proposed", "revision-accepted", "revision-rejected",
    "reviewed-no-change", "adr-superseded",
}
EVENT_RE = re.compile(
    r"^### (?P<kind>revision-proposed|revision-accepted|revision-rejected|"
    r"reviewed-no-change|adr-superseded) - (?P<timestamp>[^\n]+)\n"
    r"(?P<body>.*?)(?=^### (?:revision-proposed|revision-accepted|revision-rejected|"
    r"reviewed-no-change|adr-superseded) - |\Z)", re.MULTILINE | re.DOTALL,
)
JSON_RE = re.compile(r"```json\s*\n(?P<json>.*?)\n```", re.DOTALL)
ALLOWED_SOURCES = {"write-time", "derived"}


@dataclass(frozen=True)
class AdrPredecessor:
    decision: str
    relation_assertion: str


@dataclass(frozen=True)
class AdrEvent:
    kind: str
    event_id: str
    timestamp: str
    source: str
    decision_ref: str | None = None
    update_entry_id: str | None = None
    expected_authoritative_decision: str | None = None
    predecessors: tuple[AdrPredecessor, ...] = ()
    supporting_decisions: tuple[str, ...] = ()
    matched_decisions: tuple[str, ...] = ()
    decision: str = ""
    why: str = ""
    evolution: str = ""
    reason: str = ""
    replacement_adr: str | None = None


@dataclass(frozen=True)
class AdrState:
    current_status: str
    authoritative_decision: str | None
    revision_statuses: dict[str, str]
    pending_decisions: tuple[str, ...]
    rejected_decisions: tuple[str, ...]
    superseded_by: str | None


@dataclass
class AdrRecord:
    schema_version: int
    adr_id: str
    title: str
    topics: tuple[str, ...]
    created_at: str
    user_initials: str
    agent_type: str
    source: str
    events: list[AdrEvent] = field(default_factory=list)
    path: Path | None = None

    @property
    def state(self) -> AdrState:
        return replay_adr(self)

    @property
    def current_status(self) -> str:
        return self.state.current_status

    @property
    def authoritative_decision(self) -> str | None:
        return self.state.authoritative_decision

    @property
    def current_decision(self) -> str | None:
        proposal = current_proposal(self)
        return self.authoritative_decision or (proposal.decision_ref if proposal else None)

    @property
    def direct_predecessors(self) -> tuple[AdrPredecessor, ...]:
        proposal = current_proposal(self)
        return proposal.predecessors if proposal else ()


@dataclass(frozen=True)
class AdrOperationResult:
    ok: bool
    path: Path | None = None
    adr_id: str | None = None
    current_status: str | None = None
    authoritative_decision: str | None = None
    issues: tuple[str, ...] = ()
    written: bool = False
    rendered: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _event_id(*values: object) -> str:
    raw = json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "adre_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _parse_adr_timestamp(value: str) -> datetime | None:
    """Parse the ADR ledger's ISO-8601 timestamp grammar for validation/order."""
    if not ADR_TIMESTAMP_RE.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _scalar(block: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*([^\n]+?)\s*$", block, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _list(block: str, key: str) -> tuple[str, ...]:
    match = re.search(rf"^{re.escape(key)}:\s*\n(?P<items>(?:\s{{2}}-\s+[^\n]+\n?)*)", block, re.MULTILINE)
    if not match:
        return ()
    return tuple(line.strip()[2:].strip() for line in match.group("items").splitlines())


def _section(block: str, heading: str) -> str:
    match = re.search(rf"^#### {re.escape(heading)}\s*\n(?P<text>.*?)(?=^#### |\Z)", block, re.MULTILINE | re.DOTALL)
    return match.group("text").strip() if match else ""


def proposal_for(record: AdrRecord, decision_ref: str | None) -> AdrEvent | None:
    if decision_ref is None:
        return None
    return next((e for e in record.events if e.kind == "revision-proposed" and e.decision_ref == decision_ref), None)


def replay_adr(record: AdrRecord) -> AdrState:
    statuses: dict[str, str] = {}
    authoritative: str | None = None
    superseded_by: str | None = None
    for event in record.events:
        if event.kind == "revision-proposed" and event.decision_ref:
            statuses[event.decision_ref] = "proposed"
        elif event.kind == "revision-accepted" and event.decision_ref:
            statuses[event.decision_ref] = "accepted"
            authoritative = event.decision_ref
        elif event.kind == "revision-rejected" and event.decision_ref:
            statuses[event.decision_ref] = "rejected"
        elif event.kind == "adr-superseded":
            superseded_by = event.replacement_adr
    pending = tuple(ref for ref, status in statuses.items() if status == "proposed")
    rejected = tuple(ref for ref, status in statuses.items() if status == "rejected")
    status = "superseded" if superseded_by else "accepted" if authoritative else "proposed" if pending else "rejected" if statuses else "invalid"
    return AdrState(status, authoritative, statuses, pending, rejected, superseded_by)


def current_proposal(record: AdrRecord) -> AdrEvent | None:
    accepted = proposal_for(record, replay_adr(record).authoritative_decision)
    if accepted:
        return accepted
    proposals = [event for event in record.events if event.kind == "revision-proposed"]
    return proposals[-1] if proposals else None


def event_to_dict(event: AdrEvent) -> dict[str, Any]:
    return {
        "kind": event.kind, "event_id": event.event_id, "timestamp": event.timestamp,
        "source": event.source, "decision_ref": event.decision_ref,
        "update_entry_id": event.update_entry_id,
        "expected_authoritative_decision": event.expected_authoritative_decision,
        "predecessors": [{"decision": p.decision, "relation_assertion": p.relation_assertion} for p in event.predecessors],
        "supporting_decisions": list(event.supporting_decisions),
        "matched_decisions": list(event.matched_decisions), "decision": event.decision,
        "why": event.why, "evolution": event.evolution, "reason": event.reason,
        "replacement_adr": event.replacement_adr,
    }


def render_event(event: AdrEvent) -> str:
    metadata = {k: v for k, v in event_to_dict(event).items() if k not in {"kind", "timestamp", "decision", "why", "evolution", "reason"} and v not in (None, [], "")}
    lines = [f"### {event.kind} - {event.timestamp}", "", "```json", json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True), "```"]
    for heading, text in (("Decision", event.decision), ("Why", event.why), ("Evolution", event.evolution), ("Reason", event.reason)):
        if text:
            lines.extend(["", f"#### {heading}", "", text])
    return "\n".join(lines)


def render_adr(record: AdrRecord) -> str:
    state, proposal = replay_adr(record), current_proposal(record)
    authority = f"`{state.authoritative_decision}`" if state.authoritative_decision else "not yet accepted"
    front = ["---", "format: memory-seed-adr/1", f"schema_version: {record.schema_version}", f"adr_id: {record.adr_id}", f"title: {record.title}"]
    if record.topics:
        front.extend(["topics:", *(f"  - {topic}" for topic in record.topics)])
    front.extend([f"created_at: {record.created_at}", f"user_initials: {record.user_initials}", f"agent_type: {record.agent_type}", f"source: {record.source}", "---", ""])
    view = [
        f"# {record.title}", "", "## Current view", "", "<!-- memory-seed-derived-current-view:start -->",
        f"Status: **{state.current_status.title()}**", "", f"Authoritative decision: {authority}", "",
        "### Decision", "", proposal.decision if proposal else "Not recorded.", "",
        "### Why", "", proposal.why if proposal else "Not recorded.", "",
        "### How it evolved", "", proposal.evolution if proposal else "No evolution has been recorded.", "",
        "<!-- memory-seed-derived-current-view:end -->", "", "## Event ledger", "", "",
    ]
    events = "\n\n".join(render_event(event) for event in record.events)
    return "\n".join(front + view) + events + "\n"


def parse_adr_text(text: str, *, path: Path | None = None) -> AdrRecord:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("ADR sidecar has no closed YAML frontmatter")
    end = text.find("\n---\n", 4)
    front = text[4:end]
    required = {key: _scalar(front, key) for key in ("schema_version", "adr_id", "title", "created_at", "user_initials", "agent_type", "source")}
    missing = [key for key, value in required.items() if value is None]
    if missing:
        raise ValueError("ADR sidecar is missing frontmatter field(s): " + ", ".join(missing))
    events: list[AdrEvent] = []
    for match in EVENT_RE.finditer(text[end + 5:].lstrip("\n")):
        body = match.group("body")
        json_match = JSON_RE.search(body)
        if not json_match:
            raise ValueError(f"{match.group('kind')} event has no JSON metadata")
        meta = json.loads(json_match.group("json"))
        predecessors = tuple(AdrPredecessor(str(item.get("decision", "")), str(item.get("relation_assertion", ""))) for item in meta.get("predecessors", []) if isinstance(item, Mapping))
        events.append(AdrEvent(
            match.group("kind"), str(meta.get("event_id", "")), match.group("timestamp").strip(), str(meta.get("source", "")),
            meta.get("decision_ref"), meta.get("update_entry_id"), meta.get("expected_authoritative_decision"), predecessors,
            tuple(str(x) for x in meta.get("supporting_decisions", [])), tuple(str(x) for x in meta.get("matched_decisions", [])),
            _section(body, "Decision"), _section(body, "Why"), _section(body, "Evolution"), _section(body, "Reason"), meta.get("replacement_adr"),
        ))
    return AdrRecord(int(required["schema_version"] or "0"), required["adr_id"] or "", required["title"] or "", _list(front, "topics"), required["created_at"] or "", required["user_initials"] or "", required["agent_type"] or "", required["source"] or "", events, path)


def parse_adr(path: Path) -> AdrRecord:
    return parse_adr_text(read_text_file(path), path=path)


def reconcile_adr_records(base: AdrRecord, incoming: AdrRecord) -> tuple[AdrRecord | None, list[str]]:
    """Structurally merge two branch-local ledgers for one concern.

    Exact event duplicates are idempotent; independent append-only events are
    ordered deterministically. A reused event id with different content or a
    transition whose expected head is stale is an explicit conflict.
    """
    issues: list[str] = []
    identity_fields = (
        "schema_version", "adr_id", "title", "topics", "created_at",
        "user_initials", "agent_type", "source",
    )
    for field_name in identity_fields:
        if getattr(base, field_name) != getattr(incoming, field_name):
            issues.append(f"ADR {base.adr_id} has divergent {field_name}")
    events: dict[str, AdrEvent] = {event.event_id: event for event in base.events}
    for event in incoming.events:
        existing = events.get(event.event_id)
        if existing is not None and event_to_dict(existing) != event_to_dict(event):
            issues.append(f"ADR {base.adr_id} event {event.event_id} diverges across branches")
        else:
            events[event.event_id] = event
    if issues:
        return None, issues
    merged = AdrRecord(
        base.schema_version, base.adr_id, base.title, base.topics, base.created_at,
        base.user_initials, base.agent_type, base.source,
        sorted(events.values(), key=lambda event: (event.timestamp, event.event_id)),
        base.path,
    )
    states: dict[str, str] = {}
    authority: str | None = None
    for event in merged.events:
        if event.kind == "revision-proposed" and event.decision_ref:
            if event.decision_ref in states:
                issues.append(f"ADR {base.adr_id} has duplicate revision {event.decision_ref}")
            states[event.decision_ref] = "proposed"
        elif event.kind in {"revision-accepted", "revision-rejected"}:
            ref = event.decision_ref or ""
            if states.get(ref) != "proposed":
                issues.append(f"ADR {base.adr_id} transition targets non-pending revision {ref}")
                continue
            if event.kind == "revision-accepted":
                if event.expected_authoritative_decision != authority:
                    issues.append(
                        f"ADR {base.adr_id} has competing acceptance for {ref}; "
                        f"expected {event.expected_authoritative_decision or 'no head'}, replay has {authority or 'no head'}"
                    )
                elif authority and authority not in ancestors(merged, ref):
                    issues.append(f"ADR {base.adr_id} acceptance {ref} does not descend from {authority}")
                authority = ref
                states[ref] = "accepted"
            else:
                states[ref] = "rejected"
    return (None, issues) if issues else (merged, [])


def _entry_decisions(cwd: str | Path) -> tuple[set[str], dict[str, set[str]]]:
    sessions = resolve_runtime(cwd).memory_dir / "sessions"
    known, _ = _known_entry_ids_and_timestamps(sessions)
    ordinals: dict[str, set[str]] = {}
    for document in iter_session_documents(sessions):
        try:
            text = read_text_file(document.path)
        except (OSError, UnicodeDecodeError):
            continue
        for entry_id, ordinal in _walk_entry_bodies(text, _entry_decision_ordinals):
            ordinals.setdefault(entry_id, set()).add(ordinal)
    return known, ordinals


def _ref_issues(ref: str, known: set[str], ordinals: dict[str, set[str]], label: str, pending: set[str]) -> list[str]:
    match = DECISION_REF_RE.fullmatch(ref)
    if not match:
        return [f"{label} must use '<entry_id>:dN' decision identity"]
    if ref in pending:
        return []
    entry_id, ordinal = match.group(1), f"d{match.group(2)}"
    if entry_id not in known:
        return [f"{label} references missing entry {entry_id}"]
    if ordinal not in ordinals.get(entry_id, set()):
        return [f"{label} references missing decision {ref}"]
    return []


def ancestors(record: AdrRecord, ref: str) -> set[str]:
    proposals = {e.decision_ref: e for e in record.events if e.kind == "revision-proposed"}
    found, queue = set(), [ref]
    while queue:
        proposal = proposals.get(queue.pop())
        if not proposal:
            continue
        for predecessor in proposal.predecessors:
            if predecessor.decision not in found:
                found.add(predecessor.decision)
                queue.append(predecessor.decision)
    return found


def adr_membership(record: AdrRecord) -> set[str]:
    refs: set[str] = set()
    for event in record.events:
        if event.kind == "revision-proposed":
            if event.decision_ref:
                refs.add(event.decision_ref)
            refs.update(item.decision for item in event.predecessors)
    return refs


def validate_adr(record: AdrRecord, cwd: str | Path = ".", *, pending_decisions: Sequence[str] = (), pending_entries: Sequence[str] = ()) -> list[str]:
    known, ordinals = _entry_decisions(cwd)
    pending, pending_entry_ids = set(pending_decisions), set(pending_entries)
    issues: list[str] = []
    if record.schema_version != 1:
        issues.append("unsupported ADR schema_version; expected 1")
    if not ADR_ID_RE.fullmatch(record.adr_id):
        issues.append("adr_id must match adr_<lowercase-slug>")
    if not record.title.strip() or not record.user_initials.strip() or not record.agent_type.strip():
        issues.append("ADR title and creation attribution must be non-empty")
    created_at = _parse_adr_timestamp(record.created_at)
    if created_at is None:
        issues.append("created_at must be an ISO-8601 timestamp")
    if record.source not in ALLOWED_SOURCES:
        issues.append("frontmatter source must be write-time or derived")
    topic_index = load_topic_index(cwd)
    if record.topics and not topic_index.exists:
        issues.append("ADR topics require .memory-seed/topics.yaml")
    else:
        topic_resolution = topic_index.resolution()
        for topic in record.topics:
            if topic not in topic_resolution or topic_resolution[topic] != topic:
                issues.append(f"ADR topic '{topic}' is not a canonical slug in topics.yaml")
    if not record.events:
        return [*issues, "ADR sidecar must contain at least one event"]
    ids: set[str] = set()
    statuses: dict[str, str] = {}
    authoritative: str | None = None
    last_timestamp: datetime | None = None
    superseded = False
    for index, event in enumerate(record.events, 1):
        label = f"event {index} ({event.kind})"
        if event.kind not in EVENT_TYPES:
            issues.append(f"{label} has unsupported type")
        if not EVENT_ID_RE.fullmatch(event.event_id):
            issues.append(f"{label} has malformed event_id")
        if event.event_id in ids:
            issues.append(f"{label} has duplicate event_id")
        ids.add(event.event_id)
        if event.source not in ALLOWED_SOURCES:
            issues.append(f"{label} source must be write-time or derived")
        event_timestamp = _parse_adr_timestamp(event.timestamp)
        if event_timestamp is None:
            issues.append(f"{label} timestamp must be ISO-8601")
        else:
            if created_at is not None and event_timestamp < created_at:
                issues.append(f"{label} predates ADR creation")
            if last_timestamp is not None and event_timestamp < last_timestamp:
                issues.append(f"{label} is not in ascending timestamp order")
            last_timestamp = event_timestamp
        if not event.update_entry_id:
            issues.append(f"{label} requires update_entry_id")
        elif event.update_entry_id not in known | pending_entry_ids:
            issues.append(f"{label} references missing update entry {event.update_entry_id}")
        if event.kind == "revision-proposed":
            ref = event.decision_ref or ""
            issues.extend(_ref_issues(ref, known, ordinals, f"{label} decision", pending))
            if ref in statuses:
                issues.append(f"{label} duplicates revision {ref}")
            statuses[ref] = "proposed"
            if not event.decision.strip() or not event.why.strip():
                issues.append(f"{label} requires Decision and Why")
            for predecessor in event.predecessors:
                issues.extend(_ref_issues(predecessor.decision, known, ordinals, f"{label} predecessor", pending))
                assertion = LINK_ASSERTION_RE.fullmatch(predecessor.relation_assertion)
                if not assertion or assertion.group("source") != ref or assertion.group("target") != predecessor.decision:
                    issues.append(f"{label} predecessor assertion does not match its source and target")
            for supporting in event.supporting_decisions:
                issues.extend(_ref_issues(supporting, known, ordinals, f"{label} supporting decision", pending))
            if ref in ancestors(record, ref):
                issues.append(f"{label} creates a lineage cycle")
        elif event.kind in {"revision-accepted", "revision-rejected"}:
            ref = event.decision_ref or ""
            issues.extend(_ref_issues(ref, known, ordinals, f"{label} decision", pending))
            if statuses.get(ref) != "proposed":
                issues.append(f"{label} targets revision in state {statuses.get(ref) or 'missing'}")
            elif event.kind == "revision-accepted":
                if event.expected_authoritative_decision != authoritative:
                    issues.append(f"{label} has stale expected_authoritative_decision")
                if authoritative and authoritative not in ancestors(record, ref):
                    issues.append(f"{label} does not descend from authoritative decision {authoritative}")
                authoritative, statuses[ref] = ref, "accepted"
            else:
                statuses[ref] = "rejected"
        elif event.kind == "reviewed-no-change":
            if not event.decision_ref or not event.matched_decisions or not event.reason.strip():
                issues.append(f"{label} requires decision_ref, matched_decisions, and Reason")
            for matched in event.matched_decisions:
                if matched not in adr_membership(record):
                    issues.append(f"{label} matched decision {matched} is not in ADR lineage")
        elif event.kind == "adr-superseded":
            if superseded or not authoritative or not event.replacement_adr or not ADR_ID_RE.fullmatch(event.replacement_adr):
                issues.append(f"{label} is invalid ADR supersession")
            if event.expected_authoritative_decision != authoritative:
                issues.append(f"{label} has stale expected_authoritative_decision")
            superseded = True
    if record.events[0].kind != "revision-proposed":
        issues.append("the first ADR event must be revision-proposed")
    return issues


def iter_adrs(cwd: str | Path = ".") -> Iterable[AdrRecord]:
    directory = resolve_runtime(cwd).memory_dir / "decisions"
    if not directory.is_dir():
        return ()
    return tuple(parse_adr(path) for path in sorted(directory.glob("adr_*.md")))


def record_digest(record: AdrRecord) -> str:
    payload = {"adr_id": record.adr_id, "title": record.title, "topics": record.topics, "events": [event_to_dict(item) for item in record.events]}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def adr_to_dict(record: AdrRecord, *, include_events: bool = True) -> dict[str, Any]:
    state, proposal = replay_adr(record), current_proposal(record)
    result: dict[str, Any] = {
        "adr_id": record.adr_id, "title": record.title, "topics": list(record.topics),
        "created_at": record.created_at, "source": record.source,
        "current_status": state.current_status, "authoritative_decision": state.authoritative_decision,
        "pending_decisions": list(state.pending_decisions), "rejected_decisions": list(state.rejected_decisions),
        "superseded_by": state.superseded_by, "membership": sorted(adr_membership(record)),
        "current": {"decision_ref": proposal.decision_ref if proposal else None, "decision": proposal.decision if proposal else "", "why": proposal.why if proposal else "", "evolution": proposal.evolution if proposal else ""},
        "digest": record_digest(record), "path": str(record.path) if record.path else None,
    }
    if include_events:
        result["events"] = [event_to_dict(item) for item in record.events]
    return result


def canonical_decision_refs(cwd: str | Path, raw: str) -> tuple[str, ...]:
    target = raw.split("->", 1)[-1].strip()
    if DECISION_REF_RE.fullmatch(target):
        return (target,)
    match = re.fullmatch(r"(?P<entry>mse_[a-z0-9]+|ms-[a-z0-9]+):(?P<ords>d\d+(?:,d\d+)*)", target)
    if match:
        return tuple(f"{match.group('entry')}:{ordinal}" for ordinal in match.group("ords").split(","))
    if ENTRY_ID_RE.fullmatch(target):
        _, ordinals = _entry_decisions(cwd)
        choices = sorted(ordinals.get(target, set()))
        if len(choices) == 1:
            return (f"{target}:{choices[0]}",)
    return ()


def lifecycle_targets(cwd: str | Path, decisions: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    result: list[str] = []
    for decision in decisions:
        links = decision.get("links")
        if not isinstance(links, Mapping):
            continue
        for kind in ("evolves", "replaces"):
            values = links.get(kind, [])
            if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
                for value in values:
                    if isinstance(value, str):
                        result.extend(canonical_decision_refs(cwd, value))
    return tuple(dict.fromkeys(result))


def _excerpts(cwd: str | Path, wanted: set[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for document in iter_session_documents(resolve_runtime(cwd).memory_dir / "sessions"):
        try:
            text = read_text_file(document.path)
        except (OSError, UnicodeDecodeError):
            continue
        def inspect(body: str) -> list[str]:
            return [json.dumps({"ordinal": item.ordinal, "name": item.name, "text": item.text}) for item in entry_body_decisions(body)]
        for entry_id, encoded in _walk_entry_bodies(text, inspect):
            item = json.loads(encoded)
            ref = f"{entry_id}:{item['ordinal']}"
            if ref in wanted:
                found[ref] = ((item["name"] + "\n") if item["name"] else "") + item["text"]
    return found


def adr_review_context(cwd: str | Path, targets: Sequence[str]) -> list[dict[str, Any]]:
    wanted, contexts = set(targets), []
    matched_records: list[tuple[AdrRecord, list[str]]] = []
    excerpt_refs: set[str] = set()
    for record in iter_adrs(cwd):
        membership = adr_membership(record)
        matched = sorted(wanted & membership)
        if matched:
            matched_records.append((record, matched))
            excerpt_refs.update(membership)
    excerpts = _excerpts(cwd, excerpt_refs)
    for record, matched in matched_records:
        item = adr_to_dict(record)
        item["matched_decisions"] = matched
        item["source_excerpts"] = {
            ref: excerpts.get(ref, "") for ref in sorted(adr_membership(record))
        }
        contexts.append(item)
    return contexts


def review_receipt(cwd: str | Path, *, proposal: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]) -> str:
    payload = {"workspace": str(resolve_runtime(cwd).workspace_root.resolve()), "proposal": proposal, "adrs": sorted((str(item.get("adr_id")), str(item.get("digest"))) for item in contexts)}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return "adrr_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _save(record: AdrRecord, cwd: str | Path, dry_run: bool, *, pending_decisions: Sequence[str] = (), pending_entries: Sequence[str] = ()) -> AdrOperationResult:
    path = record.path or resolve_runtime(cwd).memory_dir / "decisions" / f"{record.adr_id}.md"
    record.path = path
    rendered = render_adr(record)
    issues = validate_adr(record, cwd, pending_decisions=pending_decisions, pending_entries=pending_entries)
    if issues:
        return AdrOperationResult(False, path, record.adr_id, record.current_status, record.authoritative_decision, tuple(issues), False, rendered)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_file(path, rendered)
    return AdrOperationResult(True, path, record.adr_id, record.current_status, record.authoritative_decision, (), not dry_run, rendered if dry_run else None)


def promote_decision(cwd: str | Path = ".", *, adr_id: str, source_entry_id: str, source_decision: str, title: str, topics: Sequence[str], user_initials: str, agent_type: str, source: str, decision: str = "See the authoritative session decision.", why: str = "See the authoritative session decision rationale.", evolution: str = "This is the first revision of this architectural concern.", update_entry_id: str | None = None, direct_predecessors: Sequence[AdrPredecessor] = (), supporting_decisions: Sequence[str] = (), timestamp: str | None = None, dry_run: bool = False) -> AdrOperationResult:
    path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
    if path.exists():
        return AdrOperationResult(False, path, adr_id, issues=("ADR already exists",))
    stamp, ref = timestamp or _now(), f"{source_entry_id}:{source_decision}"
    event = AdrEvent("revision-proposed", _event_id(adr_id, "proposed", ref, stamp), stamp, source, ref, update_entry_id or source_entry_id, predecessors=tuple(direct_predecessors), supporting_decisions=tuple(supporting_decisions), decision=decision, why=why, evolution=evolution)
    return _save(AdrRecord(1, adr_id, title, tuple(dict.fromkeys(topics)), stamp, user_initials, agent_type, source, [event], path), cwd, dry_run)


def revise_adr(cwd: str | Path = ".", *, adr_id: str, decision_ref: str, decision: str, why: str, evolution: str, update_entry_id: str, source: str, predecessors: Sequence[AdrPredecessor], supporting_decisions: Sequence[str] = (), timestamp: str | None = None, dry_run: bool = False) -> AdrOperationResult:
    path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
    if not path.exists():
        return AdrOperationResult(False, path, adr_id, issues=("ADR does not exist",))
    record, stamp = parse_adr(path), timestamp or _now()
    record.events.append(AdrEvent("revision-proposed", _event_id(adr_id, "proposed", decision_ref, stamp), stamp, source, decision_ref, update_entry_id, predecessors=tuple(predecessors), supporting_decisions=tuple(supporting_decisions), decision=decision, why=why, evolution=evolution))
    return _save(record, cwd, dry_run)


def transition_adr(cwd: str | Path = ".", *, adr_id: str, status: str, decision_ref: str | None = None, update_entry_id: str, expected_authoritative_decision: str | None = None, expected_previous_status: str | None = None, source: str, replacement_adr: str | None = None, reason: str = "", timestamp: str | None = None, dry_run: bool = False) -> AdrOperationResult:
    path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
    if not path.exists():
        return AdrOperationResult(False, path, adr_id, issues=("ADR does not exist",))
    record, stamp = parse_adr(path), timestamp or _now()
    if expected_previous_status and record.current_status != expected_previous_status:
        return AdrOperationResult(False, path, adr_id, record.current_status, record.authoritative_decision, (f"expected previous status {expected_previous_status}, current status is {record.current_status}",))
    if decision_ref is None and status in {"accepted", "rejected"}:
        pending = replay_adr(record).pending_decisions
        decision_ref = pending[-1] if len(pending) == 1 else None
    kind = {"accepted": "revision-accepted", "rejected": "revision-rejected", "superseded": "adr-superseded"}.get(status)
    if not kind:
        return AdrOperationResult(False, path, adr_id, issues=("unsupported ADR status",))
    if expected_authoritative_decision is None and expected_previous_status == "proposed":
        expected_authoritative_decision = record.authoritative_decision
    record.events.append(AdrEvent(kind, _event_id(adr_id, kind, decision_ref, update_entry_id, stamp), stamp, source, decision_ref, update_entry_id, expected_authoritative_decision, reason=reason, replacement_adr=replacement_adr))
    return _save(record, cwd, dry_run)


def append_outcome_event(record: AdrRecord, *, outcome: Mapping[str, Any], decision_ref: str, matched_decisions: Sequence[str], update_entry_id: str, timestamp: str, source: str = "write-time") -> None:
    kind = str(outcome.get("outcome", ""))
    event: AdrEvent | None = None
    if kind == "revise":
        assertions = outcome.get("assertions", {}) if isinstance(outcome.get("assertions"), Mapping) else {}
        predecessors = tuple(AdrPredecessor(item, str(assertions.get(item, ""))) for item in matched_decisions)
        event = AdrEvent("revision-proposed", _event_id(record.adr_id, "proposed", decision_ref, timestamp), timestamp, source, decision_ref, update_entry_id, predecessors=predecessors, decision=str(outcome.get("decision", "")), why=str(outcome.get("why", "")), evolution=str(outcome.get("evolution", "")))
    elif kind == "no-change":
        event = AdrEvent("reviewed-no-change", _event_id(record.adr_id, "no-change", decision_ref, timestamp), timestamp, source, decision_ref, update_entry_id, matched_decisions=tuple(matched_decisions), reason=str(outcome.get("reason", "")))
    if event is not None and all(existing.event_id != event.event_id for existing in record.events):
        record.events.append(event)


def check_adrs(cwd: str | Path = ".") -> tuple[bool, list[str]]:
    issues, seen = [], set()
    directory = resolve_runtime(cwd).memory_dir / "decisions"
    if not directory.is_dir():
        return True, []
    for path in sorted(directory.glob("*.md")):
        try:
            record = parse_adr(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(f"{path}: {exc}")
            continue
        if record.adr_id in seen:
            issues.append(f"{path}: duplicate ADR id {record.adr_id}")
        seen.add(record.adr_id)
        issues.extend(f"{path}: {issue}" for issue in validate_adr(record, cwd))
        if render_adr(record) != read_text_file(path):
            issues.append(f"{path}: derived Current view is stale")
    return not issues, issues
