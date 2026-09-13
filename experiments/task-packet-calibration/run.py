"""Run one Task Packet calibration cell through Hermes and LM Studio."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

try:  # Package import under pytest; direct-script fallback for the CLI.
    from .contracts import (
        ARMS,
        BUNDLE_SCHEMA,
        RUN_SCHEMA,
        canonical_json,
        fingerprint,
        load_json,
        require_schema,
    )
except ImportError:  # pragma: no cover - exercised by live direct-script runs
    from contracts import (
        ARMS,
        BUNDLE_SCHEMA,
        RUN_SCHEMA,
        canonical_json,
        fingerprint,
        load_json,
        require_schema,
    )


HERE = Path(__file__).resolve().parent
DEFAULT_HERMES_TREE = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "hermes-agent"
DEFAULT_HERMES_PYTHON = DEFAULT_HERMES_TREE / "venv" / "Scripts" / "python.exe"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _hermes_config(
    *, model: str, arm: str, fixture: Path, audit_log: Path, mcp_python: Path
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "model": {
            "provider": "lmstudio",
            "default": model,
            "base_url": "http://127.0.0.1:1234/v1",
            "lmstudio_load_mode": "explicit",
        },
        "platform_toolsets": {
            "cli": [] if arm == "no_memory" else ["mcp-memory_seed_calibration"]
        },
        "display": {"quiet": True},
        "compression": {"enabled": False},
        "checkpoints": {"enabled": False},
        "memory": {"provider": ""},
        # Four bounded schemas are cheaper and more observable than routing
        # them through Hermes' progressive-disclosure meta-tools.
        "tools": {"tool_search": {"enabled": "off"}},
    }
    if arm != "no_memory":
        config["mcp_servers"] = {
            "memory_seed_calibration": {
                "command": str(mcp_python),
                "args": [
                    str(HERE / "mcp_wrapper.py"),
                    "--fixture",
                    str(fixture),
                    "--audit-log",
                    str(audit_log),
                ],
                "enabled": True,
                # The facade itself is the trust boundary: it exposes only the
                # four read methods below and pins every cwd to the fixture.
                # Hermes 0.20.5 misreads MCP SDK v2's read_only_hint attribute,
                # so its untrusted gate otherwise blocks these read-only calls.
                "trust": "full",
                "tools": {
                    "include": [
                        "memory_search",
                        "memory_get_chunk",
                        "memory_adrs_list",
                        "memory_adr_show",
                    ],
                    "resources": False,
                    "prompts": False,
                },
            }
        }
    return config


def _scrub_external_credentials(environment: dict[str, str]) -> dict[str, str]:
    blocked = (
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "ANTHROPIC_API_KEY",
        "NOUS_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    )
    for key in blocked:
        environment.pop(key, None)
    return environment


def run_cell(
    bundle: Path,
    *,
    arm: str,
    model: str,
    repetition: int,
    output: Path,
    hermes_tree: Path = DEFAULT_HERMES_TREE,
    hermes_python: Path = DEFAULT_HERMES_PYTHON,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite run result: {output}")
    manifest = load_json(bundle / "bundle.json")
    require_schema(manifest, BUNDLE_SCHEMA)
    prompt_path = bundle / manifest["arms"][arm]["path"]
    prompt = prompt_path.read_text(encoding="utf-8")
    if fingerprint(prompt) != manifest["arms"][arm]["fingerprint"]:
        raise ValueError("prompt fingerprint mismatch")
    if not hermes_python.exists() or not hermes_tree.exists():
        raise FileNotFoundError("Hermes installation or Python runtime was not found")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="task-packet-calibration-") as temp_name:
        temp = Path(temp_name)
        hermes_home = temp / ".hermes"
        hermes_home.mkdir()
        usage_path = temp / "usage.json"
        diagnostics_path = temp / "hermes-diagnostics.json"
        audit_log = temp / "tool-calls.jsonl"
        config = _hermes_config(
            model=model,
            arm=arm,
            fixture=bundle / "runtime",
            audit_log=audit_log,
            mcp_python=hermes_python,
        )
        (hermes_home / "config.yaml").write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        command = [
            str(hermes_python),
            str(HERE / "hermes_bridge.py"),
            "--hermes-tree",
            str(hermes_tree),
            "--prompt-file",
            str(prompt_path),
            "--usage-file",
            str(usage_path),
            "--diagnostics-file",
            str(diagnostics_path),
            "--model",
            model,
            "--provider",
            "lmstudio",
        ]
        environment = _scrub_external_credentials(dict(os.environ))
        environment["HERMES_HOME"] = str(hermes_home)
        environment["HERMES_DISABLE_UPDATE_CHECK"] = "1"
        started = time.perf_counter()
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=str(bundle / "runtime"),
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
            return_code = completed.returncode
            stdout, stderr = completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            return_code = None
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
        wall_seconds = round(time.perf_counter() - started, 3)
        usage = load_json(usage_path) if usage_path.exists() else None
        diagnostics = load_json(diagnostics_path) if diagnostics_path.exists() else None
        tool_calls = _read_jsonl(audit_log)
        stable = {
            "schema": RUN_SCHEMA,
            "version": 1,
            "bundle_fingerprint": manifest["bundle_fingerprint"],
            "task_id": manifest["task_id"],
            "task_split": manifest["task_split"],
            "arm": arm,
            "model": model,
            "provider": "lmstudio",
            "repetition": repetition,
            "prompt_fingerprint": manifest["arms"][arm]["fingerprint"],
            "packet_fingerprint": manifest["packet_fingerprint"] if arm == "compiled_packet" else None,
            "return_code": return_code,
            "timed_out": timed_out,
            "wall_seconds": wall_seconds,
            "response": stdout.strip(),
            "stderr": stderr.strip(),
            "usage": usage,
            "hermes_diagnostics": diagnostics,
            "tool_calls": tool_calls,
            "tool_call_count": len(tool_calls),
        }
        record = {**stable, "run_fingerprint": fingerprint(stable)}
        output.write_text(
            json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--arm", required=True, choices=ARMS)
    parser.add_argument("--model", required=True)
    parser.add_argument("--repetition", type=int, default=1)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hermes-tree", type=Path, default=DEFAULT_HERMES_TREE)
    parser.add_argument("--hermes-python", type=Path, default=DEFAULT_HERMES_PYTHON)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args(argv)
    record = run_cell(
        args.bundle.resolve(),
        arm=args.arm,
        model=args.model,
        repetition=args.repetition,
        output=args.output.resolve(),
        hermes_tree=args.hermes_tree.resolve(),
        hermes_python=args.hermes_python.resolve(),
        timeout_seconds=args.timeout_seconds,
    )
    print(canonical_json({"run_fingerprint": record["run_fingerprint"], "return_code": record["return_code"]}))
    return 0 if record["return_code"] == 0 and not record["timed_out"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
