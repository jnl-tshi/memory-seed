"""Score the judged runs against the pre-registered metrics and thresholds.

Reads runs/judgements.json (blind stage 1 + keyed stage 2) and runs/summary.json, and reports the
metrics PREREGISTRATION.md named in advance:

  capture rate     judged seeded decisions recorded / seeded decisions the judge says were MADE
  faithfulness     of those recorded, how many the judge called a faithful reason
  noise rate       recorded entries with no seeded referent / recorded entries
  no-diff capture  capture rate on T3 alone (the decision that produces no code diff)

Denominator note: a seeded decision the judge says was never made is excluded rather than counted
as a miss - the task failed to force it, which is a fact about the task, not the agent. Those are
reported separately so the exclusion is visible, per the harness rule that dropped units are
counted rather than quietly removed.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"


def main() -> int:
    judgements = json.loads((RUNS / "judgements.json").read_text(encoding="utf-8"))
    summary = {row["run_id"]: row for row in json.loads((RUNS / "summary.json").read_text(encoding="utf-8"))}

    per_level: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_task: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures = []

    for judgement in judgements:
        run_id = judgement["run_id"]
        row = summary.get(run_id)
        stage2 = judgement.get("stage2") or {}
        if not row or judgement.get("error") or stage2.get("error") or "matches" not in stage2:
            failures.append((run_id, judgement.get("error") or stage2.get("error") or "no matches"))
            continue
        level, task = row["level"], row["task"]
        stage1 = judgement.get("stage1") or {}

        for match in stage2["matches"]:
            for bucket in (per_level[level], per_task[task]):
                if not match["made"]:
                    bucket["not_made"] += 1
                    continue
                bucket["made"] += 1
                if match["recorded"]:
                    bucket["recorded"] += 1
                    if match["reason_faithful"] == "yes":
                        bucket["faithful"] += 1
                    elif match["reason_faithful"] == "unclear":
                        bucket["faithful_unclear"] += 1

        per_level[level]["runs"] += 1
        per_level[level]["noise"] += stage1.get("noise_entries") or 0
        per_level[level]["entries"] += row.get("entry_count") or 0

    def rate(numerator: int, denominator: int) -> str:
        return f"{numerator / denominator:.2f}" if denominator else "  - "

    print("JUDGED CAPTURE RATE (pre-registered metric)")
    print("  level | seeded made | recorded |  rate | faithful (of recorded) | noise/entries")
    for level in sorted(per_level):
        b = per_level[level]
        faithful = f"{b['faithful']}/{b['recorded']}" if b["recorded"] else "-"
        unclear = f" (+{b['faithful_unclear']} unclear)" if b.get("faithful_unclear") else ""
        print(
            f"  {level:>5} | {b['made']:>11} | {b['recorded']:>8} | {rate(b['recorded'], b['made'])} "
            f"| {faithful:>10}{unclear:<16} | {b['noise']}/{b['entries']}"
        )

    print("\n  by task (T3 is the no-diff determination)")
    for task in sorted(per_task):
        b = per_task[task]
        print(f"  {task:>5} | made {b['made']:>3} | recorded {b['recorded']:>3} | rate {rate(b['recorded'], b['made'])}")

    print("\nPRE-REGISTERED THRESHOLDS")
    for level in sorted(per_level):
        b = per_level[level]
        if not b["made"]:
            continue
        capture = b["recorded"] / b["made"]
        noise = (b["noise"] / b["entries"]) if b["entries"] else 0.0
        reliable = capture >= 0.8 and noise <= 0.3
        print(
            f"  {level}: capture {capture:.2f}, noise {noise:.2f} -> "
            f"{'RELIABLE' if reliable else 'not reliable'}"
        )
    cheap = [
        level
        for level in ("L1", "L2")
        if per_level[level]["made"] and per_level[level]["recorded"] / per_level[level]["made"] >= 0.8
    ]
    l3 = per_level.get("L3", {})
    l3_capture = (l3["recorded"] / l3["made"]) if l3.get("made") else None
    print(
        "\n  cheapness claim: "
        + (f"SURVIVES via {'/'.join(cheap)}" if cheap else "FAILS - no L1/L2 arm reached 0.8")
    )
    if l3_capture is not None:
        print(
            f"  kill condition (L3 < 0.5): {'TRIGGERED' if l3_capture < 0.5 else 'not triggered'} "
            f"(L3 = {l3_capture:.2f})"
        )

    excluded = sum(b["not_made"] for b in per_level.values())
    print(f"\n  {excluded} seeded decision(s) excluded as never made (task did not force them)")
    if failures:
        print(f"  {len(failures)} run(s) unjudged:")
        for run_id, reason in failures[:10]:
            print(f"    {run_id}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
