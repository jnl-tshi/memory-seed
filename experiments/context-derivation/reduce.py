"""Hard-gate reducer for offline context-derivation shards."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from contracts import canonical_json, execution_approved, fingerprint, load_json
from strategies import normalize_strategy, strategy_fingerprint
from sweep import SHARD_SCHEMA


REDUCTION_SCHEMA = "context-reduction.v1"
CANDIDATE_SCHEMA = "context-candidate-manifest.v1"
HERE = Path(__file__).resolve().parent


def reduction_payload_fingerprint(value: Mapping[str, Any]) -> str:
    """Recompute the immutable reduction identity, excluding output metadata."""
    payload = dict(value)
    payload.pop("fingerprint", None)
    payload.pop("candidate_manifest", None)
    return fingerprint(payload)


def _edge_key(edge: Mapping[str, Any]) -> tuple[str, str, str]:
    return (str(edge.get("source", "")), str(edge.get("target", "")), str(edge.get("type", "")))


def _p95(values: Sequence[float]) -> float:
    if not values:
        return math.inf
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _status_ok(expected: Any, selected: Sequence[Mapping[str, Any]]) -> bool:
    actual = {str(item.get("adr_id")): item.get("status") for item in selected}
    if expected in (None, ""):
        return True
    if isinstance(expected, Mapping):
        return all(actual.get(str(adr_id)) == status for adr_id, status in expected.items())
    return bool(actual) and all(status == expected for status in actual.values())


def _gate(result: Mapping[str, Any], gold: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    selected_adrs = result.get("selected_adrs", [])
    adr_ids = {str(item.get("adr_id")) for item in selected_adrs}
    refs = set(map(str, result.get("selected_refs", [])))
    authoritative_heads = {
        str(item["authoritative_ref"])
        for item in selected_adrs
        if item.get("authoritative_ref")
    }
    expected_heads = set(map(str, gold.get("authoritative_refs", [])))
    lineage = {_edge_key(edge) for edge in result.get("lineage_edges", [])}
    related = {_edge_key(edge) for edge in result.get("related_edges", [])}
    required_edges = {_edge_key(edge) for edge in gold.get("required_lineage_edges", [])}
    required_related = {_edge_key(edge) for edge in gold.get("required_related_edges", [])}
    missing_adrs = set(map(str, gold.get("required_adr_ids", []))) - adr_ids
    missing_refs = expected_heads - refs
    if missing_adrs:
        failures.append("missing-required-adr:" + ",".join(sorted(missing_adrs)))
    if missing_refs:
        failures.append("missing-authoritative-ref:" + ",".join(sorted(missing_refs)))
    if authoritative_heads != expected_heads:
        failures.append("wrong-authoritative-head")
    if not required_edges <= lineage:
        failures.append("missing-lineage-edge")
    if not required_related <= related:
        failures.append("missing-related-edge")
    expected_statuses = gold.get("expected_statuses", gold.get("expected_status"))
    if not _status_ok(expected_statuses, selected_adrs):
        failures.append("wrong-status")
    if any(edge[2] == "related" for edge in lineage):
        failures.append("related-promoted-to-lineage")
    if any(edge[2] != "related" for edge in related):
        failures.append("non-related-edge-in-related-set")
    expected_absence = bool(gold.get("insufficient_evidence"))
    if expected_absence and not result.get("insufficient_evidence"):
        failures.append("missing-abstention")
    if expected_absence and not result.get("absence"):
        failures.append("absence-not-explicit")
    required_missing = set(map(str, gold.get("required_missing_refs", [])))
    reported_missing = {
        str(ref)
        for item in result.get("absence", [])
        for ref in item.get("refs", [])
    }
    if required_missing and not required_missing <= reported_missing:
        failures.append("wrong-missing-evidence-ref")
    if not expected_absence and result.get("insufficient_evidence"):
        failures.append("unexpected-abstention")
    allowed = set(map(str, gold.get("allowed_citations", [])))
    citations = set(map(str, result.get("citations", [])))
    material_refs = {str(item.get("ref")) for item in result.get("evidence", [])}
    if not citations <= material_refs:
        failures.append("citation-not-in-evidence")
    if allowed and not citations <= allowed:
        failures.append("unallowed-citation")
    return failures


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    keys = ("irrelevant_token_proxy", "total_token_proxy", "p95_latency_ms")
    return all(left[key] <= right[key] for key in keys) and any(left[key] < right[key] for key in keys)


def reduce_shards(
    shard_dir: str | Path,
    gold: Mapping[str, Any],
    *,
    expected_strategy_fingerprints: Iterable[str],
    candidate_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate completeness, apply gates, Pareto-reduce, and optionally freeze."""
    if gold.get("schema") != "context-gold.v1":
        raise ValueError("gold schema must be 'context-gold.v1'")
    gold_rows = {str(row["task_id"]): row for row in gold.get("tasks", [])}
    if not gold_rows or len(gold_rows) != len(gold.get("tasks", [])):
        raise ValueError("gold tasks must be a non-empty list with unique task_id values")
    shard_by_cell: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(Path(shard_dir).glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != SHARD_SCHEMA:
            raise ValueError(f"invalid shard schema: {path}")
        for field in ("task_fingerprint", "runtime_fingerprint", "resolver_fingerprint"):
            if not isinstance(value.get(field), str) or not value[field]:
                raise ValueError(f"missing {field} in shard: {path}")
        try:
            normalized = normalize_strategy(value.get("strategy") or {})
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid strategy in shard: {path}: {exc}") from exc
        computed_strategy_fingerprint = strategy_fingerprint(normalized)
        if value.get("strategy_fingerprint") != computed_strategy_fingerprint:
            raise ValueError(f"tampered strategy fingerprint in shard: {path}")
        result = value.get("result")
        if not isinstance(result, Mapping):
            raise ValueError(f"missing result in shard: {path}")
        stable_result = {
            key: item for key, item in result.items()
            if key not in {"elapsed_ms", "fingerprint"}
        }
        if result.get("fingerprint") != fingerprint(stable_result):
            raise ValueError(f"tampered result fingerprint in shard: {path}")
        if (
            result.get("task_id") != value.get("task_id")
            or result.get("strategy_fingerprint") != computed_strategy_fingerprint
            or normalize_strategy(result.get("strategy") or {}) != normalized
        ):
            raise ValueError(f"result/shard identity mismatch: {path}")
        if not value.get("deterministic"):
            value.setdefault("gate_failures", []).append("nondeterministic")
        cell = (str(value.get("task_id")), str(value.get("strategy_fingerprint")))
        previous = shard_by_cell.get(cell)
        if previous is not None:
            if canonical_json(previous) != canonical_json(value):
                raise ValueError(f"conflicting duplicate shard: {cell}")
            continue
        shard_by_cell[cell] = value
    shards = list(shard_by_cell.values())
    if not shards:
        raise ValueError("no sweep shards found")
    strategy_fps = set(expected_strategy_fingerprints)
    if not strategy_fps:
        raise ValueError("expected strategy fingerprints are required for completeness")
    expected = {(task_id, sfp) for task_id in gold_rows for sfp in strategy_fps}
    actual = {(str(s["task_id"]), str(s["strategy_fingerprint"])) for s in shards}
    missing = sorted(expected - actual)
    extras = sorted(actual - expected)
    if missing or extras:
        raise ValueError(f"incomplete shards: missing={missing}, extras={extras}")

    task_fingerprints: dict[str, str] = {}
    runtime_fingerprints: dict[str, str] = {}
    for task_id in gold_rows:
        task_cells = [item for item in shards if str(item["task_id"]) == task_id]
        task_values = {str(item["task_fingerprint"]) for item in task_cells}
        runtime_values = {str(item["runtime_fingerprint"]) for item in task_cells}
        if len(task_values) != 1 or len(runtime_values) != 1:
            raise ValueError(f"mixed task/runtime fingerprints for {task_id}")
        task_fingerprints[task_id] = next(iter(task_values))
        runtime_fingerprints[task_id] = next(iter(runtime_values))
    resolver_fingerprints = {str(item["resolver_fingerprint"]) for item in shards}
    if len(resolver_fingerprints) != 1:
        raise ValueError("mixed resolver fingerprints across sweep shards")
    resolver_fingerprint = next(iter(resolver_fingerprints))
    shard_fingerprints = {
        f"{item['task_id']}|{item['strategy_fingerprint']}": fingerprint(item)
        for item in shards
    }

    summaries: list[dict[str, Any]] = []
    for sfp in sorted(strategy_fps):
        cells = [item for item in shards if item["strategy_fingerprint"] == sfp]
        failures: list[dict[str, Any]] = []
        total_tokens = irrelevant_tokens = 0
        timings: list[float] = []
        for cell in cells:
            result = cell["result"]
            row = gold_rows[str(cell["task_id"])]
            cell_failures = _gate(result, row)
            if not cell.get("deterministic") or cell.get("repeat_fingerprint") != result.get("fingerprint"):
                cell_failures.append("nondeterministic")
            if cell_failures:
                failures.append({"task_id": cell["task_id"], "failures": sorted(set(cell_failures))})
            total_tokens += int(result.get("token_proxy", 0))
            relevant = set(map(str, row.get("relevant_refs", [])))
            distractors = set(map(str, row.get("distractor_refs", [])))
            for item in result.get("evidence", []):
                ref = str(item.get("ref"))
                entry_ref = str(item.get("entry_id") or ref)
                covers_relevant = ref in relevant or entry_ref in relevant or any(value.startswith(entry_ref + ":") for value in relevant)
                covers_distractor = ref in distractors or entry_ref in distractors or any(value.startswith(entry_ref + ":") for value in distractors)
                if covers_distractor or (relevant and not covers_relevant):
                    irrelevant_tokens += int(item.get("token_proxy", 0))
            timings.extend(float(value) for value in cell.get("timings_ms", []))
        family = cells[0]["strategy"].get("family")
        summaries.append({
            "strategy_fingerprint": sfp,
            "strategy": cells[0]["strategy"],
            "eligible": not failures,
            "selection_eligible": not failures and family != "oracle",
            "selection_exclusion": "oracle-lower-bound-only" if family == "oracle" else None,
            "failures": failures,
            "irrelevant_token_proxy": irrelevant_tokens,
            "total_token_proxy": total_tokens,
            "p95_latency_ms": _p95(timings),
        })
    eligible = [item for item in summaries if item["selection_eligible"]]
    frontier = [item for item in eligible if not any(_dominates(other, item) for other in eligible if other is not item)]
    frontier.sort(key=lambda item: (
        item["irrelevant_token_proxy"], item["total_token_proxy"],
        item["p95_latency_ms"], item["strategy_fingerprint"],
    ))
    selected = frontier[0] if frontier else None
    reduction: dict[str, Any] = {
        "schema": REDUCTION_SCHEMA,
        "task_count": len(gold_rows),
        "strategy_count": len(strategy_fps),
        "complete": True,
        "task_fingerprints": dict(sorted(task_fingerprints.items())),
        "runtime_fingerprints": dict(sorted(runtime_fingerprints.items())),
        "resolver_fingerprint": resolver_fingerprint,
        "shard_fingerprints": dict(sorted(shard_fingerprints.items())),
        "strategies": summaries,
        "pareto_frontier": [item["strategy_fingerprint"] for item in frontier],
        "selected_strategy_fingerprint": selected["strategy_fingerprint"] if selected else None,
    }
    reduction["fingerprint"] = reduction_payload_fingerprint(reduction)
    if candidate_path is not None:
        if selected is None:
            raise ValueError("no eligible strategy to freeze")
        manifest = {
            "schema": CANDIDATE_SCHEMA,
            "strategy": selected["strategy"],
            "strategy_fingerprint": selected["strategy_fingerprint"],
            "reduction_fingerprint": reduction["fingerprint"],
            "selection_rule": [
                "irrelevant_token_proxy", "total_token_proxy", "p95_latency_ms",
                "strategy_fingerprint",
            ],
        }
        target = Path(candidate_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(manifest) + "\n")
        reduction["candidate_manifest"] = str(target)
    return reduction


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shards", required=True)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--strategies", required=True)
    parser.add_argument("--freeze-candidate")
    parser.add_argument("--output")
    parser.add_argument("--owner-approved", action="store_true")
    args = parser.parse_args(argv)
    if not args.owner_approved or not execution_approved(HERE):
        parser.error("owner-approved PREREGISTRATION.md and tasks/gold.json are required for reduction")
    from strategies import strategy_fingerprint

    value = load_json(args.strategies)
    rows = value.get("strategies", value) if isinstance(value, Mapping) else value
    expected = [
        str(row["strategy_fingerprint"])
        if row.get("strategy_fingerprint")
        else strategy_fingerprint(row)
        for row in rows
    ]
    result = reduce_shards(
        args.shards, load_json(args.gold),
        expected_strategy_fingerprints=expected,
        candidate_path=args.freeze_candidate,
    )
    rendered = canonical_json(result) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
