"""Build an immutable three-arm calibration bundle from semantic task inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from memory_seed.task_packet import canonical_task_packet_json
from tests.pilot_task_packet_fixture import build_fixture_runtime, compile_fixture_packet

try:  # Package import under pytest; direct-script fallback for the CLI.
    from .contracts import (
        ANSWER_SCHEMA,
        ARMS,
        BUNDLE_SCHEMA,
        TASKS_SCHEMA,
        answer_template,
        canonical_json,
        fingerprint,
        load_json,
        require_schema,
        task_by_id,
    )
except ImportError:  # pragma: no cover - exercised by live direct-script runs
    from contracts import (
        ANSWER_SCHEMA,
        ARMS,
        BUNDLE_SCHEMA,
        TASKS_SCHEMA,
        answer_template,
        canonical_json,
        fingerprint,
        load_json,
        require_schema,
        task_by_id,
    )


def _propositions(task: Mapping[str, Any]) -> str:
    return "\n".join(f"- {row['id']}: {row['text']}" for row in task["propositions"])


def build_prompt(task: Mapping[str, Any], arm: str, packet: Mapping[str, Any]) -> str:
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    contract = answer_template(task)
    prompt = (
        "Evaluate each proposition only from evidence supplied in this run. "
        "Return one JSON object and no prose. Use verdict true, false, or insufficient. "
        "For true or false, cite only semantic evidence IDs you actually received. "
        "For insufficient, use an empty evidence_ids array. Preserve proposition order.\n\n"
        f"Required output shape:\n{canonical_json(contract)}\n\n"
        f"Task:\n{task['question']}\n\nPropositions:\n{_propositions(task)}\n"
    )
    if arm == "no_memory":
        return prompt + (
            "\nCondition: no Memory Seed evidence or retrieval tools are available. "
            "Do not rely on model memory or guess project-specific facts.\n"
        )
    if arm == "memory_tools":
        return prompt + (
            "\nCondition: no prepared packet is supplied. Use only the available read-only "
            "Memory Seed tools to locate evidence. Stop when the propositions can be decided; "
            "do not perform broad discovery. Cite only ID values returned by those tools, never "
            "a JSON field name.\n"
        )
    valid_ids = [str(row["id"]) for row in packet["materialized_evidence"]]
    return prompt + (
        "\nCondition: the compiled Task Packet below is the complete initial context. "
        "Materialized evidence is already supplied and must not be fetched again. Use the "
        "read-only Memory Seed tools only for a specific unresolved gap. The valid initial "
        f"evidence IDs are exactly {canonical_json(valid_ids)}. JSON field names such as "
        "execution_defaults are not evidence IDs.\n\n"
        "Compiled Task Packet:\n" + canonical_task_packet_json(packet) + "\n"
    )


def prepare_bundle(tasks_path: Path, task_id: str, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite bundle directory: {output}")
    tasks = load_json(tasks_path)
    require_schema(tasks, TASKS_SCHEMA)
    task = task_by_id(tasks, task_id)
    if task.get("fixture") != "task_packet_pilot":
        raise ValueError("the M0 harness currently supports fixture=task_packet_pilot only")

    output.mkdir(parents=True)
    runtime = build_fixture_runtime(output / "runtime")
    packet = compile_fixture_packet(runtime)
    packet_text = canonical_task_packet_json(packet)
    (output / "task-packet.json").write_text(packet_text + "\n", encoding="utf-8")
    prompts: dict[str, dict[str, Any]] = {}
    prompt_dir = output / "prompts"
    prompt_dir.mkdir()
    for arm in ARMS:
        text = build_prompt(task, arm, packet)
        path = prompt_dir / f"{arm}.txt"
        path.write_text(text, encoding="utf-8")
        prompts[arm] = {
            "path": path.relative_to(output).as_posix(),
            "fingerprint": fingerprint(text),
            "characters": len(text),
        }

    stable = {
        "schema": BUNDLE_SCHEMA,
        "version": 1,
        "task_id": task_id,
        "task_split": task["split"],
        "profile": task["profile"],
        "source_tasks_fingerprint": fingerprint(tasks),
        "packet_fingerprint": packet["fingerprint"],
        "runtime_revision": packet["evidence_pack"]["corpus_revision"],
        "arms": prompts,
        "answer_schema": ANSWER_SCHEMA,
    }
    manifest = {**stable, "bundle_fingerprint": fingerprint(stable)}
    (output / "bundle.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True, type=Path)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    manifest = prepare_bundle(args.tasks, args.task_id, args.output.resolve())
    print(canonical_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
