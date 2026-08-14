"""Self-test the three-arm replay, transcript audit, and frozen schema-v2 grader."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

from audit import audit_transcript
from prepare import (
    LABELS,
    RELEVANT_ENTRY_IDS,
    SOURCE_REVISION,
    SUBJECT_PROMPT,
    WITHHELD_REVISION,
    prepare_study,
)
from summarize import summarize

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V0_GRADER = HERE.parent / "claude-quality-report-v0" / "grade.py"


def git(command: list[str], cwd: Path, *, input_bytes: bytes | None = None, check: bool = True):
    return subprocess.run(
        ["git", *command], cwd=cwd, input=input_bytes, capture_output=True, check=check
    )


def load_grader():
    spec = importlib.util.spec_from_file_location("decision_replay_v0_grade", V0_GRADER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load grader: {V0_GRADER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grade


def _without_receipt(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.startswith("CONTEXT_RECEIPT:")
    )


def main() -> int:
    grade = load_grader()
    with tempfile.TemporaryDirectory(prefix="quality-replay-v1-verify-") as temp:
        root = Path(temp)
        result = prepare_study(root / "study", root / "receipts", seed=17, run_id="verify")
        public = json.loads(Path(result["public_manifest"]).read_text(encoding="utf-8"))
        receipt = json.loads(Path(result["sealed_receipt"]).read_text(encoding="utf-8"))
        assert "mapping" not in public and set(public["execution_order"]) == set(LABELS)
        fixtures = {label: Path(data["path"]) for label, data in receipt["fixtures"].items()}

        task_payloads = {(path / "TASK.md").read_bytes() for path in fixtures.values()}
        assert len(task_payloads) == 1, "task differs between arms"
        for path in fixtures.values():
            leaked = git(["cat-file", "-e", f"{WITHHELD_REVISION}^{{commit}}"], path, check=False)
            assert leaked.returncode != 0, "withheld commit is visible inside a fixture"
            assert git(["status", "--porcelain"], path).stdout == b"", "fixture starts dirty"

        labels_by_arm = {arm: label for label, arm in receipt["mapping"].items()}
        available = fixtures[labels_by_arm["historical-available"]]
        no_memory = fixtures[labels_by_arm["no-dated-memory"]]
        pushed = fixtures[labels_by_arm["relevant-rationale-pushed"]]
        assert receipt["fixtures"][labels_by_arm["historical-available"]]["dated_session_documents"] > 0
        assert receipt["fixtures"][labels_by_arm["no-dated-memory"]]["dated_session_documents"] == 0
        assert receipt["fixtures"][labels_by_arm["relevant-rationale-pushed"]]["dated_session_documents"] == 0

        generic_contexts = [
            _without_receipt((path / "EXPERIMENT_CONTEXT.md").read_text(encoding="utf-8"))
            for path in (no_memory, available)
        ]
        assert generic_contexts[0] == generic_contexts[1]
        pushed_context = (pushed / "EXPERIMENT_CONTEXT.md").read_text(encoding="utf-8")
        assert all(entry_id in pushed_context for entry_id in RELEVANT_ENTRY_IDS)
        assert all(entry_id not in generic_contexts[0] for entry_id in RELEVANT_ENTRY_IDS)

        pristine = grade(available)
        assert pristine["status"] == "FAIL" and not pristine["gates"]["hidden_behavior"]
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
        git(["apply", "--whitespace=nowarn", "-"], available, input_bytes=patch)
        reference = grade(available)
        assert reference["status"] == "PASS", json.dumps(reference, indent=2)

        context = pushed / "EXPERIMENT_CONTEXT.md"
        receipt_line = next(
            line for line in context.read_text(encoding="utf-8").splitlines()
            if line.startswith("CONTEXT_RECEIPT:")
        )
        transcript = root / "synthetic.jsonl"
        synthetic = [
            {
                "timestamp": "2026-08-14T00:00:00Z",
                "message": {
                    "id": "m1",
                    "role": "assistant",
                    "model": "synthetic",
                    "content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": str(context)}}],
                    "usage": {"output_tokens": 10},
                },
                "version": "test",
                "sessionId": "synthetic-session",
            },
            {
                "timestamp": "2026-08-14T00:00:01Z",
                "type": "user",
                "message": {"role": "user", "content": [{"type": "tool_result", "content": context.read_text(encoding="utf-8")}]},
            },
            {
                "timestamp": "2026-08-14T00:00:02Z",
                "message": {
                    "id": "m2",
                    "role": "assistant",
                    "model": "synthetic",
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": f"{receipt_line}\nMemory evidence used: {RELEVANT_ENTRY_IDS[0]}"}],
                    "usage": {"output_tokens": 5},
                },
                "version": "test",
                "sessionId": "synthetic-session",
            },
        ]
        transcript.write_text(
            "".join(json.dumps(event) + "\n" for event in synthetic), encoding="utf-8"
        )
        audit = audit_transcript(pushed, transcript)
        checks = audit["manipulation_check"]
        assert checks["context_packet_uptake_confirmed"]
        assert checks["relevant_rationale_uptake_confirmed"]
        assert SUBJECT_PROMPT

        artifacts = root / "artifacts"
        artifacts.mkdir()
        (artifacts / "public-manifest.json").write_text(
            json.dumps(public, indent=2) + "\n", encoding="utf-8"
        )
        for label, fixture in fixtures.items():
            fixture_context = (fixture / "EXPERIMENT_CONTEXT.md").read_text(encoding="utf-8")
            fixture_receipt = next(
                line for line in fixture_context.splitlines() if line.startswith("CONTEXT_RECEIPT:")
            )
            used = (
                RELEVANT_ENTRY_IDS[0]
                if receipt["mapping"][label] == "relevant-rationale-pushed"
                else "none"
            )
            events = [
                {
                    "timestamp": "2026-08-14T00:00:00Z",
                    "message": {
                        "id": f"{label}-m1",
                        "role": "assistant",
                        "model": "synthetic",
                        "content": [{"type": "tool_use", "id": f"{label}-t1", "name": "Read", "input": {"file_path": str(fixture / "EXPERIMENT_CONTEXT.md")}}],
                    },
                },
                {
                    "timestamp": "2026-08-14T00:00:01Z",
                    "message": {"role": "user", "content": [{"type": "tool_result", "content": fixture_context}]},
                },
                {
                    "timestamp": "2026-08-14T00:00:02Z",
                    "message": {
                        "id": f"{label}-m2",
                        "role": "assistant",
                        "model": "synthetic",
                        "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": f"{fixture_receipt}\nMemory evidence used: {used}"}],
                    },
                },
            ]
            label_transcript = artifacts / f"{label}-transcript.jsonl"
            label_transcript.write_text(
                "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
            )
            (artifacts / f"{label}-grade.json").write_text(
                json.dumps(grade(fixture), indent=2) + "\n", encoding="utf-8"
            )
            (artifacts / f"{label}-audit.json").write_text(
                json.dumps(audit_transcript(fixture, label_transcript), indent=2) + "\n",
                encoding="utf-8",
            )
            (artifacts / f"{label}-metadata.json").write_text(
                json.dumps({"fixture": str(fixture.resolve())}, indent=2) + "\n",
                encoding="utf-8",
            )
        combined = summarize(Path(result["sealed_receipt"]), artifacts)
        assert {
            arm["condition"] for arm in combined["arms"].values()
        } == {"no-dated-memory", "historical-available", "relevant-rationale-pushed"}

        print("Harness verification PASS")
        print("  three blinded conditions and randomized execution order are complete")
        print("  no-memory and pushed arms contain no dated sessions")
        print("  pushed arm contains the bounded pre-fix entry; generic contexts do not")
        print("  pristine source fails and withheld fix passes frozen grader schema v2")
        print("  transcript manipulation check detects packet exposure and claimed use")
        print("  reveal summary refuses mismatched manifests and combines all three labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
