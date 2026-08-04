"""Materialize a strategy result into an offline, self-contained packet."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

from contracts import canonical_json, fingerprint, load_json
from reduce import REDUCTION_SCHEMA, reduction_payload_fingerprint
from strategies import RESULT_SCHEMA, normalize_strategy, strategy_fingerprint
from sweep import (
    SHARD_SCHEMA,
    resolver_implementation_fingerprint,
    runtime_fingerprint,
    task_runtime,
)


PACKET_SCHEMA = "context-packet.v1"
LIVE_TASKS_SCHEMA = "context-live-tasks.v1"


def materialize_packet(result: Mapping[str, Any], *, include_text: bool = True) -> dict[str, Any]:
    if result.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"result schema must be {RESULT_SCHEMA!r}")
    items = []
    for evidence in result.get("evidence", []):
        item = {key: value for key, value in evidence.items() if key != "text"}
        if include_text:
            item["text"] = evidence.get("text", "")
        items.append(item)
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "task_id": result.get("task_id"),
        "strategy_fingerprint": result.get("strategy_fingerprint"),
        "selected_adrs": result.get("selected_adrs", []),
        "selected_refs": result.get("selected_refs", []),
        "typed_edges": result.get("typed_edges", []),
        "lineage_edges": result.get("lineage_edges", []),
        "related_edges": result.get("related_edges", []),
        "evidence": items,
        "omissions": result.get("omissions", []),
        "absence": result.get("absence", []),
        "insufficient_evidence": bool(result.get("insufficient_evidence")),
        "token_proxy": int(result.get("token_proxy", 0)),
    }
    packet["fingerprint"] = fingerprint(packet)
    return packet


def packet_json(result: Mapping[str, Any], *, include_text: bool = True) -> str:
    return canonical_json(materialize_packet(result, include_text=include_text))


def attach_task_packets(
    task: Mapping[str, Any],
    *,
    retrieval_v1_result: Mapping[str, Any],
    candidate_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach both inline packet arms and their accounting to a task payload."""
    arms = {
        "retrieval-v1-packet": retrieval_v1_result,
        "adr-candidate-packet": candidate_result,
    }
    payload = dict(task)
    rendered = {arm: packet_json(result) for arm, result in arms.items()}
    payload["packets"] = rendered
    payload["included_refs_by_arm"] = {
        arm: sorted(
            set(map(str, result.get("selected_refs", [])))
            | {str(item["adr_id"]) for item in result.get("selected_adrs", []) if item.get("adr_id")}
        )
        for arm, result in arms.items()
    }
    payload["context_token_proxy_by_arm"] = {
        arm: max(1, (len(packet.encode("utf-8")) + 3) // 4)
        for arm, packet in rendered.items()
    }
    return payload


def assemble_live_tasks(
    tasks_payload: Mapping[str, Any],
    shard_dir: str | Path,
    candidate_manifest: Mapping[str, Any],
    reduction: Mapping[str, Any],
    retrieval_strategy_fingerprint: str,
    *,
    fixture_base: str | Path,
) -> dict[str, Any]:
    """Assemble every fixed-arm packet from the frozen offline shards."""
    candidate_fingerprint = str(candidate_manifest.get("strategy_fingerprint", ""))
    if candidate_manifest.get("schema") != "context-candidate-manifest.v1" or not candidate_fingerprint:
        raise ValueError("a frozen context-candidate-manifest.v1 is required")
    if (candidate_manifest.get("strategy") or {}).get("family") not in {"adr-structural", "adr-hybrid"}:
        raise ValueError("frozen candidate must be ADR-aware")
    if reduction.get("schema") != REDUCTION_SCHEMA:
        raise ValueError("a context-reduction.v1 artifact is required")
    if reduction.get("complete") is not True:
        raise ValueError("reduction artifact must be complete")
    computed_reduction_fingerprint = reduction_payload_fingerprint(reduction)
    if reduction.get("fingerprint") != computed_reduction_fingerprint:
        raise ValueError("reduction artifact fingerprint is invalid")
    if candidate_manifest.get("reduction_fingerprint") != computed_reduction_fingerprint:
        raise ValueError("candidate is not bound to the supplied reduction")
    if reduction.get("selected_strategy_fingerprint") != candidate_fingerprint:
        raise ValueError("candidate does not match the reduction selection")
    selected_rows = [
        row for row in reduction.get("strategies", ())
        if row.get("strategy_fingerprint") == candidate_fingerprint
    ]
    if len(selected_rows) != 1:
        raise ValueError("reduction must contain exactly one selected strategy row")
    selected_row = selected_rows[0]
    if (
        not selected_row.get("eligible")
        or not selected_row.get("selection_eligible")
        or (selected_row.get("strategy") or {}).get("family") == "oracle"
    ):
        raise ValueError("reduction selected row is not an eligible non-oracle strategy")
    candidate_strategy = normalize_strategy(candidate_manifest.get("strategy") or {})
    if (
        strategy_fingerprint(candidate_strategy) != candidate_fingerprint
        or normalize_strategy(selected_row.get("strategy") or {}) != candidate_strategy
    ):
        raise ValueError("candidate strategy does not match the selected reduction row")
    tasks = list(tasks_payload.get("tasks", ()))
    task_ids = {str(task["task_id"]) for task in tasks}
    if (
        reduction.get("task_count") != len(tasks)
        or set(map(str, (reduction.get("task_fingerprints") or {}).keys())) != task_ids
        or set(map(str, (reduction.get("runtime_fingerprints") or {}).keys())) != task_ids
    ):
        raise ValueError("reduction task provenance does not match current tasks")
    shard_root = Path(shard_dir)

    def selected_shard(task_id: str, strategy_fp: str) -> Mapping[str, Any] | None:
        if not strategy_fp.startswith("sha256:"):
            raise ValueError(f"invalid selected strategy fingerprint: {strategy_fp!r}")
        path = shard_root / f"{task_id}--{strategy_fp.split(':', 1)[1]}.json"
        if not path.is_file():
            return None
        shard = load_json(path)
        if shard.get("schema") != SHARD_SCHEMA:
            raise ValueError(f"invalid materialization shard schema: {path}")
        if (
            str(shard.get("task_id")) != task_id
            or str(shard.get("strategy_fingerprint")) != strategy_fp
        ):
            raise ValueError(f"materialization shard identity mismatch: {path}")
        return shard

    output = []
    current_resolver_fingerprint = resolver_implementation_fingerprint()
    for task in tasks:
        task_id = str(task["task_id"])
        current_runtime_fingerprint = runtime_fingerprint(
            task_runtime(task, fixture_base), task
        )
        retrieval = selected_shard(task_id, retrieval_strategy_fingerprint)
        candidate = selected_shard(task_id, candidate_fingerprint)
        if not retrieval or not candidate:
            raise ValueError(f"missing materialization shard for {task_id}")
        for label, shard in (("retrieval", retrieval), ("candidate", candidate)):
            shard_key = f"{task_id}|{shard.get('strategy_fingerprint')}"
            if (reduction.get("shard_fingerprints") or {}).get(shard_key) != fingerprint(shard):
                raise ValueError(f"{label} shard is not represented by the reduction for {task_id}")
            if not shard.get("deterministic") or shard.get("repeat_fingerprint") != (shard.get("result") or {}).get("fingerprint"):
                raise ValueError(f"{label} shard is nondeterministic for {task_id}")
            if (
                shard.get("task_fingerprint") != fingerprint(task)
                or shard.get("task_fingerprint") != (reduction.get("task_fingerprints") or {}).get(task_id)
                or shard.get("runtime_fingerprint") != current_runtime_fingerprint
                or shard.get("runtime_fingerprint") != (reduction.get("runtime_fingerprints") or {}).get(task_id)
                or shard.get("resolver_fingerprint") != current_resolver_fingerprint
                or shard.get("resolver_fingerprint") != reduction.get("resolver_fingerprint")
            ):
                raise ValueError(f"{label} shard is stale for {task_id}")
            try:
                normalized = normalize_strategy(shard.get("strategy") or {})
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid {label} shard strategy for {task_id}: {exc}") from exc
            if strategy_fingerprint(normalized) != shard.get("strategy_fingerprint"):
                raise ValueError(f"tampered {label} shard strategy for {task_id}")
        if retrieval.get("runtime_fingerprint") != candidate.get("runtime_fingerprint"):
            raise ValueError(f"fixed-arm shards use different runtimes for {task_id}")
        if ((retrieval.get("strategy") or {}).get("family") != "retrieval-v1"
                or (candidate.get("strategy") or {}).get("family") not in {"adr-structural", "adr-hybrid"}):
            raise ValueError(f"wrong strategy family for {task_id}")
        if normalize_strategy(candidate.get("strategy") or {}) != candidate_strategy:
            raise ValueError(f"candidate shard does not match frozen candidate for {task_id}")
        output.append(attach_task_packets(
            task,
            retrieval_v1_result=retrieval["result"],
            candidate_result=candidate["result"],
        ))
    payload = {
        "schema": LIVE_TASKS_SCHEMA,
        "candidate_fingerprint": candidate_fingerprint,
        "retrieval_strategy_fingerprint": retrieval_strategy_fingerprint,
        "tasks": output,
    }
    payload["fingerprint"] = fingerprint(payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Attach fixed offline packet arms to one task or freeze all live tasks")
    parser.add_argument("--task")
    parser.add_argument("--retrieval-result")
    parser.add_argument("--candidate-result")
    parser.add_argument("--tasks")
    parser.add_argument("--shards")
    parser.add_argument("--fixture-base")
    parser.add_argument("--candidate-manifest")
    parser.add_argument("--reduction")
    parser.add_argument("--retrieval-fingerprint")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    if args.tasks:
        required = (
            args.shards, args.fixture_base, args.candidate_manifest,
            args.reduction, args.retrieval_fingerprint, args.output,
        )
        if not all(required):
            parser.error("assembly requires --tasks, --shards, --fixture-base, --candidate-manifest, --reduction, --retrieval-fingerprint, and --output")
        payload = assemble_live_tasks(
            load_json(args.tasks), args.shards, load_json(args.candidate_manifest),
            load_json(args.reduction), args.retrieval_fingerprint,
            fixture_base=args.fixture_base,
        )
    else:
        if not all((args.task, args.retrieval_result, args.candidate_result)):
            parser.error("single-task mode requires --task, --retrieval-result, and --candidate-result")
        payload = attach_task_packets(
            load_json(args.task),
            retrieval_v1_result=load_json(args.retrieval_result),
            candidate_result=load_json(args.candidate_result),
        )
    rendered = canonical_json(payload) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "x" if args.tasks else "w"
        with target.open(mode, encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
