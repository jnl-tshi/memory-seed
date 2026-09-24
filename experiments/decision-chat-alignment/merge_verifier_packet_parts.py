"""Combine two non-overlapping private verifier packet segments fail-closed."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


def merge_parts(head: dict[str, Any], tail: dict[str, Any]) -> dict[str, Any]:
    if head.get("verifier") != tail.get("verifier"):
        raise ValueError("verifier identity drift")
    if head.get("cohort_ids_sha256") != tail.get("cohort_ids_sha256"):
        raise ValueError("cohort hash drift")
    rows_a = head.get("reviews", [])
    rows_b = tail.get("reviews", [])
    if [row["decision_id"] for row in rows_a] != [row["decision_id"] for row in rows_b]:
        raise ValueError("packet decision order or IDs differ")
    result = copy.deepcopy(head)
    for position, (left, right) in enumerate(zip(rows_a, rows_b)):
        left_done = left["review"].get("label") is not None
        right_done = right["review"].get("label") is not None
        if left_done and right_done:
            raise ValueError(f"completed review overlap: {left['decision_id']}")
        if right_done:
            result["reviews"][position]["review"] = copy.deepcopy(right["review"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--tail", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    head = json.loads(args.head.read_text(encoding="utf-8"))
    tail = json.loads(args.tail.read_text(encoding="utf-8"))
    result = merge_parts(head, tail)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    completed = sum(row["review"].get("label") is not None for row in result["reviews"])
    print(json.dumps({"completed": completed, "total": len(result["reviews"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
