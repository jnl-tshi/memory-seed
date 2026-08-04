"""Run one agent-capture trial: copy a fixture template, launch a headless session inside it.

The run directory is the readout. Whatever the session recorded lands in the run's own
`.memory-seed/sessions/` (nearest-runtime discovery, launched with cwd = run dir), and the
transcript is preserved alongside it. Nothing is written to the parent repo.

Usage:
  python experiments/agent-capture/run.py --level L0 --task T1 [--agent claude|codex]
                                          [--model MODEL] [--dry-run]
                                          [--timeout 900] [--extra-arg FLAG ...]

Harness constants (identical across all arms of the same agent, so they difference out;
PREREGISTRATION.md records them):

Claude
- `--dangerously-skip-permissions`: headless runs cannot answer permission prompts.

Codex
- trust injection via `-c projects={...}`: Codex only loads project-scoped `.codex/config.toml`
  (the MCP server) and `.codex/hooks.json` for *trusted* projects, and every run directory is a
  fresh, untrusted path. Verified: `codex doctor` reports 1 MCP server in an untrusted fixture and
  2 with the override. The whole-table form is used rather than a dotted
  `projects.<path>.trust_level` path because the dotted-path parser splits on `.`, which any
  path containing a dot would break.
- `--dangerously-bypass-approvals-and-sandbox`: `approval_policy="never"` does NOT cover MCP tool
  calls - a probe with it set still came back `user cancelled MCP tool call`, because headless runs
  have nobody to approve. This is the Claude `--dangerously-skip-permissions` analogue. Because it
  also drops the sandbox, every run fingerprints the parent repo before and after (see
  `_parent_fingerprint`) and records whether it stayed untouched.
- `-c features.apps=false`: this machine's Codex exposes 240 MCP tools (~139k input tokens of tool
  surface per turn) from account-level app connectors. Disabling `apps` removes them without
  removing the project's memory-seed server - verified by an actual `memory_topics_list` call,
  not by the model's self-report, which was unreliable about its own tool list.
- explicit `cwd` pin on the MCP server (see `_pin_codex_mcp_cwd`): stock config leaves `cwd` unset,
  and the memory-seed MCP server resolves `cwd="."` against its OWN process cwd (H4). Unset means
  inheriting whatever Codex happens to pass; unpinned, a write could resolve up to the PARENT store
  (H1 has no boundary guard) while the agent reports success and the fixture store reads empty.
- `--extra-arg` exists for smoke-probe debugging and any flag used must be promoted into the
  manifest-recorded constants before real arms run.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
TEMPLATES = HERE / "templates"
RUNS = HERE / "runs"
TASKS = HERE / "tasks"

LEVELS = ("L0", "L1", "L2", "L3")

BRIEF_MARKER = "<brief elided>"

_MCP_HEADER_RE = re.compile(r"^\[mcp_servers\.(?:memory-seed|\"memory-seed\")\]\s*$")
_CWD_LINE_RE = re.compile(r"^\s*cwd\s*=")


def rmtree_force(path: Path) -> None:
    """rmtree that clears the Windows read-only bit git sets on object files."""

    def _onerror(func, target, _exc_info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=_onerror)


def _parent_fingerprint() -> dict:
    """Cheap proof that a run left the parent repository alone.

    The Codex arm runs unsandboxed, so isolation is asserted rather than assumed. The parent's
    session store is where an unpinned MCP write would land, so `session_files`/`session_bytes`
    carry the pass/fail signal. `dirty_paths` is captured alongside them but is **informational
    only**: a scored batch can easily overlap an editing session in the shared primary checkout,
    and an assertion that cries wolf on somebody else's unrelated edit stops being read.
    """
    sessions = REPO_ROOT / ".memory-seed" / "sessions"
    files = sorted(path for path in sessions.rglob("*") if path.is_file())
    status = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "session_files": len(files),
        "session_bytes": sum(path.stat().st_size for path in files),
        "dirty_paths": len([ln for ln in status.stdout.splitlines() if ln.strip()]),
    }


def load_task(task_id: str) -> dict:
    manifest = json.loads((TASKS / "tasks.json").read_text(encoding="utf-8"))
    for task in manifest["tasks"]:
        if task["id"] == task_id:
            return task
    raise SystemExit(f"unknown task {task_id!r}; known: {[t['id'] for t in manifest['tasks']]}")


def _codex_trust_override(run_dir: Path) -> str:
    """Trust exactly this run directory for one invocation.

    Replaces the whole `projects` table rather than adding one key, so the TOML key is a proper
    basic string and never has to survive dotted-path splitting.
    """
    escaped = str(run_dir).replace("\\", "\\\\")
    return f'projects={{ "{escaped}" = {{ trust_level = "trusted" }} }}'


def _pin_codex_mcp_cwd(run_dir: Path) -> bool:
    """Add `cwd = '<run dir>'` to the run's [mcp_servers.memory-seed] table.

    Done here rather than in the template because the path is per-run. Returns True if written.
    """
    config_path = run_dir / ".codex" / "config.toml"
    if not config_path.exists():
        return False
    lines = config_path.read_text(encoding="utf-8").splitlines()
    start = next((i for i, ln in enumerate(lines) if _MCP_HEADER_RE.match(ln)), None)
    if start is None:
        return False
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("[")),
        len(lines),
    )
    table = [ln for ln in lines[start + 1 : end] if not _CWD_LINE_RE.match(ln)]
    # TOML literal (single-quoted) strings take Windows backslashes verbatim.
    table.append(f"cwd = '{run_dir}'")
    rebuilt = lines[:start + 1] + table + lines[end:]
    config_path.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")
    return True


def build_command(agent: str, run_dir: Path, brief: str, args) -> list[str]:
    if agent == "claude":
        return [
            "claude",
            "-p",
            brief,
            "--output-format",
            "json",
            "--dangerously-skip-permissions",
            # The fixture's OWN .mcp.json, and nothing else. Without --strict-mcp-config the
            # operator's user-level servers leak in: probe A saw `semble` contribute 2 tools and a
            # claude.ai connector offer more. Same purpose as the Codex arm's features.apps=false.
            "--mcp-config",
            str(run_dir / ".mcp.json"),
            "--strict-mcp-config",
            *(["--model", args.model] if args.model else []),
            *args.extra_arg,
        ]
    if agent == "codex":
        executable = shutil.which("codex") or shutil.which("codex.cmd")
        if not executable:
            raise SystemExit("codex CLI not found on PATH")
        return [
            executable,
            "exec",
            "--json",
            "-C",
            str(run_dir),
            "-o",
            "RUN_LAST_MESSAGE.txt",
            "--dangerously-bypass-approvals-and-sandbox",
            "-c",
            "features.apps=false",
            "-c",
            _codex_trust_override(run_dir),
            *(["-c", f'model_reasoning_effort="{args.effort}"'] if args.effort else []),
            *(["-m", args.model] if args.model else []),
            *args.extra_arg,
            brief,
        ]
    raise SystemExit(f"no runner defined for agent {agent!r}")


def transcript_name(agent: str) -> str:
    """Codex `--json` emits JSONL; Claude `--output-format json` emits one object."""
    return "transcript.jsonl" if agent == "codex" else "transcript.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", required=True, choices=LEVELS)
    parser.add_argument("--task", required=True)
    parser.add_argument("--agent", default="claude", choices=("claude", "codex"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--effort", default=None, help="codex only: model_reasoning_effort")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--extra-arg", action="append", default=[])
    parser.add_argument(
        "--brief",
        default=None,
        help="instrument-probe only: replace the task brief with this text. Recorded in the "
        "manifest as brief_override so a probe run can never be mistaken for a scored one.",
    )
    args = parser.parse_args()

    task = load_task(args.task)
    brief = args.brief or (TASKS / task["brief"]).read_text(encoding="utf-8")

    template = TEMPLATES / f"{args.agent}-{args.level}"
    if not template.is_dir():
        raise SystemExit(f"template missing: {template} - run generate_fixtures.py first")

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{args.agent}-{args.level}-{args.task}-{stamp}"
    run_dir = RUNS / run_id
    RUNS.mkdir(exist_ok=True)
    shutil.copytree(template, run_dir)

    pinned_cwd = _pin_codex_mcp_cwd(run_dir) if args.agent == "codex" else False
    command = build_command(args.agent, run_dir, brief, args)

    manifest: dict = {
        "run_id": run_id,
        "level": args.level,
        "task": args.task,
        "agent": args.agent,
        "model": args.model,
        "effort": args.effort,
        "template": str(template.relative_to(HERE)),
        "mcp_cwd_pinned": pinned_cwd,
        "brief_override": bool(args.brief),
        "parent_before": _parent_fingerprint(),
        # Elide by identity, not position: the brief sits at a different index per agent.
        "command": [BRIEF_MARKER if part == brief else part for part in command],
        "started_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }

    if args.dry_run:
        manifest["dry_run"] = True
        print(json.dumps(manifest, indent=2))
        rmtree_force(run_dir)
        return 0

    try:
        completed = subprocess.run(
            command,
            cwd=run_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
            shell=False,
        )
        manifest["exit_code"] = completed.returncode
        (run_dir / transcript_name(args.agent)).write_text(completed.stdout, encoding="utf-8")
        if completed.stderr:
            (run_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        manifest["exit_code"] = None
        manifest["timed_out"] = True
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        (run_dir / transcript_name(args.agent)).write_text(stdout, encoding="utf-8")
        stderr = exc.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        if stderr:
            (run_dir / "stderr.log").write_text(stderr, encoding="utf-8")
    finally:
        manifest["finished_at"] = _dt.datetime.now().isoformat(timespec="seconds")
        manifest["parent_after"] = _parent_fingerprint()
        manifest["parent_isolated"] = all(
            manifest["parent_after"][key] == manifest["parent_before"][key]
            for key in ("session_files", "session_bytes")
        )
        (run_dir / "RUN_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                k: manifest.get(k)
                for k in ("run_id", "exit_code", "timed_out", "parent_isolated")
            },
            indent=2,
        )
    )
    if not manifest["parent_isolated"]:
        print(
            "WARNING: the PARENT session store changed during this run - "
            f"before={manifest['parent_before']} after={manifest['parent_after']}",
            file=sys.stderr,
        )
    elif manifest["parent_after"]["dirty_paths"] != manifest["parent_before"]["dirty_paths"]:
        print(
            "note: the parent working tree changed during this run (informational - most likely a "
            "concurrent editing session in the shared checkout, not this run). "
            f"dirty_paths {manifest['parent_before']['dirty_paths']} -> "
            f"{manifest['parent_after']['dirty_paths']}",
            file=sys.stderr,
        )
    print(f"readout: {run_dir / '.memory-seed' / 'sessions'}")
    return 0 if manifest.get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
