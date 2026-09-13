"""Apply the frozen, hidden gates to one completed decision-replay fixture."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ALLOWED_CHANGED_FILES = {"memory_seed/quality.py", "tests/test_quality.py"}

HIDDEN_TEST = r'''
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CANDIDATE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(CANDIDATE))

from memory_seed.quality import build_quality_report


def entry(heading, entry_id, body):
    return f"""## {heading}

```yaml
entry_id: {entry_id}
user_initials: JNL
agent_type: claude
project_path: .
```

{body}
"""


def metric(report, metric_id):
    return next(item for item in report.metrics if item.id == metric_id)


def snapshot(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


class HiddenRuntimeRootContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="quality-replay-hidden-")
        self.root = Path(self.temp.name)
        sessions = self.root / ".memory-seed" / "sessions" / "2026-05"
        sessions.mkdir(parents=True)
        (sessions / "2026-05-10.md").write_text(
            "# Session Log\n\n"
            + entry("2026-05-10 09:00 - Covered", "ms-a0000000", "### Decision\n\n- D: a.\n- R: because.")
            + "\n"
            + entry("2026-05-10 10:00 - Uncovered", "ms-b0000000", "### Decision\n\n- D: b with no reason."),
            encoding="utf-8",
        )
        self.nested = self.root / "memory-trace" / "src"
        self.nested.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_python_api_uses_active_runtime_root(self):
        root_report = build_quality_report(self.root)
        nested_report = build_quality_report(self.nested)
        for metric_id in ("draft_reason_coverage", "unlinked_entry_rate"):
            self.assertEqual(metric(root_report, metric_id), metric(nested_report, metric_id))
        coverage = metric(nested_report, "draft_reason_coverage")
        self.assertEqual((coverage.numerator, coverage.denominator), (1, 2))

    def test_cli_from_nested_directory_agrees_and_writes_nothing(self):
        before = snapshot(self.root)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(CANDIDATE)
        completed = subprocess.run(
            [sys.executable, "-m", "memory_seed.cli", "quality", "report", "--json"],
            cwd=self.nested,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        coverage = next(item for item in payload["metrics"] if item["id"] == "draft_reason_coverage")
        self.assertEqual((coverage["numerator"], coverage["denominator"]), (1, 2))
        self.assertEqual(before, snapshot(self.root))

    def test_source_read_failure_fails_or_reports_unavailable(self):
        # Extraction uses pathlib. The quality pass then uses this canonical reader;
        # raising here isolates the post-extraction read that the historical bug swallowed.
        before = snapshot(self.root)
        with mock.patch("memory_seed.text_files.read_text_file", side_effect=OSError("blocked")):
            try:
                report = build_quality_report(self.root)
            except OSError:
                # Fail-fast is honest: no coverage result was produced.
                pass
            else:
                # Structured degradation is equally honest when the metric makes the
                # missing input explicit and withholds every coverage number.
                coverage = metric(report, "draft_reason_coverage")
                self.assertEqual(coverage.status, "unavailable")
                self.assertIsNone(coverage.numerator)
                self.assertIsNone(coverage.denominator)
                self.assertIsNone(coverage.rate)
        self.assertEqual(before, snapshot(self.root))


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
'''


def run(command: list[str], *, cwd: Path) -> dict:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    return {
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def changed_files(candidate: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=candidate,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = []
    for line in completed.stdout.splitlines():
        raw = line[3:]
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.append(raw.replace("\\", "/"))
    return sorted(set(paths))


def grade(candidate: Path) -> dict:
    candidate = candidate.resolve()
    if not (candidate / ".git").exists() or not (candidate / "TASK.md").exists():
        raise SystemExit(f"not a prepared fixture repository: {candidate}")

    changed = changed_files(candidate)
    scope_ok = bool(changed) and set(changed).issubset(ALLOWED_CHANGED_FILES)
    test_owned = "tests/test_quality.py" in changed

    public = run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_quality.py"],
        cwd=candidate,
    )
    with tempfile.TemporaryDirectory(prefix="quality-replay-grader-") as temp:
        hidden_path = Path(temp) / "hidden_runtime_root_contract.py"
        hidden_path.write_text(textwrap.dedent(HIDDEN_TEST), encoding="utf-8")
        hidden = run([sys.executable, str(hidden_path), str(candidate)], cwd=candidate)

    gates = {
        "hidden_behavior": hidden["passed"],
        "public_quality_tests": public["passed"],
        "bounded_file_scope": scope_ok,
        "candidate_regression_test": test_owned,
    }
    return {
        "schema_version": 2,
        "candidate": str(candidate),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "changed_files": changed,
        "allowed_changed_files": sorted(ALLOWED_CHANGED_FILES),
        "commands": {
            "public": public,
            "hidden": hidden,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = grade(args.candidate)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Decision replay: {result['status']}")
        for gate, passed in result["gates"].items():
            print(f"  {'PASS' if passed else 'FAIL'}  {gate}")
        print("  changed: " + (", ".join(result["changed_files"]) or "(none)"))
        if not result["commands"]["hidden"]["passed"]:
            print("\nHidden contract output:\n" + result["commands"]["hidden"]["stdout"])
            print(result["commands"]["hidden"]["stderr"])
        if not result["commands"]["public"]["passed"]:
            print("\nPublic test output:\n" + result["commands"]["public"]["stdout"])
            print(result["commands"]["public"]["stderr"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
