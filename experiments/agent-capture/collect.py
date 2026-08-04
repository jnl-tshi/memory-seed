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


def _iter_events(run_dir: Path) -> list[dict]:
    """Parse a v2 transcript (JSONL). Returns [] for a v1 transcript or a missing file."""
    path = run_dir / "transcript.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _blocks(event: dict) -> list[dict]:
    content = (event.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def distil_transcript(run_dir: Path, tool_result_chars: int = 700) -> str:
    """Render the session as readable narration + tool calls, for the judge to check reasons against.

    The raw stream is mostly bookkeeping and some tool results run to tens of thousands of
    characters, so results are truncated while assistant text - the thing a stated reason has to be
    checked against - is kept whole. Codex transcripts use `mcp_tool_call` items instead and are
    handled by the same walk.
    """
    lines: list[str] = []
    for event in _iter_events(run_dir):
        kind = event.get("type")
        if kind in ("assistant", "user"):
            for block in _blocks(event):
                btype = block.get("type")
                if btype == "text" and block.get("text", "").strip():
                    lines.append(f"[agent] {block['text'].strip()}")
                elif btype == "tool_use":
                    args = json.dumps(block.get("input", {}))[:400]
                    lines.append(f"[tool call] {block.get('name')} {args}")
                elif btype == "tool_result":
                    parts = block.get("content")
                    text = ""
                    if isinstance(parts, list):
                        text = " ".join(
                            p.get("text", p.get("tool_name", "")) for p in parts if isinstance(p, dict)
                        )
                    elif isinstance(parts, str):
                        text = parts
                    text = text.strip().replace("\n", " ")
                    if text:
                        clipped = text[:tool_result_chars]
                        suffix = " ...[truncated]" if len(text) > tool_result_chars else ""
                        lines.append(f"[tool result] {clipped}{suffix}")
        elif kind == "item.completed":  # codex
            item = event.get("item") or {}
            if item.get("type") == "mcp_tool_call":
                lines.append(f"[tool call] {item.get('server')}.{item.get('tool')}")
            elif item.get("type") == "agent_message":
                lines.append(f"[agent] {(item.get('text') or '').strip()}")
    return "\n\n".join(lines)


def _guard_signals(run_dir: Path) -> dict:
    """Did the worktree guard tell this session not to write, and did it write anyway?

    `memory_worktree_guard` classifies every fixture as `root-checkout` and blocks write intent
    without `allow_root_write` (core.py:1580-1585). That is stock behaviour, so the fixtures keep
    it - but it means a session can fail to record because it was *told not to*, which is a
    different finding from an agent that never thought to record. Only levels carrying the rules
    contract prompt an agent to consult the guard at all, so left unmeasured this could masquerade
    as scaffolding suppressing capture. Cheap textual detection over whichever transcript exists.
    """
    events = _iter_events(run_dir)
    called = blocked = False
    for event in events:
        for block in _blocks(event):
            if block.get("type") == "tool_use" and "worktree_guard" in (block.get("name") or ""):
                called = True
            if block.get("type") == "tool_result":
                parts = block.get("content")
                text = (
                    " ".join(p.get("text", "") for p in parts if isinstance(p, dict))
                    if isinstance(parts, list)
                    else (parts or "")
                )
                if '"safe_to_write": false' in text or '"safe_to_write":false' in text:
                    blocked = True
    return {
        "guard_called": called,
        "guard_blocked": blocked,
        # v1 transcripts (--output-format json) carry only the final message, so no tool call
        # leaves a trace and both flags read false regardless of what happened. Reliable only
        # where an actual event stream exists.
        "guard_signal_reliable": bool(events),
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
    events = _iter_events(run_dir)
    if events:
        final = next((e for e in reversed(events) if e.get("type") == "result"), None)
        if final is None:
            return "no_result_event"
        if final.get("is_error"):
            return f"session_error:{final.get('subtype') or final.get('stop_reason')}"
        return None
    legacy = run_dir / "transcript.json"
    if legacy.exists():
        try:
            payload = json.loads(legacy.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "unparseable_transcript"
        if isinstance(payload, dict) and payload.get("is_error"):
            return f"session_error:{payload.get('subtype') or payload.get('stop_reason')}"
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

    # Prefer the distilled event stream: narration and tool calls are what a stated reason has to
    # be checked against. Fall back to the v1 single-object transcript (final message only), so an
    # archived run still produces a packet rather than a silently empty one.
    transcript, fence = distil_transcript(run_dir), "text"
    if not transcript:
        legacy = run_dir / "transcript.json"
        transcript = legacy.read_text(encoding="utf-8") if legacy.exists() else ""
        fence = "json"

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


def print_dose_response(summary: list[dict]) -> None:
    """The pre-registered shape: recorded-anything rate per level, broken out by task.

    Deliberately NOT the capture rate from the thresholds - that one is judged (does the recorded
    reason match what actually happened?) and cannot be computed from counts. This is the mechanical
    precursor: did the session write a decision-bearing entry at all. Reading it as the capture rate
    would overstate every arm, since an entry that records the wrong decision still counts here.
    """
    levels = sorted({row["level"] for row in summary if row.get("level")})
    tasks = sorted({row["task"] for row in summary if row.get("task")})
    if not levels:
        return

    width = max(len(t) for t in tasks) if tasks else 4
    print("\nRecorded ANY entry, by level x task (mechanical, NOT the judged capture rate)")
    print("  level | " + " | ".join(f"{t:>{width}}" for t in tasks) + " |    all | structured")
    for level in levels:
        cells = []
        for task in tasks:
            rows = [r for r in summary if r["level"] == level and r["task"] == task]
            hits = sum(1 for r in rows if r["entry_count"])
            cells.append(f"{hits}/{len(rows)}".rjust(width) if rows else "-".rjust(width))
        rows = [r for r in summary if r["level"] == level]
        hits = sum(1 for r in rows if r["entry_count"])
        structured = sum(1 for r in rows if r["decision_entry_count"])
        rate = f"{hits / len(rows):.2f}" if rows else "-"
        print(
            f"  {level:>5} | " + " | ".join(cells)
            + f" | {hits:>2}/{len(rows):<2} {rate} | {structured:>2}/{len(rows):<2}"
        )
    print(
        "  'any entry' is the headline: an agent with no format instruction records in prose, and\n"
        "  counting only the DRAFT '### Decision' shape scored those as silence - it understated the\n"
        "  low-scaffolding arms by exactly the treatment being dosed. 'structured' is a separate\n"
        "  question (does scaffolding shape the FORM), not evidence about whether anything was kept."
    )

    guarded = [r for r in summary if r.get("guard_blocked")]
    if guarded:
        silent = [r for r in guarded if not r["decision_entry_count"]]
        print(
            f"\n  worktree guard returned a block in {len(guarded)} run(s); "
            f"{len(silent)} of those recorded nothing - "
            "check these before reading a low arm as disinterest."
        )


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
    print_dose_response(summary)
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
