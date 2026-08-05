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
import threading
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
from contracts import ARMS, RUN_SCHEMA, SCHEDULE_SEED, answer_template, fingerprint, live_execution_approved, live_pin_matches, live_tasks_match, require_schema, validate_answer  # noqa: E402
from pilot_spec import (PILOT_AUTH_ENV, PILOT_AUTHORITY_MARKER, PILOT_CELLS, PILOT_CLAIM_PATH, PILOT_TASK_ID,
                        path_identity, pilot_cell_claim_path, pilot_tasks_fingerprint, sha256_text, validate_task_payload,
                        verified_claude_executable, verify_output_authority)  # noqa: E402

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
PILOT_PROVIDER_OUTPUT_LIMIT = 4 * 1024 * 1024
PILOT_CHILD_OUTPUT_LIMIT = 1024 * 1024
PILOT_TIMEOUT_MAX = 900
PILOT_FINAL_OUTPUT_LIMIT = 256 * 1024
CANONICAL_REF_RE = re.compile(r"\b(?:mse_[0-9a-hjkmnp-tv-z]{16}:d[0-9]+|adr_[a-z0-9_]+)\b")
CANONICAL_ENTRY_RE = re.compile(r"\bmse_[0-9a-hjkmnp-tv-z]{16}\b")


class CappedProcessResult:
    def __init__(self, args: list[str], returncode: int, stdout: str, stderr: str, *, overflow: bool, timed_out: bool):
        self.args = args; self.returncode = returncode; self.stdout = stdout; self.stderr = stderr
        self.overflow = overflow; self.timed_out = timed_out


def capped_subprocess(
    command: list[str], *, cwd: Path, env: dict[str, str], timeout: int,
    byte_limit: int,
) -> CappedProcessResult:
    """Drain both pipes concurrently while retaining at most ``byte_limit`` bytes."""
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retained = {"stdout": bytearray(), "stderr": bytearray()}
    lock = threading.Lock(); overflow = threading.Event()

    def drain(name: str, stream: Any) -> None:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            with lock:
                remaining = byte_limit - len(retained["stdout"]) - len(retained["stderr"])
                if remaining > 0:
                    retained[name].extend(chunk[:remaining])
                if len(chunk) > max(0, remaining):
                    overflow.set()
                    try: process.terminate()
                    except OSError: pass

    threads = [
        threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads: thread.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill(); process.wait()
    for thread in threads: thread.join(timeout=5)
    for stream in (process.stdout, process.stderr):
        try: stream.close()
        except OSError: pass
    return CappedProcessResult(
        command, process.returncode,
        retained["stdout"].decode("utf-8", errors="replace"),
        retained["stderr"].decode("utf-8", errors="replace"),
        overflow=overflow.is_set(), timed_out=timed_out,
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


def installed_cli_version(agent: str, *, executable: Path | None = None) -> tuple[str, str]:
    executable = str(executable) if executable else ("claude" if agent == "claude" else (shutil.which("codex") or "codex"))
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
    agent_executable: Path | None = None,
) -> list[str]:
    interactive = arm in MCP_ARMS
    if agent == "claude":
        command = [
            str(agent_executable or "claude"), "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--disable-slash-commands", "--no-session-persistence",
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
            command += ["--tools", "", "--safe-mode"]
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


def _pilot_protocol_failures(
    arm: str,
    calls: list[str],
    broker_calls: list[str],
    allowed: set[str],
) -> list[str]:
    """Reject interactive pilot cells that never exercise an allowed MCP tool."""
    if arm not in INTERACTIVE_ARMS:
        return []
    observed = set(calls) | set(broker_calls)
    return [] if observed & allowed else ["interactive_no_mcp_calls"]


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
    pilot: bool = False,
) -> bool:
    """Redact provider-authored files before they enter retained artifacts."""
    final = path / "RUN_LAST_MESSAGE.txt"
    if final.exists():
        if pilot and final.stat().st_size > PILOT_FINAL_OUTPUT_LIMIT:
            final.unlink()
            return False
        text = redact_output(final.read_text(encoding="utf-8", errors="replace"), secrets=secrets)
        if pilot:
            text = _schema_answer_json(text)
        elif approval_smoke:
            text = _sanitize_approval_smoke_arguments(text)
        final.write_text(text, encoding="utf-8")
    return True


def sanitize_pilot_stream(text: str, *, secrets: tuple[str, ...] = ()) -> str:
    """Normalize provider JSONL to the small evidence/usage/final contract."""
    def clean_text(value: str) -> str:
        return _normalize_retained_string(value, limit=12000)

    def evidence(value: Any) -> Any:
        if isinstance(value, str):
            try: return evidence(json.loads(value))
            except json.JSONDecodeError: return clean_text(value)
        if isinstance(value, list): return [evidence(item) for item in value[:100]]
        if not isinstance(value, dict): return value if isinstance(value, (bool, int, float)) or value is None else str(value)
        allowed = {
            "type", "text", "content", "structuredContent", "ok", "items", "results", "adrs", "refs",
            "decision_ref", "authoritative_ref", "status", "source", "target", "ref",
            "title", "decision", "why", "evolution", "schema", "insufficient_evidence",
            "lineage_edges", "related_edges", "citations", "missing_refs",
        }
        return {key: evidence(item) for key, item in value.items() if key in allowed}

    def evidence_with_refs(value: Any) -> Any:
        strings: list[str] = []
        def collect_strings(item: Any) -> None:
            if isinstance(item, str):
                try: parsed = json.loads(item)
                except json.JSONDecodeError: strings.append(item)
                else: collect_strings(parsed)
            elif isinstance(item, list):
                for child in item: collect_strings(child)
            elif isinstance(item, dict):
                for child in item.values(): collect_strings(child)
        collect_strings(value)
        blob = "\n".join(strings)
        refs = set(CANONICAL_REF_RE.findall(blob))
        # PILOT-01 contains one decision per entry. A search result may expose
        # only the canonical entry identity/section, so its safe decision form
        # is deterministically d1 for this frozen fixture only.
        refs.update(f"{entry}:d1" for entry in CANONICAL_ENTRY_RE.findall(blob))
        cleaned = evidence(value)
        if isinstance(cleaned, dict):
            return {**cleaned, "refs": sorted(refs)}
        return {"text": cleaned, "refs": sorted(refs)}

    lines: list[str] = []
    known_tools = set(__import__("mcp_wrapper").WORKFLOW_TOOLS)
    def tool_name(value: Any) -> str:
        raw = str(value)
        for candidate in (raw, raw.rsplit("__", 1)[-1], raw.rsplit(".", 1)[-1]):
            if candidate in known_tools: return candidate
        return "<undeclared-tool>"
    for line in redact_output(text, secrets=secrets).splitlines():
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        if not isinstance(event, dict): continue
        normalized: dict[str, Any] | None = None
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        if item.get("type") == "mcp_tool_call":
            normalized = {"type": "item.completed", "item": {
                "type": "mcp_tool_call", "tool": tool_name(item.get("tool", "")),
                "result": evidence_with_refs(item.get("result")),
            }}
        elif event.get("type") == "mcp_tool_call":
            normalized = {"type": "item.completed", "item": {
                "type": "mcp_tool_call", "tool": tool_name(event.get("tool", "")),
                "result": evidence_with_refs(event.get("result")),
            }}
        else:
            blocks = (event.get("message") or {}).get("content", []) if isinstance(event.get("message"), dict) else []
            kept = []
            for block in blocks if isinstance(blocks, list) else []:
                if not isinstance(block, dict): continue
                if block.get("type") == "tool_use":
                    kept.append({"type": "tool_use", "name": tool_name(block.get("name", ""))})
                elif block.get("type") == "tool_result":
                    kept.append({"type": "tool_result", "content": evidence_with_refs(block.get("content"))})
            if kept: normalized = {"type": "message", "message": {"content": kept}}
        answer = _schema_answer_json(str(event.get("result", "")))
        if not answer and item.get("type") == "agent_message":
            answer = _schema_answer_json(str(item.get("text", "")))
        if answer:
            normalized = {"type": "result", "result": answer}
        usage = event.get("usage") or ((event.get("response") or {}).get("usage") if isinstance(event.get("response"), dict) else None)
        if isinstance(usage, dict):
            safe_usage = {key: usage[key] for key in ("input_tokens", "output_tokens", "prompt_tokens", "completion_tokens", "cost_usd", "cost") if isinstance(usage.get(key), (int, float))}
            if safe_usage:
                if normalized is None: normalized = {"type": "usage"}
                normalized["usage"] = safe_usage
        if normalized is not None:
            lines.append(json.dumps(normalized, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(lines) + ("\n" if lines else "")


def _schema_answer_json(text: str) -> str:
    candidates = [text.strip(), *[line.strip() for line in text.splitlines() if line.strip().startswith("{")]]
    for candidate in reversed(candidates):
        try: value = json.loads(candidate)
        except json.JSONDecodeError: continue
        try: validate_answer(value)
        except ValueError: continue
        normalized = _normalize_answer_strings(value)
        try: validate_answer(normalized)
        except ValueError: continue
        return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    return ""


def _normalize_answer_strings(value: Any) -> Any:
    if isinstance(value, list): return [_normalize_answer_strings(item) for item in value]
    if isinstance(value, dict): return {_normalize_answer_strings(str(key))[:128]: _normalize_answer_strings(item) for key, item in value.items()}
    if not isinstance(value, str): return value
    cleaned = _normalize_retained_string(value, limit=4096)
    if CANONICAL_REF_RE.fullmatch(cleaned) or CANONICAL_ENTRY_RE.fullmatch(cleaned):
        return cleaned
    return cleaned


def _normalize_retained_string(value: str, *, limit: int) -> str:
    """Redact secrets before recognizing identifiers or normalizing paths."""
    cleaned = redact_output(value)
    cleaned = re.sub(r"\\\\[^\\\s]+\\[^\r\n\"']+", "<path>", cleaned)
    cleaned = re.sub(r"(?i)\b[A-Z]:\\[^\r\n\"']+", "<path>", cleaned)
    cleaned = re.sub(r"(?<![A-Za-z0-9_.-])/(?:[^\s\"']+/)+[^\s\"']*", "<path>", cleaned)
    cleaned = re.sub(r"%(?:[A-Z_][A-Z0-9_]*)%|\$\{?[A-Z_][A-Z0-9_]*\}?", "<env>", cleaned, flags=re.I)
    return cleaned[:limit]


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


def _pilot_claim_authorized(*, auth: str, tasks: dict[str, Any], tasks_path: Path, output: Path, cell: tuple[str, str, int]) -> bool:
    try:
        claim = json.loads(PILOT_CLAIM_PATH.read_text(encoding="utf-8"))
        fixture = Path(tasks["tasks"][0]["fixture"]).resolve(strict=True)
        tasks_sha256 = hashlib.sha256(tasks_path.read_bytes()).hexdigest()
        fixture_identity = path_identity(fixture)
    except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        return False
    return (
        bool(auth) and claim.get("schema") == "context-pilot-claim.v1"
        and claim.get("auth_sha256") == sha256_text(auth)
        and claim.get("tasks_fingerprint") == pilot_tasks_fingerprint(tasks)
        and claim.get("tasks_sha256") == tasks_sha256
        and claim.get("fixture_path_sha256") == sha256_text(str(fixture))
        and claim.get("fixture_identity") == fixture_identity
        and claim.get("output_path_sha256") == sha256_text(str(output.resolve()))
        and claim.get("authority_marker") == PILOT_AUTHORITY_MARKER
        and verify_output_authority(output, PILOT_CLAIM_PATH, auth)
        and [*cell] in claim.get("cells", []) and cell in PILOT_CELLS
        and claim.get("consumed") is True
    )


def _consume_pilot_cell_claim(cell: tuple[str, str, int]) -> None:
    path = pilot_cell_claim_path(cell)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
    except FileExistsError as exc:
        raise RuntimeError(f"pilot cell {cell!r} has already been consumed") from exc
    try:
        os.write(descriptor, b"consumed\n")
    finally:
        os.close(descriptor)


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


def _retained_command(
    command: list[str], *, prompt: str, work_dir: Path,
    claude_executable: Path | None = None,
    redact_executable: bool = False,
) -> list[str]:
    retained: list[str] = []
    work = str(work_dir.resolve()).lower()
    for index, part in enumerate(command):
        lowered = str(part).lower()
        if part == prompt:
            retained.append("<prompt>")
        elif redact_executable and index == 0:
            retained.append("<verified-agent-executable>")
        elif claude_executable and part == str(claude_executable):
            retained.append("<verified-claude-executable>")
        elif work and work in lowered:
            retained.append("<subject-path>")
        else:
            retained.append(part)
    return retained


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
    smoke_output.add_argument(
        "--pilot-output",
        help="shared OS-temporary output root for the separately gated unscored pilot",
    )
    parser.add_argument("--pilot-claude-executable")
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
    pilot_mode = args.pilot_output is not None
    if pilot_mode and (
        args.task != PILOT_TASK_ID or args.repetition != 1
        or (args.agent, args.arm, args.repetition) not in PILOT_CELLS
    ):
        parser.error("--pilot-output is valid only for a canonical PILOT-01 repetition-1 cell")
    if pilot_mode and (args.timeout <= 0 or args.timeout > PILOT_TIMEOUT_MAX):
        parser.error(f"pilot timeout must be between 1 and {PILOT_TIMEOUT_MAX} seconds")
    if args.pilot_claude_executable and (not pilot_mode or args.agent != "claude"):
        parser.error("--pilot-claude-executable is valid only for a Claude pilot cell")
    if pilot_mode and args.agent == "claude" and not args.pilot_claude_executable:
        parser.error("Claude pilot cells require --pilot-claude-executable")
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
    if not args.dry_run and smoke_kind is None and not pilot_mode and not scored_execution_ready():
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
    tasks_payload = json.loads(_tasks_path(args.tasks).read_text(encoding="utf-8"))
    if pilot_mode:
        if not validate_task_payload(tasks_payload):
            parser.error("pilot tasks do not match the frozen PILOT-01 contract")
    elif not args.dry_run and not live_tasks_match(HERE, _tasks_path(args.tasks)):
        parser.error("materialized live tasks do not match LIVE_MATRIX.json")
    pilot_claude_executable: Path | None = None
    if pilot_mode and args.agent == "claude":
        try:
            pilot_claude_executable = verified_claude_executable(Path(args.pilot_claude_executable))
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    smoke_root = _unscored_smoke_root(smoke_output_path) if smoke_output_path else None
    pilot_root = Path(args.pilot_output).resolve() if pilot_mode else None
    if pilot_root is not None:
        temp_root = Path(tempfile.gettempdir()).resolve()
        try:
            pilot_root.relative_to(temp_root)
        except ValueError:
            parser.error("pilot output must remain under the OS temporary directory")
        if not pilot_root.is_dir():
            parser.error("pilot coordinator must create the output directory before child launch")
        auth = os.environ.get(PILOT_AUTH_ENV, "")
        if not _pilot_claim_authorized(
            auth=auth, tasks=tasks_payload, tasks_path=_tasks_path(args.tasks), output=pilot_root,
            cell=(args.agent, args.arm, args.repetition),
        ):
            parser.error("pilot child is not authorized by the consumed global claim")
    observed_cli_raw: str | None = None
    if not args.dry_run:
        observed_cli_raw, observed_cli = installed_cli_version(args.agent, executable=pilot_claude_executable)
        if observed_cli != args.cli_version:
            parser.error(
                f"installed {args.agent} CLI {observed_cli!r} does not match frozen pin {args.cli_version!r}"
            )
    task = load_task(args.task, _tasks_path(args.tasks)); fixture_source = task.get("fixture")
    run_id = f"{args.agent}-{args.task}-{args.arm}-r{args.repetition}-{uuid.uuid4().hex[:10]}"
    run_dir = (smoke_root or pilot_root or RUNS) / run_id
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
            agent_executable=pilot_claude_executable,
        )
        if args.dry_run:
            manifest = {"schema": RUN_SCHEMA, "run_id": run_id, "task_id": args.task, "arm": args.arm, "agent": args.agent, "repetition": args.repetition, "schedule_seed": SCHEDULE_SEED, "model": args.model, "cli_version": args.cli_version, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "dry_run": True, "scored": False if (smoke_root or pilot_root) else None, "smoke": smoke_root is not None, "pilot": pilot_mode, "smoke_kind": smoke_kind, "subject_isolation": subject_isolation(args.agent), "command": _retained_command(command, prompt=prompt, work_dir=work_dir, claude_executable=pilot_claude_executable, redact_executable=pilot_mode)}
            print(json.dumps(manifest))
            return 0

        started = time.monotonic(); stdout = stderr = ""; exit_code: int | None = None; timed_out = False
        pilot_calls: list[str] | None = None; pilot_direct_fs: bool | None = None
        try:
            if smoke_kind == "approval-mode":
                _consume_smoke_claim(APPROVAL_SMOKE_CLAIM_PATH, label="Codex approval-mode smoke")
            elif smoke_root is not None:
                _consume_smoke_claim()
            elif pilot_mode:
                _consume_pilot_cell_claim((args.agent, args.arm, args.repetition))
            if pilot_mode:
                done = capped_subprocess(
                    command, cwd=work_dir, env=environment, timeout=args.timeout,
                    byte_limit=PILOT_PROVIDER_OUTPUT_LIMIT,
                )
                timed_out = done.timed_out
            else:
                done = subprocess.run(command, cwd=work_dir, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.timeout)
            stdout = redact_output(done.stdout, secrets=(broker_token,))
            stderr = redact_output(done.stderr, secrets=(broker_token,))
            if pilot_mode:
                raw_calls = _tool_calls(stdout)
                known = set(__import__("mcp_wrapper").WORKFLOW_TOOLS)
                pilot_calls = [call if call in known else "<undeclared-tool>" for call in raw_calls]
                pilot_direct_fs = _direct_filesystem_retrieval(stdout)
            if smoke_kind == "approval-mode":
                stdout = _sanitize_approval_smoke_arguments(stdout)
                stderr = _sanitize_approval_smoke_arguments(stderr)
            elif pilot_mode:
                stdout = sanitize_pilot_stream(stdout, secrets=(broker_token,))
                stderr = sanitize_pilot_stream(stderr, secrets=(broker_token,))
            exit_code = done.returncode
            if pilot_mode and done.overflow:
                exit_code = -1
                stderr = "pilot output byte limit exceeded"
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = (exc.stdout or "").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = (exc.stderr or "").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stdout = redact_output(stdout, secrets=(broker_token,))
            stderr = redact_output(stderr, secrets=(broker_token,))
            if pilot_mode:
                raw_calls = _tool_calls(stdout)
                known = set(__import__("mcp_wrapper").WORKFLOW_TOOLS)
                pilot_calls = [call if call in known else "<undeclared-tool>" for call in raw_calls]
                pilot_direct_fs = _direct_filesystem_retrieval(stdout)
            if smoke_kind == "approval-mode":
                stdout = _sanitize_approval_smoke_arguments(stdout)
                stderr = _sanitize_approval_smoke_arguments(stderr)
            elif pilot_mode:
                stdout = sanitize_pilot_stream(stdout, secrets=(broker_token,))
                stderr = sanitize_pilot_stream(stderr, secrets=(broker_token,))
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

        subject_artifacts_safe = sanitize_subject_artifacts(
            work_dir, secrets=(broker_token,), approval_smoke=smoke_kind == "approval-mode",
            pilot=pilot_mode,
        )
        _remove_subject_configs(work_dir)
        duration_ms = round((time.monotonic() - started) * 1000)
        (work_dir / "transcript.jsonl").write_text(stdout, encoding="utf-8")
        if stderr: (work_dir / "stderr.log").write_text(stderr, encoding="utf-8")
        calls = pilot_calls if pilot_calls is not None else _tool_calls(stdout)
        broker_calls = list(endpoint.calls) if endpoint is not None else []
        broker_call_records = list(endpoint.call_records) if endpoint is not None else []
        allowed = set() if args.arm in FIXED_ARMS else set(__import__("mcp_wrapper").allowed_names(args.arm))
        undeclared_tool_calls = sorted((set(calls) | set(broker_calls)) - allowed)
        protocol_failures = (
            _pilot_protocol_failures(args.arm, calls, broker_calls, allowed)
            if pilot_mode else []
        )
        final = _final_answer(work_dir, stdout); (work_dir / "final_answer.txt").write_text(final, encoding="utf-8")
        after = parent_fingerprint()
        fixture_after = tree_fingerprint(fixture) if fixture else None
        direct_filesystem_retrieval = pilot_direct_fs if pilot_direct_fs is not None else _direct_filesystem_retrieval(stdout)
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
        if pilot_mode:
            if not subject_artifacts_safe:
                integrity_failures.append("pilot_final_answer_overflow")
            if "output byte limit exceeded" in stderr:
                integrity_failures.append("pilot_output_overflow")
            if undeclared_tool_calls: integrity_failures.append("undeclared_tool_call")
            if direct_filesystem_retrieval: integrity_failures.append("direct_filesystem_retrieval")
            if not parent_isolated: integrity_failures.append("parent_memory_store_isolation_failure")
            if not fixture_isolated: integrity_failures.append("fixture_isolation_failure")
            if interactive_codex and broker_teardown_verified is not True:
                integrity_failures.append("broker_teardown_failure")
            if integrity_failures:
                exit_code = -1
                stderr = (stderr + "\npilot integrity failure: " + ", ".join(integrity_failures)).strip()
        failure = ("pilot_integrity_failure" if pilot_mode and integrity_failures else
                   "pilot_protocol_failure" if pilot_mode and protocol_failures else
                   "smoke_integrity_failure" if integrity_failures else classify_failure(
            timed_out=timed_out, exit_code=exit_code, stderr=stderr, transcript=stdout,
        ))
        packet = _packet(task, args.arm) if args.arm in FIXED_ARMS else ""
        refs_by_arm = task.get("included_refs_by_arm") or {}
        tokens_by_arm = task.get("context_token_proxy_by_arm") or {}
        if fixture and interactive_codex:
            shutil.copytree(fixture, work_dir / "fixture")
            _make_immutable(work_dir / "fixture")
        manifest = {"schema": RUN_SCHEMA, "run_id": run_id, "task_id": args.task, "arm": args.arm, "agent": args.agent, "repetition": args.repetition, "schedule_seed": SCHEDULE_SEED, "model": args.model, "cli_version": args.cli_version, "cli_version_observed_raw": observed_cli_raw, "effort": args.effort, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "duration_ms": duration_ms, "exit_code": exit_code, "timed_out": timed_out, "scored": smoke_root is None and not pilot_mode, "smoke": smoke_root is not None, "pilot": pilot_mode, "pilot_kind": "eight-cell-unscored" if pilot_mode else None, "smoke_kind": smoke_kind, "transcript": "transcript.jsonl", "final_answer": "final_answer.txt", "interactive_fixture": "fixture" if fixture else None, "fixed_arm_no_fixture": args.arm in FIXED_ARMS, "mcp_enabled": args.arm in MCP_ARMS, "mcp_transport": "streamable_http" if endpoint else ("stdio" if args.arm in MCP_ARMS else None), "broker_teardown_verified": broker_teardown_verified, "broker_tool_calls": broker_calls, "broker_call_records": broker_call_records, "subject_isolation": subject_isolation(args.agent), "included_refs": refs_by_arm.get(args.arm, []), "context_token_proxy": tokens_by_arm.get(args.arm, len(packet.split())), "tool_calls": calls, "undeclared_tool_calls": undeclared_tool_calls, "direct_filesystem_retrieval": direct_filesystem_retrieval, "parent_before": before, "parent_after": after, "parent_isolated": parent_isolated, "fixture_before": fixture_before, "fixture_after": fixture_after, "fixture_isolated": fixture_isolated, "integrity_failures": integrity_failures, "protocol_failures": protocol_failures, "failure_classification": failure, "command": _retained_command(command, prompt=prompt, work_dir=work_dir, claude_executable=pilot_claude_executable, redact_executable=pilot_mode), **_usage(stdout)}
        (work_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        _move_finalized_artifacts(work_dir, run_dir)
        finalized = True
        print(json.dumps({"run_id": run_id, "output": str(run_dir), "exit_code": exit_code, "failure_classification": failure, "parent_isolated": before == after, "scored": smoke_root is None and not pilot_mode, "pilot": pilot_mode}))
        return 0 if exit_code == 0 and not timed_out else 1
    finally:
        if endpoint is not None and broker_teardown_verified is None:
            endpoint.close()
        if fixture_parent is not None:
            _remove_run_dir(fixture_parent)
        if not finalized:
            _remove_run_dir(work_dir)


if __name__ == "__main__": raise SystemExit(main())
