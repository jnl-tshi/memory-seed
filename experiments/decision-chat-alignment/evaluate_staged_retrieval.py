"""Score the proposed staged read order against cited sources, never as an online proof.

This evaluates coordinates already produced by the frozen window and ranked-span
experiments. Gold evidence is used only for evaluation; it is never supplied to
the retriever. A gold-guided first-complete stage is an oracle analysis, not a
deployable stop rule. Unresolved rows are excluded from recall denominators.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def coordinates(values: list[list[Any]]) -> set[tuple[str, int]]:
    return {(str(rollout), int(turn)) for rollout, turn in values}


def classify_stages(
    evidence: set[tuple[str, int]],
    top: set[tuple[str, int]],
    envelope: set[tuple[str, int]],
    scope: set[tuple[str, int]],
) -> dict[str, Any]:
    if not top <= envelope:
        raise ValueError("Top-ranked spans must be within the envelope")
    # Fixed-radius context can include turns after the anchor that the causal
    # 72-hour source scope omits. An escalation keeps already-read context.
    expanded_scope = scope | envelope
    if not evidence:
        return {
            "evidence_status": "unresolved",
            "first_complete_stage": None,
            "top_3_all_evidence": False,
            "envelope_all_evidence": False,
            "scope_all_evidence": False,
        }
    stage = next(
        (name for name, selected in (
            ("lexical_top_3", top),
            ("lineage_backward_20", envelope),
            ("source_scope_plus_envelope", expanded_scope),
        ) if evidence <= selected),
        None,
    )
    return {
        "evidence_status": "cited",
        "first_complete_stage": stage,
        "top_3_all_evidence": evidence <= top,
        "envelope_all_evidence": evidence <= envelope,
        "scope_all_evidence": evidence <= expanded_scope,
    }


def evaluate(
    gold_rows: list[dict[str, Any]],
    window_payload: dict[str, Any],
    ranked_payload: dict[str, Any],
    token_payload: dict[str, Any] | None = None,
    *,
    documentation_ids: set[str] | None = None,
) -> dict[str, Any]:
    windows = {row["decision_id"]: row for row in window_payload["rows"]}
    ranked = {row["decision_id"]: row for row in ranked_payload["rows"]}
    tokens = {row["decision_id"]: row for row in token_payload["rows"]} if token_payload else {}
    gold_ids = {row["decision"]["id"] for row in gold_rows}
    if len(gold_ids) != len(gold_rows) or gold_ids != set(windows) or gold_ids != set(ranked):
        raise ValueError("Gold, window, and ranker cohorts differ")
    if token_payload and gold_ids != set(tokens):
        raise ValueError("Token cohort differs from gold")
    rows = []
    documentation_ids = documentation_ids or set()
    for gold in gold_rows:
        decision_id = gold["decision"]["id"]
        cited = {
            (str(ref["rollout_id"]), int(ref["turn"]))
            for ref in gold["adjudication"].get("evidence_refs", [])
        }
        envelope = coordinates(
            windows[decision_id]["strategies"]["lineage_backward_20"]["coordinates"]
        )
        top = coordinates(ranked[decision_id]["strategies"]["lexical_top_3"]["coordinates"])
        scope_data = windows[decision_id].get("source_scope_coordinates")
        if scope_data is None:
            # Older artifacts recorded only a count. The source scope cannot
            # safely be reconstructed from a token *count*; token-stage coords
            # are generated from the original rollout metadata instead.
            if not token_payload:
                raise ValueError("Source coordinates require token artifact for old windows")
            scope_data = tokens[decision_id]["stages"]["source_lineage_scope_72h"]["coordinates"]
        scope = coordinates(scope_data)
        score = classify_stages(cited, top, envelope, scope)
        row = {
            "decision_id": decision_id,
            "strict_decision": decision_id not in documentation_ids,
            "gold_label": gold["adjudication"]["label"],
            "cited_turns": len(cited),
            "top_3_turns": len(top),
            "envelope_turns": len(envelope),
            "scope_turns": len(scope),
            **score,
        }
        if token_payload:
            stages = tokens[decision_id]["stages"]
            row["proxy_tokens"] = {
                name: stages[name]["tokens"] for name in (
                    "full_logical_session", "lineage_backward_20",
                    "lexical_top_3", "minimal_useful_content",
                )
            }
        rows.append(row)
    verified = [row for row in rows if row["gold_label"] == "verified_source"]
    strict_verified = [row for row in verified if row["strict_decision"]]
    stage_counts = Counter(row["first_complete_stage"] or "beyond_scope_or_unresolved" for row in verified)
    return {
        "schema_version": "decision-staged-retrieval-evaluation/1.0",
        "method": "gold-guided oracle stage coverage; escalation unions causal source scope with previously read envelope; no online semantic stop verifier",
        "summary": {
            "rows": len(rows),
            "verified_rows": len(verified),
            "strict_decision_rows": sum(row["strict_decision"] for row in rows),
            "strict_verified_rows": len(strict_verified),
            "unresolved_rows": sum(row["gold_label"] == "unresolved" for row in rows),
            "verified_complete_at_top_3": sum(row["top_3_all_evidence"] for row in verified),
            "verified_complete_at_20": sum(row["envelope_all_evidence"] for row in verified),
            "verified_complete_at_scope": sum(row["scope_all_evidence"] for row in verified),
            "strict_verified_complete_at_top_3": sum(row["top_3_all_evidence"] for row in strict_verified),
            "strict_verified_complete_at_20": sum(row["envelope_all_evidence"] for row in strict_verified),
            "first_complete_stage_counts": dict(sorted(stage_counts.items())),
            "proxy_token_totals": {
                name: sum(row["proxy_tokens"][name] for row in rows)
                for name in ("full_logical_session", "lineage_backward_20", "lexical_top_3", "minimal_useful_content")
            } if token_payload else None,
            "strict_decision_proxy_token_totals": {
                name: sum(row["proxy_tokens"][name] for row in rows if row["strict_decision"])
                for name in ("full_logical_session", "lineage_backward_20", "lexical_top_3", "minimal_useful_content")
            } if token_payload else None,
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--window-results", type=Path, required=True)
    parser.add_argument("--ranked-results", type=Path, required=True)
    parser.add_argument("--token-results", type=Path)
    parser.add_argument("--cohort-manifest", type=Path, help="Identify historical Documentation controls excluded from strict recall")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gold = [json.loads(line) for line in args.gold.read_text(encoding="utf-8").splitlines() if line.strip()]
    window = json.loads(args.window_results.read_text(encoding="utf-8"))
    ranked = json.loads(args.ranked_results.read_text(encoding="utf-8"))
    tokens = json.loads(args.token_results.read_text(encoding="utf-8")) if args.token_results else None
    documentation_ids = set()
    if args.cohort_manifest:
        manifest = json.loads(args.cohort_manifest.read_text(encoding="utf-8"))
        documentation_ids = set(manifest["metadata"].get("known_documentation_records", []))
    result = evaluate(gold, window, ranked, tokens, documentation_ids=documentation_ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
