"""Build a private, incomplete-by-default adjudication draft from explicit choices.

The selection file names which independently checked review supplies each
final source and records the adjudicator's reason. This helper does not choose
the better review, infer labels, or treat blank selections as negatives.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


def indexed(packet: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    reviews = packet.get("reviews")
    if not isinstance(reviews, list):
        raise ValueError(f"{name} lacks reviews")
    output = {row["decision_id"]: row["review"] for row in reviews}
    if len(output) != len(reviews):
        raise ValueError(f"{name} has duplicate decision IDs")
    return output


def build_draft(
    packet_a: dict[str, Any], packet_b: dict[str, Any],
    selections: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    a = indexed(packet_a, "verifier A")
    b = indexed(packet_b, "verifier B")
    if set(a) != set(b):
        raise ValueError("Verifier cohorts differ")
    if not set(selections) <= set(a):
        raise ValueError("Selection contains an unknown decision ID")
    rows = []
    for decision_id in sorted(a):
        selected = selections.get(decision_id)
        final: dict[str, Any] = {"label": None, "evidence_refs": [], "minimal_useful_refs": [],
                                 "rationale": None, "disagreement_resolution": None}
        if selected is not None:
            reviewer = selected.get("use_review")
            if reviewer not in {"A", "B"}:
                raise ValueError(f"{decision_id}: use_review must be A or B")
            reason = selected.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"{decision_id}: adjudication reason required")
            source = a[decision_id] if reviewer == "A" else b[decision_id]
            if source.get("label") is None:
                raise ValueError(f"{decision_id}: selected review is incomplete")
            final = copy.deepcopy(source)
            final["disagreement_resolution"] = reason
            if "selected_candidate_describes_decision" in selected:
                value = selected["selected_candidate_describes_decision"]
                if value is not None and not isinstance(value, bool):
                    raise ValueError(f"{decision_id}: candidate assessment must be bool or null")
                final["selected_candidate_describes_decision"] = value
            if "adjudicated_label" in selected:
                if not (
                    source["label"] == "wrong_candidate"
                    and selected["adjudicated_label"] == "verified_source"
                    and final.get("evidence_refs")
                    and final.get("selected_candidate_describes_decision") is False
                ):
                    raise ValueError(f"{decision_id}: verified alternative requires wrong candidate, source refs, and false candidate assessment")
                final["reviewer_label"] = source["label"]
                final["label"] = "verified_source"
            final["adjudicated_from_verifier"] = reviewer
        rows.append({
            "decision_id": decision_id,
            "verifier_a_review": copy.deepcopy(a[decision_id]),
            "verifier_b_review": copy.deepcopy(b[decision_id]),
            "final_adjudication": final,
        })
    return {
        "schema_version": "decision-verification-adjudication/1.0",
        "method": "explicit human/agent adjudicator selection after independent source review",
        "reviews": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier-a", type=Path, required=True)
    parser.add_argument("--verifier-b", type=Path, required=True)
    parser.add_argument("--selections", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet_a = json.loads(args.verifier_a.read_text(encoding="utf-8"))
    packet_b = json.loads(args.verifier_b.read_text(encoding="utf-8"))
    selected = json.loads(args.selections.read_text(encoding="utf-8"))
    result = build_draft(packet_a, packet_b, selected["selections"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    complete = sum(row["final_adjudication"]["label"] is not None for row in result["reviews"])
    print(json.dumps({"selected": complete, "total": len(result["reviews"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
