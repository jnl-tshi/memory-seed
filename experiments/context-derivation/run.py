"""Launch one preregistered ADR-context subject run.

This is deliberately an execution harness, not a scorer: it preserves the raw
stream and records every configuration/isolation signal needed to judge a run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
RUNS = HERE / "runs"
TASKS = HERE / "tasks"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT))
import broker as mcp_broker  # noqa: E402
from contracts import ARMS, RUN_SCHEMA, SCHEDULE_SEED, answer_template, fingerprint, live_execution_approved, live_pin_matches, live_tasks_match, require_schema  # noqa: E402

INTERACTIVE_ARMS = frozenset({"search-mcp", "adr-mcp-workflow"})
FIXED_ARMS = frozenset(ARMS) - INTERACTIVE_ARMS
APPROVAL_SMOKE_ARM = "approval-smoke"
MCP_ARMS = INTERACTIVE_ARMS | frozenset({APPROVAL_SMOKE_ARM})
RUN_ARMS = tuple((*ARMS, APPROVAL_SMOKE_ARM))
SMOKE_TASK_ID = "CTX-01"
SMOKE_ARM = "adr-mcp-workflow"
SMOKE_REPETITION = 1
# A stable, machine-local marker.  It deliberately contains no credential and is
# never removed by this harness: the smoke is an approval-consuming observation.
SMOKE_CLAIM_PATH = Path(tempfile.gettempdir()) / "memory-seed-context-derivation-ctx-01-adr-mcp-workflow-r1.claim"
APPROVAL_SMOKE_TASK_ID = "CTX-01"
APPROVAL_SMOKE_REPETITION = 1
APPROVAL_SMOKE_CLAIM_PATH = Path(tempfile.gettempdir()) / "memory-seed-context-derivation-ctx-01-approval-smoke-r1.claim"
APPROVAL_SMOKE_LIVE_PIN_EFFORT = "medium"
DIRECT_FS_RE = re.compile(
    r"(?:\bread(?:_file)?\b|\bcat\b|\bsed\b|\brg\b|Get-Content|type\s).{0,160}"
    r"(?:\.memory-seed|\bgold(?:\.json)?\b|\btasks?\b|preregistration|context-derivation|\badr)",
    re.I,
)


def parent_fingerprint() -> dict[str, Any]:
    """Small stable proof that the parent memory store was not touched."""
    root = REPO_ROOT / ".memory-seed"
    files = sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(root)).replace("\\", "/").encode())
        digest.update(path.read_bytes())
    return {"files": len(files), "bytes": sum(p.stat().st_size for p in files), "fingerprint": "sha256:" + digest.hexdigest()}


def tree_fingerprint(root: Path) -> dict[str, Any]:
    files = sorted(path for path in root.rglob("*") if path.is_file()) if root.exists() else []
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return {"files": len(files), "bytes": sum(path.stat().st_size for path in files), "fingerprint": "sha256:" + digest.hexdigest()}


def _tasks_path(value: str | None) -> Path:
    return Path(value) if value else TASKS / "tasks.json"


def load_task(task_id: str, tasks_path: Path) -> dict[str, Any]:
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    items = data.get("tasks", data) if isinstance(data, dict) else data
    for task in items:
        if task.get("task_id", task.get("id")) == task_id:
            if task.get("schema"):
                require_schema(task, "context-benchmark-task.v1")
            return task
    raise ValueError(f"unknown task {task_id!r}")


def _packet(task: dict[str, Any], arm: str) -> str:
    packets = task.get("packets", {})
    packet = packets.get(arm, task.get(f"{arm}_packet", task.get("packet", "")))
    return str(packet)


def subject_prompt(task: dict[str, Any], arm: str) -> str:
    if arm == APPROVAL_SMOKE_ARM:
        return (
            "Call memory_adrs_list exactly once with an empty arguments object. "
            "Do not call any other tool. Do not retry. Do not modify files. "
            "After that call, return only this JSON object: {\"smoke\":\"approval-mode\"}."
        )
    prompt = (
        "Return only one JSON object. Do not modify files. Its required exact shape is "
        + json.dumps(answer_template(), separators=(",", ":"))
        + '. adr_statuses maps each reported ADR ID to accepted, proposed, rejected, '
        'superseded, or empty. lineage_edges may contain only evolves/replaces; put '
        'supporting related relationships in related_edges. No extra keys. '
        "\n\nQuestion:\n" + task["question"] + "\n"
    )
    if arm in FIXED_ARMS:
        prompt += "\nEvidence packet (the only available corpus):\n" + _packet(task, arm)
    else:
        prompt += "\nUse only the experiment-local read-only MCP tools to inspect the fixture."
    return prompt


def _wrapper_command(arm: str, fixture: Path) -> list[str]:
    return [sys.executable, str(HERE / "mcp_wrapper.py"), "--arm", arm, "--fixture", str(fixture)]


def _claude_mcp_config(run_dir: Path, arm: str, fixture: Path) -> Path:
    config = run_dir / "mcp.json"
    config.write_text(json.dumps({"mcpServers": {"context-fixture": {
        "command": _wrapper_command(arm, fixture)[0], "args": _wrapper_command(arm, fixture)[1:]}}}), encoding="utf-8")
    return config


def _codex_isolation_overrides(run_dir: Path, fixture: Path | None) -> list[str]:
    values = [
        'default_permissions="context_subject"',
        'permissions.context_subject.description="ADR benchmark subject isolation"',
        'permissions.context_subject.filesystem={":root"="deny",":minimal"="read",'
        '":workspace_roots"={"."="read"}}',
        'permissions.context_subject.network.enabled=false',
        'shell_environment_policy.inherit="none"',
        'features.shell_tool=false',
        'features.apps=false',
        'web_search="disabled"',
    ]
    return [part for value in values for part in ("-c", value)]


def subject_isolation(agent: str) -> str:
    return "claude-builtins-disabled" if agent == "claude" else "codex-deny-read-permission-profile"


def codex_interactive_ready() -> bool:
    """Keep the scored matrix held until its separate live execution approval."""
    return False


def scored_execution_ready() -> bool:
    """Fail closed until a separate implementation removes this test seam."""
    return False


def codex_broker_capable() -> bool:
    """Implementation preflight used by provider-free broker tests."""
    return mcp_broker.loopback_capable()


def subject_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    allowed = {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "OS",
        "TEMP", "TMP", "TMPDIR", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
        "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES",
        "PROGRAMFILES(X86)", "COMMONPROGRAMFILES", "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE", "USERNAME", "LANG", "LC_ALL", "CODEX_HOME",
    }
    environment = {name: value for name, value in os.environ.items() if name.upper() in allowed}
    if extra:
        environment.update(extra)
    return environment


def redact_output(text: str, *, secrets: tuple[str, ...] = ()) -> str:
    redacted = text
    secret_name = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH)", re.I)
    for name, value in os.environ.items():
        if secret_name.search(name) and len(value) >= 8:
            redacted = redacted.replace(value, f"<redacted-env:{name}>")
    for value in secrets:
        if value:
            redacted = redacted.replace(value, "<redacted-broker-token>")
    redacted = re.sub(r"\b(?:sk|sess|oauth)-[A-Za-z0-9_-]{12,}\b", "<redacted-token>", redacted)
    redacted = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*", "Bearer <redacted-token>", redacted)
    return redacted


def _sanitize_approval_smoke_arguments(text: str) -> str:
    """Retain approval-mode tool names while removing their raw argument payloads."""
    def sanitize(value: Any) -> Any:
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if not isinstance(value, dict):
            return value
        is_mcp_call = str(value.get("type", "")) == "mcp_tool_call"
        return {
            key: "<redacted-mcp-arguments>" if is_mcp_call and key in {"arguments", "params"} else sanitize(item)
            for key, item in value.items()
        }

    lines: list[str] = []
    for line in text.splitlines():
        try:
            lines.append(json.dumps(sanitize(json.loads(line)), ensure_ascii=False, separators=(",", ":")))
        except json.JSONDecodeError:
            lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def installed_cli_version(agent: str) -> tuple[str, str]:
    executable = "claude" if agent == "claude" else (shutil.which("codex") or "codex")
    completed = subprocess.run(
        [executable, "--version"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30, env=subject_environment(),
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{agent} --version failed: {redact_output(completed.stderr).strip()}")
    raw = completed.stdout.strip()
    if agent == "claude":
        match = re.match(r"(\d+\.\d+\.\d+)", raw)
        normalized = match.group(1) if match else raw
    else:
        normalized = raw
    return raw, normalized


def build_command(
    agent: str,
    run_dir: Path,
    prompt: str,
    *,
    arm: str,
    fixture: Path | None,
    model: str | None,
    effort: str | None,
    broker_url: str | None = None,
) -> list[str]:
    interactive = arm in MCP_ARMS
    if agent == "claude":
        command = [
            "claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--tools", "", "--disable-slash-commands", "--no-session-persistence",
            "--disallowed-tools", "Bash,Read,Edit,Write,Glob,Grep,NotebookEdit,WebFetch,WebSearch,Task",
            "--no-chrome", "--permission-mode", "dontAsk", "--setting-sources", "",
        ]
        if interactive:
            allowed = ",".join(
                f"mcp__context-fixture__{name}"
                for name in __import__("mcp_wrapper").allowed_names(arm)
            )
            command += [
                "--mcp-config", str(_claude_mcp_config(run_dir, arm, fixture or run_dir)),
                "--strict-mcp-config", "--allowed-tools", allowed,
            ]
        else:
            command += ["--safe-mode"]
        if model: command += ["--model", model]
        return command
    if agent == "codex":
        if interactive and not broker_url:
            raise RuntimeError("Codex interactive arms require a running harness-owned broker")
        exe = shutil.which("codex") or shutil.which("codex.cmd") or "codex"
        command = [
            exe, "exec", "--json", "-C", str(run_dir), "-o", "RUN_LAST_MESSAGE.txt",
            "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
            "--ignore-rules", "--strict-config", "-c", 'approval_policy="never"',
        ]
        command += _codex_isolation_overrides(run_dir, fixture)
        command += (
            mcp_broker.codex_config_overrides(arm, broker_url)
            if interactive else ["-c", "mcp_servers={}"]
        )
        if effort: command += ["-c", f'model_reasoning_effort="{effort}"']
        if model: command += ["-m", model]
        return command + [prompt]
    raise ValueError(f"unsupported agent {agent!r}")


def _tool_calls(text: str) -> list[str]:
    def normalized(value: Any) -> str:
        name = str(value)
        known = set(__import__("mcp_wrapper").WORKFLOW_TOOLS)
        for candidate in (name, name.rsplit("__", 1)[-1], name.rsplit(".", 1)[-1]):
            if candidate in known:
                return candidate
        return name

    calls: list[str] = []
    for line in text.splitlines():
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        item = event.get("item", {})
        item_type = str(item.get("type", ""))
        if item_type == "mcp_tool_call": calls.append(normalized(item.get("tool", "")))
        elif item_type and any(marker in item_type for marker in ("tool", "command", "file", "function_call", "web_search")):
            calls.append(item_type)
        for block in (event.get("message") or {}).get("content", []):
            if block.get("type") == "tool_use": calls.append(normalized(block.get("name", "")))
    return calls


def _direct_filesystem_retrieval(text: str) -> bool:
    """Inspect tool payloads only, so explanatory prose cannot self-incriminate."""
    for line in text.splitlines():
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        item = event.get("item") or {}
        item_type = str(item.get("type", ""))
        if item_type and any(marker in item_type for marker in ("tool", "command", "file", "function_call")):
            if DIRECT_FS_RE.search(json.dumps(item, ensure_ascii=False)):
                return True
        for block in (event.get("message") or {}).get("content", []):
            if block.get("type") == "tool_use" and DIRECT_FS_RE.search(json.dumps(block, ensure_ascii=False)):
                return True
    return False


def _usage(text: str) -> dict[str, Any]:
    """Extract either CLI's token spelling from the JSONL stream, if present."""
    values: dict[str, Any] = {"input_tokens": None, "output_tokens": None, "cost_usd": None}
    for line in text.splitlines():
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        usage = event.get("usage") or (event.get("response") or {}).get("usage") or {}
        values["input_tokens"] = usage.get("input_tokens", usage.get("prompt_tokens", values["input_tokens"]))
        values["output_tokens"] = usage.get("output_tokens", usage.get("completion_tokens", values["output_tokens"]))
        values["cost_usd"] = usage.get("cost_usd", usage.get("cost", values["cost_usd"]))
    return values


def _make_immutable(path: Path) -> None:
    """Fixture copies are corpus artifacts; subjects have no writable fixture path."""
    for item in sorted(path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try: item.chmod(item.stat().st_mode & ~stat.S_IWRITE)
        except OSError: pass
    try: path.chmod(path.stat().st_mode & ~stat.S_IWRITE)
    except OSError: pass


def _remove_run_dir(path: Path) -> None:
    if not path.exists():
        return
    for item in sorted(path.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        try: item.chmod(item.stat().st_mode | stat.S_IWRITE)
        except OSError: pass
    try: path.chmod(path.stat().st_mode | stat.S_IWRITE)
    except OSError: pass
    shutil.rmtree(path, ignore_errors=True)


def _remove_subject_configs(path: Path) -> None:
    config = path / "mcp.json"
    if config.exists():
        config.unlink()


def sanitize_subject_artifacts(
    path: Path, *, secrets: tuple[str, ...] = (), approval_smoke: bool = False,
) -> None:
    """Redact provider-authored files before they enter retained artifacts."""
    final = path / "RUN_LAST_MESSAGE.txt"
    if final.exists():
        text = redact_output(final.read_text(encoding="utf-8", errors="replace"), secrets=secrets)
        final.write_text(
            _sanitize_approval_smoke_arguments(text) if approval_smoke else text,
            encoding="utf-8",
        )


def _temporary_work_dir(run_id: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix=f"context-derivation-{run_id}-")).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return path
    _remove_run_dir(path)
    raise RuntimeError("refusing to execute a subject in a temporary directory inside the repository")


def _move_finalized_artifacts(work_dir: Path, final_dir: Path) -> Path:
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    if final_dir.exists():
        raise FileExistsError(final_dir)
    return Path(shutil.move(str(work_dir), str(final_dir)))


def _unscored_smoke_root(value: str) -> Path:
    root = Path(value).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if root == temp_root:
        raise ValueError("unscored smoke output must be a dedicated OS-temporary directory")
    try:
        root.relative_to(temp_root)
    except ValueError as exc:
        raise ValueError("unscored smoke output must be under the OS temporary directory") from exc
    try:
        root.relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("unscored smoke output must be outside the repository")
    if root.exists() and any(root.iterdir()):
        raise ValueError("unscored smoke output directory must be empty")
    return root


def _consume_smoke_claim(
    claim_path: Path | None = None, *, label: str = "Codex broker smoke",
) -> None:
    """Atomically record the one permitted local broker-smoke invocation."""
    claim_path = claim_path or SMOKE_CLAIM_PATH
    try:
        descriptor = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f"the one-shot {label} has already been consumed on this machine") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as claim:
        claim.write("consumed\n")


def _final_answer(run_dir: Path, transcript: str) -> str:
    final = run_dir / "RUN_LAST_MESSAGE.txt"
    if final.exists(): return final.read_text(encoding="utf-8")
    for line in reversed(transcript.splitlines()):
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        if event.get("type") == "result": return str(event.get("result", ""))
        item = event.get("item", {})
        if item.get("type") == "agent_message": return str(item.get("text", ""))
    return ""


def _approval_smoke_final_answer_valid(final: str) -> bool:
    try:
        return json.loads(final) == {"smoke": "approval-mode"}
    except json.JSONDecodeError:
        return False


def classify_failure(*, timed_out: bool, exit_code: int | None, stderr: str, transcript: str) -> str | None:
    haystack = (stderr + "\n" + transcript).lower()
    if timed_out: return "timeout"
    if "rate limit" in haystack or "429" in haystack or "throttl" in haystack: return "provider_throttled"
    if "provider" in haystack and ("unavailable" in haystack or "overload" in haystack): return "provider_outage"
    if exit_code not in (0, None): return "harness_error"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True); parser.add_argument("--arm", required=True, choices=RUN_ARMS)
    parser.add_argument("--agent", required=True, choices=("claude", "codex")); parser.add_argument("--repetition", type=int, required=True)
    parser.add_argument("--model", required=True); parser.add_argument("--cli-version", required=True)
    parser.add_argument("--effort"); parser.add_argument("--timeout", type=int, default=900); parser.add_argument("--tasks"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--owner-approved", action="store_true", help="required before paid/scored execution")
    smoke_output = parser.add_mutually_exclusive_group()
    smoke_output.add_argument(
        "--unscored-smoke-output",
        help="OS-temporary output root for one owner-approved, unscored Codex broker smoke",
    )
    smoke_output.add_argument(
        "--approval-smoke-output",
        help="OS-temporary output root for one owner-approved Codex approval-mode smoke",
    )
    args = parser.parse_args(argv)
    interactive_codex = args.agent == "codex" and args.arm in MCP_ARMS
    smoke_kind: str | None = None
    smoke_output_path: str | None = None
    if args.unscored_smoke_output is not None:
        smoke_kind = "broker"
        smoke_output_path = args.unscored_smoke_output
    elif args.approval_smoke_output is not None:
        smoke_kind = "approval-mode"
        smoke_output_path = args.approval_smoke_output
    if smoke_kind == "broker" and (
        not interactive_codex
        or args.task != SMOKE_TASK_ID
        or args.arm != SMOKE_ARM
        or args.repetition != SMOKE_REPETITION
    ):
        parser.error(
            "--unscored-smoke-output is only valid for Codex CTX-01 "
            "adr-mcp-workflow repetition 1"
        )
    if smoke_kind == "approval-mode" and (
        args.agent != "codex"
        or args.task != APPROVAL_SMOKE_TASK_ID
        or args.arm != APPROVAL_SMOKE_ARM
        or args.repetition != APPROVAL_SMOKE_REPETITION
    ):
        parser.error(
            "--approval-smoke-output is only valid for Codex CTX-01 "
            "approval-smoke repetition 1"
        )
    if not args.dry_run and smoke_kind is None and not scored_execution_ready():
        parser.error("scored subject execution remains blocked pending a separate live approval")
    if not args.dry_run and not args.owner_approved:
        # Check before creating a run directory or copying a fixture, and crucially
        # before either subject CLI can be invoked.
        parser.error("--owner-approved is required for non-dry-run execution")
    if not args.dry_run and not live_execution_approved(HERE):
        parser.error("gold/preregistration approval, a frozen candidate, and pinned live matrix are required")
    if smoke_kind == "approval-mode" and args.effort != "low":
        parser.error("--approval-smoke-output requires --effort low")
    pin_effort = APPROVAL_SMOKE_LIVE_PIN_EFFORT if smoke_kind == "approval-mode" else args.effort
    if not args.dry_run and not live_pin_matches(
        HERE, args.agent, args.model, args.cli_version, pin_effort,
    ):
        parser.error("requested model/CLI version does not match LIVE_MATRIX.json")
    if not args.dry_run and not live_tasks_match(HERE, _tasks_path(args.tasks)):
        parser.error("materialized live tasks do not match LIVE_MATRIX.json")
    observed_cli_raw: str | None = None
    if not args.dry_run:
        observed_cli_raw, observed_cli = installed_cli_version(args.agent)
        if observed_cli != args.cli_version:
            parser.error(
                f"installed {args.agent} CLI {observed_cli!r} does not match frozen pin {args.cli_version!r}"
            )
    smoke_root = _unscored_smoke_root(smoke_output_path) if smoke_output_path else None
    task = load_task(args.task, _tasks_path(args.tasks)); fixture_source = task.get("fixture")
    run_id = f"{args.agent}-{args.task}-{args.arm}-r{args.repetition}-{uuid.uuid4().hex[:10]}"
    run_dir = (smoke_root or RUNS) / run_id
    work_dir = _temporary_work_dir(run_id)
    fixture_parent: Path | None = None
    fixture: Path | None = None
    endpoint: mcp_broker.BrokerEndpoint | None = None
    broker_token = ""
    broker_teardown_verified: bool | None = None
    finalized = False
    try:
        if args.arm in MCP_ARMS:
            if not fixture_source: raise ValueError("interactive arm requires a fixture")
            fixture_source_path = Path(fixture_source)
            if not fixture_source_path.is_absolute():
                fixture_source_path = (HERE / fixture_source_path).resolve()
            mcp_broker.validate_fixture_tree(
                fixture_source_path, require_immutable=False, require_isolated=False,
            )
            if interactive_codex:
                fixture_parent = mcp_broker.isolated_fixture_parent(run_id)
                fixture = fixture_parent / "fixture"
            else:
                fixture = work_dir / "fixture"
            shutil.copytree(fixture_source_path, fixture)
            _make_immutable(fixture)
            mcp_broker.validate_fixture_tree(
                fixture, require_isolated=interactive_codex,
            )
        fixture_before = tree_fingerprint(fixture) if fixture else None
        prompt = subject_prompt(task, args.arm)
        before = parent_fingerprint()
        environment = subject_environment()
        broker_url: str | None = None
        if interactive_codex:
            if args.dry_run:
                broker_url = f"http://{mcp_broker.HOST}:0{mcp_broker.PATH}"
            else:
                endpoint = mcp_broker.localhost_mcp_broker(
                    arm=args.arm, fixture_cwd=fixture or work_dir,
                ).start()
                broker_url = endpoint.url
                broker_token = endpoint.token
                environment = endpoint.inject_environment(environment)
        command = build_command(
            args.agent, work_dir, prompt, arm=args.arm, fixture=fixture,
            model=args.model, effort=args.effort, broker_url=broker_url,
        )
        if args.dry_run:
            manifest = {"schema": RUN_SCHEMA, "run_id": run_id, "task_id": args.task, "arm": args.arm, "agent": args.agent, "repetition": args.repetition, "schedule_seed": SCHEDULE_SEED, "model": args.model, "cli_version": args.cli_version, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "dry_run": True, "scored": False if smoke_root else None, "smoke": smoke_root is not None, "smoke_kind": smoke_kind, "subject_isolation": subject_isolation(args.agent), "command": ["<prompt>" if part == prompt else part for part in command]}
            print(json.dumps(manifest))
            return 0

        started = time.monotonic(); stdout = stderr = ""; exit_code: int | None = None; timed_out = False
        try:
            if smoke_kind == "approval-mode":
                _consume_smoke_claim(APPROVAL_SMOKE_CLAIM_PATH, label="Codex approval-mode smoke")
            elif smoke_root is not None:
                _consume_smoke_claim()
            done = subprocess.run(command, cwd=work_dir, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.timeout)
            stdout = redact_output(done.stdout, secrets=(broker_token,))
            stderr = redact_output(done.stderr, secrets=(broker_token,))
            if smoke_kind == "approval-mode":
                stdout = _sanitize_approval_smoke_arguments(stdout)
                stderr = _sanitize_approval_smoke_arguments(stderr)
            exit_code = done.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = (exc.stdout or "").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = (exc.stderr or "").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stdout = redact_output(stdout, secrets=(broker_token,))
            stderr = redact_output(stderr, secrets=(broker_token,))
            if smoke_kind == "approval-mode":
                stdout = _sanitize_approval_smoke_arguments(stdout)
                stderr = _sanitize_approval_smoke_arguments(stderr)
        except OSError:
            exit_code = -1
            stderr = "harness launch failed"
        finally:
            if endpoint is not None:
                try:
                    endpoint.close()
                    broker_teardown_verified = True
                except mcp_broker.BrokerError:
                    broker_teardown_verified = False
                    exit_code = -1
                    stderr = (stderr + "\nbroker teardown failed").strip()

        sanitize_subject_artifacts(
            work_dir, secrets=(broker_token,), approval_smoke=smoke_kind == "approval-mode",
        )
        _remove_subject_configs(work_dir)
        duration_ms = round((time.monotonic() - started) * 1000)
        (work_dir / "transcript.jsonl").write_text(stdout, encoding="utf-8")
        if stderr: (work_dir / "stderr.log").write_text(stderr, encoding="utf-8")
        calls = _tool_calls(stdout)
        broker_calls = list(endpoint.calls) if endpoint is not None else []
        broker_call_records = list(endpoint.call_records) if endpoint is not None else []
        allowed = set() if args.arm in FIXED_ARMS else set(__import__("mcp_wrapper").allowed_names(args.arm))
        undeclared_tool_calls = sorted((set(calls) | set(broker_calls)) - allowed)
        final = _final_answer(work_dir, stdout); (work_dir / "final_answer.txt").write_text(final, encoding="utf-8")
        after = parent_fingerprint()
        fixture_after = tree_fingerprint(fixture) if fixture else None
        direct_filesystem_retrieval = _direct_filesystem_retrieval(stdout)
        parent_isolated = before == after
        fixture_isolated = fixture_before == fixture_after if fixture else True
        integrity_failures: list[str] = []
        if smoke_root is not None:
            expected_approval_call = {
                "name": "memory_adrs_list", "arguments_exact_empty": True, "succeeded": True,
            }
            if smoke_kind == "approval-mode" and (
                broker_calls != ["memory_adrs_list"] or broker_call_records != [expected_approval_call]
            ):
                integrity_failures.append("approval_smoke_tool_sequence")
            if smoke_kind == "approval-mode" and not _approval_smoke_final_answer_valid(final):
                integrity_failures.append("approval_smoke_final_answer")
            if undeclared_tool_calls: integrity_failures.append("undeclared_tool_call")
            if direct_filesystem_retrieval: integrity_failures.append("direct_filesystem_retrieval")
            if not parent_isolated: integrity_failures.append("parent_memory_store_isolation_failure")
            if not fixture_isolated: integrity_failures.append("fixture_isolation_failure")
            if broker_teardown_verified is not True: integrity_failures.append("broker_teardown_failure")
            if integrity_failures:
                exit_code = -1
                stderr = (stderr + "\nsmoke integrity failure: " + ", ".join(integrity_failures)).strip()
        failure = "smoke_integrity_failure" if integrity_failures else classify_failure(
            timed_out=timed_out, exit_code=exit_code, stderr=stderr, transcript=stdout,
        )
        packet = _packet(task, args.arm) if args.arm in FIXED_ARMS else ""
        refs_by_arm = task.get("included_refs_by_arm") or {}
        tokens_by_arm = task.get("context_token_proxy_by_arm") or {}
        if fixture and interactive_codex:
            shutil.copytree(fixture, work_dir / "fixture")
            _make_immutable(work_dir / "fixture")
        manifest = {"schema": RUN_SCHEMA, "run_id": run_id, "task_id": args.task, "arm": args.arm, "agent": args.agent, "repetition": args.repetition, "schedule_seed": SCHEDULE_SEED, "model": args.model, "cli_version": args.cli_version, "cli_version_observed_raw": observed_cli_raw, "effort": args.effort, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "duration_ms": duration_ms, "exit_code": exit_code, "timed_out": timed_out, "scored": smoke_root is None, "smoke": smoke_root is not None, "smoke_kind": smoke_kind, "transcript": "transcript.jsonl", "final_answer": "final_answer.txt", "interactive_fixture": "fixture" if fixture else None, "fixed_arm_no_fixture": args.arm in FIXED_ARMS, "mcp_enabled": args.arm in MCP_ARMS, "mcp_transport": "streamable_http" if endpoint else ("stdio" if args.arm in MCP_ARMS else None), "broker_teardown_verified": broker_teardown_verified, "broker_tool_calls": broker_calls, "broker_call_records": broker_call_records, "subject_isolation": subject_isolation(args.agent), "included_refs": refs_by_arm.get(args.arm, []), "context_token_proxy": tokens_by_arm.get(args.arm, len(packet.split())), "tool_calls": calls, "undeclared_tool_calls": undeclared_tool_calls, "direct_filesystem_retrieval": direct_filesystem_retrieval, "parent_before": before, "parent_after": after, "parent_isolated": parent_isolated, "fixture_before": fixture_before, "fixture_after": fixture_after, "fixture_isolated": fixture_isolated, "integrity_failures": integrity_failures, "failure_classification": failure, "command": ["<prompt>" if part == prompt else part for part in command], **_usage(stdout)}
        (work_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        _move_finalized_artifacts(work_dir, run_dir)
        finalized = True
        print(json.dumps({"run_id": run_id, "output": str(run_dir), "exit_code": exit_code, "failure_classification": failure, "parent_isolated": before == after, "scored": smoke_root is None}))
        return 0 if exit_code == 0 and not timed_out else 1
    finally:
        if endpoint is not None and broker_teardown_verified is None:
            endpoint.close()
        if fixture_parent is not None:
            _remove_run_dir(fixture_parent)
        if not finalized:
            _remove_run_dir(work_dir)


if __name__ == "__main__": raise SystemExit(main())
