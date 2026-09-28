"""Run the promotion gate for evidence-backed session-record checkpoints.

The legacy side reproduces the accepted hook's decision formula:
``stale OR (non-empty current diff != baseline diff)``. The candidate side
executes the production evaluator. Each scenario uses an isolated real Git
repository so HEAD, tracked, and untracked evidence are measured, not mocked.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from memory_seed.session_checkpoint import (
    _git_snapshot,
    inspect_checkpoint,
    resolve_checkpoint,
)


NOW = datetime(2026, 9, 28, 10, 0)


def _repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="memory-seed-checkpoint-trial-"))
    (root / ".memory-seed" / "sessions" / "2026-09").mkdir(parents=True)
    (root / "tracked.txt").write_text("alpha beta\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "trial"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "trial@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=root, check=True)
    return root


def _entry(root: Path, when: datetime, entry_id: str) -> None:
    target = root / ".memory-seed" / "sessions" / "2026-09" / "2026-09-28.md"
    prior = target.read_text(encoding="utf-8") if target.exists() else ""
    target.write_text(
        prior
        + f"## {when.strftime('%Y-%m-%d %H:%M')} - trial\n\n"
        + "```yaml\n"
        + f"entry_id: {entry_id}\n"
        + "user_initials: JNL\nagent_type: codex\nproject_path: .\nsubproject_path: null\n"
        + "```\n\n### Summary\n\n- Trial.\n\n### Validation\n\n- Trial.\n",
        encoding="utf-8",
    )


def _legacy_pending(*, baseline_diff: str, current_diff: str, stale: bool) -> bool:
    return stale or bool(current_diff and current_diff != baseline_diff)


def _ordinary_scenario(
    name: str,
    mutate: Callable[[Path], None],
    *,
    elapsed_minutes: int,
    capture_expected: bool,
) -> dict[str, Any]:
    root = _repo()
    try:
        _entry(root, NOW, "mse_0123456789abcdef")
        baseline = _git_snapshot(root)
        inspect_checkpoint(root, now=NOW)
        mutate(root)
        current = _git_snapshot(root)
        candidate = inspect_checkpoint(root, now=NOW + timedelta(minutes=elapsed_minutes))
        legacy = _legacy_pending(
            baseline_diff=baseline["diff_fingerprint"],
            current_diff=current["diff_fingerprint"],
            stale=elapsed_minutes >= 15,
        )
        return {
            "name": name,
            "capture_expected": capture_expected,
            "legacy_pending": legacy,
            "candidate_pending": candidate["pending"],
            "candidate_clean_advisory": candidate["clean_advisory"],
            "candidate_ok": candidate["ok"],
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _new_entry_clears() -> dict[str, Any]:
    root = _repo()
    try:
        _entry(root, NOW, "mse_0123456789abcdef")
        inspect_checkpoint(root, now=NOW)
        (root / "tracked.txt").write_text("semantic change\n", encoding="utf-8")
        before = inspect_checkpoint(root, now=NOW + timedelta(minutes=1))
        _entry(root, NOW + timedelta(minutes=2), "mse_fedcba9876543210")
        after = inspect_checkpoint(root, now=NOW + timedelta(minutes=2))
        return {
            "name": "new-entry-clears",
            "capture_expected": False,
            "legacy_pending": False,
            "candidate_pending": after["pending"],
            "candidate_clean_advisory": after["clean_advisory"],
            "candidate_ok": before["pending"] and after["ok"],
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _whitespace_resolution() -> dict[str, Any]:
    root = _repo()
    try:
        _entry(root, NOW, "mse_0123456789abcdef")
        baseline = _git_snapshot(root)
        inspect_checkpoint(root, now=NOW)
        (root / "tracked.txt").write_text("alpha   beta\n\n", encoding="utf-8")
        current = _git_snapshot(root)
        pending = inspect_checkpoint(root, now=NOW + timedelta(minutes=1))
        resolved = resolve_checkpoint(
            root,
            checkpoint_id=pending["checkpoint_id"],
            proof="whitespace-only",
            now=NOW + timedelta(minutes=2),
        )
        return {
            "name": "whitespace-only-resolution",
            "capture_expected": False,
            "legacy_pending": _legacy_pending(
                baseline_diff=baseline["diff_fingerprint"],
                current_diff=current["diff_fingerprint"],
                stale=False,
            ),
            "candidate_pending": resolved["pending"],
            "candidate_clean_advisory": resolved["clean_advisory"],
            "candidate_ok": resolved["ok"],
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_matrix() -> dict[str, Any]:
    def no_change(root: Path) -> None:
        return None

    def tracked(root: Path) -> None:
        (root / "tracked.txt").write_text("semantic change\n", encoding="utf-8")

    def untracked(root: Path) -> None:
        (root / "new.txt").write_text("new\n", encoding="utf-8")

    def head(root: Path) -> None:
        tracked(root)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "head change"], cwd=root, check=True)

    rows = [
        _ordinary_scenario(
            "clean-recent-read-only", no_change, elapsed_minutes=5, capture_expected=False
        ),
        _ordinary_scenario(
            "clean-stale-read-only", no_change, elapsed_minutes=16, capture_expected=False
        ),
        _ordinary_scenario(
            "tracked-implementation", tracked, elapsed_minutes=1, capture_expected=True
        ),
        _ordinary_scenario(
            "untracked-implementation", untracked, elapsed_minutes=1, capture_expected=True
        ),
        _ordinary_scenario(
            "head-changed-clean-tree", head, elapsed_minutes=1, capture_expected=True
        ),
        _new_entry_clears(),
        _whitespace_resolution(),
    ]
    capture_rows = [row for row in rows if row["capture_expected"]]
    clean_rows = [row for row in rows if row["name"].startswith("clean-")]
    checks = {
        "candidate_captures_all_implementation_evidence": all(
            row["candidate_pending"] for row in capture_rows
        ),
        "candidate_never_creates_clean_time_debt": all(
            not row["candidate_pending"] for row in clean_rows
        ),
        "candidate_emits_one_clean_stale_advisory": next(
            row for row in rows if row["name"] == "clean-stale-read-only"
        )["candidate_clean_advisory"],
        "new_entry_clears": not next(
            row for row in rows if row["name"] == "new-entry-clears"
        )["candidate_pending"],
        "whitespace_proof_clears": not next(
            row for row in rows if row["name"] == "whitespace-only-resolution"
        )["candidate_pending"],
        "all_candidate_evaluations_succeeded": all(row["candidate_ok"] for row in rows),
    }
    return {
        "gate_passed": all(checks.values()),
        "checks": checks,
        "scenarios": rows,
        "comparison": {
            "legacy_clean_stale_false_positive": next(
                row for row in rows if row["name"] == "clean-stale-read-only"
            )["legacy_pending"],
            "legacy_head_change_miss": not next(
                row for row in rows if row["name"] == "head-changed-clean-tree"
            )["legacy_pending"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_matrix()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("PASS" if result["gate_passed"] else "FAIL")
        for row in result["scenarios"]:
            print(
                f"{row['name']}: legacy_pending={row['legacy_pending']} "
                f"candidate_pending={row['candidate_pending']} "
                f"clean_advisory={row['candidate_clean_advisory']}"
            )
    return 0 if result["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
