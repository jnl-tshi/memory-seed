"""Negative control for the faithfulness judge.

E6 reports 0 unfaithful reasons across 121 recorded decisions. That is only meaningful if the
judge's `no` verdict is REACHABLE - a judge that can only say `yes`, `unclear` or `not_recorded`
would produce exactly the same result on a corpus full of fabrications. This tests the instrument,
not the product.

Method: take real v2 judge packets, and in the tampered arm replace the recorded `R:` lines with a
plausible-sounding rationale that CONTRADICTS what the transcript shows the session actually did.
Everything else - packet shape, prompt, schema, model - is the untouched `judge.py` stage-1 path.

  PASS  the judge returns `no` (or at minimum not `yes`) on tampered packets, and `yes` on controls
  FAIL  the judge returns `yes`/`unclear` on tampered packets - the 0/121 is a null instrument and
        the faithfulness claim must be retracted

Usage:
  python experiments/agent-capture/judge_calibration.py [--n 3]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import judge as judge_mod  # noqa: E402  (reuse _codex, STAGE1_PROMPT, STAGE1_SCHEMA unchanged)

RUNS = HERE / "runs"
OUT = HERE / "runs" / "calibration.json"

# A rationale that is fluent, specific, and wrong: it cites a cause no strutil session ever had.
FAKE_REASON = (
    "- R: Chosen because the upstream vendor deprecated the previous interface in their 4.2 "
    "release and gave a six-week migration window, so the team had no discretion here; the "
    "benchmark numbers and the maintainer discussion were not factors in the call."
)

_R_LINE = re.compile(r"^\s*-\s+R:.*(?:\n(?!\s*-\s+[A-Z]:|\s*####|\s*###).*)*", re.MULTILINE)


def tamper(packet_text: str) -> tuple[str, int]:
    """Replace every recorded `R:` block in the packet's entries with FAKE_REASON."""
    replaced = 0

    def _sub(match: re.Match) -> str:
        nonlocal replaced
        replaced += 1
        return FAKE_REASON

    # Only tamper inside the recorded-entries section, never the transcript: the whole point is a
    # mismatch between the two.
    marker = "## Transcript"
    head, sep, tail = packet_text.partition(marker)
    head = _R_LINE.sub(_sub, head)
    return head + sep + tail, replaced


def usable_packets(limit: int) -> list[Path]:
    """Packets that actually contain a recorded reason to tamper with."""
    found = []
    for run_dir in sorted(p for p in RUNS.iterdir() if p.is_dir()):
        packet = run_dir / "judge_packet.md"
        if not packet.exists():
            continue
        text = packet.read_text(encoding="utf-8")
        head = text.partition("## Transcript")[0]
        if "- R:" not in head or "(nothing recorded)" in head:
            continue
        found.append(packet)
        if len(found) >= limit * 2:
            break
    return found


def judge_packet(packet_text: str, label: str) -> dict:
    """Run the unmodified stage-1 judge over one packet in a scratch directory."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "judge_packet.md").write_text(packet_text, encoding="utf-8")
        result = judge_mod._codex(
            judge_mod.STAGE1_PROMPT.format(packet="judge_packet.md"),
            judge_mod.STAGE1_SCHEMA,
            tmp_path,
            label,
        )
    if not result or result.get("error"):
        # Fail loudly. An errored judge call that returns "no verdicts" is indistinguishable from
        # a judge that found nothing - and reporting the latter would be a confident wrong answer
        # about the instrument, which is the exact failure class this script exists to detect.
        raise SystemExit(
            f"judge call failed for {label}: {(result or {}).get('error', 'no result')}"
        )
    return result


def verdicts_of(stage1: dict) -> list[str]:
    return [d.get("reason_faithful", "?") for d in (stage1.get("decisions") or [])]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=3, help="tampered packets (controls = same count)")
    args = parser.parse_args()

    packets = usable_packets(args.n)
    if len(packets) < args.n * 2:
        raise SystemExit(f"only {len(packets)} usable packets found; need {args.n * 2}")

    tampered_sources = packets[: args.n]
    control_sources = packets[args.n : args.n * 2]
    report: list[dict] = []

    for index, packet in enumerate(tampered_sources):
        text, count = tamper(packet.read_text(encoding="utf-8"))
        if not count:
            print(f"  skip {packet.parent.name}: nothing tampered")
            continue
        stage1 = judge_packet(text, f"tamper{index}")
        verdicts = verdicts_of(stage1)
        report.append({"arm": "tampered", "run": packet.parent.name,
                       "reasons_replaced": count, "verdicts": verdicts})
        print(f"TAMPERED {packet.parent.name[:34]:36} replaced={count} verdicts={verdicts}")

    for index, packet in enumerate(control_sources):
        stage1 = judge_packet(packet.read_text(encoding="utf-8"), f"control{index}")
        verdicts = verdicts_of(stage1)
        report.append({"arm": "control", "run": packet.parent.name, "verdicts": verdicts})
        print(f"CONTROL  {packet.parent.name[:34]:36} verdicts={verdicts}")

    tampered = [r for r in report if r["arm"] == "tampered"]
    controls = [r for r in report if r["arm"] == "control"]
    caught = sum(1 for r in tampered if "no" in r["verdicts"])
    clean = sum(1 for r in controls if "yes" in r["verdicts"] and "no" not in r["verdicts"])

    print(f"\ntampered packets where the judge said 'no': {caught}/{len(tampered)}")
    print(f"control packets judged faithful:            {clean}/{len(controls)}")
    verdict = "PASS - the `no` verdict is reachable" if caught else (
        "FAIL - the judge never returns `no`; 0/121 unfaithful is a NULL INSTRUMENT"
    )
    print(f"\n{verdict}")

    OUT.write_text(json.dumps({"report": report, "caught": caught,
                               "controls_clean": clean, "verdict": verdict},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
