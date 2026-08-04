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
from contracts import ARMS, RUN_SCHEMA, SCHEDULE_SEED, answer_template, fingerprint, live_execution_approved, live_pin_matches, live_tasks_match, require_schema  # noqa: E402

INTERACTIVE_ARMS = frozenset({"search-mcp", "adr-mcp-workflow"})
FIXED_ARMS = frozenset(ARMS) - INTERACTIVE_ARMS
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
        'features.apps=false',
    ]
    return [part for value in values for part in ("-c", value)]


def subject_isolation(agent: str) -> str:
    return "claude-builtins-disabled" if agent == "claude" else "codex-deny-read-permission-profile"


def codex_interactive_ready() -> bool:
    """Remain false until an owner-approved privilege broker is implemented."""
    return False


def subject_environment() -> dict[str, str]:
    allowed = {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "OS",
        "TEMP", "TMP", "TMPDIR", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
        "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES",
        "PROGRAMFILES(X86)", "COMMONPROGRAMFILES", "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE", "USERNAME", "LANG", "LC_ALL", "CODEX_HOME",
    }
    return {name: value for name, value in os.environ.items() if name.upper() in allowed}


def redact_output(text: str) -> str:
    redacted = text
    secret_name = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH)", re.I)
    for name, value in os.environ.items():
        if secret_name.search(name) and len(value) >= 8:
            redacted = redacted.replace(value, f"<redacted-env:{name}>")
    redacted = re.sub(r"\b(?:sk|sess|oauth)-[A-Za-z0-9_-]{12,}\b", "<redacted-token>", redacted)
    redacted = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*", "Bearer <redacted-token>", redacted)
    return redacted


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


def build_command(agent: str, run_dir: Path, prompt: str, *, arm: str, fixture: Path | None, model: str | None, effort: str | None) -> list[str]:
    interactive = arm in INTERACTIVE_ARMS
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
        if interactive:
            raise RuntimeError(
                "Codex interactive arms require an explicitly approved harness-owned broker; "
                "stdio MCP cannot isolate the fixture from subject filesystem tools"
            )
        exe = shutil.which("codex") or shutil.which("codex.cmd") or "codex"
        command = [
            exe, "exec", "--json", "-C", str(run_dir), "-o", "RUN_LAST_MESSAGE.txt",
            "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
            "--ignore-rules", "--strict-config", "-c", 'approval_policy="never"',
        ]
        command += _codex_isolation_overrides(run_dir, fixture)
        command += ["-c", "mcp_servers={}"]
        if effort: command += ["-c", f'model_reasoning_effort="{effort}"']
        if model: command += ["-m", model]
        return command + [prompt]
    raise ValueError(f"unsupported agent {agent!r}")


def _tool_calls(text: str) -> list[str]:
    calls: list[str] = []
    for line in text.splitlines():
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        item = event.get("item", {})
        item_type = str(item.get("type", ""))
        if item_type == "mcp_tool_call": calls.append(str(item.get("tool", "")))
        elif item_type and any(marker in item_type for marker in ("tool", "command", "file", "function_call", "web_search")):
            calls.append(item_type)
        for block in (event.get("message") or {}).get("content", []):
            if block.get("type") == "tool_use": calls.append(str(block.get("name", "")))
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


def _remove_run_dir(path: Path) -> None:
    for item in sorted(path.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        try: item.chmod(item.stat().st_mode | stat.S_IWRITE)
        except OSError: pass
    shutil.rmtree(path, ignore_errors=True)


def _remove_subject_configs(path: Path) -> None:
    config = path / "mcp.json"
    if config.exists():
        config.unlink()


def sanitize_subject_artifacts(path: Path) -> None:
    """Redact provider-authored files before they enter retained artifacts."""
    final = path / "RUN_LAST_MESSAGE.txt"
    if final.exists():
        final.write_text(
            redact_output(final.read_text(encoding="utf-8", errors="replace")),
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
    RUNS.mkdir(parents=True, exist_ok=True)
    if final_dir.exists():
        raise FileExistsError(final_dir)
    return Path(shutil.move(str(work_dir), str(final_dir)))


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


def classify_failure(*, timed_out: bool, exit_code: int | None, stderr: str, transcript: str) -> str | None:
    haystack = (stderr + "\n" + transcript).lower()
    if timed_out: return "timeout"
    if "rate limit" in haystack or "429" in haystack or "throttl" in haystack: return "provider_throttled"
    if "provider" in haystack and ("unavailable" in haystack or "overload" in haystack): return "provider_outage"
    if exit_code not in (0, None): return "harness_error"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True); parser.add_argument("--arm", required=True, choices=ARMS)
    parser.add_argument("--agent", required=True, choices=("claude", "codex")); parser.add_argument("--repetition", type=int, required=True)
    parser.add_argument("--model", required=True); parser.add_argument("--cli-version", required=True)
    parser.add_argument("--effort"); parser.add_argument("--timeout", type=int, default=900); parser.add_argument("--tasks"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--owner-approved", action="store_true", help="required before paid/scored execution")
    args = parser.parse_args(argv)
    if not args.dry_run and not args.owner_approved:
        # Check before creating a run directory or copying a fixture, and crucially
        # before either subject CLI can be invoked.
        parser.error("--owner-approved is required for non-dry-run execution")
    if not args.dry_run and not live_execution_approved(HERE):
        parser.error("gold/preregistration approval, a frozen candidate, and pinned live matrix are required")
    if not args.dry_run and not live_pin_matches(
        HERE, args.agent, args.model, args.cli_version, args.effort,
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
    task = load_task(args.task, _tasks_path(args.tasks)); fixture_source = task.get("fixture")
    run_id = f"{args.agent}-{args.task}-{args.arm}-r{args.repetition}-{uuid.uuid4().hex[:10]}"
    run_dir = RUNS / run_id
    work_dir = _temporary_work_dir(run_id)
    fixture: Path | None = None
    try:
        if args.arm in INTERACTIVE_ARMS:
            if not fixture_source: raise ValueError("interactive arm requires a fixture")
            fixture = Path(fixture_source)
            if not fixture.is_absolute(): fixture = (HERE / fixture).resolve()
            if not fixture.is_dir(): raise ValueError(f"fixture is missing: {fixture}")
            shutil.copytree(fixture, work_dir / "fixture")
            fixture = work_dir / "fixture"
            _make_immutable(fixture)
        fixture_before = tree_fingerprint(fixture) if fixture else None
        prompt = subject_prompt(task, args.arm); before = parent_fingerprint(); command = build_command(args.agent, work_dir, prompt, arm=args.arm, fixture=fixture, model=args.model, effort=args.effort)
    except Exception:
        _remove_run_dir(work_dir)
        raise
    if args.dry_run:
        manifest = {"schema": RUN_SCHEMA, "run_id": run_id, "task_id": args.task, "arm": args.arm, "agent": args.agent, "repetition": args.repetition, "schedule_seed": SCHEDULE_SEED, "model": args.model, "cli_version": args.cli_version, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "dry_run": True, "subject_isolation": subject_isolation(args.agent), "command": ["<prompt>" if part == prompt else part for part in command]}
        print(json.dumps(manifest)); _remove_run_dir(work_dir); return 0
    started = time.monotonic(); stdout = stderr = ""; exit_code: int | None = None; timed_out = False
    try:
        done = subprocess.run(command, cwd=work_dir, env=subject_environment(), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.timeout)
        stdout, stderr, exit_code = redact_output(done.stdout), redact_output(done.stderr), done.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True; stdout = (exc.stdout or "").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""); stderr = (exc.stderr or "").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""); stdout, stderr = redact_output(stdout), redact_output(stderr)
    except OSError as exc:
        exit_code = -1; stderr = f"harness launch failed: {exc}"
    sanitize_subject_artifacts(work_dir)
    _remove_subject_configs(work_dir)
    duration_ms = round((time.monotonic() - started) * 1000)
    (work_dir / "transcript.jsonl").write_text(stdout, encoding="utf-8")
    if stderr: (work_dir / "stderr.log").write_text(stderr, encoding="utf-8")
    calls = _tool_calls(stdout); allowed = set() if args.arm in FIXED_ARMS else set(__import__("mcp_wrapper").allowed_names(args.arm))
    final = _final_answer(work_dir, stdout); (work_dir / "final_answer.txt").write_text(final, encoding="utf-8")
    after = parent_fingerprint(); fixture_after = tree_fingerprint(fixture) if fixture else None; failure = classify_failure(timed_out=timed_out, exit_code=exit_code, stderr=stderr, transcript=stdout)
    packet = _packet(task, args.arm) if args.arm in FIXED_ARMS else ""
    refs_by_arm = task.get("included_refs_by_arm") or {}
    tokens_by_arm = task.get("context_token_proxy_by_arm") or {}
    manifest = {"schema": RUN_SCHEMA, "run_id": run_id, "task_id": args.task, "arm": args.arm, "agent": args.agent, "repetition": args.repetition, "schedule_seed": SCHEDULE_SEED, "model": args.model, "cli_version": args.cli_version, "cli_version_observed_raw": observed_cli_raw, "effort": args.effort, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "duration_ms": duration_ms, "exit_code": exit_code, "timed_out": timed_out, "transcript": "transcript.jsonl", "final_answer": "final_answer.txt", "interactive_fixture": "fixture" if fixture else None, "fixed_arm_no_fixture": args.arm in FIXED_ARMS, "mcp_enabled": args.arm in INTERACTIVE_ARMS, "subject_isolation": subject_isolation(args.agent), "included_refs": refs_by_arm.get(args.arm, []), "context_token_proxy": tokens_by_arm.get(args.arm, len(packet.split())), "tool_calls": calls, "undeclared_tool_calls": sorted(set(calls) - allowed), "direct_filesystem_retrieval": _direct_filesystem_retrieval(stdout), "parent_before": before, "parent_after": after, "parent_isolated": before == after, "fixture_before": fixture_before, "fixture_after": fixture_after, "fixture_isolated": fixture_before == fixture_after if fixture else True, "failure_classification": failure, "command": ["<prompt>" if part == prompt else part for part in command], **_usage(stdout)}
    (work_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _move_finalized_artifacts(work_dir, run_dir)
    print(json.dumps({"run_id": run_id, "exit_code": exit_code, "failure_classification": failure, "parent_isolated": before == after}))
    return 0 if exit_code == 0 and not timed_out else 1


if __name__ == "__main__": raise SystemExit(main())
