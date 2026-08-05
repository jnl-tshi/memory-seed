"""Query-only corpus for the lightweight Top-K experiment.

The subject path intentionally opens the v2 manifest and this query corpus only.
Gold is loaded solely by :func:`join_queries_to_gold`, which is a scoring helper.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parent
SOURCE_MANIFEST = ROOT / "tasks" / "revision_constitution_manifest.v2.json"
GOLD = ROOT / "tasks" / "revision_constitution_gold.v2.json"
QUERY_VARIANTS = ROOT / "tasks" / "revision_constitution_queries.v1.json"
QUERY_SCHEMA = "context-query-variants.v1"
QUERY_ROW_SCHEMA = "context-query-variant.v1"
_ROUTING_FIELDS = frozenset({"fixture", "resolver_hints"})
_SUBJECT_FIELDS = frozenset({"query_id", "parent_task_id", "variant_index", "question", *_ROUTING_FIELDS})
_GOLD_FIELD_NAMES = frozenset({
    "approval_status", "authoritative_refs", "expected_statuses", "insufficient_evidence",
    "relevant_refs", "required_adr_ids", "required_constitution_bindings",
    "required_lineage_edges", "required_missing_refs", "required_related_edges",
})


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(value: Any) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _manifest_tasks(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schema") != "context-benchmark-manifest.v2":
        raise ValueError("source manifest schema must be context-benchmark-manifest.v2")
    rows = manifest.get("tasks")
    expected = [f"CTX-{number:02d}" for number in range(1, 13)]
    if not isinstance(rows, list) or [row.get("task_id") for row in rows if isinstance(row, dict)] != expected:
        raise ValueError("source manifest must contain ordered CTX-01 through CTX-12 rows")
    return rows


def _canonical_payload(source_manifest_fingerprint: str, queries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema": QUERY_SCHEMA,
        "source_manifest_fingerprint": source_manifest_fingerprint,
        "queries": list(queries),
    }


def validate_query_variants(
    value: Mapping[str, Any], *, source_manifest: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Validate the query-only contract against the v2 manifest, never gold."""
    if value.get("schema") != QUERY_SCHEMA:
        raise ValueError(f"query corpus schema must be {QUERY_SCHEMA}")
    source_tasks = _manifest_tasks(source_manifest)
    source_fingerprint = _fingerprint(source_manifest)
    if value.get("source_manifest_fingerprint") != source_fingerprint:
        raise ValueError("query corpus source_manifest_fingerprint does not match the v2 manifest")
    rows = value.get("queries")
    if not isinstance(rows, list) or len(rows) != 60 or value.get("query_count") != 60:
        raise ValueError("query corpus must contain exactly sixty rows")
    expected_ids = [f"CTX-{parent:02d}.V{variant:02d}" for parent in range(1, 13) for variant in range(1, 6)]
    if [row.get("query_id") if isinstance(row, dict) else None for row in rows] != expected_ids:
        raise ValueError("query IDs must be unique and in parent/variant stable order")
    source_by_id = {str(row["task_id"]): row for row in source_tasks}
    questions: set[str] = set()
    for row, expected_id in zip(rows, expected_ids):
        if not isinstance(row, dict) or set(row) != {"schema", *_SUBJECT_FIELDS}:
            raise ValueError(f"{expected_id} must contain only query and routing fields")
        parent, variant = expected_id.split(".", 1)
        if row.get("schema") != QUERY_ROW_SCHEMA or row.get("parent_task_id") != parent:
            raise ValueError(f"{expected_id} has an invalid query parent")
        if row.get("variant_index") != int(variant[1:]):
            raise ValueError(f"{expected_id} has an invalid variant index")
        question = row.get("question")
        if not isinstance(question, str) or not question.strip() or question in questions:
            raise ValueError(f"{expected_id} question must be non-empty and unique")
        questions.add(question)
        source = source_by_id[parent]
        for field in _ROUTING_FIELDS:
            if row.get(field) != source.get(field):
                raise ValueError(f"{expected_id} {field} must match the source manifest")
    canonical = _canonical_payload(source_fingerprint, rows)
    if value.get("canonical_fingerprint") != _fingerprint(canonical):
        raise ValueError("query corpus canonical_fingerprint is not stable")
    return rows


def load_query_variants() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load and validate subject-visible queries without opening the v2 gold file."""
    manifest = _read(SOURCE_MANIFEST)
    corpus = _read(QUERY_VARIANTS)
    return corpus, validate_query_variants(corpus, source_manifest=manifest)


def assert_subject_visible(rows: Sequence[Mapping[str, Any]]) -> None:
    """Fail closed if a subject payload contains gold keys or opaque label blobs."""
    for row in rows:
        if set(row) != _SUBJECT_FIELDS:
            raise ValueError("subject-visible query has non-subject fields")
        encoded = _canonical_json(row)
        if any(field in encoded for field in _GOLD_FIELD_NAMES):
            raise ValueError("subject-visible query contains a gold field name")
        if "gold" in encoded or "labels" in encoded:
            raise ValueError("subject-visible query contains a serialized gold fragment")


def subject_visible_queries() -> list[dict[str, Any]]:
    """Return detached query rows suitable for a subject packet or run directory."""
    _corpus, rows = load_query_variants()
    visible = [{field: row[field] for field in _SUBJECT_FIELDS} for row in rows]
    assert_subject_visible(visible)
    return visible


def materialize_subject_queries(path: str | Path) -> Path:
    """Write the query-only payload; this path has no dependency on v2 gold."""
    output = Path(path)
    payload = {"schema": QUERY_SCHEMA, "queries": subject_visible_queries()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def join_queries_to_gold() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Scoring-only inheritance join from a query parent to its immutable v2 gold row."""
    _corpus, queries = load_query_variants()
    gold = _read(GOLD)
    if gold.get("schema") != "context-gold.v2" or not isinstance(gold.get("tasks"), list):
        raise ValueError("v2 gold schema must be context-gold.v2")
    labels = {row.get("task_id"): row for row in gold["tasks"] if isinstance(row, dict)}
    if set(labels) != {f"CTX-{number:02d}" for number in range(1, 13)}:
        raise ValueError("v2 gold must have exactly one row for every parent task")
    return [(query, labels[query["parent_task_id"]]) for query in queries]
