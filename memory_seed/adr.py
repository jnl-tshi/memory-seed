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
# `context-added` (2026-08-07) is the SOFT half of attachment: it records decisions that inform a
# concern without claiming to move it. It touches no head and no status, so it is the only way to
# attach evidence to an ADR whose status must not change - notably one recording a REJECTED
# decision, where accepting a head would read as "this revision was accepted" rather than "we
# decided against this". Hard attachment stays `revision-proposed` (decision_ref + predecessors =
# membership, which is what triggers the MCP review gate); soft attachment costs nothing.
EVENT_TYPES = {
    "revision-proposed", "revision-accepted", "revision-rejected",
    "reviewed-no-change", "adr-superseded", "context-added",
}
EVENT_RE = re.compile(
    r"^### (?P<kind>revision-proposed|revision-accepted|revision-rejected|"
    r"reviewed-no-change|adr-superseded|context-added) - (?P<timestamp>[^\n]+)\n"
    r"(?P<body>.*?)(?=^### (?:revision-proposed|revision-accepted|revision-rejected|"
    r"reviewed-no-change|adr-superseded|context-added) - |\Z)", re.MULTILINE | re.DOTALL,
)
JSON_RE = re.compile(r"```json\s*\n(?P<json>.*?)\n```", re.DOTALL)
# Any `### <lowercase-kind> - <stamp>` heading is an event heading. Current-view sections
# ("### Decision", "### Why", "### Constitution") are capitalised and carry no " - <stamp>", so
# this cannot mistake one for the other.
EVENT_HEADING_RE = re.compile(r"^### (?P<kind>[a-z][a-z0-9-]*) - \S", re.MULTILINE)
ALLOWED_SOURCES = {"write-time", "derived"}
ADR_SCHEMA_VERSIONS = {1, 2}
IMPACT_PROVENANCE = {"preserved", "reconstructed", "not-recorded"}

# Constitution bindings live IN the ADR event ledger (JNL, 2026-08-06: "why can't the adr
# reference the constitution location directly?") rather than a separate sidecar family. A ref
# resolves against the anchor markers in docs/CONSTITUTION.md; `governing` names the clause the
# concern answers to, `supporting` a clause it touches.
CONSTITUTION_REF_RE = re.compile(r"^constitution:v\d+#[a-z0-9][a-z0-9-]*$")
CONSTITUTION_ANCHOR_RE = re.compile(r"<!--\s*constitution-ref:\s*(constitution:v\d+#[a-z0-9-]+)\s*-->")
ALLOWED_BINDING_ROLES = {"governing", "supporting"}

# Founding sources let an ADR exist before any session decision does. Two shapes: a control-file
# line (the index/policy bullet being lifted, e.g. ".memory-seed/index.md#L134") or the literal
# "bootstrap" (S3: a fresh project has no session corpus at all, so the machinery must support
# decision-less founding). A founding event carries a verbatim grounding quote instead of a
# decision_ref; later `revise` events attach real decisions as work touches the concern.
FOUNDING_SOURCE_RE = re.compile(r"^(bootstrap|[^\s#]+\.(?:md|yaml)#L\d+(?:-L?\d+)?)$")


@dataclass(frozen=True)
class AdrPredecessor:
    decision: str
    relation_assertion: str


@dataclass(frozen=True)
class ConstitutionRef:
    ref: str
    role: str


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
    # Optional extensions (2026-08-06). Both render omit-empty, so every ADR written before they
    # existed stays byte-canonical.
    constitution_refs: tuple[ConstitutionRef, ...] = ()
    founding_source: str | None = None
    founding_quote: str = ""
    # v2 keeps the three human sections uniform.  The legacy fields remain only so schema-v1
    # records and callers can be read without rewriting history.
    impact: str = ""
    impact_provenance: str = "preserved"
    impact_evidence: tuple[str, ...] = ()
    body_issues: tuple[str, ...] | None = None

    @property
    def revision_key(self) -> str | None:
        """The key a revision is tracked under: its decision_ref, or a founding pseudo-ref."""
        if self.decision_ref:
            return self.decision_ref
        if self.founding_source:
            return f"founding:{self.founding_source}"
        return None


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
    format_version: int = 1

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


@dataclass(frozen=True)
class AdrAppendReviewPreflight:
    """Shared ADR review result for CLI and MCP session append surfaces."""

    ok: bool
    review_required: bool
    receipt: str
    targets: tuple[str, ...]
    contexts: tuple[dict[str, Any], ...]
    outcomes: dict[str, tuple[str, dict[str, Any]]]
    issues: tuple[str, ...] = ()


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


def _canonical_reason(event: AdrEvent) -> str:
    """Return the v2 Reason, falling back to the v1 Why field."""
    return event.reason or event.why


def _canonical_impact(event: AdrEvent) -> str:
    """Return the v2 Impact, falling back to the v1 Evolution field."""
    return event.impact or event.evolution


def _v2_body_issues(body: str) -> tuple[str, ...]:
    """Validate the authored v2 event body before it becomes replay input."""
    issues: list[str] = []
    json_blocks = list(JSON_RE.finditer(body))
    if len(json_blocks) != 1:
        issues.append("requires exactly one JSON metadata envelope")
    headings = re.findall(r"^#### ([^\n]+)\s*$", body, re.MULTILINE)
    expected = ["Decision", "Reason", "Impact"]
    if headings != expected:
        issues.append("requires exactly one Decision, Reason, Impact section in that order")
    remainder = JSON_RE.sub("", body)
    remainder = re.sub(r"^#### [^\n]+\s*\n.*?(?=^#### |\Z)", "", remainder,
                       flags=re.MULTILINE | re.DOTALL)
    if remainder.strip():
        issues.append("contains prose outside its JSON envelope and canonical sections")
    return tuple(issues)


def proposal_for(record: AdrRecord, decision_ref: str | None) -> AdrEvent | None:
    if decision_ref is None:
        return None
    # Matches on revision_key so founding pseudo-refs ("founding:<source>") resolve to their
    # proposal exactly as decision refs do. The LAST match wins: a ref whose proposal was rejected
    # may be proposed again with corrected text, and the live proposal is the newest one.
    matches = [e for e in record.events if e.kind == "revision-proposed" and e.revision_key == decision_ref]
    return matches[-1] if matches else None


@dataclass
class _Replay:
    """Mutable cursor for one pass of the ADR state machine."""

    statuses: dict[str, str] = field(default_factory=dict)
    authoritative: str | None = None
    superseded_by: str | None = None


def _replay_step(cursor: _Replay, event: AdrEvent, record: AdrRecord, phrase: Any) -> list[str]:
    """Advance the state machine by ONE event, reporting any state violation.

    **This is the only copy of the replay rules.** `replay_adr`, `validate_adr` and
    `reconcile_adr_records` all drive this cursor rather than keeping their own loops. They used to
    keep three, and the divergence bit twice with the same signature both times: a rule changed in
    one copy, the checks that run it went green, and the copy nobody remembered refused the work
    later. The founding extension missed this loop first; the 2026-08-08 re-proposal relaxation
    missed it again and `session merge-branch` - which validates with the RECONCILER - refused 25
    ADRs that `adr check` had just passed.

    Wording still differs per caller, and legitimately: `validate_adr` reports against one file's
    event list ("event 4 (revision-proposed) ..."), the reconciler against a merge of two branches
    ("ADR x has competing acceptance ..."). So `phrase(code, **kw)` renders each violation in the
    caller's voice, and returning None opts a caller out of reporting that code at all. What must
    never diverge again is the TRANSITIONS, and those live here.
    """
    issues: list[str] = []

    def report(code: str, **kwargs: Any) -> None:
        text = phrase(code, **kwargs)
        if text:
            issues.append(text)

    key = event.revision_key
    ref = key or ""
    if event.kind == "revision-proposed":
        # Only a LIVE ref is a duplicate. A rejected one reopens, which is the only way to correct
        # a revision's wording: the text is fixed at proposal time and the ledger is append-only.
        if cursor.statuses.get(ref) in {"proposed", "accepted"}:
            report("duplicate", ref=ref)
        if key:
            cursor.statuses[ref] = "proposed"
    elif event.kind in {"revision-accepted", "revision-rejected"}:
        if cursor.statuses.get(ref) != "proposed":
            report("non_pending", ref=ref, state=cursor.statuses.get(ref))
        elif event.kind == "revision-accepted":
            if event.expected_authoritative_decision != cursor.authoritative:
                report("stale_expected", ref=ref,
                       expected=event.expected_authoritative_decision)
            # A founding head is a PLACEHOLDER for "this concern as recorded in the control file",
            # not a decision in the lineage graph - so nothing can descend from it, and requiring
            # descent would strand every founded ADR at its founding head forever. Descent is still
            # required between two real decisions.
            elif (cursor.authoritative and not cursor.authoritative.startswith("founding:")
                    and cursor.authoritative not in ancestors(record, ref)):
                report("no_descent", ref=ref, authoritative=cursor.authoritative)
            cursor.authoritative = ref
            cursor.statuses[ref] = "accepted"
        else:
            cursor.statuses[ref] = "rejected"
    elif event.kind == "adr-superseded":
        if (cursor.superseded_by or not cursor.authoritative or not event.replacement_adr
                or not ADR_ID_RE.fullmatch(event.replacement_adr or "")):
            report("bad_supersession")
        if event.expected_authoritative_decision != cursor.authoritative:
            report("stale_expected_supersede", expected=event.expected_authoritative_decision)
        cursor.superseded_by = event.replacement_adr
    return issues


def _silent(_code: str, **_kwargs: Any) -> None:
    """Phrase renderer for callers that want the state machine but none of its complaints."""
    return None


def replay_adr(record: AdrRecord) -> AdrState:
    cursor = _Replay()
    for event in record.events:
        _replay_step(cursor, event, record, _silent)
    statuses = cursor.statuses
    pending = tuple(ref for ref, status in statuses.items() if status == "proposed")
    rejected = tuple(ref for ref, status in statuses.items() if status == "rejected")
    status = "superseded" if cursor.superseded_by else "accepted" if cursor.authoritative else "proposed" if pending else "rejected" if statuses else "invalid"
    return AdrState(status, cursor.authoritative, statuses, pending, rejected, cursor.superseded_by)


def current_proposal(record: AdrRecord) -> AdrEvent | None:
    accepted = proposal_for(record, replay_adr(record).authoritative_decision)
    if accepted:
        return accepted
    proposals = [event for event in record.events if event.kind == "revision-proposed"]
    return proposals[-1] if proposals else None


def event_to_dict(event: AdrEvent) -> dict[str, Any]:
    reason, impact = _canonical_reason(event), _canonical_impact(event)
    return {
        "kind": event.kind, "event_id": event.event_id, "timestamp": event.timestamp,
        "source": event.source, "decision_ref": event.decision_ref,
        "update_entry_id": event.update_entry_id,
        "expected_authoritative_decision": event.expected_authoritative_decision,
        "predecessors": [{"decision": p.decision, "relation_assertion": p.relation_assertion} for p in event.predecessors],
        "supporting_decisions": list(event.supporting_decisions),
        "matched_decisions": list(event.matched_decisions), "decision": event.decision,
        "reason": reason, "impact": impact,
        "impact_provenance": event.impact_provenance,
        "impact_evidence": list(event.impact_evidence),
        # Compatibility aliases for v1 API consumers.  New code must use reason/impact.
        "why": reason, "evolution": impact,
        "replacement_adr": event.replacement_adr,
        "constitution_refs": [{"ref": r.ref, "role": r.role} for r in event.constitution_refs],
        "founding_source": event.founding_source,
        "founding_quote": event.founding_quote,
    }


def render_event(event: AdrEvent, *, schema_version: int = 1) -> str:
    metadata = {k: v for k, v in event_to_dict(event).items() if k not in {"kind", "timestamp", "decision", "why", "evolution", "reason", "impact"} and v not in (None, [], "")}
    if schema_version == 1:
        metadata.pop("impact_provenance", None)
        metadata.pop("impact_evidence", None)
    lines = [f"### {event.kind} - {event.timestamp}", "", "```json", json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True), "```"]
    sections = (("Decision", event.decision), ("Reason", _canonical_reason(event)), ("Impact", _canonical_impact(event))) if schema_version == 2 else (("Decision", event.decision), ("Why", event.why), ("Evolution", event.evolution), ("Reason", event.reason))
    for heading, text in sections:
        if text:
            lines.extend(["", f"#### {heading}", "", text])
    return "\n".join(lines)


# A plain YAML scalar cannot contain ": " (it reads as a nested mapping), end in a colon, carry
# " #" (a comment), or open with an indicator character. Our own reader is a regex (`_scalar`) and
# never noticed - but the Trace UI parses frontmatter with a real YAML parser, and five ADR titles
# broke it. Quote only when needed, so every record written before this stays byte-identical.
_YAML_INDICATORS = "-?:,[]{}#&*!|>'\"%@`"


def _yaml_risk(value: str) -> str | None:
    """Why `value` cannot be written as a bare YAML scalar, or None if it can."""
    if not value:
        return "is empty"
    if ": " in value:
        return "contains ': ', which YAML reads as a nested mapping"
    if " #" in value:
        return "contains ' #', which YAML reads as a comment"
    if value.endswith(":"):
        return "ends with ':', which YAML reads as a mapping key"
    if value[0] in _YAML_INDICATORS:
        return f"starts with the YAML indicator {value[0]!r}"
    if value != value.strip():
        return "has leading or trailing whitespace, which YAML strips"
    return None


def _yaml_scalar(value: str) -> str:
    if _yaml_risk(value) is None:
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def frontmatter_issues(text: str) -> list[str]:
    """Lint RAW frontmatter for YAML that strict parsers downstream will reject.

    `parse_adr_text` reads scalars with a regex, so it happily accepts frontmatter no YAML parser
    would - and five ADR titles containing ': ' sat in the corpus unnoticed until the Trace UI,
    which parses properly, failed on them. `adr check` did flag them once the writer began quoting,
    but only as "derived Current view is stale", which names the symptom and not the cause. This
    names the cause.

    Deliberately hand-rolled: `model2vec` is the package's only dependency, so a YAML library is
    not available to validate with.
    """
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return ["frontmatter is not delimited by --- fences"]
    issues: list[str] = []
    seen: set[str] = set()
    for line in text[4:text.find("\n---\n", 4)].splitlines():
        if not line.strip() or line.startswith((" ", "\t", "-")):
            continue  # nested list item or continuation - not a top-level scalar
        if "\t" in line:
            issues.append(f"frontmatter line uses a tab, which YAML forbids: {line.strip()[:60]}")
            continue
        key, _, raw = line.partition(":")
        if not _:
            continue
        key, raw = key.strip(), raw.strip()
        if key in seen:
            issues.append(f"frontmatter key '{key}' appears more than once")
        seen.add(key)
        if not raw or (len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}):
            continue  # empty (a list follows) or already quoted
        risk = _yaml_risk(raw)
        if risk:
            issues.append(f"frontmatter '{key}' must be quoted: it {risk}")
    return issues


def _first_sentence(text: str, cap: int = 110) -> str:
    """One-line gist of a proposal, for listing pending revisions in the Current view."""
    flat = " ".join(text.split())
    match = re.search(r"(?<=[a-z0-9)`])\.\s", flat)
    if match:
        flat = flat[:match.start() + 1]
    return flat if len(flat) <= cap else flat[:cap].rsplit(" ", 1)[0] + "..."


def render_adr(record: AdrRecord) -> str:
    state, proposal = replay_adr(record), current_proposal(record)
    authority = f"`{state.authoritative_decision}`" if state.authoritative_decision else "not yet accepted"
    front = ["---", f"format: memory-seed-adr/{record.schema_version}", f"schema_version: {record.schema_version}", f"adr_id: {record.adr_id}", f"title: {_yaml_scalar(record.title)}"]
    if record.topics:
        front.extend(["topics:", *(f"  - {topic}" for topic in record.topics)])
    front.extend([f"created_at: {record.created_at}", f"user_initials: {record.user_initials}", f"agent_type: {record.agent_type}", f"source: {record.source}", "---", ""])
    view = [
        f"# {record.title}", "", "## Current view", "", "<!-- memory-seed-derived-current-view:start -->",
        f"Status: **{state.current_status.title()}**", "", f"Authoritative decision: {authority}", "",
        "### Decision", "", proposal.decision if proposal else "Not recorded.", "",
        ("### Reason" if record.schema_version == 2 else "### Why"), "", _canonical_reason(proposal) if proposal else "Not recorded.", "",
        ("### Impact" if record.schema_version == 2 else "### How it evolved"), "", _canonical_impact(proposal) if proposal else "No impact has been recorded.", "",
    ]
    if proposal and proposal.constitution_refs:
        # Rendered only when bindings exist, so every ADR written before the field stays
        # byte-canonical. The head proposal's bindings ARE the ADR's current bindings.
        view.extend([
            "### Constitution", "",
            *(f"- `{item.ref}` ({item.role})" for item in proposal.constitution_refs), "",
        ])
    # Revisions proposed but not yet accepted, other than the one shown above. Without this a
    # reader of the summary sees only the accepted head: two branches can each append a proposal,
    # reconcile cleanly, and the Current view still reports the old position with no sign that
    # changes are waiting. Replay already knows the pending set; this surfaces it where the summary
    # is actually read. Omit-empty, so an ADR whose only pending revision is the one on display -
    # every ADR in the corpus today - renders byte-identically.
    shown = proposal.revision_key if proposal else None
    awaiting = [ref for ref in state.pending_decisions if ref != shown]
    if awaiting:
        view.extend(["### Awaiting review", ""])
        for ref in awaiting:
            pending = proposal_for(record, ref)
            summary = _first_sentence(pending.decision) if pending else ""
            view.append(f"- `{ref}`" + (f" - {summary}" if summary else ""))
        view.append("")
    view.extend(["<!-- memory-seed-derived-current-view:end -->", "", "## Event ledger", "", ""])
    events = "\n\n".join(render_event(event, schema_version=record.schema_version) for event in record.events)
    return "\n".join(front + view) + events + "\n"


def parse_adr_text(text: str, *, path: Path | None = None) -> AdrRecord:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("ADR sidecar has no closed YAML frontmatter")
    end = text.find("\n---\n", 4)
    front = text[4:end]
    required = {key: _scalar(front, key) for key in ("format", "schema_version", "adr_id", "title", "created_at", "user_initials", "agent_type", "source")}
    missing = [key for key, value in required.items() if value is None]
    if missing:
        raise ValueError("ADR sidecar is missing frontmatter field(s): " + ", ".join(missing))
    schema_version = int(required["schema_version"] or "0")
    if required["format"] != f"memory-seed-adr/{schema_version}":
        raise ValueError("ADR format must match schema_version")
    events: list[AdrEvent] = []
    for match in EVENT_RE.finditer(text[end + 5:].lstrip("\n")):
        body = match.group("body")
        json_match = JSON_RE.search(body)
        if not json_match:
            raise ValueError(f"{match.group('kind')} event has no JSON metadata")
        meta = json.loads(json_match.group("json"))
        predecessors = tuple(AdrPredecessor(str(item.get("decision", "")), str(item.get("relation_assertion", ""))) for item in meta.get("predecessors", []) if isinstance(item, Mapping))
        bindings = tuple(ConstitutionRef(str(item.get("ref", "")), str(item.get("role", ""))) for item in meta.get("constitution_refs", []) if isinstance(item, Mapping))
        is_v2 = schema_version == 2
        events.append(AdrEvent(
            match.group("kind"), str(meta.get("event_id", "")), match.group("timestamp").strip(), str(meta.get("source", "")),
            meta.get("decision_ref"), meta.get("update_entry_id"), meta.get("expected_authoritative_decision"), predecessors,
            tuple(str(x) for x in meta.get("supporting_decisions", [])), tuple(str(x) for x in meta.get("matched_decisions", [])),
            _section(body, "Decision"), _section(body, "Why"), _section(body, "Evolution"), _section(body, "Reason"), meta.get("replacement_adr"),
            bindings, meta.get("founding_source"), str(meta.get("founding_quote", "")),
            _section(body, "Impact") if is_v2 else "", str(meta.get("impact_provenance", "preserved")),
            tuple(str(x) for x in meta.get("impact_evidence", [])), _v2_body_issues(body) if is_v2 else (),
        ))
    return AdrRecord(schema_version, required["adr_id"] or "", required["title"] or "", _list(front, "topics"), required["created_at"] or "", required["user_initials"] or "", required["agent_type"] or "", required["source"] or "", events, path, schema_version)


def unknown_event_kinds(text: str) -> tuple[str, ...]:
    """Event kinds present in `text` that THIS build's parser does not recognise.

    `EVENT_RE` only matches known kinds, so an unrecognised event is skipped silently - the record
    then renders without it and reads as corrupt ("Current view is stale", "competing acceptance")
    rather than as "you are running an older parser". The fuse calls this so a branch that adds an
    event kind gets told to land its parser change first, instead of being accused of a conflict.
    """
    return tuple(sorted({m.group("kind") for m in EVENT_HEADING_RE.finditer(text)} - EVENT_TYPES))


def parse_adr(path: Path) -> AdrRecord:
    return parse_adr_text(read_text_file(path), path=path)


def load_adr_for_write(path: Path, cwd: str | Path = ".") -> tuple[AdrRecord | None, tuple[str, ...]]:
    """Load an existing ADR only when a writer can append without normalizing authored bytes."""
    try:
        source_text = read_text_file(path)
        record = parse_adr_text(source_text, path=path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, (f"existing ADR is not writable: {exc}",)
    issues = validate_adr(record, cwd)
    unknown = unknown_event_kinds(source_text)
    if unknown:
        issues.append("existing ADR has unsupported event kind(s): " + ", ".join(unknown))
    if render_adr(record) != source_text:
        issues.append(
            "existing ADR is not canonical; run adr check and repair it explicitly before lifecycle writes"
        )
    return (None, tuple(issues)) if issues else (record, ())


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
    # The rules themselves live in `_replay_step`; this only says them in the reconciler's voice.
    # `revision_key`, not `decision_ref`: a founding revision carries no decision_ref, and keying on
    # decision_ref silently skipped it - its acceptance then looked like a transition against a
    # non-pending revision and every later acceptance looked like a competing one.
    def phrase(code: str, **kw: Any) -> str | None:
        adr = base.adr_id
        if code == "duplicate":
            return f"ADR {adr} has duplicate revision {kw['ref']}"
        if code == "non_pending":
            return f"ADR {adr} transition targets non-pending revision {kw['ref']}"
        if code == "stale_expected":
            return (f"ADR {adr} has competing acceptance for {kw['ref']}; "
                    f"expected {kw['expected'] or 'no head'}, replay has "
                    f"{cursor.authoritative or 'no head'}")
        if code == "no_descent":
            return f"ADR {adr} acceptance {kw['ref']} does not descend from {kw['authoritative']}"
        # Supersession is validated by `validate_adr` against the single file. A merge only has to
        # agree that the two branches' event sets compose, so the reconciler stays silent here
        # rather than newly refusing merges it has always allowed.
        return None

    cursor = _Replay()
    for event in merged.events:
        issues.extend(_replay_step(cursor, event, merged, phrase))
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


def _constitution_anchors(cwd: str | Path) -> set[str]:
    """Anchor refs declared in docs/CONSTITUTION.md via constitution-ref markers.

    Empty set when the document or its markers are absent - in which case any binding fails
    validation with a message naming the missing anchors, rather than resolving against nothing.
    """
    path = resolve_runtime(cwd).workspace_root / "docs" / "CONSTITUTION.md"
    try:
        text = read_text_file(path)
    except OSError:
        return set()
    return set(CONSTITUTION_ANCHOR_RE.findall(text))


def _binding_issues(event: AdrEvent, label: str, anchors: set[str]) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    for item in event.constitution_refs:
        if item.role not in ALLOWED_BINDING_ROLES:
            issues.append(f"{label} constitution ref role must be governing or supporting")
        if not CONSTITUTION_REF_RE.fullmatch(item.ref):
            issues.append(f"{label} constitution ref '{item.ref}' must match constitution:vN#slug")
        elif item.ref not in anchors:
            issues.append(
                f"{label} constitution ref '{item.ref}' does not resolve to an anchor in docs/CONSTITUTION.md"
            )
        if item.ref in seen:
            issues.append(f"{label} duplicates constitution ref '{item.ref}'")
        seen.add(item.ref)
    return issues


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
    anchors = _constitution_anchors(cwd)
    pending, pending_entry_ids = set(pending_decisions), set(pending_entries)
    issues: list[str] = []
    if record.schema_version not in ADR_SCHEMA_VERSIONS:
        issues.append("unsupported ADR schema_version; expected 1 or 2")
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
    # State transitions come from `_replay_step` - the single copy - and are only WORDED here.
    # `statuses` and `authoritative` below are read-only views onto that cursor, used by the
    # structural checks that need to know what the replay has seen so far.
    cursor = _Replay()
    label = ""

    def phrase(code: str, **kw: Any) -> str | None:
        if code == "duplicate":
            return f"{label} duplicates revision {kw['ref']}"
        if code == "non_pending":
            return f"{label} targets revision in state {kw['state'] or 'missing'}"
        if code in {"stale_expected", "stale_expected_supersede"}:
            return f"{label} has stale expected_authoritative_decision"
        if code == "no_descent":
            return f"{label} does not descend from authoritative decision {kw['authoritative']}"
        if code == "bad_supersession":
            return f"{label} is invalid ADR supersession"
        return None

    statuses = cursor.statuses
    last_timestamp: datetime | None = None
    for index, event in enumerate(record.events, 1):
        label = f"event {index} ({event.kind})"
        if record.schema_version == 2 and event.body_issues is not None:
            issues.extend(f"{label} {issue}" for issue in event.body_issues)
            if not all((event.decision.strip(), _canonical_reason(event).strip(), _canonical_impact(event).strip())):
                issues.append(f"{label} requires non-empty Decision, Reason, and Impact")
            if event.impact_provenance not in IMPACT_PROVENANCE:
                issues.append(f"{label} impact_provenance must be preserved, reconstructed, or not-recorded")
            if event.impact_provenance == "reconstructed" and not event.impact_evidence:
                issues.append(f"{label} reconstructed Impact requires direct evidence references")
            if event.impact_provenance != "reconstructed" and event.impact_evidence:
                issues.append(f"{label} impact_evidence is allowed only for reconstructed Impact")
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
        founding = event.founding_source is not None
        if not event.update_entry_id:
            # Founding events may predate any session corpus (bootstrap on a fresh project),
            # so the update-entry requirement applies only to decision-sourced events.
            if not founding:
                issues.append(f"{label} requires update_entry_id")
        elif event.update_entry_id not in known | pending_entry_ids:
            issues.append(f"{label} references missing update entry {event.update_entry_id}")
        issues.extend(_binding_issues(event, label, anchors))
        if event.kind == "revision-proposed":
            ref = event.revision_key or ""
            if founding:
                if event.decision_ref:
                    issues.append(f"{label} may carry a decision_ref or a founding_source, not both")
                if not FOUNDING_SOURCE_RE.fullmatch(event.founding_source or ""):
                    issues.append(f"{label} founding_source must be 'bootstrap' or '<control-file>#L<n>'")
                if not event.founding_quote.strip():
                    issues.append(f"{label} founding events require a verbatim founding_quote")
                if event.predecessors:
                    issues.append(f"{label} founding events cannot assert predecessors (no decision to anchor the link grammar)")
            else:
                issues.extend(_ref_issues(ref, known, ordinals, f"{label} decision", pending))
            issues.extend(_replay_step(cursor, event, record, phrase))
            if record.schema_version == 1 and (not event.decision.strip() or not event.why.strip()):
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
            ref = event.revision_key or ""
            if not ref.startswith("founding:"):
                issues.extend(_ref_issues(ref, known, ordinals, f"{label} decision", pending))
            issues.extend(_replay_step(cursor, event, record, phrase))
        elif event.kind == "context-added":
            # Soft attachment: evidence only. No decision_ref, no predecessors, no status effect -
            # every ref must still resolve, so context cannot smuggle in an unverifiable claim.
            if not event.supporting_decisions:
                issues.append(f"{label} requires at least one supporting decision")
            if not event.reason.strip():
                issues.append(f"{label} requires a Reason naming why the context is relevant")
            if event.decision_ref or event.predecessors:
                issues.append(f"{label} cannot carry a decision_ref or predecessors; it moves nothing")
            for supporting in event.supporting_decisions:
                issues.extend(_ref_issues(supporting, known, ordinals, f"{label} supporting decision", pending))
        elif event.kind == "reviewed-no-change":
            if not event.decision_ref or not event.matched_decisions or not event.reason.strip():
                issues.append(f"{label} requires decision_ref, matched_decisions, and Reason")
            for matched in event.matched_decisions:
                if matched not in adr_membership(record):
                    issues.append(f"{label} matched decision {matched} is not in ADR lineage")
        elif event.kind == "adr-superseded":
            issues.extend(_replay_step(cursor, event, record, phrase))
    if record.events[0].kind != "revision-proposed":
        issues.append("the first ADR event must be revision-proposed")
    return issues


def iter_adrs(cwd: str | Path = ".") -> Iterable[AdrRecord]:
    directory = resolve_runtime(cwd).memory_dir / "decisions"
    if not directory.is_dir():
        return ()
    return tuple(parse_adr(path) for path in sorted(directory.glob("adr_*.md")))


def record_digest(record: AdrRecord) -> str:
    # Schema-v1 receipts were published before canonical fields/provenance existed. Keep their
    # byte-level digest payload stable so merely learning to read v2 does not stale old receipts.
    def legacy_event(item: AdrEvent) -> dict[str, Any]:
        return {
            "kind": item.kind, "event_id": item.event_id, "timestamp": item.timestamp,
            "source": item.source, "decision_ref": item.decision_ref,
            "update_entry_id": item.update_entry_id,
            "expected_authoritative_decision": item.expected_authoritative_decision,
            "predecessors": [{"decision": p.decision, "relation_assertion": p.relation_assertion} for p in item.predecessors],
            "supporting_decisions": list(item.supporting_decisions),
            "matched_decisions": list(item.matched_decisions), "decision": item.decision,
            "why": item.why, "evolution": item.evolution, "reason": item.reason,
            "replacement_adr": item.replacement_adr,
            "constitution_refs": [{"ref": r.ref, "role": r.role} for r in item.constitution_refs],
            "founding_source": item.founding_source, "founding_quote": item.founding_quote,
        }
    events = [event_to_dict(item) for item in record.events] if record.schema_version == 2 else [legacy_event(item) for item in record.events]
    payload = {"adr_id": record.adr_id, "title": record.title, "topics": record.topics, "events": events}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def adr_to_dict(record: AdrRecord, *, include_events: bool = True) -> dict[str, Any]:
    state, proposal = replay_adr(record), current_proposal(record)
    reason = _canonical_reason(proposal) if proposal else ""
    impact = _canonical_impact(proposal) if proposal else ""
    result: dict[str, Any] = {
        "adr_id": record.adr_id, "title": record.title, "topics": list(record.topics),
        "created_at": record.created_at, "source": record.source,
        "current_status": state.current_status, "authoritative_decision": state.authoritative_decision,
        "pending_decisions": list(state.pending_decisions), "rejected_decisions": list(state.rejected_decisions),
        "superseded_by": state.superseded_by, "membership": sorted(adr_membership(record)),
        "current": {
            "decision_ref": proposal.decision_ref if proposal else None,
            "decision": proposal.decision if proposal else "",
            "reason": reason, "impact": impact,
            # Deprecated aliases retained through the v1 compatibility window.
            "why": reason, "evolution": impact,
        },
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
                    # A link item is a bare ref string OR the {ref, why, type}
                    # object the evidence mandate introduced (2026-08-09). This
                    # gate is mandatory, so a shape it does not understand must
                    # never read as "no lifecycle target" - that would silently
                    # disable the review rather than fail loudly.
                    if isinstance(value, Mapping):
                        value = value.get("ref")
                    if isinstance(value, str) and value.strip():
                        result.extend(canonical_decision_refs(cwd, value.strip()))
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
        membership = sorted(adr_membership(record))
        # `_excerpts` is a misnomer worth keeping in mind: it truncates nothing, it returns each
        # decision's whole body. What it CAN do is fail to find one - it walks session documents
        # and skips any it cannot read - and the old `excerpts.get(ref, "")` turned that miss into
        # an empty string. The reviewing agent then saw evidence-shaped emptiness and could not
        # tell "this decision has no body" from "this decision was never located", while still
        # being required to return accept/revise/no-change for the ADR. Naming the miss is the
        # whole fix: a gate may rule on absent evidence, but not without being told it is absent.
        item["source_excerpts"] = {
            ref: excerpts[ref] for ref in membership if ref in excerpts
        }
        item["unresolved_decisions"] = [ref for ref in membership if ref not in excerpts]
        contexts.append(item)
    return contexts


def review_receipt(cwd: str | Path, *, proposal: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]) -> str:
    payload = {"workspace": str(resolve_runtime(cwd).workspace_root.resolve()), "proposal": proposal, "adrs": sorted((str(item.get("adr_id")), str(item.get("digest"))) for item in contexts)}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return "adrr_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_review_proposal(
    *,
    title: Any,
    body: str,
    timestamp: str,
    user_initials: Any,
    agent_type: Any,
    decisions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the content-bound proposal used by every append review surface."""
    receipt_decisions = [
        {key: value for key, value in item.items() if key != "adrs"}
        if isinstance(item, Mapping)
        else item
        for item in decisions
    ]
    return {
        "title": title,
        "body": body,
        "timestamp": timestamp,
        "user_initials": user_initials,
        "agent_type": agent_type,
        "decisions": receipt_decisions,
    }


def preflight_append_adr_review(
    cwd: str | Path,
    *,
    proposal: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
    supplied_receipt: str | None = None,
) -> AdrAppendReviewPreflight:
    """Run the mandatory lifecycle-linked ADR review gate once for all surfaces."""
    targets = lifecycle_targets(cwd, decisions)
    contexts = tuple(adr_review_context(cwd, targets))
    expected_receipt = review_receipt(cwd, proposal=proposal, contexts=contexts)
    outcomes: dict[str, tuple[str, dict[str, Any]]] = {}
    duplicate_outcomes: set[str] = set()
    malformed_outcomes: list[str] = []
    for decision_item in decisions:
        if not isinstance(decision_item, Mapping):
            continue
        ordinal = str(decision_item.get("decision", ""))
        actions = decision_item.get("adrs", [])
        for action in actions if isinstance(actions, list) else []:
            if not isinstance(action, dict) or not isinstance(action.get("adr_id"), str):
                continue
            adr_id = action["adr_id"]
            if adr_id in outcomes:
                duplicate_outcomes.add(adr_id)
            outcomes[adr_id] = (ordinal, action)
            outcome = action.get("outcome")
            if outcome not in {"revise", "no-change"}:
                malformed_outcomes.append(
                    f"ADR {adr_id} outcome must be revise or no-change"
                )
            elif outcome == "revise" and not all(
                isinstance(action.get(field), str) and action[field].strip()
                for field in ("decision",)
            ):
                malformed_outcomes.append(
                    f"ADR {adr_id} revise outcome requires non-empty decision, reason, and impact"
                )
            elif outcome == "revise" and not all(
                isinstance(action.get(field, action.get(legacy, "")), str)
                and str(action.get(field, action.get(legacy, ""))).strip()
                for field, legacy in (("reason", "why"), ("impact", "evolution"))
            ):
                malformed_outcomes.append(
                    f"ADR {adr_id} revise outcome requires non-empty decision, reason, and impact"
                )
            if outcome == "no-change" and not (
                isinstance(action.get("reason"), str) and action["reason"].strip()
            ):
                malformed_outcomes.append(
                    f"ADR {adr_id} no-change outcome requires a non-empty reason"
                )

    matched_ids = {str(item["adr_id"]) for item in contexts}
    supplied_ids = set(outcomes)
    receipt_ok = supplied_receipt == expected_receipt
    outcomes_ok = supplied_ids == matched_ids and not duplicate_outcomes and not malformed_outcomes
    review_attempted = bool(contexts or supplied_ids or supplied_receipt)
    if not review_attempted or (contexts and receipt_ok and outcomes_ok):
        return AdrAppendReviewPreflight(
            True, False, expected_receipt, targets, contexts, outcomes, ()
        )

    issues = ["ADR review is required before this lifecycle-linked session entry can be written"]
    if supplied_receipt and not receipt_ok:
        issues.append(
            "adr_review_receipt is stale or does not match the proposed entry and current ADR ledgers"
        )
    if supplied_ids != matched_ids:
        missing = sorted(matched_ids - supplied_ids)
        extra = sorted(supplied_ids - matched_ids)
        if missing:
            issues.append("missing ADR review outcome(s): " + ", ".join(missing))
        if extra:
            issues.append("unexpected ADR review outcome(s): " + ", ".join(extra))
    if duplicate_outcomes:
        issues.append("duplicated ADR review outcome(s): " + ", ".join(sorted(duplicate_outcomes)))
    issues.extend(malformed_outcomes)
    return AdrAppendReviewPreflight(
        False, True, expected_receipt, targets, contexts, outcomes, tuple(issues)
    )


def _save(record: AdrRecord, cwd: str | Path, dry_run: bool, *, pending_decisions: Sequence[str] = (), pending_entries: Sequence[str] = ()) -> AdrOperationResult:
    path = record.path or resolve_runtime(cwd).memory_dir / "decisions" / f"{record.adr_id}.md"
    record.path = path
    rendered = render_adr(record)
    # Validate the exact bytes to be written.  This catches v2 body grammar even when the
    # writer constructed an in-memory event directly rather than parsing it first.
    validated = parse_adr_text(rendered, path=path) if record.schema_version == 2 else record
    issues = validate_adr(validated, cwd, pending_decisions=pending_decisions, pending_entries=pending_entries)
    if issues:
        return AdrOperationResult(False, path, record.adr_id, record.current_status, record.authoritative_decision, tuple(issues), False, rendered)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_file(path, rendered)
    return AdrOperationResult(True, path, record.adr_id, record.current_status, record.authoritative_decision, (), not dry_run, rendered if dry_run else None)


def promote_decision(cwd: str | Path = ".", *, adr_id: str, source_entry_id: str | None = None, source_decision: str | None = None, title: str, topics: Sequence[str], user_initials: str, agent_type: str, source: str, decision: str = "See the authoritative session decision.", why: str | None = None, evolution: str | None = None, reason: str | None = None, impact: str | None = None, update_entry_id: str | None = None, direct_predecessors: Sequence[AdrPredecessor] = (), supporting_decisions: Sequence[str] = (), constitution_refs: Sequence[ConstitutionRef] = (), founding_source: str | None = None, founding_quote: str = "", timestamp: str | None = None, dry_run: bool = False) -> AdrOperationResult:
    """Create a new ADR from a session decision OR from a founding source.

    Decision-sourced (the original path): `source_entry_id` + `source_decision` name the
    authoritative session decision. Founding-sourced (2026-08-06): `founding_source` names a
    control-file line (".memory-seed/index.md#L134") or "bootstrap", with a verbatim
    `founding_quote` as the grounding evidence - for concerns whose decision predates the session
    corpus, or for bootstrap on a fresh project that has no corpus at all. Exactly one of the two
    shapes must be supplied; later `revise` events attach real decisions as work touches the
    concern.
    """
    path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
    if path.exists():
        return AdrOperationResult(False, path, adr_id, issues=("ADR already exists",))
    stamp = timestamp or _now()
    reason = reason or why or "See the authoritative session decision rationale."
    impact = impact or evolution or "The decision is expected to govern this architectural concern; contrary evidence requires a successor revision."
    if founding_source is not None:
        if source_entry_id or source_decision:
            return AdrOperationResult(False, path, adr_id, issues=("supply a session decision or a founding source, not both",))
        event = AdrEvent("revision-proposed", _event_id(adr_id, "proposed", founding_source, stamp), stamp, source, None, update_entry_id, predecessors=(), supporting_decisions=tuple(supporting_decisions), decision=decision, reason=reason, constitution_refs=tuple(constitution_refs), founding_source=founding_source, founding_quote=founding_quote, impact=impact)
    else:
        if not source_entry_id or not source_decision:
            return AdrOperationResult(False, path, adr_id, issues=("promotion requires source_entry_id and source_decision (or a founding_source)",))
        ref = f"{source_entry_id}:{source_decision}"
        event = AdrEvent("revision-proposed", _event_id(adr_id, "proposed", ref, stamp), stamp, source, ref, update_entry_id or source_entry_id, predecessors=tuple(direct_predecessors), supporting_decisions=tuple(supporting_decisions), decision=decision, reason=reason, constitution_refs=tuple(constitution_refs), impact=impact)
    return _save(AdrRecord(2, adr_id, title, tuple(dict.fromkeys(topics)), stamp, user_initials, agent_type, source, [event], path, 2), cwd, dry_run)


def revise_adr(cwd: str | Path = ".", *, adr_id: str, decision_ref: str, decision: str, why: str | None = None, evolution: str | None = None, reason: str | None = None, impact: str | None = None, update_entry_id: str, source: str, predecessors: Sequence[AdrPredecessor], supporting_decisions: Sequence[str] = (), constitution_refs: Sequence[ConstitutionRef] = (), timestamp: str | None = None, dry_run: bool = False) -> AdrOperationResult:
    path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
    if not path.exists():
        return AdrOperationResult(False, path, adr_id, issues=("ADR does not exist",))
    record, existing_issues = load_adr_for_write(path, cwd)
    if record is None:
        return AdrOperationResult(False, path, adr_id, issues=existing_issues)
    stamp = timestamp or _now()
    reason, impact = reason or why or "", impact or evolution or ""
    if record.schema_version == 2:
        record.events.append(AdrEvent("revision-proposed", _event_id(adr_id, "proposed", decision_ref, stamp), stamp, source, decision_ref, update_entry_id, predecessors=tuple(predecessors), supporting_decisions=tuple(supporting_decisions), decision=decision, reason=reason, constitution_refs=tuple(constitution_refs), impact=impact))
    else:
        record.events.append(AdrEvent("revision-proposed", _event_id(adr_id, "proposed", decision_ref, stamp), stamp, source, decision_ref, update_entry_id, predecessors=tuple(predecessors), supporting_decisions=tuple(supporting_decisions), decision=decision, why=reason, evolution=impact, constitution_refs=tuple(constitution_refs)))
    return _save(record, cwd, dry_run)


def transition_adr(cwd: str | Path = ".", *, adr_id: str, status: str, decision_ref: str | None = None, update_entry_id: str, expected_authoritative_decision: str | None = None, expected_previous_status: str | None = None, source: str, replacement_adr: str | None = None, reason: str = "", timestamp: str | None = None, dry_run: bool = False) -> AdrOperationResult:
    path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
    if not path.exists():
        return AdrOperationResult(False, path, adr_id, issues=("ADR does not exist",))
    record, existing_issues = load_adr_for_write(path, cwd)
    if record is None:
        return AdrOperationResult(False, path, adr_id, issues=existing_issues)
    stamp = timestamp or _now()
    if expected_previous_status and record.current_status != expected_previous_status:
        return AdrOperationResult(False, path, adr_id, record.current_status, record.authoritative_decision, (f"expected previous status {expected_previous_status}, current status is {record.current_status}",))
    if decision_ref is None and status in {"accepted", "rejected"}:
        pending = replay_adr(record).pending_decisions
        decision_ref = pending[-1] if len(pending) == 1 else None
    kind = {"accepted": "revision-accepted", "rejected": "revision-rejected", "superseded": "adr-superseded"}.get(status)
    if not kind:
        return AdrOperationResult(False, path, adr_id, issues=("unsupported ADR status",))
    reason = reason or f"Record the {status} transition for this ADR revision."
    if expected_authoritative_decision is None and expected_previous_status == "proposed":
        expected_authoritative_decision = record.authoritative_decision
    # A founding revision is tracked under its pseudo-ref. Store it back on the event's founding
    # side, never in decision_ref - decision_ref carries only <entry_id>:dN grammar.
    founding_source: str | None = None
    if decision_ref and decision_ref.startswith("founding:"):
        founding_source, decision_ref = decision_ref[len("founding:"):], None
    ref = decision_ref or (f"founding:{founding_source}" if founding_source else "the selected revision")
    if record.schema_version == 2:
        decision = (
            f"Accept {ref}." if status == "accepted" else
            f"Reject {ref}." if status == "rejected" else
            f"Supersede this ADR with {replacement_adr or 'the replacement ADR'}."
        )
        impact = (
            f"{ref} becomes the authoritative decision; later contrary evidence must create a successor revision."
            if status == "accepted" else
            f"{ref} is not adopted and the current authoritative decision remains unchanged."
            if status == "rejected" else
            f"Authority for this concern moves to {replacement_adr or 'the replacement ADR'} while this ledger remains historical evidence."
        )
        record.events.append(AdrEvent(kind, _event_id(adr_id, kind, decision_ref or founding_source, update_entry_id, stamp), stamp, source, decision_ref, update_entry_id, expected_authoritative_decision, decision=decision, reason=reason, replacement_adr=replacement_adr, founding_source=founding_source, impact=impact))
    else:
        record.events.append(AdrEvent(kind, _event_id(adr_id, kind, decision_ref or founding_source, update_entry_id, stamp), stamp, source, decision_ref, update_entry_id, expected_authoritative_decision, reason=reason, replacement_adr=replacement_adr, founding_source=founding_source))
    return _save(record, cwd, dry_run)


def add_context(cwd: str | Path = ".", *, adr_id: str, supporting_decisions: Sequence[str], reason: str, update_entry_id: str, source: str, timestamp: str | None = None, dry_run: bool = False) -> AdrOperationResult:
    """Attach decisions to a concern as SOFT context - no head move, no status change.

    The counterpart to `revise_adr`. Use when a decision informs a concern without being the
    decision the concern now rests on: an instance of a policy being followed, a related thread, or
    any evidence for an ADR whose status must stay put (a `rejected` ADR accepting a head would
    read as the revision being accepted). Supporting refs stay outside `adr_membership`, so they
    never trigger the MCP review gate.
    """
    path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
    if not path.exists():
        return AdrOperationResult(False, path, adr_id, issues=("ADR does not exist",))
    record, existing_issues = load_adr_for_write(path, cwd)
    if record is None:
        return AdrOperationResult(False, path, adr_id, issues=existing_issues)
    stamp = timestamp or _now()
    if record.schema_version == 2:
        refs = ", ".join(supporting_decisions)
        record.events.append(AdrEvent(
            "context-added", _event_id(adr_id, "context", tuple(supporting_decisions), stamp), stamp,
            source, None, update_entry_id, supporting_decisions=tuple(supporting_decisions),
            decision=f"Record {refs} as context for this ADR.", reason=reason,
            impact="This adds supporting context only; it does not change ADR membership, status, or authority.",
        ))
    else:
        record.events.append(AdrEvent(
            "context-added", _event_id(adr_id, "context", tuple(supporting_decisions), stamp), stamp,
            source, None, update_entry_id, supporting_decisions=tuple(supporting_decisions), reason=reason,
        ))
    return _save(record, cwd, dry_run)


def append_outcome_event(record: AdrRecord, *, outcome: Mapping[str, Any], decision_ref: str, matched_decisions: Sequence[str], update_entry_id: str, timestamp: str, source: str = "write-time") -> None:
    kind = str(outcome.get("outcome", ""))
    event: AdrEvent | None = None
    if kind == "revise":
        assertions = outcome.get("assertions", {}) if isinstance(outcome.get("assertions"), Mapping) else {}
        predecessors = tuple(AdrPredecessor(item, str(assertions.get(item, ""))) for item in matched_decisions)
        reason = str(outcome.get("reason", outcome.get("why", "")))
        impact = str(outcome.get("impact", outcome.get("evolution", "")))
        if record.schema_version == 2:
            event = AdrEvent("revision-proposed", _event_id(record.adr_id, "proposed", decision_ref, timestamp), timestamp, source, decision_ref, update_entry_id, predecessors=predecessors, decision=str(outcome.get("decision", "")), reason=reason, impact=impact)
        else:
            event = AdrEvent("revision-proposed", _event_id(record.adr_id, "proposed", decision_ref, timestamp), timestamp, source, decision_ref, update_entry_id, predecessors=predecessors, decision=str(outcome.get("decision", "")), why=reason, evolution=impact)
    elif kind == "no-change":
        reason = str(outcome.get("reason", ""))
        if record.schema_version == 2:
            event = AdrEvent("reviewed-no-change", _event_id(record.adr_id, "no-change", decision_ref, timestamp), timestamp, source, decision_ref, update_entry_id, matched_decisions=tuple(matched_decisions), decision=f"Retain {decision_ref} as the governing decision.", reason=reason, impact="The reviewed evidence supports retaining the current decision; no successor revision is required.")
        else:
            event = AdrEvent("reviewed-no-change", _event_id(record.adr_id, "no-change", decision_ref, timestamp), timestamp, source, decision_ref, update_entry_id, matched_decisions=tuple(matched_decisions), reason=reason)
    if event is not None and all(existing.event_id != event.event_id for existing in record.events):
        record.events.append(event)


def record_reviewed_no_change(
    cwd: str | Path = ".",
    *,
    adr_id: str,
    entry_id: str,
    reason: str,
    timestamp: str | None = None,
    dry_run: bool = False,
) -> AdrOperationResult:
    """Record that an ADR head was reviewed and remains current.

    The named existing entry is the evidence/provenance anchor. The reviewed
    decision is the ADR's current head, so this event records no new lineage
    membership and cannot move authority or status.
    """
    path = resolve_runtime(cwd).memory_dir / "decisions" / f"{adr_id}.md"
    if not path.exists():
        return AdrOperationResult(False, path, adr_id, issues=("ADR does not exist",))
    if not reason.strip():
        return AdrOperationResult(
            False, path, adr_id, issues=("reviewed-no-change requires a non-empty reason",)
        )
    known_entries, _ = _entry_decisions(cwd)
    if entry_id not in known_entries:
        return AdrOperationResult(
            False, path, adr_id, issues=(f"review evidence references missing entry {entry_id}",)
        )
    record, existing_issues = load_adr_for_write(path, cwd)
    if record is None:
        return AdrOperationResult(False, path, adr_id, issues=existing_issues)
    reviewed_decision = record.authoritative_decision or record.current_decision
    if not reviewed_decision or reviewed_decision not in adr_membership(record):
        return AdrOperationResult(
            False, path, adr_id, issues=("ADR has no reviewable current decision",)
        )
    stamp = timestamp or _now()
    append_outcome_event(
        record,
        outcome={"outcome": "no-change", "reason": reason.strip()},
        decision_ref=reviewed_decision,
        matched_decisions=(reviewed_decision,),
        update_entry_id=entry_id,
        timestamp=stamp,
    )
    return _save(record, cwd, dry_run)


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
        source_text = read_text_file(path)
        # Lint the RAW frontmatter before the canonical comparison: an unquoted risky scalar also
        # trips that comparison, but only as "Current view is stale", which sends a reader looking
        # at the wrong half of the file.
        issues.extend(f"{path}: {issue}" for issue in frontmatter_issues(source_text))
        if render_adr(record) != source_text:
            issues.append(f"{path}: derived Current view is stale")
    return not issues, issues
