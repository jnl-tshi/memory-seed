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


# Real decisions whose S: lines exercise every source-following path: a
# Constitution anchor, followed Todo/Deferred plans, and retired (archived)
# reports that must be listed rather than followed.
REPO_PINS = (
    ("mse_v048edjgmvk5mqsx:d1", "Integrates the decision proposal pack; cites Todo, Deferred and archived sources."),
    ("mse_nw47r0vpcj5tr2pj:d1", "Designs the worktree-reconciliation skill; cites skills and a Constitution heading anchor."),
)


def _repo_dispatch(profile_version: int) -> dict:
    dispatch = copy.deepcopy(semantic_dispatch())
    dispatch["retrieval"] = {
        "profile": "implementation",
        "profile_version": profile_version,
        "overrides": {
            "selectors": {
                "pinned": [
                    {"kind": "decision", "id": ref, "reason": reason, "required": True}
                    for ref, reason in REPO_PINS
                ]
            },
            "limits": {"max_entries": 60, "max_tokens": 20000},
        },
    }
    dispatch["budget"]["over_soft_cap"] = "allow"
    dispatch["budget"]["over_soft_cap_reason"] = "Measurement run over the real corpus."
    return dispatch


def _repo_binding() -> dict:
    head = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "-C", str(REPO), "branch", "--show-current"], capture_output=True, text=True, check=True
    ).stdout.strip()
    return {
        "owner": "frontier-orchestrator",
        "agent_type": "claude",
        "base_branch": branch,
        "base_sha": head,
        "working_branch": None,
        "worktree": None,
        "expected_directory": str(REPO),
        "integration_artifact": "handoff",
    }


def _measure_repo(packet: dict) -> dict:
    result = _measure(packet)
    evidence = packet["evidence_pack"]["evidence"]
    followed = [item for item in evidence if "optional.source_references" in item["selected_by"]]
    result["followed_sources"] = {item["id"]: item["token_estimate"] for item in followed}
    result["source_warnings"] = sorted(
        f"{item['code']}: {item['detail']}"
        for item in packet["evidence_pack"]["warnings"]
        if item["code"].startswith("source_ref_")
    )
    projection = packet["constitution_projection"]
    result["constitution"] = {
        "mode": projection["mode"],
        "selection_mode": projection.get("selection_mode"),
        "content_tokens": projection["content_tokens"],
        "clauses": [clause["ref"] for clause in projection.get("clauses", [])],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="measurement")
    parser.add_argument(
        "--repo",
        action="store_true",
        help="compile read-only packets over this repository's real corpus with v1 and v2 profiles",
    )
    args = parser.parse_args()
    if args.repo:
        # Real-corpus resolution takes ~4.8 s against the 5 s production
        # deadline (measured 2026-09-24), so a measurement run would fail by
        # chance. Lift the deadline for measurement only; see RESULTS.md.
        import memory_seed.retrieval as retrieval

        retrieval.resolve_retrieval_spec.__kwdefaults__["_timeout_ms"] = 120_000
        env = worker_environment()
        result = {
            "label": args.label,
            "repo_head": _repo_binding()["base_sha"],
            "profile_v1": _measure_repo(compile_task_packet(_repo_dispatch(1), _repo_binding(), REPO, environment=env)),
            "profile_v2": _measure_repo(compile_task_packet(_repo_dispatch(2), _repo_binding(), REPO, environment=env)),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
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
