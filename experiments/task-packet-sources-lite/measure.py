"""Measure Task Packet size by component for the sources/orientation-lite plan.

Compiles the offline pilot fixture twice - as the shipped read-only dispatch and
as a session-writing ``worker_checkpoint`` variant - with this repository's real
``agent-rules.md`` and ``session_logging.md`` substituted into the fixture, so
the worker-baseline cost reflects production control-plane files rather than
the fixture's one-line stand-ins.  Prints one JSON document; rerun at T7/T10.

Usage: python -X utf8 experiments/task-packet-sources-lite/measure.py [--label T0]
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from memory_seed.task_packet import (  # noqa: E402
    canonical_task_packet_json,
    compile_task_packet,
    estimate_tokens,
)
from tests.pilot_task_packet_fixture import (  # noqa: E402
    build_fixture_runtime,
    runtime_binding,
    semantic_dispatch,
    worker_environment,
)

SESSION_PATH = ".memory-seed/sessions/2026-09/2026-09-24.md"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _runtime(tmp: Path) -> Path:
    root = build_fixture_runtime(tmp / "runtime")
    for rel in (".memory-seed/agent-rules.md", ".memory-seed/skills/session_logging.md"):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    _git(root, "add", ".")
    _git(root, "commit", "-m", "Use production control-plane baselines")
    return root


def _writing_dispatch() -> dict:
    dispatch = copy.deepcopy(semantic_dispatch())
    execution = dispatch["execution"]
    execution["write_intent"] = "writing"
    execution["allowed_files"] = ["docs/pilot-support.md", SESSION_PATH]
    dispatch["memory_update_policy"] = "worker_checkpoint"
    dispatch["memory_checkpoints"] = {
        "names": ["implementation-complete"],
        "session_paths": [SESSION_PATH],
        "branch_local_only": True,
        "guarded_append": True,
    }
    return dispatch


def _writing_binding(root: Path) -> dict:
    binding = runtime_binding(root)
    binding.update(
        {
            "working_branch": "main",
            "worktree": str(root.resolve()),
            "integration_artifact": "branch",
        }
    )
    return binding


def _measure(packet: dict) -> dict:
    ledger = packet["input_ledger"]
    baseline = packet.get("worker_baseline") or {}
    sources = baseline.get("sources") or {}
    return {
        "packet_fingerprint": packet.get("packet_fingerprint") or packet.get("fingerprint"),
        "serialized_packet_tokens": estimate_tokens(canonical_task_packet_json(packet)),
        "baseline_tokens": {
            name: (record or {}).get("token_estimate") for name, record in sources.items()
        },
        "input_ledger": {
            key: value for key, value in ledger.items() if isinstance(value, int)
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="measurement")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="tp-measure-") as tmp:
        root = _runtime(Path(tmp))
        env = worker_environment()
        read_only = compile_task_packet(semantic_dispatch(), runtime_binding(root), root, environment=env)
        writing = compile_task_packet(_writing_dispatch(), _writing_binding(root), root, environment=env)
        result = {
            "label": args.label,
            "repo_head": subprocess.run(
                ["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True
            ).stdout.strip(),
            "read_only": _measure(read_only),
            "session_writing": _measure(writing),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
