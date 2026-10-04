"""Inventory the authoritative Markdown corpus before hosted import.

The scanner is deliberately dependency-free and lexical.  Several historical
sidecar blocks are accepted by Memory Seed's parser but are not generic YAML
(most commonly an unquoted colon in a note).  Running a generic YAML loader
would therefore turn valid historical evidence into a false parse failure.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Any, Iterable

from memory_seed.core import iter_session_documents


_ENTRY_HEADING = re.compile(r"^##\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+-", re.MULTILINE)
_RECORD_HEADING = re.compile(
    r"^(?:####\s+D\d+\s+-\s+(?:Decision|Documentation):|###\s+Decision(?:\s+\d+)?:)",
    re.MULTILINE,
)
_RECORD_FIELD = re.compile(r"^-\s+(?:\*\*)?([^*:\n]+?):(?:\*\*)?\s*", re.MULTILINE)
_CONSTITUTION_REF = re.compile(r"constitution-ref:\s*([^\s>]+)")
_CONSTITUTION_TOPIC = re.compile(r"constitution-topic:\s*([^\s>]+)")
_ADR_JSON = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
_YAML_FENCE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
_STRUCTURAL_RECORD_FIELDS = {
    "A",
    "Alternatives",
    "D",
    "Decision",
    "Disposition",
    "F",
    "Files",
    "R",
    "Rationale",
    "S",
    "Scope",
    "Sources",
    "T",
    "Tests",
}


def load_json_yaml(path: Path) -> dict[str, Any]:
    """Load a contract written in the JSON subset of YAML."""
    return json.loads(path.read_text(encoding="utf-8"))


def _blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() != "---":
            continue
        if start is None:
            start = index + 1
        else:
            blocks.append("\n".join(lines[start:index]))
            start = None
    return blocks


def _clean_scalar(value: str) -> str | None:
    value = value.strip()
    if not value or value in {"[]", "{}"}:
        return None
    if value in {"null", "~"}:
        return "<null>"
    if value.startswith("[") and value.endswith("]"):
        return None
    if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
        value = value[1:-1]
    return value.strip() or None


def _yaml_lex(block: str) -> tuple[set[str], dict[str, list[str]]]:
    """Return dotted key paths and scalar values without requiring valid YAML."""
    fields: set[str] = set()
    values: dict[str, list[str]] = {}
    stack: list[tuple[int, str]] = []
    sequence_path: str | None = None

    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()
        is_sequence = content.startswith("- ")
        if is_sequence:
            content = content[2:].strip()
        match = re.match(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$", content)
        if not match:
            if is_sequence and sequence_path:
                scalar = _clean_scalar(content)
                if scalar is not None:
                    values.setdefault(sequence_path, []).append(scalar)
            continue

        key, raw_value = match.group(1), match.group(2) or ""
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else ""
        path = f"{parent}.{key}" if parent else key
        fields.add(path)
        scalar = _clean_scalar(raw_value)
        if scalar is not None:
            values.setdefault(path, []).append(scalar)
        else:
            stack.append((indent, path))
            sequence_path = path
        if is_sequence and scalar is not None:
            sequence_path = parent or path
    return fields, values


def _flatten_json(value: Any, prefix: str = "") -> set[str]:
    fields: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            fields.add(path)
            fields.update(_flatten_json(child, path))
    elif isinstance(value, list):
        wildcard = f"{prefix}.*" if prefix else "*"
        if value:
            fields.add(wildcard)
        for child in value:
            fields.update(_flatten_json(child, wildcard))
    return fields


def _normalise_path(path: str) -> str:
    parts = path.split(".")
    if parts[:1] == ["decision_origins"] and len(parts) > 1:
        return "decision_origins.*"
    if parts[:1] in (["edge_confidence"], ["edge_evidence"]) and len(parts) > 2:
        return ".".join((parts[0], "*", *parts[2:]))
    if parts[:1] == ["topics"] and len(parts) >= 3:
        # Topic axes and slugs are data, not schema.  Child slugs are likewise
        # represented by a wildcard while their structural fields stay exact.
        normalised = ["topics", "*", "*"]
        remaining = parts[3:]
        while remaining:
            if remaining[0] == "children" and len(remaining) >= 2:
                normalised.extend(("children", "*"))
                remaining = remaining[2:]
            else:
                normalised.append(remaining[0])
                remaining = remaining[1:]
        return ".".join(normalised)
    return path


def _add_yaml_fields(target: set[str], prefix: str, block: str) -> dict[str, list[str]]:
    fields, values = _yaml_lex(block)
    target.update(f"{prefix}.{_normalise_path(field)}" for field in fields)
    return values


def _scalar(values: dict[str, list[str]], key: str) -> Iterable[str]:
    return values.get(key, ())


def build_inventory(root: str | Path) -> dict[str, Any]:
    """Scan all live import families beneath *root* deterministically."""
    root = Path(root)
    memory = root / ".memory-seed"
    sessions = memory / "sessions"
    fields: set[str] = set()
    families: set[str] = set()
    counts: Counter[str] = Counter()
    actors: dict[str, set[str]] = {
        "user_initials": set(),
        "agent_types": set(),
        "legacy_agent_names": set(),
        "decision_origins": set(),
        "provenance_sources": set(),
        "member_slugs": set(),
        "member_initials": set(),
        "member_display_names": set(),
    }
    actor_counts: dict[str, Counter[str]] = {key: Counter() for key in actors}

    def observe(dimension: str, observed: Iterable[str]) -> None:
        values = list(observed)
        actors[dimension].update(values)
        actor_counts[dimension].update(values)

    sidecar_dirs = {"links", "topics", "diagrams"}
    if sessions.is_dir():
        for document in iter_session_documents(sessions):
            path = document.path
            families.add("sessions")
            text = path.read_text(encoding="utf-8")
            blocks = _blocks(text)
            has_file_frontmatter = text.startswith("---\n") or text.startswith("---\r\n")
            if blocks and has_file_frontmatter:
                _add_yaml_fields(fields, "sessions.file", blocks[0])
            metadata_blocks = [
                *(blocks[1:] if has_file_frontmatter else blocks),
                *_YAML_FENCE.findall(text),
            ]
            for block in metadata_blocks:
                values = _add_yaml_fields(fields, "sessions.entry", block)
                observe("user_initials", _scalar(values, "user_initials"))
                observe("agent_types", _scalar(values, "agent_type"))
                observe("legacy_agent_names", _scalar(values, "agent_name"))
                for key, observed in values.items():
                    if key.startswith("decision_origins."):
                        observe("decision_origins", observed)
            entry_count = len(_ENTRY_HEADING.findall(text))
            counts["session_files"] += 1
            counts["session_entries"] += entry_count
            if _RECORD_HEADING.search(text):
                fields.update(
                    {
                        "sessions.record.heading.kind",
                        "sessions.record.heading.ordinal",
                        "sessions.record.heading.title",
                    }
                )
            for label in _RECORD_FIELD.findall(text):
                label = label.strip()
                if label in _STRUCTURAL_RECORD_FIELDS:
                    fields.add(f"sessions.record.{label.replace(' ', '_')}")

        for family, singular in (("links", "link"), ("topics", "topic"), ("diagrams", "diagram")):
            base = sessions / family
            if not base.is_dir():
                continue
            families.add(f"session-{singular}-sidecars")
            for path in sorted(base.rglob("*.md")):
                text = path.read_text(encoding="utf-8")
                blocks = _blocks(text)
                if blocks:
                    _add_yaml_fields(fields, f"{family}.file", blocks[0])
                assertion_blocks = [*blocks[1:], *_YAML_FENCE.findall(text)]
                for block in assertion_blocks:
                    values = _add_yaml_fields(fields, f"{family}.assertion", block)
                    observe("provenance_sources", _scalar(values, "source"))
                    counts[f"{singular}_assertions"] += 1
                counts[f"{singular}_sidecar_files"] += 1

    decisions = memory / "decisions"
    if decisions.is_dir():
        families.add("living-adrs")
        for path in sorted(decisions.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            blocks = _blocks(text)
            if blocks:
                values = _add_yaml_fields(fields, "adrs.frontmatter", blocks[0])
                observe("user_initials", _scalar(values, "user_initials"))
                observe("agent_types", _scalar(values, "agent_type"))
                observe("provenance_sources", _scalar(values, "source"))
            for match in _ADR_JSON.findall(text):
                try:
                    event = json.loads(match)
                except json.JSONDecodeError:
                    fields.add("adrs.event.raw_unparsed_json")
                    continue
                fields.update(f"adrs.event.{item}" for item in _flatten_json(event))
                source = event.get("source")
                if isinstance(source, str):
                    observe("provenance_sources", (source,))
                counts["adr_events"] += 1
            fields.update(
                {
                    "adrs.current_view.authoritative_decision",
                    "adrs.current_view.body_markdown",
                    "adrs.current_view.status",
                }
            )
            counts["adrs"] += 1

    topics_path = memory / "topics.yaml"
    if topics_path.is_file():
        families.add("topic-catalog")
        _add_yaml_fields(fields, "topics_index", topics_path.read_text(encoding="utf-8"))
        counts["topic_catalogs"] += 1

    project_path = memory / "project.yaml"
    if project_path.is_file():
        families.add("project-actors")
        values = _add_yaml_fields(fields, "project", project_path.read_text(encoding="utf-8"))
        observe("member_slugs", _scalar(values, "participants.slug"))
        observe("member_initials", _scalar(values, "participants.initials"))
        observe("member_display_names", _scalar(values, "participants.display_name"))
        counts["project_manifests"] += 1

    constitution = root / "docs" / "CONSTITUTION.md"
    if constitution.is_file():
        families.add("constitution")
        text = constitution.read_text(encoding="utf-8")
        blocks = _blocks(text)
        if blocks:
            _add_yaml_fields(fields, "constitution.frontmatter", blocks[0])
        if _CONSTITUTION_REF.search(text):
            fields.add("constitution.clause.anchor")
            counts["constitution_clauses"] += len(_CONSTITUTION_REF.findall(text))
        if _CONSTITUTION_TOPIC.search(text):
            fields.add("constitution.clause.topic")

    archive = memory / "archive"
    if archive.is_dir() and any(path.is_file() for path in archive.rglob("*")):
        families.add("archive-snapshots")
        fields.add("archive.artifact.raw_bytes")
        fields.add("archive.artifact.relative_path")
        counts["archive_files"] = sum(1 for path in archive.rglob("*") if path.is_file())

    return {
        "schema_version": 1,
        "counts": dict(sorted(counts.items())),
        "families": sorted(families),
        "observed_fields": sorted(fields),
        "observed_actors": {key: sorted(value) for key, value in sorted(actors.items())},
        "observed_actor_counts": {
            key: dict(sorted(value.items())) for key, value in sorted(actor_counts.items())
        },
    }


def validate_inventory(
    inventory: dict[str, Any], crosswalk: dict[str, Any], actors: dict[str, Any]
) -> dict[str, list[str]]:
    """Compare observed vocabulary with the approved classification contracts."""
    classified_fields = {item["source"] for item in crosswalk["fields"]}
    unknown_fields = sorted(set(inventory["observed_fields"]) - classified_fields)

    unknown_actors: list[str] = []
    dimensions = actors["dimensions"]
    for dimension, values in inventory["observed_actors"].items():
        classified_values = set(dimensions.get(dimension, {}).get("values", {}))
        unknown_actors.extend(
            f"{dimension}={value}" for value in values if value not in classified_values
        )

    required = set(crosswalk["required_families"])
    missing_families = sorted(required - set(inventory["families"]))
    return {
        "unknown_fields": unknown_fields,
        "unknown_actors": sorted(unknown_actors),
        "missing_required_families": missing_families,
    }
