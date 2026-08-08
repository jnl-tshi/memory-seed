"""Validate re-synthesised ADR summaries against their live chains.

Same drop-never-repair contract as the rest of the campaign, with the checks retargeted at what
the new criterion actually asserts. A synthesis is not judged on whether it picked the right head -
it is judged on whether it accounts for the whole live chain.

1. **Closed member list.** Every ref in `covered` must be a live member of THAT ADR. A ref under
   `replaced` is retired and must not shape the summary, so citing one is a drop, not a warning.
2. **Coverage.** `covered` must name every live member. A member left out is the worker declaring
   it irrelevant, which is a claim the completeness pass then has to defend - so it is reported
   loudly rather than silently accepted.
3. **Not a copy.** A `decision` equal to the summary it replaces means the pass did nothing. The 22
   provenance-only ADRs are the reason this exists: their current summary is control-file wording,
   and restating it is exactly the failure being corrected.
4. **Length is REPORTED, never a drop** - the standing rule. The caps here match the ones the
   founding writer used, and a summary over them is flagged for trimming rather than discarded.

Usage:  python experiments/adr-campaign/validate_synthesis.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CAPS = {"decision": 700, "why": 700, "evolution": 450}


def norm(text: str) -> str:
    return " ".join((text or "").split())


def main() -> int:
    chains = {c["adr_id"]: c for c in
              json.loads((HERE / "live-chain.json").read_text(encoding="utf-8"))}
    kept, drops, gaps, overlong = [], [], [], []
    seen: set[str] = set()

    for path in sorted(HERE.glob("synth-result-*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            adr = item.get("adr_id", "?")
            item["batch"] = path.name
            seen.add(adr)

            def drop(reason: str) -> None:
                drops.append({"adr_id": adr, "reason": reason, "batch": path.name})

            chain = chains.get(adr)
            if chain is None:
                drop("ADR is not in live-chain.json")
                continue
            # No live member means there is nothing to synthesise FROM: every decision the concern
            # rested on has been replaced. Whatever the worker wrote came from the title and its
            # own reading, not from the corpus, so it cannot pass a chain-synthesis bar. The ADR
            # needs a new head before it needs a summary.
            if not chain["live_chain"]:
                drop("no live chain member - the concern's decisions are all replaced; re-head first")
                continue
            live = {m["ref"] for m in chain["live_chain"]}
            retired = {r["ref"] for r in chain["replaced"]}
            covered = list(item.get("covered") or [])

            missing_fields = [k for k in CAPS if not norm(item.get(k))]
            if missing_fields:
                drop(f"empty {', '.join(missing_fields)}")
                continue
            bad = [r for r in covered if r not in live]
            if bad:
                why = "retired member" if set(bad) & retired else "not a live member"
                drop(f"covered cites {why}: {bad}")
                continue
            if norm(item["decision"]) == norm(chain["current_summary"]):
                drop("decision is the summary it was meant to replace, verbatim")
                continue

            uncovered = sorted(live - set(covered))
            if uncovered:
                gaps.append({"adr_id": adr, "uncovered": uncovered, "live": len(live)})
            over = {k: len(norm(item[k])) for k, cap in CAPS.items() if len(norm(item[k])) > cap}
            if over:
                overlong.append({"adr_id": adr, "over": over})
            kept.append(item)

    unanswered = sorted(set(chains) - seen)
    (HERE / "synthesis-validated.json").write_text(
        json.dumps({"kept": kept, "drops": drops, "coverage_gaps": gaps,
                    "overlong": overlong, "unanswered": unanswered}, indent=1, ensure_ascii=False),
        encoding="utf-8")

    print(f"synthesised: {len(kept) + len(drops)} of {len(chains)} ADRs")
    print(f"  kept:              {len(kept)}")
    print(f"  dropped:           {len(drops)}")
    print(f"  coverage gaps:     {len(gaps)}  (kept, reported - the completeness pass judges these)")
    print(f"  over length caps:  {len(overlong)}  (kept, reported)")
    for g in gaps:
        print(f"    GAP  {g['adr_id']:<38} {len(g['uncovered'])}/{g['live']} live members uncovered: {', '.join(g['uncovered'])}")
    for o in overlong:
        print(f"    LONG {o['adr_id']:<38} {o['over']}")
    for d in drops:
        print(f"    DROP {d['adr_id']:<38} {d['reason'][:90]}")
    if unanswered:
        print(f"  unanswered: {', '.join(unanswered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
