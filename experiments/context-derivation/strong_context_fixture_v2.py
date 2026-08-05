"""Read-only bridge from generated fixtures to the tiered context resolver.

The experiment keeps three authoritative inputs separate: session decisions,
ADR ledgers, and explicit fixture Constitution bindings.  This module joins
them only in memory, so an offline sweep exercises the actual ADR replay and
the production decision-level ranking without changing either production
format.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from memory_seed.adr import adr_membership, parse_adr, proposal_for
from memory_seed.retrieval import search_memory


FIXTURE_BINDINGS_SCHEMA = "context-fixture-adr-constitution-bindings.v1"
MATERIALIZED_SCHEMA = "strong-context-v2-bindings.v1"


def _load_strong_context() -> Any:
    path = Path(__file__).with_name("strong_context_v2.py")
    spec = importlib.util.spec_from_file_location("strong_context_v2_fixture_bridge", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load strong_context_v2.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read fixture binding document {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("fixture binding document must be a JSON object")
    return value


def _section_index(document: Mapping[str, Any], root: Path) -> dict[str, Mapping[str, str]]:
    sections = document.get("sections")
    constitution_path = root / "CONSTITUTION.md"
    if not isinstance(sections, list) or not constitution_path.is_file():
        raise ValueError("generated fixture is missing Constitution sections")
    constitution = constitution_path.read_text(encoding="utf-8")
    indexed: dict[str, Mapping[str, str]] = {}
    for section in sections:
        if not isinstance(section, dict) or set(section) != {"ref", "title", "text", "digest"}:
            raise ValueError("fixture Constitution section has an invalid shape")
        ref, text, digest = section.get("ref"), section.get("text"), section.get("digest")
        if not all(isinstance(value, str) and value for value in (ref, text, digest)) or ref in indexed:
            raise ValueError("fixture Constitution section has invalid or duplicate data")
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != actual:
            raise ValueError(f"fixture Constitution section {ref} has a stale digest")
        if f"constitution-ref: {ref}" not in constitution or text not in constitution:
            raise ValueError(f"fixture Constitution section {ref} is not materialized in CONSTITUTION.md")
        indexed[ref] = {"ref": ref, "title": str(section["title"]), "text": text, "digest": digest}
    return indexed


def _lineage(record: Any) -> list[dict[str, Any]]:
    statuses = record.state.revision_statuses

    def relation_type(assertion: str) -> str:
        for kind in ("evolves", "replaces"):
            if f":{kind}:" in assertion:
                return kind
        raise ValueError(f"ADR predecessor has no typed lifecycle assertion: {assertion}")

    return [
        {
            "ref": event.decision_ref,
            "predecessors": [
                {"ref": predecessor.decision, "type": relation_type(predecessor.relation_assertion)}
                for predecessor in event.predecessors
            ],
            "status": statuses.get(event.decision_ref, "proposed"),
            "decision": event.decision,
            "why": event.why,
            "evolution": event.evolution,
        }
        for event in record.events
        if event.kind == "revision-proposed" and event.decision_ref
    ]


def materialize_fixture_bindings(fixture_root: str | Path) -> dict[str, Any]:
    """Build the resolver's binding contract from a generated fixture root.

    Membership comes from every proposed revision and curated predecessor in
    the parsed ADR ledger.  ``supporting_decisions`` stay explicitly separate
    so a related evidence reference cannot be promoted to lineage by this
    bridge.
    """
    root = Path(fixture_root).resolve()
    document = _read_json(root / "CONSTITUTION_BINDINGS.json")
    if set(document) != {"schema", "fixture_id", "sections", "bindings"}:
        raise ValueError("fixture binding document has an invalid top-level shape")
    if document.get("schema") != FIXTURE_BINDINGS_SCHEMA or not isinstance(document.get("fixture_id"), str):
        raise ValueError(f"fixture binding document must use {FIXTURE_BINDINGS_SCHEMA!r}")
    manifest = _read_json(root / "FIXTURE_MANIFEST.json")
    if manifest.get("schema") != "context-fixture-manifest.v1" or manifest.get("fixture_id") != document["fixture_id"]:
        raise ValueError("fixture manifest does not match the binding document")
    bindings = document.get("bindings")
    if not isinstance(bindings, list):
        raise ValueError("fixture binding document bindings must be an array")
    sections = _section_index(document, root)
    decisions_dir = root / ".memory-seed" / "decisions"
    if not decisions_dir.is_dir():
        raise ValueError("generated fixture has no ADR decisions directory")

    binding_by_adr: dict[str, Mapping[str, Any]] = {}
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {
            "fixture_id", "adr_id", "decision_refs", "constitution_refs"
        }:
            raise ValueError("fixture ADR binding has an invalid shape")
        if binding.get("fixture_id") != document["fixture_id"]:
            raise ValueError("fixture ADR binding belongs to another fixture")
        adr_id = binding.get("adr_id")
        if not isinstance(adr_id, str) or not adr_id or adr_id in binding_by_adr:
            raise ValueError("fixture ADR bindings must have unique ADR IDs")
        binding_by_adr[adr_id] = binding

    paths = sorted(decisions_dir.glob("adr_*.md"), key=lambda path: path.name)
    records = {record.adr_id: record for record in (parse_adr(path) for path in paths)}
    if set(records) != set(binding_by_adr):
        raise ValueError("fixture ADR binding coverage does not match the ADR ledger set")

    strong = _load_strong_context()
    rows: list[dict[str, Any]] = []
    for adr_id in sorted(records):
        record = records[adr_id]
        binding = binding_by_adr[adr_id]
        membership = sorted(adr_membership(record))
        declared = binding.get("decision_refs")
        if not isinstance(declared, list) or not all(isinstance(ref, str) for ref in declared):
            raise ValueError(f"fixture ADR {adr_id} decision_refs must be an array of strings")
        if not set(declared) <= set(membership):
            raise ValueError(f"fixture ADR {adr_id} binding names a non-lineage decision")
        if not membership:
            raise ValueError(f"fixture ADR {adr_id} has no decision membership")
        state = record.state
        synopsis = proposal_for(record, state.authoritative_decision)
        section_refs = binding.get("constitution_refs")
        if not isinstance(section_refs, list) or not section_refs:
            raise ValueError(f"fixture ADR {adr_id} must bind Constitution sections")
        constitution: list[dict[str, str]] = []
        seen_sections: set[str] = set()
        governing = 0
        for item in section_refs:
            if not isinstance(item, dict) or set(item) != {"ref", "role"}:
                raise ValueError(f"fixture ADR {adr_id} has a malformed Constitution binding")
            ref, role = item.get("ref"), item.get("role")
            if not isinstance(ref, str) or ref not in sections or ref in seen_sections or role not in {"governing", "supporting"}:
                raise ValueError(f"fixture ADR {adr_id} has an invalid Constitution binding")
            seen_sections.add(ref)
            governing += int(role == "governing")
            constitution.append({"ref": ref, "role": role, "excerpt": sections[ref]["text"]})
        if not governing:
            raise ValueError(f"fixture ADR {adr_id} must include a governing Constitution section")
        related = sorted(
            {
                ref
                for event in record.events
                if event.kind == "revision-proposed"
                for ref in event.supporting_decisions
                if strong.is_canonical_decision_ref(ref) and ref not in membership
            }
        )
        rows.append(
            {
                "adr_id": adr_id,
                "membership": membership,
                "current": {
                    "authoritative_ref": state.authoritative_decision,
                    "status": state.current_status,
                    "decision": synopsis.decision if state.authoritative_decision and synopsis else "",
                    "why": synopsis.why if state.authoritative_decision and synopsis else "",
                    "evolution": synopsis.evolution if state.authoritative_decision and synopsis else "",
                },
                "lineage": _lineage(record),
                "constitution_refs": constitution,
                "related_refs": related,
            }
        )
    materialized = {"schema": MATERIALIZED_SCHEMA, "adrs": rows}
    strong.load_bindings(materialized)
    return materialized


def ranked_fixture_payload(query: str, fixture_root: str | Path, *, top_k: int = 8) -> dict[str, Any]:
    """Adapt real decision-level retrieval rows for the experiment resolver.

    This is an offline evaluator helper.  It deliberately exposes no new MCP
    field and turns semantic ranking off so a fixture remains deterministic
    across machines while still exercising the production lexical ranking and
    relevance classifier.
    """
    if not isinstance(query, str) or not query.strip() or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("query must be non-empty and top_k must be positive")
    payload = search_memory(query, cwd=fixture_root, top_k=top_k, semantic_enabled=False, granularity="decision")
    rows: list[dict[str, Any]] = []
    for result in payload["results"]:
        rows.append(
            {
                "ref": result["chunk_id"],
                "relevance": result["relevance"],
                "excerpt": result["excerpt"],
                "links": {
                    "evolves": list(result["evolves"]),
                    "replaces": list(result["replaces"]),
                    "related": list(result["related_entries"]),
                },
            }
        )
    return {
        "rows": rows,
        "relevance_calibrated": bool(payload.get("relevance_calibrated", False)),
        "relevance_rule": payload.get("relevance_rule"),
    }


def ranked_fixture_results(query: str, fixture_root: str | Path, *, top_k: int = 8) -> list[dict[str, Any]]:
    """Compatibility wrapper for callers that only need ranked rows."""
    return ranked_fixture_payload(query, fixture_root, top_k=top_k)["rows"]
