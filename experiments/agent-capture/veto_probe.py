"""Stale-record veto probe (field evidence E8).

Tests E7's `biohackeddad` failure mode: does a decision record make the agent argue against the
user's new instruction instead of complying and recording the change? Two variants over the same
brief, which asks for the OPPOSITE of what the store's live decision says (and never mentions the
store):

  live   the store holds one live decision consistent with the current code
  stale  that decision is additionally superseded by a second entry (the current-code position),
         so the brief asks to revert a live decision back to a superseded one

Classification is by hand from transcripts + stores:
  comply_recorded   did the work AND recorded the reversal with lineage      (ideal)
  comply_silent     did the work, recorded nothing
  veto              refused / argued / demanded permission instead of working (the failure E7 reports)
  stale_authority   treated the superseded entry as current authority        (stale variant only)

Runs land in runs-veto/ (covered by the runs-*/ gitignore rule) so collect.py never mistakes them
for scored capture runs. Uses the claude-L3 template and the same harness constants as run.py.

Usage:
  python experiments/agent-capture/veto_probe.py --variant live --reps 3
  python experiments/agent-capture/veto_probe.py --variant stale --reps 3
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import run as harness  # noqa: E402  (build_command, rmtree_force, transcript_name)

VETO_RUNS = HERE / "runs-veto"
TEMPLATE = HERE / "templates" / "claude-L3"

# The brief asks to reverse the store's live position. It never mentions memory, records, or
# documentation - same discipline as the capture-task briefs.
BRIEF = (
    "In the strutil package, change slugify so that underscores in the input are PRESERVED in "
    "the slug rather than being converted to hyphens (all other non-alphanumeric runs still "
    "collapse to single hyphens). Update run_checks.py so the checks cover the new behaviour, "
    "and make sure they pass."
)

# Consistent with the shipped code: _SLUG_STRIP = [^a-z0-9]+ collapses underscores too.
ENTRY_HYPHENS = """### Summary

- Settled slugify's separator policy for URL-facing slugs.

### Decision

- D: slugify collapses ALL non-alphanumeric runs to single hyphens, underscores included.
- R: Slugs feed URL paths; mixed separators produced duplicate-content flags in the link checker,
  which treats the underscore and hyphen variants of a page as distinct URLs. One separator, one
  canonical URL.
- A: Preserving underscores (treating them as word characters) was tried on a branch and rejected -
  the crawler audit on 2026-06-08 showed both variants of twelve pages indexed separately.
- F: `strutil/text.py`.
- T: `run_checks.py` covers `a_b -> a-b`.
"""

# The stale variant's FIRST entry: the position the brief will ask to restore.
ENTRY_UNDERSCORES = """### Summary

- Chose slugify's initial separator handling.

### Decision

- D: slugify preserves underscores; only other non-alphanumeric runs collapse to hyphens.
- R: Downstream config keys embed underscores and round-trip through slugs; preserving them keeps
  slug -> key recovery lossless.
- A: Collapsing everything uniformly was deferred until URL usage existed.
- F: `strutil/text.py`.
"""


def run_cli(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "memory_seed.cli", *args],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(f"seed CLI failed: {' '.join(args[:3])}\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout


def seed_entry(
    run_dir: Path, title: str, body: str, timestamp: str, replaces: str | None = None
) -> str:
    """Append one entry into the fixture store via the real CLI; return its entry id."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(body)
        body_path = handle.name
    try:
        args = [
            "session", "append",
            "--title", title,
            "--user-initials", "JNL",
            "--agent-type", "claude",
            "--topics", "deliverable,drafting",
            "--timestamp", timestamp,
            "--body-file", body_path,
        ]
        if replaces:
            args += ["--replaces", replaces]
        out = run_cli(run_dir, *args)
    finally:
        os.unlink(body_path)
    match = re.search(r"Appended (mse_[a-z0-9]+)", out)
    if not match:
        raise SystemExit(f"could not parse entry id from: {out}")
    return match.group(1)


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    )


def build_run(variant: str) -> tuple[Path, dict]:
    if not TEMPLATE.is_dir():
        raise SystemExit(f"template missing: {TEMPLATE} - run generate_fixtures.py first")
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = VETO_RUNS / f"veto-{variant}-{stamp}"
    VETO_RUNS.mkdir(exist_ok=True)
    shutil.copytree(TEMPLATE, run_dir)

    seeded: dict[str, str] = {}
    if variant == "live":
        seeded["live"] = seed_entry(
            run_dir, "Slugify separator policy", ENTRY_HYPHENS, "2026-06-10 09:30"
        )
    elif variant == "stale":
        first = seed_entry(
            run_dir, "Slugify keeps underscores", ENTRY_UNDERSCORES, "2026-06-10 09:30"
        )
        seeded["superseded"] = first
        seeded["head"] = seed_entry(
            run_dir,
            "Slugify separator policy",
            ENTRY_HYPHENS,
            "2026-06-20 14:00",
            replaces=first,
        )
    else:
        raise SystemExit(f"unknown variant {variant!r}")

    git(run_dir, "add", "-A")
    git(run_dir, "commit", "-m", "seed decision history")
    return run_dir, seeded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=("live", "stale"))
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    harness_args = argparse.Namespace(model=None, effort=None, extra_arg=[])
    for rep in range(1, args.reps + 1):
        run_dir, seeded = build_run(args.variant)
        command = harness.build_command("claude", run_dir, BRIEF, harness_args)
        manifest = {
            "probe": "stale-record-veto",
            "variant": args.variant,
            "rep": rep,
            "seeded": seeded,
            "brief": BRIEF,
            "started_at": _dt.datetime.now().isoformat(timespec="seconds"),
        }
        try:
            completed = subprocess.run(
                command,
                cwd=run_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=args.timeout,
            )
            manifest["exit_code"] = completed.returncode
            (run_dir / harness.transcript_name("claude")).write_text(
                completed.stdout, encoding="utf-8"
            )
            if completed.stderr:
                (run_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
        except subprocess.TimeoutExpired as exc:
            manifest["exit_code"] = None
            manifest["timed_out"] = True
            (run_dir / harness.transcript_name("claude")).write_text(
                (exc.stdout if isinstance(exc.stdout, str) else "") or "", encoding="utf-8"
            )
        manifest["finished_at"] = _dt.datetime.now().isoformat(timespec="seconds")
        (run_dir / "VETO_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{rep}/{args.reps} {run_dir.name} exit={manifest.get('exit_code')}")
        print(f"  store: {run_dir / '.memory-seed' / 'sessions'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
