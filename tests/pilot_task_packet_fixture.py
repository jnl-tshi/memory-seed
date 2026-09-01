"""Build and compile the offline clean-session Task Packet pilot fixture."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from memory_seed.core import SEED_ROOT
from memory_seed.task_packet import canonical_task_packet_json, compile_task_packet


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "task_packet_pilot"


def _git(root: Path, *args: str) -> str:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2026-09-01T09:00:00Z",
            "GIT_COMMITTER_DATE": "2026-09-01T09:00:00Z",
        }
    )
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    ).stdout.strip()


def build_fixture_runtime(root: Path) -> Path:
    """Create one fresh deterministic Git/runtime fixture at *root*."""
    root = root.resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"fixture runtime is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE_ROOT / "runtime", root, dirs_exist_ok=True)
    profile = (
        root
        / ".memory-seed"
        / "retrieval-profiles"
        / "implementation"
        / "v1.yaml"
    )
    profile.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        SEED_ROOT
        / ".memory-seed"
        / "retrieval-profiles"
        / "implementation"
        / "v1.yaml",
        profile,
    )
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "pilot@example.invalid")
    _git(root, "config", "user.name", "Task Packet Pilot")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "Create offline Task Packet pilot corpus")
    return root


def semantic_dispatch() -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / "dispatch.json").read_text(encoding="utf-8"))


def expected_assessment() -> dict[str, Any]:
    return json.loads(
        (FIXTURE_ROOT / "expected_assessment.json").read_text(encoding="utf-8")
    )


def runtime_binding(root: Path) -> dict[str, Any]:
    base_sha = _git(root, "rev-parse", "main")
    return {
        "owner": "frontier-orchestrator",
        "agent_type": "codex",
        "base_branch": "main",
        "base_sha": base_sha,
        "working_branch": None,
        "worktree": None,
        "expected_directory": str(root.resolve()),
        "integration_artifact": "handoff",
    }


def compile_fixture_packet(root: Path) -> dict[str, Any]:
    return compile_task_packet(semantic_dispatch(), runtime_binding(root), root)


def export_fixture_packet(output: Path) -> tuple[Path, Path]:
    """Build beside *output* and publish the derived canonical packet once."""
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite pilot packet: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    runtime = build_fixture_runtime(output.parent / "runtime")
    packet = compile_fixture_packet(runtime)
    output.write_text(canonical_task_packet_json(packet) + "\n", encoding="utf-8")
    return output, runtime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output, runtime = export_fixture_packet(args.output)
    print(json.dumps({"output": str(output), "runtime": str(runtime)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
