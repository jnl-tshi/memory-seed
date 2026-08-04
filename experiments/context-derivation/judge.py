"""Freeze and optionally execute the 96 secondary cross-family reviews."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from contracts import ARMS, AGENTS, SCHEDULE_SEED, TASK_COUNT, live_execution_approved

HERE = Path(__file__).resolve().parent
SELECTION_PATH = HERE / "JUDGE_SELECTION.json"


JUDGE_SCHEMA = {
    "type": "object",
    "required": ["schema", "explanation_supported", "explanation_complete", "unsupported_claims", "notes"],
    "properties": {
        "schema": {"const": "context-judge.v1"},
        "explanation_supported": {"type": "boolean"},
        "explanation_complete": {"type": "boolean"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}


def require_execution_approval(*, owner_approved: bool, experiment_root: Path | None = None) -> None:
    """Fail closed before any paid blind-judge subprocess is started."""
    if not owner_approved:
        raise SystemExit("refusing paid judge calls without --owner-approved")
    root = experiment_root or Path(__file__).resolve().parent
    if not live_execution_approved(root):
        raise SystemExit("gold/preregistration approval, a frozen candidate, and pinned live matrix are required")


def selected_repetition(task_id: str, arm: str, agent: str) -> int:
    payload = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    for cell in payload.get("cells", []):
        if (cell.get("task_id"), cell.get("arm"), cell.get("subject_agent")) == (task_id, arm, agent):
            repetition = int(cell["repetition"])
            expected = random.Random(f"{SCHEDULE_SEED}:{task_id}:{arm}:{agent}").choice((1, 2, 3))
            if repetition != expected:
                raise ValueError("frozen judge selection does not match the committed seed")
            return repetition
    raise ValueError(f"missing frozen judge selection for {(task_id, arm, agent)}")


def select_reviews(summary: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    selected = []
    for run in summary.get("runs", ()):
        if int(run.get("repetition", 0)) == selected_repetition(str(run.get("task_id")), str(run.get("arm")), str(run.get("agent"))):
            selected.append(run)
    selected.sort(key=lambda row: (str(row.get("task_id")), str(row.get("arm")), str(row.get("agent"))))
    return selected


def expected_review_cells(tasks_payload: Mapping[str, Any]) -> set[tuple[str, str, str, int]]:
    task_ids = [str(item["task_id"]) for item in tasks_payload.get("tasks", ())]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("judge tasks must have unique task IDs")
    expected_task_ids = {f"CTX-{number:02d}" for number in range(1, TASK_COUNT + 1)}
    if set(task_ids) != expected_task_ids:
        raise ValueError("judge tasks must be the exact frozen CTX-01..CTX-12 set")
    return {
        (task_id, arm, subject, selected_repetition(task_id, arm, subject))
        for task_id in task_ids
        for arm in ARMS
        for subject in AGENTS
    }


def validate_review_cells(selected: list[Mapping[str, Any]], expected: set[tuple[str, str, str, int]]) -> None:
    """Count equality is insufficient: duplicates can hide omitted blind cells."""
    cells = [
        (str(run.get("task_id")), str(run.get("arm")), str(run.get("agent")), int(run.get("repetition", 0)))
        for run in selected
    ]
    run_ids = [run.get("run_id") for run in selected]
    if any(not isinstance(run_id, str) or not run_id for run_id in run_ids):
        raise ValueError("selected reviews must have non-empty run_id values")
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("selected reviews contain duplicate run_id values")
    actual = set(cells)
    if len(cells) != len(actual) or actual != expected:
        raise ValueError(
            "selected review cells mismatch: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}, "
            f"duplicates={len(cells) - len(actual)}"
        )


def build_packets(summary: Mapping[str, Any], tasks_payload: Mapping[str, Any], output: Path) -> list[dict[str, Any]]:
    tasks = {str(item["task_id"]): item for item in tasks_payload.get("tasks", ())}
    selected = select_reviews(summary)
    validate_review_cells(selected, expected_review_cells(tasks_payload))
    output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for run in selected:
        task = tasks[str(run["task_id"])]
        subject = str(run["agent"])
        judge = "codex" if subject == "claude" else "claude"
        packet = {
            "task_id": run["task_id"],
            "arm": run["arm"],
            "subject_agent": subject,
            "judge_agent": judge,
            "question": task["question"],
            "answer": run.get("answer"),
            "included_refs": run.get("included_refs", []),
            "tool_calls": run.get("tool_calls", []),
            "evidence_excerpt": run.get("evidence_excerpt", ""),
        }
        raw = json.dumps(packet, indent=2, ensure_ascii=False) + "\n"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        path = output / f"{run['task_id']}-{run['arm']}-{subject}-{digest}.json"
        path.write_text(raw, encoding="utf-8")
        manifest.append({
            "packet": str(path),
            "task_id": str(run["task_id"]),
            "arm": str(run["arm"]),
            "repetition": int(run["repetition"]),
            "judge": judge,
            "subject": subject,
            "run_id": str(run["run_id"]),
        })
    return manifest


def _extract_json(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema") == "context-judge.v1":
            return value
    raise ValueError("judge output did not contain context-judge.v1 JSON")


def execute_review(packet: Path, judge: str, output: Path) -> None:
    prompt = (
        "Review the answer in the JSON packet below. Judge only whether its prose explanation is "
        "supported and complete relative to the included refs and observable tool evidence. Identity, "
        "edge and citation correctness are scored mechanically elsewhere. Return only context-judge.v1 JSON.\n\n"
        + packet.read_text(encoding="utf-8")
        + "\nSchema:\n"
        + json.dumps(JUDGE_SCHEMA)
    )
    if judge == "codex":
        executable = shutil.which("codex") or shutil.which("codex.cmd")
        command = [executable, "exec", "--json", "--dangerously-bypass-approvals-and-sandbox", "-c", "features.apps=false", "-"] if executable else []
    else:
        executable = shutil.which("claude") or shutil.which("claude.cmd")
        command = [executable, "-p", "--output-format", "json", "--dangerously-skip-permissions"] if executable else []
    if not command:
        raise RuntimeError(f"{judge} CLI is unavailable")
    completed = subprocess.run(command, input=prompt, text=True, encoding="utf-8", capture_output=True, timeout=600, cwd=packet.parent)
    if completed.returncode:
        raise RuntimeError(f"{judge} judge failed: {completed.stderr[-1000:]}")
    result = _extract_json(completed.stdout)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def execute_manifest(manifest: list[Mapping[str, Any]], output: Path, *, jobs_per_agent: int = 3) -> None:
    """Run two isolated judge queues, each bounded to three concurrent calls."""
    if jobs_per_agent < 1 or jobs_per_agent > 3:
        raise ValueError("judge concurrency must be between one and three per agent")

    def run_queue(judge: str, items: list[Mapping[str, Any]]) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs_per_agent) as pool:
            futures = []
            for item in items:
                packet = Path(str(item["packet"]))
                destination = output / f"{packet.stem}.judgement.json"
                futures.append(pool.submit(execute_review, packet, judge, destination))
            for future in futures:
                future.result()

    grouped = {agent: [item for item in manifest if item["judge"] == agent] for agent in AGENTS}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(AGENTS)) as pool:
        futures = [pool.submit(run_queue, agent, grouped[agent]) for agent in AGENTS]
        for future in futures:
            future.result()


def collect_results(
    manifest: list[Mapping[str, Any]], output: Path, *, expected_cells: set[tuple[str, str, str, int]]
) -> list[dict[str, Any]]:
    """Verify returned files retain the exact pre-selected blind-cell identity."""
    manifest_cells = {
        (str(item.get("task_id")), str(item.get("arm")), str(item.get("subject")), int(item.get("repetition", 0)))
        for item in manifest
    }
    run_ids = [item.get("run_id") for item in manifest]
    if len(manifest) != len(manifest_cells) or manifest_cells != expected_cells:
        raise ValueError("judge manifest does not contain the exact frozen review cells")
    if any(not isinstance(run_id, str) or not run_id for run_id in run_ids) or len(run_ids) != len(set(run_ids)):
        raise ValueError("judge manifest has missing or duplicate run_id values")
    rows = []
    for item in manifest:
        packet = Path(str(item["packet"]))
        path = output / f"{packet.stem}.judgement.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != "context-judge.v1":
            raise ValueError(f"invalid judge result: {path}")
        rows.append({
            **value,
            "run_id": str(item["run_id"]),
            "task_id": str(item["task_id"]),
            "arm": str(item["arm"]),
            "repetition": int(item["repetition"]),
            "judge": str(item["judge"]),
            "subject": str(item["subject"]),
        })
    result_cells = {(row["task_id"], row["arm"], row["subject"], row["repetition"]) for row in rows}
    if len(rows) != len(result_cells) or result_cells != expected_cells:
        raise ValueError("returned judgements do not cover the exact frozen review cells")
    (output / "results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--owner-approved", action="store_true")
    parser.add_argument("--jobs-per-agent", type=int, default=3)
    args = parser.parse_args()
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    output = Path(args.output_dir)
    manifest = build_packets(summary, tasks, output / "packets")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if args.execute:
        require_execution_approval(owner_approved=args.owner_approved)
        execute_manifest(manifest, output, jobs_per_agent=args.jobs_per_agent)
        collect_results(manifest, output, expected_cells=expected_review_cells(tasks))
    print(f"prepared {len(manifest)} cross-family review packets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
