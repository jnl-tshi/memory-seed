"""Pair each synthesised summary with its live chain for the completeness pass.

The synthesis pass and the pass that checks it must not be the same reader. This builds the second
reader's payload: the ADR's ordered live chain with bodies inline, and the summary written from it,
so the question "which live member's substance is missing" can be answered from the payload alone.

Only summaries that survived `validate_synthesis.py` reach here - a summary citing a retired member
or copying the wording it was meant to replace is already gone, and there is nothing for a
completeness reader to add to that.

Usage:  python experiments/adr-campaign/build_completeness_payload.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PER_BATCH = 5


def main() -> int:
    chains = {c["adr_id"]: c for c in
              json.loads((HERE / "live-chain.json").read_text(encoding="utf-8"))}
    kept = json.loads((HERE / "synthesis-validated.json").read_text(encoding="utf-8"))["kept"]

    payload = []
    for item in kept:
        chain = chains[item["adr_id"]]
        payload.append({
            "adr_id": item["adr_id"],
            "title": chain["title"],
            "live_chain": [
                {"ref": m["ref"], "title": m["title"], "date": m["date"], "body": m["body"]}
                for m in chain["live_chain"]
            ],
            "summary": {
                "decision": item["decision"],
                "why": item["why"],
                "evolution": item["evolution"],
                "covered": item.get("covered") or [],
            },
        })

    (HERE / "completeness-payload.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    for i in range(0, len(payload), PER_BATCH):
        (HERE / f"complete-batch-{i // PER_BATCH}.json").write_text(
            json.dumps(payload[i:i + PER_BATCH], indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"summaries to check: {len(payload)}; batches: {-(-len(payload) // PER_BATCH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
