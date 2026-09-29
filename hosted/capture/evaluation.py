from __future__ import annotations

import importlib.util
import json
import re
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


PROSPECTIVE_FORWARD_TURNS = 20
_AGREEMENT_TEXT = re.compile(r"\b(?:yes|agree|approved|accept|choose|use|adopt|go with|right approach|would be wise)\b", re.I)
_CONTEXTUAL_ACCEPTANCE_TEXT = re.compile(r"\b(?:that'?s (?:the )?right|would be wise|sounds right)\b", re.I)
_STOPWORDS = {
    "about", "after", "again", "also", "because", "been", "before", "being", "could", "from",
    "have", "into", "only", "should", "that", "their", "there", "these", "this", "those", "through",
    "using", "were", "what", "when", "where", "which", "with", "would",
}


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


def _load_window_strategy(repo_root: Path):
    path = repo_root / "experiments" / "decision-chat-alignment" / "evaluate_window_strategies.py"
    spec = importlib.util.spec_from_file_location("p02_window_strategy_foundation", path)
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


def _prospective_marker_envelope(
    *,
    rollout_id: str,
    marker_turn: int,
    marker_time: Any,
    metas: list[Any],
    blocks_by_rollout: dict[str, list[Any]],
    window_strategy: Any,
) -> set[tuple[str, int]]:
    """Recover causal context, then observe a small number of turns after the marker."""
    by_rollout = {meta.rollout_id: meta for meta in metas}
    selected = by_rollout.get(rollout_id)
    if selected is None:
        return set()
    envelope = window_strategy.lineage_adaptive_coordinates(
        selected_rollout_id=rollout_id,
        anchor_turn=marker_turn,
        decision_time=marker_time,
        metas=metas,
        blocks_by_rollout=blocks_by_rollout,
        plan_lookback=0,
        fallback_lookback=window_strategy.SAFETY_LOOKBACK_TURNS,
        forward_turns=0,
        max_depth=window_strategy.MAX_PARENT_DEPTH,
    )
    current_task = sorted(
        [
            block
            for meta in metas
            if meta.session_id == selected.session_id
            for block in blocks_by_rollout.get(meta.rollout_id, [])
        ],
        key=lambda block: (block.start_utc, block.session.timestamp_utc, block.session.rollout_id, block.turn_number),
    )
    marker_index = next(
        (
            index for index, block in enumerate(current_task)
            if block.session.rollout_id == rollout_id and block.turn_number == marker_turn
        ),
        None,
    )
    if marker_index is not None:
        start = max(0, marker_index - window_strategy.SAFETY_LOOKBACK_TURNS)
        end = min(len(current_task), marker_index + PROSPECTIVE_FORWARD_TURNS + 1)
        envelope.update(
            (block.session.rollout_id, block.turn_number)
            for block in current_task[start:end]
        )
    return envelope


def _semantic_terms(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text)
        if token.lower() not in _STOPWORDS
    }


def _record_text(repo_root: Path, row: dict[str, Any]) -> str:
    record = row["record"]
    lines = (repo_root / record["path"]).read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[int(record["start_line"]) - 1:int(record["end_line"])])


def evaluate_source_windows(repo_root: Path, codex_home: Path) -> dict[str, Any]:
    manifest = build_manifest(repo_root)
    module = _load_alignment_parser(repo_root)
    window_strategy = _load_window_strategy(repo_root)
    rollout_paths = _rollout_paths(codex_home)
    parser = DecisionParser()
    eligible = [
        row for row in manifest["rows"]
        if row["record_kind"] == "Decision"
        and row["split"] in {"development", "heldout_descriptive"}
        and row["adjudication_label"] == "verified_source"
        and row["evidence_coordinates"]
    ]
    all_metas = []
    meta_paths: dict[str, Path] = {}
    for rollout_id, path in rollout_paths.items():
        meta = module.read_session_meta(path)
        if meta is not None:
            all_metas.append(meta)
            meta_paths[rollout_id] = path
    by_rollout = {meta.rollout_id: meta for meta in all_metas}
    relevant_tasks: set[str] = set()
    for row in eligible:
        refs = row["evidence_coordinates"]
        anchor = max(refs, key=lambda ref: str(ref.get("timestamp", "")))
        meta = by_rollout.get(str(anchor["rollout_id"]).lower())
        if meta is not None:
            relevant_tasks.add(meta.session_id)
    for _depth in range(window_strategy.MAX_PARENT_DEPTH):
        parents = {
            meta.parent_thread_id
            for meta in all_metas
            if meta.session_id in relevant_tasks and meta.parent_thread_id
        }
        relevant_tasks.update(parents)
    relevant_metas = [meta for meta in all_metas if meta.session_id in relevant_tasks]
    blocks_by_rollout = {
        meta.rollout_id: module.parse_rollout(meta_paths[meta.rollout_id], meta)
        for meta in relevant_metas
        if meta.rollout_id in meta_paths
    }

    legacy_marker_hits = 0
    hierarchical_hits = 0
    unmarked_hits = 0
    unavailable: list[str] = []
    hierarchical_misses: list[str] = []
    extraction_rows: list[dict[str, Any]] = []
    for row in eligible:
        refs = row["evidence_coordinates"]
        turns = [ref["turn"] for ref in refs if isinstance(ref.get("turn"), int)]
        if not turns:
            unavailable.append(row["case_id"])
            continue
        anchor = max(refs, key=lambda ref: str(ref.get("timestamp", "")))
        marker_turn = int(anchor["turn"])
        rollout_id = str(anchor["rollout_id"]).lower()
        if all(
            str(ref["rollout_id"]).lower() == rollout_id
            and marker_turn - 2 <= int(ref["turn"]) <= marker_turn + 1
            for ref in refs
        ):
            legacy_marker_hits += 1

        selected_meta = by_rollout.get(rollout_id)
        decision_time = module.parse_iso_timestamp(str(anchor.get("timestamp", "")))
        if selected_meta is None or decision_time is None or rollout_id not in blocks_by_rollout:
            unavailable.append(row["case_id"])
            continue
        envelope = _prospective_marker_envelope(
            rollout_id=rollout_id,
            marker_turn=marker_turn,
            marker_time=decision_time,
            metas=relevant_metas,
            blocks_by_rollout=blocks_by_rollout,
            window_strategy=window_strategy,
        )
        evidence = {(str(ref["rollout_id"]).lower(), int(ref["turn"])) for ref in refs}
        if evidence.issubset(envelope):
            hierarchical_hits += 1
        else:
            hierarchical_misses.append(row["case_id"])

        blocks = [
            block
            for candidate_rollout, candidate_turn in sorted(envelope)
            for block in blocks_by_rollout.get(candidate_rollout, [])
            if block.turn_number == candidate_turn
        ]
        messages = [
            {
                "rollout_id": block.session.rollout_id,
                "turn": block.turn_number,
                "source_ordinal": item.source_ordinal if item.source_ordinal is not None else -1,
                "actor": "agent" if item.role == "assistant" else item.role,
                "timestamp": item.timestamp,
                "collaboration_mode": block.collaboration_mode,
                "text": item.text,
            }
            for block in sorted(blocks, key=lambda value: (value.start_utc, value.session.rollout_id, value.turn_number))
            for item in block.items
            if item.role in {"user", "assistant"}
        ]
        current = [message for message in messages if message["rollout_id"] == rollout_id]
        lineage = [message for message in messages if message["rollout_id"] != rollout_id]
        if parser.parse(rollout_id, current, lineage_messages=lineage):
            unmarked_hits += 1
        anchor_message = next(
            (
                message for message in current
                if int(message.get("turn", -1)) == marker_turn
                and int(message.get("source_ordinal", -1)) == int(anchor.get("source_ordinal", -2))
            ),
            next((message for message in current if int(message.get("turn", -1)) == marker_turn), None),
        )
        if anchor_message is None:
            unavailable.append(row["case_id"])
            continue
        anchor_text = str(anchor_message.get("text", ""))
        actor = str(anchor_message.get("actor", "agent"))
        accepted = actor == "user" and bool(_AGREEMENT_TEXT.search(anchor_text))
        marker = {
            "turn": marker_turn,
            "source_ordinal": int(anchor_message.get("source_ordinal", -1)),
            "strength": "hard" if accepted else "soft",
            "state": "accepted" if accepted else "proposed",
            "origin": "user" if actor == "user" else "agent",
            "trigger_class": (
                "contextual_acceptance" if accepted and _CONTEXTUAL_ACCEPTANCE_TEXT.search(anchor_text)
                else "explicit_commitment" if accepted
                else "agent_inference"
            ),
            "issue_hint": " ".join(sorted(_semantic_terms(anchor_text))[:8]) or "decision candidate",
            "trigger_quote": anchor_text[:160],
        }
        drafts = parser.parse_stepped(rollout_id, current, marker=marker, lineage_messages=lineage)
        extraction_rows.append({
            "case_id": row["case_id"],
            "split": row["split"],
            "drafts_emitted": len(drafts),
            "complete_drafts": sum(bool(draft.get("complete")) for draft in drafts),
            "semantic_equivalence": None,
            "semantic_review_status": "not_adjudicated",
            "drafts": [{
                "candidate_id": draft["candidate_id"],
                "state": draft["state"],
                "complete": draft.get("complete", False),
                "missing_components": draft.get("missing_components", []),
                "source_coordinates": draft["source"]["source_coordinates"],
                "rule_path": draft["rule_path"],
                "trace": draft["source"].get("retrieval_trace"),
            } for draft in drafts],
        })
    denominator = len(eligible)
    return {
        "evaluation_kind": "oracle_source_anchor_diagnostic",
        "limitations": [
            "Gold source coordinates select the anchor and lineage; this is not prospective detection.",
            "Turn-envelope coverage is not exact-span coverage or extracted decision correctness.",
            "Candidate presence in a gold-selected window is not unmarked detection recall.",
            "Historical records lack field-level semantic and accepted/proposed adjudication.",
            "Future turns in this retrospective diagnostic may contain post-hoc records.",
        ],
        "eligible_verified_rows": denominator,
        "available_rollout_ids": len(blocks_by_rollout),
        "legacy_four_turn_envelope_coverage": legacy_marker_hits / denominator if denominator else 0.0,
        "oracle_hierarchical_envelope_coverage": hierarchical_hits / denominator if denominator else 0.0,
        "oracle_hierarchical_envelope_hits": hierarchical_hits,
        "oracle_hierarchical_envelope_misses": hierarchical_misses,
        "candidate_presence_in_gold_windows": unmarked_hits / denominator if denominator else 0.0,
        "marker_assisted_source_window_recall": None,
        "unmarked_source_window_recall": None,
        "semantic_equivalence": None,
        "extraction_diagnostics": extraction_rows,
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
    if output_dir.resolve() in {(repo_root / "hosted" / "evaluation").resolve(),
                                (repo_root / "hosted" / "evaluation" / "results").resolve()}:
        raise ValueError("Preserve the frozen baseline; choose a separate diagnostic output directory")
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
        "marker_assisted_recall_at_least_95_percent": None,
        "unmarked_recall_at_least_80_percent": None,
        "semantic_decision_equivalence": None,
        "accepted_precision_at_least_90_percent": negatives["accepted_precision"] >= 0.90,
        "no_duplicate_replay": live["gates"]["replay_deduplicated"],
        "no_paused_backfill": live["gates"]["no_paused_backfill"],
        "p95_below_30_seconds": live["gates"]["p95_below_30_seconds"],
    }
    report = {
        "schema_version": "p0.2-evaluation-v2-diagnostic",
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
