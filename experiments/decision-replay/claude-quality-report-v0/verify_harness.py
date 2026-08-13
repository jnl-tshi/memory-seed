"""Self-test the replay instrument against the pristine base and withheld historical fix."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from grade import grade
from prepare import SOURCE_REVISION, WITHHELD_REVISION, prepare_pair

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]


def git(command: list[str], cwd: Path, *, input_bytes: bytes | None = None, check: bool = True):
    return subprocess.run(
        ["git", *command],
        cwd=cwd,
        input=input_bytes,
        capture_output=True,
        check=check,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="quality-replay-verify-") as temp:
        root = Path(temp)
        result = prepare_pair(root / "pair", root / "receipts", seed=17, run_id="verify")
        receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
        fixtures = {label: Path(data["path"]) for label, data in receipt["fixtures"].items()}

        task_hashes = {(path / "TASK.md").read_bytes() for path in fixtures.values()}
        assert len(task_hashes) == 1, "task differs between arms"
        for path in fixtures.values():
            leaked = git(["cat-file", "-e", f"{WITHHELD_REVISION}^{{commit}}"], path, check=False)
            assert leaked.returncode != 0, "withheld commit is visible inside a fixture"
            assert git(["status", "--porcelain"], path).stdout == b"", "fixture starts dirty"

        memory_label = next(
            label for label, arm in receipt["mapping"].items() if arm == "historical-rationale"
        )
        control_label = next(
            label for label, arm in receipt["mapping"].items() if arm == "current-state"
        )
        assert receipt["fixtures"][memory_label]["dated_session_documents"] > 0
        assert receipt["fixtures"][control_label]["dated_session_documents"] == 0

        candidate = fixtures[memory_label]
        pristine = grade(candidate)
        assert pristine["status"] == "FAIL", "pristine defect does not fail the grader"
        assert pristine["gates"]["hidden_behavior"] is False

        patch = git(
            [
                "diff",
                SOURCE_REVISION,
                WITHHELD_REVISION,
                "--",
                "memory_seed/quality.py",
                "tests/test_quality.py",
            ],
            REPO_ROOT,
        ).stdout
        git(["apply", "--whitespace=nowarn", "-"], candidate, input_bytes=patch)
        reference = grade(candidate)
        assert reference["status"] == "PASS", json.dumps(reference, indent=2)

        print("Harness verification PASS")
        print("  pristine historical source fails hidden behavior")
        print("  withheld historical fix passes all four gates")
        print("  arm tasks are byte-identical and later Git history is absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
