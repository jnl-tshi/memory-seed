"""Build the adversarial verification payload for the v2 attachment picks.

25 of 29 came back `primary`. An 86% conversion rate is a red flag, not a win: a worker handed the
top-25 semantic hits will find SOMETHING plausible in every list, which is fitting to the ranking
rather than finding the decision that founded the concern. The grounding check catches invented
quotes (it caught 2) but says nothing about whether the right decision was chosen.

So each pick goes to a second worker prompted to REFUTE it, with the same candidate list in hand so
"a different candidate is the real founder" is an available answer alongside "none of them is".

Usage:  python experiments/adr-campaign/build_refute_payload.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PER_BATCH = 5


def main() -> int:
    payload = {p["adr_id"]: p for p in
               json.loads((HERE / "attach-payload-v2.json").read_text(encoding="utf-8"))}
    validated = json.loads((HERE / "attach-validated.json").read_text(encoding="utf-8"))
    picks = [k for k in validated["kept"] if k["verdict"] in {"primary", "supporting"}]

    out = []
    for pick in picks:
        source = payload[pick["adr_id"]]
        chosen = next(c for c in source["candidates"] if c["ref"] == pick["ref"])
        others = [c for c in source["candidates"] if c["ref"] != pick["ref"]]
        out.append({
            "adr_id": pick["adr_id"],
            "title": source["title"],
            "concern": source["concern"],
            "claim": {
                "ref": pick["ref"],
                "title": chosen["title"],
                "body": chosen["body"],
                "why_claimed": pick["why"],
            },
            "other_candidates": others,
        })

    (HERE / "refute-payload.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for i in range(0, len(out), PER_BATCH):
        (HERE / f"refute-batch-{i // PER_BATCH}.json").write_text(
            json.dumps(out[i:i + PER_BATCH], indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"claims to refute: {len(out)}; batches: {-(-len(out) // PER_BATCH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
