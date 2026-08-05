"""Run the owner-approved, unscored 8-cell ADR context pilot exactly once."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT))

import collect  # noqa: E402
import generate_fixtures  # noqa: E402
import run as subject_run  # noqa: E402
from contracts import ARMS, canonical_json, live_execution_approved, live_pin_matches, load_json  # noqa: E402
from pilot_spec import (  # noqa: E402
    PILOT_AUTH_ENV, PILOT_CELLS, PILOT_CLAIM_PATH, PILOT_SCHEMA,
    PILOT_AUTHORITY_MARKER, PILOT_SUMMARY_SCHEMA, PILOT_TASK_ID, SOURCE, gold_payload,
    output_authority_payload, path_identity, pilot_cell_claim_path, safe_absent_temp_path, sha256_text, task_payload, validate_task_payload,
    verify_output_authority,
    verified_claude_executable,
)
from score import score_run  # noqa: E402


def _fingerprint_tree(root: Path, *, exclude: frozenset[str] = frozenset()) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root).as_posix()
        if any(part in exclude for part in path.relative_to(root).parts):
            continue
        digest.update(rel.encode("utf-8")); digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def _protected_snapshot(repo: Path, experiment: Path, gold_path: Path, tasks_path: Path, fixture: Path) -> dict[str, str]:
    return {
        "repo": _fingerprint_tree(repo, exclude=frozenset({".git", "__pycache__", ".pytest_cache"})),
        "experiment": _fingerprint_tree(experiment, exclude=frozenset({"__pycache__"})),
        "gold": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
        "tasks": hashlib.sha256(tasks_path.read_bytes()).hexdigest(),
        "fixture": _fingerprint_tree(fixture),
    }


def assert_pilot_gold_isolated(gold_path: Path, *subject_visible: Path) -> None:
    gold_bytes = gold_path.read_bytes()
    for root in subject_visible:
        paths = [root] if root.is_file() else [item for item in root.rglob("*") if item.is_file()]
        for path in paths:
            if gold_bytes in path.read_bytes():
                raise ValueError(f"pilot gold bytes leaked into subject-visible artifact: {path.name}")


def build_runtime(runtime: Path) -> tuple[Path, Path, dict[str, Any], Path]:
    fixture = runtime / "fixture"
    fixture.mkdir(parents=True)
    generate_fixtures._write_text(fixture / "CONSTITUTION.md", "# Pilot Fixture\n\nEvidence is read-only and attributable.\n")
    generate_fixtures._build_adversarial(fixture, SOURCE)
    manifest = {
        "schema": "context-fixture-manifest.v1", "fixture_id": SOURCE["fixture_id"],
        "task_ids": [PILOT_TASK_ID], "gold_included": False,
        "content_fingerprint": generate_fixtures.tree_fingerprint(fixture),
        "generated_by": "experiments/context-derivation/pilot.py",
    }
    generate_fixtures._write_text(fixture / "FIXTURE_MANIFEST.json", json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    payload = task_payload(fixture)
    if not validate_task_payload(payload):
        raise RuntimeError("pilot task materialization is not deterministic")
    tasks = runtime / "pilot-tasks.json"
    tasks.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    gold = gold_payload()
    gold_path = runtime / "pilot-gold.json"
    gold_path.write_text(json.dumps(gold, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    generate_fixtures.assert_gold_isolated(fixture)
    assert_pilot_gold_isolated(gold_path, fixture, tasks)
    gold_bytes = gold_path.read_bytes()
    for arm in ARMS:
        if gold_bytes in subject_run.subject_prompt(payload["tasks"][0], arm).encode("utf-8"):
            raise ValueError(f"pilot gold bytes leaked into {arm} prompt")
    return fixture, tasks, gold, gold_path


def _consume_claim(
    *, auth: str, tasks_fingerprint: str, tasks_path: Path, fixture: Path,
    output: Path,
) -> None:
    tasks_sha256 = hashlib.sha256(tasks_path.read_bytes()).hexdigest()
    fixture_path = fixture.resolve()
    fixture_identity = path_identity(fixture)
    claim = {
        "schema": "context-pilot-claim.v1", "pilot": PILOT_TASK_ID,
        "auth_sha256": sha256_text(auth), "tasks_fingerprint": tasks_fingerprint,
        "tasks_sha256": tasks_sha256,
        "fixture_path_sha256": sha256_text(str(fixture_path)),
        "fixture_identity": fixture_identity,
        "cells": [list(cell) for cell in PILOT_CELLS], "consumed": True,
    }
    # The output is deliberately absent at claim creation. Atomic mkdir follows
    # the claim; any competing creation therefore fails closed before queues.
    validated_output = safe_absent_temp_path(output, REPO_ROOT)
    claim["output_path_sha256"] = sha256_text(str(validated_output.resolve()))
    claim["authority_marker"] = PILOT_AUTHORITY_MARKER
    try:
        descriptor = os.open(PILOT_CLAIM_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("the one-shot unscored pilot has already been consumed on this machine") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(canonical_json(claim) + "\n")


def _create_output_authority(output: Path, auth: str) -> str:
    output.mkdir(exist_ok=False)
    identity = path_identity(output)
    marker = output / PILOT_AUTHORITY_MARKER
    payload = output_authority_payload(output, PILOT_CLAIM_PATH.read_bytes(), auth)
    with marker.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(payload) + "\n")
    if path_identity(output) != identity or {item.name for item in output.iterdir()} != {PILOT_AUTHORITY_MARKER}:
        raise RuntimeError("pilot output was populated or replaced during authority creation")
    if not verify_output_authority(output, PILOT_CLAIM_PATH, auth):
        raise RuntimeError("pilot output authority marker verification failed")
    try:
        claim = json.loads(PILOT_CLAIM_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("pilot claim became unreadable during output creation") from exc
    resolved = output.resolve(strict=True)
    if claim.get("output_path_sha256") != sha256_text(str(resolved)):
        raise RuntimeError("pilot output resolved path no longer matches the claim")
    temp_root = Path(tempfile.gettempdir()).resolve()
    try: output.absolute().relative_to(temp_root)
    except ValueError as exc: raise RuntimeError("pilot output escaped the OS temporary root") from exc
    current = output.absolute()
    while True:
        try: info = current.lstat()
        except OSError as exc: raise RuntimeError("pilot output ancestor became unreadable") from exc
        attrs = getattr(info, "st_file_attributes", 0)
        if current.is_symlink() or bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise RuntimeError("pilot output ancestor became a reparse point")
        if current == temp_root: break
        if current.parent == current:
            raise RuntimeError("pilot output ancestor chain did not reach the OS temporary root")
        current = current.parent
    return identity


def _read_manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "RUN_MANIFEST.json"
    if not path.exists():
        raise RuntimeError(f"pilot child did not finalize a manifest: {run_dir.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validated_manifest_cell(
    manifest: dict[str, Any], requested: tuple[str, str, int],
    run_dir: Path, output: Path,
) -> tuple[str, str, int] | None:
    cell = (manifest.get("agent"), manifest.get("arm"), manifest.get("repetition"))
    if not (
        manifest.get("task_id") == PILOT_TASK_ID and cell == requested
        and manifest.get("pilot") is True and manifest.get("scored") is False
        and run_dir.resolve().parent == output.resolve()
        and manifest.get("run_id") == run_dir.name
        and manifest.get("transcript") == "transcript.jsonl"
        and manifest.get("final_answer") == "final_answer.txt"
    ):
        return None
    return cell  # type: ignore[return-value]


def _run_cell(
    agent: str, arm: str, *, output: Path, tasks: Path, claude_executable: Path,
    pins: dict[str, Any], auth: str, stop: threading.Event, timeout: int,
    containment_check: Any,
) -> dict[str, Any]:
    if stop.is_set():
        return {"cell": [agent, arm, 1], "not_launched": "containment_stop"}
    pin = pins[agent]
    command = [
        sys.executable, str(HERE / "run.py"), "--owner-approved",
        "--pilot-output", str(output), "--task", PILOT_TASK_ID, "--arm", arm,
        "--agent", agent, "--repetition", "1", "--model", pin["model"],
        "--cli-version", pin["cli_version"], "--tasks", str(tasks),
        "--timeout", str(timeout),
    ]
    if pin.get("effort") is not None:
        command += ["--effort", str(pin["effort"])]
    if agent == "claude":
        command += ["--pilot-claude-executable", str(claude_executable)]
    environment = subject_run.subject_environment({PILOT_AUTH_ENV: auth, "PYTHONDONTWRITEBYTECODE": "1"})
    try:
        completed = subject_run.capped_subprocess(
            command, cwd=HERE, env=environment, timeout=timeout + 60,
            byte_limit=subject_run.PILOT_CHILD_OUTPUT_LIMIT,
        )
    except OSError as exc:
        stop.set()
        return {
            "cell": [agent, arm, 1], "containment_failure": "child_process_control_failure",
            "detail": type(exc).__name__,
        }
    if completed.overflow or completed.timed_out:
        stop.set()
        return {"cell": [agent, arm, 1], "containment_failure": "child_output_or_timeout"}
    try:
        receipt = json.loads(completed.stdout.strip().splitlines()[-1])
        run_dir = Path(receipt["output"])
        if run_dir.resolve().parent != output.resolve():
            raise ValueError("child receipt escaped pilot output")
        manifest = _read_manifest(run_dir)
    except (ValueError, KeyError, IndexError, OSError) as exc:
        stop.set()
        return {"cell": [agent, arm, 1], "returncode": completed.returncode, "containment_failure": "missing_or_invalid_child_receipt", "detail": type(exc).__name__}
    expected_cell = (agent, arm, 1)
    manifest_cell = (manifest.get("agent"), manifest.get("arm"), manifest.get("repetition"))
    manifest_valid = _validated_manifest_cell(manifest, expected_cell, run_dir, output) is not None
    try:
        snapshot_safe = bool(containment_check())
    except (OSError, ValueError, RuntimeError):
        stop.set()
        return {"cell": [agent, arm, 1], "manifest_cell": list(manifest_cell), "returncode": completed.returncode, "run_dir": str(run_dir), "containment_failure": "containment_snapshot_read_failure"}
    containment = (
        not manifest_valid or bool(manifest.get("integrity_failures"))
        or not manifest.get("parent_isolated") or not manifest.get("fixture_isolated")
        or not snapshot_safe
    )
    if containment:
        stop.set()
    return {"cell": [agent, arm, 1], "manifest_cell": list(manifest_cell), "returncode": completed.returncode, "run_dir": str(run_dir), "containment_failure": "child_integrity" if containment else None}


def _queue(agent: str, **kwargs: Any) -> list[dict[str, Any]]:
    return [_run_cell(agent, arm, **kwargs) for arm in ARMS]


def _execute_queues(queue_args: dict[str, Any]) -> list[dict[str, Any]]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_queue, agent, **queue_args) for agent in ("claude", "codex")]
        return [item for future in futures for item in future.result()]


def _canonical_summary_order(cells: list[tuple[Any, ...]]) -> bool:
    return cells == list(PILOT_CELLS)


def _claims_complete() -> bool:
    try:
        return all(
            pilot_cell_claim_path(cell).is_file()
            and pilot_cell_claim_path(cell).read_bytes() == b"consumed\n"
            for cell in PILOT_CELLS
        )
    except OSError:
        return False


def _pilot_row(run_dir: Path) -> dict[str, Any]:
    manifest = _read_manifest(run_dir)
    final = (run_dir / manifest["final_answer"]).read_text(encoding="utf-8", errors="replace")
    answer = collect.parse_answer(final)
    transcript = collect.events(run_dir / manifest["transcript"])
    _excerpt, observed_refs = collect.transcript_evidence(transcript)
    included_refs = (
        sorted(set(observed_refs))
        if manifest["arm"] in {"search-mcp", "adr-mcp-workflow"}
        else manifest.get("included_refs", [])
    )
    protocol_failures = list(manifest.get("protocol_failures") or [])
    if answer is None or manifest.get("integrity_failures"):
        protocol_failures.append("invalid_answer_or_integrity")
    return {
        "run_id": manifest["run_id"], "task_id": manifest["task_id"],
        "arm": manifest["arm"], "agent": manifest["agent"], "repetition": manifest["repetition"],
        "answer": answer, "included_refs": included_refs,
        "context_token_proxy": manifest.get("context_token_proxy"), "duration_ms": manifest.get("duration_ms"),
        "input_tokens": manifest.get("input_tokens"), "output_tokens": manifest.get("output_tokens"),
        "cost_usd": manifest.get("cost_usd"), "tool_calls": manifest.get("tool_calls", []),
        "protocol_failure": ";".join(protocol_failures) or None,
        "harness_failure": manifest.get("failure_classification"), "exclusion_reason": manifest.get("failure_classification"),
    }


def _usage_summary(rows: list[dict[str, Any]]) -> dict[str, int | float | None]:
    known_costs = [
        float(row["cost_usd"])
        for row in rows
        if isinstance(row.get("cost_usd"), (int, float))
        and not isinstance(row.get("cost_usd"), bool)
    ]
    return {
        "input_tokens": sum(int(row.get("input_tokens") or 0) for row in rows),
        "output_tokens": sum(int(row.get("output_tokens") or 0) for row in rows),
        "cost_usd": sum(known_costs) if known_costs else None,
    }


def _write_partial_summary(
    output: Path, observed: dict[str, str], receipts: list[dict[str, Any]],
    error: BaseException,
) -> int:
    summary = {
        "schema": PILOT_SUMMARY_SCHEMA, "pilot": True, "scored": False,
        "task_id": PILOT_TASK_ID, "expected_calls": 8,
        "launched_calls": sum(bool(item.get("run_dir")) for item in receipts),
        "max_total_concurrency": 2, "max_agent_concurrency": 1, "retries": 0,
        "gold_used": True, "judges_run": 0, "normal_scoring_run": False,
        "per_cell_claims_complete": _claims_complete(), "passed": False,
        "failure_classification": "coordinator_containment_failure",
        "error_type": type(error).__name__, "cells": [],
        "receipts": [{key: value for key, value in item.items() if key != "run_dir"} for item in receipts],
        "usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": None},
        "cli_versions": observed,
    }
    (output / "PILOT_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "passed": False, "launched_calls": summary["launched_calls"]}))
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-approved", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--claude-executable", required=True)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args(argv)
    if not args.owner_approved:
        parser.error("--owner-approved is required before the paid pilot")
    if args.timeout <= 0 or args.timeout > subject_run.PILOT_TIMEOUT_MAX:
        parser.error(f"--timeout must be between 1 and {subject_run.PILOT_TIMEOUT_MAX}")
    if not live_execution_approved(HERE):
        parser.error("the frozen live prerequisites are not valid")
    output = safe_absent_temp_path(args.output, REPO_ROOT)
    claude_executable = verified_claude_executable(Path(args.claude_executable))
    if PILOT_CLAIM_PATH.exists() or any(pilot_cell_claim_path(cell).exists() for cell in PILOT_CELLS):
        parser.error("the one-shot unscored pilot has already been consumed on this machine")
    matrix = load_json(HERE / "LIVE_MATRIX.json"); pins = matrix["pins"]
    observed: dict[str, str] = {}
    for agent in ("claude", "codex"):
        executable = claude_executable if agent == "claude" else None
        _raw, version = subject_run.installed_cli_version(agent, executable=executable)
        observed[agent] = version
        pin = pins[agent]
        if version != pin["cli_version"] or not live_pin_matches(HERE, agent, pin["model"], pin["cli_version"], pin.get("effort")):
            parser.error(f"{agent} executable/model does not match LIVE_MATRIX.json")

    runtime = Path(tempfile.mkdtemp(prefix="context-derivation-pilot-runtime-")).resolve()
    try:
        fixture, tasks, gold, gold_path = build_runtime(runtime)
        payload = json.loads(tasks.read_text(encoding="utf-8"))
        protected_before = _protected_snapshot(REPO_ROOT, HERE, gold_path, tasks, fixture)
        auth = secrets.token_urlsafe(32)
        # The irreversible global claim binds the still-absent path. Atomic
        # directory creation and its authority marker precede both queues.
        _consume_claim(
            auth=auth, tasks_fingerprint=payload["fingerprint"], tasks_path=tasks,
            fixture=fixture, output=output,
        )
        try:
            _create_output_authority(output, auth)
        except (OSError, ValueError, RuntimeError) as exc:
            print(json.dumps({"output": str(output), "passed": False, "launched_calls": 0, "failure_classification": "output_authority_creation_failure", "error_type": type(exc).__name__}))
            return 1
        stop = threading.Event()
        def containment_check() -> bool:
            return protected_before == _protected_snapshot(REPO_ROOT, HERE, gold_path, tasks, fixture)
        queue_args = {"output": output, "tasks": tasks, "claude_executable": claude_executable, "pins": pins, "auth": auth, "stop": stop, "timeout": args.timeout, "containment_check": containment_check}
        try:
            receipts = _execute_queues(queue_args)
        except (OSError, ValueError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
            return _write_partial_summary(output, observed, [], exc)

        launched = [item for item in receipts if item.get("run_dir")]
        cells = [tuple(item.get("manifest_cell", ())) for item in launched]
        valid_launched = [item for item in launched if not item.get("containment_failure")]
        rows = []
        row_failures = []
        for item in valid_launched:
            try: rows.append(_pilot_row(Path(item["run_dir"])))
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                row_failures.append({"cell": item.get("manifest_cell"), "containment_failure": "invalid_finalized_artifact", "detail": type(exc).__name__})
        gold_row = gold["tasks"][0]
        mechanical = [score_run(row, gold_row) for row in rows]
        containment = [item for item in receipts if item.get("containment_failure")] + row_failures
        try:
            protected_after = _protected_snapshot(REPO_ROOT, HERE, gold_path, tasks, fixture)
        except (OSError, ValueError, RuntimeError) as exc:
            protected_after = {key: "<unreadable>" for key in protected_before}
            containment.append({"containment_failure": "final_snapshot_read_failure", "detail": type(exc).__name__})
        snapshots = {f"{key}_unchanged": protected_before[key] == protected_after[key] for key in protected_before}
        claims_complete = _claims_complete()
        passed = (
            len(launched) == len(PILOT_CELLS) and _canonical_summary_order(cells)
            and claims_complete and not containment and all(snapshots.values())
            and all(row.get("complete_correct") for row in mechanical)
        )
        summary = {
            "schema": PILOT_SUMMARY_SCHEMA, "pilot": True, "scored": False,
            "task_id": PILOT_TASK_ID, "expected_calls": 8, "launched_calls": len(launched),
            "max_total_concurrency": 2, "max_agent_concurrency": 1, "retries": 0,
            "gold_used": True, "judges_run": 0, "normal_scoring_run": False,
            "gold_fingerprint": "sha256:" + protected_before["gold"],
            "per_cell_claims_complete": claims_complete,
            "passed": passed, "snapshots": snapshots,
            "cells": mechanical, "receipts": [{key: value for key, value in item.items() if key != "run_dir"} for item in receipts],
            "usage": _usage_summary(rows),
            "cli_versions": observed,
        }
        (output / "PILOT_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), "passed": passed, "launched_calls": len(launched)}))
        return 0 if passed else 1
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
