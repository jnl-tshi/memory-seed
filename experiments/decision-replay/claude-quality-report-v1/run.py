"""Run the blinded fixtures as fresh headless Claude sessions and preserve JSONL transcripts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from audit import audit_transcript
from prepare import DEFAULT_STATE_ROOT, HERE, SUBJECT_PROMPT

V0_GRADER = HERE.parent / "claude-quality-report-v0" / "grade.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_clean(fixture: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=fixture, capture_output=True, check=True
    )
    return not result.stdout.strip()


def _git_head(fixture: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=fixture, capture_output=True, check=True, text=True
    )
    return result.stdout.strip()


def _load_grader():
    spec = importlib.util.spec_from_file_location("decision_replay_v0_grade", V0_GRADER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load grader: {V0_GRADER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grade


def _claude_version() -> str:
    completed = subprocess.run(["claude", "--version"], capture_output=True, check=True, text=True)
    return completed.stdout.strip()


def _saved_session_transcript(session_id: str) -> Path | None:
    project_store = Path.home() / ".claude" / "projects"
    if not project_store.is_dir():
        return None
    candidates = list(project_store.rglob(f"{session_id}.jsonl"))
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _run_subject(
    *, fixture: Path, label: str, artifacts: Path, model: str, effort: str, permission_mode: str
) -> dict:
    if not _git_clean(fixture):
        raise RuntimeError(f"fixture {label} is not pristine: {fixture}")
    stream = artifacts / f"{label}-stream.jsonl"
    transcript = artifacts / f"{label}-transcript.jsonl"
    stderr_path = artifacts / f"{label}-stderr.txt"
    metadata_path = artifacts / f"{label}-metadata.json"
    for path in (stream, transcript, stderr_path, metadata_path):
        if path.exists():
            raise FileExistsError(f"refusing existing artifact: {path}")

    session_id = str(uuid.uuid4())
    command = [
        "claude",
        "--print",
        SUBJECT_PROMPT,
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-hook-events",
        "--setting-sources",
        "project,local",
        "--permission-mode",
        permission_mode,
        "--model",
        model,
        "--effort",
        effort,
        "--session-id",
        session_id,
        "--mcp-config",
        str(fixture / ".mcp.json"),
        "--strict-mcp-config",
        "--disallowedTools",
        "WebSearch,WebFetch",
    ]
    started_at = dt.datetime.now(dt.timezone.utc)
    started = time.monotonic()
    with stream.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        completed = subprocess.run(
            command,
            cwd=fixture,
            stdout=stdout_handle,
            stderr=stderr_handle,
            check=False,
        )
    ended_at = dt.datetime.now(dt.timezone.utc)
    saved_transcript = _saved_session_transcript(session_id)
    transcript_source = "claude-session-store" if saved_transcript else "stdout-stream-fallback"
    shutil.copyfile(saved_transcript or stream, transcript)
    metadata = {
        "schema_version": 1,
        "label": label,
        "fixture": str(fixture.resolve()),
        "session_id": session_id,
        "model_argument": model,
        "effort": effort,
        "permission_mode": permission_mode,
        "claude_cli_version": _claude_version(),
        "prompt": SUBJECT_PROMPT,
        "started_at": started_at.isoformat(timespec="milliseconds"),
        "ended_at": ended_at.isoformat(timespec="milliseconds"),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "returncode": completed.returncode,
        "stream": str(stream.resolve()),
        "stream_sha256": _sha256(stream),
        "transcript": str(transcript.resolve()),
        "transcript_sha256": _sha256(transcript),
        "transcript_source": transcript_source,
        "stderr": str(stderr_path.resolve()),
        "stderr_sha256": _sha256(stderr_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def _write_blinded_evaluation(*, fixture: Path, label: str, transcript: Path, artifacts: Path) -> dict:
    grade_path = artifacts / f"{label}-grade.json"
    audit_path = artifacts / f"{label}-audit.json"
    for path in (grade_path, audit_path):
        if path.exists():
            raise FileExistsError(f"refusing existing blinded evaluation: {path}")
    grade_result = _load_grader()(fixture)
    audit_result = audit_transcript(fixture, transcript)
    grade_path.write_text(json.dumps(grade_result, indent=2) + "\n", encoding="utf-8")
    audit_path.write_text(json.dumps(audit_result, indent=2) + "\n", encoding="utf-8")
    return {"grade": grade_result["status"], "audit": audit_result["manipulation_check"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path, default=None)
    parser.add_argument("--model", default="opus")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--permission-mode", default="auto")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 2 or "mapping" in manifest:
        raise ValueError("expected a blinded schema-v2 public manifest")
    if manifest.get("prompt_sha256") != hashlib.sha256(SUBJECT_PROMPT.encode()).hexdigest():
        raise ValueError("public manifest prompt hash differs from this runner")
    artifacts = args.artifacts_root or (DEFAULT_STATE_ROOT / f"{manifest['run_id']}-artifacts")
    artifacts = artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=False)
    (artifacts / "public-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    results = []
    for label in manifest["execution_order"]:
        fixture = Path(manifest["fixtures"][label]["path"]).resolve()
        expected_task = manifest["task_sha256"]
        if _sha256(fixture / "TASK.md") != expected_task:
            raise ValueError(f"fixture {label} task hash differs from public manifest")
        if _git_head(fixture) != manifest["fixtures"][label]["fixture_commit"]:
            raise ValueError(f"fixture {label} HEAD differs from public manifest")
        metadata = _run_subject(
            fixture=fixture,
            label=label,
            artifacts=artifacts,
            model=args.model,
            effort=args.effort,
            permission_mode=args.permission_mode,
        )
        metadata["blinded_evaluation"] = _write_blinded_evaluation(
            fixture=fixture,
            label=label,
            transcript=Path(metadata["transcript"]),
            artifacts=artifacts,
        )
        (artifacts / f"{label}-metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        results.append(metadata)
        if metadata["returncode"] != 0:
            break
    complete = len(results) == len(manifest["execution_order"]) and all(
        item["returncode"] == 0 for item in results
    )
    summary = {
        "run_id": manifest["run_id"],
        "artifacts": str(artifacts),
        "subjects": results,
        "next": (
            "All blinded grade/audit files exist; the sealed receipt may now be summarized."
            if complete
            else "Run invalid: do not reveal or resume; prepare fresh fixtures with a new run ID."
        ),
    }
    print(json.dumps(summary, indent=2))
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
