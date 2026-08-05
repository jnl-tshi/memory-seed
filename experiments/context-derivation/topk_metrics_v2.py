"""Deterministic offline top-K diagnostics for ADR context derivation.

This module intentionally consumes already-captured ranked decision rows.  It
does not call retrieval, read a runtime, materialize a packet, or contribute a
field to an MCP response.  Its job is to make the expansion policy measurable:
only a strong, canonical, non-``related`` decision may expand to ADRs; ADRs in
turn may expand to explicitly bound Constitution references.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


SCHEMA = "context-top-k-metrics.v2"
K_VALUES = (1, 2, 3, 5, 8)
_DECISION_REF_RE = re.compile(r"^(?:mse_[a-z0-9]+|ms-[a-z0-9]+):d[1-9][0-9]*$")
_RELEVANCE = frozenset({"strong", "weak", "none"})


def _string_set(value: Any, *, field: str) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field} must be an array of strings")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} must not contain duplicates")
    return set(value)


def _rate(hits: set[str], required: set[str]) -> dict[str, Any]:
    return {
        "hits": len(hits & required),
        "required": len(required),
        "rate": (len(hits & required) / len(required)) if required else None,
    }


def _validate_gold(gold: Mapping[str, Any]) -> tuple[set[str], set[str], set[str]]:
    if not isinstance(gold, Mapping):
        raise ValueError("gold must be an object")
    fields = (
        "required_decision_refs",
        "required_adr_ids",
        "required_constitution_refs",
    )
    missing = [field for field in fields if field not in gold]
    if missing:
        raise ValueError("gold is missing required fields: " + ", ".join(missing))
    decisions = _string_set(gold["required_decision_refs"], field="required_decision_refs")
    invalid = sorted(ref for ref in decisions if not _DECISION_REF_RE.fullmatch(ref))
    if invalid:
        raise ValueError("gold has non-canonical decision refs: " + ", ".join(invalid))
    return (
        decisions,
        _string_set(gold["required_adr_ids"], field="required_adr_ids"),
        _string_set(gold["required_constitution_refs"], field="required_constitution_refs"),
    )


def _validate_mapping(
    value: Mapping[str, Sequence[str]], *, field: str, keys_are_decisions: bool = False
) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    normalized: dict[str, tuple[str, ...]] = {}
    for key, refs in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field} keys must be non-empty strings")
        if keys_are_decisions and not _DECISION_REF_RE.fullmatch(key):
            raise ValueError(f"{field} key is not a canonical decision ref: {key}")
        values = _string_set(refs, field=f"{field}[{key!r}]")
        normalized[key] = tuple(sorted(values))
    return normalized


def _normalize_rows(ranked_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(ranked_rows, Sequence) or isinstance(ranked_rows, (str, bytes)):
        raise ValueError("ranked_rows must be an ordered array of decision rows")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, row in enumerate(ranked_rows, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"ranked row {rank} must be an object")
        ref = row.get("decision_ref")
        relevance = row.get("relevance")
        relation_type = row.get("relation_type", row.get("edge_type"))
        if not isinstance(ref, str) or not _DECISION_REF_RE.fullmatch(ref):
            raise ValueError(f"ranked row {rank} has no canonical decision_ref")
        if relevance not in _RELEVANCE:
            raise ValueError(f"ranked row {rank} relevance must be strong, weak, or none")
        if relation_type is not None and relation_type not in {"related", "evolves", "replaces"}:
            raise ValueError(f"ranked row {rank} has unknown relation_type")
        if ref in seen:
            raise ValueError(f"ranked_rows has duplicate decision_ref: {ref}")
        seen.add(ref)
        rows.append({
            "rank": rank,
            "decision_ref": ref,
            "relevance": relevance,
            "relation_type": relation_type,
        })
    return rows


def _eligible(row: Mapping[str, Any]) -> bool:
    """Return whether a row may mechanically trigger ADR expansion."""
    return row["relevance"] == "strong" and row["relation_type"] != "related"


def _selected_expansions(
    prefix: Sequence[Mapping[str, Any]], requested: set[str] | None
) -> tuple[set[str], set[str], set[str]]:
    """Return valid, invalid, and suppressed expansion refs for one K prefix."""
    prefix_by_ref = {str(row["decision_ref"]): row for row in prefix}
    if requested is None:
        chosen = {ref for ref, row in prefix_by_ref.items() if _eligible(row)}
    else:
        chosen = requested & set(prefix_by_ref)
    valid = {ref for ref in chosen if _eligible(prefix_by_ref[ref])}
    invalid = chosen - valid
    suppressed = {
        ref for ref, row in prefix_by_ref.items()
        if not _eligible(row) and ref not in chosen
    }
    return valid, invalid, suppressed


def measure_top_k(
    ranked_rows: Sequence[Mapping[str, Any]],
    gold: Mapping[str, Any],
    *,
    adr_membership: Mapping[str, Sequence[str]],
    constitution_bindings: Mapping[str, Sequence[str]],
    expanded_decision_refs: Iterable[str] | None = None,
    k_values: Iterable[int] = K_VALUES,
) -> dict[str, Any]:
    """Measure decision-to-ADR-to-Constitution recall at deterministic K values.

    ``expanded_decision_refs`` is optional instrumentation from a future
    resolver.  If absent, this diagnostic applies the proposed policy itself.
    If supplied, it exposes a resolver that attempted to expand weak, none, or
    related rows through ``false_expansion`` while ensuring those rows never
    contribute ADR or Constitution recall.
    """
    rows = _normalize_rows(ranked_rows)
    required_decisions, required_adrs, required_constitution = _validate_gold(gold)
    memberships = _validate_mapping(adr_membership, field="adr_membership", keys_are_decisions=True)
    bindings = _validate_mapping(constitution_bindings, field="constitution_bindings")

    values = tuple(k_values)
    if not values or any(not isinstance(value, int) or value <= 0 for value in values):
        raise ValueError("k_values must contain positive integers")
    if len(values) != len(set(values)):
        raise ValueError("k_values must not contain duplicates")
    unsupported = sorted(set(values) - set(K_VALUES))
    if unsupported:
        raise ValueError("unsupported K values: " + ", ".join(map(str, unsupported)))

    requested: set[str] | None = None
    if expanded_decision_refs is not None:
        if isinstance(expanded_decision_refs, (str, bytes)):
            raise ValueError("expanded_decision_refs must be an iterable of canonical decision refs")
        requested = set(expanded_decision_refs)
        if any(not isinstance(ref, str) or not _DECISION_REF_RE.fullmatch(ref) for ref in requested):
            raise ValueError("expanded_decision_refs must contain canonical decision refs")
        unknown = requested - {str(row["decision_ref"]) for row in rows}
        if unknown:
            raise ValueError("expanded_decision_refs are absent from ranked_rows: " + ", ".join(sorted(unknown)))

    first_hit_rank = next(
        (row["rank"] for row in rows if row["decision_ref"] in required_decisions), None
    )
    metrics: dict[str, dict[str, Any]] = {}
    for k in sorted(values):
        prefix = rows[:k]
        ranked_refs = {str(row["decision_ref"]) for row in prefix}
        valid_expansions, invalid_expansions, suppressed = _selected_expansions(prefix, requested)
        selected_adrs = {
            adr_id for ref in valid_expansions for adr_id in memberships.get(ref, ())
        }
        selected_constitution = {
            section for adr_id in selected_adrs for section in bindings.get(adr_id, ())
        }
        attempted = len(valid_expansions) + len(invalid_expansions)
        metrics[str(k)] = {
            "decision_recall": _rate(ranked_refs, required_decisions),
            "adr_trigger_recall": _rate(selected_adrs, required_adrs),
            "constitution_binding_recall": _rate(selected_constitution, required_constitution),
            "mrr_at_k": (1 / first_hit_rank) if first_hit_rank is not None and first_hit_rank <= k else 0.0,
            "strong_canonical_decision_refs": sorted(
                row["decision_ref"] for row in prefix if _eligible(row)
            ),
            "expanded_decision_refs": sorted(valid_expansions),
            "selected_adr_ids": sorted(selected_adrs),
            "selected_constitution_refs": sorted(selected_constitution),
            "false_expansion": {
                "invalid_decision_refs": sorted(invalid_expansions),
                "suppressed_decision_refs": sorted(suppressed),
                "attempted": attempted,
                "count": len(invalid_expansions),
                "rate": len(invalid_expansions) / attempted if attempted else 0.0,
            },
        }
    return {
        "schema": SCHEMA,
        "k_values": sorted(values),
        "first_hit_rank": first_hit_rank,
        "mrr": (1 / first_hit_rank) if first_hit_rank is not None else 0.0,
        "metrics": metrics,
    }
