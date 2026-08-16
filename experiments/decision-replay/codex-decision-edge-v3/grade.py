"""Grade one decision-edge candidate with an external frozen oracle."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HIDDEN_ORACLE = HERE / "hidden_semantic_tests.py"
CANDIDATE_TEST_RUNNER = HERE / "candidate_test_runner.py"
PUBLIC_TEST_PATH = Path("memory-trace/tests/test_trail_decision_edges.py")
FIXTURE_TEST_RUNNER_PATH = Path("RUN_TASK_TESTS.py")
SERVICE_PATH = Path("memory-trace/memory_trace/service.py")
ALLOWED_CHANGED_FILES = frozenset({SERVICE_PATH.as_posix(), PUBLIC_TEST_PATH.as_posix()})
SEMANTIC_GATES = (
    "decision_row_target",
    "focused_membership",
    "entry_edge_set_equality",
    "entry_ref_regression",
    "invalid_ordinal_no_widening",
    "single_decision_d1",
)
ALL_GATES = (*SEMANTIC_GATES, "public_task_tests", "bounded_scope", "candidate_test_discriminates")
PUBLIC_COMMAND = (sys.executable, FIXTURE_TEST_RUNNER_PATH.as_posix())
SCHEMA_VERSION = 5
GRADER_VERSION = "codex-decision-edge-grader-v5"
ORACLE_SCHEMA_VERSION = 1
ORACLE_VERSION = "codex-decision-edge-v3-semantic-v1"
PROTOCOL_REQUIRED_FIELDS = frozenset(
    {
        "context_receipt",
        "memory_evidence_used",
        "rationale_propositions_used",
        "diagnosis",
        "implementation_choice",
        "alternatives_rejected",
        "files_changed",
        "validation",
        "residual_risks",
    }
)
COMMAND_TIMEOUT_SECONDS = 30
OUTCOME_KEYS = frozenset(
    {
        "semantic_safety_pass",
        "visible_behavior_pass",
        "non_projection_pass",
        "robustness_pass",
        "candidate_test_discriminates",
    }
)
PROTOCOL_STATUS_KEYS = frozenset(
    {
        "status",
        "complete",
        "missing_fields",
        "wrong_shape_fields",
        "invalid_fields",
        "detail",
    }
)
ENVIRONMENT_PASSTHROUGH = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "TMPDIR",
)


def _minimal_environment(*, cwd: Path | None = None, pythonpath: bool = False) -> dict[str, str]:
    """Build a bounded subprocess environment without Python/Git redirections."""

    environment = {name: os.environ[name] for name in ENVIRONMENT_PASSTHROUGH if name in os.environ}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if pythonpath:
        if cwd is None:
            raise ValueError("candidate cwd is required for PYTHONPATH")
        environment["PYTHONPATH"] = os.pathsep.join((str(cwd / "memory-trace"), str(cwd)))
    return environment


def _git(candidate: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=candidate,
        capture_output=True,
        check=check,
        env=_minimal_environment(),
    )


def assess_baseline(candidate: Path, expected_commit: str | None) -> dict[str, Any]:
    """Verify the dispatched fixture identity before any archive is created."""

    base = {
        "status": "error",
        "expected_commit": expected_commit,
        "actual_commit": None,
        "expected_tree": None,
        "actual_tree": None,
        "detail": "",
    }
    if not expected_commit:
        base["detail"] = "expected prepared fixture commit is required"
        return base
    exists = _git(candidate, "cat-file", "-e", f"{expected_commit}^{{commit}}", check=False)
    if exists.returncode != 0:
        base["detail"] = "expected prepared fixture commit is absent from candidate repository"
        return base
    actual_commit = _git(candidate, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    expected_tree = _git(candidate, "rev-parse", f"{expected_commit}^{{tree}}").stdout.decode("ascii").strip()
    actual_tree = _git(candidate, "rev-parse", "HEAD^{tree}").stdout.decode("ascii").strip()
    base.update(
        {
            "actual_commit": actual_commit,
            "expected_tree": expected_tree,
            "actual_tree": actual_tree,
        }
    )
    if actual_commit != expected_commit or actual_tree != expected_tree:
        base["detail"] = "candidate HEAD/tree differs from the dispatched prepared fixture"
        return base
    base.update({"status": "pass", "detail": "candidate HEAD and tree match expected fixture"})
    return base


def changed_paths(candidate: Path) -> set[str]:
    """Return tracked and untracked candidate delta paths relative to its HEAD."""

    tracked = _git(candidate, "diff", "--name-only", "HEAD", "--").stdout.decode(
        "utf-8", errors="surrogateescape"
    )
    untracked = _git(candidate, "ls-files", "--others", "--exclude-standard").stdout.decode(
        "utf-8", errors="surrogateescape"
    )
    return {Path(line).as_posix() for line in (*tracked.splitlines(), *untracked.splitlines()) if line}


def assess_scope(paths: set[str]) -> dict[str, Any]:
    unexpected = sorted(paths - ALLOWED_CHANGED_FILES)
    return {
        "status": "pass" if not unexpected else "fail",
        "detail": "only allowed candidate paths changed" if not unexpected else "unexpected changed paths",
        "changed_files": sorted(paths),
        "allowed_changed_files": sorted(ALLOWED_CHANGED_FILES),
        "unexpected_changed_files": unexpected,
    }


def assess_protocol(payload: Any) -> dict[str, Any]:
    """Assess the task's final evidence object without affecting correctness."""

    base = {
        "status": "not_assessed",
        "complete": None,
        "missing_fields": sorted(PROTOCOL_REQUIRED_FIELDS),
        "wrong_shape_fields": [],
        "invalid_fields": [],
        "detail": "no protocol payload supplied",
    }
    if payload is None:
        return base
    if not isinstance(payload, dict):
        return {
            **base,
            "status": "incomplete",
            "complete": False,
            "detail": "protocol payload is not a JSON object",
        }
    missing = sorted(PROTOCOL_REQUIRED_FIELDS - set(payload))
    list_fields = (
        "memory_evidence_used",
        "rationale_propositions_used",
        "alternatives_rejected",
        "files_changed",
        "residual_risks",
    )
    wrong_shapes = [name for name in list_fields if name in payload and not isinstance(payload[name], list)]
    if "validation" in payload and not isinstance(payload["validation"], list):
        wrong_shapes.append("validation")
    invalid: list[str] = []
    for name in ("context_receipt", "diagnosis", "implementation_choice"):
        if name in payload and (not isinstance(payload[name], str) or not payload[name].strip()):
            invalid.append(name)
    for name in list_fields:
        value = payload.get(name)
        if isinstance(value, list) and (
            not value or any(not isinstance(item, str) or not item.strip() for item in value)
        ):
            invalid.append(name)
    validation = payload.get("validation")
    if isinstance(validation, list):
        if not validation:
            invalid.append("validation")
        for item in validation:
            if not isinstance(item, dict) or set(item) != {"command", "result"}:
                invalid.append("validation")
                break
            if any(not isinstance(item[key], str) or not item[key].strip() for key in ("command", "result")):
                invalid.append("validation")
                break
    wrong_shapes = sorted(set(wrong_shapes))
    invalid = sorted(set(invalid))
    complete = not missing and not wrong_shapes and not invalid
    detail = "all required final-evidence fields present" if complete else "missing or malformed fields"
    return {
        "status": "complete" if complete else "incomplete",
        "complete": complete,
        "missing_fields": missing,
        "wrong_shape_fields": wrong_shapes,
        "invalid_fields": invalid,
        "detail": detail,
    }


def _safe_extract_archive(candidate: Path, destination: Path) -> None:
    archive_path = destination.parent / f"{destination.name}.tar"
    with archive_path.open("wb") as handle:
        result = subprocess.run(
            ["git", "archive", "--format=tar", "HEAD"],
            cwd=candidate,
            stdout=handle,
            stderr=subprocess.PIPE,
            check=False,
            env=_minimal_environment(),
        )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    destination.mkdir()
    root = destination.resolve()
    with tarfile.open(archive_path, "r:") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe archive member: {member.name}")
            if member.issym() or member.islnk():
                raise RuntimeError(f"archive link is not allowed: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f"archive member has no bytes: {member.name}")
                with target.open("xb") as handle:
                    shutil.copyfileobj(source, handle)
            else:
                raise RuntimeError(f"unsupported archive member: {member.name}")
    archive_path.unlink()


def _overlay_delta(candidate: Path, destination: Path, paths: set[str]) -> None:
    for relative in sorted(paths):
        source = candidate / relative
        target = destination / relative
        if source.is_symlink():
            raise RuntimeError(f"candidate symlink is not allowed: {relative}")
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        elif not source.exists():
            target.unlink(missing_ok=True)
        else:
            raise RuntimeError(f"unsupported candidate path: {relative}")


def _external_copies(
    candidate: Path,
    root: Path,
    paths: set[str],
    *,
    pristine_snapshot: Path | None = None,
) -> tuple[Path, Path]:
    pristine = root / "pristine"
    patched = root / "candidate"
    if pristine_snapshot is None:
        _safe_extract_archive(candidate, pristine)
    else:
        shutil.copytree(pristine_snapshot, pristine)
    shutil.copytree(pristine, patched)
    _overlay_delta(candidate, patched, paths)
    return pristine, patched


def _run(
    command: tuple[str, ...] | list[str],
    cwd: Path,
    *,
    pythonpath: bool = False,
    output_limit: int | None = 4000,
) -> dict[str, Any]:
    environment = _minimal_environment(cwd=cwd, pythonpath=pythonpath)
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "returncode": None,
            "timed_out": True,
            "stdout": (error.stdout or b"").decode("utf-8", errors="replace")[-4000:],
            "stderr": (error.stderr or b"").decode("utf-8", errors="replace")[-4000:],
        }
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if output_limit is not None:
        stdout = stdout[-output_limit:]
        stderr = stderr[-output_limit:]
    return {
        "returncode": completed.returncode,
        "timed_out": False,
        "stdout": stdout,
        "stderr": stderr,
    }


def _run_hidden_oracle(candidate_copy: Path) -> dict[str, dict[str, Any]]:
    execution = _run(
        [sys.executable, str(HIDDEN_ORACLE)],
        candidate_copy,
        pythonpath=True,
        output_limit=None,
    )
    try:
        if execution["timed_out"] or execution["returncode"] != 0:
            raise ValueError("hidden oracle did not exit successfully")
        payload = json.loads(execution["stdout"])
        if payload.get("schema_version") != ORACLE_SCHEMA_VERSION:
            raise ValueError("unexpected hidden oracle schema")
        if payload.get("oracle_version") != ORACLE_VERSION:
            raise ValueError("unexpected hidden oracle version")
        observed = payload["gates"]
        if set(observed) != set(SEMANTIC_GATES):
            raise ValueError("hidden oracle gate set changed")
        return observed
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        detail = (
            f"hidden oracle execution error: {error}; returncode={execution['returncode']}; "
            f"stdout={execution['stdout']!r}; stderr={execution['stderr']!r}"
        )
        return {gate: {"status": "error", "detail": detail} for gate in SEMANTIC_GATES}


def _unittest_count(output: str) -> int | None:
    matches = re.findall(r"Ran\s+(\d+)\s+tests?", output)
    return int(matches[-1]) if matches else None


def _public_gate(candidate_copy: Path) -> dict[str, Any]:
    execution = _run(PUBLIC_COMMAND, candidate_copy, pythonpath=True)
    combined = execution["stdout"] + "\n" + execution["stderr"]
    count = _unittest_count(combined)
    passed = (
        not execution["timed_out"]
        and execution["returncode"] == 0
        and count is not None
        and count > 0
    )
    return {
        "status": "pass" if passed else "fail",
        "detail": f"public task command ran {count if count is not None else 'unknown'} tests",
        "command": "python RUN_TASK_TESTS.py",
        "returncode": execution["returncode"],
        "timed_out": execution["timed_out"],
        "test_count": count,
        "output_tail": combined[-4000:],
    }


def _contains_actual_test_code(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "candidate test delta is absent"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        return False, f"candidate test delta is not parseable Python: {error}"
    tampering = _runner_tamper_violations(tree)
    if tampering:
        return False, "candidate test delta contains prohibited runner tampering: " + "; ".join(tampering)
    tests = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test")]
    assertions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assert)
        or (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and (node.func.attr.startswith("assert") or node.func.attr == "fail")
        )
    ]
    if not tests or not assertions:
        return False, "candidate delta must contain a test function and an assertion"
    return True, f"candidate delta contains {len(tests)} test function(s) and {len(assertions)} assertion(s)"


def _root_name(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _runner_tamper_violations(tree: ast.AST) -> list[str]:
    """Reject ordinary monkeypatch/introspection patterns aimed at the runner."""

    unittest_roots = {"unittest"}
    unittest_symbols: set[str] = set()
    sys_roots = {"sys"}
    sys_modules_symbols: set[str] = set()
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                if alias.name == "unittest":
                    unittest_roots.add(bound)
                elif alias.name == "sys":
                    sys_roots.add(bound)
                elif alias.name == "__main__":
                    violations.append(f"line {node.lineno}: import __main__")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__main__":
                violations.append(f"line {node.lineno}: import from __main__")
            elif node.module == "unittest":
                unittest_symbols.update(alias.asname or alias.name for alias in node.names)
            elif node.module == "sys":
                for alias in node.names:
                    if alias.name == "modules":
                        sys_modules_symbols.add(alias.asname or alias.name)

    def infrastructure(node: ast.AST) -> bool:
        root = _root_name(node)
        if root in unittest_roots or root in unittest_symbols:
            return True
        return bool(root and any(word in root.lower() for word in ("result", "suite", "loader")))

    mutation_targets: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            mutation_targets.extend(targets)
        elif isinstance(node, ast.Delete):
            mutation_targets.extend(node.targets)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
                violations.append(f"line {node.lineno}: {node.func.id}()")
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in {"setattr", "delattr"}
                and node.args
                and infrastructure(node.args[0])
            ):
                violations.append(f"line {node.lineno}: {node.func.id} runner infrastructure")
        if isinstance(node, ast.Attribute):
            root = _root_name(node)
            if root in sys_roots and node.attr == "modules":
                violations.append(f"line {node.lineno}: sys.modules access")
        elif isinstance(node, ast.Name) and node.id in sys_modules_symbols:
            violations.append(f"line {node.lineno}: sys.modules alias access")

    for target in mutation_targets:
        for nested in ast.walk(target):
            if isinstance(nested, ast.Attribute) and infrastructure(nested):
                violations.append(f"line {getattr(nested, 'lineno', '?')}: mutate runner infrastructure")
    return sorted(set(violations))


def _candidate_test_gate(candidate: Path, pristine: Path, patched: Path, paths: set[str]) -> dict[str, Any]:
    if PUBLIC_TEST_PATH.as_posix() not in paths:
        return {"status": "fail", "detail": "candidate did not author the task-named test module"}
    actual, actual_detail = _contains_actual_test_code(candidate / PUBLIC_TEST_PATH)
    if not actual:
        return {"status": "fail", "detail": actual_detail}
    test_only = pristine.parent / "test-delta-on-pristine"
    shutil.copytree(pristine, test_only)
    _overlay_delta(candidate, test_only, {PUBLIC_TEST_PATH.as_posix()})
    pristine_result = _run_candidate_test_runner(test_only)
    candidate_result = _run_candidate_test_runner(patched)
    test_files_identical = (test_only / PUBLIC_TEST_PATH).read_bytes() == (
        patched / PUBLIC_TEST_PATH
    ).read_bytes()
    return _assess_discrimination_results(
        pristine_result,
        candidate_result,
        detail=actual_detail,
        test_files_identical=test_files_identical,
    )


def _valid_runner_payload(payload: Any) -> bool:
    required = {
        "schema_version",
        "runner_version",
        "status",
        "discovered_ids",
        "testsRun",
        "failures",
        "errors",
        "skipped",
        "load_error",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        return False
    if payload["schema_version"] != 1 or payload["runner_version"] != "codex-candidate-unittest-runner-v2":
        return False
    if payload["status"] not in {"ok", "error"}:
        return False
    if not isinstance(payload["testsRun"], int) or isinstance(payload["testsRun"], bool):
        return False
    if payload["testsRun"] < 0:
        return False
    if not isinstance(payload["discovered_ids"], list) or any(
        not isinstance(item, str) or not item for item in payload["discovered_ids"]
    ):
        return False
    if payload["discovered_ids"] != sorted(set(payload["discovered_ids"])):
        return False
    for field in ("failures", "errors"):
        if not isinstance(payload[field], list) or any(
            not isinstance(item, dict)
            or set(item) != {"id", "detail"}
            or not isinstance(item["id"], str)
            or not isinstance(item["detail"], str)
            for item in payload[field]
        ):
            return False
    if not isinstance(payload["skipped"], list) or any(
        not isinstance(item, dict)
        or set(item) != {"id", "reason"}
        or not isinstance(item["id"], str)
        or not isinstance(item["reason"], str)
        for item in payload["skipped"]
    ):
        return False
    if payload["status"] == "ok" and payload["load_error"] is not None:
        return False
    if payload["status"] == "error" and (
        not isinstance(payload["load_error"], dict)
        or set(payload["load_error"]) != {"type", "detail"}
        or any(not isinstance(payload["load_error"][key], str) for key in ("type", "detail"))
    ):
        return False
    return True


def _run_candidate_test_runner(candidate_copy: Path) -> dict[str, Any]:
    execution = _run(
        [sys.executable, str(CANDIDATE_TEST_RUNNER), str(candidate_copy / PUBLIC_TEST_PATH)],
        candidate_copy,
        pythonpath=True,
        output_limit=None,
    )
    payload: Any = None
    if not execution["timed_out"] and execution["returncode"] == 0:
        try:
            payload = json.loads(execution["stdout"])
        except json.JSONDecodeError:
            payload = None
    return {
        "process_ok": not execution["timed_out"] and execution["returncode"] == 0,
        "timed_out": execution["timed_out"],
        "returncode": execution["returncode"],
        "runner_schema_ok": _valid_runner_payload(payload),
        "payload": payload,
        "stdout": execution["stdout"][-4000:],
        "stderr": execution["stderr"][-4000:],
    }


def _assess_discrimination_results(
    pristine_result: dict[str, Any],
    candidate_result: dict[str, Any],
    *,
    detail: str = "candidate test execution",
    test_files_identical: bool = True,
) -> dict[str, Any]:
    """Assess only runner-owned discovery and unittest result events."""

    runner_ok = all(
        result.get("process_ok") and result.get("runner_schema_ok")
        for result in (pristine_result, candidate_result)
    )
    pristine = pristine_result.get("payload") if runner_ok else None
    candidate = candidate_result.get("payload") if runner_ok else None
    suite_equal = bool(
        test_files_identical
        and runner_ok
        and pristine["status"] == "ok"
        and candidate["status"] == "ok"
        and pristine["discovered_ids"]
        and pristine["discovered_ids"] == candidate["discovered_ids"]
        and pristine["testsRun"] == candidate["testsRun"] == len(pristine["discovered_ids"])
    )
    discriminates = bool(
        suite_equal
        and len(pristine["failures"]) >= 1
        and not pristine["errors"]
        and not candidate["failures"]
        and not candidate["errors"]
    )
    return {
        "status": "pass" if discriminates else "fail",
        "detail": detail,
        "runner_processes_and_schemas_ok": runner_ok,
        "test_files_identical": test_files_identical,
        "identical_nonempty_suite": suite_equal,
        "pristine": pristine_result,
        "candidate": candidate_result,
    }


def _oracle_sha256() -> str:
    return hashlib.sha256(HIDDEN_ORACLE.read_bytes()).hexdigest()


def _candidate_runner_sha256() -> str:
    return hashlib.sha256(CANDIDATE_TEST_RUNNER.read_bytes()).hexdigest()


def validate_report_schema(report: dict[str, Any]) -> None:
    """Fail closed if a refactor changes the frozen scoring JSON shape."""

    required = {
        "schema_version",
        "grader_version",
        "instrument",
        "status",
        "ready_for_scoring",
        "baseline_integrity",
        "candidate",
        "oracle",
        "candidate_test_runner",
        "gates",
        "outcomes",
        "protocol",
    }
    if set(report) != required:
        raise ValueError(f"grader report keys changed: {sorted(report)}")
    if report["schema_version"] != SCHEMA_VERSION or report["grader_version"] != GRADER_VERSION:
        raise ValueError("grader report version changed")
    if tuple(report["gates"]) != ALL_GATES:
        raise ValueError("grader gate order or membership changed")
    if report["status"] not in {"pass", "fail", "error"}:
        raise ValueError("invalid grader status")
    if report["baseline_integrity"].get("status") not in {"pass", "error"}:
        raise ValueError("invalid baseline integrity status")
    for name, gate in report["gates"].items():
        if not isinstance(gate, dict) or gate.get("status") not in {"pass", "fail", "error"}:
            raise ValueError(f"invalid gate status: {name}")
    if set(report["outcomes"]) != OUTCOME_KEYS or any(
        not isinstance(value, bool) for value in report["outcomes"].values()
    ):
        raise ValueError("invalid outcome shape")
    if set(report["protocol"]) != PROTOCOL_STATUS_KEYS:
        raise ValueError("invalid protocol shape")
    if report["protocol"]["status"] not in {"complete", "incomplete", "not_assessed"}:
        raise ValueError("invalid protocol status")
    if report["protocol"]["status"] == "not_assessed":
        if report["protocol"]["complete"] is not None:
            raise ValueError("unassessed protocol must use complete=null")
    elif not isinstance(report["protocol"]["complete"], bool):
        raise ValueError("assessed protocol completeness must be boolean")


def _error_report(
    candidate: Path,
    baseline: dict[str, Any],
    protocol_payload: Any,
) -> dict[str, Any]:
    detail = f"grading rejected before archive: {baseline['detail']}"
    report = {
        "schema_version": SCHEMA_VERSION,
        "grader_version": GRADER_VERSION,
        "instrument": "codex-decision-edge-v3",
        "status": "error",
        "ready_for_scoring": False,
        "baseline_integrity": baseline,
        "candidate": {
            "path": str(candidate),
            "baseline_commit": baseline.get("actual_commit"),
        },
        "oracle": {
            "path_scope": "external-to-candidate",
            "version": ORACLE_VERSION,
            "sha256": _oracle_sha256(),
        },
        "candidate_test_runner": {
            "path_scope": "external-to-candidate",
            "version": "codex-candidate-unittest-runner-v2",
            "sha256": _candidate_runner_sha256(),
        },
        "gates": {
            name: {"status": "error", "detail": detail, "not_run": True}
            for name in ALL_GATES
        },
        "outcomes": {name: False for name in OUTCOME_KEYS},
        "protocol": assess_protocol(protocol_payload),
    }
    validate_report_schema(report)
    return report


def grade_candidate(
    candidate: Path,
    *,
    expected_baseline: str | None,
    protocol_payload: Any = None,
    _qualification_pristine_snapshot: Path | None = None,
) -> dict[str, Any]:
    candidate = candidate.resolve()
    baseline = assess_baseline(candidate, expected_baseline)
    if baseline["status"] != "pass":
        return _error_report(candidate, baseline, protocol_payload)
    paths = changed_paths(candidate)
    scope = assess_scope(paths)
    gates: dict[str, dict[str, Any]] = {"bounded_scope": scope}
    with tempfile.TemporaryDirectory(prefix="codex-dedge-grade-") as temporary:
        pristine, patched = _external_copies(
            candidate,
            Path(temporary),
            paths,
            pristine_snapshot=_qualification_pristine_snapshot,
        )
        gates.update(_run_hidden_oracle(patched))
        gates["public_task_tests"] = _public_gate(patched)
        gates["candidate_test_discriminates"] = _candidate_test_gate(
            candidate, pristine, patched, paths
        )
    all_pass = all(gates[name]["status"] == "pass" for name in ALL_GATES)
    visible = all(gates[name]["status"] == "pass" for name in ("decision_row_target", "focused_membership"))
    non_projection = gates["entry_edge_set_equality"]["status"] == "pass"
    robustness = all(
        gates[name]["status"] == "pass"
        for name in ("invalid_ordinal_no_widening", "single_decision_d1")
    )
    operational_error = any(gate["status"] == "error" for gate in gates.values())
    report = {
        "schema_version": SCHEMA_VERSION,
        "grader_version": GRADER_VERSION,
        "instrument": "codex-decision-edge-v3",
        "status": "error" if operational_error else ("pass" if all_pass else "fail"),
        "ready_for_scoring": not operational_error,
        "baseline_integrity": baseline,
        "candidate": {
            "path": str(candidate),
            "baseline_commit": baseline["actual_commit"],
        },
        "oracle": {
            "path_scope": "external-to-candidate",
            "version": ORACLE_VERSION,
            "sha256": _oracle_sha256(),
        },
        "candidate_test_runner": {
            "path_scope": "external-to-candidate",
            "version": "codex-candidate-unittest-runner-v2",
            "sha256": _candidate_runner_sha256(),
        },
        "gates": {name: gates[name] for name in ALL_GATES},
        "outcomes": {
            "semantic_safety_pass": all_pass,
            "visible_behavior_pass": visible,
            "non_projection_pass": non_projection,
            "robustness_pass": robustness,
            "candidate_test_discriminates": gates["candidate_test_discriminates"]["status"] == "pass",
        },
        "protocol": assess_protocol(protocol_payload),
    }
    validate_report_schema(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    baseline_group = parser.add_mutually_exclusive_group(required=True)
    baseline_group.add_argument("--expected-baseline", help="prepared fixture commit expected at HEAD")
    baseline_group.add_argument("--public-manifest", type=Path, help="condition-free run manifest")
    parser.add_argument("--subject-id", help="subject key when --public-manifest is used")
    parser.add_argument("--protocol-json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = None
    if args.protocol_json:
        try:
            payload = json.loads(args.protocol_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            payload = {"_protocol_load_error": str(error)}
    expected_baseline = args.expected_baseline
    if args.public_manifest:
        if not args.subject_id:
            parser.error("--subject-id is required with --public-manifest")
        try:
            manifest = json.loads(args.public_manifest.read_text(encoding="utf-8"))
            expected_baseline = manifest["subjects"][args.subject_id]["fixture_commit"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            parser.error(f"could not resolve expected fixture commit from public manifest: {error}")
    elif args.subject_id:
        parser.error("--subject-id is valid only with --public-manifest")
    report = grade_candidate(
        args.candidate,
        expected_baseline=expected_baseline,
        protocol_payload=payload,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
