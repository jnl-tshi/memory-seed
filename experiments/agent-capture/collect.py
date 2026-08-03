"""Collect agent-capture results: tabulate what each run recorded, emit blind judge packets.

For every run under runs/: parse the run's own `.memory-seed/sessions/` store (the readout),
count entries and decision sections, compare against the seeded-decision answer key in
tasks/tasks.json, and write:

  runs/<id>/judge_packet.md   - task brief + transcript summary + recorded entries, NO answer key
  runs/summary.json           - per-run counts plus the answer-key comparison (never in packets)

Judges see packets only. The answer key stays out of every packet by construction - the packet
builder has no access to the expected-decisions list, mirroring the topic-swarm harness rule that
blind payloads and the answer key never travel together.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from memory_seed.core import _ENTRY_HEADING_RE, iter_session_documents  # noqa: E402

RUNS = HERE / "runs"
TASKS = HERE / "tasks"

_DECISION_SECTION_RE = re.compile(r"^###\s+Decisions?\s*$", re.MULTILINE)
_DECISION_ORDINAL_RE = re.compile(r"^####\s+D\d+\s*-", re.MULTILINE)


def split_entries(text: str) -> list[str]:
    """Split a session document into entry bodies using the canonical heading regex."""
    headings = list(_ENTRY_HEADING_RE.finditer(text))
    entries = []
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        entries.append(text[match.start() : end])
    return entries


def _guard_signals(run_dir: Path) -> dict:
    """Did the worktree guard tell this session not to write, and did it write anyway?

    `memory_worktree_guard` classifies every fixture as `root-checkout` and blocks write intent
    without `allow_root_write` (core.py:1580-1585). That is stock behaviour, so the fixtures keep
    it - but it means a session can fail to record because it was *told not to*, which is a
    different finding from an agent that never thought to record. Only levels carrying the rules
    contract prompt an agent to consult the guard at all, so left unmeasured this could masquerade
    as scaffolding suppressing capture. Cheap textual detection over whichever transcript exists.
    """
    text = ""
    for name in ("transcript.json", "transcript.jsonl"):
        path = run_dir / name
        if path.exists():
            text = path.read_text(encoding="utf-8")
            break
    return {
        "guard_called": "worktree_guard" in text,
        "guard_blocked": '"safe_to_write": false' in text.replace("\\", ""),
    }


def _harness_failure(run_dir: Path, manifest: dict) -> str | None:
    """Why this run is not evidence about capture behaviour, or None if it is.

    A rate-limited, timed-out or crashed session records nothing - and an empty store is exactly
    what "the agent did not capture" also looks like. Scoring the two the same way would turn every
    harness problem into a false negative, biasing capture rate DOWN in whichever arm happened to
    hit the limits. These are separated out and counted, never silently dropped.
    """
    if manifest.get("timed_out"):
        return "timed_out"
    if manifest.get("exit_code") not in (0, None):
        return f"exit_code={manifest.get('exit_code')}"
    transcript = run_dir / "transcript.json"
    if transcript.exists():
        try:
            payload = json.loads(transcript.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "unparseable_transcript"
        if isinstance(payload, dict):
            if payload.get("is_error"):
                return f"session_error:{payload.get('subtype') or payload.get('stop_reason')}"
            if payload.get("stop_reason") not in (None, "end_turn", "stop_sequence", "tool_use"):
                return f"stop_reason={payload.get('stop_reason')}"
    return None


def analyse_run(run_dir: Path) -> dict:
    manifest_path = run_dir / "RUN_MANIFEST.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    )
    sessions_dir = run_dir / ".memory-seed" / "sessions"

    entries: list[dict] = []
    for document in iter_session_documents(sessions_dir):
        text = document.path.read_text(encoding="utf-8")
        for body in split_entries(text):
            ordinal_count = len(_DECISION_ORDINAL_RE.findall(body))
            has_decision_section = bool(_DECISION_SECTION_RE.search(body))
            decision_count = ordinal_count if ordinal_count else (1 if has_decision_section else 0)
            entries.append(
                {
                    "source": str(document.path.relative_to(run_dir)),
                    "heading": body.splitlines()[0].strip(),
                    "has_decision_section": has_decision_section,
                    "decision_count": decision_count,
                    "has_reason": "- R:" in body,
                    "body": body,
                }
            )

    return {
        "run_id": run_dir.name,
        "level": manifest.get("level"),
        "task": manifest.get("task"),
        "agent": manifest.get("agent"),
        "exit_code": manifest.get("exit_code"),
        "brief_override": bool(manifest.get("brief_override")),
        "harness_failure": _harness_failure(run_dir, manifest),
        **_guard_signals(run_dir),
        "entry_count": len(entries),
        "decision_entry_count": sum(1 for e in entries if e["decision_count"]),
        "decision_count": sum(e["decision_count"] for e in entries),
        "entries": entries,
    }


def write_judge_packet(run_dir: Path, analysis: dict) -> None:
    """Blind packet: brief + transcript + recorded entries. No answer key, no level label."""
    task_id = analysis.get("task")
    brief_text = ""
    if task_id:
        manifest = json.loads((TASKS / "tasks.json").read_text(encoding="utf-8"))
        for task in manifest["tasks"]:
            if task["id"] == task_id:
                brief_text = (TASKS / task["brief"]).read_text(encoding="utf-8")
                break

    # Claude writes transcript.json (one object); Codex `--json` writes transcript.jsonl.
    # Resolve by existence rather than by agent so a packet is never silently transcript-less.
    transcript, fence = "", "json"
    for name in ("transcript.json", "transcript.jsonl"):
        path = run_dir / name
        if path.exists():
            transcript = path.read_text(encoding="utf-8")
            fence = "jsonl" if name.endswith(".jsonl") else "json"
            break

    recorded = "\n\n---\n\n".join(entry["body"] for entry in analysis["entries"]) or "(nothing recorded)"

    packet = (
        "# Judge packet\n\n"
        "You are judging whether the work session recorded its durable decisions.\n"
        "Answer, with quotes as evidence: (1) What durable decisions does the TRANSCRIPT show were\n"
        "made? (2) For each, was it recorded in the session store, and does the recorded reason\n"
        "faithfully match the transcript's actual reasoning? (3) Do any recorded entries describe\n"
        "no real decision (noise)?\n\n"
        "## Task brief\n\n" + brief_text + "\n\n"
        "## Recorded session entries\n\n" + recorded + "\n\n"
        "## Transcript\n\n```" + fence + "\n" + transcript + "\n```\n"
    )
    (run_dir / "judge_packet.md").write_text(packet, encoding="utf-8")


def main() -> int:
    if not RUNS.is_dir():
        raise SystemExit("no runs/ directory - nothing to collect")

    answer_key = json.loads((TASKS / "tasks.json").read_text(encoding="utf-8"))
    expected_by_task = {
        task["id"]: {
            "required": sum(1 for d in task["seeded_decisions"] if not d.get("optional")),
            "optional": sum(1 for d in task["seeded_decisions"] if d.get("optional")),
        }
        for task in answer_key["tasks"]
    }

    summary = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []
    in_flight: list[str] = []
    for run_dir in sorted(path for path in RUNS.iterdir() if path.is_dir()):
        # run.py writes RUN_MANIFEST.json last, so its absence means the session is still going.
        # Without this guard a collect() during a batch scores in-flight runs as empty stores.
        if not (run_dir / "RUN_MANIFEST.json").exists():
            in_flight.append(run_dir.name)
            continue
        analysis = analyse_run(run_dir)
        # Instrument probes ran a substituted brief, so their store is not evidence about
        # capture behaviour. Excluded here rather than filtered later, so they can never be
        # pooled into a capture-rate table by accident.
        if analysis.get("brief_override"):
            skipped.append(run_dir.name)
            continue
        if analysis.get("harness_failure"):
            failed.append((run_dir.name, analysis["harness_failure"]))
            continue
        write_judge_packet(run_dir, analysis)
        expected = expected_by_task.get(analysis.get("task") or "", {})
        summary.append(
            {
                **{k: analysis[k] for k in (
                    "run_id", "level", "task", "agent", "exit_code",
                    "entry_count", "decision_entry_count", "decision_count",
                    "guard_called", "guard_blocked",
                )},
                "expected_required_decisions": expected.get("required"),
                "expected_optional_decisions": expected.get("optional"),
            }
        )

    (RUNS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\n{len(summary)} run(s) collected; judge packets written per run (answer key withheld)")
    if in_flight:
        print(f"{len(in_flight)} run(s) still in flight, not collected: {', '.join(in_flight)}")
    if skipped:
        print(f"{len(skipped)} instrument probe(s) excluded: {', '.join(skipped)}")
    if failed:
        print(f"{len(failed)} harness failure(s) excluded (NOT zero-capture evidence):")
        for run_id, reason in failed:
            print(f"  {run_id}: {reason}")
        print("  Re-run these cells to restore balance before reading the matrix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
