"""Build deterministic, gold-isolated ADR context benchmark fixtures.

The committed source declarations are reviewable inputs. Generated runtimes are
disposable and intentionally contain neither ``tasks/gold.json`` nor any answer
key. Scored execution is separately gated on owner approval by the runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts import TASK_COUNT, TASK_SCHEMA, canonical_json, fingerprint, load_json
from memory_seed.adr import AdrEvent, AdrPredecessor, AdrRecord, adr_membership, parse_adr, render_adr
from memory_seed.core import entry_body_decisions


SOURCE_DIR = EXPERIMENT_ROOT / "fixture_source"
TASK_DIR = EXPERIMENT_ROOT / "tasks"
DEFAULT_OUTPUT = EXPERIMENT_ROOT / "generated" / "fixtures"
MANIFEST_PATH = TASK_DIR / "manifest.json"
GOLD_PATH = TASK_DIR / "gold.json"
PREREGISTRATION_PATH = EXPERIMENT_ROOT / "PREREGISTRATION.md"
CONSTITUTION_BINDINGS_PATH = SOURCE_DIR / "adr_constitution_bindings.v1.json"
REVISION_CONSTITUTION_BINDINGS_PATH = SOURCE_DIR / "revision_constitution_bindings.v1.json"

TASK_KEYS = {"schema", "task_id", "fixture", "question", "task_type", "resolver_hints"}
HINT_KEYS = {"adr_ids", "decision_refs", "topics", "paths"}
TASK_TYPES = {"accepted-head", "explain-evolution", "change-impact", "insufficient-evidence"}
GOLD_REQUIRED = {
    "task_id",
    "required_adr_ids",
    "authoritative_refs",
    "required_lineage_edges",
    "relevant_refs",
    "distractor_refs",
    "expected_statuses",
    "insufficient_evidence",
    "allowed_citations",
}
ENTRY_RE = re.compile(
    r"^(?P<heading>## \d{4}-\d{2}-\d{2} \d{2}:\d{2} - [^\n]+)\n"
    r"(?P<body>.*?)(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} - |\Z)",
    re.MULTILINE | re.DOTALL,
)
ENTRY_ID_RE = re.compile(r"^entry_id:\s*(\S+)\s*$", re.MULTILINE)
SCALAR_RE = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<value>[^\n]+)\s*$", re.MULTILINE)
CONSTITUTION_REF_RE = re.compile(r"^constitution:v1#[a-z0-9-]+$")
CONSTITUTION_ROLES = {"governing", "supporting"}


@dataclass(frozen=True)
class BuiltFixture:
    fixture_id: str
    path: Path
    content_fingerprint: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_verified_source(spec: Mapping[str, Any]) -> tuple[Path, str]:
    path = REPO_ROOT / str(spec["path"])
    data = path.read_bytes()
    actual = _sha256(data)
    expected = str(spec["sha256"]).lower()
    if actual != expected:
        raise ValueError(f"frozen source drift for {spec['path']}: expected {expected}, got {actual}")
    return path, data.decode("utf-8")


def _require_unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must not contain duplicates")
    return value


def validate_task_manifest(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    if value.get("schema") != "context-benchmark-manifest.v1":
        raise ValueError("task manifest schema must be context-benchmark-manifest.v1")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != TASK_COUNT or value.get("task_count") != TASK_COUNT:
        raise ValueError(f"task manifest must contain exactly {TASK_COUNT} tasks")
    expected_ids = [f"CTX-{number:02d}" for number in range(1, TASK_COUNT + 1)]
    actual_ids: list[str] = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or set(task) != TASK_KEYS:
            raise ValueError(f"task {index + 1} must use exactly the benchmark task fields")
        if task.get("schema") != TASK_SCHEMA:
            raise ValueError(f"task {index + 1} schema must be {TASK_SCHEMA}")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not re.fullmatch(r"CTX-[0-9]{2}", task_id):
            raise ValueError(f"task {index + 1} has malformed task_id")
        actual_ids.append(task_id)
        if not isinstance(task.get("fixture"), str) or not task["fixture"]:
            raise ValueError(f"{task_id}.fixture must be non-empty")
        if not isinstance(task.get("question"), str) or not task["question"].strip():
            raise ValueError(f"{task_id}.question must be non-empty")
        if task.get("task_type") not in TASK_TYPES:
            raise ValueError(f"{task_id}.task_type is unsupported")
        hints = task.get("resolver_hints")
        if not isinstance(hints, dict) or set(hints) != HINT_KEYS:
            raise ValueError(f"{task_id}.resolver_hints must use exactly the frozen fields")
        for key in sorted(HINT_KEYS):
            _require_unique_strings(hints[key], f"{task_id}.resolver_hints.{key}")
    if actual_ids != expected_ids:
        raise ValueError(f"task IDs must be ordered {expected_ids!r}")
    return tasks


def validate_gold(value: Mapping[str, Any], tasks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if value.get("schema") != "context-gold.v1":
        raise ValueError("gold schema must be context-gold.v1")
    if value.get("approval_status") not in {"DRAFT-PENDING-OWNER-APPROVAL", "APPROVED"}:
        raise ValueError("gold approval_status is invalid")
    rows = value.get("tasks")
    if not isinstance(rows, list) or len(rows) != len(tasks):
        raise ValueError("gold must contain one row per benchmark task")
    expected_ids = [str(task["task_id"]) for task in tasks]
    actual_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not GOLD_REQUIRED.issubset(row):
            raise ValueError("every gold row must contain the frozen gold fields")
        task_id = row.get("task_id")
        if not isinstance(task_id, str):
            raise ValueError("gold task_id must be a string")
        actual_ids.append(task_id)
        for key in (
            "required_adr_ids",
            "authoritative_refs",
            "relevant_refs",
            "distractor_refs",
            "allowed_citations",
        ):
            _require_unique_strings(row.get(key), f"{task_id}.{key}")
        edges = row.get("required_lineage_edges")
        if not isinstance(edges, list):
            raise ValueError(f"{task_id}.required_lineage_edges must be an array")
        seen_edges: set[tuple[str, str, str]] = set()
        for edge in edges:
            if not isinstance(edge, dict) or set(edge) != {"source", "target", "type"}:
                raise ValueError(f"{task_id} has malformed lineage edge")
            if edge["type"] not in {"evolves", "replaces"}:
                raise ValueError(f"{task_id} gold must never classify related as lineage")
            encoded = (edge["source"], edge["target"], edge["type"])
            if encoded in seen_edges:
                raise ValueError(f"{task_id} has duplicate lineage edge {encoded!r}")
            seen_edges.add(encoded)
        if not isinstance(row.get("insufficient_evidence"), bool):
            raise ValueError(f"{task_id}.insufficient_evidence must be boolean")
        statuses = row.get("expected_statuses")
        if not isinstance(statuses, dict) or set(statuses) != set(row["required_adr_ids"]):
            raise ValueError(f"{task_id}.expected_statuses must map every required ADR exactly once")
        if any(status not in {"accepted", "proposed", "rejected", "superseded", "empty"} for status in statuses.values()):
            raise ValueError(f"{task_id}.expected_statuses contains an invalid status")
        related = row.get("required_related_edges", [])
        if not isinstance(related, list):
            raise ValueError(f"{task_id}.required_related_edges must be an array")
        for edge in related:
            if not isinstance(edge, dict) or set(edge) != {"source", "target", "type"} or edge["type"] != "related":
                raise ValueError(f"{task_id} has malformed related edge")
        _require_unique_strings(row.get("required_missing_refs", []), f"{task_id}.required_missing_refs")
    if actual_ids != expected_ids:
        raise ValueError("gold rows must be in the same order as the task manifest")
    return rows


def load_definitions() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(MANIFEST_PATH)
    gold = load_json(GOLD_PATH)
    if not isinstance(manifest, dict) or not isinstance(gold, dict):
        raise ValueError("task and gold roots must be JSON objects")
    tasks = validate_task_manifest(manifest)
    validate_gold(gold, tasks)
    return manifest, gold, tasks


def scored_execution_approved() -> bool:
    """Fail closed unless both candidate gold and preregistration are approved."""
    _manifest, gold, _tasks = load_definitions()
    preregistration = PREREGISTRATION_PATH.read_text(encoding="utf-8")
    status = re.search(r"^Status:\s+\*\*(?P<status>[^*]+)\*\*", preregistration, re.MULTILINE)
    return gold.get("approval_status") == "APPROVED" and bool(
        status and status.group("status").strip().upper() == "APPROVED"
    )


def _entry_block(text: str, entry_id: str) -> str:
    matches = [match.group(0).rstrip() for match in ENTRY_RE.finditer(text) if ENTRY_ID_RE.search(match.group("body")) and ENTRY_ID_RE.search(match.group("body")).group(1) == entry_id]
    if len(matches) != 1:
        raise ValueError(f"expected one source entry {entry_id}, found {len(matches)}")
    return matches[0]


def _entry_scalars(block: str) -> dict[str, str]:
    yaml_match = re.search(r"```yaml\s*\n(?P<yaml>.*?)\n```", block, re.DOTALL)
    if not yaml_match:
        raise ValueError("source entry has no metadata fence")
    return {match.group("key"): match.group("value").strip() for match in SCALAR_RE.finditer(yaml_match.group("yaml"))}


def _entry_title(block: str) -> str:
    heading = block.splitlines()[0]
    return heading.split(" - ", 1)[1]


_EVOLUTION_TYPES = ("(refines)", "(builds-on)")


def _target_entry(ref: str) -> str:
    target = ref.split("->", 1)[-1].strip()
    return target.split(":", 1)[0]


def _render_link(raw: str, decision_counts: Mapping[str, int], source_entry: str) -> str:
    source_ordinal = ""
    target = raw.strip()
    # An evolution type (` (refines)` / ` (builds-on)`) rides at the end of the
    # ref and survives every rewrite below - collapsing a single-decision target
    # to its bare entry id used to take the suffix with it, which authored an
    # untyped edge `links check` now rejects outright.
    suffix = ""
    for evolution_type in _EVOLUTION_TYPES:
        if target.endswith(evolution_type):
            suffix = f" {evolution_type}"
            target = target[: -len(evolution_type)].strip()
            break
    if "->" in target:
        source_ordinal, target = (part.strip() for part in target.split("->", 1))
    target_entry = _target_entry(target)
    if decision_counts.get(target_entry) == 1:
        target = target_entry
    if decision_counts.get(source_entry, 0) <= 1:
        source_ordinal = ""
    return (f"{source_ordinal} -> {target}" if source_ordinal else target) + suffix


def _render_entry(
    *,
    heading: str,
    entry_id: str,
    decisions: Sequence[tuple[str, str, str]],
    agent_type: str,
    evolves: Sequence[str] = (),
    replaces: Sequence[str] = (),
    related_entries: Sequence[str] = (),
) -> str:
    lines = [
        heading,
        "",
        "```yaml",
        f"entry_id: {entry_id}",
        "user_initials: JNL",
        f"agent_type: {agent_type}",
        "project_path: .",
        "subproject_path: null",
        "topics:",
        "  - architecture",
        "  - schema",
        "  - mcp-tools",
        "  - session-fuse",
        "  - feature-build",
    ]
    for key, values in (("evolves", evolves), ("replaces", replaces), ("related_entries", related_entries)):
        if values:
            lines.append(f"{key}:")
            lines.extend(f"  - {value}" for value in values)
    lines.extend(["```", "", "### Decisions", ""])
    for ordinal, name, body in decisions:
        number = ordinal[1:] if ordinal.startswith("d") else ordinal
        lines.extend([f"#### D{number} - {name or 'Recorded decision'}", "", body.strip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def _session_document(date: str, entries: Iterable[str]) -> str:
    front = "---\ntags:\n  - session-log\n  - context-benchmark-fixture\nsession_date: " + date + "\n---\n\n"
    return front + "\n".join(entry.rstrip() for entry in entries) + "\n"


def _topics_yaml() -> str:
    return """schema_version: 2
topics:
  - slug: architecture
    label: Architecture
    description: Architectural decisions in the benchmark fixture.
    status: active
    axis: area
    aliases: []
  - slug: schema
    label: Schema
    description: Data and interface contracts.
    status: active
    axis: area
    aliases: []
  - slug: mcp-tools
    label: MCP Tools
    description: MCP tool behavior.
    status: active
    axis: area
    aliases: []
  - slug: session-fuse
    label: Session Fuse
    description: Branch-local memory integration.
    status: active
    axis: activity
    aliases: []
  - slug: feature-build
    label: Feature Build
    description: Feature implementation work.
    status: active
    axis: activity
    aliases: []
"""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _source_adr_records(
    real: Mapping[str, Any], adversarial: Mapping[str, Any]
) -> dict[str, dict[str, AdrRecord]]:
    """Load the ADR membership declarations without changing frozen v1 sources."""
    records: dict[str, dict[str, AdrRecord]] = {}
    real_records: dict[str, AdrRecord] = {}
    for spec in real["adr_sources"]:
        path, _text = _read_verified_source(spec)
        record = parse_adr(path)
        real_records[record.adr_id] = record
    records[str(real["fixture_id"])] = real_records

    for fixture in adversarial["fixtures"]:
        fixture_id = str(fixture["fixture_id"])
        synthetic: dict[str, AdrRecord] = {}
        for adr in fixture["adrs"]:
            record = AdrRecord(
                schema_version=1,
                adr_id=str(adr["adr_id"]),
                title=str(adr["title"]),
                topics=("architecture",),
                created_at="2026-01-01T00:00:00Z",
                user_initials="JNL",
                agent_type="fixture",
                source="derived",
                events=_synthetic_events(fixture_id, adr),
            )
            synthetic[record.adr_id] = record
        records[fixture_id] = synthetic
    return records


def validate_constitution_bindings(
    value: Mapping[str, Any], records_by_fixture: Mapping[str, Mapping[str, AdrRecord]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate experiment-only ADR-to-Constitution bindings before fixture output.

    The source deliberately remains outside both ADR storage and the frozen task/gold
    contracts.  Every fixture ADR needs one binding, and every bound decision must be
    a member of that ADR's validated lineage rather than a merely related entry.
    """
    if set(value) != {"schema", "sections", "bindings"} or value.get("schema") != "context-adr-constitution-bindings.v1":
        raise ValueError("constitution bindings must use context-adr-constitution-bindings.v1")
    sections = value.get("sections")
    bindings = value.get("bindings")
    if not isinstance(sections, list) or not sections:
        raise ValueError("constitution sections must be a non-empty array")
    if not isinstance(bindings, list):
        raise ValueError("constitution bindings must be an array")

    sections_by_ref: dict[str, dict[str, Any]] = {}
    for index, section in enumerate(sections):
        if not isinstance(section, dict) or set(section) != {"ref", "title", "text", "digest"}:
            raise ValueError(f"constitution section {index} has malformed fields")
        ref = section.get("ref")
        title = section.get("title")
        text = section.get("text")
        digest = section.get("digest")
        if not isinstance(ref, str) or not CONSTITUTION_REF_RE.fullmatch(ref):
            raise ValueError(f"constitution section {index} has malformed ref")
        if ref in sections_by_ref:
            raise ValueError(f"duplicate constitution section {ref}")
        if not isinstance(title, str) or not title.strip() or not isinstance(text, str) or not text.strip():
            raise ValueError(f"constitution section {ref} must have title and text")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"constitution section {ref} has malformed digest")
        if _sha256(text.encode("utf-8")) != digest:
            raise ValueError(f"constitution section {ref} has stale digest")
        sections_by_ref[ref] = section

    expected = {(fixture_id, adr_id) for fixture_id, adrs in records_by_fixture.items() for adr_id in adrs}
    actual: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict) or set(binding) != {"fixture_id", "adr_id", "decision_refs", "constitution_refs"}:
            raise ValueError(f"constitution binding {index} has malformed fields")
        fixture_id = binding.get("fixture_id")
        adr_id = binding.get("adr_id")
        if not isinstance(fixture_id, str) or fixture_id not in records_by_fixture:
            raise ValueError(f"constitution binding {index} references unknown fixture")
        if not isinstance(adr_id, str) or adr_id not in records_by_fixture[fixture_id]:
            raise ValueError(f"constitution binding {index} references unknown ADR {adr_id!r}")
        key = (fixture_id, adr_id)
        if key in actual:
            raise ValueError(f"duplicate constitution binding for {fixture_id}/{adr_id}")
        actual.add(key)

        decision_refs = _require_unique_strings(binding.get("decision_refs"), f"constitution binding {fixture_id}/{adr_id}.decision_refs")
        if not decision_refs:
            raise ValueError(f"constitution binding {fixture_id}/{adr_id} must bind at least one decision")
        known_members = adr_membership(records_by_fixture[fixture_id][adr_id])
        stale = sorted(set(decision_refs) - known_members)
        if stale:
            raise ValueError(f"constitution binding {fixture_id}/{adr_id} has stale ADR decision references: {stale}")

        refs = binding.get("constitution_refs")
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"constitution binding {fixture_id}/{adr_id} must bind at least one section")
        seen_refs: set[str] = set()
        governing = 0
        normalized_refs: list[dict[str, str]] = []
        for item in refs:
            if not isinstance(item, dict) or set(item) != {"ref", "role"}:
                raise ValueError(f"constitution binding {fixture_id}/{adr_id} has malformed section ref")
            ref, role = item.get("ref"), item.get("role")
            if not isinstance(ref, str) or ref not in sections_by_ref:
                raise ValueError(f"constitution binding {fixture_id}/{adr_id} references stale constitution section {ref!r}")
            if ref in seen_refs:
                raise ValueError(f"constitution binding {fixture_id}/{adr_id} has duplicate constitution section {ref}")
            if role not in CONSTITUTION_ROLES:
                raise ValueError(f"constitution binding {fixture_id}/{adr_id} has invalid section role {role!r}")
            seen_refs.add(ref)
            governing += int(role == "governing")
            normalized_refs.append({"ref": ref, "role": role})
        if not governing:
            raise ValueError(f"constitution binding {fixture_id}/{adr_id} must include a governing section")
        normalized.append(
            {
                "fixture_id": fixture_id,
                "adr_id": adr_id,
                "decision_refs": decision_refs,
                "constitution_refs": normalized_refs,
            }
        )

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise ValueError(f"missing constitution bindings for ADRs: {missing}")
    if extra:
        raise ValueError(f"stale constitution bindings for ADRs: {extra}")
    return [sections_by_ref[ref] for ref in sorted(sections_by_ref)], normalized


def validate_revision_constitution_bindings(
    value: Mapping[str, Any], records_by_fixture: Mapping[str, Mapping[str, AdrRecord]],
    adr_bindings: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Validate per-revision evidence independently of score gold.

    This versioned fixture declaration narrows an ADR's available Constitution
    sections for a particular decision revision.  It is intentionally not part
    of the established ADR-to-Constitution v1 contract and has no task/gold
    identifiers, so packet construction never needs score gold to select it.
    """
    if set(value) != {"schema", "bindings"} or value.get("schema") != "context-revision-constitution-bindings.v1":
        raise ValueError("revision Constitution bindings must use context-revision-constitution-bindings.v1")
    bindings = value.get("bindings")
    if not isinstance(bindings, list):
        raise ValueError("revision Constitution bindings must be an array")
    adr_by_key = {(row["fixture_id"], row["adr_id"]): row for row in adr_bindings}
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, binding in enumerate(bindings):
        required = {"fixture_id", "adr_id", "decision_ref", "constitution_refs"}
        if not isinstance(binding, dict) or set(binding) != required:
            raise ValueError(f"revision Constitution binding {index} has malformed fields")
        fixture_id, adr_id, decision_ref = binding.get("fixture_id"), binding.get("adr_id"), binding.get("decision_ref")
        if (not isinstance(fixture_id, str) or fixture_id not in records_by_fixture
                or not isinstance(adr_id, str) or adr_id not in records_by_fixture[fixture_id]
                or not isinstance(decision_ref, str) or not decision_ref):
            raise ValueError(f"revision Constitution binding {index} has an unknown fixture, ADR, or decision")
        key = (fixture_id, adr_id, decision_ref)
        if key in seen:
            raise ValueError(f"duplicate revision Constitution binding for {fixture_id}/{adr_id}/{decision_ref}")
        seen.add(key)
        if decision_ref not in adr_membership(records_by_fixture[fixture_id][adr_id]):
            raise ValueError(f"revision Constitution binding {fixture_id}/{adr_id} names a non-member decision")
        adr_binding = adr_by_key.get((fixture_id, adr_id))
        if adr_binding is None:
            raise ValueError(f"revision Constitution binding {fixture_id}/{adr_id} has no ADR binding")
        available = {(item["ref"], item["role"]) for item in adr_binding["constitution_refs"]}
        refs = binding.get("constitution_refs")
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"revision Constitution binding {fixture_id}/{adr_id}/{decision_ref} must bind sections")
        chosen: list[dict[str, str]] = []
        seen_refs: set[str] = set()
        for item in refs:
            if not isinstance(item, dict) or set(item) != {"ref", "role"}:
                raise ValueError("revision Constitution binding has malformed section refs")
            ref, role = item.get("ref"), item.get("role")
            if not isinstance(ref, str) or ref in seen_refs or (ref, role) not in available:
                raise ValueError("revision Constitution binding references unavailable ADR section evidence")
            seen_refs.add(ref)
            chosen.append({"ref": ref, "role": role})
        normalized.append({"fixture_id": fixture_id, "adr_id": adr_id, "decision_ref": decision_ref, "constitution_refs": chosen})
    return sorted(normalized, key=lambda row: (row["fixture_id"], row["adr_id"], row["decision_ref"]))


def _render_constitution(sections: Sequence[Mapping[str, Any]]) -> str:
    lines = ["# Fixture Constitution", ""]
    for section in sections:
        lines.extend(
            [
                f"## {section['title']}",
                "",
                f"<!-- constitution-ref: {section['ref']} -->",
                "",
                str(section["text"]),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _fixture_binding_document(
    fixture_id: str, sections: Sequence[Mapping[str, Any]], bindings: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    fixture_bindings = [binding for binding in bindings if binding["fixture_id"] == fixture_id]
    needed_refs = {
        item["ref"]
        for binding in fixture_bindings
        for item in binding["constitution_refs"]
    }
    return {
        "schema": "context-fixture-adr-constitution-bindings.v1",
        "fixture_id": fixture_id,
        "sections": [section for section in sections if section["ref"] in needed_refs],
        "bindings": fixture_bindings,
    }


def _fixture_revision_binding_document(
    fixture_id: str, bindings: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema": "context-fixture-revision-constitution-bindings.v1",
        "fixture_id": fixture_id,
        "bindings": [
            {
                "adr_id": binding["adr_id"], "decision_ref": binding["decision_ref"],
                "constitution_refs": binding["constitution_refs"],
            }
            for binding in bindings if binding["fixture_id"] == fixture_id
        ],
    }
def _build_real(root: Path, source: Mapping[str, Any]) -> None:
    adr_records: list[AdrRecord] = []
    for adr_spec in source["adr_sources"]:
        path, text = _read_verified_source(adr_spec)
        target = root / ".memory-seed" / "decisions" / path.name
        _write_text(target, text)
        adr_records.append(parse_adr(target))

    source_blocks: list[tuple[str, str, str]] = []
    for session_spec in source["session_sources"]:
        path, text = _read_verified_source(session_spec)
        for entry_id in session_spec["entry_ids"]:
            source_blocks.append((str(path.relative_to(REPO_ROOT)), entry_id, _entry_block(text, entry_id)))

    decision_counts: dict[str, int] = {}
    parsed: dict[str, tuple[str, dict[str, str], list[tuple[str, str, str]]]] = {}
    for source_path, entry_id, block in source_blocks:
        decisions = [(item.ordinal, item.name, item.text) for item in entry_body_decisions(block)]
        if not decisions:
            raise ValueError(f"real source entry {entry_id} has no decisions")
        decision_counts[entry_id] = len(decisions)
        parsed[entry_id] = (source_path, _entry_scalars(block), decisions)

    lifecycle: dict[str, dict[str, list[str]]] = {}
    for record in adr_records:
        for event in record.events:
            if event.kind != "revision-proposed" or not event.decision_ref:
                continue
            source_entry, source_ordinal = event.decision_ref.split(":", 1)
            for predecessor in event.predecessors:
                relation = predecessor.relation_assertion.split(":", 3)[2]
                lifecycle.setdefault(source_entry, {}).setdefault(relation, []).append(
                    f"{source_ordinal} -> {predecessor.decision}"
                )

    by_date: dict[str, list[str]] = {}
    for entry_id, (source_path, scalars, decisions) in parsed.items():
        date = Path(source_path).stem
        stamp = scalars.get("timestamp")
        source_block = next(block for path, eid, block in source_blocks if path == source_path and eid == entry_id)
        heading = source_block.splitlines()[0]
        links = lifecycle.get(entry_id, {})
        rendered = _render_entry(
            heading=heading,
            entry_id=entry_id,
            decisions=decisions,
            agent_type=scalars.get("agent_type", "fixture-extract"),
            evolves=[_render_link(item, decision_counts, entry_id) for item in links.get("evolves", [])],
            replaces=[_render_link(item, decision_counts, entry_id) for item in links.get("replaces", [])],
        )
        by_date.setdefault(date, []).append(rendered)
    for date, entries in sorted(by_date.items()):
        month = date[:7]
        _write_text(root / ".memory-seed" / "sessions" / month / f"{date}.md", _session_document(date, entries))
    _write_text(root / ".memory-seed" / "topics.yaml", _topics_yaml())


def _synthetic_events(fixture_id: str, adr: Mapping[str, Any]) -> list[AdrEvent]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events: list[AdrEvent] = []
    for index, spec in enumerate(adr["events"]):
        kind = str(spec["kind"])
        decision_ref = str(spec.get("decision_ref", "")) or None
        update_entry = decision_ref.split(":", 1)[0] if decision_ref else "mse_ctxfixture"
        stamp = (start + timedelta(seconds=index)).isoformat().replace("+00:00", "Z")
        event_id = "adre_" + hashlib.sha256(
            canonical_json([fixture_id, adr["adr_id"], index, spec]).encode("utf-8")
        ).hexdigest()[:20]
        predecessors = tuple(
            AdrPredecessor(
                str(item["decision"]),
                f"link:{decision_ref}:{item['type']}:{item['decision']}",
            )
            for item in spec.get("predecessors", [])
        )
        events.append(
            AdrEvent(
                kind=kind,
                event_id=event_id,
                timestamp=stamp,
                source="derived",
                decision_ref=decision_ref,
                update_entry_id=update_entry,
                expected_authoritative_decision=spec.get("expected_head"),
                predecessors=predecessors,
                supporting_decisions=tuple(spec.get("supporting_decisions", [])),
                decision=str(spec.get("decision", "")),
                why=str(spec.get("why", "")),
                evolution=str(spec.get("evolution", "")),
                reason=str(spec.get("reason", "")),
            )
        )
    return events


def _build_adversarial(root: Path, fixture: Mapping[str, Any]) -> None:
    entries = fixture["entries"]
    decision_counts = {str(entry["entry_id"]): len(entry["decisions"]) for entry in entries}
    rendered_entries: list[str] = []
    for index, entry in enumerate(entries):
        decisions = [
            (str(item["ordinal"]), str(item.get("title", "")), f"- D: {item['decision']}\n- R: {item['why']}")
            for item in entry["decisions"]
        ]
        rendered_entries.append(
            _render_entry(
                heading=f"## 2026-01-01 {index:02d}:00 - {entry['title']}",
                entry_id=str(entry["entry_id"]),
                decisions=decisions,
                agent_type="fixture",
                evolves=[_render_link(item, decision_counts, str(entry["entry_id"])) for item in entry.get("evolves", [])],
                replaces=[_render_link(item, decision_counts, str(entry["entry_id"])) for item in entry.get("replaces", [])],
                related_entries=list(entry.get("related_entries", [])),
            )
        )
    _write_text(
        root / ".memory-seed" / "sessions" / "2026-01" / "2026-01-01.md",
        _session_document("2026-01-01", rendered_entries),
    )
    _write_text(root / ".memory-seed" / "topics.yaml", _topics_yaml())
    for adr in fixture["adrs"]:
        record = AdrRecord(
            schema_version=1,
            adr_id=str(adr["adr_id"]),
            title=str(adr["title"]),
            topics=("architecture",),
            created_at="2026-01-01T00:00:00Z",
            user_initials="JNL",
            agent_type="fixture",
            source="derived",
            events=_synthetic_events(str(fixture["fixture_id"]), adr),
        )
        _write_text(root / ".memory-seed" / "decisions" / f"{record.adr_id}.md", render_adr(record))


def tree_fingerprint(root: Path, *, exclude_manifest: bool = False) -> str:
    payload: list[tuple[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if exclude_manifest and relative == "FIXTURE_MANIFEST.json":
            continue
        payload.append((relative, _sha256(path.read_bytes())))
    return fingerprint(payload)


def assert_gold_isolated(root: Path) -> None:
    """Fail if an agent-visible fixture contains the gold file or answer-key names."""
    gold_bytes = GOLD_PATH.read_bytes()
    for path in (item for item in root.rglob("*") if item.is_file()):
        lowered = path.name.lower()
        if "gold" in lowered or "answer-key" in lowered or "answer_key" in lowered:
            raise ValueError(f"gold-like file leaked into fixture: {path}")
        if path.read_bytes() == gold_bytes:
            raise ValueError(f"gold bytes leaked into fixture: {path}")


def _safe_reset_fixture(path: Path, output_root: Path) -> None:
    resolved_path = path.resolve()
    resolved_output = output_root.resolve()
    if resolved_path.parent != resolved_output or not path.name:
        raise ValueError(f"refusing to replace fixture outside output root: {path}")
    if path.exists():
        def remove_readonly(function, target, _error):
            os.chmod(target, stat.S_IWRITE)
            function(target)
        shutil.rmtree(path, onerror=remove_readonly)
    path.mkdir(parents=True)


def build_all(output_root: Path = DEFAULT_OUTPUT) -> list[BuiltFixture]:
    manifest, _gold, tasks = load_definitions()
    real = load_json(SOURCE_DIR / "real-current.json")
    adversarial = load_json(SOURCE_DIR / "adversarial.json")
    constitution_source = load_json(CONSTITUTION_BINDINGS_PATH)
    revision_constitution_source = load_json(REVISION_CONSTITUTION_BINDINGS_PATH)
    if not isinstance(real, dict) or real.get("schema") != "context-fixture-source.v1":
        raise ValueError("real fixture source has the wrong schema")
    if not isinstance(adversarial, dict) or adversarial.get("schema") != "context-adversarial-corpus.v1":
        raise ValueError("adversarial fixture source has the wrong schema")
    if not isinstance(constitution_source, dict):
        raise ValueError("constitution bindings source must be a JSON object")
    source_by_id = {str(item["fixture_id"]): item for item in adversarial["fixtures"]}
    constitution_sections, constitution_bindings = validate_constitution_bindings(
        constitution_source, _source_adr_records(real, adversarial)
    )
    revision_constitution_bindings = validate_revision_constitution_bindings(
        revision_constitution_source, _source_adr_records(real, adversarial), constitution_bindings
    )
    fixture_ids = sorted({str(task["fixture"]) for task in tasks})
    expected_ids = {str(real["fixture_id"]), *source_by_id}
    if set(fixture_ids) != expected_ids:
        raise ValueError(f"task/source fixture mismatch: tasks={fixture_ids}, sources={sorted(expected_ids)}")

    output_root.mkdir(parents=True, exist_ok=True)
    built: list[BuiltFixture] = []
    task_ids_by_fixture: dict[str, list[str]] = {}
    for task in tasks:
        task_ids_by_fixture.setdefault(str(task["fixture"]), []).append(str(task["task_id"]))
    for fixture_id in fixture_ids:
        root = output_root / fixture_id
        _safe_reset_fixture(root, output_root)
        _write_text(root / "CONSTITUTION.md", _render_constitution(constitution_sections))
        if fixture_id == real["fixture_id"]:
            _build_real(root, real)
        else:
            _build_adversarial(root, source_by_id[fixture_id])
        _write_text(
            root / "CONSTITUTION_BINDINGS.json",
            json.dumps(
                _fixture_binding_document(fixture_id, constitution_sections, constitution_bindings),
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        _write_text(
            root / "REVISION_CONSTITUTION_BINDINGS.json",
            json.dumps(
                _fixture_revision_binding_document(fixture_id, revision_constitution_bindings),
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        content_fingerprint = tree_fingerprint(root)
        fixture_manifest = {
            "schema": "context-fixture-manifest.v1",
            "fixture_id": fixture_id,
            "experiment_base_sha": manifest["base_sha"],
            "task_ids": task_ids_by_fixture[fixture_id],
            "content_fingerprint": content_fingerprint,
            "gold_included": False,
            "generated_by": "experiments/context-derivation/generate_fixtures.py",
        }
        _write_text(root / "FIXTURE_MANIFEST.json", json.dumps(fixture_manifest, indent=2, sort_keys=True) + "\n")
        assert_gold_isolated(root)
        built.append(BuiltFixture(fixture_id, root, content_fingerprint))
    generated_tasks = {
        "schema": "context-generated-tasks.v1",
        "source_manifest_fingerprint": fingerprint(manifest),
        "tasks": [
            {
                **task,
                "fixture": Path(
                    os.path.relpath(output_root / str(task["fixture"]), EXPERIMENT_ROOT)
                ).as_posix(),
            }
            for task in tasks
        ],
    }
    _write_text(output_root.parent / "tasks.json", json.dumps(generated_tasks, indent=2, sort_keys=True) + "\n")
    return built


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="validate definitions without materializing fixtures")
    args = parser.parse_args(argv)
    manifest, gold, tasks = load_definitions()
    if args.check:
        print(
            json.dumps(
                {
                    "ok": True,
                    "tasks": len(tasks),
                    "fixtures": len({task["fixture"] for task in tasks}),
                    "gold_approval_status": gold["approval_status"],
                    "scored_execution_approved": scored_execution_approved(),
                    "manifest_fingerprint": fingerprint(manifest),
                },
                sort_keys=True,
            )
        )
        return 0
    for result in build_all(args.output):
        print(f"built {result.fixture_id} {result.content_fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
