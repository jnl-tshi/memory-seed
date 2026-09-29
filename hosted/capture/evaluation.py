from __future__ import annotations

import importlib.util
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from .adapter import CaptureAdapter
from .codex_rollout import ALLOWED_CLI_VERSIONS
from .corpus import build_manifest, evaluate_negative_controls, write_manifest
from .parser import DecisionParser
from .store import CaptureStore


def _load_alignment_parser(repo_root: Path):
    path = repo_root / "experiments" / "decision-chat-alignment" / "align_decisions.py"
    spec = importlib.util.spec_from_file_location("p02_alignment_foundation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rollout_paths(codex_home: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for base in (codex_home / "sessions", codex_home / "archived_sessions"):
        if not base.is_dir():
            continue
        for path in base.rglob("*.jsonl"):
            if path.is_file() and len(path.stem) >= 36:
                paths[path.stem[-36:].lower()] = path
    return paths


def evaluate_source_windows(repo_root: Path, codex_home: Path) -> dict[str, Any]:
    manifest = build_manifest(repo_root)
    module = _load_alignment_parser(repo_root)
    rollout_paths = _rollout_paths(codex_home)
    parser = DecisionParser()
    parsed: dict[str, Any] = {}
    eligible = [
        row for row in manifest["rows"]
        if row["record_kind"] == "Decision"
        and row["split"] in {"development", "heldout_descriptive"}
        and row["adjudication_label"] == "verified_source"
        and row["evidence_coordinates"]
    ]
    marker_hits = 0
    unmarked_hits = 0
    unavailable: list[str] = []
    for row in eligible:
        refs = row["evidence_coordinates"]
        turns = [ref["turn"] for ref in refs if isinstance(ref.get("turn"), int)]
        if not turns:
            unavailable.append(row["case_id"])
            continue
        marker_turn = max(turns)
        if all(marker_turn - 2 <= turn <= marker_turn + 1 for turn in turns):
            marker_hits += 1

        selected = row.get("selected_candidate") or {}
        rollout_id = str(selected.get("rollout_id") or refs[0]["rollout_id"]).lower()
        path = rollout_paths.get(rollout_id)
        if path is None:
            unavailable.append(row["case_id"])
            continue
        if rollout_id not in parsed:
            meta = module.read_session_meta(path)
            parsed[rollout_id] = module.parse_rollout(path, meta) if meta else []
        start = int(selected.get("window_turn_start") or marker_turn - 2)
        end = int(selected.get("window_turn_end") or marker_turn + 1)
        messages = [
            {
                "turn": block.turn_number,
                "source_ordinal": item.source_ordinal if item.source_ordinal is not None else -1,
                "actor": "agent" if item.role == "assistant" else item.role,
                "text": item.text,
            }
            for block in parsed[rollout_id]
            if start <= block.turn_number <= end
            for item in block.items
            if item.role in {"user", "assistant"}
        ]
        if parser.parse(rollout_id, messages):
            unmarked_hits += 1
    denominator = len(eligible)
    return {
        "eligible_verified_rows": denominator,
        "available_rollout_ids": len(parsed),
        "marker_assisted_source_window_recall": marker_hits / denominator if denominator else 0.0,
        "unmarked_source_window_recall": unmarked_hits / denominator if denominator else 0.0,
        "unavailable_case_ids": sorted(set(unavailable)),
        "parser_backend": parser.backend,
    }


def evaluate_live_adapter() -> dict[str, Any]:
    version = next(iter(ALLOWED_CLI_VERSIONS))
    latencies: list[float] = []
    with tempfile.TemporaryDirectory(prefix="p02-live-") as tmp:
        root = Path(tmp)
        rollout = root / "rollout-2026-09-29T10-00-00-00000000-0000-0000-0000-000000000001.jsonl"
        meta = {"timestamp": "2026-09-29T10:00:00Z", "type": "session_meta", "payload": {"id": "synthetic", "cli_version": version}}
        rollout.write_text(json.dumps(meta, sort_keys=True) + "\n", encoding="utf-8")
        with CaptureStore(root / "capture.sqlite3") as store:
            adapter = CaptureAdapter(store)
            adapter.poll([rollout])
            for index in range(30):
                marker = {
                    "timestamp": f"2026-09-29T10:00:{index:02d}Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "memory_decision_mark",
                        "arguments": json.dumps({
                            "strength": "soft", "state": "proposed", "origin": "agent",
                            "trigger_class": "agent_inference", "issue_hint": f"synthetic-{index}",
                            "trigger_quote": "I propose the synthetic option",
                        }, sort_keys=True),
                    },
                }
                start = time.perf_counter()
                with rollout.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(marker, sort_keys=True) + "\n")
                adapter.poll([rollout])
                latencies.append((time.perf_counter() - start) * 1000)
            first_count = store.status()["queued"]
            adapter.poll([rollout])
            replay_count = store.status()["queued"]
            adapter.pause([rollout])
            with rollout.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(marker, sort_keys=True) + "\n")
            adapter.resume([rollout])
            adapter.poll([rollout])
            paused_count = store.status()["queued"]
    ordered = sorted(latencies)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    return {
        "synthetic_only": True,
        "events_recovered": first_count,
        "expected_events": 31,
        "marker_events_recovered": first_count - 1,
        "marker_events_expected": 30,
        "replay_queue_count": replay_count,
        "paused_resume_queue_count": paused_count,
        "p95_local_capture_latency_ms": round(p95, 3),
        "median_local_capture_latency_ms": round(statistics.median(latencies), 3),
        "gates": {
            "marker_recovery": first_count == 31,
            "replay_deduplicated": replay_count == first_count,
            "no_paused_backfill": paused_count == first_count,
            "p95_below_30_seconds": p95 < 30000,
        },
    }


def run_evaluation(repo_root: Path, codex_home: Path, output_dir: Path) -> dict[str, Any]:
    manifest = write_manifest(repo_root, output_dir)
    negatives = evaluate_negative_controls(repo_root / "hosted" / "evaluation" / "negative_controls.jsonl")
    source_windows = evaluate_source_windows(repo_root, codex_home)
    live = evaluate_live_adapter()
    deterministic_probe = DecisionParser()
    probe_messages = [
        {"turn": 1, "source_ordinal": 1, "actor": "agent", "text": "I propose option A."},
        {"turn": 2, "source_ordinal": 2, "actor": "user", "text": "Yes, choose option A."},
    ]
    runs = [json.dumps(deterministic_probe.parse("probe", probe_messages), sort_keys=True, separators=(",", ":")) for _ in range(3)]
    gates = {
        "marker_recovery_100_percent": live["gates"]["marker_recovery"],
        "byte_identical_three_runs": len(set(runs)) == 1,
        "marker_assisted_recall_at_least_95_percent": source_windows["marker_assisted_source_window_recall"] >= 0.95,
        "unmarked_recall_at_least_80_percent": source_windows["unmarked_source_window_recall"] >= 0.80,
        "accepted_precision_at_least_90_percent": negatives["accepted_precision"] >= 0.90,
        "no_duplicate_replay": live["gates"]["replay_deduplicated"],
        "no_paused_backfill": live["gates"]["no_paused_backfill"],
        "p95_below_30_seconds": live["gates"]["p95_below_30_seconds"],
    }
    report = {
        "schema_version": "p0.2-evaluation-v1",
        "corpus": manifest,
        "source_windows": source_windows,
        "negative_controls": negatives,
        "live_adapter": live,
        "gates": gates,
        "feasible": all(gates.values()),
        "authority": "inert drafts only; curator verification required",
        "oauth_trial_started": False,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
