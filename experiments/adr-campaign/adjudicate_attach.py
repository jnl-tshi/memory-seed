"""Join the attachment picks to their refutations and report what survives.

Three outcomes, and the second is the reason this pass exists:

- **stands** - both passes agree the decision founded the concern. Write it.
- **refuted, better_ref named** - the refuter found a decision that institutes the rule where the
  claim only proposed, applied or refined it. The better ref must ITSELF be re-grounded before it
  can be written, so it is reported as a candidate rather than silently swapped in.
- **refuted, no alternative** - the concern predates the session log. The ADR keeps its founding
  control-file line, which is the honest record.

Usage:  python experiments/adr-campaign/adjudicate_attach.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from memory_seed.retrieval import get_chunk  # noqa: E402


def norm(text: str) -> str:
    return " ".join(text.split())


def main() -> int:
    validated = json.loads((HERE / "attach-validated.json").read_text(encoding="utf-8"))
    picks = {p["adr_id"]: p for p in validated["kept"] if p["verdict"] in {"primary", "supporting"}}
    nones = [p["adr_id"] for p in validated["kept"] if p["verdict"] == "none"]
    dropped = {d["adr_id"] for d in validated["drops"]}

    verdicts = {}
    for path in sorted(HERE.glob("refute-result-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            verdicts[item["adr_id"]] = item

    stands, swap, unfounded, unjudged = [], [], [], []
    for adr_id, pick in picks.items():
        verdict = verdicts.get(adr_id)
        if not verdict:
            unjudged.append(adr_id)
            continue
        row = {"adr_id": adr_id, "ref": pick["ref"], "quote": pick["quote"],
               "why": pick["why"], "refuter": verdict["reason"]}
        if verdict["verdict"] == "stands":
            stands.append(row)
        elif verdict.get("better_ref"):
            row["better_ref"] = verdict["better_ref"]
            try:
                chunk = get_chunk(verdict["better_ref"], REPO)
                row["better_title"] = norm(chunk.get("title") or "")
                row["better_resolves"] = True
            except Exception as exc:
                row["better_resolves"] = False
                row["better_error"] = str(exc)
            swap.append(row)
        else:
            unfounded.append(row)

    report = {"stands": stands, "needs_swap": swap, "unfounded": unfounded,
              "worker_none": nones, "grounding_drops": sorted(dropped), "unjudged": unjudged}
    (HERE / "attach-adjudicated.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")

    total = len(picks) + len(nones) + len(dropped)
    print(f"29 founding-only ADRs -> {total} answers")
    print(f"  survive both passes (write):      {len(stands)}")
    print(f"  refuted, better ref named:        {len(swap)}")
    print(f"  refuted, nothing founds it:       {len(unfounded)}")
    print(f"  worker said none:                 {len(nones)}")
    print(f"  dropped on grounding:             {len(dropped)}")
    if unjudged:
        print(f"  UNJUDGED (no refutation): {', '.join(unjudged)}")
    print()
    for row in swap:
        flag = "" if row.get("better_resolves") else "  [BETTER REF DOES NOT RESOLVE]"
        print(f"  SWAP {row['adr_id']:<32} {row['ref']} -> {row['better_ref']}{flag}")
    for row in unfounded:
        print(f"  KEEP-FOUNDING {row['adr_id']}")
    for adr_id in nones + sorted(dropped):
        print(f"  KEEP-FOUNDING {adr_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
