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

from contracts import ARMS, AGENTS, SCHEDULE_SEED, live_execution_approved

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


def build_packets(summary: Mapping[str, Any], tasks_payload: Mapping[str, Any], output: Path) -> list[dict[str, Any]]:
    tasks = {str(item["task_id"]): item for item in tasks_payload.get("tasks", ())}
    selected = select_reviews(summary)
    if len(selected) != len(tasks) * len(ARMS) * len(AGENTS):
        raise ValueError(f"expected {len(tasks) * len(ARMS) * len(AGENTS)} selected reviews, found {len(selected)}")
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
        manifest.append({"packet": str(path), "judge": judge, "subject": subject, "run_id": run.get("run_id")})
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


def collect_results(manifest: list[Mapping[str, Any]], output: Path) -> list[dict[str, Any]]:
    rows = []
    for item in manifest:
        packet = Path(str(item["packet"]))
        path = output / f"{packet.stem}.judgement.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != "context-judge.v1":
            raise ValueError(f"invalid judge result: {path}")
        rows.append({**value, "run_id": item["run_id"], "judge": item["judge"], "subject": item["subject"]})
    if len(rows) != 96:
        raise ValueError(f"expected 96 blind judgements, found {len(rows)}")
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
        collect_results(manifest, output)
    print(f"prepared {len(manifest)} cross-family review packets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
