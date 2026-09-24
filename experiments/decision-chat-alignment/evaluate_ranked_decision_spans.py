"""Rank short causal turn spans inside the frozen 50-row retrieval safety envelope.

Gold evidence is read only after ranking. Outputs contain coordinates and counts, never chat text.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


alignment = load_module("align_decisions", "align_decisions.py")
phase = load_module("evaluate_origin_phase_hypotheses", "evaluate_origin_phase_hypotheses.py")

CHOICE = re.compile(r"\b(decid(?:e|ed)|cho(?:ose|se|sen)|prefer|reject|instead|settle|defer|approve|commit to)\b", re.I)
REVIEW = re.compile(r"\b(review(?:er)?|verdict|finding|revise|approved)\b", re.I)
RATIONALE = re.compile(r"\b(because|reason|trade.?off|constraint|alternative|therefore)\b", re.I)


def causal_items(block: Any, cutoff: datetime) -> list[Any]:
    """A turn may span the record time; never score its later messages."""
    end = cutoff + timedelta(minutes=1)  # record headings have minute precision
    return [
        item for item in [*block.items, *block.reasoning_summary_items]
        if (stamp := alignment.parse_iso_timestamp(item.timestamp)) is not None and stamp < end
    ]


def block_text(block: Any, cutoff: datetime) -> str:
    return "\n".join(item.text for item in causal_items(block, cutoff))


def block_features(block: Any, cutoff: datetime) -> dict[str, Any]:
    items = causal_items(block, cutoff)
    texts = [item.text for item in items]
    combined = "\n".join(texts)
    return {
        "text": combined,
        "characters": len(combined),
        "user": any(item.role == "user" for item in items),
        "assistant": any(item.role == "assistant" for item in items),
        "tool_count": sum(item.role == "tool" for item in items),
        "choice": bool(CHOICE.search(combined)),
        "review": bool(REVIEW.search(combined)),
        "rationale": bool(RATIONALE.search(combined)),
        "plan": block.collaboration_mode == "plan",
    }


def lexical_score(title: str, text: str) -> float:
    query = alignment.distinctive_tokens(title)
    document = alignment.distinctive_tokens(text)
    if not query:
        return 0.0
    overlap = len(query & document) / len(query)
    identifiers = alignment.identifiers(title)
    id_overlap = len(identifiers & alignment.identifiers(text)) / len(identifiers) if identifiers else 0.0
    return overlap + 0.35 * id_overlap


def decision_query(repo: Path, decision: dict[str, Any]) -> str:
    lines = (repo / decision["record_path"]).read_text(encoding="utf-8").splitlines()
    start = int(decision["record_start_line"]) - 1
    end = int(decision["record_end_line"])
    return "\n".join(lines[start:end])


def rank_spans(
    blocks: list[Any], title: str, origin: str | None, cutoff: datetime, *,
    width: int = 3, variant: str = "phase",
) -> list[dict[str, Any]]:
    """Rank without inspecting evidence coordinates or adjudication labels."""
    if width < 1:
        raise ValueError("width must be positive")
    groups: dict[str, list[Any]] = defaultdict(list)
    for block in blocks:
        if block.start_utc and block.start_utc < cutoff + timedelta(minutes=1):
            groups[block.session.session_id].append(block)
    candidates: list[dict[str, Any]] = []
    for group in groups.values():
        group.sort(key=lambda block: (block.start_utc, block.session.rollout_id, block.turn_number))
        features = [block_features(block, cutoff) for block in group]
        for start in range(len(group)):
            members = group[start:start + width]
            member_features = features[start:start + width]
            if not any(value["text"] for value in member_features):
                continue
            text = "\n".join(value["text"] for value in member_features)
            score = lexical_score(title, text)
            if variant == "recency":
                score = members[-1].start_utc.timestamp()
            elif variant == "phase":
                score += 0.055 * any(value["choice"] for value in member_features)
                score += 0.035 * any(value["rationale"] for value in member_features)
                score += 0.025 * any(value["plan"] for value in member_features)
                score += 0.025 * any(value["review"] for value in member_features)
                if origin == "user" and any(value["user"] for value in member_features):
                    score += 0.025
                if origin == "agent" and any(value["assistant"] for value in member_features):
                    score += 0.015
            elif variant == "plan":
                score += 0.025 * any(value["plan"] for value in member_features)
            elif variant == "review":
                score += 0.025 * any(value["review"] for value in member_features)
            elif variant == "origin":
                if origin == "user" and any(value["user"] for value in member_features):
                    score += 0.025
                if origin == "agent" and any(value["assistant"] for value in member_features):
                    score += 0.015
            elif variant not in {"lexical", "boundary"}:
                raise ValueError(f"Unknown variant: {variant}")
            # A new user message after tool-heavy work is a possible round boundary.
            if variant in {"boundary", "phase"} and start > 0 and features[start - 1]["tool_count"] >= 3 and member_features[0]["user"]:
                score += 0.025
            coordinates = {(block.session.rollout_id, block.turn_number) for block in members}
            candidates.append({
                "coordinates": coordinates,
                "score": score,
                "characters": sum(value["characters"] for value in member_features),
                "start": members[0].start_utc,
            })
    return sorted(candidates, key=lambda span: (-span["score"], -span["start"].timestamp(), sorted(span["coordinates"])))


def select_top(spans: list[dict[str, Any]], count: int) -> set[tuple[str, int]]:
    selected: set[tuple[str, int]] = set()
    for span in spans[:count]:
        selected.update(span["coordinates"])
    return selected


def summarize(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    verified = [row for row in rows if row["label"] == "verified_source"]
    retained = sum(len(row[key]) for row in rows)
    pool = sum(len(row["pool"]) for row in rows)
    retained_chars = sum(sum(row["turn_chars"].get(coord, 0) for coord in row[key]) for row in rows)
    pool_chars = sum(sum(row["turn_chars"].get(coord, 0) for coord in row["pool"]) for row in rows)
    return {
        "any_evidence_rows": sum(bool(row[key] & row["evidence"]) for row in rows),
        "all_evidence_rows": sum(row["evidence"] <= row[key] for row in rows),
        "verified_all_evidence_rows": sum(row["evidence"] <= row[key] for row in verified),
        "mean_turns": retained / len(rows),
        "turn_reduction_vs_pool": 1 - retained / pool if pool else 0,
        "character_reduction_vs_pool": 1 - retained_chars / pool_chars if pool_chars else 0,
        "missed_verified_ids": [row["id"] for row in verified if not row["evidence"] <= row[key]],
    }


def evaluate(repo: Path, codex_home: Path) -> dict[str, Any]:
    gold = phase.read_gold(BASE / "GOLD-SET.jsonl")
    control = json.loads((BASE / "WINDOW-STRATEGY-RESULTS.json").read_text(encoding="utf-8"))
    controls = {row["decision_id"]: row for row in control["rows"]}
    if set(controls) != {row["decision"]["id"] for row in gold}:
        raise RuntimeError("Gold and safety envelope cohorts differ")
    selected_rollouts = {
        str(coord[0]) for row in controls.values()
        for coord in row["strategies"]["lineage_backward_12"]["coordinates"]
    }
    metas = [
        meta for path in alignment.iter_rollout_paths(codex_home)
        if (meta := alignment.read_session_meta(path)) is not None and meta.rollout_id in selected_rollouts
    ]
    alignment.validate_unique_rollouts(metas)
    blocks_by_rollout = {
        meta.rollout_id: alignment.parse_rollout(Path(meta.source_path), meta) for meta in metas
    }
    rows: list[dict[str, Any]] = []
    for item in gold:
        decision = item["decision"]
        decision_id = decision["id"]
        cutoff = alignment.parse_iso_timestamp(decision["timestamp"])
        if cutoff is None:
            raise RuntimeError(f"Bad record timestamp: {decision_id}")
        envelope = {
            (str(coord[0]), int(coord[1]))
            for coord in controls[decision_id]["strategies"]["lineage_backward_12"]["coordinates"]
        }
        blocks = [
            block for rollout_id in {coord[0] for coord in envelope}
            for block in blocks_by_rollout.get(rollout_id, [])
            if (rollout_id, block.turn_number) in envelope and causal_items(block, cutoff)
        ]
        pool = {(block.session.rollout_id, block.turn_number) for block in blocks}
        turn_chars = {
            (block.session.rollout_id, block.turn_number): len(block_text(block, cutoff))
            for block in blocks
        }
        entry_id, ordinal = decision_id.rsplit(":", 1)
        origin = phase.read_explicit_origin(repo / decision["record_path"], entry_id, ordinal)
        ranked = {
            variant: rank_spans(blocks, decision["title"], origin, cutoff, variant=variant)
            for variant in ("recency", "lexical", "boundary", "plan", "review", "origin", "phase")
        }
        ranked["full_record"] = rank_spans(
            blocks, decision_query(repo, decision), origin, cutoff, variant="lexical"
        )
        evidence = {
            (str(ref["rollout_id"]), int(ref["turn"]))
            for ref in item["adjudication"]["evidence_refs"]
        }
        rows.append({
            "id": decision_id,
            "label": item["adjudication"]["label"],
            "evidence": evidence,
            "pool": pool,
            "turn_chars": turn_chars,
            **{
                f"{variant}_top_{count}": select_top(ranked[variant], count)
                for variant in ranked for count in (1, 2, 3)
            },
        })
    keys = ["pool", *(f"{variant}_top_{count}" for variant in ("recency", "lexical", "full_record", "boundary", "plan", "review", "origin", "phase") for count in (1, 2, 3))]
    return {
        "schema_version": "decision-ranked-span-ablation/1.0",
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sample_ids_sha256": gold[0]["cohort"]["sample_ids_sha256"],
            "gold_rows": len(rows),
            "verified_rows": sum(row["label"] == "verified_source" for row in rows),
            "span_width_turns": 3,
            "causal_cutoff": "record minute end",
            "queries": ["decision title", "full final record"],
            "raw_text_serialized": False,
        },
        "summary": {key: summarize(rows, key) for key in keys},
        "rows": [{
            "decision_id": row["id"],
            "gold_label": row["label"],
            "pool_turns": len(row["pool"]),
            "evidence_turns": sorted([list(coord) for coord in row["evidence"]]),
            "strategies": {
                key: {
                    "turns": len(row[key]),
                    "any_evidence": bool(row[key] & row["evidence"]),
                    "all_evidence": row["evidence"] <= row[key],
                    "coordinates": sorted([list(coord) for coord in row[key]]),
                }
                for key in keys
            },
        } for row in rows],
    }


def report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Ranked short-span decision retrieval",
        "",
        "## Method",
        "",
        "The frozen Codex-only 50-decision gold cohort and previously measured lineage plus 12-turn envelope are reused. Candidate spans contain up to three adjacent turns from one logical task. Turns and messages after the decision-record minute are excluded. Queries use the decision title or full final record. Gold evidence coordinates are read only after ranking. Recency, lexical overlap, isolated cue variants, and a combined phase variant are compared. Cues affect ranking only.",
        "",
        "| Strategy | Any evidence /50 | All evidence /50 | Verified complete /42 | Mean turns | Turn reduction vs causal envelope | Character reduction vs causal envelope |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key in ("pool", *(f"{variant}_top_{count}" for count in (1, 2, 3) for variant in ("recency", "lexical", "full_record", "boundary", "plan", "review", "origin", "phase"))):
        value = summary[key]
        lines.append(
            f"| {key.replace('_', ' ')} | {value['any_evidence_rows']} | {value['all_evidence_rows']} | "
            f"{value['verified_all_evidence_rows']} | {value['mean_turns']:.1f} | "
            f"{value['turn_reduction_vs_pool']:.1%} | {value['character_reduction_vs_pool']:.1%} |"
        )
    lines.extend([
        "", "## Interpretation", "",
        "The best tested three-span setting is title lexical overlap: 39/42 verified decisions retain every cited turn (92.9%), with 64.0% fewer parsed characters than the causal envelope. That is below the exploratory 98% complete-evidence target. A full final-record query is stronger for a single span (36/42 versus title-only 26/42), but weaker at three spans (37/42 versus 39/42); more query text is not a uniformly better ranker. The combined phase-cue score retains only 31/42 at three spans. These figures support using ranking to prioritize inspection, not to discard the rest of the envelope.",
        "",
        "The next bounded test should inspect the three title-lexical misses at message level, then trial adaptive expansion: inspect the highest-ranked spans first, expand backward/through lineage when evidence is incomplete, and retain the 12-turn envelope as a fallback. The tool-heavy-then-user cue is only a possible round boundary; this experiment did not establish that implementation was complete at those points. The origin field is too sparse in this cohort to judge its value.",
        "",
        "The causal envelope is the recall ceiling for these ranking variants. A gold turn can be counted even if the cited message is later in a long turn; future work should evaluate message-level provenance before treating turn recall as curator-ready context.",
        "",
        "This is a development-cohort ablation. The 50 rows informed the feature choices. A held-out cohort is needed before adopting weights or a cutoff. The envelope starts from the previously selected session, so the result does not measure end-to-end session finding. Full final records may echo source wording, so their lexical advantage cannot be transferred to prospective decision detection. Review language identifies relevant context but cannot by itself identify a reviewer agent. Character counts measure retained parsed message text, not billed tokens or the curator's exact input.",
        "", "## Provenance", "",
        f"Sample hash: `{result['metadata']['sample_ids_sha256']}`. Coordinate-level results are in `RANKED-SPAN-RESULTS.json`. No raw chat or reasoning text is written to either artifact.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--output", type=Path, default=BASE)
    args = parser.parse_args()
    result = evaluate(args.repo.resolve(), args.codex_home.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "RANKED-SPAN-RESULTS.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "RANKED-SPAN-REPORT.md").write_text(report(result), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
